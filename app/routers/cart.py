import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from app.i18n import lang_of, t
from app.models.cart import BookingRequest, BookingResponse, PaymentAction
from app.models.telegram import TelegramUser
from app.money import fmt
from app.routers.deps import telegram_user
from app.services import analytics, orders, payments
from app.services.pricing_service import PricingError, quote
from app.services.telegram import (
    ManagerNotifyError,
    delivery_configured,
    notify_manager,
    render_booking_message,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["booking"])

# The order is now persisted (payments need something to reconcile against — see
# migration 009), but only the transaction: the name and phone still live only in
# the manager's chat, never in the database or analytics.

# The manager's copy of the chosen payment method, in Russian (the manager reads
# Russian). The customer picks it in their own language on the client.
_PAYMENT_LABELS = {
    "cash": "Наличными при установке",
    "telegram": "Картой в Telegram",
    "uzum": "Рассрочка Uzum",
}


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
    method = req.payment_method

    # Persist the order before charging: an online method (Phase 2) starts as
    # "pending" and is confirmed by a webhook; an offline/manager method is
    # "manual" — the manager arranges payment, exactly as the shop does today.
    order = orders.create(
        order_code=booking_id,
        telegram_id=user.id if user else None,
        car_label=req.car_label,
        positions=len(req.cart),
        total=total,
        payment_method=method,
        payment_status="pending" if payments.is_online(method) else "manual",
    )
    action = payments.initiate(order, method)

    # The manager is notified now for anything they handle (cash, or an online
    # method with no provider configured yet). A live online payment instead
    # notifies after the webhook confirms it, so nobody chases an unpaid order.
    if action["kind"] == "manager":
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
                        payment_label=_PAYMENT_LABELS.get(method, method),
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
        payload={"total": total, "positions": len(req.cart), "payment_method": method},
    )

    return BookingResponse(
        booking_id=booking_id,
        status="received",
        positions=len(req.cart),
        total=total,
        total_formatted=fmt(total),
        car_label=req.car_label,
        payment_method=method,
        payment=PaymentAction(**action),
    )
