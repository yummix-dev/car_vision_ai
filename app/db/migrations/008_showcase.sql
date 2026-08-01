-- "Реальные сборки" — the shop's own finished installs, shown as a public feed
-- for social proof. Owner-curated in /admin (before/after photos + what was
-- done), filterable by car model on the client. Not user-generated.

CREATE TABLE IF NOT EXISTS showcase_builds (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  car_brand        TEXT    NOT NULL,
  car_model        TEXT    NOT NULL,
  car_year         INTEGER,
  category_id      TEXT,          -- the zone installed, links a "try it" CTA
  title            TEXT    NOT NULL,
  before_photo_id  TEXT    NOT NULL,
  after_photo_id   TEXT    NOT NULL,
  active           INTEGER NOT NULL DEFAULT 1,
  sort             INTEGER NOT NULL DEFAULT 0,
  created_at       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_showcase_active
  ON showcase_builds(active, created_at DESC);
