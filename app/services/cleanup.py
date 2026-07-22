"""Periodic reclamation. Nothing in this app may grow without a bound.

Before this existed, `media/` reached 99 files in two days of testing and no
code path ever deleted one.
"""

import asyncio
import logging
import time

from app.config import get_settings
from app.services import analytics, gallery, generation_service, photos, quota

log = logging.getLogger(__name__)


def sweep_media() -> int:
    """Delete generated and uploaded images past their TTL.

    The demo photo is exempt: it is only seeded at startup, so deleting it from
    under a running app breaks the zero-input funnel until the next restart.

    Renders saved to a user's gallery ("Мои примерки") are exempt too — their
    whole point is to outlive the sweep. A file is kept while its photo id, or
    the id it derives from ("<id>-after"), belongs to a saved render.
    """
    settings = get_settings()
    cutoff = time.time() - settings.media_ttl_days * 86400
    protected = gallery.protected_photo_ids()
    removed = 0
    for path in settings.media_path.glob("*.*"):
        if path.stem == photos.DEMO_PHOTO_ID or path.stem.startswith(
            f"{photos.DEMO_PHOTO_ID}-"
        ):
            continue
        if _is_protected(path.stem, protected):
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:  # a file vanishing under us is not an error
            continue
    return removed


def _is_protected(stem: str, protected: set[str]) -> bool:
    """A file backs a saved render if its stem is a protected id, or a suffixed
    derivative of one ("<id>-after", "<id>-card")."""
    if stem in protected:
        return True
    return any(stem.startswith(f"{pid}-") for pid in protected)


def sweep_jobs() -> int:
    """Drop finished jobs. A job is only interesting while its client polls it."""
    cutoff = time.monotonic() - get_settings().job_ttl_minutes * 60
    stale = [
        job_id
        for job_id in list(generation_service._jobs)
        if (finished := generation_service.finished_at(job_id)) is not None
        and finished < cutoff
    ]
    for job_id in stale:
        generation_service.forget(job_id)
    return len(stale)


def sweep() -> dict:
    settings = get_settings()
    result = {
        "media": sweep_media(),
        "jobs": sweep_jobs(),
        "events": analytics.purge_old(settings.analytics_ttl_days)
        if settings.analytics_enabled
        else 0,
        # A crash between reserving and generating would otherwise swallow a
        # try permanently.
        "reservations": quota.expire_stale() if settings.quota_enabled else 0,
    }
    if any(result.values()):
        log.info("cleanup: %s", result)
    return result


async def run_forever() -> None:
    """Background loop started from the app lifespan."""
    interval = get_settings().cleanup_interval_minutes * 60
    while True:
        try:
            await asyncio.to_thread(sweep)
        except Exception:  # noqa: BLE001 - a failed sweep must not kill the app
            log.exception("cleanup sweep failed")
        await asyncio.sleep(interval)
