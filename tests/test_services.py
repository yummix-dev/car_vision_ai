"""Paid services: pricing integration, validation, and the seed."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.pricing import Selection
from app.server import create_app
from app.services import services_repo
from app.services.pricing_service import PricingError, quote


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_db", str(tmp_path / "app.db"))
    reset_for_tests()
    yield


def _service(category="rul", name="Установка руля", price=500_000, default_on=False):
    return services_repo.create(category, name, price, default_on=default_on)


# ── the seed ──────────────────────────────────────────────────


def test_seed_gives_every_category_an_installation_service():
    services_repo.seed_installation()
    from app.services.catalog_service import get_catalog

    for cat in get_catalog().categories:
        names = [s["name"] for s in services_repo.list_for_category(cat.id)]
        assert "Установка" in names, f"{cat.id} has no installation service"


def test_seed_is_idempotent():
    services_repo.seed_installation()
    services_repo.seed_installation()
    rul = services_repo.list_for_category("rul")
    assert sum(1 for s in rul if s["name"] == "Установка") == 1


# ── pricing ───────────────────────────────────────────────────


def test_a_selected_service_adds_a_line_and_its_price():
    svc = _service(price=500_000)
    q = quote("amg", [], [svc["id"]])

    assert any(line.label == "Установка руля" and line.amount == 500_000 for line in q.lines)
    # amg base+options is 7_100_000; the service is on top.
    assert q.total == 7_100_000 + 500_000


def test_multiple_services_stack():
    a = _service(name="Установка", price=400_000)
    b = _service(name="Перепайка", price=150_000)
    q = quote("amg", [], [a["id"], b["id"]])
    assert q.total == 7_100_000 + 400_000 + 150_000


def test_a_service_from_another_category_is_rejected():
    """The rigor options get: a client cannot attach an audio service to a wheel."""
    audio_svc = _service(category="audio", name="Установка магнитолы", price=300_000)
    with pytest.raises(PricingError):
        quote("amg", [], [audio_svc["id"]])


def test_an_inactive_service_is_rejected():
    svc = _service(price=500_000)
    services_repo.deactivate(svc["id"])
    with pytest.raises(PricingError):
        quote("amg", [], [svc["id"]])


def test_an_unknown_service_id_is_rejected():
    with pytest.raises(PricingError):
        quote("amg", [], [999999])


def test_a_repeated_service_id_is_charged_once():
    svc = _service(price=500_000)
    q = quote("amg", [], [svc["id"], svc["id"]])
    assert q.total == 7_100_000 + 500_000


def test_no_services_leaves_the_quote_unchanged():
    q = quote("amg", [])
    assert q.total == 7_100_000


# ── resolve ordering ──────────────────────────────────────────


def test_resolve_keeps_sort_order_and_drops_inactive():
    first = _service(name="A", price=100)
    second = _service(name="B", price=200)
    services_repo.deactivate(first["id"])

    # Only the active one resolves; requesting the inactive raises.
    resolved = services_repo.resolve("rul", [second["id"]])
    assert [s["name"] for s in resolved] == ["B"]


# ── the endpoint ──────────────────────────────────────────────


def test_services_endpoint_returns_only_public_active_fields():
    services_repo.seed_installation()
    _service(name="Скрытая", price=1, default_on=False)
    hidden = _service(name="Выключенная", price=1)
    services_repo.deactivate(hidden["id"])

    client = TestClient(create_app())
    res = client.get("/api/catalog/rul/services")
    assert res.status_code == 200
    body = res.json()

    names = {s["name"] for s in body}
    assert "Установка" in names
    assert "Выключенная" not in names, "inactive services are not offered"
    for s in body:
        assert set(s.keys()) == {"id", "name", "price", "default_on"}


def test_booking_recomputes_total_with_services(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")  # log, don't deliver
    svc = _service(price=500_000)
    client = TestClient(create_app())

    res = client.post(
        "/api/booking",
        json={
            "cart": [{"product_id": "amg", "selections": [], "service_ids": [svc["id"]]}],
            "contact": {"phone": "+998900000000"},
            "car_label": "Test",
        },
    )
    assert res.status_code == 200
    assert res.json()["total"] == 7_100_000 + 500_000
