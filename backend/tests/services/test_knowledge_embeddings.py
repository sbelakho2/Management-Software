"""Tests for knowledge embeddings and semantic search."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import select

from sensei.models.knowledge_pack import (
    KnowledgeDocument,
    KnowledgeChunk,
    LicenseType,
    ContentFormat,
    TaxonomyTag,
)
from sensei.services.knowledge_embeddings import (
    EmbeddingService,
    KnowledgeEmbeddingService,
    SemanticSearchService,
)


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model."""
    with patch("sensei.services.knowledge_embeddings.SentenceTransformer") as mock:
        model = Mock()
        # Return fixed embeddings for testing
        model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4] * 96)  # 384 dimensions
        mock.return_value = model
        yield mock


@pytest.fixture
def embedding_service(mock_sentence_transformer):
    """EmbeddingService with mocked model."""
    return EmbeddingService(model_name="all-MiniLM-L6-v2")


class TestEmbeddingService:
    """Test EmbeddingService."""
    
    def test_init(self, embedding_service):
        """Should initialize with model name."""
        assert embedding_service.model_name == "all-MiniLM-L6-v2"
        assert embedding_service.embedding_dim == 384
    
    def test_get_model_dimension(self):
        """Should return correct dimensions for known models."""
        assert EmbeddingService._get_model_dimension("all-MiniLM-L6-v2") == 384
        assert EmbeddingService._get_model_dimension("all-mpnet-base-v2") == 768
        assert EmbeddingService._get_model_dimension("unknown-model") == 384  # default
    
    def test_lazy_load_model(self, embedding_service):
        """Should lazy load model on first access."""
        assert embedding_service._model is None
        model = embedding_service.model
        assert model is not None
        assert embedding_service._model is not None
    
    def test_encode_single_text(self, embedding_service):
        """Should encode single text."""
        text = "This is a test document about TPS."
        embedding = embedding_service.encode(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
    
    def test_encode_multiple_texts(self, embedding_service):
        """Should encode multiple texts."""
        texts = ["First document", "Second document", "Third document"]
        
        # Mock encode to return correct shape for batch
        embedding_service._model.encode.return_value = np.random.rand(3, 384)
        
        embeddings = embedding_service.encode(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
    
    def test_encode_batch(self, embedding_service):
        """Should encode batch with progress bar."""
        texts = ["Doc 1", "Doc 2", "Doc 3", "Doc 4", "Doc 5"]
        
        # Mock encode to return correct shape
        embedding_service._model.encode.return_value = np.random.rand(5, 384)
        
        embeddings = embedding_service.encode_batch(texts, batch_size=2)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (5, 384)
        
        # Verify batch_size and show_progress_bar were passed
        call_kwargs = embedding_service._model.encode.call_args[1]
        assert call_kwargs["batch_size"] == 2
        assert call_kwargs["show_progress_bar"] is True


class TestKnowledgeEmbeddingService:
    """Test KnowledgeEmbeddingService."""
    
    @pytest.mark.asyncio
    async def test_embed_chunk(self, embedding_service, async_session):
        """Should generate and store embedding for chunk."""
        # Create document and chunk
        document = KnowledgeDocument(
            title="Test Doc",
            source_url="https://example.com",
            license_type=LicenseType.CC0,
            original_format=ContentFormat.HTML,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="This is test content about lean manufacturing.",
            chunk_index=0,
        )
        async_session.add(chunk)
        await async_session.commit()
        
        # Embed chunk
        service = KnowledgeEmbeddingService(embedding_service)
        await service.embed_chunk(chunk, async_session)
        
        # Verify embedding was stored
        await async_session.refresh(chunk)
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 384
    
    @pytest.mark.asyncio
    async def test_embed_document_chunks(self, embedding_service, async_session):
        """Should embed all chunks of a document."""
        # Create document with multiple chunks
        document = KnowledgeDocument(
            title="Test Doc",
            source_url="https://example.com",
            license_type=LicenseType.CC_BY,
            original_format=ContentFormat.MARKDOWN,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                chunk_text=f"Chunk {i} content",
                chunk_index=i,
            )
            for i in range(3)
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        # Mock encode_batch to return correct shape
        embedding_service._model.encode.return_value = np.random.rand(3, 384)
        
        # Embed document chunks
        service = KnowledgeEmbeddingService(embedding_service)
        count = await service.embed_document_chunks(document.id, async_session)
        
        assert count == 3
        
        # Verify all chunks have embeddings
        for chunk in chunks:
            await async_session.refresh(chunk)
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 384
    
    @pytest.mark.asyncio
    async def test_embed_document_chunks_skip_already_embedded(
        self, embedding_service, async_session
    ):
        """Should skip chunks that already have embeddings."""
        # Create document
        document = KnowledgeDocument(
            title="Test Doc",
            source_url="https://example.com",
            license_type=LicenseType.MIT,
            original_format=ContentFormat.PDF,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        # Create chunk with existing embedding
        chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="Already embedded",
            chunk_index=0,
            embedding=[0.1] * 384,
        )
        async_session.add(chunk)
        await async_session.commit()
        
        # Try to embed
        service = KnowledgeEmbeddingService(embedding_service)
        count = await service.embed_document_chunks(document.id, async_session)
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_embed_all_unembedded(self, embedding_service, async_session):
        """Should embed all chunks without embeddings across all documents."""
        # Create multiple documents with chunks
        doc1 = KnowledgeDocument(
            title="Doc 1",
            source_url="https://example.com/1",
            license_type=LicenseType.CC_BY_SA,
            original_format=ContentFormat.HTML,
            raw_content="test1",
            normalized_content="test1",
        )
        doc2 = KnowledgeDocument(
            title="Doc 2",
            source_url="https://example.com/2",
            license_type=LicenseType.APACHE_2,
            original_format=ContentFormat.MARKDOWN,
            raw_content="test2",
            normalized_content="test2",
        )
        async_session.add_all([doc1, doc2])
        await async_session.commit()
        
        chunks = [
            KnowledgeChunk(document_id=doc1.id, chunk_text="Chunk 1", chunk_index=0),
            KnowledgeChunk(document_id=doc1.id, chunk_text="Chunk 2", chunk_index=1),
            KnowledgeChunk(document_id=doc2.id, chunk_text="Chunk 3", chunk_index=0),
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        # Mock encode_batch
        embedding_service._model.encode.return_value = np.random.rand(3, 384)
        
        # Embed all
        service = KnowledgeEmbeddingService(embedding_service)
        count = await service.embed_all_unembedded(async_session)
        
        assert count == 3
        
        # Verify all chunks have embeddings
        for chunk in chunks:
            await async_session.refresh(chunk)
            assert chunk.embedding is not None


class TestSemanticSearchService:
    """Test SemanticSearchService."""
    
    @pytest.mark.asyncio
    async def test_search(self, embedding_service, async_session):
        """Should perform semantic search."""
        # Create document with embedded chunks
        document = KnowledgeDocument(
            title="TPS Guide",
            author="Toyota",
            source_url="https://example.com/tps",
            license_type=LicenseType.CC_BY,
            original_format=ContentFormat.HTML,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        # Create chunks with embeddings (similar to query)
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="Just-in-time production minimizes inventory.",
                chunk_index=0,
                embedding=[0.9, 0.1, 0.1, 0.1] * 96,  # Similar to query
                tags=[TaxonomyTag.TPS.value],
                quality_score=0.95,
            ),
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="Jidoka enables autonomous defect detection.",
                chunk_index=1,
                embedding=[0.1, 0.9, 0.1, 0.1] * 96,  # Different from query
                tags=[TaxonomyTag.TPS.value],
                quality_score=0.90,
            ),
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        # Mock query embedding (similar to first chunk)
        embedding_service._model.encode.return_value = np.array([0.9, 0.1, 0.1, 0.1] * 96)
        
        # Search
        service = SemanticSearchService(embedding_service)
        results = await service.search(
            query="just in time inventory",
            session=async_session,
            limit=10,
            min_similarity=0.5,
        )
        
        # Should return chunks sorted by similarity
        assert len(results) >= 1
        chunk, similarity = results[0]
        assert chunk.chunk_text == "Just-in-time production minimizes inventory."
        assert similarity > 0.5
    
    @pytest.mark.asyncio
    async def test_search_with_tag_filter(self, embedding_service, async_session):
        """Should filter search results by taxonomy tags."""
        # Create document with chunks
        document = KnowledgeDocument(
            title="Lean Guide",
            source_url="https://example.com/lean",
            license_type=LicenseType.MIT,
            original_format=ContentFormat.MARKDOWN,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="TPS content",
                chunk_index=0,
                embedding=[0.9, 0.1] * 192,
                tags=[TaxonomyTag.TPS.value],
            ),
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="PDCA content",
                chunk_index=1,
                embedding=[0.9, 0.1] * 192,
                tags=[TaxonomyTag.PDCA.value],
            ),
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        # Mock query embedding
        embedding_service._model.encode.return_value = np.array([0.9, 0.1] * 192)
        
        # Search with tag filter
        service = SemanticSearchService(embedding_service)
        results = await service.search(
            query="continuous improvement",
            session=async_session,
            limit=10,
            min_similarity=0.0,
            filter_tags=[TaxonomyTag.PDCA.value],
        )
        
        # Should only return PDCA tagged chunk
        assert len(results) == 1
        chunk, _ = results[0]
        assert TaxonomyTag.PDCA.value in chunk.tags
    
    @pytest.mark.asyncio
    async def test_search_with_context(self, embedding_service, async_session):
        """Should return enriched search results with document context."""
        # Create document and chunk
        document = KnowledgeDocument(
            title="Kata Guide",
            author="Mike Rother",
            source_url="https://example.com/kata",
            license_type=LicenseType.CC_BY_SA,
            original_format=ContentFormat.PDF,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="The improvement kata provides a structured approach.",
            chunk_index=0,
            heading="Improvement Kata",
            section_path=["Introduction", "Improvement Kata"],
            embedding=[0.8, 0.2] * 192,
            tags=[TaxonomyTag.KATA.value],
            quality_score=0.95,
            citation="Test citation",
        )
        async_session.add(chunk)
        await async_session.commit()
        
        # Mock query embedding
        embedding_service._model.encode.return_value = np.array([0.8, 0.2] * 192)
        
        # Search with context
        service = SemanticSearchService(embedding_service)
        results = await service.search_with_context(
            query="kata approach",
            session=async_session,
            limit=5,
            min_similarity=0.5,
        )
        
        assert len(results) >= 1
        result = results[0]
        
        # Verify enriched fields
        assert result["chunk_text"] == chunk.chunk_text
        assert result["document_title"] == "Kata Guide"
        assert result["document_author"] == "Mike Rother"
        assert result["source_url"] == "https://example.com/kata"
        assert result["license_type"] == "cc_by_sa"
        assert result["heading"] == "Improvement Kata"
        assert result["section_path"] == ["Introduction", "Improvement Kata"]
        assert result["tags"] == [TaxonomyTag.KATA.value]
        assert result["quality_score"] == 0.95
        assert result["citation"] == "Test citation"
        assert "similarity" in result
    
    @pytest.mark.asyncio
    async def test_get_related_chunks(self, embedding_service, async_session):
        """Should find chunks similar to a given chunk."""
        # Create document with multiple chunks
        document = KnowledgeDocument(
            title="Quality Guide",
            source_url="https://example.com/quality",
            license_type=LicenseType.PUBLIC_DOMAIN,
            original_format=ContentFormat.PLAIN_TEXT,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        source_chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="CTQ characteristics define quality.",
            chunk_index=0,
            embedding=[0.7, 0.3] * 192,
            tags=[TaxonomyTag.CTQ.value],
        )
        related_chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="Critical to quality metrics are essential.",
            chunk_index=1,
            embedding=[0.71, 0.29] * 192,  # Similar to source
            tags=[TaxonomyTag.CTQ.value],
        )
        unrelated_chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="Completely different topic.",
            chunk_index=2,
            embedding=[0.1, 0.9] * 192,  # Very different
            tags=[TaxonomyTag.PROBLEM_SOLVING.value],
        )
        async_session.add_all([source_chunk, related_chunk, unrelated_chunk])
        await async_session.commit()
        
        # Find related chunks
        service = SemanticSearchService(embedding_service)
        results = await service.get_related_chunks(
            chunk_id=source_chunk.id,
            session=async_session,
            limit=5,
            min_similarity=0.7,
        )
        
        # Should return related_chunk but not unrelated_chunk
        assert len(results) >= 1
        chunk, similarity = results[0]
        assert chunk.id == related_chunk.id
        assert similarity >= 0.7
    
    @pytest.mark.asyncio
    async def test_get_related_chunks_nonexistent(
        self, embedding_service, async_session
    ):
        """Should handle nonexistent chunk gracefully."""
        service = SemanticSearchService(embedding_service)
        results = await service.get_related_chunks(
            chunk_id=99999,
            session=async_session,
            limit=5,
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_min_similarity_filter(self, embedding_service, async_session):
        """Should filter results below minimum similarity threshold."""
        # Create document with chunks
        document = KnowledgeDocument(
            title="Test Doc",
            source_url="https://example.com",
            license_type=LicenseType.BSD,
            original_format=ContentFormat.HTML,
            raw_content="test",
            normalized_content="test",
        )
        async_session.add(document)
        await async_session.commit()
        
        chunk = KnowledgeChunk(
            document_id=document.id,
            chunk_text="Low similarity content",
            chunk_index=0,
            embedding=[0.1, 0.9] * 192,  # Very different from query
        )
        async_session.add(chunk)
        await async_session.commit()
        
        # Mock query embedding (very different from chunk)
        embedding_service._model.encode.return_value = np.array([0.9, 0.1] * 192)
        
        # Search with high min_similarity
        service = SemanticSearchService(embedding_service)
        results = await service.search(
            query="unrelated query",
            session=async_session,
            limit=10,
            min_similarity=0.9,  # Very high threshold
        )
        
        # Should return no results
        assert len(results) == 0
