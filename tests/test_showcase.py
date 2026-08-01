"""Реальные сборки — the shop's public feed of real installs.

Covers the store, the public endpoint (image URLs + localized category label,
active-only), the admin upload/delete flow, and the media-sweep exemption.
"""

import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.server import create_app
from app.services import cleanup, photos, showcase


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(s, "media_dir", str(tmp_path / "media"))
    reset_for_tests()
    yield


def _media(pid: str) -> str:
    Image.new("RGB", (4, 4), "#246").save(get_settings().media_path / f"{pid}.jpg", "JPEG")
    return pid


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "#357").save(buf, "JPEG")
    return buf.getvalue()


def _auth(password: str) -> dict:
    token = base64.b64encode(f"admin:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _build(**over) -> dict:
    args = dict(
        car_brand="Chevrolet", car_model="Malibu", car_year=2023,
        category_id="rul", title="Руль Mercedes-AMG",
        before_photo_id="b1", after_photo_id="a1",
    )
    args.update(over)
    return showcase.create(**args)


# ── the store ─────────────────────────────────────────────────


def test_create_then_list_public():
    _build()
    items = showcase.list_public()
    assert len(items) == 1
    assert items[0]["car_model"] == "Malibu"
    assert items[0]["title"] == "Руль Mercedes-AMG"


def test_requires_brand_model_and_title():
    with pytest.raises(showcase.ShowcaseError):
        _build(title="   ")
    with pytest.raises(showcase.ShowcaseError):
        _build(car_model="")


def test_list_public_is_sort_desc_then_id_desc():
    first = _build(title="A")
    second = _build(title="B")
    ids = [b["id"] for b in showcase.list_public()]
    assert ids == [second["id"], first["id"]]


def test_deactivate_hides_from_public_but_not_admin():
    b = _build()
    showcase.deactivate(b["id"])
    assert showcase.list_public() == []
    assert len(showcase.all_admin()) == 1


def test_delete_removes_the_build():
    b = _build()
    showcase.delete(b["id"])
    assert showcase.all_admin() == []


def test_protected_photo_ids_covers_active_and_inactive():
    a = _build(before_photo_id="src-1", after_photo_id="gen-1")
    showcase.deactivate(a["id"])  # still protected while the row exists
    assert showcase.protected_photo_ids() == {"src-1", "gen-1"}


# ── the public endpoint ───────────────────────────────────────


def test_showcase_endpoint_is_empty_by_default():
    res = TestClient(create_app()).get("/api/showcase")
    assert res.status_code == 200
    assert res.json() == []


def test_showcase_endpoint_serves_urls_and_localized_category():
    _media("b1")
    _media("a1")
    _build()
    client = TestClient(create_app())

    ru = client.get("/api/showcase").json()
    assert len(ru) == 1
    assert ru[0]["car_label"] == "Chevrolet Malibu 2023"
    assert ru[0]["category_label"] == "Руль"
    assert ru[0]["before_url"].endswith("b1.jpg")
    assert ru[0]["after_url"].endswith("a1.jpg")

    uz = client.get("/api/showcase", headers={"X-Lang": "uz"}).json()
    assert uz[0]["category_label"] == "Rul"


def test_showcase_endpoint_hides_inactive_builds():
    _media("b1")
    _media("a1")
    b = _build()
    showcase.deactivate(b["id"])
    assert TestClient(create_app()).get("/api/showcase").json() == []


# ── the admin upload flow ─────────────────────────────────────


def test_admin_can_upload_a_build_and_it_reaches_the_feed(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    client = TestClient(create_app())

    res = client.post(
        "/admin/showcase",
        data={"car_brand": "Chevrolet", "car_model": "Cobalt", "car_year": "2022",
              "category_id": "audio", "title": "Магнитола Teyes"},
        files={"before": ("b.jpg", _jpeg_bytes(), "image/jpeg"),
               "after": ("a.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=_auth("secret"),
        follow_redirects=False,
    )
    assert res.status_code == 303

    feed = client.get("/api/showcase").json()
    assert len(feed) == 1
    assert feed[0]["title"] == "Магнитола Teyes"
    assert feed[0]["car_label"] == "Chevrolet Cobalt 2022"
    # The uploaded images are real, resolvable files.
    assert feed[0]["before_url"].startswith("/media/")


def test_admin_delete_removes_a_build(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    _media("b1")
    _media("a1")
    b = _build()
    client = TestClient(create_app())

    res = client.post(
        f"/admin/showcase/{b['id']}/delete",
        headers=_auth("secret"),
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert showcase.all_admin() == []


def test_admin_showcase_requires_the_password(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    client = TestClient(create_app())
    res = client.post("/admin/showcase/1/delete", headers=_auth("wrong"))
    assert res.status_code == 401


# ── media sweep exemption ─────────────────────────────────────


def test_showcase_media_survives_the_sweep():
    import os
    import time

    media = get_settings().media_path
    old = time.time() - 999 * 86400
    for name in ("keep-b", "keep-a", "drop-x"):
        p = media / f"{name}.jpg"
        p.write_bytes(b"x")
        os.utime(p, (old, old))

    _build(before_photo_id="keep-b", after_photo_id="keep-a")

    removed = cleanup.sweep_media()

    assert (media / "keep-b.jpg").exists()
    assert (media / "keep-a.jpg").exists()
    assert not (media / "drop-x.jpg").exists()
    assert removed == 1
