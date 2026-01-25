#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = ROOT / "backend" / "src"

import sys

sys.path.append(str(BACKEND_SRC))

from sensei.core.database import async_session_factory
from sensei.models.user import RoleType
from sensei.services.ai.ai_email_drafting import (
    AIEmailDraftingService,
    EmailContext,
    EmailPurpose,
    EmailTone,
    GenerationRequest,
    Language,
    Recipient,
)
from sensei.services.core.common_thread import get_common_thread_service

ROLE_SCENARIOS: dict[RoleType, dict[str, Any]] = {
    RoleType.ADMIN: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Cross-site operations status",
        "key_points": [
            "Plant throughput up 6% week-over-week",
            "Two RFQs awaiting final technical review",
            "Action requested: approve staffing for Line 3",
        ],
    },
    RoleType.CEO: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.FORMAL,
        "subject_hint": "Executive weekly brief",
        "key_points": [
            "Gross margin tracking 1.2% above target",
            "On-time delivery holding at 96%",
            "Strategic risk: supplier lead time on MCU",
        ],
    },
    RoleType.GM: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Site readiness update",
        "key_points": [
            "Line changeover completed ahead of schedule",
            "Training coverage at 98% for new SOP",
            "Request approval for preventive maintenance window",
        ],
    },
    RoleType.EXEC: {
        "purpose": EmailPurpose.MEETING_REQUEST,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Q3 pipeline alignment",
        "key_points": [
            "Review top 5 pipeline opportunities",
            "Align on pricing strategy for aerospace bids",
            "Confirm executive sponsor for key account",
        ],
    },
    RoleType.FINANCE: {
        "purpose": EmailPurpose.MISSING_INFO_REQUEST,
        "tone": EmailTone.FORMAL,
        "subject_hint": "Invoice details needed",
        "key_points": [
            "Confirm PO number and billing entity",
            "Clarify tax exemption status",
            "Provide updated payment terms",
        ],
    },
    RoleType.ACCOUNTANT: {
        "purpose": EmailPurpose.MISSING_INFO_REQUEST,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Remittance advice request",
        "key_points": [
            "Attach remittance advice for last payment",
            "Confirm open balance for Q2 invoices",
            "Verify account contact for reconciliations",
        ],
    },
    RoleType.HR: {
        "purpose": EmailPurpose.MEETING_REQUEST,
        "tone": EmailTone.FRIENDLY,
        "subject_hint": "Onboarding sync",
        "key_points": [
            "Confirm onboarding schedule for new operator class",
            "Review safety training completion checklist",
            "Align on badge access provisioning",
        ],
    },
    RoleType.OPS: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Operations status",
        "key_points": [
            "Line 2 uptime at 94% this week",
            "Material shortage resolved for WO-1842",
            "Next focus: reduce changeover time by 10%",
        ],
    },
    RoleType.QUALITY: {
        "purpose": EmailPurpose.ISSUE_NOTIFICATION,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "NC review required",
        "key_points": [
            "Non-conformance detected on lot 24-041",
            "Immediate containment in place",
            "Request disposition decision by Friday",
        ],
    },
    RoleType.AUDITOR: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.FORMAL,
        "subject_hint": "Audit readiness",
        "key_points": [
            "Evidence packages compiled for ISO clause 8.5",
            "Open corrective action: CA-017",
            "Confirm audit schedule and attendees",
        ],
    },
    RoleType.IT: {
        "purpose": EmailPurpose.ISSUE_NOTIFICATION,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Systems maintenance window",
        "key_points": [
            "Planned ERP maintenance Saturday 02:00-04:00",
            "Downtime expected for reporting module",
            "Request confirmation from operations leads",
        ],
    },
    RoleType.SALES: {
        "purpose": EmailPurpose.QUOTE_FOLLOWUP,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Quote follow-up",
        "key_points": [
            "Confirm scope for RFQ-2024-118",
            "Review lead time expectations",
            "Offer a call to walk through pricing",
        ],
    },
    RoleType.PURCHASING: {
        "purpose": EmailPurpose.SUPPLIER_INQUIRY,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Supplier capability check",
        "key_points": [
            "Need current lead times for MCU-557",
            "Confirm MOQ and pricing tiers",
            "Request quality certifications",
        ],
    },
    RoleType.SALES_ENGINEER: {
        "purpose": EmailPurpose.QUOTE_SUBMISSION,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Quote submission details",
        "key_points": [
            "Attached technical response and DFM notes",
            "Outlined test coverage and fixtures",
            "Recommend review meeting next week",
        ],
    },
    RoleType.ESTIMATOR: {
        "purpose": EmailPurpose.MISSING_INFO_REQUEST,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Cost model inputs needed",
        "key_points": [
            "Awaiting updated BOM with alternates",
            "Need assembly volume forecast",
            "Confirm target delivery window",
        ],
    },
    RoleType.SUPPLY_CHAIN: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Supply chain status",
        "key_points": [
            "Critical parts ETA aligned for WO-1842",
            "Secondary sourcing identified for U45",
            "Request approval for expedited freight",
        ],
    },
    RoleType.LOGISTICS: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Shipment coordination",
        "key_points": [
            "Shipment SHP-778 staged for pickup",
            "Carrier requires dock appointment",
            "Confirm delivery window preference",
        ],
    },
    RoleType.MAINTENANCE: {
        "purpose": EmailPurpose.ISSUE_NOTIFICATION,
        "tone": EmailTone.URGENT,
        "subject_hint": "Equipment maintenance alert",
        "key_points": [
            "Pick-and-place Line 1 showing feeder faults",
            "Maintenance window needed within 24 hours",
            "Spare parts inventory low on feeder pins",
        ],
    },
    RoleType.WAREHOUSE: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Inventory update",
        "key_points": [
            "Cycle count completed for Aisle 4",
            "Discrepancy noted on resistor reels",
            "Request approval for adjustment",
        ],
    },
    RoleType.ENGINEERING: {
        "purpose": EmailPurpose.MEETING_REQUEST,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "DFM review",
        "key_points": [
            "Review stackup and impedance targets",
            "Align on test-point coverage",
            "Confirm change order timelines",
        ],
    },
    RoleType.SUPERVISOR: {
        "purpose": EmailPurpose.STATUS_UPDATE,
        "tone": EmailTone.PROFESSIONAL,
        "subject_hint": "Shift performance",
        "key_points": [
            "First pass yield at 98.4%",
            "Top defect: solder bridges on U12",
            "Request coaching slot for new operators",
        ],
    },
    RoleType.TEAM_LEAD: {
        "purpose": EmailPurpose.MEETING_CONFIRMATION,
        "tone": EmailTone.FRIENDLY,
        "subject_hint": "Daily standup confirmation",
        "key_points": [
            "Confirm 9:00 AM standup attendance",
            "Share blockers before end of shift",
            "Align on priority work orders",
        ],
    },
    RoleType.OPERATOR: {
        "purpose": EmailPurpose.ISSUE_NOTIFICATION,
        "tone": EmailTone.URGENT,
        "subject_hint": "Line stoppage alert",
        "key_points": [
            "Line 3 stopped due to feeder jam",
            "Safety check completed",
            "Request immediate support",
        ],
    },
    RoleType.VIEWER: {
        "purpose": EmailPurpose.INTRODUCTION,
        "tone": EmailTone.FRIENDLY,
        "subject_hint": "Introduction to weekly updates",
        "key_points": [
            "You will receive weekly operational summaries",
            "Reply with topics you want tracked",
            "We can add alerts for critical events",
        ],
    },
}


def _build_context(role: RoleType) -> EmailContext:
    scenario = ROLE_SCENARIOS[role]
    recipient = Recipient(
        email="jordan.lee@apexmfg.com",
        name="Jordan Lee",
        title="Operations Director",
        company="Apex Manufacturing",
        relationship="customer",
        language_preference=Language.ENGLISH,
        previous_interactions=4,
    )

    return EmailContext(
        purpose=scenario["purpose"],
        recipient=recipient,
        subject_hint=scenario.get("subject_hint"),
        key_points=scenario.get("key_points", []),
        attachments=["Scope Summary.pdf"] if role in {RoleType.SALES_ENGINEER, RoleType.ESTIMATOR} else [],
        reference_number="RFQ-2024-118",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        tone=scenario["tone"],
        language=Language.ENGLISH,
        include_signature=True,
        max_paragraphs=4,
        additional_context={"role": role.value},
    )


async def _record_thread(reasoning_id: str, entity_type: str, entity_id: str) -> bool:
    try:
        async with async_session_factory() as db:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                reasoning_id=reasoning_id,
                created_by_id=None,
                source="email_drafting_role_samples",
            )
            await db.commit()
        return True
    except Exception:
        return False


def _draft_to_dict(draft: Any) -> dict[str, Any]:
    return {
        "id": str(draft.id),
        "subject": draft.subject,
        "salutation": draft.salutation,
        "opening": draft.opening,
        "main_content": draft.main_content,
        "closing": draft.closing,
        "signature": draft.signature,
        "body_plain": draft.body_plain,
        "body_html": draft.body_html,
        "status": draft.status.value,
        "confidence_score": draft.confidence_score,
        "alternatives": draft.alternatives,
        "compliance_issues": draft.compliance_issues,
        "suggestions": draft.suggestions,
        "tokens_used": draft.tokens_used,
        "generation_time_ms": draft.generation_time_ms,
    }


async def generate_role_outputs(
    *,
    output_path: Path,
    thread_entity_type: str,
    thread_entity_id: str,
    record_thread: bool,
) -> None:
    service = AIEmailDraftingService()
    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thread": {
            "entity_type": thread_entity_type,
            "entity_id": thread_entity_id,
        },
        "roles": [],
    }

    for role in RoleType:
        context = _build_context(role)
        request = GenerationRequest(
            context=context,
            sender_name="Alex Morgan",
            sender_title="Account Manager",
            sender_email="alex.morgan@sensei.com",
            company_name="Sensei",
            requested_by=uuid4(),
        )
        reasoning_id = str(uuid4())
        thread_recorded = False
        if record_thread:
            thread_recorded = await _record_thread(reasoning_id, thread_entity_type, thread_entity_id)

        draft = service.generate_draft(request)
        results["roles"].append(
            {
                "role": role.value,
                "thread": {
                    "reasoning_id": reasoning_id,
                    "recorded": thread_recorded,
                },
                "context": {
                    "purpose": context.purpose.value,
                    "tone": context.tone.value,
                    "language": context.language.value,
                    "subject_hint": context.subject_hint,
                    "key_points": context.key_points,
                    "reference_number": context.reference_number,
                },
                "draft": _draft_to_dict(draft),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate email drafts for all roles.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "test-results" / "email-role-outputs.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--thread-entity-type",
        default="rfq",
        help="Thread entity type (default: rfq)",
    )
    parser.add_argument(
        "--thread-entity-id",
        default="RFQ-2024-118",
        help="Thread entity id (default: RFQ-2024-118)",
    )
    parser.add_argument(
        "--no-thread-record",
        action="store_true",
        help="Skip recording thread reasoning IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        generate_role_outputs(
            output_path=args.output,
            thread_entity_type=args.thread_entity_type,
            thread_entity_id=args.thread_entity_id,
            record_thread=not args.no_thread_record,
        )
    )


if __name__ == "__main__":
    main()
