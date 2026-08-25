-- Switch vector indexes from IVFFlat to HNSW
--
-- HNSW provides better recall and supports incremental inserts without
-- index rebuilds, which is important as embeddings grow. The old IVFFlat
-- indexes (created in 012_indexes_and_constraints.sql) are dropped and
-- recreated as HNSW.

DROP INDEX IF EXISTS idx_supplier_quotes_embedding;
DROP INDEX IF EXISTS idx_knowledge_packs_embedding;

CREATE INDEX idx_supplier_quotes_embedding
    ON supplier_quotes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_packs_embedding
    ON knowledge_packs USING hnsw (embedding vector_cosine_ops);
