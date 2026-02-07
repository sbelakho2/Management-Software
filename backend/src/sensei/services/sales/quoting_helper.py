import hashlib
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.api.deps import DBSession

from sensei.models.rfq import RFQ, RFQStatus
from sensei.models.quote import Quote, QuoteLineItem, QuoteStatus
from sensei.models.a3 import A3, A3Section
from sensei.models.quoting_helper import (
    WorkPacket,
    WorkPacketStatus,
    DisciplineType,
    PCBSpec,
    RateCard,
    RFQPackageVersion,
    QuoteActual,
)
from sensei.models.user import User
from sensei.models.project_management import Project, ProjectType, ProjectStatus
from sensei.models.product import Product, BOMItem, Routing
from sensei.models.quality import InspectionPlan
from sensei.models.andon import AndonEvent
from sensei.api.exceptions import NotFoundError, ConflictError
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.ai.onnx_text_embeddings import get_onnx_embedder
from sensei.core.storage import download_file
from sensei.services.smart_ingestion import SmartIngestionService

logger = logging.getLogger(__name__)


class QuotingHelperService:
    """
    Service for managing the Quoting Helper workflow.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_work_packets(self, rfq_id: UUID) -> List[WorkPacket]:
        """
        Generate default work packets for an RFQ based on its type.
        """
        # Check if RFQ exists
        rfq = await self.session.get(RFQ, rfq_id)
        if not rfq:
            raise NotFoundError(f"RFQ {rfq_id} not found")

        # Record reasoning in common thread
        await get_common_thread_service().record_reasoning(
            self.session,
            entity_type="rfq",
            entity_id=rfq_id,
            reasoning_id=f"work_packets_gen_{rfq_id}",
            source="quoting_helper",
        )

        # Check if work packets already exist
        stmt = select(WorkPacket).where(WorkPacket.rfq_id == rfq_id)
        result = await self.session.execute(stmt)
        existing_packets = result.scalars().all()
        if existing_packets:
            return list(existing_packets)

        # Default disciplines
        disciplines = [
            DisciplineType.EE,
            DisciplineType.EMBEDDED,
            DisciplineType.ME,
            DisciplineType.MFGE,
            DisciplineType.QE,
            DisciplineType.PURCHASING,
        ]

        packets = []
        now = datetime.now(timezone.utc)
        due_at = now + timedelta(days=2) # Default SLA: 2 days

        for disc in disciplines:
            packet = WorkPacket(
                rfq_id=rfq_id,
                discipline=disc.value,
                status=WorkPacketStatus.PENDING.value,
                due_at=due_at,
                outputs={},
                attachments=[],
            )
            self.session.add(packet)
            packets.append(packet)

        await self.session.commit()
        return packets

    async def get_work_packets(self, rfq_id: UUID) -> List[WorkPacket]:
        """Get all work packets for an RFQ."""
        stmt = select(WorkPacket).where(WorkPacket.rfq_id == rfq_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_work_packet(
        self, packet_id: UUID, update_data: Dict[str, Any]
    ) -> WorkPacket:
        """Update a work packet."""
        packet = await self.session.get(WorkPacket, packet_id)
        if not packet:
            raise NotFoundError(f"WorkPacket {packet_id} not found")

        for key, value in update_data.items():
            if hasattr(packet, key) and value is not None:
                setattr(packet, key, value)

        await self.session.commit()
        await self.session.refresh(packet)
        
        # Trigger risk detection after packet update
        await self.detect_technical_risks(packet.rfq_id)
        
        return packet

    async def calculate_cost_estimate(
        self, quote_id: UUID, rate_card_id: Optional[UUID] = None
    ) -> Quote:
        """
        Calculate cost estimate for a quote using deterministic rules and rate card.
        """
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Quote)
            .where(Quote.id == quote_id)
            .options(selectinload(Quote.line_items))
        )
        result = await self.session.execute(stmt)
        quote = result.scalar_one_or_none()
        
        if not quote:
            raise NotFoundError(f"Quote {quote_id} not found")

        # Get active rate card
        if rate_card_id:
            rate_card = await self.session.get(RateCard, rate_card_id)
        else:
            stmt = select(RateCard).where(RateCard.is_active == True).limit(1)
            result = await self.session.execute(stmt)
            rate_card = result.scalar_one_or_none()

        if not rate_card:
            raise NotFoundError("No active rate card found")

        # Implementation of Stage 3 Cost Engine
        # This is a simplified version of the logic
        total_material_cost = Decimal("0")
        total_labor_cost = Decimal("0")
        total_nre_cost = Decimal("0")

        # 1. Material Rollup (from line items/BOM)
        for item in quote.line_items:
            # In a real scenario, we'd look up supplier quotes and internal history
            material_cost = item.unit_cost or Decimal("0")
            total_material_cost += material_cost * item.quantity

        # 2. Labor Cost (placements, setups, hand ops)
        # Assuming some values are stored in custom_fields for now
        placements = Decimal(str(quote.custom_fields.get("total_placements", 0)))
        setup_count = int(quote.custom_fields.get("setup_count", 1))
        
        labor_hours = Decimal(str(quote.custom_fields.get("labor_hours", 0)))
        
        total_labor_cost += placements * rate_card.smt_placement_rate
        total_labor_cost += setup_count * rate_card.setup_charge
        total_labor_cost += labor_hours * rate_card.labor_rate_hourly

        # 3. Yield/Scrap Multipliers
        yield_multiplier = rate_card.default_yield_multiplier
        # Adjust based on risk if available
        risk_score = quote.custom_fields.get("risk_score", 0)
        if risk_score > 70:
            yield_multiplier += Decimal("0.05")

        total_cost = (total_material_cost + total_labor_cost) * yield_multiplier

        # Update quote costs
        quote.total_cost = total_cost
        
        # Recalculate margin if total is set
        if quote.total and quote.total > 0:
            quote.actual_margin = ((quote.total - total_cost) / quote.total) * 100

        await self.session.commit()
        await self.session.refresh(quote)
        return quote

    async def ingest_rfq_package(self, rfq_id: UUID, files: List[Dict[str, Any]]) -> RFQPackageVersion:
        """
        Stage 0 - Ingest RFQ package and run initial analysis.
        """
        rfq = await self.session.get(RFQ, rfq_id)
        if not rfq:
            raise NotFoundError(f"RFQ {rfq_id} not found")

        # Generate semantic embedding for the RFQ based on its title and description
        embedder = get_onnx_embedder()
        text_to_embed = f"{rfq.title} {rfq.description or ''}"
        rfq.embedding = embedder.embed_text(text_to_embed)

        # Get latest version number
        stmt = select(RFQPackageVersion).where(RFQPackageVersion.rfq_id == rfq_id).order_by(RFQPackageVersion.version_number.desc()).limit(1)
        result = await self.session.execute(stmt)
        latest_version = result.scalar_one_or_none()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # Calculate package checksum from provided file metadata
        checksum_source = "|".join(
            f"{f.get('checksum') or f.get('storage_key') or f.get('filename') or ''}"
            for f in files
        )
        checksum = hashlib.sha256(checksum_source.encode()).hexdigest() if checksum_source else hashlib.sha256(str(rfq_id).encode()).hexdigest()

        # Run Smart Ingestion against stored files
        ingestion_service = SmartIngestionService(db=self.session)
        extracted_metadata = {}
        
        ingestion_errors: list[dict[str, str]] = []
        for file_info in files:
            storage_key = file_info.get("storage_key")
            if not storage_key:
                ingestion_errors.append({"file": str(file_info), "error": "missing storage_key"})
                continue

            filename = file_info.get("filename") or storage_key.split("/")[-1]
            try:
                file_bytes = await download_file(storage_key)
                if not file_bytes:
                    ingestion_errors.append({"file": filename, "error": "file not found in storage"})
                    continue

                job = ingestion_service.ingest_document(filename, file_bytes)
                if job.extracted_entities:
                    for entity in job.extracted_entities:
                        extracted_metadata.update(entity.fields)
            except Exception as exc:
                logger.warning(
                    "Failed to ingest file %s for RFQ %s: %s",
                    filename, rfq_id, exc,
                )
                ingestion_errors.append({"file": filename, "error": str(exc)})
                continue

        if ingestion_errors:
            extracted_metadata["_ingestion_errors"] = ingestion_errors
            logger.warning(
                "RFQ %s package ingestion completed with %d error(s)",
                rfq_id, len(ingestion_errors),
            )

        package_version = RFQPackageVersion(
            rfq_id=rfq_id,
            version_number=new_version_number,
            files=files,
            extracted_metadata=extracted_metadata,
            checksum=checksum,
        )
        self.session.add(package_version)
        
        # Update RFQ triage score based on extracted metadata
        rfq.triage_risk_score = extracted_metadata.get("complexity_score")
        
        await self.session.commit()
        await self.session.refresh(package_version)
        return package_version

    async def convert_to_npi(self, quote_id: UUID, user_id: UUID) -> Project:
        """
        Stage 6.10 - One-click 'Quote -> NPI Pack'
        
        Converts an accepted quote into a formal NPI project with:
        - BOM freeze
        - Traveler baseline
        - Process route
        - Inspection plan stub
        """
        quote = await self.session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote {quote_id} not found")
            
        if quote.status != QuoteStatus.ACCEPTED.value:
            # In a real scenario, we might allow it anyway, but PRD implies PO arrived
            pass

        # 1. Create NPI Project
        project = Project(
            name=f"NPI: {quote.title}",
            slug=f"npi-{quote.quote_number.lower()}",
            description=f"New Product Introduction for {quote.quote_number}. Customer: {quote.account_id}",
            project_type=ProjectType.NPI.value,
            status=ProjectStatus.ACTIVE.value,
            owner_id=user_id,
            related_rfq_id=quote.rfq_id,
            start_date=datetime.now(timezone.utc).date(),
            tags=["npi", "quoting-handoff"],
        )
        self.session.add(project)
        await self.session.flush()

        # 2. Freeze BOM (Simplified: Create Product and BOM Items)
        product = Product(
            name=quote.title,
            part_number=quote.line_items[0].part_number if quote.line_items else "NEW-PART",
            revision="1.0",
            description=quote.description,
            status="active",
        )
        self.session.add(product)
        await self.session.flush()

        for item in quote.line_items:
            bom_item = BOMItem(
                product_id=product.id,
                component_part_number=item.part_number or "UNKNOWN",
                quantity=item.quantity,
                unit_of_measure="each",
                component_description=item.description,
            )
            self.session.add(bom_item)

        # 3. Generate initial Route
        # Based on Manufacturing Engineer packet outputs if available
        routing = Routing(
            product_id=product.id,
            sequence=10,
            operation_name="Initial Assembly",
            description="Auto-generated from NPI Handoff",
        )
        self.session.add(routing)

        # 4. Create Inspection Plan stub
        inspection_plan = InspectionPlan(
            name=f"IP-{product.part_number}",
            product_id=product.id,
            status="draft",
        )
        self.session.add(inspection_plan)

        # Record reasoning
        await get_common_thread_service().record_reasoning(
            self.session,
            entity_type="project",
            entity_id=project.id,
            reasoning_id=f"npi_handoff_{quote_id}",
            source="quoting_helper",
        )

        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def detect_technical_risks(self, rfq_id: UUID) -> List[AndonEvent]:
        """
        Requirement 4 - Jidoka / Andon for technical risks.
        """
        rfq = await self.session.get(RFQ, rfq_id)
        if not rfq:
            raise NotFoundError(f"RFQ {rfq_id} not found")

        packets = await self.get_work_packets(rfq_id)
        risks = []

        # 1. Missing Centroid / Unknown PCB finish (EE Packet)
        ee_packet = next((p for p in packets if p.discipline == DisciplineType.EE.value), None)
        if ee_packet:
            if not ee_packet.outputs.get("centroid_data_available", True):
                risks.append({
                    "reason": "missing_centroid",
                    "description": "Missing Centroid Data for placement estimation",
                    "severity": "high"
                })
            if not ee_packet.outputs.get("pcb_finish_specified", True):
                risks.append({
                    "reason": "unknown_pcb_finish",
                    "description": "Unknown PCB Finish",
                    "severity": "medium"
                })

        # 2. BGA without X-ray plan
        if ee_packet and ee_packet.outputs.get("has_bga", False):
            if not ee_packet.outputs.get("needs_xray", False):
                risks.append({
                    "reason": "bga_no_xray",
                    "description": "BGA detected without X-ray inspection plan",
                    "severity": "high"
                })

        # 3. BOM risks (Purchasing Packet)
        pur_packet = next((p for p in packets if p.discipline == DisciplineType.PURCHASING.value), None)
        if pur_packet:
            if pur_packet.outputs.get("obsolete_parts_count", 0) > 0:
                risks.append({
                    "reason": "obsolete_parts",
                    "description": f"{pur_packet.outputs['obsolete_parts_count']} obsolete parts detected in BOM",
                    "severity": "critical"
                })
            if pur_packet.outputs.get("single_source_count", 0) > 5:
                risks.append({
                    "reason": "single_source_risk",
                    "description": "High number of single-source components",
                    "severity": "medium"
                })

        # Create Andon Events for detected risks
        events = []
        for risk in risks:
            event = AndonEvent(
                title=f"Technical Risk: {risk['reason'].replace('_', ' ').title()}",
                description=risk['description'],
                entity_type="rfq",
                entity_id=str(rfq_id),
                status="active",
                severity=risk['severity'],
            )
            self.session.add(event)
            events.append(event)

        if events:
            await self.session.commit()
            logger.info(f"Detected {len(events)} technical risks for RFQ {rfq_id}. Andon triggered.")

        return events

    async def log_actuals_and_learn(self, quote_id: UUID, actual_data: Dict[str, Any]) -> QuoteActual:
        """
        Stage 5 - Post-Quote Learning. Compare quote vs actuals.
        """
        quote = await self.session.get(Quote, quote_id)
        if not quote:
            raise NotFoundError(f"Quote {quote_id} not found")

        actuals = QuoteActual(
            quote_id=quote_id,
            quoted_material_cost=quote.total_cost or Decimal("0"), # Simplified
            actual_material_cost=Decimal(str(actual_data.get("actual_material_cost", 0))),
            quoted_labor_minutes=int(quote.custom_fields.get("labor_minutes", 0)),
            actual_labor_minutes=int(actual_data.get("actual_labor_minutes", 0)),
            quoted_yield=Decimal(str(
                actual_data.get("quoted_yield")
                or quote.custom_fields.get("quoted_yield")
                or quote.custom_fields.get("estimated_yield")
                or actual_data.get("actual_yield")
                or 0
            )),
            actual_yield=Decimal(str(actual_data.get("actual_yield", 0))),
            variance_notes=actual_data.get("notes"),
            root_cause_categories=actual_data.get("root_causes", []),
        )
        self.session.add(actuals)

        # Trigger A3 if variance is > 15%
        material_variance = 0
        if actuals.quoted_material_cost > 0:
            material_variance = abs((actuals.actual_material_cost - actuals.quoted_material_cost) / actuals.quoted_material_cost)
        
        if material_variance > 0.15:
            a3 = A3(
                a3_number=f"A3-QUOTE-{quote.quote_number}",
                title=f"Recurring Quoting Error: {quote.quote_number}",
                summary=f"Significant variance in material cost detected. Quote: {actuals.quoted_material_cost}, Actual: {actuals.actual_material_cost}",
                status="draft",
            )
            self.session.add(a3)
            logger.warning(f"High variance detected for quote {quote_id}. A3 record created.")

        await self.session.commit()
        await self.session.refresh(actuals)
        return actuals

def get_quoting_helper_service(session: DBSession) -> QuotingHelperService:
    return QuotingHelperService(session)
