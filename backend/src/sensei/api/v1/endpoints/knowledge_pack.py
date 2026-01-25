from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.schemas import APIResponse
from sensei.models.user import User
from sensei.api.utils import build_response
from sensei.services.ai.knowledge_enrichment import (
    ContentFormat,
    KnowledgeEnrichmentService,
    SourceType,
)

router = APIRouter()

_service = KnowledgeEnrichmentService()


_KNOWLEDGE_READER_ROLES = frozenset(
    {
        "admin",
        "knowledge_curator",
        "ml_engineer",
        "gm",
        "ops",
        "auditor",
        "ceo",
    }
)

_KNOWLEDGE_CURATOR_ROLES = frozenset({"admin", "knowledge_curator", "ml_engineer"})


class KnowledgeSourceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    uri: str
    is_active: bool
    metadata_fields: dict[str, Any]


class KnowledgePackResponse(BaseModel):
    id: UUID
    name: str
    description: str
    source_ids: list[UUID]
    created_at: datetime
    is_active: bool
    sources: list[KnowledgeSourceResponse] = Field(default_factory=list)


class RegisterSourceRequest(BaseModel):
    name: str
    url: str
    content_format: ContentFormat
    license_type: str
    tags: list[str] = Field(default_factory=list)


class CreatePackRequest(BaseModel):
    name: str
    description: str
    source_ids: list[UUID]


class IngestContentRequest(BaseModel):
    source_id: UUID
    content: str
    chunk_size: int = 1500
    overlap: int = 200


class KnowledgeSourceRecordResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    uri: str
    is_active: bool
    metadata_fields: dict[str, Any]


def _roles_for_user(user: Any) -> set[str]:
    if hasattr(user, "get_role_names"):
        return {role.lower() for role in user.get_role_names()}
    if hasattr(user, "roles"):
        return {getattr(role, "name", "").lower() for role in user.roles}
    return set()


def _require_reader(roles: set[str]) -> None:
    if not roles or not (roles & _KNOWLEDGE_READER_ROLES):
        raise HTTPException(status_code=403, detail="Access denied")


def _require_curator(roles: set[str]) -> None:
    if not roles or not (roles & _KNOWLEDGE_CURATOR_ROLES):
        raise HTTPException(status_code=403, detail="Knowledge curator access required")


def _to_source_response(source: Any) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        uri=source.uri,
        is_active=source.is_active,
        metadata_fields=source.metadata_fields or {},
    )


def _to_pack_response(pack: Any) -> KnowledgePackResponse:
    sources = [link.source for link in pack.sources] if getattr(pack, "sources", None) else []
    return KnowledgePackResponse(
        id=pack.id,
        name=pack.name,
        description=pack.description,
        source_ids=[link.source_id for link in pack.sources] if getattr(pack, "sources", None) else [],
        created_at=pack.created_at,
        is_active=pack.is_active,
        sources=[_to_source_response(source) for source in sources],
    )


@router.get(
    "/knowledge-pack/sources",
    response_model=APIResponse[list[KnowledgeSourceResponse]],
)
async def list_sources(
    source_type: SourceType | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[list[KnowledgeSourceResponse]]:
    """List knowledge sources stored in the database."""
    roles = _roles_for_user(current_user)
    _require_reader(roles)
    sources = await _service.get_sources(db)
    if source_type:
        sources = [s for s in sources if s.source_type == source_type.value]
    if tag:
        sources = [s for s in sources if tag in (s.metadata_fields or {}).get("tags", [])]
    return build_response([_to_source_response(source) for source in sources])


@router.post(
    "/knowledge-pack/sources/custom",
    response_model=APIResponse[KnowledgeSourceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register_custom_source(
    payload: RegisterSourceRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[KnowledgeSourceResponse]:
    """Register a custom knowledge source stored in the database."""
    roles = _roles_for_user(current_user)
    _require_curator(roles)
    try:
        source = await _service.add_custom_source(
            db,
            name=payload.name,
            uri=payload.url,
            source_type=SourceType.CUSTOM_PDF,
            metadata={
                "content_format": payload.content_format.value,
                "license_type": payload.license_type,
                "tags": payload.tags,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_response(_to_source_response(source))


@router.post(
    "/knowledge-pack/sources/initialize",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def initialize_default_sources(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[dict[str, Any]]:
    """Seed default knowledge sources into the database."""
    roles = _roles_for_user(current_user)
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    await _service.initialize_default_sources(db)
    return build_response({"status": "ok"})


@router.get(
    "/knowledge-pack/sources/db",
    response_model=APIResponse[list[KnowledgeSourceRecordResponse]],
)
async def list_sources_db(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[list[KnowledgeSourceRecordResponse]]:
    """List knowledge sources stored in the database."""
    roles = _roles_for_user(current_user)
    _require_reader(roles)
    sources = await _service.get_sources(db)
    return build_response(
        [
            KnowledgeSourceRecordResponse(
                id=src.id,
                name=src.name,
                source_type=src.source_type,
                uri=src.uri,
                is_active=src.is_active,
                metadata_fields=src.metadata_fields or {},
            )
            for src in sources
        ]
    )


@router.post(
    "/knowledge-pack/ingest",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_content(
    payload: IngestContentRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[dict[str, Any]]:
    """Ingest content into semantic chunks stored in the database."""
    roles = _roles_for_user(current_user)
    _require_curator(roles)
    try:
        chunks = await _service.ingest_content(
            db,
            source_id=payload.source_id,
            content=payload.content,
            chunk_size=payload.chunk_size,
            overlap=payload.overlap,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_response({"chunks": len(chunks)})


@router.post(
    "/knowledge-pack/packs",
    response_model=APIResponse[KnowledgePackResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_pack(
    payload: CreatePackRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[KnowledgePackResponse]:
    """Create a knowledge pack from existing database sources."""
    roles = _roles_for_user(current_user)
    _require_curator(roles)
    _ = request
    try:
        pack = await _service.create_pack_db(
            db,
            actor_id=current_user.id,
            name=payload.name,
            description=payload.description,
            source_ids=payload.source_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_response(_to_pack_response(pack))


@router.get(
    "/knowledge-pack/packs",
    response_model=APIResponse[list[KnowledgePackResponse]],
)
async def list_packs(
    active_only: bool = True,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[list[KnowledgePackResponse]]:
    """List knowledge packs."""
    roles = _roles_for_user(current_user)
    _require_reader(roles)
    packs = await _service.list_packs_db(db, active_only=active_only)
    return build_response([_to_pack_response(pack) for pack in packs])


@router.post(
    "/knowledge-pack/packs/{pack_id}/deactivate",
    response_model=APIResponse[KnowledgePackResponse],
)
async def deactivate_pack(
    pack_id: UUID,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[KnowledgePackResponse]:
    """Deactivate a knowledge pack."""
    roles = _roles_for_user(current_user)
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    _ = request
    try:
        pack = await _service.deactivate_pack_db(db, pack_id=pack_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_response(_to_pack_response(pack))
