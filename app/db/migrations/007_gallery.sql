-- "Мои примерки" — a Telegram user's own saved AI renders, so they can return
-- to them after the media sweep would otherwise reclaim the files. One row per
-- generation job (UNIQUE job_id makes the auto-save idempotent under polling).

CREATE TABLE IF NOT EXISTS saved_generations (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id          INTEGER NOT NULL REFERENCES users(id),
  job_id           TEXT    NOT NULL UNIQUE,
  product_id       TEXT    NOT NULL,
  category_id      TEXT    NOT NULL,
  before_photo_id  TEXT    NOT NULL,
  after_photo_id   TEXT    NOT NULL,
  car_label        TEXT,
  created_at       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_saved_gen_user
  ON saved_generations(user_id, created_at DESC);
