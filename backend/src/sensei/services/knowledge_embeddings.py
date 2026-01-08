"""
Knowledge Embeddings Service

Generates vector embeddings for knowledge chunks using open-source models
and provides semantic search capabilities via pgvector.
"""

import logging
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.knowledge_pack import KnowledgeChunk, KnowledgeDocument


logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate embeddings using open-source sentence-transformers models.
    
    Default model: 'all-MiniLM-L6-v2' (384 dimensions, fast, good quality)
    Alternative: 'all-mpnet-base-v2' (768 dimensions, better quality, slower)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: Sentence-transformers model name
        """
        self.model_name = model_name
        self._model = None
        self.embedding_dim = self._get_model_dimension(model_name)
        logger.info(f"Initialized EmbeddingService with model: {model_name} ({self.embedding_dim}D)")
    
    @staticmethod
    def _get_model_dimension(model_name: str) -> int:
        """Get embedding dimension for model."""
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384,
            "multi-qa-MiniLM-L6-cos-v1": 384,
        }
        return dimensions.get(model_name, 384)
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model on first use."""
        if self._model is None:
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode(self, text: str | list[str]) -> np.ndarray:
        """
        Generate embedding(s) for text.
        
        Args:
            text: Single text or list of texts
            
        Returns:
            Numpy array of embeddings
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts
            batch_size: Batch size for encoding
            
        Returns:
            Numpy array of embeddings
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=True,
        )


class KnowledgeEmbeddingService:
    """Service for generating and managing knowledge chunk embeddings."""
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize knowledge embedding service.
        
        Args:
            embedding_service: EmbeddingService instance
        """
        self.embedding_service = embedding_service
    
    async def embed_chunk(self, chunk: KnowledgeChunk, session: AsyncSession) -> None:
        """
        Generate and store embedding for a chunk.
        
        Args:
            chunk: KnowledgeChunk to embed
            session: Database session
        """
        # Generate embedding from chunk text
        embedding = self.embedding_service.encode(chunk.chunk_text)
        
        # Store embedding
        chunk.embedding = embedding.tolist()
        await session.commit()
        
        logger.debug(f"Generated embedding for chunk {chunk.id}")
    
    async def embed_document_chunks(
        self,
        document_id: int,
        session: AsyncSession,
        batch_size: int = 32,
    ) -> int:
        """
        Generate embeddings for all chunks of a document.
        
        Args:
            document_id: Document ID
            session: Database session
            batch_size: Batch size for encoding
            
        Returns:
            Number of chunks embedded
        """
        # Get all chunks without embeddings
        stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.document_id == document_id,
            KnowledgeChunk.embedding.is_(None),
        ).order_by(KnowledgeChunk.chunk_index)
        
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            logger.info(f"No chunks to embed for document {document_id}")
            return 0
        
        # Extract texts
        texts = [chunk.chunk_text for chunk in chunks]
        
        # Generate embeddings in batch
        logger.info(f"Generating embeddings for {len(chunks)} chunks from document {document_id}")
        embeddings = self.embedding_service.encode_batch(texts, batch_size=batch_size)
        
        # Store embeddings
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
        
        await session.commit()
        
        logger.info(f"Successfully embedded {len(chunks)} chunks for document {document_id}")
        return len(chunks)
    
    async def embed_all_unembedded(
        self,
        session: AsyncSession,
        batch_size: int = 32,
    ) -> int:
        """
        Generate embeddings for all chunks without embeddings.
        
        Args:
            session: Database session
            batch_size: Batch size for encoding
            
        Returns:
            Total number of chunks embedded
        """
        # Get all chunks without embeddings
        stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.embedding.is_(None),
        ).order_by(KnowledgeChunk.document_id, KnowledgeChunk.chunk_index)
        
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            logger.info("No chunks to embed")
            return 0
        
        # Extract texts
        texts = [chunk.chunk_text for chunk in chunks]
        
        # Generate embeddings in batch
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = self.embedding_service.encode_batch(texts, batch_size=batch_size)
        
        # Store embeddings
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
        
        await session.commit()
        
        logger.info(f"Successfully embedded {len(chunks)} total chunks")
        return len(chunks)


class SemanticSearchService:
    """Semantic search over knowledge chunks using vector similarity."""
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize semantic search service.
        
        Args:
            embedding_service: EmbeddingService instance
        """
        self.embedding_service = embedding_service
    
    async def search(
        self,
        query: str,
        session: AsyncSession,
        limit: int = 10,
        min_similarity: float = 0.5,
        filter_tags: list[str] | None = None,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """
        Semantic search for knowledge chunks.
        
        Args:
            query: Search query
            session: Database session
            limit: Maximum number of results
            min_similarity: Minimum cosine similarity (0-1)
            filter_tags: Optional list of taxonomy tags to filter by
            
        Returns:
            List of (chunk, similarity_score) tuples, ordered by relevance
        """
        # Generate query embedding
        query_embedding = self.embedding_service.encode(query)
        
        # Build search query with cosine similarity
        # pgvector's <=> operator computes cosine distance (1 - cosine similarity)
        # So we compute similarity as: 1 - (embedding <=> query)
        stmt = select(
            KnowledgeChunk,
            (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding.tolist())).label("similarity")
        ).where(
            KnowledgeChunk.embedding.isnot(None),
        )
        
        # Filter by tags if specified
        if filter_tags:
            stmt = stmt.where(KnowledgeChunk.tags.overlap(filter_tags))
        
        # Order by similarity and limit
        stmt = stmt.order_by(
            (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding.tolist())).desc()
        ).limit(limit)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # Filter by minimum similarity
        results = [
            (chunk, similarity)
            for chunk, similarity in rows
            if similarity >= min_similarity
        ]
        
        logger.info(
            f"Search query: '{query[:50]}...' returned {len(results)} results "
            f"(min_similarity={min_similarity})"
        )
        
        return results
    
    async def search_with_context(
        self,
        query: str,
        session: AsyncSession,
        limit: int = 5,
        min_similarity: float = 0.6,
        filter_tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search with full document context.
        
        Args:
            query: Search query
            session: Database session
            limit: Maximum number of results
            min_similarity: Minimum cosine similarity
            filter_tags: Optional taxonomy tags filter
            
        Returns:
            List of result dictionaries with chunk, document, and metadata
        """
        # Perform search
        results = await self.search(
            query=query,
            session=session,
            limit=limit,
            min_similarity=min_similarity,
            filter_tags=filter_tags,
        )
        
        # Enrich with document metadata
        enriched_results = []
        for chunk, similarity in results:
            # Load document if not already loaded
            if not chunk.document:
                stmt = select(KnowledgeDocument).where(
                    KnowledgeDocument.id == chunk.document_id
                )
                result = await session.execute(stmt)
                document = result.scalar_one_or_none()
            else:
                document = chunk.document
            
            if not document:
                logger.warning(f"Document {chunk.document_id} not found for chunk {chunk.id}")
                continue
            
            enriched_results.append({
                "chunk_text": chunk.chunk_text,
                "heading": chunk.heading,
                "section_path": chunk.section_path,
                "similarity": similarity,
                "citation": chunk.citation,
                "document_title": document.title,
                "document_author": document.author,
                "source_url": document.source_url,
                "license_type": document.license_type.value,
                "tags": chunk.tags,
                "quality_score": chunk.quality_score,
            })
        
        return enriched_results
    
    async def get_related_chunks(
        self,
        chunk_id: int,
        session: AsyncSession,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> list[tuple[KnowledgeChunk, float]]:
        """
        Find chunks similar to a given chunk.
        
        Args:
            chunk_id: Source chunk ID
            session: Database session
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (chunk, similarity) tuples
        """
        # Get source chunk
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
        result = await session.execute(stmt)
        source_chunk = result.scalar_one_or_none()
        
        if not source_chunk or source_chunk.embedding is None:
            logger.warning(f"Chunk {chunk_id} not found or has no embedding")
            return []
        
        # Search using chunk's embedding
        stmt = select(
            KnowledgeChunk,
            (1 - KnowledgeChunk.embedding.cosine_distance(source_chunk.embedding)).label("similarity")
        ).where(
            KnowledgeChunk.embedding.isnot(None),
            KnowledgeChunk.id != chunk_id,  # Exclude self
        ).order_by(
            (1 - KnowledgeChunk.embedding.cosine_distance(source_chunk.embedding)).desc()
        ).limit(limit)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # Filter by minimum similarity
        results = [
            (chunk, similarity)
            for chunk, similarity in rows
            if similarity >= min_similarity
        ]
        
        return results
