"""Photo rotation — the last dead button on the upload screen."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.telegram import TelegramUser
from app.server import create_app
from app.services import photos, users

from tests.test_telegram import make_init_data


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "media_dir", str(tmp_path / "media"))
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    reset_for_tests()
    yield


def _upload(width=120, height=60, colour="#804020") -> str:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buf, "JPEG")
    return photos.save_upload(buf.getvalue(), "image/jpeg")["photo_id"]


def test_rotation_swaps_the_sides():
    """expand=True, or a portrait photo gets cropped into a landscape box."""
    photo_id = _upload(120, 60)
    rotated = photos.rotate(photo_id)

    assert (rotated["width"], rotated["height"]) == (60, 120)
    raw, _ = photos.load_bytes(rotated["photo_id"])
    assert Image.open(io.BytesIO(raw)).size == (60, 120)


def test_rotation_leaves_the_original_alone():
    """A new id, not an overwrite: the same URL with different bytes is how a
    customer ends up staring at a cached stale image."""
    photo_id = _upload(120, 60)
    rotated = photos.rotate(photo_id)

    assert rotated["photo_id"] != photo_id
    raw, _ = photos.load_bytes(photo_id)
    assert Image.open(io.BytesIO(raw)).size == (120, 60)


def test_four_rotations_return_to_the_start():
    photo_id = _upload(120, 60)
    for _ in range(4):
        photo_id = photos.rotate(photo_id)["photo_id"]

    raw, _ = photos.load_bytes(photo_id)
    assert Image.open(io.BytesIO(raw)).size == (120, 60)


def test_rotating_an_unknown_photo_raises():
    with pytest.raises(photos.PhotoError):
        photos.rotate("no-such-photo")


# ── the endpoint ──────────────────────────────────────────────


def test_the_endpoint_returns_the_new_photo():
    client = TestClient(create_app())
    photo_id = _upload(120, 60)

    res = client.post("/api/photos/rotate", json={"photo_id": photo_id})
    assert res.status_code == 200
    body = res.json()
    assert body["photo_id"] != photo_id
    assert body["url"].startswith("/media/")
    assert (body["width"], body["height"]) == (60, 120)


def test_unknown_photo_is_a_404():
    client = TestClient(create_app())
    res = client.post("/api/photos/rotate", json={"photo_id": "nope"})
    assert res.status_code == 404


def test_rotation_carries_the_fingerprint_forward(monkeypatch):
    """Rotating changes every byte, so a fresh hash would make one photograph
    look like two — exactly the move somebody farming referrals would try."""
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123456:TEST-TOKEN")
    client = TestClient(create_app())
    user = users.get_or_create(TelegramUser(id=8001, first_name="U"))
    auth = {"X-Telegram-Init-Data": make_init_data(user={"id": 8001, "first_name": "U"})}

    buf = io.BytesIO()
    Image.new("RGB", (120, 60), "#123456").save(buf, "JPEG")
    uploaded = client.post(
        "/api/photos", files={"file": ("a.jpg", buf.getvalue(), "image/jpeg")},
        headers=auth,
    ).json()

    rotated = client.post(
        "/api/photos/rotate", json={"photo_id": uploaded["photo_id"]}, headers=auth
    ).json()

    with connect() as conn:
        rows = conn.execute(
            "SELECT photo_id, sha256 FROM photo_uploads WHERE user_id=?", (user["id"],)
        ).fetchall()
    hashes = {r["photo_id"]: r["sha256"] for r in rows}

    assert uploaded["photo_id"] in hashes
    assert rotated["photo_id"] in hashes
    assert hashes[uploaded["photo_id"]] == hashes[rotated["photo_id"]], (
        "a rotated copy must not read as a different photograph"
    )
