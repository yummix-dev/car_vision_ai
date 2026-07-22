-- Language for i18n: the user's chosen language (for notifications sent outside
-- a request), and an Uzbek name for admin-entered services.

ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'ru';
ALTER TABLE services ADD COLUMN name_uz TEXT;
