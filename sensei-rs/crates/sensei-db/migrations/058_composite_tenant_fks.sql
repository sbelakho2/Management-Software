-- Same-tenant relationship integrity: when a table references users, the
-- reference must never point at a user of ANOTHER tenant. This composite
-- FK makes cross-tenant references impossible even if the application has a
-- bug. (The generic entity_store JSONB table cannot host composite FKs —
-- its PK is (tenant_id, entity_type, id) — so tenant isolation there is
-- enforced at the repository layer instead.)

-- Support the composite references.
CREATE UNIQUE INDEX IF NOT EXISTS users_tenant_id_id_unique ON users (tenant_id, id);

-- a3_reports.owner_id must belong to the SAME tenant as the report.
ALTER TABLE a3_reports
    DROP CONSTRAINT IF EXISTS a3_reports_owner_id_tenant_fk;
ALTER TABLE a3_reports
    ADD CONSTRAINT a3_reports_owner_id_tenant_fk
    FOREIGN KEY (tenant_id, owner_id)
    REFERENCES users (tenant_id, id)
    ON DELETE CASCADE;
