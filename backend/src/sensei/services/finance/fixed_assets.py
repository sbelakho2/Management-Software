"""Fixed Assets (Accounting) service.

Implements Development Plan Section 22.5:
- Capitalization workflow from maintenance/asset register
- Depreciation schedules (monthly) with optional GL postings
- Asset events (transfer, impairment, disposal) with audit trail

State is persisted via the service_state table for DB-backed continuity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _q2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _norm_currency(c: str) -> str:
    cc = (c or "").strip().upper()
    if len(cc) != 3 or not cc.isalpha():
        raise ValueError("Invalid currency")
    return cc


_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _encode_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _decode_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _encode_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _encode_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _decode_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _encode_audit_event(event: "AuditEvent") -> dict[str, Any]:
    return {
        "id": str(event.id),
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "correlation_id": event.correlation_id,
        "metadata": event.metadata,
    }


def _decode_audit_event(data: dict[str, Any]) -> "AuditEvent":
    return AuditEvent(
        id=UUID(data["id"]),
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
        actor_id=data["actor_id"],
        action=data["action"],
        entity_type=data["entity_type"],
        entity_id=data["entity_id"],
        correlation_id=data.get("correlation_id", ""),
        metadata=data.get("metadata", {}) or {},
    )


def _encode_asset(asset: "FixedAsset") -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "asset_tag": asset.asset_tag,
        "name": asset.name,
        "currency": asset.currency,
        "capitalization_date": asset.capitalization_date.isoformat(),
        "in_service_date": asset.in_service_date.isoformat(),
        "acquisition_cost": _encode_decimal(asset.acquisition_cost),
        "residual_value": _encode_decimal(asset.residual_value),
        "useful_life_months": asset.useful_life_months,
        "method": asset.method.value,
        "source_system": asset.source_system,
        "source_asset_id": asset.source_asset_id,
        "status": asset.status.value,
        "disposed_at": _encode_datetime(asset.disposed_at),
        "disposed_by": asset.disposed_by,
        "location": asset.location,
        "cost_center": asset.cost_center,
        "accumulated_depreciation": _encode_decimal(asset.accumulated_depreciation),
        "impairment_loss_total": _encode_decimal(asset.impairment_loss_total),
        "metadata": asset.metadata,
    }


def _decode_asset(data: dict[str, Any]) -> "FixedAsset":
    return FixedAsset(
        id=UUID(data["id"]),
        asset_tag=data.get("asset_tag", ""),
        name=data.get("name", ""),
        currency=data.get("currency", ""),
        capitalization_date=date.fromisoformat(data["capitalization_date"]),
        in_service_date=date.fromisoformat(data["in_service_date"]),
        acquisition_cost=Decimal(data.get("acquisition_cost", "0")),
        residual_value=Decimal(data.get("residual_value", "0")),
        useful_life_months=int(data.get("useful_life_months", 0)),
        method=DepreciationMethod(data.get("method", DepreciationMethod.STRAIGHT_LINE.value)),
        source_system=data.get("source_system"),
        source_asset_id=data.get("source_asset_id"),
        status=FixedAssetStatus(data.get("status", FixedAssetStatus.IN_SERVICE.value)),
        disposed_at=_decode_datetime(data.get("disposed_at")),
        disposed_by=data.get("disposed_by"),
        location=data.get("location"),
        cost_center=data.get("cost_center"),
        accumulated_depreciation=Decimal(data.get("accumulated_depreciation", "0")),
        impairment_loss_total=Decimal(data.get("impairment_loss_total", "0")),
        metadata=data.get("metadata", {}) or {},
    )


def _encode_depreciation_posting(posting: "DepreciationPosting") -> dict[str, Any]:
    return {
        "id": str(posting.id),
        "asset_id": str(posting.asset_id),
        "period_key": posting.period_key,
        "amount": _encode_decimal(posting.amount),
        "posted_at": posting.posted_at.isoformat(),
        "posted_by": posting.posted_by,
        "journal_entry_id": str(posting.journal_entry_id) if posting.journal_entry_id else None,
    }


def _decode_depreciation_posting(data: dict[str, Any]) -> "DepreciationPosting":
    journal_entry_id = data.get("journal_entry_id")
    return DepreciationPosting(
        id=UUID(data["id"]),
        asset_id=UUID(data["asset_id"]),
        period_key=data.get("period_key", ""),
        amount=Decimal(data.get("amount", "0")),
        posted_at=datetime.fromisoformat(data["posted_at"]),
        posted_by=data.get("posted_by", ""),
        journal_entry_id=UUID(journal_entry_id) if journal_entry_id else None,
    )


def _encode_asset_event(event: "AssetEvent") -> dict[str, Any]:
    return {
        "id": str(event.id),
        "asset_id": str(event.asset_id),
        "event_type": event.event_type.value,
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "correlation_id": event.correlation_id,
        "amount": _encode_decimal(event.amount),
        "details": event.details,
    }


def _decode_asset_event(data: dict[str, Any]) -> "AssetEvent":
    return AssetEvent(
        id=UUID(data["id"]),
        asset_id=UUID(data["asset_id"]),
        event_type=AssetEventType(data.get("event_type", AssetEventType.CAPITALIZED.value)),
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
        actor_id=data.get("actor_id", ""),
        correlation_id=data.get("correlation_id", ""),
        amount=_decode_decimal(data.get("amount")),
        details=data.get("details", {}) or {},
    )


def _encode_config(cfg: "FixedAssetsConfig") -> dict[str, Any]:
    return {
        "base_currency": cfg.base_currency,
        "fixed_asset_account_code": cfg.fixed_asset_account_code,
        "accumulated_depr_account_code": cfg.accumulated_depr_account_code,
        "depreciation_expense_account_code": cfg.depreciation_expense_account_code,
        "asset_clearing_account_code": cfg.asset_clearing_account_code,
        "impairment_loss_account_code": cfg.impairment_loss_account_code,
        "disposal_gain_loss_account_code": cfg.disposal_gain_loss_account_code,
        "cash_account_code": cfg.cash_account_code,
    }


def _decode_config(data: dict[str, Any], fallback: "FixedAssetsConfig") -> "FixedAssetsConfig":
    return FixedAssetsConfig(
        base_currency=data.get("base_currency", fallback.base_currency),
        fixed_asset_account_code=data.get(
            "fixed_asset_account_code", fallback.fixed_asset_account_code
        ),
        accumulated_depr_account_code=data.get(
            "accumulated_depr_account_code", fallback.accumulated_depr_account_code
        ),
        depreciation_expense_account_code=data.get(
            "depreciation_expense_account_code", fallback.depreciation_expense_account_code
        ),
        asset_clearing_account_code=data.get(
            "asset_clearing_account_code", fallback.asset_clearing_account_code
        ),
        impairment_loss_account_code=data.get(
            "impairment_loss_account_code", fallback.impairment_loss_account_code
        ),
        disposal_gain_loss_account_code=data.get(
            "disposal_gain_loss_account_code", fallback.disposal_gain_loss_account_code
        ),
        cash_account_code=data.get("cash_account_code", fallback.cash_account_code),
    )


# ---------------------- RBAC Role Sets ----------------------

_FINANCE_READ_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
    "auditor",
}

_FINANCE_WRITE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}

_FINANCE_APPROVE_ROLES: set[str] = {
    "admin",
    "ceo",
    "exec",
    "gm",
    "finance",
    "accountant",
}


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


# ---------------------- Enums ----------------------


class DepreciationMethod(str, Enum):
    STRAIGHT_LINE = "straight_line"


class FixedAssetStatus(str, Enum):
    IN_SERVICE = "in_service"
    DISPOSED = "disposed"


class AssetEventType(str, Enum):
    CAPITALIZED = "capitalized"
    DEPRECIATION = "depreciation"
    TRANSFER = "transfer"
    IMPAIRMENT = "impairment"
    DISPOSAL = "disposal"


# ---------------------- Dataclasses ----------------------


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    occurred_at: datetime
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FixedAsset:
    id: UUID
    asset_tag: str
    name: str
    currency: str

    capitalization_date: date
    in_service_date: date

    acquisition_cost: Decimal
    residual_value: Decimal
    useful_life_months: int
    method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE

    source_system: str | None = None
    source_asset_id: str | None = None

    status: FixedAssetStatus = FixedAssetStatus.IN_SERVICE
    disposed_at: datetime | None = None
    disposed_by: str | None = None

    location: str | None = None
    cost_center: str | None = None

    accumulated_depreciation: Decimal = Decimal("0")
    impairment_loss_total: Decimal = Decimal("0")

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def depreciable_base(self) -> Decimal:
        base = _q2(self.acquisition_cost - self.residual_value)
        return base if base > 0 else Decimal("0")

    @property
    def carrying_amount(self) -> Decimal:
        return _q2(
            self.acquisition_cost
            - self.accumulated_depreciation
            - self.impairment_loss_total
        )


@dataclass(frozen=True)
class DepreciationPosting:
    id: UUID
    asset_id: UUID
    period_key: str  # YYYY-MM
    amount: Decimal
    posted_at: datetime
    posted_by: str
    journal_entry_id: UUID | None = None


@dataclass(frozen=True)
class DisposalResult:
    gain_loss: Decimal
    proceeds: Decimal
    carrying_amount: Decimal


@dataclass(frozen=True)
class AssetEvent:
    """Immutable record of an asset event for audit trail."""

    id: UUID
    asset_id: UUID
    event_type: AssetEventType
    occurred_at: datetime
    actor_id: str
    correlation_id: str
    amount: Decimal | None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class FixedAssetsConfig:
    base_currency: str = "EUR"

    # GL accounts (defaults; can be overridden)
    fixed_asset_account_code: str = "1500"
    accumulated_depr_account_code: str = "1590"
    depreciation_expense_account_code: str = "6100"

    asset_clearing_account_code: str = "2100"  # e.g. AP clearing

    impairment_loss_account_code: str = "6200"
    disposal_gain_loss_account_code: str = "6300"
    cash_account_code: str = "1000"


# ---------------------- Service ----------------------


class FixedAssetsService(PersistentServiceMixin):
    """Fixed asset register with depreciation and optional GL postings.

    In-memory state backed by PostgreSQL fixed_assets and
    depreciation_schedules tables.
    """

    SERVICE_NAME = "fixed_assets"

    def __init__(
        self,
        *,
        config: FixedAssetsConfig | None = None,
        ledger: Any | None = None,
    ):
        self._cfg = config or FixedAssetsConfig()
        self._ledger = ledger

        self._assets_by_id: dict[UUID, FixedAsset] = {}
        self._assets_by_tag: dict[str, UUID] = {}
        self._depr_postings: dict[tuple[UUID, str], DepreciationPosting] = {}
        self._audit: list[AuditEvent] = []
        self._events: list[AssetEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        cfg_data = await self.load_state(_DEFAULT_TENANT_ID, "config") or {}
        assets_data = await self.load_state(_DEFAULT_TENANT_ID, "assets") or {}
        postings_data = await self.load_state(_DEFAULT_TENANT_ID, "depr_postings") or {}
        events_data = await self.load_state(_DEFAULT_TENANT_ID, "events") or []
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        if cfg_data:
            self._cfg = _decode_config(cfg_data, self._cfg)

        self._assets_by_id = {UUID(aid): _decode_asset(a) for aid, a in assets_data.items()}
        self._assets_by_tag = {asset.asset_tag: asset.id for asset in self._assets_by_id.values()}
        self._depr_postings = {
            (p.asset_id, p.period_key): p for p in (_decode_depreciation_posting(item) for item in postings_data)
        }
        self._events = [_decode_asset_event(e) for e in events_data]
        self._audit = [_decode_audit_event(a) for a in audit_data]

        self._state_loaded = True

    async def persist_all(self) -> None:
        cfg_data = _encode_config(self._cfg)
        assets_data = {str(aid): _encode_asset(a) for aid, a in self._assets_by_id.items()}
        postings_data = [_encode_depreciation_posting(p) for p in self._depr_postings.values()]
        events_data = [_encode_asset_event(e) for e in self._events]
        audit_data = [_encode_audit_event(a) for a in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "config", cfg_data)
        await self.save_state(_DEFAULT_TENANT_ID, "assets", assets_data)
        await self.save_state(_DEFAULT_TENANT_ID, "depr_postings", postings_data)
        await self.save_state(_DEFAULT_TENANT_ID, "events", events_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    async def get_asset_async(self, *, actor_roles: Iterable[str], asset_id: UUID) -> FixedAsset | None:
        await self._ensure_loaded()
        return self.get_asset(actor_roles=actor_roles, asset_id=asset_id)

    async def list_assets_async(self, *, actor_roles: Iterable[str], include_disposed: bool = False) -> list[FixedAsset]:
        await self._ensure_loaded()
        return self.list_assets(actor_roles=actor_roles, include_disposed=include_disposed)

    async def list_audit_events_async(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(actor_roles=actor_roles)

    async def list_asset_events_async(self, *, actor_roles: Iterable[str], asset_id: UUID | None = None) -> list[AssetEvent]:
        await self._ensure_loaded()
        return self.list_asset_events(actor_roles=actor_roles, asset_id=asset_id)

    async def get_depreciation_postings_async(self, *, actor_roles: Iterable[str], asset_id: UUID) -> list[DepreciationPosting]:
        await self._ensure_loaded()
        return self.get_depreciation_postings(actor_roles=actor_roles, asset_id=asset_id)

    async def capitalize_from_source_async(self, **kwargs: Any) -> FixedAsset:
        await self._ensure_loaded()
        asset = self.capitalize_from_source(**kwargs)
        await self.persist_all()
        return asset

    async def compute_monthly_depreciation_async(self, *, actor_roles: Iterable[str], asset_id: UUID) -> Decimal:
        await self._ensure_loaded()
        return self.compute_monthly_depreciation(actor_roles=actor_roles, asset_id=asset_id)

    async def post_monthly_depreciation_async(self, **kwargs: Any) -> DepreciationPosting:
        await self._ensure_loaded()
        posting = self.post_monthly_depreciation(**kwargs)
        await self.persist_all()
        return posting

    async def transfer_asset_async(self, **kwargs: Any) -> FixedAsset:
        await self._ensure_loaded()
        asset = self.transfer_asset(**kwargs)
        await self.persist_all()
        return asset

    async def impair_asset_async(self, **kwargs: Any) -> FixedAsset:
        await self._ensure_loaded()
        asset = self.impair_asset(**kwargs)
        await self.persist_all()
        return asset

    async def dispose_asset_async(self, **kwargs: Any) -> DisposalResult:
        await self._ensure_loaded()
        result = self.dispose_asset(**kwargs)
        await self.persist_all()
        return result

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_asset(
        self, *, actor_roles: Iterable[str], asset_id: UUID
    ) -> FixedAsset | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        return self._assets_by_id.get(asset_id)

    def list_assets(
        self, *, actor_roles: Iterable[str], include_disposed: bool = False
    ) -> list[FixedAsset]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        assets = list(self._assets_by_id.values())
        if not include_disposed:
            assets = [a for a in assets if a.status != FixedAssetStatus.DISPOSED]
        assets.sort(key=lambda a: a.asset_tag)
        return assets

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        return list(self._audit)

    def list_asset_events(
        self, *, actor_roles: Iterable[str], asset_id: UUID | None = None
    ) -> list[AssetEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        events = list(self._events)
        if asset_id is not None:
            events = [e for e in events if e.asset_id == asset_id]
        events.sort(key=lambda e: e.occurred_at)
        return events

    def get_depreciation_postings(
        self, *, actor_roles: Iterable[str], asset_id: UUID
    ) -> list[DepreciationPosting]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        postings = [p for p in self._depr_postings.values() if p.asset_id == asset_id]
        postings.sort(key=lambda p: p.period_key)
        return postings

    # ------------------------------------------------------------------
    # Capitalization
    # ------------------------------------------------------------------

    def capitalize_from_source(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset_tag: str,
        name: str,
        acquisition_cost: Decimal,
        currency: str | None = None,
        capitalization_date: date | None = None,
        in_service_date: date | None = None,
        residual_value: Decimal = Decimal("0"),
        useful_life_months: int,
        method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
        source_system: str | None = None,
        source_asset_id: str | None = None,
        location: str | None = None,
        cost_center: str | None = None,
        post_to_gl: bool = False,
    ) -> FixedAsset:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")

        tag = (asset_tag or "").strip()
        if not tag:
            raise ValueError("asset_tag required")
        if tag in self._assets_by_tag:
            raise ValueError("asset_tag already exists")

        nm = (name or "").strip()
        if not nm:
            raise ValueError("name required")

        cur = _norm_currency(currency or self._cfg.base_currency)
        cap_date = capitalization_date or date.today()
        svc_date = in_service_date or cap_date

        cost = _q2(acquisition_cost)
        if cost <= 0:
            raise ValueError("acquisition_cost must be > 0")
        rv = _q2(residual_value)
        if rv < 0:
            raise ValueError("residual_value must be >= 0")
        if rv > cost:
            raise ValueError("residual_value cannot exceed acquisition_cost")
        if useful_life_months <= 0:
            raise ValueError("useful_life_months must be > 0")

        asset = FixedAsset(
            id=uuid4(),
            asset_tag=tag,
            name=nm,
            currency=cur,
            capitalization_date=cap_date,
            in_service_date=svc_date,
            acquisition_cost=cost,
            residual_value=rv,
            useful_life_months=int(useful_life_months),
            method=method,
            source_system=(source_system or None),
            source_asset_id=(source_asset_id or None),
            location=(location or None),
            cost_center=(cost_center or None),
        )

        self._assets_by_id[asset.id] = asset
        self._assets_by_tag[tag] = asset.id

        self._record_event(
            asset_id=asset.id,
            event_type=AssetEventType.CAPITALIZED,
            actor_id=actor_id,
            correlation_id=correlation_id,
            amount=cost,
            details={
                "asset_tag": tag,
                "source_system": source_system,
                "source_asset_id": source_asset_id,
                "currency": cur,
            },
        )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fa.capitalize",
            entity_type="fixed_asset",
            entity_id=str(asset.id),
            correlation_id=correlation_id,
            metadata={
                "asset_tag": tag,
                "source_system": source_system,
                "source_asset_id": source_asset_id,
                "acquisition_cost": str(cost),
                "currency": cur,
            },
        )

        if post_to_gl:
            self._post_capitalization_to_gl(
                actor_id=actor_id,
                actor_roles=roles,
                correlation_id=correlation_id,
                asset=asset,
            )

        return asset

    # ------------------------------------------------------------------
    # Depreciation
    # ------------------------------------------------------------------

    def compute_monthly_depreciation(
        self, *, actor_roles: Iterable[str], asset_id: UUID
    ) -> Decimal:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read role required")
        asset = self._require_asset(asset_id)
        if asset.method != DepreciationMethod.STRAIGHT_LINE:
            raise ValueError("Unsupported depreciation method")
        return _q2(asset.depreciable_base / Decimal(str(asset.useful_life_months)))

    def post_monthly_depreciation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset_id: UUID,
        period_key: str,
        post_date: date,
    ) -> DepreciationPosting:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")

        asset = self._require_asset(asset_id)
        if asset.status == FixedAssetStatus.DISPOSED:
            raise ValueError("Asset is disposed")

        pk = (period_key or "").strip()
        if not pk or len(pk) != 7 or pk[4] != "-":
            raise ValueError("period_key must be YYYY-MM")

        key = (asset.id, pk)
        existing = self._depr_postings.get(key)
        if existing is not None:
            return existing

        amt = self.compute_monthly_depreciation(actor_roles=roles, asset_id=asset.id)
        if amt <= 0:
            raise ValueError("Depreciation amount must be > 0")

        # Cap depreciation so carrying amount never goes below residual.
        remaining = _q2(asset.carrying_amount - asset.residual_value)
        if remaining <= 0:
            raise ValueError("No remaining depreciable amount")
        if amt > remaining:
            amt = remaining

        je_id: UUID | None = None
        if self._ledger is not None:
            je_id = self._post_depreciation_to_gl(
                actor_id=actor_id,
                actor_roles=roles,
                correlation_id=correlation_id,
                asset=asset,
                amount=amt,
                post_date=post_date,
            )

        asset.accumulated_depreciation = _q2(asset.accumulated_depreciation + amt)

        posting = DepreciationPosting(
            id=uuid4(),
            asset_id=asset.id,
            period_key=pk,
            amount=_q2(amt),
            posted_at=_now(),
            posted_by=actor_id,
            journal_entry_id=je_id,
        )
        self._depr_postings[key] = posting

        self._record_event(
            asset_id=asset.id,
            event_type=AssetEventType.DEPRECIATION,
            actor_id=actor_id,
            correlation_id=correlation_id,
            amount=_q2(amt),
            details={"period_key": pk},
        )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fa.depreciation.post",
            entity_type="fixed_asset",
            entity_id=str(asset.id),
            correlation_id=correlation_id,
            metadata={"period_key": pk, "amount": str(_q2(amt))},
        )
        return posting

    # ------------------------------------------------------------------
    # Asset events
    # ------------------------------------------------------------------

    def transfer_asset(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset_id: UUID,
        new_location: str | None = None,
        new_cost_center: str | None = None,
        reason: str,
    ) -> FixedAsset:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")

        asset = self._require_asset(asset_id)
        if asset.status == FixedAssetStatus.DISPOSED:
            raise ValueError("Asset is disposed")
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        old_location = asset.location
        old_cost_center = asset.cost_center

        asset.location = new_location or asset.location
        asset.cost_center = new_cost_center or asset.cost_center

        self._record_event(
            asset_id=asset.id,
            event_type=AssetEventType.TRANSFER,
            actor_id=actor_id,
            correlation_id=correlation_id,
            amount=None,
            details={
                "reason": r,
                "old_location": old_location,
                "new_location": asset.location,
                "old_cost_center": old_cost_center,
                "new_cost_center": asset.cost_center,
            },
        )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fa.transfer",
            entity_type="fixed_asset",
            entity_id=str(asset.id),
            correlation_id=correlation_id,
            metadata={
                "reason": r,
                "location": asset.location,
                "cost_center": asset.cost_center,
            },
        )
        return asset

    def impair_asset(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset_id: UUID,
        amount: Decimal,
        impairment_date: date,
        reason: str,
    ) -> FixedAsset:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")

        asset = self._require_asset(asset_id)
        if asset.status == FixedAssetStatus.DISPOSED:
            raise ValueError("Asset is disposed")

        amt = _q2(amount)
        if amt <= 0:
            raise ValueError("amount must be > 0")
        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        if amt > asset.carrying_amount:
            raise ValueError("impairment exceeds carrying amount")

        if self._ledger is not None:
            self._post_impairment_to_gl(
                actor_id=actor_id,
                actor_roles=roles,
                correlation_id=correlation_id,
                asset=asset,
                amount=amt,
                impairment_date=impairment_date,
                reason=r,
            )

        asset.impairment_loss_total = _q2(asset.impairment_loss_total + amt)

        self._record_event(
            asset_id=asset.id,
            event_type=AssetEventType.IMPAIRMENT,
            actor_id=actor_id,
            correlation_id=correlation_id,
            amount=amt,
            details={
                "date": impairment_date.isoformat(),
                "reason": r,
            },
        )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fa.impair",
            entity_type="fixed_asset",
            entity_id=str(asset.id),
            correlation_id=correlation_id,
            metadata={
                "amount": str(amt),
                "date": impairment_date.isoformat(),
                "reason": r,
            },
        )
        return asset

    def dispose_asset(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset_id: UUID,
        disposal_date: date,
        proceeds: Decimal = Decimal("0"),
        currency: str | None = None,
        reason: str,
    ) -> DisposalResult:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_APPROVE_ROLES, "Finance approve role required")

        asset = self._require_asset(asset_id)
        if asset.status == FixedAssetStatus.DISPOSED:
            raise ValueError("Asset already disposed")

        r = (reason or "").strip()
        if not r:
            raise ValueError("reason required")

        cur = _norm_currency(currency or asset.currency)
        if cur != asset.currency:
            raise ValueError("Currency mismatch")

        proc = _q2(proceeds)
        if proc < 0:
            raise ValueError("proceeds must be >= 0")

        carrying = asset.carrying_amount
        gain_loss = _q2(proc - carrying)

        if self._ledger is not None:
            self._post_disposal_to_gl(
                actor_id=actor_id,
                actor_roles=roles,
                correlation_id=correlation_id,
                asset=asset,
                disposal_date=disposal_date,
                proceeds=proc,
                gain_loss=gain_loss,
                reason=r,
            )

        asset.status = FixedAssetStatus.DISPOSED
        asset.disposed_at = _now()
        asset.disposed_by = actor_id

        self._record_event(
            asset_id=asset.id,
            event_type=AssetEventType.DISPOSAL,
            actor_id=actor_id,
            correlation_id=correlation_id,
            amount=gain_loss,
            details={
                "date": disposal_date.isoformat(),
                "proceeds": str(proc),
                "gain_loss": str(gain_loss),
                "reason": r,
            },
        )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="fa.dispose",
            entity_type="fixed_asset",
            entity_id=str(asset.id),
            correlation_id=correlation_id,
            metadata={
                "date": disposal_date.isoformat(),
                "proceeds": str(proc),
                "gain_loss": str(gain_loss),
                "reason": r,
            },
        )

        return DisposalResult(
            gain_loss=gain_loss, proceeds=proc, carrying_amount=carrying
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_asset(self, asset_id: UUID) -> FixedAsset:
        asset = self._assets_by_id.get(asset_id)
        if asset is None:
            raise ValueError("Unknown asset")
        return asset

    def _record_event(
        self,
        *,
        asset_id: UUID,
        event_type: AssetEventType,
        actor_id: str,
        correlation_id: str,
        amount: Decimal | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._events.append(
            AssetEvent(
                id=uuid4(),
                asset_id=asset_id,
                event_type=event_type,
                occurred_at=_now(),
                actor_id=actor_id,
                correlation_id=correlation_id,
                amount=amount,
                details=details or {},
            )
        )

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write role required")
        self._audit.append(
            AuditEvent(
                id=uuid4(),
                occurred_at=_now(),
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                metadata=metadata or {},
            )
        )

    # ------------------------------------------------------------------
    # GL integration
    # ------------------------------------------------------------------

    def _post_capitalization_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset: FixedAsset,
    ) -> None:
        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        lines = [
            GLLine(
                account_code=self._cfg.fixed_asset_account_code,
                debit=_q2(asset.acquisition_cost),
                credit=Decimal("0"),
                currency=asset.currency,
                memo=f"Capitalize {asset.asset_tag}",
            ),
            GLLine(
                account_code=self._cfg.asset_clearing_account_code,
                debit=Decimal("0"),
                credit=_q2(asset.acquisition_cost),
                currency=asset.currency,
                memo=f"Capitalize {asset.asset_tag}",
            ),
        ]

        if self._ledger is None:
            raise ValueError("Ledger integration not configured")
        
        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            reference=f"FA-{asset.asset_tag}",
            entry_date=asset.capitalization_date,
            description=f"Fixed asset capitalization {asset.asset_tag}",
            lines=lines,
            metadata={
                "source": "fixed_assets",
                "asset_id": str(asset.id),
                "asset_tag": asset.asset_tag,
            },
        )
        self._ledger.approve_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
        self._ledger.post_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )

    def _post_depreciation_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset: FixedAsset,
        amount: Decimal,
        post_date: date,
    ) -> UUID:
        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        lines = [
            GLLine(
                account_code=self._cfg.depreciation_expense_account_code,
                debit=_q2(amount),
                credit=Decimal("0"),
                currency=asset.currency,
                memo=f"Depreciation {asset.asset_tag}",
            ),
            GLLine(
                account_code=self._cfg.accumulated_depr_account_code,
                debit=Decimal("0"),
                credit=_q2(amount),
                currency=asset.currency,
                memo=f"Depreciation {asset.asset_tag}",
            ),
        ]

        if self._ledger is None:
            raise ValueError("Ledger integration not configured")
        
        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            reference=f"DEP-{asset.asset_tag}",
            entry_date=post_date,
            description=f"Depreciation for {asset.asset_tag}",
            lines=lines,
            metadata={
                "source": "fixed_assets",
                "asset_id": str(asset.id),
                "asset_tag": asset.asset_tag,
            },
        )
        self._ledger.approve_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
        self._ledger.post_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
        return je.id

    def _post_impairment_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset: FixedAsset,
        amount: Decimal,
        impairment_date: date,
        reason: str,
    ) -> None:
        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        lines = [
            GLLine(
                account_code=self._cfg.impairment_loss_account_code,
                debit=_q2(amount),
                credit=Decimal("0"),
                currency=asset.currency,
                memo=f"Impairment {asset.asset_tag}: {reason}",
            ),
            GLLine(
                account_code=self._cfg.fixed_asset_account_code,
                debit=Decimal("0"),
                credit=_q2(amount),
                currency=asset.currency,
                memo=f"Impairment {asset.asset_tag}",
            ),
        ]

        if self._ledger is None:
            raise ValueError("Ledger integration not configured")
        
        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            reference=f"IMP-{asset.asset_tag}",
            entry_date=impairment_date,
            description=f"Impairment for {asset.asset_tag}",
            lines=lines,
            metadata={
                "source": "fixed_assets",
                "asset_id": str(asset.id),
                "asset_tag": asset.asset_tag,
                "reason": reason,
            },
        )
        self._ledger.approve_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
        self._ledger.post_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )

    def _post_disposal_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        asset: FixedAsset,
        disposal_date: date,
        proceeds: Decimal,
        gain_loss: Decimal,
        reason: str,
    ) -> None:
        from sensei.services.finance.accounting_ledger import JournalLine as GLLine

        # Remove asset cost and accumulated depreciation; recognize gain/loss and proceeds.
        lines: list[GLLine] = []

        if proceeds > 0:
            lines.append(
                GLLine(
                    account_code=self._cfg.cash_account_code,
                    debit=_q2(proceeds),
                    credit=Decimal("0"),
                    currency=asset.currency,
                    memo=f"Disposal proceeds {asset.asset_tag}",
                )
            )

        if asset.accumulated_depreciation > 0:
            lines.append(
                GLLine(
                    account_code=self._cfg.accumulated_depr_account_code,
                    debit=_q2(asset.accumulated_depreciation),
                    credit=Decimal("0"),
                    currency=asset.currency,
                    memo=f"Clear accum depr {asset.asset_tag}",
                )
            )

        # Credit the asset cost
        lines.append(
            GLLine(
                account_code=self._cfg.fixed_asset_account_code,
                debit=Decimal("0"),
                credit=_q2(asset.acquisition_cost),
                currency=asset.currency,
                memo=f"Dispose asset {asset.asset_tag}",
            )
        )

        if gain_loss != 0:
            if gain_loss > 0:
                # Gain is credit
                lines.append(
                    GLLine(
                        account_code=self._cfg.disposal_gain_loss_account_code,
                        debit=Decimal("0"),
                        credit=_q2(gain_loss),
                        currency=asset.currency,
                        memo=f"Gain on disposal {asset.asset_tag}",
                    )
                )
            else:
                # Loss is debit
                lines.append(
                    GLLine(
                        account_code=self._cfg.disposal_gain_loss_account_code,
                        debit=_q2(-gain_loss),
                        credit=Decimal("0"),
                        currency=asset.currency,
                        memo=f"Loss on disposal {asset.asset_tag}",
                    )
                )

        if self._ledger is None:
            raise ValueError("Ledger integration not configured")
        
        je = self._ledger.create_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            reference=f"DSP-{asset.asset_tag}",
            entry_date=disposal_date,
            description=f"Disposal of {asset.asset_tag}",
            lines=lines,
            metadata={
                "source": "fixed_assets",
                "asset_id": str(asset.id),
                "asset_tag": asset.asset_tag,
                "reason": reason,
            },
        )
        self._ledger.approve_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
        self._ledger.post_journal_entry(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            entry_id=je.id,
        )
