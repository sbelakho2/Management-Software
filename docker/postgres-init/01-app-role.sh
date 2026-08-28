#!/bin/bash
# RLS requires the application to connect as a NON-OWNER role: the table
# owner bypasses ordinary RLS (FORCE ROW LEVEL SECURITY now removes that
# exemption, but the app identity must still be distinct so grants and
# ownership stay clean).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_app') THEN
            CREATE ROLE sensei_app LOGIN PASSWORD '${SENSEI_APP_PASSWORD}';
        END IF;
    END
    \$\$;
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO sensei_app;
    GRANT USAGE ON SCHEMA public TO sensei_app;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sensei_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sensei_app;
EOSQL
