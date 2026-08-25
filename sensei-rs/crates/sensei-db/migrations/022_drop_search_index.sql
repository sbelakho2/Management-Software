-- Drop the obsolete search_index table
--
-- The search_index table became unused after the search unification: the
-- search_all() function (migration 016) queries the source tables directly.
-- Drop it defensively; it never existed in some environments because the
-- table was only ever populated by application code, never by a migration.
-- Any code that still writes to it will fail loudly at the query layer.

DROP TABLE IF EXISTS search_index;
