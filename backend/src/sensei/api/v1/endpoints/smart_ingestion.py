from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.schemas import APIResponse
from sensei.api import deps
from sensei.api.deps import get_db
from sensei.api.utils import build_response
from sensei.core.config import settings
from sensei.models.service_persistence import IngestionJobDB, IngestionDocumentDB
from sensei.models.user import User
from sensei.services.smart_ingestion import (
    EmailAttachment,
    EmailContent,
    IngestionJob,
    SmartIngestionService,
)

router = APIRouter()

_service = SmartIngestionService()


class EmailAttachmentInput(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    content_base64: str | None = None


class EmailIngestionRequest(BaseModel):
    id: str
    subject: str
    from_address: str
    from_name: str | None = None
    to_addresses: list[str]
    cc_addresses: list[str] = Field(default_factory=list)
    body_text: str = ""
    body_html: str = ""
    received_date: datetime | None = None
    attachments: list[EmailAttachmentInput] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class IngestionJobResponse(BaseModel):
    id: str
    status: str
    document_metadata: dict[str, Any] | None
    email_content: dict[str, Any] | None
    ocr_result: dict[str, Any] | None
    extracted_entities: list[dict[str, Any]]
    created_entity_ids: dict[str, str]
    errors: list[str]
    warnings: list[str]
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    created_by: str | None
    review_notes: str | None
    processing_duration_ms: int | None
    needs_review: bool


class IngestionStatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_review_jobs: int
    entities_created: int
    avg_processing_time_ms: float
    avg_confidence: float


def _serialize_dataclass(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_dataclass(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_dataclass(v) for v in value]
    if hasattr(value, "__dict__"):
        return _serialize_dataclass(value.__dict__)
    return value


def _job_to_response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=job.id,
        status=job.status.value,
        document_metadata=_serialize_dataclass(job.document_metadata),
        email_content=_serialize_dataclass(job.email_content),
        ocr_result=_serialize_dataclass(job.ocr_result),
        extracted_entities=_serialize_dataclass(job.extracted_entities) or [],
        created_entity_ids=job.created_entity_ids,
        errors=job.errors,
        warnings=job.warnings,
        processing_started_at=job.processing_started_at,
        processing_completed_at=job.processing_completed_at,
        created_at=job.created_at,
        created_by=job.created_by,
        review_notes=job.review_notes,
        processing_duration_ms=job.processing_duration_ms,
        needs_review=job.needs_review,
    )


async def _persist_job_to_db(db: AsyncSession, job: IngestionJob) -> None:
    """Persist an in-memory IngestionJob to the database."""
    try:
        row = IngestionJobDB(
            id=UUID(job.id),
            job_type="email" if job.email_content else "document",
            status=job.status.value,
            source_id=job.id,
            source_metadata=_serialize_dataclass(job.document_metadata) if job.document_metadata else None,
            started_at=job.processing_started_at,
            completed_at=job.processing_completed_at,
            extracted_entities=_serialize_dataclass(job.extracted_entities) if job.extracted_entities else None,
            created_entity_ids=job.created_entity_ids if job.created_entity_ids else None,
            error_message="; ".join(job.errors) if job.errors else None,
            user_id=UUID(job.created_by) if job.created_by else None,
        )
        db.add(row)
        await db.commit()
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to persist ingestion job %s to DB", job.id, exc_info=True
        )


@router.post(
    "/smart-ingestion/document",
    response_model=APIResponse[IngestionJobResponse],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[IngestionJobResponse]:
    """Ingest a document for OCR and entity extraction (persisted to DB)."""
    _ = current_user
    try:
        content = await file.read()
        job = _service.ingest_document(file.filename, content, file.content_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Persist to database
    await _persist_job_to_db(db, job)

    return build_response(_job_to_response(job))


@router.post(
    "/smart-ingestion/email",
    response_model=APIResponse[IngestionJobResponse],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_email(
    payload: EmailIngestionRequest,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[IngestionJobResponse]:
    """Ingest a parsed email and extract entities (persisted to DB)."""
    attachments = [
        EmailAttachment(
            id=item.id,
            filename=item.filename,
            mime_type=item.mime_type,
            size_bytes=item.size_bytes,
            content_base64=item.content_base64,
        )
        for item in payload.attachments
    ]

    email = EmailContent(
        id=payload.id,
        subject=payload.subject,
        from_address=payload.from_address,
        from_name=payload.from_name,
        to_addresses=payload.to_addresses,
        cc_addresses=payload.cc_addresses,
        body_text=payload.body_text,
        body_html=payload.body_html,
        received_date=payload.received_date or datetime.utcnow(),
        attachments=attachments,
        headers=payload.headers,
    )

    try:
        job = _service.ingest_email(email)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Persist to database
    await _persist_job_to_db(db, job)

    return build_response(_job_to_response(job))


@router.get(
    "/smart-ingestion/jobs/{job_id}",
    response_model=APIResponse[IngestionJobResponse],
)
async def get_job(
    job_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[IngestionJobResponse]:
    """Get an ingestion job by ID (checks in-memory then DB)."""
    # Try in-memory first (active jobs)
    job = _service.get_job(job_id)
    if job:
        return build_response(_job_to_response(job))

    # Fall back to database
    from sqlalchemy import select
    try:
        uid = UUID(job_id)
        result = await db.execute(
            select(IngestionJobDB).where(IngestionJobDB.id == uid)
        )
        row = result.scalar_one_or_none()
        if row:
            return build_response(IngestionJobResponse(
                id=str(row.id),
                status=row.status,
                document_metadata=row.source_metadata,
                email_content=None,
                ocr_result=None,
                extracted_entities=row.extracted_entities or [],
                created_entity_ids=row.created_entity_ids or {},
                errors=[row.error_message] if row.error_message else [],
                warnings=[],
                processing_started_at=row.started_at,
                processing_completed_at=row.completed_at,
                created_at=row.created_at,
                created_by=str(row.user_id) if row.user_id else None,
                review_notes=None,
                processing_duration_ms=None,
                needs_review=row.status == "requires_review",
            ))
    except (ValueError, Exception):
        pass

    raise HTTPException(status_code=404, detail="Job not found")


@router.get(
    "/smart-ingestion/jobs/review",
    response_model=APIResponse[list[IngestionJobResponse]],
)
async def get_jobs_requiring_review(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list[IngestionJobResponse]]:
    """List jobs requiring manual review (from in-memory + DB)."""
    # In-memory active jobs
    jobs = [_job_to_response(job) for job in _service.get_jobs_requiring_review()]

    # Also check database for persisted review jobs
    from sqlalchemy import select
    result = await db.execute(
        select(IngestionJobDB)
        .where(IngestionJobDB.status == "requires_review")
        .order_by(IngestionJobDB.created_at.desc())
    )
    for row in result.scalars().all():
        if str(row.id) not in {j.id for j in jobs}:
            jobs.append(IngestionJobResponse(
                id=str(row.id),
                status=row.status,
                document_metadata=row.source_metadata,
                email_content=None,
                ocr_result=None,
                extracted_entities=row.extracted_entities or [],
                created_entity_ids=row.created_entity_ids or {},
                errors=[row.error_message] if row.error_message else [],
                warnings=[],
                processing_started_at=row.started_at,
                processing_completed_at=row.completed_at,
                created_at=row.created_at,
                created_by=str(row.user_id) if row.user_id else None,
                review_notes=None,
                processing_duration_ms=None,
                needs_review=True,
            ))

    return build_response(jobs)


@router.get(
    "/smart-ingestion/stats",
    response_model=APIResponse[IngestionStatsResponse],
)
async def get_ingestion_stats(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[IngestionStatsResponse]:
    """Get ingestion pipeline statistics (from DB)."""
    from sqlalchemy import select, func as sqla_func

    total = (await db.execute(
        select(sqla_func.count()).select_from(IngestionJobDB)
    )).scalar() or 0
    completed = (await db.execute(
        select(sqla_func.count()).select_from(IngestionJobDB)
        .where(IngestionJobDB.status == "completed")
    )).scalar() or 0
    failed = (await db.execute(
        select(sqla_func.count()).select_from(IngestionJobDB)
        .where(IngestionJobDB.status == "failed")
    )).scalar() or 0
    pending_review = (await db.execute(
        select(sqla_func.count()).select_from(IngestionJobDB)
        .where(IngestionJobDB.status == "requires_review")
    )).scalar() or 0

    # Fall back to in-memory stats for other metrics
    mem_stats = _service.get_stats()

    return build_response(IngestionStatsResponse(
        total_jobs=max(total, mem_stats.total_jobs),
        completed_jobs=max(completed, mem_stats.completed_jobs),
        failed_jobs=max(failed, mem_stats.failed_jobs),
        pending_review_jobs=max(pending_review, mem_stats.pending_review_jobs),
        entities_created=mem_stats.entities_created,
        avg_processing_time_ms=mem_stats.avg_processing_time_ms,
        avg_confidence=mem_stats.avg_confidence,
    ))
