-- Employee site assignment (item 17): the agent context resolves the
-- caller's plant scope at request time instead of filling None.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS site_id UUID REFERENCES sites(id) ON DELETE SET NULL;
