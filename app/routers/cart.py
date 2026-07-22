import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from app.i18n import lang_of, t
from app.models.cart import BookingRequest, BookingResponse
from app.models.telegram import TelegramUser
from app.money import fmt
from app.routers.deps import telegram_user
from app.services import analytics
from app.services.pricing_service import PricingError, quote
from app.services.telegram import (
    ManagerNotifyError,
    delivery_configured,
    notify_manager,
    render_booking_message,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["booking"])

# There is deliberately no booking store. The manager's Telegram chat is the
# system of record; a dict here was written and never read by anything but its
# own tests, and putting it in a database would only have made that durable.
# Analytics gets the fact and the amount — never the name or the phone, which
# stay in the one place that needs them.


@router.post("/booking")
async def create_booking(
    req: BookingRequest,
    user: TelegramUser | None = Depends(telegram_user),
    x_session_id: str | None = Header(default=None),
    x_lang: str | None = Header(default=None),
) -> BookingResponse:
    """The booking event is recorded here rather than by the client: the server
    knows a booking happened for certain, while a client can navigate away
    before its event queue flushes."""
    lang = lang_of(x_lang)
    if not req.cart:
        raise HTTPException(status_code=400, detail=t("err.cart_empty", lang))
    if not req.contact.phone.strip():
        raise HTTPException(status_code=400, detail=t("err.need_phone", lang))

    # Totals are recomputed here, never trusted from the client.
    total = 0
    lines: list[str] = []
    try:
        for item in req.cart:
            breakdown = quote(item.product_id, item.selections, item.service_ids)
            total += breakdown.total
            # Everything after the base-price line — options and services alike.
            options = ", ".join(line.label for line in breakdown.lines[1:])
            lines.append(
                f"{breakdown.product_name}"
                f"{f' ({options})' if options else ''}"
                f" — {breakdown.total_formatted} сум"
            )
    except PricingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    booking_id = uuid.uuid4().hex[:10]

    # Deliver before confirming: a booking the shop never received must not come
    # back as "заявка отправлена". On an unconfigured dev box there is nowhere to
    # deliver to, and the funnel stays walkable — the warning is the signal.
    if delivery_configured():
        try:
            await notify_manager(
                render_booking_message(
                    booking_id=booking_id,
                    car_label=req.car_label,
                    lines=lines,
                    total_formatted=fmt(total),
                    contact=req.contact.model_dump(),
                    user=user,
                )
            )
        except ManagerNotifyError as exc:
            raise HTTPException(
                status_code=502,
                detail=t("err.booking_failed", lang),
            ) from exc
    else:
        log.warning(
            "Booking %s not delivered: TELEGRAM_BOT_TOKEN/"
            "TELEGRAM_MANAGER_CHAT_ID are unset",
            booking_id,
        )

    analytics.record_server_event(
        "booking_submitted",
        session_id=x_session_id or "server",
        payload={"total": total, "positions": len(req.cart)},
    )

    return BookingResponse(
        booking_id=booking_id,
        status="received",
        positions=len(req.cart),
        total=total,
        total_formatted=fmt(total),
        car_label=req.car_label,
    )
