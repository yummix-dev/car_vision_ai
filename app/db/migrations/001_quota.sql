-- AI try-on quotas: users, per-category free allowances, bonus balance,
-- reservations and the ledger that every balance change must go through.

CREATE TABLE IF NOT EXISTS users(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id      INTEGER UNIQUE NOT NULL,
  -- Short readable code for the referral link. Unused until phase 2; one
  -- column now is cheaper than a migration later.
  ref_code         TEXT UNIQUE NOT NULL,
  -- The "car project": brand/model/year as confirmed on the car screen. A
  -- separate project entity would add nothing the funnel does not already have.
  car_brand        TEXT,
  car_model        TEXT,
  car_year         INTEGER,
  car_confirmed_at INTEGER,
  created_at       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_balances(
  user_id         INTEGER PRIMARY KEY REFERENCES users(id),
  bonus_remaining INTEGER NOT NULL DEFAULT 0,
  updated_at      INTEGER NOT NULL
);

-- free_limit stays at the configured default forever. Bonuses never raise it:
-- a category shows "0 из 3" with bonuses held separately, never "7 из 7".
CREATE TABLE IF NOT EXISTS user_category_allowances(
  user_id        INTEGER NOT NULL REFERENCES users(id),
  category_id    TEXT NOT NULL,
  free_limit     INTEGER NOT NULL,
  free_remaining INTEGER NOT NULL,
  last_reset_at  INTEGER,
  updated_at     INTEGER NOT NULL,
  PRIMARY KEY(user_id, category_id)
);

-- Every balance change writes a row here. The balance is never edited without
-- one, which is what makes a disputed count answerable.
CREATE TABLE IF NOT EXISTS generation_transactions(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id          INTEGER NOT NULL REFERENCES users(id),
  category_id      TEXT,
  job_id           TEXT,
  transaction_type TEXT NOT NULL,
  balance_type     TEXT,
  amount           INTEGER NOT NULL,
  free_before      INTEGER,
  free_after       INTEGER,
  bonus_before     INTEGER,
  bonus_after      INTEGER,
  source           TEXT,
  idempotency_key  TEXT UNIQUE,
  status           TEXT NOT NULL DEFAULT 'done',
  metadata         TEXT,
  created_at       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_user ON generation_transactions(user_id, id DESC);

CREATE TABLE IF NOT EXISTS generation_reservations(
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id         INTEGER NOT NULL REFERENCES users(id),
  category_id     TEXT NOT NULL,
  job_id          TEXT UNIQUE,
  balance_type    TEXT NOT NULL,
  status          TEXT NOT NULL,
  idempotency_key TEXT UNIQUE NOT NULL,
  expires_at      INTEGER NOT NULL,
  created_at      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_res_open ON generation_reservations(status, expires_at);
