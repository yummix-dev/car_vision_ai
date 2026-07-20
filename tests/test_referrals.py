"""Referrals: attribution, what does and does not qualify, caps and fraud.

Most of this file is about what must NOT pay a bonus. That is the whole point:
clicks, installs and registrations are free to manufacture, so they are worth
nothing.
"""

import time

import pytest

from app.config import get_settings
from app.db import connect, reset_for_tests
from app.models.telegram import TelegramUser
from app.services import photos, quota, referrals, users

CATEGORY = "rul"
OWN_PHOTO = "own-photo-1"


@pytest.fixture(autouse=True)
def app_db(tmp_path, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "app_db", str(tmp_path / "app.db"))
    monkeypatch.setattr(s, "quota_enabled", True)
    monkeypatch.setattr(s, "referrals_enabled", True)
    monkeypatch.setattr(s, "referral_bonus", 1)
    monkeypatch.setattr(s, "referral_monthly_limit", 10)
    monkeypatch.setattr(s, "referral_min_seconds", 0)  # speed check off by default
    monkeypatch.setattr(s, "telegram_bot_username", "Test_Umid_bot")
    monkeypatch.setattr(s, "telegram_bot_token", "")  # no notifications in tests
    reset_for_tests()
    yield


def make_user(tg_id: int, with_car: bool = True) -> dict:
    user = users.get_or_create(TelegramUser(id=tg_id, first_name=f"U{tg_id}"))
    if with_car:
        users.confirm_car(user["id"], "Chevrolet", "Malibu", 2023)
    with connect() as conn:
        return dict(conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone())


def reload(user_id: int) -> dict:
    with connect() as conn:
        return dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


def bonus_of(user_id: int) -> int:
    return quota.snapshot(user_id)["bonus_remaining"]


def qualify(invited, photo_id=OWN_PHOTO):
    return referrals.on_first_generation(invited["id"], photo_id)


# ── the link ──────────────────────────────────────────────────


def test_start_param_round_trips():
    param = referrals.start_param("ABC1234", "shr9")
    assert referrals.parse_start_param(param) == ("ABC1234", "shr9")
    assert referrals.parse_start_param(referrals.start_param("ABC1234")) == ("ABC1234", None)


def test_a_link_without_a_bot_username_is_empty(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "")
    assert referrals.link_for("ABC1234") == ""


def test_the_link_carries_the_code():
    inviter = make_user(1)
    assert f"startapp=ref_{inviter['ref_code']}" in referrals.link_for(inviter["ref_code"])


# ── attribution ───────────────────────────────────────────────


def test_a_visit_is_attributed_once(monkeypatch):
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    # A second link never reassigns credit — the first inviter keeps it.
    other = make_user(3)
    with pytest.raises(referrals.AttributionRefused):
        referrals.attribute(invited, referrals.start_param(other["ref_code"]))

    assert referrals.pending_for(invited["id"])["inviter_user_id"] == inviter["id"]


def test_self_invitation_is_refused():
    user = make_user(1)
    with pytest.raises(referrals.AttributionRefused, match="self-invite"):
        referrals.attribute(user, referrals.start_param(user["ref_code"]))


def test_an_unknown_code_is_refused():
    invited = make_user(2)
    with pytest.raises(referrals.AttributionRefused, match="unknown"):
        referrals.attribute(invited, referrals.start_param("NOSUCH1"))


def test_someone_who_already_generated_is_not_a_new_user():
    """A returning customer opening a friend's link is not a recruit."""
    inviter = make_user(1)
    invited = make_user(2)
    qualify(invited)  # their first generation, with no referral attached

    with pytest.raises(referrals.AttributionRefused, match="not a new user"):
        referrals.attribute(reload(invited["id"]), referrals.start_param(inviter["ref_code"]))


# ── what does not pay ─────────────────────────────────────────


def test_a_click_alone_pays_nothing():
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    assert bonus_of(inviter["id"]) == 0, "attribution is not a reward"


def test_the_demo_photo_does_not_qualify():
    """§8 requires the invited person's own photograph. The stock demo image is
    evidence of nothing."""
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    assert qualify(invited, photos.DEMO_PHOTO_ID) is None
    assert bonus_of(inviter["id"]) == 0


def test_an_unconfirmed_car_does_not_qualify():
    inviter = make_user(1)
    invited = make_user(2, with_car=False)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    assert qualify(invited) is None
    assert bonus_of(inviter["id"]) == 0


def test_only_the_first_generation_pays():
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    assert qualify(invited) is not None
    assert bonus_of(inviter["id"]) == 1

    # Everything the invited person does afterwards is worth nothing more.
    assert qualify(invited) is None
    assert qualify(invited) is None
    assert bonus_of(inviter["id"]) == 1


# ── what does pay ─────────────────────────────────────────────


def test_a_completed_first_try_on_pays_once():
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    reward = qualify(invited)
    assert reward == {"inviter_id": inviter["id"], "amount": 1}
    assert bonus_of(inviter["id"]) == 1

    with connect() as conn:
        row = conn.execute("SELECT * FROM referrals").fetchone()
    assert row["status"] == referrals.QUALIFIED
    assert row["reward_issued_at"] is not None


def test_the_ledger_records_the_referral_grant():
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    qualify(invited)

    entry = quota.history(inviter["id"])[0]
    assert entry["transaction_type"] == quota.TX_GRANT
    assert entry["source"] == "referral"
    assert entry["amount"] == 1


def test_arriving_through_a_shared_result_pays_the_same_single_bonus():
    """§11: one new person is worth one bonus, whichever link they came by."""
    inviter, invited = make_user(1), make_user(2)
    link = referrals.create_share_link(inviter["id"], job_id="job-1")

    referrals.attribute(
        invited, referrals.start_param(inviter["ref_code"], link["public_code"])
    )
    qualify(invited)

    assert bonus_of(inviter["id"]) == 1
    with connect() as conn:
        share = conn.execute("SELECT * FROM share_links").fetchone()
        ref = conn.execute("SELECT * FROM referrals").fetchone()
    assert ref["source_type"] == referrals.SOURCE_SHARE
    assert share["qualified_users_count"] == 1
    assert share["opens_count"] == 1


# ── limits and fraud ──────────────────────────────────────────


def test_the_monthly_cap_stops_paying(monkeypatch):
    monkeypatch.setattr(get_settings(), "referral_monthly_limit", 2)
    inviter = make_user(1)

    for tg_id in (10, 11, 12):
        invited = make_user(tg_id)
        referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
        qualify(invited)

    assert bonus_of(inviter["id"]) == 2, "the third invite is over the cap"
    with connect() as conn:
        capped = conn.execute(
            "SELECT COUNT(*) c FROM referrals WHERE status=?", (referrals.CAPPED,)
        ).fetchone()["c"]
    assert capped == 1


def test_qualifying_within_seconds_is_held_for_review(monkeypatch):
    monkeypatch.setattr(get_settings(), "referral_min_seconds", 300)
    monkeypatch.setattr(get_settings(), "referral_fraud_threshold", 2)

    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    assert qualify(invited) is None
    assert bonus_of(inviter["id"]) == 0

    with connect() as conn:
        row = conn.execute("SELECT * FROM referrals").fetchone()
    # Frozen, not rejected: a weak signal is not proof, and a wrongly refused
    # bonus is invisible to everyone.
    assert row["status"] == referrals.FROZEN
    assert row["fraud_score"] >= 2
    assert "qualified in" in row["fraud_reasons"]


def test_one_photograph_across_accounts_is_held_for_review(monkeypatch):
    """The actual farming pattern: many accounts, one picture."""
    monkeypatch.setattr(get_settings(), "referral_fraud_threshold", 3)
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))

    now = int(time.time())
    with connect(immediate=True) as conn:
        for photo_id, user_id in ((OWN_PHOTO, invited["id"]), ("other", inviter["id"])):
            conn.execute(
                "INSERT INTO photo_uploads(photo_id, user_id, sha256, created_at)"
                " VALUES(?,?,?,?)",
                (photo_id, user_id, "same-hash", now),
            )

    assert qualify(invited) is None
    with connect() as conn:
        row = conn.execute("SELECT * FROM referrals").fetchone()
    assert row["status"] == referrals.FROZEN
    assert "reused" in row["fraud_reasons"]


def test_many_invites_from_one_address_are_held_for_review(monkeypatch):
    monkeypatch.setattr(get_settings(), "referral_fraud_threshold", 2)
    inviter = make_user(1)

    first = make_user(10)
    referrals.attribute(first, referrals.start_param(inviter["ref_code"]), ip="1.2.3.4")
    qualify(first)

    second = make_user(11)
    referrals.attribute(second, referrals.start_param(inviter["ref_code"]), ip="1.2.3.4")
    assert qualify(second) is None

    assert bonus_of(inviter["id"]) == 1, "only the first one paid"


def test_disabling_referrals_stops_all_payment(monkeypatch):
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    monkeypatch.setattr(get_settings(), "referrals_enabled", False)

    assert qualify(invited) is None
    assert bonus_of(inviter["id"]) == 0


# ── the way out of the frozen state ───────────────────────────


def _freeze(monkeypatch) -> tuple[dict, dict]:
    """Drive a referral into review with a real signal, not a hand-set status."""
    monkeypatch.setattr(get_settings(), "referral_min_seconds", 300)
    monkeypatch.setattr(get_settings(), "referral_fraud_threshold", 2)
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    assert qualify(invited) is None
    return inviter, invited


def _frozen_id() -> int:
    held = referrals.list_frozen()
    assert len(held) == 1
    return held[0]["id"]


def test_frozen_referrals_are_listed_with_their_reasons(monkeypatch):
    _freeze(monkeypatch)
    held = referrals.list_frozen()[0]
    assert held["fraud_score"] >= 2
    assert any("qualified in" in r for r in held["reasons"])
    # A reviewer needs to see both sides to judge anything.
    assert held["inviter_telegram_id"] == 1
    assert held["invited_telegram_id"] == 2


def test_approving_pays_the_held_bonus(monkeypatch):
    inviter, _ = _freeze(monkeypatch)
    assert bonus_of(inviter["id"]) == 0

    assert referrals.approve(_frozen_id(), note="проверил") is True
    assert bonus_of(inviter["id"]) == 1

    with connect() as conn:
        row = conn.execute("SELECT * FROM referrals").fetchone()
    assert row["status"] == referrals.QUALIFIED
    assert row["reward_issued_at"] is not None
    assert row["review_note"] == "проверил"


def test_approving_twice_does_not_pay_twice(monkeypatch):
    """The ledger's unique idempotency key is the real guarantee, not the
    status check above it."""
    inviter, _ = _freeze(monkeypatch)
    referral_id = _frozen_id()

    assert referrals.approve(referral_id) is True
    assert referrals.approve(referral_id) is False, "no longer frozen"
    assert bonus_of(inviter["id"]) == 1


def test_an_approved_referral_cannot_also_pay_automatically(monkeypatch):
    """Manual and automatic payment share one key, so only one can land."""
    inviter, invited = _freeze(monkeypatch)
    referrals.approve(_frozen_id())

    # Re-open the door the automatic path uses and push it again.
    with connect(immediate=True) as conn:
        conn.execute("UPDATE users SET first_generation_at=NULL WHERE id=?", (invited["id"],))
        conn.execute("UPDATE referrals SET status=?", (referrals.PENDING,))
    monkeypatch.setattr(get_settings(), "referral_min_seconds", 0)

    with pytest.raises(Exception):
        qualify(invited)
    assert bonus_of(inviter["id"]) == 1


def test_rejecting_pays_nothing(monkeypatch):
    inviter, _ = _freeze(monkeypatch)
    assert referrals.reject(_frozen_id(), note="накрутка") is True
    assert bonus_of(inviter["id"]) == 0

    with connect() as conn:
        row = conn.execute("SELECT * FROM referrals").fetchone()
    assert row["status"] == referrals.REJECTED
    assert row["reviewed_at"] is not None


def test_reviewing_something_not_frozen_does_nothing(monkeypatch):
    inviter, invited = make_user(1), make_user(2)
    referrals.attribute(invited, referrals.start_param(inviter["ref_code"]))
    qualify(invited)  # paid automatically, status qualified

    with connect() as conn:
        referral_id = conn.execute("SELECT id FROM referrals").fetchone()["id"]

    assert referrals.approve(referral_id) is False
    assert referrals.reject(referral_id) is False
    assert bonus_of(inviter["id"]) == 1


def test_approval_overrides_the_monthly_cap(monkeypatch):
    """Otherwise a reviewer's decision would mean nothing in the month it
    matters most."""
    monkeypatch.setattr(get_settings(), "referral_monthly_limit", 0)
    inviter, _ = _freeze(monkeypatch)

    assert referrals.approve(_frozen_id()) is True
    assert bonus_of(inviter["id"]) == 1


def test_a_manual_decision_is_distinguishable_in_the_ledger(monkeypatch):
    inviter, _ = _freeze(monkeypatch)
    referrals.approve(_frozen_id())

    entry = quota.history(inviter["id"])[0]
    assert entry["source"] == "referral_approved", "manual and automatic must differ"


# ── reporting ─────────────────────────────────────────────────


def test_stats_report_invited_and_qualified_separately():
    inviter = make_user(1)
    clicked = make_user(10)
    referrals.attribute(clicked, referrals.start_param(inviter["ref_code"]))

    generated = make_user(11)
    referrals.attribute(generated, referrals.start_param(inviter["ref_code"]))
    qualify(generated)

    stats = referrals.stats(reload(inviter["id"]))
    assert stats["invited"] == 2
    assert stats["qualified"] == 1, "a click is counted but never as qualified"
    assert stats["bonus_earned"] == 1
    assert stats["monthly_remaining"] == 9
