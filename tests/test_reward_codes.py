"""One-time codes and the free-allowance restore that a purchase triggers.

Activation is the only place a customer can increase their own balance, so most
of this file is about the ways that must not be exploitable.
"""

import threading
import time

import pytest

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.telegram import TelegramUser
from app.services import quota, reward_codes, users

CATEGORY = "rul"


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(s, "quota_enabled", True)
    monkeypatch.setattr(s, "free_tries_per_category", 3)
    monkeypatch.setattr(s, "visit_bonus", 3)
    monkeypatch.setattr(s, "purchase_bonus", 3)
    monkeypatch.setattr(s, "telegram_bot_token", "")
    reset_for_tests()
    yield


@pytest.fixture
def user():
    return users.get_or_create(TelegramUser(id=7001, first_name="U"))


def snap(user_id, category=CATEGORY):
    return quota.snapshot(user_id, category)


def spend(user_id, n, category=CATEGORY, prefix="s"):
    for i in range(n):
        quota.reserve(user_id, category, f"{prefix}-{category}-{i}")


# ── visit codes ───────────────────────────────────────────────


def test_a_visit_code_grants_bonuses(user):
    code = reward_codes.create(reward_codes.VISIT)
    result = reward_codes.activate(user["id"], code["code"])

    assert result["bonus_amount"] == 3
    assert result["restored_free"] == 0, "a visit does not restore free tries"
    assert snap(user["id"])["bonus_remaining"] == 3


def test_a_code_is_accepted_in_any_case_and_with_spaces(user):
    code = reward_codes.create(reward_codes.VISIT)
    reward_codes.activate(user["id"], f"  {code['code'].lower()}  ")
    assert snap(user["id"])["bonus_remaining"] == 3


# ── purchase codes ────────────────────────────────────────────


def test_a_purchase_restores_every_category_and_adds_bonuses(user):
    spend(user["id"], 3, "rul")
    spend(user["id"], 1, "audio")
    assert snap(user["id"], "rul")["current"]["free_remaining"] == 0
    assert snap(user["id"], "audio")["current"]["free_remaining"] == 2

    code = reward_codes.create(reward_codes.PURCHASE)
    result = reward_codes.activate(user["id"], code["code"])

    assert snap(user["id"], "rul")["current"]["free_remaining"] == 3
    assert snap(user["id"], "audio")["current"]["free_remaining"] == 3
    assert result["restored_free"] == 4  # 3 + 1
    assert snap(user["id"])["bonus_remaining"] == 3, "bonuses are separate"


def test_restoring_a_full_category_does_not_overfill_it(user):
    """"3 из 3" must stay "3 из 3", never become "6 из 3"."""
    spend(user["id"], 1)
    quota.restore_free(user["id"], "test")
    quota.restore_free(user["id"], "test")

    current = snap(user["id"])["current"]
    assert current == {"free_limit": 3, "free_remaining": 3}


def test_restore_writes_one_ledger_row_per_category(user):
    spend(user["id"], 2, "rul")
    spend(user["id"], 1, "audio")
    quota.restore_free(user["id"], "code_purchase")

    restores = [
        e for e in quota.history(user["id"], limit=50)
        if e["transaction_type"] == quota.TX_RESTORE
    ]
    assert {e["category_id"] for e in restores} == {"rul", "audio"}
    assert sum(e["amount"] for e in restores) == 3


def test_restore_ignores_categories_never_used(user):
    """Untouched categories are already full; inventing rows for them would
    only invent history."""
    spend(user["id"], 1, "rul")
    quota.restore_free(user["id"], "test")

    with connect() as conn:
        rows = conn.execute(
            "SELECT category_id FROM user_category_allowances WHERE user_id=?",
            (user["id"],),
        ).fetchall()
    assert {r["category_id"] for r in rows} == {"rul"}


# ── what must not work ────────────────────────────────────────


def test_an_unknown_code_is_refused(user):
    with pytest.raises(reward_codes.CodeError, match=reward_codes.NOT_FOUND):
        reward_codes.activate(user["id"], "NOSUCH99")


def test_the_same_user_cannot_redeem_twice(user):
    code = reward_codes.create(reward_codes.VISIT, max_activations=5)
    reward_codes.activate(user["id"], code["code"])

    with pytest.raises(reward_codes.CodeError, match=reward_codes.ALREADY_USED):
        reward_codes.activate(user["id"], code["code"])
    assert snap(user["id"])["bonus_remaining"] == 3


def test_a_single_use_code_is_spent_by_the_first_user(user):
    other = users.get_or_create(TelegramUser(id=7002, first_name="O"))
    code = reward_codes.create(reward_codes.VISIT)
    reward_codes.activate(user["id"], code["code"])

    with pytest.raises(reward_codes.CodeError, match=reward_codes.ALREADY_USED):
        reward_codes.activate(other["id"], code["code"])


def test_an_expired_code_is_refused(user):
    code = reward_codes.create(reward_codes.VISIT, valid_days=1)
    with connect(immediate=True) as conn:
        conn.execute(
            "UPDATE reward_codes SET expires_at=? WHERE id=?",
            (int(time.time()) - 10, code["id"]),
        )

    with pytest.raises(reward_codes.CodeError, match=reward_codes.IS_EXPIRED):
        reward_codes.activate(user["id"], code["code"])
    assert snap(user["id"])["bonus_remaining"] == 0


def test_a_code_assigned_to_someone_else_is_refused(user):
    other = users.get_or_create(TelegramUser(id=7002, first_name="O"))
    code = reward_codes.create(reward_codes.VISIT, assigned_user_id=other["id"])

    with pytest.raises(reward_codes.CodeError, match=reward_codes.WRONG_USER):
        reward_codes.activate(user["id"], code["code"])


def test_a_cancelled_code_stops_working(user):
    code = reward_codes.create(reward_codes.VISIT)
    assert reward_codes.cancel(code["id"]) is True

    with pytest.raises(reward_codes.CodeError):
        reward_codes.activate(user["id"], code["code"])


def test_concurrent_activation_cannot_oversubscribe_a_code():
    """Two people, one remaining slot — exactly one may take it."""
    code = reward_codes.create(reward_codes.VISIT, max_activations=1)
    a = users.get_or_create(TelegramUser(id=7101, first_name="A"))
    b = users.get_or_create(TelegramUser(id=7102, first_name="B"))

    ok, refused = [], []
    barrier = threading.Barrier(2)

    def attempt(uid):
        barrier.wait()
        try:
            reward_codes.activate(uid, code["code"])
            ok.append(uid)
        except reward_codes.CodeError:
            refused.append(uid)

    threads = [threading.Thread(target=attempt, args=(u["id"],)) for u in (a, b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ok) == 1, f"exactly one activation should win, got {len(ok)}"
    assert len(refused) == 1


def test_activation_is_recorded_in_the_ledger(user):
    code = reward_codes.create(reward_codes.VISIT)
    reward_codes.activate(user["id"], code["code"])

    entry = quota.history(user["id"])[0]
    assert entry["transaction_type"] == quota.TX_GRANT
    assert entry["source"] == "code_visit"
    assert entry["amount"] == 3
