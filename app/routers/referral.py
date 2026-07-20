"""Referral link, attribution and share links.

Nothing here accepts a bonus amount, a code to credit, or a user to credit it
to. The client reports only what it observed — the startapp payload it was
opened with — and every consequence is decided on the server.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.models.generation import JobStatus
from app.routers.deps import current_user, require_telegram_user
from app.services import generation_service, referrals, users

router = APIRouter(prefix="/api", tags=["referral"])


class AttributeRequest(BaseModel):
    start_param: str
    channel: str | None = None


class ShareLinkRequest(BaseModel):
    job_id: str
    channel: str | None = None


def _client_ip(request: Request) -> str | None:
    # Behind the tunnel the socket address is the proxy, so the forwarded
    # header is what carries the visitor. Both are weak signals, scored rather
    # than trusted.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/referral")
def read_referral(user: dict | None = Depends(current_user)) -> dict:
    if user is None:
        # A browser visitor has no durable identity, so no link to own.
        return {"available": False}
    return {"available": True, **referrals.stats(user)}


@router.post("/referral/attribute")
def attribute(
    req: AttributeRequest,
    request: Request,
    user: dict | None = Depends(current_user),
) -> dict:
    """Record who invited this user. Refusals are normal, not errors."""
    if user is None:
        return {"attributed": False, "reason": "no_identity"}
    try:
        referrals.attribute(user, req.start_param, ip=_client_ip(request))
    except referrals.AttributionRefused as exc:
        return {"attributed": False, "reason": str(exc)}
    return {"attributed": True}


@router.get("/referral/invited-by")
def invited_by(user: dict | None = Depends(current_user)) -> dict:
    """Whether this user owes somebody a first try-on.

    Returns no identifying detail about the inviter — §8 forbids showing their
    personal data without consent, and the invited person does not need it.
    """
    if user is None:
        return {"pending": False}
    return {"pending": referrals.pending_for(user["id"]) is not None}


@router.post("/share-links")
def create_share_link(
    req: ShareLinkRequest,
    telegram=Depends(require_telegram_user),
    user: dict | None = Depends(current_user),
) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Откройте приложение в Telegram.")

    state = generation_service.get_job(req.job_id)
    if state is None or state.status is not JobStatus.done or not state.after_photo_id:
        raise HTTPException(status_code=404, detail="Результат не найден")

    reservation = None
    from app.services import quota

    reservation = quota.reservation_for(req.job_id)
    if reservation is not None and reservation["user_id"] != user["id"]:
        # Sharing somebody else's render would attach their picture to your
        # referral code.
        raise HTTPException(status_code=403, detail="Это не ваш результат")

    link = referrals.create_share_link(
        user["id"],
        job_id=req.job_id,
        result_photo_id=state.after_photo_id,
        category_id=reservation["category_id"] if reservation else None,
        channel=req.channel,
    )
    return {
        "public_code": link["public_code"],
        "url": referrals.link_for(user["ref_code"], link["public_code"]),
    }
