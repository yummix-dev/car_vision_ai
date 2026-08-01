"""Orders and the payment seam.

Phase 1: an order is persisted for every booking, the chosen method is captured
and (with no provider configured) routed to the manager. The online rails are
dormant until a credential is set.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import reset_for_tests
from app.server import create_app
from app.services import orders, payments


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_db", str(tmp_path / "app.db"))
    reset_for_tests()
    yield


def _order(**over) -> dict:
    args = dict(
        order_code="abc123", telegram_id=42, car_label="Chevrolet Malibu 2023",
        positions=1, total=6_200_000, payment_method="uzum", payment_status="manual",
    )
    args.update(over)
    return orders.create(**args)


# ── orders store ──────────────────────────────────────────────


def test_create_and_get_by_code():
    _order()
    o = orders.get_by_code("abc123")
    assert o["total"] == 6_200_000
    assert o["payment_method"] == "uzum"
    assert o["telegram_id"] == 42


def test_rejects_unknown_method_and_status():
    with pytest.raises(ValueError):
        _order(payment_method="crypto")
    with pytest.raises(ValueError):
        _order(payment_status="settled")


def test_set_status_moves_and_records_provider_ref():
    _order(order_code="s1", payment_method="telegram", payment_status="pending")
    orders.set_status("s1", "paid", provider_ref="inv_9")
    o = orders.get_by_code("s1")
    assert o["payment_status"] == "paid"
    assert o["provider_ref"] == "inv_9"


# ── the seam ──────────────────────────────────────────────────


def test_all_methods_offline_by_default():
    assert payments.is_online("telegram") is False
    assert payments.is_online("uzum") is False
    assert payments.is_online("cash") is False


def test_telegram_is_online_once_a_provider_token_is_set(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_payment_provider_token", "TEST:PROVIDER")
    assert payments.is_online("telegram") is True


def test_uzum_needs_both_merchant_id_and_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "uzum_merchant_id", "M1")
    assert payments.is_online("uzum") is False  # key still missing
    monkeypatch.setattr(get_settings(), "uzum_api_key", "K1")
    assert payments.is_online("uzum") is True


def test_initiate_routes_to_manager_when_unconfigured():
    for method in ("cash", "telegram", "uzum"):
        assert payments.initiate({"order_code": "x"}, method) == {"kind": "manager"}


# ── the booking endpoint ──────────────────────────────────────


def _book(client, payment_method=None):
    body = {
        "cart": [{"product_id": "amg", "selections": [], "service_ids": []}],
        "contact": {"phone": "+998900000000"},
        "car_label": "Chevrolet Malibu 2023",
    }
    if payment_method is not None:
        body["payment_method"] = payment_method
    return client.post("/api/booking", json=body)


def test_booking_persists_an_order_with_the_chosen_method(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")  # log, don't deliver
    client = TestClient(create_app())

    res = _book(client, "uzum")
    assert res.status_code == 200
    body = res.json()
    assert body["payment_method"] == "uzum"
    assert body["payment"]["kind"] == "manager"

    order = orders.get_by_code(body["booking_id"])
    assert order is not None
    assert order["payment_method"] == "uzum"
    assert order["payment_status"] == "manual"
    assert order["total"] == 6_200_000


def test_booking_defaults_to_cash():
    client = TestClient(create_app())
    body = _book(client).json()
    assert body["payment_method"] == "cash"


def test_booking_rejects_an_unknown_method():
    client = TestClient(create_app())
    res = _book(client, "bitcoin")
    assert res.status_code == 422  # pydantic Literal rejects it


def test_manager_message_carries_the_payment_method(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_manager_chat_id", "123")
    sent = {}

    async def fake_notify(text):
        sent["text"] = text

    monkeypatch.setattr("app.routers.cart.notify_manager", fake_notify)
    client = TestClient(create_app())

    _book(client, "telegram")
    assert "Оплата: Картой в Telegram" in sent["text"]
