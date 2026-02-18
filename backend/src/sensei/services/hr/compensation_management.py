"""Compensation Management (Development Plan 22.6).

Implements:
- Salary/Hourly Rates: track current and historical compensation for each employee.
- Pay Bands: define compensation ranges by grade/level for SoD compliance.
- Change Approvals: workflow for salary adjustments requiring multiple approvals.
- SoD Enforcement: prevent same actor from proposing and approving changes.

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass

logger = logging.getLogger(__name__)


class CompensationType(str, Enum):
    SALARY = "salary"
    HOURLY = "hourly"
    CONTRACT = "contract"


class ChangeStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ChangeReason(str, Enum):
    MERIT = "merit"
    PROMOTION = "promotion"
    MARKET_ADJUSTMENT = "market_adjustment"
    ANNUAL_INCREASE = "annual_increase"
    CORRECTION = "correction"
    NEW_HIRE = "new_hire"
    OTHER = "other"


# RBAC role sets
_HR_WRITE_ROLES: set[str] = {"admin", "hr", "ceo"}
_HR_READ_ROLES: set[str] = {"admin", "hr", "ceo", "exec", "gm", "finance", "auditor"}
_COMP_APPROVE_ROLES: set[str] = {"admin", "ceo", "exec", "hr"}
_SALARY_VIEW_ROLES: set[str] = {"admin", "hr", "ceo", "finance", "auditor"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PayBand:
    """Compensation range for a grade/level."""

    id: UUID
    grade: str
    level: int
    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal
    currency: str
    compensation_type: CompensationType
    effective_date: date
    end_date: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompensationRecord:
    """Current or historical compensation for an employee."""

    id: UUID
    employee_id: UUID
    compensation_type: CompensationType
    amount: Decimal
    currency: str
    pay_band_id: UUID | None
    effective_date: date
    end_date: date | None = None
    reason: ChangeReason = ChangeReason.NEW_HIRE
    notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""


@dataclass(frozen=True)
class CompensationChange:
    """Proposed compensation change requiring approval."""

    id: UUID
    employee_id: UUID
    current_record_id: UUID | None
    proposed_amount: Decimal
    proposed_type: CompensationType
    currency: str
    pay_band_id: UUID | None
    effective_date: date
    reason: ChangeReason
    justification: str
    status: ChangeStatus
    proposed_by: str
    proposed_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class CompensationManagementService(PersistentServiceMixin):
    """In-memory compensation management service."""

    SERVICE_NAME = "compensation_management"

    def __init__(self) -> None:
        self._pay_bands: dict[UUID, PayBand] = {}
        self._compensation_records: dict[UUID, CompensationRecord] = {}
        self._changes: dict[UUID, CompensationChange] = {}
        self._audit: list[AuditEvent] = []
        # Secondary index: employee_id -> set of record ids (#96)
        self._records_by_employee: dict[UUID, set[UUID]] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        bands_data = await self.load_state(_DEFAULT_TENANT_ID, "pay_bands") or {}
        records_data = await self.load_state(_DEFAULT_TENANT_ID, "compensation_records") or {}
        changes_data = await self.load_state(_DEFAULT_TENANT_ID, "changes") or {}
        audit_data = await self.load_state(_DEFAULT_TENANT_ID, "audit") or []

        self._pay_bands = {UUID(bid): decode_dataclass(b, PayBand) for bid, b in bands_data.items()}
        self._compensation_records = {
            UUID(rid): decode_dataclass(r, CompensationRecord) for rid, r in records_data.items()
        }
        self._changes = {UUID(cid): decode_dataclass(c, CompensationChange) for cid, c in changes_data.items()}
        self._audit = [decode_dataclass(ev, AuditEvent) for ev in audit_data]

        self._records_by_employee.clear()
        for record in self._compensation_records.values():
            self._records_by_employee.setdefault(record.employee_id, set()).add(record.id)

        self._state_loaded = True

    async def persist_all(self) -> None:
        bands_data = {str(bid): encode_dataclass(b) for bid, b in self._pay_bands.items()}
        records_data = {str(rid): encode_dataclass(r) for rid, r in self._compensation_records.items()}
        changes_data = {str(cid): encode_dataclass(c) for cid, c in self._changes.items()}
        audit_data = [encode_dataclass(ev) for ev in self._audit]

        await self.save_state(_DEFAULT_TENANT_ID, "pay_bands", bands_data)
        await self.save_state(_DEFAULT_TENANT_ID, "compensation_records", records_data)
        await self.save_state(_DEFAULT_TENANT_ID, "changes", changes_data)
        await self.save_state(_DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

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
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return list(self._audit)

    async def list_audit_events_async(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(actor_roles=actor_roles)

    # ----------------------------------------------------------------
    # Pay Bands
    # ----------------------------------------------------------------

    def create_pay_band(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        grade: str,
        level: int,
        min_amount: Decimal,
        mid_amount: Decimal,
        max_amount: Decimal,
        currency: str = "EUR",
        compensation_type: CompensationType = CompensationType.SALARY,
        effective_date: date | None = None,
        end_date: date | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PayBand:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if not grade or not grade.strip():
            raise ValueError("grade required")
        if level < 1:
            raise ValueError("level must be >= 1")
        if min_amount <= 0:
            raise ValueError("min_amount must be > 0")
        if mid_amount < min_amount:
            raise ValueError("mid_amount must be >= min_amount")
        if max_amount < mid_amount:
            raise ValueError("max_amount must be >= mid_amount")

        band = PayBand(
            id=uuid4(),
            grade=grade.strip(),
            level=level,
            min_amount=min_amount,
            mid_amount=mid_amount,
            max_amount=max_amount,
            currency=currency.upper(),
            compensation_type=compensation_type,
            effective_date=effective_date or date.today(),
            end_date=end_date,
            metadata=metadata or {},
        )
        self._pay_bands[band.id] = band

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.pay_band.create",
            entity_type="pay_band",
            entity_id=str(band.id),
            correlation_id=correlation_id,
            metadata={"grade": band.grade, "level": band.level},
        )

        return band

    async def create_pay_band_async(self, **kwargs: Any) -> PayBand:
        await self._ensure_loaded()
        band = self.create_pay_band(**kwargs)
        await self.persist_all()
        return band

    def list_pay_bands(
        self,
        *,
        actor_roles: Iterable[str],
        grade: str | None = None,
        active_only: bool = True,
    ) -> list[PayBand]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        result = []
        today = date.today()
        for band in self._pay_bands.values():
            if grade and band.grade != grade:
                continue
            if active_only:
                if band.effective_date > today:
                    continue
                if band.end_date and band.end_date < today:
                    continue
            result.append(band)

        return sorted(result, key=lambda b: (b.grade, b.level))

    async def list_pay_bands_async(self, **kwargs: Any) -> list[PayBand]:
        await self._ensure_loaded()
        return self.list_pay_bands(**kwargs)

    def get_pay_band(
        self, *, actor_roles: Iterable[str], band_id: UUID
    ) -> PayBand | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return self._pay_bands.get(band_id)

    async def get_pay_band_async(self, **kwargs: Any) -> PayBand | None:
        await self._ensure_loaded()
        return self.get_pay_band(**kwargs)

    # ----------------------------------------------------------------
    # Compensation Records
    # ----------------------------------------------------------------

    def set_compensation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        employee_id: UUID,
        amount: Decimal,
        compensation_type: CompensationType = CompensationType.SALARY,
        currency: str = "EUR",
        pay_band_id: UUID | None = None,
        effective_date: date | None = None,
        reason: ChangeReason = ChangeReason.NEW_HIRE,
        notes: str = "",
    ) -> CompensationRecord:
        """Set compensation directly (bypasses approval for initial setup)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if amount <= 0:
            raise ValueError("amount must be > 0")

        eff_date = effective_date or date.today()

        # Validate against pay band if provided
        if pay_band_id:
            band = self._pay_bands.get(pay_band_id)
            if not band:
                raise ValueError("pay_band_id not found")
            if amount < band.min_amount or amount > band.max_amount:
                raise ValueError(
                    f"amount must be within band range [{band.min_amount}, {band.max_amount}]"
                )

        # End any current record for this employee (O(k) via index)
        for rec_id in list(self._records_by_employee.get(employee_id, set())):
            rec = self._compensation_records.get(rec_id)
            if rec and rec.end_date is None:
                if eff_date < rec.effective_date:
                    raise ValueError(
                        "effective_date must be on or after current record effective_date"
                    )
                # Create updated record with end date
                updated = CompensationRecord(
                    id=rec.id,
                    employee_id=rec.employee_id,
                    compensation_type=rec.compensation_type,
                    amount=rec.amount,
                    currency=rec.currency,
                    pay_band_id=rec.pay_band_id,
                    effective_date=rec.effective_date,
                    end_date=eff_date,
                    reason=rec.reason,
                    notes=rec.notes,
                    created_at=rec.created_at,
                    created_by=rec.created_by,
                )
                self._compensation_records[rec.id] = updated

        record = CompensationRecord(
            id=uuid4(),
            employee_id=employee_id,
            compensation_type=compensation_type,
            amount=amount,
            currency=currency.upper(),
            pay_band_id=pay_band_id,
            effective_date=eff_date,
            end_date=None,
            reason=reason,
            notes=notes,
            created_at=_utcnow(),
            created_by=actor_id,
        )
        self._compensation_records[record.id] = record
        self._records_by_employee.setdefault(record.employee_id, set()).add(record.id)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.record.set",
            entity_type="compensation_record",
            entity_id=str(record.id),
            correlation_id=correlation_id,
            metadata={
                "employee_id": str(employee_id),
                "amount": str(amount),
                "reason": reason.value,
            },
        )

        return record

    async def set_compensation_async(self, **kwargs: Any) -> CompensationRecord:
        await self._ensure_loaded()
        record = self.set_compensation(**kwargs)
        await self.persist_all()
        return record

    def get_current_compensation(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        employee_id: UUID,
        mask_amount: bool = False,
    ) -> CompensationRecord | None:
        """Get current compensation record for employee."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        can_see_salary = bool(roles.intersection(_SALARY_VIEW_ROLES))

        for rec_id in self._records_by_employee.get(employee_id, set()):
            rec = self._compensation_records.get(rec_id)
            if rec and rec.end_date is None:
                if mask_amount and not can_see_salary:
                    # Return record with masked amount
                    return CompensationRecord(
                        id=rec.id,
                        employee_id=rec.employee_id,
                        compensation_type=rec.compensation_type,
                        amount=Decimal("0"),  # Masked
                        currency=rec.currency,
                        pay_band_id=rec.pay_band_id,
                        effective_date=rec.effective_date,
                        end_date=rec.end_date,
                        reason=rec.reason,
                        notes="[MASKED]",
                        created_at=rec.created_at,
                        created_by=rec.created_by,
                    )
                return rec
        return None

    async def get_current_compensation_async(self, **kwargs: Any) -> CompensationRecord | None:
        await self._ensure_loaded()
        return self.get_current_compensation(**kwargs)

    def get_compensation_history(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        employee_id: UUID,
    ) -> list[CompensationRecord]:
        """Get full compensation history for employee."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _SALARY_VIEW_ROLES, "Salary view role required")

        result = [
            self._compensation_records[rid]
            for rid in self._records_by_employee.get(employee_id, set())
            if rid in self._compensation_records
        ]
        return sorted(result, key=lambda r: r.effective_date)

    async def get_compensation_history_async(self, **kwargs: Any) -> list[CompensationRecord]:
        await self._ensure_loaded()
        return self.get_compensation_history(**kwargs)

    # ----------------------------------------------------------------
    # Compensation Change Workflow
    # ----------------------------------------------------------------

    def propose_change(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        employee_id: UUID,
        proposed_amount: Decimal,
        proposed_type: CompensationType = CompensationType.SALARY,
        currency: str = "EUR",
        pay_band_id: UUID | None = None,
        effective_date: date | None = None,
        reason: ChangeReason = ChangeReason.MERIT,
        justification: str = "",
    ) -> CompensationChange:
        """Propose a compensation change for approval."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write role required")

        if proposed_amount <= 0:
            raise ValueError("proposed_amount must be > 0")
        if not justification or not justification.strip():
            raise ValueError("justification required")

        # Validate against pay band if provided
        if pay_band_id:
            band = self._pay_bands.get(pay_band_id)
            if not band:
                raise ValueError("pay_band_id not found")
            if proposed_amount < band.min_amount or proposed_amount > band.max_amount:
                raise ValueError(
                    f"proposed_amount must be within band range [{band.min_amount}, {band.max_amount}]"
                )

        # Find current record
        current_record_id = None
        for rec in self._compensation_records.values():
            if rec.employee_id == employee_id and rec.end_date is None:
                current_record_id = rec.id
                break

        change = CompensationChange(
            id=uuid4(),
            employee_id=employee_id,
            current_record_id=current_record_id,
            proposed_amount=proposed_amount,
            proposed_type=proposed_type,
            currency=currency.upper(),
            pay_band_id=pay_band_id,
            effective_date=effective_date or date.today(),
            reason=reason,
            justification=justification.strip(),
            status=ChangeStatus.PENDING_APPROVAL,
            proposed_by=actor_id,
            proposed_at=_utcnow(),
        )
        self._changes[change.id] = change

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.change.propose",
            entity_type="compensation_change",
            entity_id=str(change.id),
            correlation_id=correlation_id,
            metadata={
                "employee_id": str(employee_id),
                "proposed_amount": str(proposed_amount),
                "reason": reason.value,
            },
        )

        return change

    async def propose_change_async(self, **kwargs: Any) -> CompensationChange:
        await self._ensure_loaded()
        change = self.propose_change(**kwargs)
        await self.persist_all()
        return change

    def approve_change(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        change_id: UUID,
    ) -> CompensationChange:
        """Approve a pending compensation change."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COMP_APPROVE_ROLES, "Compensation approve role required")

        change = self._changes.get(change_id)
        if not change:
            raise ValueError("change_id not found")
        if change.status != ChangeStatus.PENDING_APPROVAL:
            raise ValueError(f"Change is {change.status.value}, cannot approve")

        # SoD: proposer cannot approve
        if change.proposed_by == actor_id:
            raise PermissionError(
                "Segregation of Duties: proposer cannot approve their own change"
            )

        # Apply the change by creating new compensation record
        new_record = self.set_compensation(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            employee_id=change.employee_id,
            amount=change.proposed_amount,
            compensation_type=change.proposed_type,
            currency=change.currency,
            pay_band_id=change.pay_band_id,
            effective_date=change.effective_date,
            reason=change.reason,
            notes=f"Approved change {change.id}",
        )

        approved = CompensationChange(
            id=change.id,
            employee_id=change.employee_id,
            current_record_id=change.current_record_id,
            proposed_amount=change.proposed_amount,
            proposed_type=change.proposed_type,
            currency=change.currency,
            pay_band_id=change.pay_band_id,
            effective_date=change.effective_date,
            reason=change.reason,
            justification=change.justification,
            status=ChangeStatus.APPROVED,
            proposed_by=change.proposed_by,
            proposed_at=change.proposed_at,
            approved_by=actor_id,
            approved_at=_utcnow(),
            metadata={**change.metadata, "new_record_id": str(new_record.id)},
        )
        self._changes[change.id] = approved

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.change.approve",
            entity_type="compensation_change",
            entity_id=str(change.id),
            correlation_id=correlation_id,
            metadata={"employee_id": str(change.employee_id)},
        )

        return approved

    async def approve_change_async(self, **kwargs: Any) -> CompensationChange:
        await self._ensure_loaded()
        change = self.approve_change(**kwargs)
        await self.persist_all()
        return change

    def reject_change(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        change_id: UUID,
        reason: str,
    ) -> CompensationChange:
        """Reject a pending compensation change."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _COMP_APPROVE_ROLES, "Compensation approve role required")

        change = self._changes.get(change_id)
        if not change:
            raise ValueError("change_id not found")
        if change.status != ChangeStatus.PENDING_APPROVAL:
            raise ValueError(f"Change is {change.status.value}, cannot reject")
        if not reason or not reason.strip():
            raise ValueError("rejection reason required")

        rejected = CompensationChange(
            id=change.id,
            employee_id=change.employee_id,
            current_record_id=change.current_record_id,
            proposed_amount=change.proposed_amount,
            proposed_type=change.proposed_type,
            currency=change.currency,
            pay_band_id=change.pay_band_id,
            effective_date=change.effective_date,
            reason=change.reason,
            justification=change.justification,
            status=ChangeStatus.REJECTED,
            proposed_by=change.proposed_by,
            proposed_at=change.proposed_at,
            rejected_by=actor_id,
            rejected_at=_utcnow(),
            rejection_reason=reason.strip(),
            metadata=change.metadata,
        )
        self._changes[change.id] = rejected

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.change.reject",
            entity_type="compensation_change",
            entity_id=str(change.id),
            correlation_id=correlation_id,
            metadata={"employee_id": str(change.employee_id), "reason": reason},
        )

        return rejected

    async def reject_change_async(self, **kwargs: Any) -> CompensationChange:
        await self._ensure_loaded()
        change = self.reject_change(**kwargs)
        await self.persist_all()
        return change

    def list_pending_changes(
        self, *, actor_roles: Iterable[str]
    ) -> list[CompensationChange]:
        """List all pending compensation changes."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")

        return [
            c
            for c in self._changes.values()
            if c.status == ChangeStatus.PENDING_APPROVAL
        ]

    async def list_pending_changes_async(self, **kwargs: Any) -> list[CompensationChange]:
        await self._ensure_loaded()
        return self.list_pending_changes(**kwargs)

    def get_change(
        self, *, actor_roles: Iterable[str], change_id: UUID
    ) -> CompensationChange | None:
        """Get a specific compensation change."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read role required")
        return self._changes.get(change_id)

    async def get_change_async(self, **kwargs: Any) -> CompensationChange | None:
        await self._ensure_loaded()
        return self.get_change(**kwargs)

    # ----------------------------------------------------------------
    # Exports
    # ----------------------------------------------------------------

    def export_payroll_rates(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Export current compensation rates for payroll processing."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _SALARY_VIEW_ROLES, "Salary view role required")

        as_of = as_of_date or date.today()
        result = []

        for rec in self._compensation_records.values():
            if rec.effective_date > as_of:
                continue
            if rec.end_date and rec.end_date <= as_of:
                continue

            result.append({
                "employee_id": str(rec.employee_id),
                "compensation_type": rec.compensation_type.value,
                "amount": str(rec.amount),
                "currency": rec.currency,
                "effective_date": rec.effective_date.isoformat(),
            })

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="comp.export.payroll_rates",
            entity_type="export",
            entity_id=f"payroll-{as_of.isoformat()}",
            correlation_id=correlation_id,
            metadata={"record_count": len(result)},
        )

        return result

    async def export_payroll_rates_async(self, **kwargs: Any) -> list[dict[str, Any]]:
        await self._ensure_loaded()
        return self.export_payroll_rates(**kwargs)
