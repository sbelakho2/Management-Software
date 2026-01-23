"""
Attachment API endpoints.

Provides file attachment management with:
- Upload and download
- Version control
- Metadata management
- Entity-based querying
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.exceptions import NotFoundError, ConflictError, ValidationError
from sensei.api.utils import (
    build_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    build_paginated_response,
)
from sensei.core.storage import upload_file_stream, generate_presigned_url, delete_file
from sensei.models.attachment import (
    Attachment,
    AttachmentVersion,
    AttachmentCategory,
    AttachmentStatus,
)


router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class AttachmentBase(BaseModel):
    """Base schema for attachments."""

    title: str | None = None
    description: str | None = None
    category: AttachmentCategory = AttachmentCategory.DOCUMENT
    is_confidential: bool = False
    access_level: str | None = None
    document_number: str | None = None
    revision: str | None = None
    tags: list[str] | None = None
    custom_metadata: dict | None = None


class AttachmentCreate(AttachmentBase):
    """Schema for creating an attachment."""

    entity_type: str
    entity_id: UUID
    filename: str | None = None  # Optional, will use original if not provided


class AttachmentUpdate(BaseModel):
    """Schema for updating an attachment."""

    title: str | None = None
    description: str | None = None
    category: AttachmentCategory | None = None
    is_confidential: bool | None = None
    access_level: str | None = None
    document_number: str | None = None
    revision: str | None = None
    tags: list[str] | None = None
    custom_metadata: dict | None = None


class AttachmentResponse(BaseModel):
    """Response schema for an attachment."""

    id: UUID
    entity_type: str
    entity_id: UUID
    filename: str
    original_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    file_size_human: str
    storage_bucket: str
    storage_key: str
    category: str
    title: str | None
    description: str | None
    current_version: int
    is_latest: bool
    document_number: str | None
    revision: str | None
    uploaded_by_id: UUID | None
    uploaded_at: datetime
    is_confidential: bool
    access_level: str | None
    scan_status: str | None
    scanned_at: datetime | None
    checksum_md5: str | None
    checksum_sha256: str | None
    has_preview: bool
    preview_storage_key: str | None
    has_thumbnail: bool
    thumbnail_storage_key: str | None
    tags: list[str] | None
    custom_metadata: dict | None
    is_deleted: bool
    is_image: bool
    is_pdf: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class VersionCreate(BaseModel):
    """Schema for creating a new version."""

    change_reason: str | None = None
    change_notes: str | None = None
    revision: str | None = None

class VersionResponse(BaseModel):
    """Response schema for an attachment version."""

    id: UUID
    attachment_id: UUID
    version_number: int
    filename: str
    file_size: int
    file_size_human: str
    mime_type: str
    storage_bucket: str
    storage_key: str
    checksum_md5: str | None
    checksum_sha256: str | None
    created_by_id: UUID | None
    change_reason: str | None
    change_notes: str | None
    revision: str | None
    is_current: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Helper Functions
# =============================================================================


def detect_category(mime_type: str, extension: str) -> AttachmentCategory:
    """Detect attachment category from mime type and extension."""
    mime_lower = mime_type.lower()
    ext_lower = extension.lower().lstrip(".")

    if mime_lower.startswith("image/"):
        return AttachmentCategory.IMAGE
    elif mime_lower.startswith("video/"):
        return AttachmentCategory.VIDEO
    elif mime_lower.startswith("audio/"):
        return AttachmentCategory.AUDIO
    elif mime_lower == "application/pdf":
        return AttachmentCategory.PDF
    elif ext_lower in ("xls", "xlsx", "csv", "ods"):
        return AttachmentCategory.SPREADSHEET
    elif ext_lower in ("ppt", "pptx", "odp"):
        return AttachmentCategory.PRESENTATION
    elif ext_lower in ("doc", "docx", "odt", "txt", "rtf"):
        return AttachmentCategory.DOCUMENT
    elif ext_lower in ("dwg", "dxf"):
        return AttachmentCategory.DRAWING
    elif ext_lower in ("stl", "step", "stp", "iges", "igs", "obj"):
        return AttachmentCategory.MODEL_3D
    elif ext_lower in ("zip", "tar", "gz", "rar", "7z"):
        return AttachmentCategory.ARCHIVE
    else:
        return AttachmentCategory.OTHER


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename."""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


def generate_storage_key(entity_type: str, entity_id: UUID, filename: str) -> str:
    """Generate a unique storage key."""
    unique_id = uuid4().hex[:8]
    return f"{entity_type}/{entity_id}/{unique_id}_{filename}"


# =============================================================================
# Attachment CRUD Endpoints
# =============================================================================


@router.post("", response_model=None)
async def create_attachment(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str = Form(...),
    entity_id: UUID = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: AttachmentCategory | None = Form(None),
    is_confidential: bool = Form(False),
    document_number: str | None = Form(None),
    revision: str | None = Form(None),
    tags: str | None = Form(None),  # JSON string or comma-separated
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """
    Upload a new attachment.
    
    Creates a new attachment record with file metadata.
    The actual file should be stored in the configured storage backend.
    """
    # Get file info
    original_filename = file.filename or "unknown"
    extension = get_file_extension(original_filename)
    mime_type = file.content_type or "application/octet-stream"

    # Auto-detect category if not provided
    if category is None:
        category = detect_category(mime_type, extension)

    # Generate storage key
    storage_key = generate_storage_key(entity_type, entity_id, original_filename)

    # Upload to storage (streamed)
    upload_result = await upload_file_stream(
        file_obj=file.file,
        key=storage_key,
        content_type=mime_type,
        metadata={
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "original_filename": original_filename,
            "uploaded_by": str(current_user.id),
        },
    )

    # Parse tags
    parsed_tags = None
    if tags:
        try:
            import json

            parsed_tags = json.loads(tags)
        except json.JSONDecodeError:
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    # Create attachment
    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=original_filename,
        original_filename=original_filename,
        file_extension=extension,
        mime_type=mime_type,
        file_size=upload_result["size"],
        storage_bucket="attachments",
        storage_key=storage_key,
        category=category.value if isinstance(category, AttachmentCategory) else category,
        title=title,
        description=description,
        current_version=1,
        is_latest=True,
        document_number=document_number,
        revision=revision,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
        is_confidential=is_confidential,
        checksum_sha256=upload_result["hash"],
        tags=parsed_tags,
    )

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return build_created_response(
        data=AttachmentResponse.model_validate(attachment),
        resource_name="Attachment",
    )


@router.post("/metadata", response_model=None)
async def create_attachment_metadata(
    data: AttachmentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Create attachment metadata without file upload.
    
    Use this when the file is uploaded separately (e.g., directly to S3).
    """
    # Generate a placeholder storage key
    storage_key = generate_storage_key(
        data.entity_type,
        data.entity_id,
        data.filename or "file",
    )

    attachment = Attachment(
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        filename=data.filename or "file",
        original_filename=data.filename or "file",
        file_extension=get_file_extension(data.filename or ""),
        mime_type="application/octet-stream",
        file_size=0,
        storage_bucket="attachments",
        storage_key=storage_key,
        category=data.category.value if isinstance(data.category, AttachmentCategory) else data.category,
        title=data.title,
        description=data.description,
        current_version=1,
        is_latest=True,
        document_number=data.document_number,
        revision=data.revision,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.now(timezone.utc),
        is_confidential=data.is_confidential,
        access_level=data.access_level,
        tags=data.tags,
        custom_metadata=data.custom_metadata,
    )

    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return build_created_response(
        data=AttachmentResponse.model_validate(attachment),
        resource_name="Attachment",
    )


@router.get("/{attachment_id}", response_model=None)
async def get_attachment(
    attachment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get an attachment by ID."""
    query = select(Attachment).where(
        and_(
            Attachment.id == attachment_id,
            Attachment.deleted_at.is_(None),  # noqa: E712
        )
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    return build_response(
        data=AttachmentResponse.model_validate(attachment),
        message="Attachment retrieved successfully",
    )


@router.get("", response_model=None)
async def list_attachments(
    db: DBSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    category: AttachmentCategory | None = Query(None, description="Filter by category"),
    is_confidential: bool | None = Query(None, description="Filter by confidentiality"),
    search: str | None = Query(None, description="Search in filename/title"),
    include_deleted: bool = Query(False, description="Include deleted attachments"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """List attachments with filtering."""
    # Build query
    conditions: list[Any] = []

    if not include_deleted:
        conditions.append(Attachment.deleted_at.is_(None))  # noqa: E712

    if entity_type:
        conditions.append(Attachment.entity_type == entity_type)

    if entity_id:
        conditions.append(Attachment.entity_id == entity_id)

    if category:
        conditions.append(Attachment.category == category.value)

    if is_confidential is not None:
        conditions.append(Attachment.is_confidential == is_confidential)

    if search:
        search_filter = or_(
            Attachment.filename.ilike(f"%{search}%"),
            Attachment.title.ilike(f"%{search}%"),
            Attachment.original_filename.ilike(f"%{search}%"),
        )
        conditions.append(search_filter)

    # Count
    count_query = select(func.count(Attachment.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(Attachment)
        .where(and_(*conditions))
        .order_by(Attachment.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    attachments = data_result.scalars().all()

    return build_paginated_response(
        data=[AttachmentResponse.model_validate(a) for a in attachments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{attachment_id}", response_model=None)
async def update_attachment(
    attachment_id: UUID,
    data: AttachmentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Update attachment metadata."""
    query = select(Attachment).where(
        and_(
            Attachment.id == attachment_id,
            Attachment.deleted_at.is_(None),  # noqa: E712
        )
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and value is not None:
            setattr(attachment, field, value.value if isinstance(value, AttachmentCategory) else value)
        else:
            setattr(attachment, field, value)

    await db.commit()
    await db.refresh(attachment)

    return build_updated_response(
        data=AttachmentResponse.model_validate(attachment),
        resource_name="Attachment",
    )


@router.delete("/{attachment_id}", response_model=None)
async def delete_attachment(
    attachment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(False, description="Permanently delete"),
) -> dict[str, Any]:
    """
    Delete an attachment.
    
    By default, performs a soft delete. Use hard_delete=true for permanent deletion.
    """
    query = select(Attachment).where(Attachment.id == attachment_id)
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    if attachment.is_deleted and not hard_delete:
        raise ConflictError("Attachment is already deleted")

    if hard_delete:
        await db.delete(attachment)
    else:
        attachment.is_deleted = True
        attachment.deleted_at = datetime.now(timezone.utc)
        attachment.deleted_by_id = current_user.id

    await db.commit()

    return build_deleted_response(resource_name="Attachment")


@router.post("/{attachment_id}/restore", response_model=None)
async def restore_attachment(
    attachment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Restore a soft-deleted attachment."""
    query = select(Attachment).where(
        and_(
            Attachment.id == attachment_id,
            Attachment.is_deleted.is_(True),  # noqa: E712
        )
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    attachment.is_deleted = False
    attachment.deleted_at = None
    attachment.deleted_by_id = None

    await db.commit()
    await db.refresh(attachment)

    return build_response(
        data=AttachmentResponse.model_validate(attachment),
        message="Attachment restored successfully",
    )


# =============================================================================
# Version Endpoints
# =============================================================================


@router.post("/{attachment_id}/versions", response_model=None)
async def create_version(
    attachment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    change_reason: str | None = Form(None),
    change_notes: str | None = Form(None),
    revision: str | None = Form(None),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """
    Upload a new version of an attachment.
    
    Creates a version record for the previous state and updates the attachment.
    """
    query = select(Attachment).where(
        and_(
            Attachment.id == attachment_id,
            Attachment.deleted_at.is_(None),  # noqa: E712
        )
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    # Create version record for current state
    version = AttachmentVersion(
        attachment_id=attachment.id,
        version_number=attachment.current_version,
        filename=attachment.filename,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        storage_bucket=attachment.storage_bucket,
        storage_key=attachment.storage_key,
        checksum_md5=attachment.checksum_md5,
        checksum_sha256=attachment.checksum_sha256,
        created_by_id=current_user.id,
        change_reason=change_reason,
        change_notes=change_notes,
        revision=attachment.revision,
        is_current=False,
    )
    db.add(version)

    # Stream new file to storage
    new_filename = file.filename or attachment.original_filename
    new_extension = get_file_extension(new_filename)
    new_mime_type = file.content_type or attachment.mime_type
    new_storage_key = generate_storage_key(
        attachment.entity_type,
        attachment.entity_id,
        new_filename,
    )

    # Update attachment with new file info
    attachment.filename = new_filename
    attachment.original_filename = new_filename
    attachment.file_extension = new_extension
    attachment.mime_type = new_mime_type
    attachment.storage_key = new_storage_key
    attachment.current_version += 1
    attachment.revision = revision
    attachment.uploaded_at = datetime.now(timezone.utc)
    attachment.uploaded_by_id = current_user.id

    # Upload new version to storage
    upload_result = await upload_file_stream(
        file_obj=file.file,
        key=new_storage_key,
        content_type=new_mime_type,
        metadata={
            "attachment_id": str(attachment.id),
            "version": str(attachment.current_version),
            "original_filename": new_filename,
            "uploaded_by": str(current_user.id),
        }
    )
    attachment.file_size = upload_result["size"]
    attachment.checksum_sha256 = upload_result["hash"]

    await db.commit()
    await db.refresh(attachment)

    return build_response(
        data=AttachmentResponse.model_validate(attachment),
        message=f"Attachment updated to version {attachment.current_version}",
    )


@router.get("/{attachment_id}/versions", response_model=None)
async def list_versions(
    attachment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get all versions of an attachment."""
    # Verify attachment exists
    attach_query = select(Attachment).where(Attachment.id == attachment_id)
    attach_result = await db.execute(attach_query)
    attachment = attach_result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    # Get versions
    query = (
        select(AttachmentVersion)
        .where(AttachmentVersion.attachment_id == attachment_id)
        .order_by(AttachmentVersion.version_number.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    return build_response(
        data=[VersionResponse.model_validate(v) for v in versions],
        message=f"Found {len(versions)} version(s)",
    )


@router.get("/{attachment_id}/versions/{version_number}", response_model=None)
async def get_version(
    attachment_id: UUID,
    version_number: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get a specific version of an attachment."""
    query = select(AttachmentVersion).where(
        and_(
            AttachmentVersion.attachment_id == attachment_id,
            AttachmentVersion.version_number == version_number,
        )
    )
    result = await db.execute(query)
    version = result.scalar_one_or_none()

    if not version:
        raise NotFoundError("Attachment version")

    return build_response(
        data=VersionResponse.model_validate(version),
        message="Version retrieved successfully",
    )


@router.post("/{attachment_id}/versions/{version_number}/restore", response_model=None)
async def restore_version(
    attachment_id: UUID,
    version_number: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Restore an attachment to a specific version.
    
    Creates a new version and restores the file from the specified version.
    """
    # Get the version to restore
    version_query = select(AttachmentVersion).where(
        and_(
            AttachmentVersion.attachment_id == attachment_id,
            AttachmentVersion.version_number == version_number,
        )
    )
    version_result = await db.execute(version_query)
    version = version_result.scalar_one_or_none()

    if not version:
        raise NotFoundError("Attachment version")

    # Get the attachment
    attach_query = select(Attachment).where(Attachment.id == attachment_id)
    attach_result = await db.execute(attach_query)
    attachment = attach_result.scalar_one_or_none()

    if not attachment:
        raise NotFoundError("Attachment")

    # Save current state as a version
    current_version = AttachmentVersion(
        attachment_id=attachment.id,
        version_number=attachment.current_version,
        filename=attachment.filename,
        file_size=attachment.file_size,
        mime_type=attachment.mime_type,
        storage_bucket=attachment.storage_bucket,
        storage_key=attachment.storage_key,
        checksum_md5=attachment.checksum_md5,
        checksum_sha256=attachment.checksum_sha256,
        created_by_id=current_user.id,
        change_reason=f"Before restoring to version {version_number}",
        is_current=False,
    )
    db.add(current_version)

    # Restore attachment from version
    attachment.filename = version.filename
    attachment.file_size = version.file_size
    attachment.mime_type = version.mime_type
    attachment.storage_bucket = version.storage_bucket
    attachment.storage_key = version.storage_key
    attachment.checksum_md5 = version.checksum_md5
    attachment.checksum_sha256 = version.checksum_sha256
    attachment.current_version += 1
    attachment.revision = version.revision
    attachment.uploaded_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(attachment)

    return build_response(
        data=AttachmentResponse.model_validate(attachment),
        message=f"Attachment restored to version {version_number} as version {attachment.current_version}",
    )


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get("/entity/{entity_type}/{entity_id}", response_model=None)
async def get_entity_attachments(
    entity_type: str,
    entity_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    category: AttachmentCategory | None = Query(None),
    include_deleted: bool = Query(False),
) -> dict[str, Any]:
    """Get all attachments for a specific entity."""
    conditions = [
        Attachment.entity_type == entity_type,
        Attachment.entity_id == entity_id,
    ]

    if not include_deleted:
        conditions.append(Attachment.deleted_at.is_(None))  # noqa: E712

    if category:
        conditions.append(Attachment.category == category.value)

    query = (
        select(Attachment)
        .where(and_(*conditions))
        .order_by(Attachment.uploaded_at.desc())
    )
    result = await db.execute(query)
    attachments = result.scalars().all()

    return build_response(
        data=[AttachmentResponse.model_validate(a) for a in attachments],
        message=f"Found {len(attachments)} attachment(s)",
    )


@router.get("/my-uploads", response_model=None)
async def get_my_uploads(
    db: DBSession,
    current_user: CurrentUser,
    category: AttachmentCategory | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get attachments uploaded by the current user."""
    conditions = [
        Attachment.uploaded_by_id == current_user.id,
        Attachment.deleted_at.is_(None),  # noqa: E712
    ]

    if category:
        conditions.append(Attachment.category == category.value)

    # Count
    count_query = select(func.count(Attachment.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(Attachment)
        .where(and_(*conditions))
        .order_by(Attachment.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    attachments = data_result.scalars().all()

    return build_paginated_response(
        data=[AttachmentResponse.model_validate(a) for a in attachments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recent", response_model=None)
async def get_recent_attachments(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    """Get recently uploaded attachments."""
    query = (
        select(Attachment)
        .where(Attachment.deleted_at.is_(None))  # noqa: E712
        .order_by(Attachment.uploaded_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    attachments = result.scalars().all()

    return build_response(
        data=[AttachmentResponse.model_validate(a) for a in attachments],
        message=f"Found {len(attachments)} recent attachment(s)",
    )


@router.get("/by-category", response_model=None)
async def get_attachments_by_category(
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Get attachment counts grouped by category."""
    query = (
        select(Attachment.category, func.count(Attachment.id).label("count"))
        .where(Attachment.deleted_at.is_(None))  # noqa: E712
        .group_by(Attachment.category)
    )
    result = await db.execute(query)
    rows = result.all()

    category_counts = {row[0]: row[1] for row in rows}

    return build_response(
        data=category_counts,
        message="Attachment counts by category",
    )


@router.get("/confidential", response_model=None)
async def get_confidential_attachments(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Get all confidential attachments."""
    conditions = [
        Attachment.is_confidential.is_(True),  # noqa: E712
        Attachment.deleted_at.is_(None),  # noqa: E712
    ]

    # Count
    count_query = select(func.count(Attachment.id)).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Data
    data_query = (
        select(Attachment)
        .where(and_(*conditions))
        .order_by(Attachment.uploaded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    attachments = data_result.scalars().all()

    return build_paginated_response(
        data=[AttachmentResponse.model_validate(a) for a in attachments],
        total=total,
        page=page,
        page_size=page_size,
    )
