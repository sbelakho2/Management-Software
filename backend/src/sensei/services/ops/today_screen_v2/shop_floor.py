"""
Shop floor management for Today Screen.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

from sensei.services.ops.today_screen_v2.base import BaseRedisStore, InMemoryRedis
from sensei.services.ops.today_screen_models import (
    CAPAVerification,
    CellOEE,
    CriticalAndon,
    ExpiringCertification,
    KanbanAlert,
    ScheduledTraining,
    ShopFloorSummary,
    StationEfficiency,
    WIPViolation,
    WorkOrderAtRisk,
)

logger = logging.getLogger(__name__)


class ShopFloorManager(BaseRedisStore):
    """Manages shop floor data for the Today screen."""
    
    def __init__(self, redis_client: Any) -> None:
        # Use "shop_floor" as base store name, but we'll use global stores
        super().__init__(redis_client, "shop_floor")

    # ========== Work Orders at Risk ==========
    
    async def add_work_order_at_risk(
        self,
        work_order_id: UUID,
        work_order_number: str,
        job_name: str,
        customer_name: str,
        scheduled_ship_date: date,
        current_operation: str,
        work_center_id: UUID,
        work_center_name: str,
        reason_at_risk: str,
        estimated_delay_hours: float | None = None,
        priority: int = 3,
    ) -> WorkOrderAtRisk:
        """Add a work order at risk."""
        today = date.today()
        days_until_due = (scheduled_ship_date - today).days
        
        order = WorkOrderAtRisk(
            work_order_id=work_order_id,
            work_order_number=work_order_number,
            job_name=job_name,
            customer_name=customer_name,
            scheduled_ship_date=scheduled_ship_date,
            days_until_due=days_until_due,
            current_operation=current_operation,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            reason_at_risk=reason_at_risk,
            estimated_delay_hours=estimated_delay_hours,
            priority=priority,
        )
        
        await self._save_global_item("work_orders_at_risk", str(order.work_order_id), asdict(order))
        return order
    
    async def get_work_orders_at_risk(
        self,
        work_center_id: UUID | None = None,
    ) -> List[WorkOrderAtRisk]:
        """Get work orders at risk."""
        today = date.today()
        data = await self._get_global_store("work_orders_at_risk")
        result = []
        
        for order_dict in data.values():
            # Parse date if string
            if 'scheduled_ship_date' in order_dict and order_dict['scheduled_ship_date']:
                if isinstance(order_dict['scheduled_ship_date'], str):
                    order_dict['scheduled_ship_date'] = date.fromisoformat(order_dict['scheduled_ship_date'])
            
            order = WorkOrderAtRisk(**order_dict)
            # Update days until due
            order.days_until_due = (order.scheduled_ship_date - today).days
            
            if work_center_id and order.work_center_id != work_center_id:
                continue
            result.append(order)
        
        # Sort by priority then days until due
        result.sort(key=lambda o: (o.priority, o.days_until_due))
        return result
    
    async def resolve_work_order_risk(self, work_order_id: UUID) -> bool:
        """Resolve a work order risk."""
        key = "today:global:work_orders_at_risk"
        return await self._redis.hdel(key, str(work_order_id)) > 0

    # ========== Critical Andons ==========
    
    async def add_critical_andon(
        self,
        work_center_id: UUID,
        work_center_name: str,
        station_id: UUID,
        station_name: str,
        andon_type: str,
        description: str,
        raised_by_id: UUID,
        raised_by_name: str,
    ) -> CriticalAndon:
        """Add a critical Andon event."""
        andon = CriticalAndon(
            id=uuid4(),
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            station_id=station_id,
            station_name=station_name,
            andon_type=andon_type,
            description=description,
            raised_at=datetime.now(timezone.utc).replace(tzinfo=None),
            raised_by_id=raised_by_id,
            raised_by_name=raised_by_name,
            minutes_open=0,
            acknowledged=False,
            acknowledged_by_id=None,
            acknowledged_by_name=None,
        )
        
        payload = andon if isinstance(self._redis, InMemoryRedis) else asdict(andon)
        await self._save_global_item("critical_andons", str(andon.id), payload)
        return andon
    
    async def acknowledge_andon(
        self,
        andon_id: UUID,
        acknowledged_by_id: UUID,
        acknowledged_by_name: str,
    ) -> CriticalAndon | None:
        """Acknowledge an Andon event."""
        data = await self._get_global_store("critical_andons")
        cid_str = str(andon_id)
        if cid_str in data:
            andon_dict = data[cid_str]
            if isinstance(andon_dict, CriticalAndon):
                andon_dict.acknowledged = True
                andon_dict.acknowledged_by_id = acknowledged_by_id
                andon_dict.acknowledged_by_name = acknowledged_by_name
                await self._save_global_item("critical_andons", cid_str, andon_dict)
                return andon_dict

            andon_dict['acknowledged'] = True
            andon_dict['acknowledged_by_id'] = acknowledged_by_id if isinstance(self._redis, InMemoryRedis) else str(acknowledged_by_id)
            andon_dict['acknowledged_by_name'] = acknowledged_by_name
            await self._save_global_item("critical_andons", cid_str, andon_dict)
            
            if 'raised_at' in andon_dict and andon_dict['raised_at'] and isinstance(andon_dict['raised_at'], str):
                andon_dict['raised_at'] = datetime.fromisoformat(andon_dict['raised_at'])
            return CriticalAndon(**andon_dict)
        return None
    
    async def resolve_andon(self, andon_id: UUID) -> bool:
        """Resolve an Andon event."""
        key = "today:global:critical_andons"
        return await self._redis.hdel(key, str(andon_id)) > 0
    
    async def get_critical_andons(
        self,
        work_center_id: UUID | None = None,
        unacknowledged_only: bool = False,
    ) -> List[CriticalAndon]:
        """Get critical Andon events."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        data = await self._get_global_store("critical_andons")
        result = []
        
        for andon_dict in data.values():
            if isinstance(andon_dict, CriticalAndon):
                andon = andon_dict
            else:
                if 'raised_at' in andon_dict and andon_dict['raised_at'] and isinstance(andon_dict['raised_at'], str):
                    andon_dict['raised_at'] = datetime.fromisoformat(andon_dict['raised_at'])
                andon = CriticalAndon(**andon_dict)
            # Update minutes open
            andon.minutes_open = int((now - andon.raised_at).total_seconds() / 60)
            
            if work_center_id and andon.work_center_id != work_center_id:
                continue
            if unacknowledged_only and andon.acknowledged:
                continue
            result.append(andon)
        
        # Sort by acknowledged status (unacknowledged first), then by time open
        result.sort(key=lambda a: (0 if not a.acknowledged else 1, -a.minutes_open))
        return result

    # ========== Station Efficiency ==========
    
    async def add_station_efficiency(
        self,
        station_id: UUID,
        station_name: str,
        work_center_id: UUID,
        work_center_name: str,
        current_efficiency: float,
        target_efficiency: float,
        operator_id: UUID | None = None,
        operator_name: str | None = None,
    ) -> StationEfficiency:
        """Add or update station efficiency data."""
        variance = current_efficiency - target_efficiency
        is_below_target = current_efficiency < target_efficiency
        
        # Determine trend (in production, compare with historical data)
        trend = "stable"
        
        eff = StationEfficiency(
            station_id=station_id,
            station_name=station_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_efficiency=current_efficiency,
            target_efficiency=target_efficiency,
            variance=variance,
            trend=trend,
            is_below_target=is_below_target,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        
        await self._save_global_item("station_efficiencies", str(eff.station_id), asdict(eff))
        return eff
    
    async def get_low_efficiency_stations(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> List[StationEfficiency]:
        """Get stations with efficiency below target or threshold."""
        data = await self._get_global_store("station_efficiencies")
        result = []
        
        for eff_dict in data.values():
            eff = StationEfficiency(**eff_dict)
            if work_center_id and eff.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if eff.current_efficiency < threshold:
                    result.append(eff)
            elif eff.is_below_target:
                result.append(eff)
        
        # Sort by variance (worst first)
        result.sort(key=lambda e: e.variance)
        return result

    # ========== Cell OEE ==========
    
    async def add_cell_oee(
        self,
        cell_id: UUID,
        cell_name: str,
        work_center_id: UUID,
        work_center_name: str,
        availability: float,
        performance: float,
        quality: float,
        target_oee: float,
    ) -> CellOEE:
        """Add or update cell OEE data."""
        current_oee = (availability / 100) * (performance / 100) * (quality / 100) * 100
        variance = current_oee - target_oee
        
        oee = CellOEE(
            cell_id=cell_id,
            cell_name=cell_name,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            current_oee=round(current_oee, 2),
            target_oee=target_oee,
            availability=availability,
            performance=performance,
            quality=quality,
            is_below_threshold=current_oee < target_oee,
            variance=round(variance, 2),
        )
        
        await self._save_global_item("cell_oees", str(oee.cell_id), asdict(oee))
        return oee
    
    async def get_low_oee_cells(
        self,
        work_center_id: UUID | None = None,
        threshold: float | None = None,
    ) -> List[CellOEE]:
        """Get cells with OEE below target or threshold."""
        data = await self._get_global_store("cell_oees")
        result = []
        
        for oee_dict in data.values():
            oee = CellOEE(**oee_dict)
            if work_center_id and oee.work_center_id != work_center_id:
                continue
            if threshold is not None:
                if oee.current_oee < threshold:
                    result.append(oee)
            elif oee.is_below_threshold:
                result.append(oee)
        
        # Sort by variance (worst first)
        result.sort(key=lambda o: o.variance)
        return result
    
    async def get_overall_oee(self) -> float:
        """Get overall OEE across all cells."""
        data = await self._get_global_store("cell_oees")
        if not data:
            return 0.0
        
        total_oee = sum(oee['current_oee'] for oee in data.values())
        return round(total_oee / len(data), 2)

    # ========== Kanban Alerts ==========
    
    async def add_kanban_alert(
        self,
        material_code: str,
        material_name: str,
        bin_location: str,
        work_center_id: UUID,
        work_center_name: str,
        quantity_needed: float,
        unit: str,
        due_date: date,
        supplier_name: str | None = None,
        replenishment_status: str = "pending",
    ) -> KanbanAlert:
        """Add a Kanban alert."""
        days_overdue = (date.today() - due_date).days
        
        alert = KanbanAlert(
            id=uuid4(),
            material_code=material_code,
            material_name=material_name,
            bin_location=bin_location,
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            quantity_needed=quantity_needed,
            unit=unit,
            due_date=due_date,
            days_overdue=max(0, days_overdue),
            supplier_name=supplier_name,
            replenishment_status=replenishment_status,
        )
        
        await self._save_global_item("kanban_alerts", str(alert.id), asdict(alert))
        return alert
    
    async def update_kanban_status(
        self,
        kanban_id: UUID,
        status: str,
    ) -> KanbanAlert | None:
        """Update Kanban replenishment status."""
        data = await self._get_global_store("kanban_alerts")
        kid_str = str(kanban_id)
        if kid_str in data:
            alert_dict = data[kid_str]
            alert_dict['replenishment_status'] = status
            await self._save_global_item("kanban_alerts", kid_str, alert_dict)
            
            if 'due_date' in alert_dict and alert_dict['due_date'] and isinstance(alert_dict['due_date'], str):
                alert_dict['due_date'] = date.fromisoformat(alert_dict['due_date'])
            return KanbanAlert(**alert_dict)
        return None
    
    async def resolve_kanban_alert(self, kanban_id: UUID) -> bool:
        """Resolve a Kanban alert."""
        key = "today:global:kanban_alerts"
        return await self._redis.hdel(key, str(kanban_id)) > 0
    
    async def get_overdue_kanbans(
        self,
        work_center_id: UUID | None = None,
    ) -> List[KanbanAlert]:
        """Get overdue Kanban alerts."""
        today = date.today()
        data = await self._get_global_store("kanban_alerts")
        result = []
        
        for alert_dict in data.values():
            if 'due_date' in alert_dict and alert_dict['due_date'] and isinstance(alert_dict['due_date'], str):
                alert_dict['due_date'] = date.fromisoformat(alert_dict['due_date'])
            
            alert = KanbanAlert(**alert_dict)
            # Update days overdue
            alert.days_overdue = max(0, (today - alert.due_date).days)
            
            if work_center_id and alert.work_center_id != work_center_id:
                continue
            if alert.days_overdue > 0:
                result.append(alert)
        
        # Sort by days overdue (most overdue first)
        result.sort(key=lambda a: -a.days_overdue)
        return result

    # ========== Expiring Certifications ==========
    
    async def add_expiring_certification(
        self,
        user_id: UUID,
        user_name: str,
        certification_name: str,
        certification_type: str,
        expiration_date: date,
        required_for_work_centers: List[str] | None = None,
        renewal_training_id: UUID | None = None,
    ) -> ExpiringCertification:
        """Add an expiring certification."""
        today = date.today()
        days_until_expiry = (expiration_date - today).days
        is_expired = expiration_date < today
        
        cert = ExpiringCertification(
            id=uuid4(),
            user_id=user_id,
            user_name=user_name,
            certification_name=certification_name,
            certification_type=certification_type,
            expiration_date=expiration_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            required_for_work_centers=required_for_work_centers or [],
            renewal_training_id=renewal_training_id,
        )
        
        await self._save_global_item("expiring_certifications", str(cert.id), asdict(cert))
        return cert
    
    async def get_expiring_certifications(
        self,
        user_id: UUID | None = None,
        days_ahead: int = 30,
        include_expired: bool = True,
    ) -> List[ExpiringCertification]:
        """Get expiring certifications."""
        today = date.today()
        data = await self._get_global_store("expiring_certifications")
        result = []
        
        for cert_dict in data.values():
            if 'expiration_date' in cert_dict and cert_dict['expiration_date'] and isinstance(cert_dict['expiration_date'], str):
                cert_dict['expiration_date'] = date.fromisoformat(cert_dict['expiration_date'])
            
            cert = ExpiringCertification(**cert_dict)
            # Update days until expiry
            cert.days_until_expiry = (cert.expiration_date - today).days
            cert.is_expired = cert.expiration_date < today
            
            if user_id and cert.user_id != user_id:
                continue
            
            if cert.is_expired:
                if include_expired:
                    result.append(cert)
            elif cert.days_until_expiry <= days_ahead:
                result.append(cert)
        
        # Sort: expired first, then by days until expiry
        result.sort(key=lambda c: (0 if c.is_expired else 1, c.days_until_expiry))
        return result
    
    async def renew_certification(self, certification_id: UUID) -> bool:
        """Mark certification as renewed (remove from expiring list)."""
        key = "today:global:expiring_certifications"
        return await self._redis.hdel(key, str(certification_id)) > 0

    # ========== WIP Violations ==========
    
    async def add_wip_violation(
        self,
        work_center_id: UUID,
        work_center_name: str,
        current_wip: int,
        wip_limit: int,
        cell_id: UUID | None = None,
        cell_name: str | None = None,
    ) -> WIPViolation:
        """Add a WIP violation."""
        violation = WIPViolation(
            id=uuid4(),
            work_center_id=work_center_id,
            work_center_name=work_center_name,
            cell_id=cell_id,
            cell_name=cell_name,
            current_wip=current_wip,
            wip_limit=wip_limit,
            violation_amount=current_wip - wip_limit,
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            duration_minutes=0,
        )
        
        payload = violation if isinstance(self._redis, InMemoryRedis) else asdict(violation)
        await self._save_global_item("wip_violations", str(violation.id), payload)
        return violation
    
    async def get_wip_violations(
        self,
        work_center_id: UUID | None = None,
    ) -> List[WIPViolation]:
        """Get WIP violations."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        data = await self._get_global_store("wip_violations")
        result = []
        
        for v_dict in data.values():
            if isinstance(v_dict, WIPViolation):
                violation = v_dict
            else:
                if 'started_at' in v_dict and v_dict['started_at'] and isinstance(v_dict['started_at'], str):
                    v_dict['started_at'] = datetime.fromisoformat(v_dict['started_at'])
                violation = WIPViolation(**v_dict)
            # Update duration
            violation.duration_minutes = int((now - violation.started_at).total_seconds() / 60)
            
            if work_center_id and violation.work_center_id != work_center_id:
                continue
            result.append(violation)
        
        # Sort by violation amount (worst first)
        result.sort(key=lambda v: -v.violation_amount)
        return result
    
    async def resolve_wip_violation(self, violation_id: UUID) -> bool:
        """Resolve a WIP violation."""
        key = "today:global:wip_violations"
        return await self._redis.hdel(key, str(violation_id)) > 0

    # ========== CAPA Verifications ==========
    
    async def add_capa_verification(
        self,
        capa_number: str,
        title: str,
        capa_type: str,
        verification_due_date: date,
        owner_id: UUID,
        owner_name: str,
        original_nc_id: UUID | None = None,
        effectiveness_check: bool = False,
    ) -> CAPAVerification:
        """Add a CAPA verification."""
        today = date.today()
        days_until_due = (verification_due_date - today).days
        is_overdue = verification_due_date < today
        
        capa = CAPAVerification(
            id=uuid4(),
            capa_number=capa_number,
            title=title,
            capa_type=capa_type,
            verification_due_date=verification_due_date,
            days_until_due=days_until_due,
            is_overdue=is_overdue,
            owner_id=owner_id,
            owner_name=owner_name,
            original_nc_id=original_nc_id,
            effectiveness_check=effectiveness_check,
        )
        
        await self._save_global_item("capa_verifications", str(capa.id), asdict(capa))
        return capa
    
    async def get_capa_verifications_due(
        self,
        owner_id: UUID | None = None,
        days_ahead: int = 7,
        include_overdue: bool = True,
    ) -> List[CAPAVerification]:
        """Get CAPA verifications due."""
        today = date.today()
        data = await self._get_global_store("capa_verifications")
        result = []
        
        for capa_dict in data.values():
            if 'verification_due_date' in capa_dict and capa_dict['verification_due_date'] and isinstance(capa_dict['verification_due_date'], str):
                capa_dict['verification_due_date'] = date.fromisoformat(capa_dict['verification_due_date'])
            
            capa = CAPAVerification(**capa_dict)
            # Update status
            capa.days_until_due = (capa.verification_due_date - today).days
            capa.is_overdue = capa.verification_due_date < today
            
            if owner_id and capa.owner_id != owner_id:
                continue
            
            if capa.is_overdue:
                if include_overdue:
                    result.append(capa)
            elif capa.days_until_due <= days_ahead:
                result.append(capa)
        
        # Sort: overdue first, then by days until due
        result.sort(key=lambda c: (0 if c.is_overdue else 1, c.days_until_due))
        return result
    
    async def resolve_capa_verification(self, capa_id: UUID) -> bool:
        """Resolve a CAPA verification."""
        key = "today:global:capa_verifications"
        return await self._redis.hdel(key, str(capa_id)) > 0

    # ========== Scheduled Trainings ==========
    
    async def add_scheduled_training(
        self,
        title: str,
        training_type: str,
        scheduled_date: date,
        scheduled_time: str,
        duration_minutes: int,
        attendee_count: int = 0,
        description: str | None = None,
        location: str | None = None,
        instructor_name: str | None = None,
        max_attendees: int | None = None,
        is_user_enrolled: bool = False,
    ) -> ScheduledTraining:
        """Add a scheduled training session."""
        training = ScheduledTraining(
            id=uuid4(),
            title=title,
            description=description,
            training_type=training_type,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            location=location,
            instructor_name=instructor_name,
            attendee_count=attendee_count,
            max_attendees=max_attendees,
            is_user_enrolled=is_user_enrolled,
        )
        
        await self._save_global_item("scheduled_trainings", str(training.id), asdict(training))
        return training
    
    async def get_scheduled_trainings(
        self,
        target_date: date | None = None,
        user_enrolled_only: bool = False,
        days_ahead: int = 7,
    ) -> List[ScheduledTraining]:
        """Get scheduled training sessions."""
        today = date.today()
        data = await self._get_global_store("scheduled_trainings")
        result = []
        
        for t_dict in data.values():
            if 'scheduled_date' in t_dict and t_dict['scheduled_date']:
                if isinstance(t_dict['scheduled_date'], str):
                    t_dict['scheduled_date'] = date.fromisoformat(t_dict['scheduled_date'])
            
            training = ScheduledTraining(**t_dict)
            if user_enrolled_only and not training.is_user_enrolled:
                continue
            
            if target_date:
                if training.scheduled_date == target_date:
                    result.append(training)
            elif training.scheduled_date >= today and training.scheduled_date <= today + timedelta(days=days_ahead):
                result.append(training)
        
        # Sort by date and time
        result.sort(key=lambda t: (t.scheduled_date, t.scheduled_time))
        return result
    
    async def enroll_in_training(self, training_id: UUID) -> ScheduledTraining | None:
        """Enroll user in a training session."""
        data = await self._get_global_store("scheduled_trainings")
        tid_str = str(training_id)
        if tid_str in data:
            training_dict = data[tid_str]
            if training_dict.get('max_attendees') and training_dict.get('attendee_count', 0) >= training_dict['max_attendees']:
                return None
            
            training_dict['attendee_count'] = training_dict.get('attendee_count', 0) + 1
            training_dict['is_user_enrolled'] = True
            await self._save_global_item("scheduled_trainings", tid_str, training_dict)
            
            if 'scheduled_date' in training_dict and training_dict['scheduled_date']:
                if isinstance(training_dict['scheduled_date'], str):
                    training_dict['scheduled_date'] = date.fromisoformat(training_dict['scheduled_date'])
            
            return ScheduledTraining(**training_dict)
        return None

    # ========== Shop Floor Summary ==========
    
    async def get_shop_floor_summary(
        self,
        user_id: UUID | None = None,
        work_center_id: UUID | None = None,
    ) -> ShopFloorSummary:
        """Get complete shop floor summary for Today screen."""
        today = date.today()
        
        # Work orders at risk
        work_orders_at_risk = await self.get_work_orders_at_risk(work_center_id=work_center_id)
        
        # Critical Andons
        critical_andons = await self.get_critical_andons(work_center_id=work_center_id)
        unacknowledged = [a for a in critical_andons if not a.acknowledged]
        avg_response = (
            sum(a.minutes_open for a in critical_andons) / len(critical_andons)
            if critical_andons else 0.0
        )
        
        # Efficiency
        low_efficiency = await self.get_low_efficiency_stations(work_center_id=work_center_id)
        low_oee = await self.get_low_oee_cells(work_center_id=work_center_id)
        overall_oee = await self.get_overall_oee()
        
        # Kanbans
        overdue_kanbans = await self.get_overdue_kanbans(work_center_id=work_center_id)
        pending_data = await self._get_global_store("kanban_alerts")
        pending_kanbans = [
            k for k in pending_data.values()
            if k.get('replenishment_status') == "pending"
        ]
        
        # Certifications
        expiring_certs = await self.get_expiring_certifications(user_id=user_id)
        expired = [c for c in expiring_certs if c.is_expired]
        expiring_soon = [c for c in expiring_certs if not c.is_expired and c.days_until_expiry <= 30]
        
        # WIP violations
        wip_violations = await self.get_wip_violations(work_center_id=work_center_id)
        
        # CAPA verifications
        capa_due = await self.get_capa_verifications_due(owner_id=user_id)
        overdue_capas = [c for c in capa_due if c.is_overdue]
        
        # Scheduled trainings
        trainings_today = await self.get_scheduled_trainings(target_date=today)
        all_trainings = await self.get_scheduled_trainings()
        
        return ShopFloorSummary(
            work_orders_at_risk=work_orders_at_risk,
            work_orders_at_risk_count=len(work_orders_at_risk),
            critical_andons=critical_andons,
            unacknowledged_andon_count=len(unacknowledged),
            avg_andon_response_minutes=round(avg_response, 1),
            low_efficiency_stations=low_efficiency,
            low_oee_cells=low_oee,
            overall_oee=overall_oee,
            overdue_kanbans=overdue_kanbans,
            pending_kanban_count=len(pending_kanbans),
            expiring_certifications=expiring_certs,
            expired_certification_count=len(expired),
            expiring_soon_count=len(expiring_soon),
            wip_violations=wip_violations,
            total_wip_violation_count=len(wip_violations),
            capa_verifications_due=capa_due,
            overdue_capa_count=len(overdue_capas),
            scheduled_trainings=all_trainings,
            training_sessions_today=len(trainings_today),
        )
