-- One-time codes (visit, purchase, manual) and their activations.

CREATE TABLE IF NOT EXISTS reward_codes(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  code             TEXT UNIQUE NOT NULL,
  reward_type      TEXT NOT NULL,      -- visit | purchase | manual
  bonus_amount     INTEGER NOT NULL DEFAULT 0,
  -- Purchase codes restore every category to full as well as granting bonuses.
  restores_free    INTEGER NOT NULL DEFAULT 0,
  expires_at       INTEGER,
  max_activations  INTEGER NOT NULL DEFAULT 1,
  activation_count INTEGER NOT NULL DEFAULT 0,
  -- When set, only this user may activate the code.
  assigned_user_id INTEGER REFERENCES users(id),
  related_order_id TEXT,
  status           TEXT NOT NULL DEFAULT 'active',  -- active|used|expired|cancelled
  note             TEXT,
  created_by       TEXT,
  created_at       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reward_code_activations(
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  code_id         INTEGER NOT NULL REFERENCES reward_codes(id),
  user_id         INTEGER NOT NULL REFERENCES users(id),
  activated_at    INTEGER NOT NULL,
  -- One activation per (code, user), enforced rather than checked: a double
  -- tap on "Активировать" must not grant twice.
  idempotency_key TEXT UNIQUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_activations_user ON reward_code_activations(user_id);
