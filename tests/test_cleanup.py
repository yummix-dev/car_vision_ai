"""Reclamation and the generation limit — the two things standing between this
app and unbounded disk, memory and spend."""

import os
import time

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.models.generation import JobState, JobStatus
from app.server import create_app
from app.services import cleanup, generation_service, photos, rate_limit


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_dir", str(tmp_path))
    photos.ensure_demo_photo()
    return get_settings().media_path


def _age(path, days):
    old = time.time() - days * 86400
    os.utime(path, (old, old))


# ── media ─────────────────────────────────────────────────────


def test_sweep_deletes_stale_images(media):
    stale = media / "stale-after.jpg"
    stale.write_bytes(b"x")
    _age(stale, 30)

    assert cleanup.sweep_media() == 1
    assert not stale.exists()


def test_sweep_keeps_recent_images(media):
    fresh = media / "fresh-after.jpg"
    fresh.write_bytes(b"x")

    assert cleanup.sweep_media() == 0
    assert fresh.exists()


def test_sweep_never_deletes_the_demo_photo(media):
    """The demo photo is only seeded at startup. Deleting it from under a
    running app dead-ends the zero-input funnel until the next restart."""
    demo = next(media.glob(f"{photos.DEMO_PHOTO_ID}.*"))
    _age(demo, 999)

    cleanup.sweep_media()
    assert demo.exists()


def test_sweep_survives_a_vanishing_file(media, monkeypatch):
    doomed = media / "gone-after.jpg"
    doomed.write_bytes(b"x")
    _age(doomed, 30)

    original = type(doomed).unlink

    def racy(self, *a, **kw):
        original(self, *a, **kw)
        original(self, *a, **kw)  # second call raises FileNotFoundError

    monkeypatch.setattr(type(doomed), "unlink", racy)
    cleanup.sweep_media()  # must not propagate


# ── jobs ──────────────────────────────────────────────────────


def test_sweep_evicts_finished_jobs_only():
    generation_service._jobs.clear()
    generation_service._finished_at.clear()

    generation_service._jobs["done"] = JobState(job_id="done", status=JobStatus.done)
    generation_service._finished_at["done"] = time.monotonic() - 7200
    generation_service._jobs["recent"] = JobState(job_id="recent", status=JobStatus.done)
    generation_service._finished_at["recent"] = time.monotonic()
    generation_service._jobs["running"] = JobState(
        job_id="running", status=JobStatus.running
    )

    assert cleanup.sweep_jobs() == 1
    assert generation_service.get_job("done") is None
    assert generation_service.get_job("recent") is not None
    # A running job has no finish time and must never be collected mid-flight.
    assert generation_service.get_job("running") is not None


# ── the generation limit ──────────────────────────────────────


def test_generation_is_capped_per_session(monkeypatch):
    monkeypatch.setattr(get_settings(), "generation_limit_per_hour", 3)
    rate_limit.reset()
    client = TestClient(create_app())

    demo = photos.ensure_demo_photo()
    body = {"photo_id": demo["photo_id"], "product_id": "amg", "selections": []}
    headers = {"X-Session-Id": "burner"}

    for _ in range(3):
        assert client.post("/api/generation", json=body, headers=headers).status_code == 200

    res = client.post("/api/generation", json=body, headers=headers)
    assert res.status_code == 429
    assert "Слишком много" in res.json()["detail"]


def test_the_limit_is_per_caller(monkeypatch):
    monkeypatch.setattr(get_settings(), "generation_limit_per_hour", 1)
    rate_limit.reset()
    client = TestClient(create_app())

    demo = photos.ensure_demo_photo()
    body = {"photo_id": demo["photo_id"], "product_id": "amg", "selections": []}

    assert client.post("/api/generation", json=body,
                       headers={"X-Session-Id": "a"}).status_code == 200
    # One caller exhausting quota must not lock out everyone else.
    assert client.post("/api/generation", json=body,
                       headers={"X-Session-Id": "b"}).status_code == 200
    assert client.post("/api/generation", json=body,
                       headers={"X-Session-Id": "a"}).status_code == 429


def test_being_over_quota_does_not_extend_the_window():
    rate_limit.reset()
    assert rate_limit.check("k", limit=1) is True
    assert rate_limit.check("k", limit=1) is False
    # The rejected call was not recorded, so raising the limit frees it at once.
    assert rate_limit.check("k", limit=2) is True
