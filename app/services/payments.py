"""The payment seam.

One boundary for how an order gets paid, so the booking flow never branches on a
provider. Two online rails are planned — Telegram Payments (card) and Uzum Nasiya
(installments) — each behind its own credential. Until a credential is set, the
method is *available to choose* but routed to the manager, who arranges payment
as the shop does today. When a credential appears, that rail goes live with no
change above this file.

Phase 1 (here): method selection + the manager fallback. Phase 2: `_telegram_invoice`
and `_uzum_installment` create real charges; both are unreachable until configured.

An `initiate` result is one of:
  {"kind": "manager"}                       — the manager will handle payment
  {"kind": "invoice",  "url": "..."}        — open a Telegram invoice
  {"kind": "redirect", "url": "..."}        — send the customer to Uzum
"""

from app.config import get_settings

MANAGER = {"kind": "manager"}


def is_online(method: str) -> bool:
    """Whether `method` can charge online right now (a provider is configured)."""
    s = get_settings()
    if method == "telegram":
        return bool(s.telegram_payment_provider_token)
    if method == "uzum":
        return bool(s.uzum_merchant_id and s.uzum_api_key)
    return False  # cash is always offline


def initiate(order: dict, method: str) -> dict:
    """Start payment for an order. Returns an action for the client to take, or
    the manager fallback when the method has no configured provider."""
    if not is_online(method):
        return dict(MANAGER)
    if method == "telegram":
        return _telegram_invoice(order)
    return _uzum_installment(order)


# ── Phase 2: real rails (unreachable until a provider is configured) ──────────

def _telegram_invoice(order: dict) -> dict:  # pragma: no cover - Phase 2
    """Create a Telegram Payments invoice link for `order` and return
    {"kind": "invoice", "url": link}. Needs telegram_payment_provider_token and
    a bot-update webhook handling pre_checkout_query / successful_payment."""
    raise NotImplementedError(
        "Telegram Payments is not wired yet — set TELEGRAM_PAYMENT_PROVIDER_TOKEN "
        "and implement the invoice + webhook (Phase 2)."
    )


def _uzum_installment(order: dict) -> dict:  # pragma: no cover - Phase 2
    """Create a Uzum Nasiya installment for `order` and return
    {"kind": "redirect", "url": checkout}. Needs a Uzum merchant account and the
    check/create/confirm/reverse/status callback endpoints."""
    raise NotImplementedError(
        "Uzum installments are not wired yet — set UZUM_MERCHANT_ID / UZUM_API_KEY "
        "and implement the Merchant API (Phase 2)."
    )
