"""initData validation and manager delivery.

`make_init_data` builds a payload with the algorithm exactly as Telegram
documents it. That is the point of the helper: if the implementation ever swaps
the HMAC key and message (the easy mistake — the key is the literal
"WebAppData", the message is the bot token), these tests stop passing.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.models.telegram import TelegramUser
from app.server import create_app
from app.services import telegram as tg_service
from app.services.telegram import (
    InitDataError,
    ManagerNotifyError,
    render_booking_message,
    validate_init_data,
)

TOKEN = "123456:TEST-TOKEN"
USER = {"id": 4242, "first_name": "Иван", "last_name": "П", "username": "ivan"}


def make_init_data(
    token: str = TOKEN, user: dict | None = None, auth_date: int | None = None, **extra
) -> str:
    fields = {
        "user": json.dumps(user or USER, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF",
        **extra,
    }
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(
        secret, check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(fields)


@pytest.fixture
def settings(monkeypatch):
    """get_settings is lru_cached, so patch the cached instance in place."""
    s = get_settings()
    monkeypatch.setattr(s, "telegram_bot_token", TOKEN)
    monkeypatch.setattr(s, "telegram_manager_chat_id", "")
    monkeypatch.setattr(s, "telegram_require_init_data", False)
    return s


@pytest.fixture
def client(settings):
    return TestClient(create_app())


CART = [{"product_id": "amg", "selections": []}]
CONTACT = {"name": "Иван", "phone": "+998901234567"}


def _booking_payload() -> dict:
    return {"cart": CART, "contact": CONTACT, "car_label": "Chevrolet Malibu 2023"}


# ── validation ────────────────────────────────────────────────


def test_valid_init_data_identifies_the_user(settings):
    user = validate_init_data(make_init_data())
    assert isinstance(user, TelegramUser)
    assert user.id == 4242
    assert user.handle == "@ivan"
    assert user.full_name == "Иван П"


def test_tampered_field_is_rejected(settings):
    """The signature covers every field, so swapping the user invalidates it."""
    raw = make_init_data()
    forged = raw.replace("4242", "9999")
    assert forged != raw
    with pytest.raises(InitDataError):
        validate_init_data(forged)


def test_payload_signed_with_another_token_is_rejected(settings):
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(token="999:OTHER-TOKEN"))


def test_stale_init_data_is_rejected(settings):
    """A valid signature never expires on its own — a captured payload would
    otherwise be replayable forever."""
    old = int(time.time()) - settings.telegram_auth_max_age_seconds - 60
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=old))


def test_unknown_fields_still_validate(settings):
    """Telegram adds fields over time; they are signed and must be included in
    the check string rather than dropped."""
    user = validate_init_data(make_init_data(chat_type="private", signature="abc"))
    assert user.id == 4242


def test_missing_hash_is_rejected(settings):
    with pytest.raises(InitDataError):
        validate_init_data(urlencode({"user": json.dumps(USER), "auth_date": "1"}))


# ── the booking endpoint ──────────────────────────────────────


def test_booking_without_init_data_is_allowed_in_development(client):
    """The browser demo has no initData and must keep working."""
    res = client.post("/api/booking", json=_booking_payload())
    assert res.status_code == 200
    assert res.json()["status"] == "received"


def test_booking_without_init_data_is_rejected_when_required(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_require_init_data", True)
    res = client.post("/api/booking", json=_booking_payload())
    assert res.status_code == 401


def test_booking_with_forged_init_data_is_rejected_when_required(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_require_init_data", True)
    res = client.post(
        "/api/booking",
        json=_booking_payload(),
        headers={"X-Telegram-Init-Data": make_init_data(token="999:OTHER")},
    )
    assert res.status_code == 401


def test_booking_from_a_verified_user_is_accepted(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_require_init_data", True)
    monkeypatch.setattr(get_settings(), "telegram_manager_chat_id", "-100500")
    sent = {}

    async def fake_notify(text):
        sent["text"] = text

    monkeypatch.setattr("app.routers.cart.notify_manager", fake_notify)

    res = client.post(
        "/api/booking",
        json=_booking_payload(),
        headers={"X-Telegram-Init-Data": make_init_data()},
    )
    assert res.status_code == 200
    # The user reaches the manager through the message, which is the only place
    # a booking is now kept.
    assert "tg://user?id=4242" in sent["text"]


# ── manager delivery ──────────────────────────────────────────


def test_booking_is_delivered_to_the_manager(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_manager_chat_id", "-100500")
    sent = {}

    async def fake_notify(text):
        sent["text"] = text

    monkeypatch.setattr("app.routers.cart.notify_manager", fake_notify)

    res = client.post("/api/booking", json=_booking_payload())
    assert res.status_code == 200

    text = sent["text"]
    assert res.json()["booking_id"] in text
    assert "AMG Carbon LED" in text          # the position
    assert "+998901234567" in text           # how to call back
    assert res.json()["total_formatted"] in text


def test_failed_delivery_does_not_confirm_the_booking(client, monkeypatch):
    """A booking nobody received must not come back as 'заявка отправлена'."""
    monkeypatch.setattr(get_settings(), "telegram_manager_chat_id", "-100500")

    async def fake_notify(text):
        raise ManagerNotifyError("boom")

    monkeypatch.setattr("app.routers.cart.notify_manager", fake_notify)

    res = client.post("/api/booking", json=_booking_payload())
    assert res.status_code == 502
    assert "booking_id" not in res.text


def test_manager_message_escapes_user_input():
    """The message is parse_mode=HTML and the comment is arbitrary user text."""
    text = render_booking_message(
        booking_id="abc",
        car_label="Malibu",
        lines=["Руль — 1 сум"],
        total_formatted="1",
        contact={"phone": "+998", "comment": "<b>жирный</b> & <script>"},
        user=None,
    )
    assert "<b>жирный</b>" not in text
    assert "&lt;script&gt;" in text
    assert "&amp;" in text


@pytest.mark.asyncio
async def test_notify_manager_refuses_when_unconfigured(settings, monkeypatch):
    monkeypatch.setattr(settings, "telegram_manager_chat_id", "")
    with pytest.raises(ManagerNotifyError):
        await tg_service.notify_manager("hi")


@pytest.mark.asyncio
async def test_notify_manager_posts_the_bot_api_shape(settings, monkeypatch):
    """The one place that talks to Telegram for real — the URL carries the token
    and the payload must name the chat, or the shop silently gets nothing."""
    monkeypatch.setattr(settings, "telegram_manager_chat_id", "-100500")
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            seen["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            seen["url"] = url
            seen["json"] = json
            return FakeResponse()

    monkeypatch.setattr(tg_service.httpx, "AsyncClient", FakeClient)
    await tg_service.notify_manager("привет")

    assert seen["url"] == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert seen["json"]["chat_id"] == "-100500"
    assert seen["json"]["text"] == "привет"
    assert seen["json"]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_notify_manager_wraps_transport_failures(settings, monkeypatch):
    """A raw httpx error must not escape as a 500 — the router turns
    ManagerNotifyError into a 502 the customer can act on."""
    monkeypatch.setattr(settings, "telegram_manager_chat_id", "-100500")

    class ExplodingClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json):
            raise tg_service.httpx.ConnectError("no route to host")

    monkeypatch.setattr(tg_service.httpx, "AsyncClient", ExplodingClient)
    with pytest.raises(ManagerNotifyError):
        await tg_service.notify_manager("привет")
