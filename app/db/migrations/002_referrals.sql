-- Referrals, share links, and the upload fingerprints one fraud check needs.

-- When this user first completed a try-on. Attribution is refused once it is
-- set: somebody who has already generated is not a new user, whatever link
-- they open next.
ALTER TABLE users ADD COLUMN first_generation_at INTEGER;

CREATE TABLE IF NOT EXISTS referrals(
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  inviter_user_id  INTEGER NOT NULL REFERENCES users(id),
  -- One row per invited user, enforced by the database: a person cannot be
  -- claimed twice, and the inviter can never be changed afterwards.
  invited_user_id  INTEGER NOT NULL UNIQUE REFERENCES users(id),
  referral_code    TEXT NOT NULL,
  source_type      TEXT NOT NULL,      -- link | share
  source_share_id  INTEGER REFERENCES share_links(id),
  source_channel   TEXT,
  first_opened_at  INTEGER NOT NULL,
  qualified_at     INTEGER,
  reward_issued_at INTEGER,
  status           TEXT NOT NULL,      -- pending|qualified|capped|frozen|rejected
  fraud_score      INTEGER NOT NULL DEFAULT 0,
  fraud_reasons    TEXT,
  invited_ip       TEXT,
  metadata         TEXT
);

CREATE INDEX IF NOT EXISTS idx_ref_inviter ON referrals(inviter_user_id, reward_issued_at);

CREATE TABLE IF NOT EXISTS share_links(
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id         INTEGER NOT NULL REFERENCES users(id),
  public_code           TEXT UNIQUE NOT NULL,
  job_id                TEXT,
  result_photo_id       TEXT,
  product_id            TEXT,
  category_id           TEXT,
  car_label             TEXT,
  share_type            TEXT NOT NULL DEFAULT 'result',
  channel               TEXT,
  opens_count           INTEGER NOT NULL DEFAULT 0,
  qualified_users_count INTEGER NOT NULL DEFAULT 0,
  status                TEXT NOT NULL DEFAULT 'active',
  created_at            INTEGER NOT NULL
);

-- Upload fingerprints. The one fraud signal that catches the actual farming
-- pattern: many accounts, one photograph.
CREATE TABLE IF NOT EXISTS photo_uploads(
  photo_id   TEXT PRIMARY KEY,
  user_id    INTEGER REFERENCES users(id),
  sha256     TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_uploads_hash ON photo_uploads(sha256);
