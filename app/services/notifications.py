"""In-app events that reach the user through the bot.

Every function here is fire-and-forget and swallows its failures. A notification
that cannot be delivered — most often because the user never allowed the bot to
message them — must never turn into a failed generation or an unpaid bonus.

Each message is sent in the recipient's stored language (users.lang).
"""

import asyncio
import logging

from app.config import get_settings
from app.db import connect
from app.i18n import t, tries
from app.services.telegram import (
    PhotoSendError,
    WriteAccessDenied,
    send_message_to_user,
)

log = logging.getLogger(__name__)


def _recipient(user_id: int) -> tuple[int, str] | None:
    """(telegram_id, lang) for a user, or None if unknown."""
    with connect() as conn:
        row = conn.execute(
            "SELECT telegram_id, lang FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return (row["telegram_id"], row["lang"]) if row else None


def _send(user_id: int, key: str, **params) -> None:
    """Deliver notification `key` in the user's language, or nothing."""
    if not get_settings().telegram_bot_token:
        return
    recipient = _recipient(user_id)
    if recipient is None:
        return
    telegram_id, lang = recipient
    text = _render(key, lang, params)
    if text is None:
        return

    async def deliver():
        try:
            await send_message_to_user(telegram_id, text)
        except (WriteAccessDenied, PhotoSendError):
            # Expected: plenty of users never grant write access.
            pass
        except Exception:  # noqa: BLE001 - never load-bearing
            log.exception("notification failed for user %s", user_id)

    try:
        asyncio.get_running_loop().create_task(deliver())
    except RuntimeError:
        # No loop (a sync test, a script): deliver inline rather than silently
        # dropping the message.
        asyncio.run(deliver())


def _render(key: str, lang: str, params: dict) -> str | None:
    # `tries_n` / `bonus_n` params carry a count that needs pluralising first.
    resolved = dict(params)
    if "tries_n" in resolved:
        resolved["tries"] = tries(resolved.pop("tries_n"), lang)
    return t(key, lang, **resolved)


def referral_rewarded(inviter_user_id: int, amount: int) -> None:
    _send(inviter_user_id, "notif.referral", tries_n=amount)


def referred_client_rewarded(inviter_user_id: int, amount: int) -> None:
    _send(inviter_user_id, "notif.referred_client", tries_n=amount)


def code_activated(user_id: int, bonus: int, restored: int) -> None:
    if restored and bonus:
        _send(user_id, "notif.code_both", tries_n=bonus)
    elif restored:
        _send(user_id, "notif.code_restore")
    elif bonus:
        _send(user_id, "notif.code_visit", tries_n=bonus)


def low_balance(user_id: int, category_label: str, left: int) -> None:
    _send(user_id, "notif.low_balance", tries_n=left, cat=category_label)


def category_exhausted(user_id: int, category_label: str, bonus_left: int) -> None:
    if bonus_left:
        _send(user_id, "notif.cat_exhausted_bonus", tries_n=bonus_left, cat=category_label)
    else:
        _send(user_id, "notif.cat_exhausted_none", cat=category_label)


def referral_frozen(inviter_user_id: int) -> None:
    _send(inviter_user_id, "notif.referral_frozen")
