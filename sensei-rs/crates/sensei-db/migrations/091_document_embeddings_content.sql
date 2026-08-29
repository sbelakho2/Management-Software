-- Document embeddings reconcile (RAG golden gate discovery): the lexical
-- retrieval leg searches title + content, but the base table stores only
-- title + hash. Persist the actual content for lexical/trigram search.
ALTER TABLE document_embeddings
    ADD COLUMN IF NOT EXISTS content TEXT NOT NULL DEFAULT '';

-- Keep the upsert path in sync: content is written by the ingestion
-- helpers; the trigram index powers the lexical leg.
CREATE INDEX IF NOT EXISTS idx_document_embeddings_content_trgm
    ON document_embeddings USING GIN (content gin_trgm_ops);
