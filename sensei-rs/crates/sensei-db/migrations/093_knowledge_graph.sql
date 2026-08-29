-- Knowledge graph (item 73): explicit relationships between operational
-- objects — Abnormality -> deviates_from -> Standard, occurred_at ->
-- WorkCenter, caused -> Downtime, contained_by -> Action,
-- investigated_in -> A3, tested_by -> Experiment, changed ->
-- StandardRevision, recurred_as -> Abnormality. Vector search alone
-- cannot reason about these structures; the graph can.
CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type   VARCHAR(50) NOT NULL,
    source_id     UUID NOT NULL,
    relation      VARCHAR(50) NOT NULL,
    target_type   VARCHAR(50) NOT NULL,
    target_id     UUID NOT NULL,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, source_type, source_id, relation, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_graph_source
    ON knowledge_graph_edges (tenant_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_graph_target
    ON knowledge_graph_edges (tenant_id, target_type, target_id);
