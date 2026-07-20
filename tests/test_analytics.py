"""Event ingestion, the funnel query, and the /admin page."""

import base64
import time

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.server import create_app
from app.services import analytics


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Fresh databases per test — the funnel counts everything in the file.

    app_db is isolated too, not just the analytics one: /admin reads referrals,
    so without this the suite would open (and migrate) the developer's real
    application database.
    """
    monkeypatch.setattr(get_settings(), "analytics_db", str(tmp_path / "a.db"))
    monkeypatch.setattr(get_settings(), "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(get_settings(), "analytics_enabled", True)
    analytics.reset_for_tests()
    db.reset_for_tests()
    from app.routers import events as events_router

    events_router._recent.clear()
    yield


@pytest.fixture
def client():
    return TestClient(create_app())


def _post(client, session_id="s1", **events):
    return client.post(
        "/api/events",
        json={"session_id": session_id, "events": list(events.get("events", []))},
    )


def _seed(session_id, *names, **fields):
    analytics._record_sync(
        [{"session_id": session_id, "name": n, **fields} for n in names], None
    )


# ── ingestion ─────────────────────────────────────────────────


def test_events_are_stored_and_readable(client):
    res = _post(client, events=[{"name": "screen_view", "screen": "pick"}])
    assert res.status_code == 200
    assert res.json()["stored"] == 1
    assert analytics.totals(days=1)["sessions"] == 1


def test_unknown_event_name_is_rejected(client):
    """A typo that lands in the table splits a funnel step in two, and the
    numbers stop adding up long after anyone remembers why."""
    res = _post(client, events=[{"name": "screen_veiw"}])
    assert res.status_code == 400
    assert "screen_veiw" in res.json()["detail"]


def test_oversized_batch_is_rejected(client):
    res = _post(
        client,
        events=[{"name": "screen_view"}] * (analytics.MAX_BATCH + 1),
    )
    assert res.status_code == 422  # pydantic bounds the list before the handler


def test_oversized_payload_is_rejected(client):
    res = _post(
        client,
        events=[{"name": "screen_view", "payload": {"x": "y" * 3000}}],
    )
    assert res.status_code == 400


def test_the_server_assigns_the_timestamp(client):
    """A phone's clock is not evidence. A client-supplied ts would let one
    device rewrite yesterday's numbers."""
    before = int(time.time())
    _post(
        client,
        events=[{"name": "screen_view", "payload": {"ts": 0}}],
    )
    with analytics._connect() as conn:
        ts = conn.execute("SELECT ts FROM events").fetchone()["ts"]
    assert ts >= before


def test_rate_limit_stops_a_flood(client):
    from app.routers.events import RATE_MAX_EVENTS

    for _ in range(RATE_MAX_EVENTS // 10):
        assert _post(client, events=[{"name": "screen_view"}] * 10).status_code == 200
    assert _post(client, events=[{"name": "screen_view"}]).status_code == 429


def test_a_disabled_pipeline_stores_nothing(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "analytics_enabled", False)
    assert _post(client, events=[{"name": "screen_view"}]).json()["stored"] == 0


# ── the funnel ────────────────────────────────────────────────


def test_funnel_counts_distinct_sessions(client):
    """Revisiting a screen must not inflate a step."""
    _seed("a", "category_picked", "category_picked", "photo_uploaded")
    _seed("b", "category_picked")

    steps = {s["name"]: s for s in analytics.funnel(days=1)}
    assert steps["category_picked"]["sessions"] == 2
    assert steps["photo_uploaded"]["sessions"] == 1


def test_funnel_reports_conversion_and_drop_off(client):
    _seed("a", "category_picked", "photo_uploaded")
    _seed("b", "category_picked")

    steps = analytics.funnel(days=1)
    first, second = steps[0], steps[1]
    assert first["conversion"] is None, "nothing to convert from on the first step"
    assert second["sessions"] == 1
    assert second["conversion"] == 50.0
    assert second["dropped"] == 1


def test_funnel_ignores_events_outside_the_window(client):
    _seed("old", "category_picked")
    with analytics._connect() as conn:
        conn.execute("UPDATE events SET ts=?", (int(time.time()) - 40 * 86400,))
        conn.commit()

    assert analytics.funnel(days=7)[0]["sessions"] == 0
    assert analytics.funnel(days=90)[0]["sessions"] == 1


def test_failure_rate_counts_only_generation_outcomes(client):
    _seed("a", "generation_done")
    _seed("b", "generation_failed")
    _seed("c", "screen_view")

    stats = analytics.totals(days=1)
    assert stats["generations"] == 2
    assert stats["failure_rate"] == 50.0


def test_top_products_ranks_by_distinct_sessions(client):
    _seed("a", "product_opened", product_id="amg")
    _seed("b", "product_opened", product_id="amg")
    _seed("c", "product_opened", product_id="other")

    top = analytics.top("product_id", days=1)
    assert top[0]["key"] == "amg"
    assert top[0]["sessions"] == 2


def test_top_rejects_an_arbitrary_column():
    """The column is interpolated into SQL, so the whitelist is load-bearing."""
    with pytest.raises(ValueError):
        analytics.top("payload; DROP TABLE events--")


def test_purge_removes_only_old_events(client):
    _seed("old", "screen_view")
    with analytics._connect() as conn:
        conn.execute("UPDATE events SET ts=?", (int(time.time()) - 400 * 86400,))
        conn.commit()
    _seed("new", "screen_view")

    assert analytics.purge_old(180) == 1
    assert analytics.totals(days=365)["sessions"] == 1


# ── /admin ────────────────────────────────────────────────────


def _auth(password: str) -> dict:
    token = base64.b64encode(f"admin:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_admin_is_absent_without_a_password(monkeypatch):
    """An unset password means no page — never a page without a password."""
    monkeypatch.setattr(get_settings(), "admin_password", "")
    res = TestClient(create_app()).get("/admin", headers=_auth(""))
    assert res.status_code == 404


def test_admin_rejects_a_wrong_password(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    res = TestClient(create_app()).get("/admin", headers=_auth("guess"))
    assert res.status_code == 401


def test_admin_renders_the_funnel(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    client = TestClient(create_app())
    _seed("a", "category_picked", "photo_uploaded")
    _seed("b", "category_picked")

    res = client.get("/admin?days=7", headers=_auth("secret"))
    assert res.status_code == 200
    assert "Выбрал раздел" in res.text
    assert "Загрузил фото" in res.text
    assert "50.0%" in res.text


def test_admin_lists_frozen_referrals_and_ends_them(monkeypatch):
    """The page is the only exit from the frozen state, so it has to be there."""
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    monkeypatch.setattr(get_settings(), "referral_min_seconds", 300)
    monkeypatch.setattr(get_settings(), "referral_fraud_threshold", 2)
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")
    client = TestClient(create_app())

    from app.models.telegram import TelegramUser
    from app.services import quota, referrals, users

    inviter = users.get_or_create(TelegramUser(id=1, first_name="A"))
    invited = users.get_or_create(TelegramUser(id=2, first_name="B"))
    users.confirm_car(invited["id"], "Chevrolet", "Malibu", 2023)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    referrals.on_first_generation(invited["id"], "own-photo")

    page = client.get("/admin", headers=_auth("secret"))
    assert "Замороженные бонусы" in page.text
    assert "Подтвердить" in page.text

    referral_id = referrals.list_frozen()[0]["id"]
    res = client.post(
        f"/admin/referrals/{referral_id}/approve",
        data={"note": "ок"},
        headers=_auth("secret"),
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert quota.snapshot(inviter["id"])["bonus_remaining"] == 1


def test_admin_actions_require_the_password(monkeypatch):
    """A state change reachable without the password would be worse than no
    review page at all."""
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    client = TestClient(create_app())

    res = client.post("/admin/referrals/1/approve", headers=_auth("wrong"))
    assert res.status_code == 401


def test_admin_shows_catalog_names_not_ids(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_password", "secret")
    client = TestClient(create_app())
    _seed("a", "product_opened", product_id="amg", category_id="rul")

    res = client.get("/admin", headers=_auth("secret"))
    assert "AMG Carbon LED" in res.text
    assert "Руль" in res.text
