"""
Entity provider factories for production wiring.

These helpers map service entity types to SQLAlchemy models and provide
CRUD/query operations backed by the database.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from sensei.models import (
    A3,
    Account,
    AnalyticsExportedRecord,
    Attachment,
    AuditLog,
    CAPA,
    CTQ,
    Contact,
    Notification,
    Opportunity,
    Product,
    Project,
    Quote,
    RFQ,
    RefreshToken,
    Risk,
    StandardWork,
    Task,
    TaskComment,
    User,
    UserRole,
    Role,
    RolePermission,
    WorkOrder,
)
from sensei.services.core.access_review import (
    AccessItem,
    AccessType,
    RiskLevel,
    UserAccess,
)
from sensei.services.utils.csv_export import ExportConfig


MODEL_MAP: dict[str, type] = {
    "opportunity": Opportunity,
    "rfq": RFQ,
    "quote": Quote,
    "task": Task,
    "account": Account,
    "contact": Contact,
    "attachment": Attachment,
    "audit_log": AuditLog,
    "notification": Notification,
    "session": RefreshToken,
    "export": AnalyticsExportedRecord,
    "work_order": WorkOrder,
    "comment": TaskComment,
    "product": Product,
    "risk": Risk,
    "capa": CAPA,
    "project": Project,
    "a3": A3,
    "ctq": CTQ,
    "checklist": Task,
    "user": User,
    "customer": Account,
}

DRAFT_MODELS: tuple[type, ...] = (
    RFQ,
    Quote,
    WorkOrder,
    A3,
    CTQ,
    StandardWork,
)


def _normalize_entity_type(entity_type: str | Enum) -> str:
    if isinstance(entity_type, Enum):
        return str(entity_type.value).lower()
    return str(entity_type).lower()


def _resolve_model(entity_type: str | Enum) -> type | None:
    return MODEL_MAP.get(_normalize_entity_type(entity_type))


def _model_to_dict(instance: Any) -> dict[str, Any]:
    return {column.key: getattr(instance, column.key) for column in instance.__table__.columns}


def _apply_filters(query, model: type, filters: dict[str, Any]) -> Any:
    for key, value in filters.items():
        if not hasattr(model, key):
            continue
        column = getattr(model, key)
        if value is None:
            query = query.where(column.is_(None))
        elif isinstance(value, (list, tuple, set)):
            query = query.where(column.in_(list(value)))
        else:
            query = query.where(column == value)
    return query


def _apply_updates(instance: Any, updates: dict[str, Any]) -> None:
    columns = {column.key for column in instance.__table__.columns}
    for key, value in updates.items():
        if key in columns:
            setattr(instance, key, value)
    if "updated_at" in columns and "updated_at" not in updates:
        setattr(instance, "updated_at", datetime.now(timezone.utc))


def build_entity_getter(session: Session) -> Callable[[str | Enum, UUID], dict[str, Any] | None]:
    def _getter(entity_type: str | Enum, entity_id: UUID) -> dict[str, Any] | None:
        normalized = _normalize_entity_type(entity_type)
        if normalized == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is not None and getattr(instance, "status", None) == "draft":
                    return _model_to_dict(instance)
            return None
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        return _model_to_dict(instance) if instance else None

    return _getter


def build_entity_lister(session: Session) -> Callable[[str | Enum], list[dict[str, Any]]]:
    def _lister(entity_type: str | Enum) -> list[dict[str, Any]]:
        normalized = _normalize_entity_type(entity_type)
        if normalized == "draft":
            results: list[dict[str, Any]] = []
            for model in DRAFT_MODELS:
                if not hasattr(model, "status"):
                    continue
                result = session.execute(select(model).where(getattr(model, "status") == "draft"))
                results.extend(_model_to_dict(item) for item in result.scalars().all())
            return results
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        result = session.execute(select(model))
        return [_model_to_dict(item) for item in result.scalars().all()]

    return _lister


def build_entity_query(session: Session) -> Callable[[str | Enum, dict[str, Any]], list[dict[str, Any]]]:
    def _query(entity_type: str | Enum, filters: dict[str, Any]) -> list[dict[str, Any]]:
        if _normalize_entity_type(entity_type) == "draft":
            results: list[dict[str, Any]] = []
            for model in DRAFT_MODELS:
                if not hasattr(model, "status"):
                    continue
                draft_filters = {**filters, "status": "draft"}
                query = _apply_filters(select(model), model, draft_filters)
                result = session.execute(query)
                results.extend(_model_to_dict(item) for item in result.scalars().all())
            return results
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        query = _apply_filters(select(model), model, filters)
        result = session.execute(query)
        return [_model_to_dict(item) for item in result.scalars().all()]

    return _query


def build_entity_saver(session: Session) -> Callable[[str | Enum, UUID, dict[str, Any]], None]:
    def _saver(entity_type: str | Enum, entity_id: UUID, entity: dict[str, Any]) -> None:
        if _normalize_entity_type(entity_type) == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is not None:
                    _apply_updates(instance, entity)
                    session.commit()
                    return
            raise ValueError(f"No draft entity found for ID {entity_id}")
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        columns = {column.key for column in model.__table__.columns}
        if instance is None:
            payload = {k: v for k, v in entity.items() if k in columns}
            payload["id"] = entity_id
            instance = model(**payload)
            session.add(instance)
        else:
            _apply_updates(instance, entity)
        session.commit()

    return _saver


def build_entity_updater(session: Session) -> Callable[[str | Enum, UUID, dict[str, Any]], bool]:
    def _updater(entity_type: str | Enum, entity_id: UUID, updates: dict[str, Any]) -> bool:
        if _normalize_entity_type(entity_type) == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is not None and getattr(instance, "status", None) == "draft":
                    _apply_updates(instance, updates)
                    session.commit()
                    return True
            return False
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        if not instance:
            return False
        _apply_updates(instance, updates)
        session.commit()
        return True

    return _updater


def build_entity_archiver(session: Session) -> Callable[[str | Enum, UUID], bool]:
    def _archiver(entity_type: str | Enum, entity_id: UUID) -> bool:
        if _normalize_entity_type(entity_type) == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is not None and getattr(instance, "status", None) == "draft":
                    columns = {column.key for column in instance.__table__.columns}
                    now = datetime.now(timezone.utc)
                    if "archived_at" in columns:
                        setattr(instance, "archived_at", now)
                    elif "is_archived" in columns:
                        setattr(instance, "is_archived", True)
                    elif "deleted_at" in columns:
                        setattr(instance, "deleted_at", now)
                    else:
                        return False
                    session.commit()
                    return True
            return False
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        if not instance:
            return False
        columns = {column.key for column in instance.__table__.columns}
        now = datetime.now(timezone.utc)
        if "archived_at" in columns:
            setattr(instance, "archived_at", now)
        elif "is_archived" in columns:
            setattr(instance, "is_archived", True)
        elif "deleted_at" in columns:
            setattr(instance, "deleted_at", now)
        else:
            return False
        session.commit()
        return True

    return _archiver


def build_entity_deleter(session: Session) -> Callable[[str | Enum, UUID, bool], bool]:
    def _deleter(entity_type: str | Enum, entity_id: UUID, force: bool = False) -> bool:
        if _normalize_entity_type(entity_type) == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is not None and getattr(instance, "status", None) == "draft":
                    columns = {column.key for column in instance.__table__.columns}
                    if not force and "deleted_at" in columns:
                        setattr(instance, "deleted_at", datetime.now(timezone.utc))
                    else:
                        session.delete(instance)
                    session.commit()
                    return True
            return False
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        if not instance:
            return False
        columns = {column.key for column in instance.__table__.columns}
        if not force and "deleted_at" in columns:
            setattr(instance, "deleted_at", datetime.now(timezone.utc))
        else:
            session.delete(instance)
        session.commit()
        return True

    return _deleter


def build_archived_lister(session: Session) -> Callable[[str | Enum], list[dict[str, Any]]]:
    def _lister(entity_type: str | Enum) -> list[dict[str, Any]]:
        if _normalize_entity_type(entity_type) == "draft":
            results: list[dict[str, Any]] = []
            for model in DRAFT_MODELS:
                columns = {column.key for column in model.__table__.columns}
                query = select(model)
                if "archived_at" in columns:
                    query = query.where(getattr(model, "archived_at").is_not(None))
                elif "is_archived" in columns:
                    query = query.where(getattr(model, "is_archived").is_(True))
                elif "deleted_at" in columns:
                    query = query.where(getattr(model, "deleted_at").is_not(None))
                else:
                    continue
                result = session.execute(query)
                results.extend(_model_to_dict(item) for item in result.scalars().all())
            return results
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        columns = {column.key for column in model.__table__.columns}
        query = select(model)
        if "archived_at" in columns:
            query = query.where(getattr(model, "archived_at").is_not(None))
        elif "is_archived" in columns:
            query = query.where(getattr(model, "is_archived").is_(True))
        elif "deleted_at" in columns:
            query = query.where(getattr(model, "deleted_at").is_not(None))
        else:
            return []
        result = session.execute(query)
        return [_model_to_dict(item) for item in result.scalars().all()]

    return _lister


def build_archived_restorer(session: Session) -> Callable[[str | Enum, UUID], bool]:
    def _restorer(entity_type: str | Enum, entity_id: UUID) -> bool:
        if _normalize_entity_type(entity_type) == "draft":
            for model in DRAFT_MODELS:
                instance = session.get(model, entity_id)
                if instance is None:
                    continue
                columns = {column.key for column in instance.__table__.columns}
                if "archived_at" in columns:
                    setattr(instance, "archived_at", None)
                elif "is_archived" in columns:
                    setattr(instance, "is_archived", False)
                elif "deleted_at" in columns:
                    setattr(instance, "deleted_at", None)
                else:
                    return False
                session.commit()
                return True
            return False
        model = _resolve_model(entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {entity_type}")
        instance = session.get(model, entity_id)
        if not instance:
            return False
        columns = {column.key for column in instance.__table__.columns}
        if "archived_at" in columns:
            setattr(instance, "archived_at", None)
        elif "is_archived" in columns:
            setattr(instance, "is_archived", False)
        elif "deleted_at" in columns:
            setattr(instance, "deleted_at", None)
        else:
            return False
        session.commit()
        return True

    return _restorer


def build_export_entity_provider(session: Session) -> Callable[[ExportConfig], list[dict[str, Any]]]:
    def _provider(config: ExportConfig) -> list[dict[str, Any]]:
        model = _resolve_model(config.entity_type)
        if not model:
            raise ValueError(f"No model mapping for entity type {config.entity_type}")
        query = _apply_filters(select(model), model, config.filters)
        if config.sort_by and hasattr(model, config.sort_by):
            column = getattr(model, config.sort_by)
            query = query.order_by(column.desc() if config.sort_descending else column.asc())
        if config.offset:
            query = query.offset(config.offset)
        if config.limit is not None:
            query = query.limit(config.limit)
        result = session.execute(query)
        return [_model_to_dict(item) for item in result.scalars().all()]

    return _provider


def build_user_access_provider(session: Session) -> Callable[[list[str]], list[UserAccess]]:
    def _risk_level_for_role(role_name: str) -> RiskLevel:
        normalized = role_name.lower()
        if "admin" in normalized or "gm" in normalized:
            return RiskLevel.CRITICAL
        if "exec" in normalized or "finance" in normalized:
            return RiskLevel.HIGH
        if "manager" in normalized or "lead" in normalized:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _risk_level_for_permission(resource: str, action: str) -> RiskLevel:
        if action in {"delete", "approve", "manage", "export"}:
            return RiskLevel.HIGH
        if resource in {"security", "admin", "billing", "finance", "hr"}:
            return RiskLevel.HIGH
        if action in {"write", "update"}:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _provider(roles: list[str]) -> list[UserAccess]:
        if not roles:
            return []
        query = (
            select(UserRole)
            .join(Role)
            .options(
                selectinload(UserRole.user),
                selectinload(UserRole.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission),
            )
            .where(Role.name.in_(roles), UserRole.is_active.is_(True))
        )
        user_roles = session.execute(query).scalars().all()
        users: dict[UUID, dict[str, Any]] = {}
        for user_role in user_roles:
            user = user_role.user
            role = user_role.role
            if not user or not role:
                continue
            entry = users.get(user.id)
            if entry is None:
                entry = {
                    "user": user,
                    "access_items": [],
                    "access_item_ids": set(),
                }
                users[user.id] = entry
            access_items: list[AccessItem] = entry["access_items"]
            access_item_ids: set[UUID] = entry["access_item_ids"]

            if role.id not in access_item_ids:
                access_item_ids.add(role.id)
                access_items.append(
                    AccessItem(
                        id=role.id,
                        access_type=AccessType.ROLE,
                        name=role.name,
                        description=role.description or role.display_name,
                        risk_level=_risk_level_for_role(role.name),
                        granted_at=user_role.assigned_at or user_role.created_at,
                        granted_by=user_role.assigned_by_id,
                        last_used=None,
                        usage_count=0,
                        is_active=user_role.is_active and not user_role.is_expired,
                    )
                )

            for role_permission in role.permissions:
                permission = role_permission.permission
                if not permission or permission.id in access_item_ids:
                    continue
                access_item_ids.add(permission.id)
                access_items.append(
                    AccessItem(
                        id=permission.id,
                        access_type=AccessType.PERMISSION,
                        name=permission.name,
                        description=permission.description or permission.display_name,
                        risk_level=_risk_level_for_permission(permission.resource, permission.action),
                        granted_at=role_permission.created_at,
                        granted_by=None,
                        last_used=None,
                        usage_count=0,
                        is_active=True,
                    )
                )

        user_access_list: list[UserAccess] = []
        for entry in users.values():
            user = entry["user"]
            access_items = entry["access_items"]
            risk_score = sum(
                {
                    RiskLevel.LOW: 1,
                    RiskLevel.MEDIUM: 2,
                    RiskLevel.HIGH: 3,
                    RiskLevel.CRITICAL: 4,
                }[item.risk_level]
                for item in access_items
            )
            user_access_list.append(
                UserAccess(
                    user_id=user.id,
                    user_name=user.display_name or f"{user.first_name} {user.last_name}",
                    user_email=user.email,
                    department=user.department,
                    manager_id=None,
                    access_items=access_items,
                    total_risk_score=float(risk_score),
                )
            )
        return user_access_list

    return _provider
