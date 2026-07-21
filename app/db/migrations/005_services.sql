-- Paid services per category (installation, rework, ...), edited in /admin at
-- runtime. The catalog stays in YAML; only these prices need changing without a
-- deploy, so only these live in the database.

CREATE TABLE IF NOT EXISTS services(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id TEXT NOT NULL,
  name        TEXT NOT NULL,
  price       INTEGER NOT NULL DEFAULT 0,
  -- Pre-selected for the customer (installation usually is).
  default_on  INTEGER NOT NULL DEFAULT 0,
  -- Deactivated services keep their history but stop being offered or charged.
  active      INTEGER NOT NULL DEFAULT 1,
  sort        INTEGER NOT NULL DEFAULT 0,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_services_cat ON services(category_id, active, sort);
