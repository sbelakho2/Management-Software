-- Field-level source-of-truth matrix (item 2): field ownership, not just
-- entity ownership. With StarzERP and CRM remaining operational after
-- Sensei deployment, EVERY field must have exactly one owner, otherwise
-- "last write wins" becomes accidental policy.
--
-- mode:
--   'source_wins'  — the legacy system owns the field; the importer may
--                    update it from the source payload.
--   'sensei_wins'  — Sensei owns the field; the importer must NEVER
--                    overwrite it (an import attempt is skipped/rejected).
--   'manual'       — cutover-dependent; the importer records the source
--                    value as a candidate but does not write it.
--
-- The importer checks this matrix before every field write; a
-- 'sensei_wins' field is never clobbered by a re-import.

CREATE TABLE IF NOT EXISTS integration_field_authority (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sensei_entity   VARCHAR(50) NOT NULL,   -- product, account, contact, ...
    field_name      VARCHAR(100) NOT NULL,
    authority_system VARCHAR(50) NOT NULL,  -- starzerp | crm_v2 | sensei
    mode            VARCHAR(20) NOT NULL DEFAULT 'source_wins'
                    CHECK (mode IN ('source_wins', 'sensei_wins', 'manual')),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, sensei_entity, field_name)
);

-- ── Seed the audit's field-ownership matrix ─────────────────────────────
INSERT INTO integration_field_authority (tenant_id, sensei_entity, field_name, authority_system, mode, note)
SELECT t.id, v.entity, v.field, v.system, v.mode, v.note
FROM tenants t,
     (VALUES
        ('product', 'product_number',  'starzerp', 'source_wins', 'SKU originates in StarzERP'),
        ('product', 'name',            'starzerp', 'source_wins', 'description is a legacy master-data fact'),
        ('product', 'standard_cost',   'starzerp', 'source_wins', 'cost originates in the ERP cost rollup'),
        ('product', 'selling_price',   'starzerp', 'source_wins', 'price list lives in the ERP'),
        ('product', 'unit_of_measure', 'starzerp', 'source_wins', 'UOM is a master-data fact'),
        ('product', 'min_stock_level', 'sensei',   'sensei_wins', 'planning policy is Sensei-owned (TPS)'),
        ('product', 'max_stock_level', 'sensei',   'sensei_wins', 'planning policy is Sensei-owned (TPS)'),
        ('account', 'name',            'crm_v2',   'source_wins', 'customer name originates in CRM'),
        ('account', 'email',           'crm_v2',   'source_wins', 'contact facts originate in CRM'),
        ('account', 'phone',           'crm_v2',   'source_wins', 'contact facts originate in CRM'),
        ('account', 'account_type',    'sensei',   'sensei_wins', 'Sensei classifies the account role'),
        ('account', 'status',          'sensei',   'sensei_wins', 'lifecycle state is Sensei-owned'),
        ('opportunity', 'stage',       'crm_v2',   'source_wins', 'pipeline stage maps from CRM deliberately'),
        ('opportunity', 'amount',      'sensei',   'manual',      'cutover-dependent: CRM estimate vs Sensei value'),
        ('supplier', 'name',           'starzerp', 'source_wins', 'supplier master data lives in the ERP'),
        ('supplier', 'status',         'sensei',   'sensei_wins', 'qualification state is Sensei-owned'),
        ('sales_order', 'status',      'starzerp', 'source_wins', 'order lifecycle is the ERP contract'),
        ('sales_order', 'delivery_date','starzerp', 'source_wins', 'customer-requested date is a contract fact'),
        ('stock_move', 'quantity',     'starzerp', 'source_wins', 'the movement fact is historical truth'),
        ('stock_move', 'move_type',    'starzerp', 'source_wins', 'the movement fact is historical truth')
     ) AS v(entity, field, system, mode, note)
WHERE NOT EXISTS (
    SELECT 1 FROM integration_field_authority fa
    WHERE fa.tenant_id = t.id AND fa.sensei_entity = v.entity AND fa.field_name = v.field
);

-- Fail-closed RLS (item 26).
ALTER TABLE integration_field_authority ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_field_authority FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON integration_field_authority
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
