-- A way out of the frozen state. Without these, "held for review" meant
-- "taken quietly": the status was written and never read by anything.

ALTER TABLE referrals ADD COLUMN reviewed_at INTEGER;
ALTER TABLE referrals ADD COLUMN review_note TEXT;
ALTER TABLE referrals ADD COLUMN reviewed_by TEXT;
