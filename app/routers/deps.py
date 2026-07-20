"""Shared FastAPI dependencies.

Two ways to resolve the Telegram caller, and the difference matters:

  * `telegram_user` — optional. A browser has no initData, and the whole funnel
    is developed there, so callers without one are allowed unless
    TELEGRAM_REQUIRE_INIT_DATA is on. Used by /api/booking.
  * `require_telegram_user` — always strict. Used where the user id *is* the
    destination (sharing a photo into someone's chat): there is nothing to fall
    back to, so a soft None would just fail later and less clearly.
"""

from fastapi import Depends, Header, HTTPException

from app.config import get_settings
from app.models.telegram import TelegramUser
from app.services import users
from app.services.telegram import InitDataError, validate_init_data

NO_TELEGRAM = "Откройте приложение в Telegram."
BAD_INIT_DATA = "Не удалось подтвердить вход через Telegram."


def telegram_user(
    x_telegram_init_data: str | None = Header(default=None),
) -> TelegramUser | None:
    required = get_settings().telegram_require_init_data

    if not x_telegram_init_data:
        if required:
            raise HTTPException(status_code=401, detail=NO_TELEGRAM)
        return None

    try:
        return validate_init_data(x_telegram_init_data)
    except InitDataError as exc:
        if required:
            raise HTTPException(status_code=401, detail=BAD_INIT_DATA) from exc
        # Outside Telegram a stray or stale header is not worth failing a
        # booking over; in production the branch above has already fired.
        return None


def require_telegram_user(
    x_telegram_init_data: str | None = Header(default=None),
) -> TelegramUser:
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail=NO_TELEGRAM)
    try:
        return validate_init_data(x_telegram_init_data)
    except InitDataError as exc:
        raise HTTPException(status_code=401, detail=BAD_INIT_DATA) from exc


def current_user(
    telegram: TelegramUser | None = Depends(telegram_user),
) -> dict | None:
    """The persistent user behind this request, or None outside Telegram.

    None is not an error: a browser visitor has no durable identity, so nothing
    is metered for them. Quotas exist only where an identity cannot be discarded
    by clearing site data.
    """
    if telegram is None or not get_settings().quota_enabled:
        return None
    return users.get_or_create(telegram)
