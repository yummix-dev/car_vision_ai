"""In-app events that reach the user through the bot.

Every function here is fire-and-forget and swallows its failures. A notification
that cannot be delivered — most often because the user never allowed the bot to
message them — must never turn into a failed generation or an unpaid bonus.
"""

import asyncio
import logging

from app.config import get_settings
from app.db import connect
from app.services.telegram import (
    PhotoSendError,
    WriteAccessDenied,
    send_message_to_user,
)

log = logging.getLogger(__name__)


def _telegram_id(user_id: int) -> int | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT telegram_id FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return row["telegram_id"] if row else None


def _send(user_id: int, text: str) -> None:
    if not get_settings().telegram_bot_token:
        return
    telegram_id = _telegram_id(user_id)
    if telegram_id is None:
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


def _tries(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} примерка"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} примерки"
    return f"{n} примерок"


def referral_rewarded(inviter_user_id: int, amount: int) -> None:
    _send(
        inviter_user_id,
        f"Ваш друг создал первую AI-примерку. "
        f"Вам начислена бонусная примерка ({_tries(amount)}).",
    )


def referred_client_rewarded(inviter_user_id: int, amount: int) -> None:
    _send(
        inviter_user_id,
        f"Приглашённый вами клиент оформил установку. "
        f"Вам начислено: {_tries(amount)}.",
    )


def code_activated(user_id: int, bonus: int, restored: int) -> None:
    parts = []
    if restored:
        parts.append("мы восстановили бесплатные примерки во всех разделах")
    if bonus:
        parts.append(f"начислили {_tries(bonus)}")
    if not parts:
        return
    _send(user_id, "Код активирован: " + " и ".join(parts) + ".")


def low_balance(user_id: int, category_label: str, left: int) -> None:
    _send(
        user_id,
        f"Осталась {_tries(left)} в разделе «{category_label}».",
    )


def category_exhausted(user_id: int, category_label: str, bonus_left: int) -> None:
    tail = (
        f" У вас есть {_tries(bonus_left)} бонусных."
        if bonus_left
        else " Пригласите друга, чтобы получить бонусные примерки."
    )
    _send(
        user_id,
        f"Бесплатные примерки в разделе «{category_label}» закончились.{tail}",
    )


def referral_frozen(inviter_user_id: int) -> None:
    _send(
        inviter_user_id,
        "Бонус за приглашённого друга временно на проверке. "
        "Мы сообщим, когда она завершится.",
    )
