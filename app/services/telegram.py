"""Everything that talks to Telegram: initData validation and manager delivery.

Nothing else in the app imports `httpx` for Telegram or knows the Bot API shape.

Notes on the algorithm (these are load-bearing):
  * `secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)`. Telegram writes
    it as `HMAC_SHA256(<bot_token>, "WebAppData")` in their own data-first
    notation, which reads as the exact opposite. Swapping the two produces a
    validator that rejects every real payload and accepts nothing — it looks
    like a config problem, not a code bug. The tests build initData with the
    documented algorithm, so a swap fails them.
  * The `hash` field is excluded from the data-check-string; every other field
    is included, sorted, joined with \\n — including fields we do not model.
  * Comparison must be constant-time: a `==` on a hex digest leaks it to timing.
"""

import hashlib
import hmac
import html
import json
import logging
import time
from urllib.parse import parse_qsl

import httpx

from app.config import get_settings
from app.models.telegram import TelegramUser

log = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
SECRET_KEY_SALT = b"WebAppData"


class InitDataError(ValueError):
    """initData was absent, malformed, forged or stale."""


class ManagerNotifyError(RuntimeError):
    """The booking could not be delivered to the shop."""


class WriteAccessDenied(RuntimeError):
    """The bot may not message this user.

    Distinct from a transport failure: the user can fix this one by granting
    permission, so the UI must say something different. Telegram answers 403
    both when the user never allowed writes and when they blocked the bot.
    """


class PhotoSendError(RuntimeError):
    """The photo could not be delivered for any other reason."""


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(SECRET_KEY_SALT, bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(raw: str, *, bot_token: str | None = None) -> TelegramUser:
    """Verify a Telegram initData string and return the user it identifies.

    Raises InitDataError on anything short of a valid, fresh, signed payload.
    """
    settings = get_settings()
    token = bot_token or settings.telegram_bot_token
    if not token:
        raise InitDataError("TELEGRAM_BOT_TOKEN is not configured")
    if not raw:
        raise InitDataError("Empty initData")

    # strict_parsing so a malformed pair is an error rather than a silent drop —
    # a dropped pair would change the data-check-string and fail confusingly.
    try:
        fields = dict(parse_qsl(raw, strict_parsing=True))
    except ValueError as exc:
        raise InitDataError("Malformed initData") from exc

    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise InitDataError("initData carries no hash")

    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    expected = hmac.new(
        _secret_key(token), check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("initData signature does not match")

    # A valid signature is forever unless auth_date is checked: anyone who once
    # captured a payload could replay it indefinitely.
    try:
        auth_date = int(fields.get("auth_date", ""))
    except ValueError as exc:
        raise InitDataError("initData carries no usable auth_date") from exc
    age = time.time() - auth_date
    if age > settings.telegram_auth_max_age_seconds:
        raise InitDataError("initData has expired")

    try:
        user = json.loads(fields["user"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise InitDataError("initData carries no user") from exc

    return TelegramUser.model_validate(user)


def _escape(value: object) -> str:
    """Contact fields are user input and the message is parse_mode=HTML —
    an unescaped '<' would break delivery or inject markup into the chat."""
    return html.escape(str(value), quote=False)


def render_booking_message(
    booking_id: str,
    car_label: str,
    lines: list[str],
    total_formatted: str,
    contact: dict,
    user: TelegramUser | None,
    payment_label: str = "",
) -> str:
    """The manager's copy of a booking. Everything they need to call back."""
    rows = [
        f"<b>Заявка № {_escape(booking_id)}</b>",
        f"Автомобиль: {_escape(car_label or '—')}",
        "",
        "<b>Позиции</b>",
        *(f"• {_escape(line)}" for line in lines),
        "",
        f"<b>Итого: {_escape(total_formatted)} сум</b>",
    ]
    if payment_label:
        rows.append(f"Оплата: {_escape(payment_label)}")
    rows += [
        "",
        "<b>Контакты</b>",
        f"Имя: {_escape(contact.get('name') or '—')}",
        f"Телефон: {_escape(contact.get('phone') or '—')}",
    ]

    handle = contact.get("telegram") or (user.handle if user else "")
    if handle:
        rows.append(f"Telegram: {_escape(handle)}")
    if user:
        # tg://user?id= opens a direct chat even when the account has no
        # @username, which is the common case here.
        rows.append(
            f'Профиль: <a href="tg://user?id={user.id}">'
            f"{_escape(user.full_name or user.id)}</a>"
        )
    if contact.get("date"):
        rows.append(f"Желаемая дата: {_escape(contact['date'])}")
    if contact.get("comment"):
        rows.append(f"Комментарий: {_escape(contact['comment'])}")

    return "\n".join(rows)


def delivery_configured() -> bool:
    """Whether bookings can reach a manager at all.

    Kept separate from a delivery failure on purpose: an unconfigured dev box
    must not turn every booking into a 502, while a *configured* shop that fails
    to deliver must never confirm the booking. Callers branch on this.
    """
    settings = get_settings()
    return bool(settings.telegram_bot_token and settings.telegram_manager_chat_id)


async def notify_manager(text: str) -> None:
    """Deliver a booking to the shop's manager chat.

    Raises ManagerNotifyError so the caller can refuse to confirm a booking that
    nobody received — a silent failure would send the customer away believing
    they are booked.
    """
    settings = get_settings()
    if not delivery_configured():
        raise ManagerNotifyError("Telegram manager delivery is not configured")

    url = f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_manager_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.telegram_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - any failure means undelivered
        log.exception("Telegram sendMessage failed")
        raise ManagerNotifyError("Не удалось отправить заявку менеджеру") from exc


async def send_message_to_user(user_id: int, text: str) -> None:
    """Plain text into a user's chat with the bot. Same 403 rule as photos."""
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise PhotoSendError("Telegram is not configured")

    url = f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(
            timeout=settings.telegram_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": user_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
            )
    except Exception as exc:  # noqa: BLE001 - transport failure
        raise PhotoSendError("Не удалось отправить сообщение") from exc

    if response.status_code == 403:
        raise WriteAccessDenied("Бот не может писать вам первым")
    if response.status_code >= 400:
        log.error("sendMessage returned %s: %s", response.status_code, response.text[:300])
        raise PhotoSendError("Не удалось отправить сообщение")


async def send_photo_to_user(
    user_id: int, image_bytes: bytes, filename: str, caption: str = ""
) -> None:
    """Send a generated render into the user's own chat with the bot.

    The bytes go up as multipart rather than as a URL: Telegram's servers fetch
    a `photo` URL themselves, and this app is routinely served from 127.0.0.1
    where they cannot reach it.
    """
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise PhotoSendError("Telegram is not configured")

    url = f"{API_BASE}/bot{settings.telegram_bot_token}/sendPhoto"

    try:
        async with httpx.AsyncClient(
            timeout=settings.telegram_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                data={"chat_id": str(user_id), "caption": caption},
                files={"photo": (filename, image_bytes, "image/jpeg")},
            )
    except Exception as exc:  # noqa: BLE001 - transport failure
        log.exception("Telegram sendPhoto failed for user %s", user_id)
        raise PhotoSendError("Не удалось отправить изображение") from exc

    if response.status_code == 403:
        # Not an error to log loudly: the user simply has not allowed the bot
        # to write to them, which the client asks for separately.
        raise WriteAccessDenied("Бот не может писать вам первым")
    if response.status_code >= 400:
        log.error(
            "Telegram sendPhoto returned %s: %s",
            response.status_code,
            response.text[:300],
        )
        raise PhotoSendError("Не удалось отправить изображение")
