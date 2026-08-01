-- Orders — introduced for payments. Until now the shop had no order store on
-- purpose ("the manager's chat is the system of record"): a booking was
-- delivered, never persisted. Charging money needs a durable record to
-- reconcile a payment against, so the transaction — code, amount, method,
-- status — lives here. Customer PII (name, phone) still does NOT: it stays in
-- the manager's chat, exactly as before.

CREATE TABLE IF NOT EXISTS orders (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  order_code      TEXT    NOT NULL UNIQUE,   -- the booking id shown to everyone
  telegram_id     INTEGER,                   -- payer, for notification / reconcile
  car_label       TEXT,
  positions       INTEGER NOT NULL,
  total           INTEGER NOT NULL,
  payment_method  TEXT    NOT NULL,          -- 'cash' | 'telegram' | 'uzum'
  payment_status  TEXT    NOT NULL,          -- 'manual' | 'pending' | 'paid' | 'failed'
  provider_ref    TEXT,                      -- invoice / installment id from the provider
  created_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(payment_status, created_at DESC);
