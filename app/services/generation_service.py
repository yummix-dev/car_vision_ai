"""Async generation jobs.

Real inpainting takes seconds to tens of seconds, so generation is a job the
client polls rather than a synchronous call. The mock honours the same contract,
which means the 5-step checklist on the `generating` screen is driven by real
polling — and the error path is a real `status: "error"`, not UI theatre.

Jobs are held in memory: they are short-lived and tied to one session. If this
ever needs to survive a restart, swap this dict for a store.
"""

import asyncio
import logging
import math
import time
import uuid

from app.models.generation import (
    GenerationJob,
    GenerationRequest,
    JobState,
    JobStatus,
)
from app.config import get_settings
from app.db import connect
from app.services import gallery, notifications, photos, quota, referrals
from app.services.ai import get_image_generator
from app.services.catalog_service import get_catalog

log = logging.getLogger(__name__)

# The bar never claims 100 until the file is real — it eases toward this ceiling.
CEILING = 97
# Minimum fill time, so even the near-instant mock shows a few seconds of motion.
MIN_DURATION_SECONDS = 3.0
_TICK = 0.06


def _expected_seconds() -> float:
    """Roughly how long the running provider takes, for pacing the bar.

    The mock finishes almost instantly; the real provider takes tens of seconds.
    Pacing to the wrong one is the whole bug — the old code raced to 95% in four
    seconds and then sat frozen for the 20–40s gpt-image-2 actually needs.
    """
    settings = get_settings()
    if settings.imagegen_provider.lower() == "provider":
        return max(2.0, settings.generation_expected_seconds)
    return 3.0


def _eased_progress(elapsed: float, expected: float) -> int:
    """Approach CEILING asymptotically over `expected` seconds, never reaching it.

    Because it only approaches the ceiling, the bar keeps inching up even when a
    generation runs longer than expected — it reads as "still working", never as
    "frozen". `tau` is picked so progress is ~85% at the expected duration.
    """
    tau = expected / 1.9
    return min(CEILING, int(CEILING * (1 - math.exp(-elapsed / tau))))

_jobs: dict[str, JobState] = {}
# When each job reached a terminal state, on the monotonic clock. Kept beside
# JobState rather than on it: JobState is serialised straight to the client and
# an internal bookkeeping field would leak into the API.
_finished_at: dict[str, float] = {}
# Strong references to in-flight tasks: asyncio only holds weak ones, so without
# this a running job can be garbage-collected mid-generation.
_tasks: set[asyncio.Task] = set()


def get_job(job_id: str) -> JobState | None:
    return _jobs.get(job_id)


def finished_at(job_id: str) -> float | None:
    """Monotonic time the job settled, or None while it is still running."""
    return _finished_at.get(job_id)


def forget(job_id: str) -> None:
    _jobs.pop(job_id, None)
    _finished_at.pop(job_id, None)


async def create_job(req: GenerationRequest) -> JobState:
    """Async so the background task is scheduled on the running event loop —
    a sync route would execute in a threadpool where there is no loop."""
    catalog = get_catalog()
    found = catalog.find_product(req.product_id)
    if found is None:
        raise ValueError(f"Unknown product: {req.product_id}")
    category, _product = found

    job_id = uuid.uuid4().hex
    state = JobState(
        job_id=job_id,
        status=JobStatus.pending,
        steps=category.gen_steps,
        sub=(
            f"Мы изменим только {category.acc}. "
            "Остальные элементы постараемся сохранить без изменений."
        ),
    )
    _jobs[job_id] = state

    job = GenerationJob(
        job_id=job_id,
        source_photo_id=req.photo_id,
        product_id=req.product_id,
        category_id=category.id,
        region_label=category.acc,
        selections=req.selections,
    )
    task = asyncio.create_task(_run(job, state))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return state


async def _run(job: GenerationJob, state: JobState) -> None:
    state.status = JobStatus.running
    generator = get_image_generator()
    work = asyncio.create_task(generator.generate(job))

    elapsed = 0.0
    expected = _expected_seconds()
    # Ease toward the ceiling over the expected duration, and keep going until
    # the work is actually done. A fast provider still paces the checklist for
    # the user; a slow one keeps the bar creeping instead of stalling.
    while not work.done() or elapsed < MIN_DURATION_SECONDS:
        await asyncio.sleep(_TICK)
        elapsed += _TICK
        state.progress = _eased_progress(elapsed, expected)
        state.step_index = min(len(state.steps) - 1, state.progress * len(state.steps) // 100)

    try:
        result = await work
    except Exception as exc:  # noqa: BLE001 - any provider failure is a job failure
        state.status = JobStatus.error
        state.error = str(exc) or "Не удалось точно распознать фото"
        _finished_at[state.job_id] = time.monotonic()
        quota.release(state.job_id, "generation_failed")
        return

    # A provider can report success and still leave nothing usable behind. The
    # try is only spent for a render the customer can actually see, so the file
    # is verified before the reservation is committed.
    if not _output_is_usable(result.after_photo_id):
        state.status = JobStatus.error
        state.error = "Не удалось сохранить результат. Попробуйте ещё раз."
        _finished_at[state.job_id] = time.monotonic()
        quota.release(state.job_id, "result_unusable")
        return

    state.progress = 100
    state.step_index = len(state.steps) - 1
    state.before_url = result.before_url
    state.after_url = result.after_url
    state.after_photo_id = result.after_photo_id
    state.status = JobStatus.done
    _finished_at[state.job_id] = time.monotonic()
    quota.commit(state.job_id)
    _settle_referral(state.job_id, job.source_photo_id)
    _save_to_gallery(job, state)


def _save_to_gallery(job: GenerationJob, state: JobState) -> None:
    """Record the render in the owner's "Мои примерки".

    Only metered Telegram users have a gallery; the job's owner is the user
    behind its quota reservation, so a browser generation (no reservation) is
    simply not saved. Best-effort: a save that fails must not fail the render the
    customer already has.
    """
    reservation = quota.reservation_for(job.job_id)
    if reservation is None or not state.after_photo_id:
        return
    try:
        gallery.save(
            user_id=reservation["user_id"],
            job_id=job.job_id,
            product_id=job.product_id,
            category_id=job.category_id,
            before_photo_id=job.source_photo_id,
            after_photo_id=state.after_photo_id,
            car_label=_car_label(reservation["user_id"]),
        )
    except Exception:  # noqa: BLE001 - a saved render must not fail a render
        log.exception("gallery save failed for job %s", job.job_id)


def _car_label(user_id: int) -> str | None:
    """The user's confirmed car as one label, or None if none is on file."""
    with connect() as conn:
        row = conn.execute(
            "SELECT car_brand, car_model, car_year FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
    if not row or not row["car_brand"]:
        return None
    parts = [row["car_brand"], row["car_model"], row["car_year"]]
    return " ".join(str(p) for p in parts if p)


def _settle_referral(job_id: str, source_photo_id: str) -> None:
    """A delivered image is the only thing that qualifies an invited person.

    Never allowed to break a generation: the customer has their render either
    way, and a missed bonus is recoverable while a failed job is not.
    """
    reservation = quota.reservation_for(job_id)
    if reservation is None:
        return
    try:
        reward = referrals.on_first_generation(
            reservation["user_id"], source_photo_id
        )
    except Exception:  # noqa: BLE001 - a bonus must not fail a render
        log.exception("referral settlement failed for job %s", job_id)
        return
    if reward:
        notifications.referral_rewarded(reward["inviter_id"], reward["amount"])


def _output_is_usable(photo_id: str | None) -> bool:
    if not photo_id:
        return False
    try:
        raw, _ = photos.load_bytes(photo_id)
    except photos.PhotoError:
        return False
    return len(raw) > 0
