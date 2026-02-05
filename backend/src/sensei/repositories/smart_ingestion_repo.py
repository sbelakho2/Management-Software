"""
Database repository for Smart Ingestion.

Provides async database access for ingestion job and document persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.service_persistence import (
    IngestionJobDB,
    IngestionDocumentDB,
)


class SmartIngestionRepository:
    """Repository for smart ingestion database operations."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session
    
    # --------------------------------------------------------------------------
    # Ingestion Jobs
    # --------------------------------------------------------------------------
    
    async def create_job(
        self,
        source_type: str,
        source_config: dict[str, Any],
        created_by_user_id: UUID | None = None,
        job_name: str | None = None,
        total_documents: int = 0,
        processing_options: dict[str, Any] | None = None,
    ) -> IngestionJobDB:
        """Create a new ingestion job."""
        job = IngestionJobDB(
            job_name=job_name,
            source_type=source_type,
            source_config=source_config,
            created_by_user_id=created_by_user_id,
            total_documents=total_documents,
            processing_options=processing_options or {},
            status="pending",
        )
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job
    
    async def get_job(self, job_id: UUID) -> IngestionJobDB | None:
        """Get a job by ID."""
        result = await self._session.execute(
            select(IngestionJobDB).where(IngestionJobDB.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def update_job(
        self,
        job_id: UUID,
        **fields: Any,
    ) -> IngestionJobDB | None:
        """Update a job."""
        job = await self.get_job(job_id)
        if not job:
            return None
        
        for field, value in fields.items():
            if hasattr(job, field):
                setattr(job, field, value)
        
        job.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(job)
        return job
    
    async def start_job(self, job_id: UUID) -> IngestionJobDB | None:
        """Mark a job as started."""
        return await self.update_job(
            job_id,
            status="processing",
            started_at=datetime.now(timezone.utc),
        )
    
    async def complete_job(
        self,
        job_id: UUID,
        processed_documents: int | None = None,
        failed_documents: int | None = None,
    ) -> IngestionJobDB | None:
        """Mark a job as completed."""
        updates: dict[str, Any] = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc),
        }
        
        if processed_documents is not None:
            updates["processed_documents"] = processed_documents
        if failed_documents is not None:
            updates["failed_documents"] = failed_documents
        
        return await self.update_job(job_id, **updates)
    
    async def fail_job(
        self,
        job_id: UUID,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> IngestionJobDB | None:
        """Mark a job as failed."""
        return await self.update_job(
            job_id,
            status="failed",
            error_message=error_message,
            error_details=error_details,
            completed_at=datetime.now(timezone.utc),
        )
    
    async def pause_job(self, job_id: UUID) -> IngestionJobDB | None:
        """Pause a job."""
        return await self.update_job(job_id, status="paused")
    
    async def resume_job(self, job_id: UUID) -> IngestionJobDB | None:
        """Resume a paused job."""
        return await self.update_job(job_id, status="processing")
    
    async def cancel_job(self, job_id: UUID) -> IngestionJobDB | None:
        """Cancel a job."""
        return await self.update_job(
            job_id,
            status="cancelled",
            completed_at=datetime.now(timezone.utc),
        )
    
    async def increment_progress(
        self,
        job_id: UUID,
        processed_count: int = 1,
        failed_count: int = 0,
    ) -> IngestionJobDB | None:
        """Increment job progress counters."""
        job = await self.get_job(job_id)
        if not job:
            return None
        
        job.processed_documents = (job.processed_documents or 0) + processed_count
        job.failed_documents = (job.failed_documents or 0) + failed_count
        job.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(job)
        return job
    
    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a job and its documents."""
        # Delete documents first
        await self._session.execute(
            delete(IngestionDocumentDB).where(
                IngestionDocumentDB.job_id == job_id
            )
        )
        
        result = await self._session.execute(
            delete(IngestionJobDB).where(IngestionJobDB.id == job_id)
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def list_jobs(
        self,
        user_id: UUID | None = None,
        status: str | None = None,
        source_type: str | None = None,
        limit: int = 100,
    ) -> list[IngestionJobDB]:
        """List ingestion jobs."""
        query = select(IngestionJobDB)
        
        if user_id:
            query = query.where(IngestionJobDB.created_by_user_id == user_id)
        
        if status:
            query = query.where(IngestionJobDB.status == status)
        
        if source_type:
            query = query.where(IngestionJobDB.source_type == source_type)
        
        query = query.order_by(IngestionJobDB.created_at.desc())
        query = query.limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def list_active_jobs(self) -> list[IngestionJobDB]:
        """List jobs that are currently processing or paused."""
        result = await self._session.execute(
            select(IngestionJobDB).where(
                IngestionJobDB.status.in_(["processing", "paused", "pending"])
            ).order_by(IngestionJobDB.created_at)
        )
        return list(result.scalars().all())
    
    async def get_job_stats(self, job_id: UUID) -> dict[str, Any]:
        """Get statistics for a job."""
        job = await self.get_job(job_id)
        if not job:
            return {}
        
        # Count documents by status
        result = await self._session.execute(
            select(
                IngestionDocumentDB.status,
                func.count(IngestionDocumentDB.id).label("count"),
            )
            .where(IngestionDocumentDB.job_id == job_id)
            .group_by(IngestionDocumentDB.status)
        )
        status_counts = {row.status: row.count for row in result}
        
        return {
            "job_id": str(job_id),
            "status": job.status,
            "total_documents": job.total_documents,
            "processed_documents": job.processed_documents,
            "failed_documents": job.failed_documents,
            "document_status_counts": status_counts,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    
    # --------------------------------------------------------------------------
    # Ingestion Documents
    # --------------------------------------------------------------------------
    
    async def create_document(
        self,
        job_id: UUID,
        source_path: str,
        file_name: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        file_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionDocumentDB:
        """Create a document record for ingestion."""
        doc = IngestionDocumentDB(
            job_id=job_id,
            source_path=source_path,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            file_hash=file_hash,
            metadata=metadata or {},
            status="pending",
        )
        self._session.add(doc)
        await self._session.flush()
        await self._session.refresh(doc)
        return doc
    
    async def create_documents_bulk(
        self,
        job_id: UUID,
        documents: list[dict[str, Any]],
    ) -> int:
        """Create multiple document records."""
        count = 0
        for doc_data in documents:
            doc = IngestionDocumentDB(
                job_id=job_id,
                source_path=doc_data["source_path"],
                file_name=doc_data.get("file_name"),
                file_size=doc_data.get("file_size"),
                file_type=doc_data.get("file_type"),
                file_hash=doc_data.get("file_hash"),
                metadata=doc_data.get("metadata", {}),
                status="pending",
            )
            self._session.add(doc)
            count += 1
        
        await self._session.flush()
        return count
    
    async def get_document(self, document_id: UUID) -> IngestionDocumentDB | None:
        """Get a document by ID."""
        result = await self._session.execute(
            select(IngestionDocumentDB).where(IngestionDocumentDB.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def update_document(
        self,
        document_id: UUID,
        **fields: Any,
    ) -> IngestionDocumentDB | None:
        """Update a document."""
        doc = await self.get_document(document_id)
        if not doc:
            return None
        
        for field, value in fields.items():
            if hasattr(doc, field):
                setattr(doc, field, value)
        
        doc.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(doc)
        return doc
    
    async def start_document_processing(
        self,
        document_id: UUID,
    ) -> IngestionDocumentDB | None:
        """Mark a document as being processed."""
        return await self.update_document(
            document_id,
            status="processing",
            processing_started_at=datetime.now(timezone.utc),
        )
    
    async def complete_document_processing(
        self,
        document_id: UUID,
        extracted_text_length: int | None = None,
        chunk_count: int | None = None,
        knowledge_id: UUID | None = None,
    ) -> IngestionDocumentDB | None:
        """Mark a document as successfully processed."""
        updates: dict[str, Any] = {
            "status": "completed",
            "processing_completed_at": datetime.now(timezone.utc),
        }
        
        if extracted_text_length is not None:
            updates["extracted_text_length"] = extracted_text_length
        if chunk_count is not None:
            updates["chunk_count"] = chunk_count
        if knowledge_id is not None:
            updates["knowledge_id"] = knowledge_id
        
        return await self.update_document(document_id, **updates)
    
    async def fail_document_processing(
        self,
        document_id: UUID,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> IngestionDocumentDB | None:
        """Mark a document as failed."""
        doc = await self.get_document(document_id)
        if not doc:
            return None
        
        doc.status = "failed"
        doc.processing_completed_at = datetime.now(timezone.utc)
        doc.retry_count = (doc.retry_count or 0) + 1
        doc.last_error = error_message
        doc.error_details = error_details
        doc.updated_at = datetime.now(timezone.utc)
        
        await self._session.flush()
        await self._session.refresh(doc)
        return doc
    
    async def skip_document(
        self,
        document_id: UUID,
        reason: str,
    ) -> IngestionDocumentDB | None:
        """Mark a document as skipped."""
        return await self.update_document(
            document_id,
            status="skipped",
            last_error=reason,
        )
    
    async def list_documents_for_job(
        self,
        job_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IngestionDocumentDB]:
        """List documents for a job."""
        query = select(IngestionDocumentDB).where(
            IngestionDocumentDB.job_id == job_id
        )
        
        if status:
            query = query.where(IngestionDocumentDB.status == status)
        
        query = query.order_by(IngestionDocumentDB.created_at)
        query = query.offset(offset).limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_next_pending_document(
        self,
        job_id: UUID,
    ) -> IngestionDocumentDB | None:
        """Get the next pending document for processing."""
        result = await self._session.execute(
            select(IngestionDocumentDB)
            .where(
                and_(
                    IngestionDocumentDB.job_id == job_id,
                    IngestionDocumentDB.status == "pending",
                )
            )
            .order_by(IngestionDocumentDB.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_pending_documents_batch(
        self,
        job_id: UUID,
        batch_size: int = 10,
    ) -> list[IngestionDocumentDB]:
        """Get a batch of pending documents for processing."""
        result = await self._session.execute(
            select(IngestionDocumentDB)
            .where(
                and_(
                    IngestionDocumentDB.job_id == job_id,
                    IngestionDocumentDB.status == "pending",
                )
            )
            .order_by(IngestionDocumentDB.created_at)
            .limit(batch_size)
        )
        return list(result.scalars().all())
    
    async def get_failed_documents_for_retry(
        self,
        job_id: UUID,
        max_retries: int = 3,
    ) -> list[IngestionDocumentDB]:
        """Get failed documents that can be retried."""
        result = await self._session.execute(
            select(IngestionDocumentDB).where(
                and_(
                    IngestionDocumentDB.job_id == job_id,
                    IngestionDocumentDB.status == "failed",
                    IngestionDocumentDB.retry_count < max_retries,
                )
            ).order_by(IngestionDocumentDB.created_at)
        )
        return list(result.scalars().all())
    
    async def reset_document_for_retry(
        self,
        document_id: UUID,
    ) -> IngestionDocumentDB | None:
        """Reset a failed document to pending for retry."""
        return await self.update_document(
            document_id,
            status="pending",
            processing_started_at=None,
            processing_completed_at=None,
        )
    
    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document."""
        result = await self._session.execute(
            delete(IngestionDocumentDB).where(
                IngestionDocumentDB.id == document_id
            )
        )
        return result.rowcount > 0  # type: ignore[return-value]
    
    async def check_duplicate_hash(
        self,
        file_hash: str,
        exclude_job_id: UUID | None = None,
    ) -> IngestionDocumentDB | None:
        """Check if a document with the same hash already exists."""
        query = select(IngestionDocumentDB).where(
            and_(
                IngestionDocumentDB.file_hash == file_hash,
                IngestionDocumentDB.status == "completed",
            )
        )
        
        if exclude_job_id:
            query = query.where(IngestionDocumentDB.job_id != exclude_job_id)
        
        result = await self._session.execute(query.limit(1))
        return result.scalar_one_or_none()


async def get_smart_ingestion_repo(
    session: AsyncSession,
) -> SmartIngestionRepository:
    """Dependency injection helper for SmartIngestionRepository."""
    return SmartIngestionRepository(session)
