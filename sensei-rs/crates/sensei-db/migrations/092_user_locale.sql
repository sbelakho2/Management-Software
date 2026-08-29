-- Employee locale (item 59): the agent context and the UI language come
-- from the EMPLOYEE PROFILE, never a hardcoded "en" — a French operator
-- must receive French coaching.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS locale VARCHAR(10) NOT NULL DEFAULT 'en'
        CHECK (locale IN ('en', 'fr', 'ar', 'de', 'es'));
