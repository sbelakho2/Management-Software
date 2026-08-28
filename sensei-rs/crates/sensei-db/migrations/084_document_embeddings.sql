-- Hybrid retrieval index (item 24): document embeddings for the DENSE leg
-- of retrieval. Embeddings are LOCATORS, never truth — retrieved ids are
-- hydrated through canonical tools/effective-document filters.
CREATE TABLE IF NOT EXISTS document_embeddings (
    document_type VARCHAR(100) NOT NULL,
    document_id   UUID NOT NULL,
    tenant_id     UUID NOT NULL,
    title         TEXT NOT NULL DEFAULT '',
    content_hash  TEXT NOT NULL DEFAULT '',
    embedding     vector(384),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (document_type, document_id)
);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_tenant
    ON document_embeddings (tenant_id, document_type);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_hnsw
    ON document_embeddings USING hnsw (embedding vector_cosine_ops);
