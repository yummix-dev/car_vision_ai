"""Saved renders — "Мои примерки".

Covers the store, the auto-save at job completion, the listing/delete endpoints,
and the media-sweep exemption that keeps a saved render from ageing out.
"""

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.generation import GenerationJob, JobState, JobStatus
from app.models.telegram import TelegramUser
from app.server import create_app
from app.services import cleanup, gallery, generation_service, photos, quota, users

from tests.test_telegram import make_init_data  # signs for USER id 4242


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(s, "media_dir", str(tmp_path / "media"))
    reset_for_tests()
    yield


def _media(pid: str) -> str:
    Image.new("RGB", (4, 4), "#123456").save(
        get_settings().media_path / f"{pid}.jpg", "JPEG"
    )
    return pid


def _user(tid: int = 4242) -> dict:
    return users.get_or_create(TelegramUser(id=tid, first_name="U"))


def _save(user_id: int, **over) -> None:
    args = dict(
        user_id=user_id, job_id="j1", product_id="amg", category_id="rul",
        before_photo_id="b1", after_photo_id="a1-after",
        car_label="Chevrolet Malibu 2023",
    )
    args.update(over)
    gallery.save(**args)


# ── the store ─────────────────────────────────────────────────


def test_save_then_list_returns_the_render():
    u = _user()
    _save(u["id"])
    items = gallery.list_for_user(u["id"])
    assert len(items) == 1
    assert items[0]["product_id"] == "amg"
    assert items[0]["car_label"] == "Chevrolet Malibu 2023"


def test_save_is_idempotent_on_job_id():
    """A retried completion path (or a re-polled done job) is one saved row."""
    u = _user()
    _save(u["id"])
    _save(u["id"], product_id="rs")  # same job_id, different payload
    items = gallery.list_for_user(u["id"])
    assert len(items) == 1
    assert items[0]["product_id"] == "amg", "the first save wins; the retry is ignored"


def test_list_is_newest_first():
    u = _user()
    gallery.save(user_id=u["id"], job_id="old", product_id="amg", category_id="rul",
                 before_photo_id="b", after_photo_id="a", car_label=None)
    with connect(immediate=True) as conn:
        conn.execute("UPDATE saved_generations SET created_at=100 WHERE job_id='old'")
    gallery.save(user_id=u["id"], job_id="new", product_id="rs", category_id="rul",
                 before_photo_id="b2", after_photo_id="a2", car_label=None)
    ids = [r["job_id"] for r in gallery.list_for_user(u["id"])]
    assert ids == ["new", "old"]


def test_delete_is_scoped_to_the_owner():
    owner = _user(4242)
    other = _user(9999)
    _save(owner["id"])
    row = gallery.list_for_user(owner["id"])[0]

    assert gallery.delete(other["id"], row["id"]) is False, "not the owner"
    assert gallery.list_for_user(owner["id"]), "still there"
    assert gallery.delete(owner["id"], row["id"]) is True
    assert gallery.list_for_user(owner["id"]) == []


def test_protected_photo_ids_covers_before_and_after():
    u = _user()
    _save(u["id"], before_photo_id="src-1", after_photo_id="gen-1-after")
    assert gallery.protected_photo_ids() == {"src-1", "gen-1-after"}


# ── auto-save at completion ───────────────────────────────────


def _reserved_job(user_id: int, job_id: str = "job-x") -> tuple[GenerationJob, JobState]:
    reservation = quota.reserve(user_id, "rul", f"key-{job_id}")
    quota.attach_job(reservation["id"], job_id)
    job = GenerationJob(
        job_id=job_id, source_photo_id="src-x", product_id="amg",
        category_id="rul", region_label="руль",
    )
    state = JobState(job_id=job_id, status=JobStatus.done, after_photo_id="gen-x-after")
    return job, state


def test_completion_saves_for_the_reserving_user_with_their_car():
    u = _user()
    users.confirm_car(u["id"], "Chevrolet", "Malibu", 2023)
    job, state = _reserved_job(u["id"])

    generation_service._save_to_gallery(job, state)

    items = gallery.list_for_user(u["id"])
    assert len(items) == 1
    assert items[0]["job_id"] == "job-x"
    assert items[0]["before_photo_id"] == "src-x"
    assert items[0]["after_photo_id"] == "gen-x-after"
    assert items[0]["car_label"] == "Chevrolet Malibu 2023"


def test_completion_without_a_reservation_saves_nothing():
    """A browser generation has no quota reservation, hence no owner, hence no
    gallery row — the same line quotas and referrals draw."""
    job = GenerationJob(
        job_id="anon", source_photo_id="s", product_id="amg",
        category_id="rul", region_label="руль",
    )
    state = JobState(job_id="anon", status=JobStatus.done, after_photo_id="g-after")

    generation_service._save_to_gallery(job, state)

    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM saved_generations").fetchone()["c"] == 0


# ── the endpoints ─────────────────────────────────────────────


def test_gallery_is_empty_for_a_browser_visitor():
    client = TestClient(create_app())
    res = client.get("/api/gallery")  # no initData
    assert res.status_code == 200
    assert res.json() == []


def test_gallery_lists_saved_renders_with_localized_category():
    u = _user()
    _media("b1")
    _media("a1-after")
    _save(u["id"])
    client = TestClient(create_app())

    ru = client.get("/api/gallery", headers={"X-Telegram-Init-Data": make_init_data()}).json()
    assert len(ru) == 1
    assert ru[0]["product_name"] == "AMG Carbon LED"   # brand, not translated
    assert ru[0]["category_label"] == "Руль"
    assert ru[0]["after_url"].endswith("a1-after.jpg")

    uz = client.get(
        "/api/gallery",
        headers={"X-Telegram-Init-Data": make_init_data(), "X-Lang": "uz"},
    ).json()
    assert uz[0]["category_label"] == "Rul"


def test_gallery_hides_a_render_whose_files_are_gone():
    """A row can outlive its media if the files are removed by hand; it is
    dropped from the listing rather than shown as a broken image."""
    u = _user()
    _save(u["id"])  # no media files created
    client = TestClient(create_app())
    res = client.get("/api/gallery", headers={"X-Telegram-Init-Data": make_init_data()})
    assert res.json() == []


def test_delete_endpoint_removes_the_render():
    u = _user()
    _media("b1")
    _media("a1-after")
    _save(u["id"])
    row_id = gallery.list_for_user(u["id"])[0]["id"]
    client = TestClient(create_app())

    res = client.delete(
        f"/api/gallery/{row_id}", headers={"X-Telegram-Init-Data": make_init_data()}
    )
    assert res.status_code == 200
    assert gallery.list_for_user(u["id"]) == []


def test_delete_of_an_unknown_id_is_404():
    _user()
    client = TestClient(create_app())
    res = client.delete(
        "/api/gallery/999999", headers={"X-Telegram-Init-Data": make_init_data()}
    )
    assert res.status_code == 404


def test_delete_requires_a_telegram_user():
    client = TestClient(create_app())
    assert client.delete("/api/gallery/1").status_code == 401


# ── media sweep exemption ─────────────────────────────────────


def test_saved_render_media_survives_the_sweep():
    import os
    import time

    u = _user()
    media = get_settings().media_path
    old = time.time() - 999 * 86400

    for name in ("keep-src", "keep-gen-after", "keep-gen-after-card", "drop-after"):
        p = media / f"{name}.jpg"
        p.write_bytes(b"x")
        os.utime(p, (old, old))

    _save(u["id"], before_photo_id="keep-src", after_photo_id="keep-gen-after")

    removed = cleanup.sweep_media()

    assert (media / "keep-src.jpg").exists(), "the before photo is protected"
    assert (media / "keep-gen-after.jpg").exists(), "the after photo is protected"
    assert (media / "keep-gen-after-card.jpg").exists(), "a derived share card is protected"
    assert not (media / "drop-after.jpg").exists(), "an unsaved stale render is reclaimed"
    assert removed == 1
