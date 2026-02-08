"""
Knowledge Embeddings Service

Generates vector embeddings for knowledge chunks using optimized ONNX models
or fallback sentence-transformers, with automatic hardware detection.
Provides semantic search capabilities via pgvector.
"""

import asyncio
import functools
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.knowledge_pack import KnowledgeChunk, KnowledgeDocument
from sensei.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """
    Detect best available device for inference.
    
    Returns:
        'cuda', 'cpu', or specific device string
    """
    device_config = settings.ML_DEVICE.lower()
    
    if device_config == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA GPU detected and available")
                return "cuda"
        except ImportError:
            pass
        
        logger.info("Using CPU for inference")
        return "cpu"
    
    return device_config


class EmbeddingService:
    """
    Generate embeddings using ONNX-optimized models (preferred) or sentence-transformers.
    
    Modes:
    - 'onnx': Uses optimized ONNX Runtime with INT8 quantization (fast, CPU-optimized)
    - 'pytorch': Uses sentence-transformers (fallback)
    """
    
    def __init__(
        self, 
        use_onnx: bool = True,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize embedding service.
        
        Args:
            use_onnx: Use ONNX models if available (default: True)
            model_name: Specific model name (optional)
            device: Device to use ('auto', 'cuda', 'cpu')
        """
        self.use_onnx = use_onnx and settings.ML_USE_ONNX
        self.model_name = model_name or settings.ML_EMBEDDING_MODEL
        self.device = device or detect_device()
        self._model: Any = None
        self._onnx_embedder: Any = None
        self.embedding_dim = settings.ML_EMBEDDING_DIM
        
        # Try ONNX first if enabled
        if self.use_onnx:
            try:
                self._init_onnx()
                logger.info(f"Initialized with ONNX embeddings (optimized for CPU)")
                return
            except Exception as e:
                logger.warning(f"ONNX initialization failed, falling back to PyTorch: {e}")
                self.use_onnx = False
        
        # Fallback to PyTorch
        logger.info(f"Initialized with PyTorch model: {self.model_name} on {self.device}")
    
    def _init_onnx(self):
        """Initialize ONNX embedder."""
        from sensei.services.ai.onnx_text_embeddings import ONNXTextEmbedder, EmbeddingConfig
        
        onnx_path = Path(settings.ML_ONNX_MODEL_PATH)
        
        if not onnx_path.exists():
            raise FileNotFoundError(f"ONNX model not found at {onnx_path}")
        
        config = EmbeddingConfig(
            model_id=self.model_name,
            cache_dir=onnx_path.parent,
            quantize_int8=True,
            max_length=256,
        )
        
        self._onnx_embedder = ONNXTextEmbedder(config)
        
        if not self._onnx_embedder.is_ready():
            raise RuntimeError("ONNX embedder dependencies not available")
        
        # Force load
        self._onnx_embedder._ensure_loaded()
    
    @staticmethod
    def _get_model_dimension(model_name: str) -> int:
        """Get embedding dimension for model."""
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384,
            "multi-qa-MiniLM-L6-cos-v1": 384,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return dimensions.get(model_name, 384)
    
    @property
    def model(self) -> Any:
        """Lazy load PyTorch model."""
        if self._model is None:
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformers model: {self.model_name} on {self.device}")
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model
    
    def encode(self, text: str | list[str]) -> np.ndarray:
        """
        Generate embedding(s) for text.
        
        Args:
            text: Single text or list of texts
            
        Returns:
            Numpy array of embeddings
        """
        if self.use_onnx and self._onnx_embedder:
            if isinstance(text, str):
                return np.array(self._onnx_embedder.embed_text(text))
            else:
                return np.array(self._onnx_embedder.embed_texts(text))
        
        # PyTorch fallback
        return self.model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of embeddings
        """
        if self.use_onnx and self._onnx_embedder:
            # ONNX embedder handles batching internally
            return np.array(self._onnx_embedder.embed_texts(texts))
        
        # PyTorch fallback
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
        # Generate embedding from chunk text (CPU-bound; offload to thread pool #81)
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            functools.partial(self.embedding_service.encode, chunk.chunk_text),
        )
        
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
        chunks = list(result.scalars().all())
        
        if not chunks:
            logger.info(f"No chunks to embed for document {document_id}")
            return 0
        
        # Extract texts
        texts = [chunk.chunk_text for chunk in chunks]
        
        # Generate embeddings in batch (CPU-bound; offload to thread pool #81)
        logger.info(f"Generating embeddings for {len(chunks)} chunks from document {document_id}")
        loop = asyncio.get_running_loop()
        failed = 0
        try:
            embeddings = await loop.run_in_executor(
                None,
                functools.partial(self.embedding_service.encode_batch, texts, batch_size=batch_size),
            )
            # Store embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding.tolist()
        except Exception as batch_err:
            # Batch failed — fall back to per-chunk processing so one bad chunk
            # doesn't kill the entire document (#182)
            logger.warning(
                f"Batch embedding failed for document {document_id}, "
                f"falling back to per-chunk: {batch_err}"
            )
            for chunk in chunks:
                try:
                    emb = await loop.run_in_executor(
                        None,
                        functools.partial(self.embedding_service.encode_batch, [chunk.chunk_text], batch_size=1),
                    )
                    chunk.embedding = emb[0].tolist()
                except Exception as chunk_err:
                    logger.error(f"Failed to embed chunk {chunk.id}: {chunk_err}")
                    failed += 1
        
        await session.commit()
        
        embedded = len(chunks) - failed
        logger.info(f"Successfully embedded {embedded}/{len(chunks)} chunks for document {document_id}")
        return embedded
    
    async def embed_all_unembedded(
        self,
        session: AsyncSession,
        batch_size: int = 32,
        db_batch_size: int = 500,
    ) -> int:
        """
        Generate embeddings for all chunks without embeddings.

        Processes in paginated database batches of *db_batch_size* to
        avoid loading all unembedded chunks into memory at once (#105).

        Args:
            session: Database session
            batch_size: Encoder batch size (passed to ONNX)
            db_batch_size: Number of chunks to fetch from DB per page

        Returns:
            Total number of chunks embedded
        """
        total_embedded = 0
        loop = asyncio.get_running_loop()

        while True:
            # Fetch one page of unembedded chunks
            stmt = (
                select(KnowledgeChunk)
                .where(KnowledgeChunk.embedding.is_(None))
                .order_by(KnowledgeChunk.document_id, KnowledgeChunk.chunk_index)
                .limit(db_batch_size)
            )
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                break

            texts = [chunk.chunk_text for chunk in chunks]

            logger.info(
                f"Embedding batch of {len(chunks)} chunks "
                f"(total so far: {total_embedded})"
            )

            # CPU-bound; offload to thread pool (#81)
            embeddings = await loop.run_in_executor(
                None,
                functools.partial(
                    self.embedding_service.encode_batch,
                    texts,
                    batch_size=batch_size,
                ),
            )

            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding.tolist()

            await session.commit()
            total_embedded += len(chunks)

            # If we got fewer than the page size we're done
            if len(chunks) < db_batch_size:
                break

        if total_embedded:
            logger.info(f"Successfully embedded {total_embedded} total chunks")
        else:
            logger.info("No chunks to embed")

        return total_embedded


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
        # Generate query embedding (CPU-bound; offload to thread pool #81)
        loop = asyncio.get_running_loop()
        query_embedding = await loop.run_in_executor(
            None,
            functools.partial(self.embedding_service.encode, query),
        )
        
        # Build search query with cosine similarity
        # pgvector's <=> operator computes cosine distance (1 - cosine similarity)
        # So we compute similarity as: 1 - (embedding <=> query)
        similarity_expr = (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding.tolist()))
        stmt = select(
            KnowledgeChunk,
            similarity_expr.label("similarity")
        ).where(
            KnowledgeChunk.embedding.isnot(None),
        )
        
        # Filter by tags if specified
        if filter_tags:
            stmt = stmt.where(KnowledgeChunk.tags.overlap(filter_tags))
        
        # Order by similarity (reference the label to avoid recomputing) and limit
        stmt = stmt.order_by(
            text("similarity DESC")
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
        
        # Batch-load all missing documents in ONE query (#101 — fix N+1)
        missing_doc_ids = {
            chunk.document_id
            for chunk, _ in results
            if not chunk.document and chunk.document_id is not None
        }
        doc_map: dict[int, Any] = {}
        if missing_doc_ids:
            doc_stmt = select(KnowledgeDocument).where(
                KnowledgeDocument.id.in_(missing_doc_ids)
            )
            doc_result = await session.execute(doc_stmt)
            doc_map = {d.id: d for d in doc_result.scalars().all()}

        # Enrich with document metadata
        enriched_results = []
        for chunk, similarity in results:
            document = chunk.document or doc_map.get(chunk.document_id)

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
        
        # Search using chunk's embedding (use labeled expression to avoid recomputing)
        similarity_expr = (1 - KnowledgeChunk.embedding.cosine_distance(source_chunk.embedding))
        stmt = select(
            KnowledgeChunk,
            similarity_expr.label("similarity")
        ).where(
            KnowledgeChunk.embedding.isnot(None),
            KnowledgeChunk.id != chunk_id,  # Exclude self
        ).order_by(
            text("similarity DESC")
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
