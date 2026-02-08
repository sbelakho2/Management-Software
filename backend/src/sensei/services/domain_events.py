"""
Domain Event Catalog (#356–361, #383).

Centralised definitions for all domain events used across services.
Services publish these events instead of calling each other directly,
reducing cross-domain coupling.

Each event extends ``DomainEvent`` from the event bus and carries only
the minimum data needed by subscribers.

Usage::

    from sensei.services.domain_events import NCCreatedEvent, CAPACreatedEvent
    from sensei.services.event_bus import event_bus

    # Publisher (quality service)
    await event_bus.publish(NCCreatedEvent(nc_id=..., severity="critical"))

    # Subscriber (CAPA service — registered at startup)
    event_bus.subscribe(NCCreatedEvent, handle_nc_created)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from sensei.services.event_bus import DomainEvent


# =====================================================================
# Quality domain events (#356 — decouple quality ↔ AI)
# =====================================================================


@dataclass
class NCCreatedEvent(DomainEvent):
    """A Non-Conformance was recorded."""
    nc_id: UUID | str = ""
    severity: str = ""
    nc_type: str = ""
    product_id: str | None = None
    process_id: str | None = None
    defect_code: str | None = None
    detected_by: str = ""


@dataclass
class CAPACreatedEvent(DomainEvent):
    """A Corrective/Preventive Action was created."""
    capa_id: UUID | str = ""
    nc_id: UUID | str | None = None
    priority: str = ""
    auto_created: bool = False
    creation_reason: str = ""


@dataclass
class InspectionCompletedEvent(DomainEvent):
    """An inspection was finished."""
    inspection_id: UUID | str = ""
    result: str = ""  # pass / fail / conditional
    product_id: str | None = None
    inspector_id: str = ""


@dataclass
class AuditFindingEvent(DomainEvent):
    """An audit finding was recorded."""
    finding_id: UUID | str = ""
    audit_id: UUID | str = ""
    severity: str = ""
    area: str = ""


# =====================================================================
# Finance domain events (#357, #359 — decouple finance ↔ ops)
# =====================================================================


@dataclass
class CostRollupCompleted(DomainEvent):
    """Cost roll-up computation finished for a product."""
    product_id: UUID | str = ""
    total_cost: float = 0.0
    currency: str = "USD"


@dataclass
class JournalEntryPosted(DomainEvent):
    """A journal entry was posted to the ledger."""
    entry_id: UUID | str = ""
    debit_total: float = 0.0
    credit_total: float = 0.0
    period: str = ""


@dataclass
class InvoiceCreatedEvent(DomainEvent):
    """An invoice was created (AP or AR)."""
    invoice_id: UUID | str = ""
    invoice_type: str = ""  # payable / receivable
    amount: float = 0.0
    currency: str = "USD"
    counterparty: str = ""


# =====================================================================
# Maintenance domain events (#358 — decouple maintenance ↔ in-memory)
# =====================================================================


@dataclass
class WorkOrderCreatedEvent(DomainEvent):
    """A maintenance work order was created."""
    work_order_id: UUID | str = ""
    asset_id: UUID | str = ""
    priority: str = ""
    work_type: str = ""  # corrective / preventive / predictive


@dataclass
class DowntimeRecordedEvent(DomainEvent):
    """Equipment downtime was recorded."""
    asset_id: UUID | str = ""
    duration_minutes: float = 0.0
    cause: str = ""
    impact: str = ""


@dataclass
class PMScheduleTriggeredEvent(DomainEvent):
    """A preventive-maintenance schedule triggered a work order."""
    schedule_id: UUID | str = ""
    asset_id: UUID | str = ""
    next_due: str = ""


# =====================================================================
# HR / Training domain events (#360 — decouple training ↔ models)
# =====================================================================


@dataclass
class TrainingCompletedEvent(DomainEvent):
    """An employee completed a training course."""
    employee_id: UUID | str = ""
    training_id: UUID | str = ""
    skill_id: str = ""
    score: float | None = None
    passed: bool = True


@dataclass
class CertificationExpiredEvent(DomainEvent):
    """An employee's certification has expired or is about to expire."""
    employee_id: UUID | str = ""
    certification_id: UUID | str = ""
    expired_at: str = ""
    skill_name: str = ""


@dataclass
class EmployeeOnboardedEvent(DomainEvent):
    """A new employee completed onboarding."""
    employee_id: UUID | str = ""
    department: str = ""
    position: str = ""


# =====================================================================
# Production domain events
# =====================================================================


@dataclass
class ProductionOrderStartedEvent(DomainEvent):
    """A production order started on the shop floor."""
    order_id: UUID | str = ""
    product_id: UUID | str = ""
    quantity: int = 0
    line_id: str = ""


@dataclass
class ProductionOrderCompletedEvent(DomainEvent):
    """A production order was completed."""
    order_id: UUID | str = ""
    product_id: UUID | str = ""
    quantity_produced: int = 0
    scrap_quantity: int = 0


@dataclass
class MRPRunCompleted(DomainEvent):
    """An MRP explosion run finished."""
    run_id: UUID | str = ""
    planned_orders: int = 0
    shortage_count: int = 0


# =====================================================================
# Supply-chain / CRM domain events (#361 — decouple recruiting ↔ utils)
# =====================================================================


@dataclass
class SupplierEvaluatedEvent(DomainEvent):
    """A supplier was evaluated / scored."""
    supplier_id: UUID | str = ""
    score: float = 0.0
    tier: str = ""


@dataclass
class OpportunityStageChangedEvent(DomainEvent):
    """A CRM opportunity changed pipeline stage."""
    opportunity_id: UUID | str = ""
    old_stage: str = ""
    new_stage: str = ""
    amount: float = 0.0


@dataclass
class ApplicationReceivedEvent(DomainEvent):
    """A job application was received."""
    application_id: UUID | str = ""
    job_posting_id: UUID | str = ""
    candidate_email: str = ""


# =====================================================================
# AI / ML domain events
# =====================================================================


@dataclass
class AnomalyDetectedEvent(DomainEvent):
    """The AI anomaly detector found a potential anomaly."""
    entity_type: str = ""
    entity_id: UUID | str = ""
    anomaly_type: str = ""
    confidence: float = 0.0
    description: str = ""


@dataclass
class ModelRetrainedEvent(DomainEvent):
    """An ML model was retrained."""
    model_name: str = ""
    version: str = ""
    accuracy: float = 0.0
    dataset_size: int = 0


# =====================================================================
# Convenience: register standard event subscriptions at startup
# =====================================================================


def register_standard_subscriptions() -> None:
    """Wire up well-known cross-domain event handlers.

    Call this once at application startup (e.g. in ``create_app``).
    """
    import logging

    from sensei.services.event_bus import event_bus

    _log = logging.getLogger(__name__)

    async def _log_event(event: DomainEvent) -> None:
        _log.info(
            "DomainEvent[%s] id=%s tenant=%s",
            type(event).__name__,
            event.event_id,
            event.tenant_id,
        )

    # Global audit subscriber
    event_bus.subscribe_all(_log_event)
    _log.info("Registered standard domain event subscriptions")
