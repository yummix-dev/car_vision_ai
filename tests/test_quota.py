"""AI try-on quotas: allowances, spend order, refunds, idempotency, races."""

import threading

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.telegram import TelegramUser
from app.server import create_app
from app.services import photos, quota, rate_limit, users

from tests.test_telegram import TOKEN, make_init_data

CATEGORY = "rul"


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(s, "analytics_db", str(tmp_path / "an.db"))
    monkeypatch.setattr(s, "quota_enabled", True)
    monkeypatch.setattr(s, "free_tries_per_category", 3)
    monkeypatch.setattr(s, "telegram_bot_token", TOKEN)
    monkeypatch.setattr(s, "generation_limit_per_hour", 1000)
    reset_for_tests()
    rate_limit.reset()
    yield


@pytest.fixture
def user():
    return users.get_or_create(TelegramUser(id=4242, first_name="Иван"))


def _spend(user_id, n, category=CATEGORY, prefix="k"):
    for i in range(n):
        quota.reserve(user_id, category, f"{prefix}-{i}")


# ── allowances ────────────────────────────────────────────────


def test_a_new_user_starts_with_three_per_category(user):
    snap = quota.snapshot(user["id"], CATEGORY)
    assert snap["current"] == {"free_limit": 3, "free_remaining": 3}
    assert snap["bonus_remaining"] == 0
    assert snap["next_charge"] == quota.FREE


def test_a_category_never_seen_before_still_has_its_full_limit(user):
    """Adding a category to catalog.yaml must need no migration and no admin
    action — the allowance appears the first time it is touched."""
    snap = quota.snapshot(user["id"], "brand-new-category")
    assert snap["current"]["free_remaining"] == 3

    quota.reserve(user["id"], "brand-new-category", "k1")
    assert quota.snapshot(user["id"], "brand-new-category")["current"]["free_remaining"] == 2


def test_allowances_are_independent_per_category(user):
    _spend(user["id"], 3)
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 0
    assert quota.snapshot(user["id"], "audio")["current"]["free_remaining"] == 3


# ── spend order ───────────────────────────────────────────────


def test_free_is_spent_before_bonus(user):
    quota.grant(user["id"], 5, "test")
    quota.reserve(user["id"], CATEGORY, "k1")

    snap = quota.snapshot(user["id"], CATEGORY)
    assert snap["current"]["free_remaining"] == 2
    assert snap["bonus_remaining"] == 5, "bonus untouched while free remains"


def test_bonus_is_spent_once_the_category_is_empty(user):
    quota.grant(user["id"], 5, "test")
    _spend(user["id"], 3)

    snap = quota.snapshot(user["id"], CATEGORY)
    assert snap["next_charge"] == quota.BONUS

    quota.reserve(user["id"], CATEGORY, "bonus-1")
    after = quota.snapshot(user["id"], CATEGORY)
    assert after["bonus_remaining"] == 4
    assert after["current"]["free_remaining"] == 0


def test_a_bonus_never_raises_the_category_limit(user):
    """"Рули: 3 из 3" must not become "7 из 7" — bonuses are held separately."""
    quota.grant(user["id"], 4, "test")
    snap = quota.snapshot(user["id"], CATEGORY)
    assert snap["current"]["free_limit"] == 3
    assert snap["bonus_remaining"] == 4


def test_exhausting_both_raises(user):
    _spend(user["id"], 3)
    assert quota.snapshot(user["id"], CATEGORY)["next_charge"] == quota.NONE
    with pytest.raises(quota.QuotaExhausted):
        quota.reserve(user["id"], CATEGORY, "over")


# ── refunds ───────────────────────────────────────────────────


def test_a_failed_generation_costs_nothing(user):
    reservation = quota.reserve(user["id"], CATEGORY, "k1")
    quota.attach_job(reservation["id"], "job-1")
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 2

    assert quota.release("job-1", "generation_failed") is True
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 3


def test_a_refund_is_not_paid_twice(user):
    reservation = quota.reserve(user["id"], CATEGORY, "k1")
    quota.attach_job(reservation["id"], "job-1")
    quota.release("job-1")

    assert quota.release("job-1") is False, "a released reservation cannot refund again"
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 3


def test_a_committed_try_is_not_refundable(user):
    reservation = quota.reserve(user["id"], CATEGORY, "k1")
    quota.attach_job(reservation["id"], "job-1")
    assert quota.commit("job-1") is True

    assert quota.release("job-1") is False
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 2


def test_stale_reservations_are_refunded(user, monkeypatch):
    """A crash between reserving and generating must not swallow a try."""
    monkeypatch.setattr(get_settings(), "reservation_ttl_minutes", -1)
    quota.reserve(user["id"], CATEGORY, "k1")
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 2

    assert quota.expire_stale() == 1
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 3


# ── idempotency and races ─────────────────────────────────────


def test_the_same_key_charges_once(user):
    """A double tap, a reload and a retry over a slow connection are all this."""
    first = quota.reserve(user["id"], CATEGORY, "same-key")
    second = quota.reserve(user["id"], CATEGORY, "same-key")

    assert first["id"] == second["id"]
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 2


def test_concurrent_reserves_cannot_oversell_the_last_try(user):
    """The reason the debit happens at reserve time rather than at completion:
    two threads must not both pass a check-then-debit."""
    _spend(user["id"], 2)  # one free try left, no bonus

    results, errors = [], []
    barrier = threading.Barrier(2)

    def attempt(i):
        barrier.wait()
        try:
            results.append(quota.reserve(user["id"], CATEGORY, f"race-{i}"))
        except quota.QuotaExhausted:
            errors.append(i)
        except Exception as exc:  # noqa: BLE001 - surfaced by the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 1, f"exactly one reservation should win, got {len(results)}"
    assert quota.snapshot(user["id"], CATEGORY)["current"]["free_remaining"] == 0


# ── the ledger ────────────────────────────────────────────────


def test_every_change_writes_a_ledger_row_with_before_and_after(user):
    quota.reserve(user["id"], CATEGORY, "k1")
    entry = quota.history(user["id"])[0]

    assert entry["transaction_type"] == quota.TX_SPEND
    assert entry["balance_type"] == quota.FREE
    assert entry["amount"] == -1

    with connect() as conn:
        row = conn.execute(
            "SELECT free_before, free_after FROM generation_transactions"
        ).fetchone()
    assert (row["free_before"], row["free_after"]) == (3, 2)


def test_a_failure_leaves_a_matched_pair_in_the_ledger(user):
    reservation = quota.reserve(user["id"], CATEGORY, "k1")
    quota.attach_job(reservation["id"], "job-1")
    quota.release("job-1", "generation_failed")

    kinds = [e["transaction_type"] for e in quota.history(user["id"])]
    assert kinds == [quota.TX_REFUND, quota.TX_SPEND]


# ── the endpoint ──────────────────────────────────────────────


def _start(client, headers):
    demo = photos.ensure_demo_photo()
    return client.post(
        "/api/generation",
        json={"photo_id": demo["photo_id"], "product_id": "amg", "selections": []},
        headers=headers,
    )


def test_low_balance_notification_fires_at_the_threshold(monkeypatch):
    """When a spend drops free tries to the warning threshold, the user is told."""
    monkeypatch.setattr(get_settings(), "free_tries_per_category", 3)
    monkeypatch.setattr(get_settings(), "low_balance_threshold", 1)
    sent = []
    monkeypatch.setattr(
        "app.routers.generation.notifications.low_balance",
        lambda uid, label, left: sent.append(("low", left)),
    )
    monkeypatch.setattr(
        "app.routers.generation.notifications.category_exhausted",
        lambda uid, label, bonus: sent.append(("exhausted", bonus)),
    )
    client = TestClient(create_app())
    headers = {"X-Telegram-Init-Data": make_init_data()}

    def _gen(key):
        return _start(client, {**headers, "Idempotency-Key": key})

    _gen("a")  # 3 -> 2, nothing
    assert sent == []
    _gen("b")  # 2 -> 1, low-balance warning
    assert sent == [("low", 1)]
    _gen("c")  # 1 -> 0, exhausted warning
    assert sent[-1][0] == "exhausted"


def test_generation_is_blocked_once_tries_run_out():
    client = TestClient(create_app())
    headers = {"X-Telegram-Init-Data": make_init_data()}

    for i in range(3):
        assert _start(client, {**headers, "Idempotency-Key": f"a{i}"}).status_code == 200

    res = _start(client, {**headers, "Idempotency-Key": "a4"})
    assert res.status_code == 409
    assert "закончились" in res.json()["detail"]


def test_a_browser_visitor_is_not_metered():
    """No durable identity means no quota — and no rows either."""
    client = TestClient(create_app())
    for i in range(5):
        assert _start(client, {"X-Session-Id": "browser"}).status_code == 200

    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0

    balance = client.get("/api/generation-balance?category_id=rul").json()
    assert balance["metered"] is False


def test_the_balance_endpoint_reports_the_category(user):
    client = TestClient(create_app())
    headers = {"X-Telegram-Init-Data": make_init_data()}
    _start(client, {**headers, "Idempotency-Key": "one"})

    body = client.get("/api/generation-balance?category_id=rul", headers=headers).json()
    assert body["metered"] is True
    assert body["current"]["free_remaining"] == 2
    assert body["next_charge"] == quota.FREE


def test_a_repeated_request_with_one_key_spends_one_try():
    client = TestClient(create_app())
    headers = {"X-Telegram-Init-Data": make_init_data(), "Idempotency-Key": "tap"}

    assert _start(client, headers).status_code == 200
    assert _start(client, headers).status_code == 200

    body = client.get(
        "/api/generation-balance?category_id=rul",
        headers={"X-Telegram-Init-Data": make_init_data()},
    ).json()
    assert body["current"]["free_remaining"] == 2, "the double tap cost one try"
