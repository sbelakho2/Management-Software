"""Tests for knowledge embeddings and semantic search."""

import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import Mock, patch

from sensei.models.knowledge_pack import (
    KnowledgeDocument,
    KnowledgeChunk,
    LicenseType,
    ContentFormat,
    TaxonomyTag,
)
from sensei.services.ai.knowledge_embeddings import (
    EmbeddingService,
    KnowledgeEmbeddingService,
    SemanticSearchService,
)


@pytest_asyncio.fixture
async def async_session():
    """Mock async database session for testing."""
    from unittest.mock import AsyncMock, MagicMock
    from sqlalchemy.ext.asyncio import AsyncSession
    
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    
    # Track objects added to session
    session._objects = []
    session._id_counter = 1
    
    def add_side_effect(obj):
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = session._id_counter
            session._id_counter += 1
        session._objects.append(obj)
    
    def add_all_side_effect(objs):
        for obj in objs:
            add_side_effect(obj)
    
    session.add.side_effect = add_side_effect
    session.add_all.side_effect = add_all_side_effect
    
    # Mock execute to return proper result with scalars
    async def execute_side_effect(stmt):
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        
        # Check if the query is looking for chunks with or without embeddings
        # Inspect the actual WHERE clause compilation
        try:
            # Try to compile statement to understand filters
            compiled = stmt.compile()
            stmt_str = str(compiled)
            # Get bind parameters
            params = compiled.params
        except Exception:
            # Fallback to string representation
            stmt_str = str(stmt)
            params = {}
        
        # Debug: print statement to understand it
        # import sys
        # print(f"\n=== STMT DEBUG ===\n{stmt_str}\nPARAMS: {params}\n==================\n", file=sys.stderr)
        
        # Check what table is being queried
        is_document_query = "knowledge_documents" in stmt_str
        is_chunk_query = "knowledge_chunks" in stmt_str
        
        # Check for IS NULL / IS NOT NULL patterns in WHERE clause
        has_is_null = "IS NULL" in stmt_str.upper()
        has_is_not_null = "IS NOT NULL" in stmt_str.upper()
        has_cosine = "cosine_distance" in stmt_str
        has_overlap = "tags &&" in stmt_str
        
        if is_document_query:
            # Handle document queries
            documents = [obj for obj in session._objects if isinstance(obj, KnowledgeDocument)]
            # Filter by ID if present in params
            doc_id = params.get('id_1') or params.get('document_id_1')
            if doc_id:
                documents = [doc for doc in documents if doc.id == doc_id]
            
            scalars_mock.all.return_value = documents
            result_mock.scalars.return_value = scalars_mock
            result_mock.scalar_one_or_none.return_value = documents[0] if documents else None
            result_mock.all.return_value = [(doc, 0.9) for doc in documents]
            return result_mock
        
        # Handle chunk queries
        if has_is_not_null or has_cosine:
            # Query for chunks WITH embeddings (for search)
            chunks = [
                obj for obj in session._objects 
                if isinstance(obj, KnowledgeChunk) and 
                   hasattr(obj, 'embedding') and 
                   obj.embedding is not None and 
                   (not isinstance(obj.embedding, list) or len(obj.embedding) > 0)
            ]
        elif has_is_null:
            # Query explicitly for chunks WITHOUT embeddings
            chunks = [
                obj for obj in session._objects
                if isinstance(obj, KnowledgeChunk) and
                   (not hasattr(obj, 'embedding') or 
                    obj.embedding is None or
                    (isinstance(obj.embedding, list) and len(obj.embedding) == 0))
            ]
        else:
            # Ambiguous query - default to all chunks
            chunks = [obj for obj in session._objects if isinstance(obj, KnowledgeChunk)]
        
        # Apply tag overlap filtering if present
        if has_overlap and chunks:
            # Extract filter tags from bind parameters
            filter_tags = params.get('tags_1', [])
            if filter_tags:
                # Filter chunks that have overlapping tags
                filtered_chunks = []
                for chunk in chunks:
                    if hasattr(chunk, 'tags') and chunk.tags:
                        if any(tag in chunk.tags for tag in filter_tags):
                            filtered_chunks.append(chunk)
                chunks = filtered_chunks
        
        scalars_mock.all.return_value = chunks
        result_mock.scalars.return_value = scalars_mock
        
        # For search queries, return tuples of (chunk, similarity)
        result_mock.all.return_value = [(chunk, 0.9) for chunk in chunks]
        return result_mock
    
    session.execute = AsyncMock(side_effect=execute_side_effect)
    
    return session


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model."""
    with patch("sentence_transformers.SentenceTransformer") as mock:
        model = Mock()
        # Return fixed embeddings for testing (384 dimensions)
        model.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4] * 96)
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
        embedding_service.model.encode.return_value = np.random.rand(3, 384)
        
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
        
        # Create chunks with embeddings
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="Just-in-time production minimizes inventory.",
                chunk_index=0,
                embedding=[0.9, 0.1, 0.1, 0.1] * 96,
                tags=[TaxonomyTag.TPS.value],
                quality_score=0.95,
            ),
            KnowledgeChunk(
                document_id=document.id,
                chunk_text="Jidoka enables autonomous defect detection.",
                chunk_index=1,
                embedding=[0.1, 0.9, 0.1, 0.1] * 96,
                tags=[TaxonomyTag.TPS.value],
                quality_score=0.90,
            ),
        ]
        async_session.add_all(chunks)
        await async_session.commit()
        
        # Mock query embedding (similar to first chunk)
        embedding_service.model.encode.return_value = np.array([0.9, 0.1, 0.1, 0.1] * 96)
        
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
        embedding_service.model.encode.return_value = np.array([0.9, 0.1] * 192)
        
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
        
        # Populate ORM relationship so search_with_context can resolve it
        chunk.document = document
        
        # Mock query embedding
        embedding_service.model.encode.return_value = np.array([0.8, 0.2] * 192)
        
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
