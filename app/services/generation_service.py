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
import time
import uuid

from app.models.generation import (
    GenerationJob,
    GenerationRequest,
    JobState,
    JobStatus,
)
from app.services import notifications, photos, quota, referrals
from app.services.ai import get_image_generator
from app.services.catalog_service import get_catalog

log = logging.getLogger(__name__)

# Roughly matches the prototype's 4200ms animation, so the pacing feels the same
# when the mock finishes near-instantly.
MIN_DURATION_SECONDS = 4.2
_TICK = 0.06

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
    # Advance to 95% over the minimum duration; the last 5% waits on real work.
    # Both conditions must clear: a fast provider still paces the checklist for
    # the user, and a slow one keeps ticking past the minimum until it finishes.
    while not work.done() or elapsed < MIN_DURATION_SECONDS:
        await asyncio.sleep(_TICK)
        elapsed += _TICK
        state.progress = min(95, int(elapsed / MIN_DURATION_SECONDS * 95))
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
