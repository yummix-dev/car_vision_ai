import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.models.generation import GenerationRequest, JobStatus, JobState
from app.models.telegram import TelegramUser
from app.routers.deps import current_user, require_telegram_user, telegram_user
from app.services import (
    generation_service,
    photos,
    quota,
    rate_limit,
    referrals,
    share_card,
)
from app.services.catalog_service import get_catalog
from app.services.telegram import (
    PhotoSendError,
    WriteAccessDenied,
    send_photo_to_user,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("")
async def start_generation(
    req: GenerationRequest,
    user: TelegramUser | None = Depends(telegram_user),
    account: dict | None = Depends(current_user),
    x_session_id: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
) -> JobState:
    # The hourly cap and the try-on quota are different things and both stay:
    # the quota is the product rule, this is the abuse guard that also covers
    # unmetered browser traffic.
    key = f"user:{user.id}" if user else f"session:{x_session_id or 'anonymous'}"
    if not rate_limit.check(key, get_settings().generation_limit_per_hour):
        raise HTTPException(
            status_code=429,
            detail="Слишком много генераций за час. Попробуйте позже.",
        )

    found = get_catalog().find_product(req.product_id)
    if found is None:
        raise HTTPException(status_code=400, detail=f"Unknown product: {req.product_id}")
    category = found[0]

    reservation = None
    if account is not None:
        # Without a client-supplied key, a double tap is two distinct requests
        # and would spend two tries. The client sends one per attempt.
        key = idempotency_key or f"{account['id']}:{req.photo_id}:{req.product_id}"
        try:
            reservation = quota.reserve(account["id"], category.id, key)
        except quota.QuotaExhausted as exc:
            raise HTTPException(
                status_code=409,
                detail="Примерки в этой категории закончились.",
            ) from exc

    try:
        state = await generation_service.create_job(req)
    except ValueError as exc:
        if reservation is not None:
            quota.release_by_id(reservation["id"], "job_not_created")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if reservation is not None:
        quota.attach_job(reservation["id"], state.job_id)
    return state


@router.get("/{job_id}")
def poll_generation(job_id: str) -> JobState:
    state = generation_service.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return state


class ShareRequest(BaseModel):
    job_id: str
    product_id: str = ""
    car_label: str = ""


class ShareResponse(BaseModel):
    status: str = "sent"


@router.post("/share", response_model=ShareResponse)
async def share_result(
    req: ShareRequest,
    user: TelegramUser = Depends(require_telegram_user),
    account: dict | None = Depends(current_user),
) -> ShareResponse:
    """Send the finished render into the requester's own chat with the bot.

    The photo is addressed by job_id, never by a path from the client: a
    caller-supplied filename would let anyone have the bot mail them any image
    sitting in media/, including other people's uploads.
    """
    state = generation_service.get_job(req.job_id)
    if state is None or state.status is not JobStatus.done or not state.after_photo_id:
        raise HTTPException(status_code=404, detail="Результат не найден")

    try:
        image_bytes, _ = photos.load_bytes(state.after_photo_id)
    except photos.PhotoError as exc:
        raise HTTPException(status_code=404, detail="Результат не найден") from exc

    found = get_catalog().find_product(req.product_id) if req.product_id else None
    card = _build_card(image_bytes, found, req)

    # The link rides in the caption, not in the picture: a link in pixels is
    # not tappable, and a forwarded screenshot keeps the caption anyway.
    share_url = ""
    if account is not None:
        link = referrals.create_share_link(
            account["id"],
            job_id=req.job_id,
            result_photo_id=state.after_photo_id,
            product_id=req.product_id,
            category_id=found[0].id if found else None,
            car_label=req.car_label,
            channel="telegram",
        )
        share_url = referrals.link_for(account["ref_code"], link["public_code"])

    try:
        await send_photo_to_user(
            user_id=user.id,
            image_bytes=card,
            filename=f"{state.after_photo_id}-card.jpg",
            caption=_caption(req, share_url),
        )
    except WriteAccessDenied as exc:
        raise HTTPException(
            status_code=403,
            detail="Разрешите боту писать вам, чтобы получить изображение.",
        ) from exc
    except PhotoSendError as exc:
        raise HTTPException(
            status_code=502, detail="Не удалось отправить изображение."
        ) from exc

    return ShareResponse()


def _build_card(image_bytes: bytes, found, req: ShareRequest) -> bytes:
    """A card that fails to compose must not cost the customer their share —
    fall back to the bare render."""
    try:
        return share_card.build(
            image_bytes,
            product_name=found[1].name if found else "AI-визуализация",
            car_label=req.car_label,
            category_label=found[0].label if found else "",
            price=found[1].base_price if found else None,
        )
    except Exception:  # noqa: BLE001
        log.exception("share card composition failed")
        return image_bytes


def _caption(req: ShareRequest, share_url: str = "") -> str:
    found = get_catalog().find_product(req.product_id) if req.product_id else None
    product = found[1].name if found else "Визуализация"
    car = f" · {req.car_label}" if req.car_label else ""
    lines = [f"{product}{car}"]
    if share_url:
        lines += [
            "",
            "Попробуй собрать свою машину:",
            share_url,
        ]
    return "\n".join(lines)
