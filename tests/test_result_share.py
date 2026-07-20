"""Sharing a finished render into the requester's own Telegram chat.

Reuses `make_init_data` from test_telegram.py — the same documented algorithm,
so these tests exercise real signature verification rather than a bypass.
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.models.generation import JobState, JobStatus
from app.server import create_app
from app.services import generation_service, photos, share_card
from app.services import telegram as tg_service

from tests.test_telegram import TOKEN, make_init_data

CAPTION_PRODUCT = "AMG Carbon LED"


@pytest.fixture
def settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "telegram_bot_token", TOKEN)
    # Deliberately off: sharing must demand a signed caller regardless, because
    # the user id is the destination, not just an audit field.
    monkeypatch.setattr(s, "telegram_require_init_data", False)
    return s


@pytest.fixture
def client(settings):
    return TestClient(create_app())


@pytest.fixture
def done_job():
    """A finished job pointing at a real file on disk."""
    demo = photos.ensure_demo_photo()
    state = JobState(
        job_id="job-1",
        status=JobStatus.done,
        after_url=f"/media/{demo['photo_id']}.jpg",
        after_photo_id=demo["photo_id"],
    )
    generation_service._jobs[state.job_id] = state
    yield state
    generation_service._jobs.pop(state.job_id, None)


def _capture_send(monkeypatch) -> dict:
    sent = {}

    async def fake_send(user_id, image_bytes, filename, caption=""):
        sent.update(
            user_id=user_id, image_bytes=image_bytes, filename=filename, caption=caption
        )

    monkeypatch.setattr("app.routers.generation.send_photo_to_user", fake_send)
    return sent


def _share(client, job_id="job-1", headers=None, **body):
    return client.post(
        "/api/generation/share",
        json={"job_id": job_id, "product_id": "amg", **body},
        headers=headers if headers is not None else {"X-Telegram-Init-Data": make_init_data()},
    )


# ── authentication ────────────────────────────────────────────


def test_sharing_requires_init_data_even_in_development(client, done_job):
    """Unlike /api/booking, this endpoint has no meaningful anonymous mode:
    without a verified user id there is no chat to send to."""
    assert get_settings().telegram_require_init_data is False
    res = _share(client, headers={})
    assert res.status_code == 401


def test_sharing_rejects_a_forged_signature(client, done_job):
    res = _share(client, headers={"X-Telegram-Init-Data": make_init_data(token="9:NOPE")})
    assert res.status_code == 401


# ── addressing the photo ──────────────────────────────────────


def test_unknown_job_is_not_found(client, monkeypatch):
    _capture_send(monkeypatch)
    assert _share(client, job_id="nope").status_code == 404


def test_unfinished_job_is_not_found(client, monkeypatch):
    """A running job has no image yet — sharing it would send whatever the
    after_photo_id happens to be, i.e. nothing."""
    _capture_send(monkeypatch)
    generation_service._jobs["running"] = JobState(
        job_id="running", status=JobStatus.running
    )
    try:
        assert _share(client, job_id="running").status_code == 404
    finally:
        generation_service._jobs.pop("running", None)


def test_client_cannot_name_the_file_it_receives(client, done_job, monkeypatch):
    """The request body carries job_id only. If a path or photo_id were accepted
    here, any caller could have the bot mail them another customer's upload."""
    sent = _capture_send(monkeypatch)

    res = client.post(
        "/api/generation/share",
        json={
            "job_id": "job-1",
            "product_id": "amg",
            # All ignored — not part of the schema.
            "photo_id": "demo-interior",
            "after_photo_id": "../../secrets",
            "url": "/media/anything.jpg",
        },
        headers={"X-Telegram-Init-Data": make_init_data()},
    )

    assert res.status_code == 200
    # The filename still derives from the job's own photo id — the extra fields
    # above were ignored, not honoured.
    assert sent["filename"].startswith(done_job.after_photo_id)


# ── delivery ──────────────────────────────────────────────────


def test_share_sends_a_card_built_from_this_job(client, done_job, monkeypatch):
    """What goes out is the share card, not the bare render: a forwarded
    screenshot has to carry the car, the part and the price with it."""
    sent = _capture_send(monkeypatch)

    res = _share(client, car_label="Chevrolet Malibu 2023")
    assert res.status_code == 200
    assert res.json()["status"] == "sent"

    source = Image.open(io.BytesIO(photos.load_bytes(done_job.after_photo_id)[0]))
    card = Image.open(io.BytesIO(sent["image_bytes"]))

    assert card.width == share_card.WIDTH
    scaled = round(share_card.WIDTH * source.height / source.width)
    assert card.height > scaled, "the card adds a details panel below the render"

    assert sent["user_id"] == 4242              # from make_init_data's USER
    assert CAPTION_PRODUCT in sent["caption"]
    assert "Chevrolet Malibu 2023" in sent["caption"]


def test_denied_write_access_is_a_403_the_user_can_act_on(client, done_job, monkeypatch):
    async def denied(**kwargs):
        raise tg_service.WriteAccessDenied("nope")

    monkeypatch.setattr("app.routers.generation.send_photo_to_user", denied)

    res = _share(client)
    assert res.status_code == 403
    assert "Разрешите" in res.json()["detail"]


def test_transport_failure_is_a_502_not_a_500(client, done_job, monkeypatch):
    async def boom(**kwargs):
        raise tg_service.PhotoSendError("network")

    monkeypatch.setattr("app.routers.generation.send_photo_to_user", boom)

    res = _share(client)
    assert res.status_code == 502


# ── the transport itself ──────────────────────────────────────


@pytest.mark.asyncio
async def test_send_photo_posts_multipart_not_a_url(settings):
    """Telegram fetches a `photo` URL from its own servers, which cannot reach
    127.0.0.1 — the bytes have to be uploaded."""
    seen = {}

    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, files=None):
            seen.update(url=url, data=data, files=files)
            return FakeResponse()

    import pytest as _pytest  # noqa: F401 - keep monkeypatch out of this scope

    original = tg_service.httpx.AsyncClient
    tg_service.httpx.AsyncClient = FakeClient
    try:
        await tg_service.send_photo_to_user(7, b"JPEGBYTES", "x.jpg", "подпись")
    finally:
        tg_service.httpx.AsyncClient = original

    assert seen["url"] == f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    assert seen["data"]["chat_id"] == "7"
    assert seen["data"]["caption"] == "подпись"
    assert seen["files"]["photo"][1] == b"JPEGBYTES"


@pytest.mark.asyncio
async def test_send_photo_maps_403_to_write_access_denied(settings):
    class Forbidden:
        status_code = 403
        text = "Forbidden: bot can't initiate conversation with a user"

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, files=None):
            return Forbidden()

    original = tg_service.httpx.AsyncClient
    tg_service.httpx.AsyncClient = FakeClient
    try:
        with pytest.raises(tg_service.WriteAccessDenied):
            await tg_service.send_photo_to_user(7, b"x", "x.jpg")
    finally:
        tg_service.httpx.AsyncClient = original
