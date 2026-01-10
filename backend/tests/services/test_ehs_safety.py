"""
Tests for EHS / Safety Compliance Service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from sensei.services.ehs_safety import (
    # Enums
    IncidentSeverity,
    IncidentType,
    IncidentStatus,
    BodyPart,
    HazardCategory,
    RiskLevel,
    PPEType,
    CertificationType,
    CertificationStatus,
    AlertPriority,
    # Data Models
    SafetyIncident,
    JSAHazard,
    JobSafetyAnalysis,
    EmployeeCertification,
    SafetyAlert,
    JSAAcknowledgment,
    AuditPack,
    # Service
    EHSSafetyService,
    create_ehs_safety_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance."""
    return EHSSafetyService()


@pytest.fixture
def sample_incident(service):
    """Create a sample incident."""
    return service.report_incident(
        incident_type=IncidentType.INJURY,
        severity=IncidentSeverity.FIRST_AID,
        description="Employee cut finger on sharp edge",
        location_id="shop-floor-1",
        work_center_id="wc-001",
        reported_by="emp-001",
        injured_employee_id="emp-002",
        body_parts=[BodyPart.FINGER],
    )


@pytest.fixture
def sample_near_miss(service):
    """Create a sample near-miss."""
    return service.report_near_miss(
        description="Forklift nearly hit pedestrian in aisle",
        location_id="warehouse-1",
        reported_by="emp-003",
        photos=["photo1.jpg", "photo2.jpg"],
    )


@pytest.fixture
def sample_jsa(service):
    """Create a sample JSA."""
    jsa = service.create_jsa(
        work_center_id="wc-001",
        job_name="CNC Machine Operation",
        job_description="Operating CNC milling machine",
        station_id="station-001",
        prepared_by="safety-mgr",
    )
    return jsa


@pytest.fixture
def sample_certification(service):
    """Create a sample certification."""
    return service.add_certification(
        employee_id="emp-001",
        certification_type=CertificationType.FORKLIFT,
        certification_name="Powered Industrial Truck Operator",
        issue_date=datetime.now(timezone.utc) - timedelta(days=30),
        expiry_date=datetime.now(timezone.utc) + timedelta(days=335),
        training_provider="Safety Training Inc.",
        training_hours=Decimal("8"),
    )


# =============================================================================
# TEST: ENUMS
# =============================================================================


class TestEnums:
    """Tests for enumeration types."""
    
    def test_incident_severity_values(self):
        """Test IncidentSeverity enum values."""
        assert IncidentSeverity.NEAR_MISS == "near_miss"
        assert IncidentSeverity.FIRST_AID == "first_aid"
        assert IncidentSeverity.RECORDABLE == "recordable"
        assert IncidentSeverity.LOST_TIME == "lost_time"
        assert IncidentSeverity.CRITICAL == "critical"
        assert IncidentSeverity.FATAL == "fatal"
    
    def test_incident_type_values(self):
        """Test IncidentType enum values."""
        assert IncidentType.INJURY == "injury"
        assert IncidentType.SLIP_TRIP_FALL == "slip_trip_fall"
        assert IncidentType.CHEMICAL == "chemical"
        assert IncidentType.ELECTRICAL == "electrical"
    
    def test_hazard_category_values(self):
        """Test HazardCategory enum values."""
        assert HazardCategory.MECHANICAL == "mechanical"
        assert HazardCategory.ELECTRICAL == "electrical"
        assert HazardCategory.CHEMICAL == "chemical"
        assert HazardCategory.ERGONOMIC == "ergonomic"
    
    def test_ppe_type_values(self):
        """Test PPEType enum values."""
        assert PPEType.SAFETY_GLASSES == "safety_glasses"
        assert PPEType.HARD_HAT == "hard_hat"
        assert PPEType.SAFETY_SHOES == "safety_shoes"
        assert PPEType.CUT_RESISTANT_GLOVES == "cut_resistant_gloves"
    
    def test_certification_type_values(self):
        """Test CertificationType enum values."""
        assert CertificationType.FORKLIFT == "forklift"
        assert CertificationType.LOTO == "loto"
        assert CertificationType.FIRST_AID == "first_aid"
        assert CertificationType.CONFINED_SPACE == "confined_space"
    
    def test_alert_priority_values(self):
        """Test AlertPriority enum values."""
        assert AlertPriority.INFORMATION == "information"
        assert AlertPriority.WARNING == "warning"
        assert AlertPriority.URGENT == "urgent"
        assert AlertPriority.CRITICAL == "critical"


# =============================================================================
# TEST: DATA MODELS
# =============================================================================


class TestDataModels:
    """Tests for data models."""
    
    def test_safety_incident_creation(self):
        """Test SafetyIncident creation."""
        incident = SafetyIncident(
            id="inc-001",
            incident_number="INC-000001",
            incident_type=IncidentType.INJURY,
            severity=IncidentSeverity.FIRST_AID,
        )
        
        assert incident.id == "inc-001"
        assert incident.status == IncidentStatus.REPORTED
        assert incident.osha_recordable is False
    
    def test_jsa_hazard_creation(self):
        """Test JSAHazard creation."""
        hazard = JSAHazard(
            id="hazard-001",
            step_number=1,
            task_step="Load material",
            hazard_category=HazardCategory.MECHANICAL,
            hazard_description="Pinch point at chuck",
            potential_consequences="Finger crush",
            initial_risk_level=RiskLevel.HIGH,
        )
        
        assert hazard.id == "hazard-001"
        assert hazard.residual_risk_level == RiskLevel.LOW
    
    def test_job_safety_analysis_creation(self):
        """Test JobSafetyAnalysis creation."""
        jsa = JobSafetyAnalysis(
            id="jsa-001",
            jsa_number="JSA-00001",
            work_center_id="wc-001",
            job_name="Test Job",
        )
        
        assert jsa.id == "jsa-001"
        assert jsa.is_active is True
        assert jsa.revision == 1
    
    def test_employee_certification_creation(self):
        """Test EmployeeCertification creation."""
        cert = EmployeeCertification(
            id="cert-001",
            employee_id="emp-001",
            certification_type=CertificationType.FORKLIFT,
        )
        
        assert cert.id == "cert-001"
        assert cert.status == CertificationStatus.ACTIVE
    
    def test_safety_alert_creation(self):
        """Test SafetyAlert creation."""
        alert = SafetyAlert(
            id="alert-001",
            alert_number="ALERT-00001",
            priority=AlertPriority.URGENT,
            title="Chemical Spill",
            message="Spill in aisle 5",
        )
        
        assert alert.id == "alert-001"
        assert alert.is_active is True


# =============================================================================
# TEST: INCIDENT & NEAR-MISS MANAGEMENT
# =============================================================================


class TestIncidentManagement:
    """Tests for incident management functions."""
    
    def test_report_incident(self, service):
        """Test reporting an incident."""
        incident = service.report_incident(
            incident_type=IncidentType.SLIP_TRIP_FALL,
            severity=IncidentSeverity.RECORDABLE,
            description="Employee slipped on wet floor",
            location_id="area-1",
        )
        
        assert incident.id is not None
        assert incident.incident_number.startswith("INC-")
        assert incident.status == IncidentStatus.REPORTED
        assert incident.osha_recordable is True  # RECORDABLE severity
    
    def test_report_near_miss(self, service):
        """Test reporting a near-miss."""
        near_miss = service.report_near_miss(
            description="Heavy object nearly fell on worker",
            location_id="area-2",
            photos=["photo.jpg"],
        )
        
        assert near_miss.severity == IncidentSeverity.NEAR_MISS
        assert near_miss.osha_recordable is False
        assert "photo.jpg" in near_miss.photos
    
    def test_critical_incident_triggers_alert(self, service):
        """Test that critical incidents auto-trigger alerts."""
        incident = service.report_incident(
            incident_type=IncidentType.INJURY,
            severity=IncidentSeverity.CRITICAL,
            description="Severe injury requiring hospitalization",
            location_id="area-1",
        )
        
        alerts = service.get_active_alerts()
        assert len(alerts) >= 1
        assert alerts[0].priority == AlertPriority.CRITICAL
        assert alerts[0].incident_id == incident.id
    
    def test_get_incident(self, service, sample_incident):
        """Test getting incident by ID."""
        incident = service.get_incident(sample_incident.id)
        assert incident is not None
        assert incident.id == sample_incident.id
    
    def test_get_incident_by_number(self, service, sample_incident):
        """Test getting incident by number."""
        incident = service.get_incident_by_number(sample_incident.incident_number)
        assert incident is not None
        assert incident.incident_number == sample_incident.incident_number
    
    def test_get_incidents_filtering(self, service, sample_incident, sample_near_miss):
        """Test filtering incidents."""
        # By severity
        near_misses = service.get_incidents(severity=IncidentSeverity.NEAR_MISS)
        assert len(near_misses) == 1
        
        # By type
        injuries = service.get_incidents(incident_type=IncidentType.INJURY)
        assert len(injuries) == 1
        
        # Open only
        open_incidents = service.get_incidents(open_only=True)
        assert len(open_incidents) == 2
    
    def test_start_investigation(self, service, sample_incident):
        """Test starting an investigation."""
        updated = service.start_investigation(
            sample_incident.id,
            investigator_id="safety-mgr",
        )
        
        assert updated.status == IncidentStatus.UNDER_INVESTIGATION
        assert updated.investigator_id == "safety-mgr"
        assert updated.investigation_started is not None
    
    def test_add_five_why(self, service, sample_incident):
        """Test adding 5-Why analysis steps."""
        service.start_investigation(sample_incident.id, "safety-mgr")
        
        service.add_five_why(sample_incident.id, "Why did the cut occur?", "Sharp edge on part")
        service.add_five_why(sample_incident.id, "Why was the edge sharp?", "Deburring not complete")
        
        incident = service.get_incident(sample_incident.id)
        assert len(incident.five_why_analysis) == 2
        assert incident.five_why_analysis[0]["step"] == 1
    
    def test_set_root_cause(self, service, sample_incident):
        """Test setting root cause."""
        service.start_investigation(sample_incident.id, "safety-mgr")
        
        updated = service.set_root_cause(
            sample_incident.id,
            root_cause="Inadequate deburring process",
            contributing_factors=["Rush order pressure", "No deburr verification step"],
        )
        
        assert updated.status == IncidentStatus.ROOT_CAUSE_IDENTIFIED
        assert updated.root_cause == "Inadequate deburring process"
        assert len(updated.contributing_factors) == 2
    
    def test_add_corrective_action(self, service, sample_incident):
        """Test adding corrective actions."""
        service.start_investigation(sample_incident.id, "safety-mgr")
        
        updated = service.add_corrective_action(
            sample_incident.id,
            action_description="Add deburring verification step",
            responsible_id="eng-001",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        assert updated.status == IncidentStatus.CORRECTIVE_ACTION
        assert len(updated.corrective_actions) == 1
    
    def test_add_preventive_action(self, service, sample_incident):
        """Test adding preventive actions."""
        updated = service.add_corrective_action(
            sample_incident.id,
            action_description="Train all operators on deburr hazards",
            responsible_id="safety-mgr",
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            is_preventive=True,
        )
        
        assert len(updated.preventive_actions) == 1
    
    def test_complete_action(self, service, sample_incident):
        """Test completing a corrective action."""
        service.add_corrective_action(
            sample_incident.id,
            action_description="Install guard",
            responsible_id="eng-001",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        incident = service.get_incident(sample_incident.id)
        action_id = incident.corrective_actions[0]["id"]
        
        updated = service.complete_action(
            sample_incident.id,
            action_id,
            completion_notes="Guard installed and tested",
        )
        
        assert updated.corrective_actions[0]["status"] == "completed"
    
    def test_close_incident(self, service, sample_incident):
        """Test closing an incident."""
        updated = service.close_incident(
            sample_incident.id,
            closed_by="safety-mgr",
            verification_notes="All actions completed and verified effective",
        )
        
        assert updated.status == IncidentStatus.CLOSED
        assert updated.closed_by == "safety-mgr"
        assert updated.closed_at is not None


# =============================================================================
# TEST: JOB SAFETY ANALYSIS (JSA)
# =============================================================================


class TestJSAManagement:
    """Tests for JSA management functions."""
    
    def test_create_jsa(self, service):
        """Test creating a JSA."""
        jsa = service.create_jsa(
            work_center_id="wc-001",
            job_name="Welding Operation",
            job_description="Manual welding of steel assemblies",
            prepared_by="safety-eng",
        )
        
        assert jsa.id is not None
        assert jsa.jsa_number.startswith("JSA-")
        assert jsa.is_active is True
    
    def test_add_hazard_to_jsa(self, service, sample_jsa):
        """Test adding hazards to a JSA."""
        updated = service.add_hazard_to_jsa(
            sample_jsa.id,
            task_step="Load workpiece into chuck",
            hazard_category=HazardCategory.MECHANICAL,
            hazard_description="Pinch point between workpiece and chuck jaws",
            potential_consequences="Finger crush injury",
            initial_risk_level=RiskLevel.HIGH,
            engineering_controls=["Chuck guard installed"],
            administrative_controls=["Keep hands clear of rotating parts"],
            ppe_required=[PPEType.SAFETY_GLASSES, PPEType.SAFETY_SHOES],
            residual_risk_level=RiskLevel.LOW,
        )
        
        assert len(updated.hazards) == 1
        assert updated.hazards[0].step_number == 1
        assert PPEType.SAFETY_GLASSES in updated.ppe_matrix
    
    def test_electrical_hazard_sets_loto(self, service, sample_jsa):
        """Test that electrical hazards auto-set LOTO requirement."""
        service.add_hazard_to_jsa(
            sample_jsa.id,
            task_step="Access electrical panel",
            hazard_category=HazardCategory.ELECTRICAL,
            hazard_description="Live electrical components",
            potential_consequences="Electrocution",
            initial_risk_level=RiskLevel.CRITICAL,
        )
        
        jsa = service.get_jsa(sample_jsa.id)
        assert jsa.loto_required is True
    
    def test_get_jsa(self, service, sample_jsa):
        """Test getting JSA by ID."""
        jsa = service.get_jsa(sample_jsa.id)
        assert jsa is not None
        assert jsa.id == sample_jsa.id
    
    def test_get_jsa_for_station(self, service, sample_jsa):
        """Test getting JSA for a station."""
        jsa = service.get_jsa_for_station("station-001")
        assert jsa is not None
        assert jsa.station_id == "station-001"
    
    def test_get_jsas_by_work_center(self, service, sample_jsa):
        """Test filtering JSAs by work center."""
        jsas = service.get_jsas(work_center_id="wc-001")
        assert len(jsas) >= 1
    
    def test_approve_jsa(self, service, sample_jsa):
        """Test approving a JSA."""
        approved = service.approve_jsa(
            sample_jsa.id,
            reviewed_by="safety-eng",
            approved_by="plant-mgr",
        )
        
        assert approved.reviewed_by == "safety-eng"
        assert approved.approved_by == "plant-mgr"
        assert approved.approval_date is not None
        assert approved.expiry_date is not None
    
    def test_set_jsa_training_requirements(self, service, sample_jsa):
        """Test setting training requirements for a JSA."""
        updated = service.set_jsa_training_requirements(
            sample_jsa.id,
            training_required=[CertificationType.LOTO, CertificationType.GENERAL_SAFETY],
            permit_required=True,
        )
        
        assert len(updated.training_required) == 2
        assert updated.permit_required is True
    
    def test_get_ppe_matrix_for_station(self, service, sample_jsa):
        """Test getting PPE matrix for station."""
        service.add_hazard_to_jsa(
            sample_jsa.id,
            task_step="Test step",
            hazard_category=HazardCategory.MECHANICAL,
            hazard_description="Test hazard",
            potential_consequences="Test consequence",
            initial_risk_level=RiskLevel.MEDIUM,
            ppe_required=[PPEType.SAFETY_GLASSES, PPEType.HARD_HAT],
        )
        
        ppe = service.get_ppe_matrix_for_station("station-001")
        assert PPEType.SAFETY_GLASSES in ppe
        assert PPEType.HARD_HAT in ppe
    
    def test_revise_jsa(self, service, sample_jsa):
        """Test revising a JSA."""
        new_jsa = service.revise_jsa(
            sample_jsa.id,
            revised_by="safety-eng",
        )
        
        # New revision created
        assert new_jsa.id != sample_jsa.id
        assert new_jsa.jsa_number == sample_jsa.jsa_number  # Same number
        assert new_jsa.revision == sample_jsa.revision + 1
        
        # Old version deactivated
        old_jsa = service.get_jsa(sample_jsa.id)
        assert old_jsa.is_active is False


# =============================================================================
# TEST: CERTIFICATIONS & TRAINING
# =============================================================================


class TestCertificationManagement:
    """Tests for certification management functions."""
    
    def test_add_certification(self, service):
        """Test adding a certification."""
        cert = service.add_certification(
            employee_id="emp-001",
            certification_type=CertificationType.FORKLIFT,
            issue_date=datetime.now(timezone.utc),
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            training_provider="Safety Co",
        )
        
        assert cert.id is not None
        assert cert.status == CertificationStatus.ACTIVE
    
    def test_certification_expiring_soon_status(self, service):
        """Test that certifications expiring soon are flagged."""
        cert = service.add_certification(
            employee_id="emp-001",
            certification_type=CertificationType.FIRST_AID,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),  # Within 60 days
        )
        
        assert cert.status == CertificationStatus.EXPIRING_SOON
    
    def test_certification_expired_status(self, service):
        """Test that expired certifications are flagged."""
        cert = service.add_certification(
            employee_id="emp-001",
            certification_type=CertificationType.CPR_AED,
            expiry_date=datetime.now(timezone.utc) - timedelta(days=10),  # Past expiry
        )
        
        assert cert.status == CertificationStatus.EXPIRED
    
    def test_get_certification(self, service, sample_certification):
        """Test getting certification by ID."""
        cert = service.get_certification(sample_certification.id)
        assert cert is not None
        assert cert.id == sample_certification.id
    
    def test_get_employee_certifications(self, service, sample_certification):
        """Test getting certifications for an employee."""
        # Add another cert
        service.add_certification(
            employee_id="emp-001",
            certification_type=CertificationType.FIRST_AID,
        )
        
        certs = service.get_employee_certifications("emp-001")
        assert len(certs) == 2
    
    def test_get_employee_certifications_by_type(self, service, sample_certification):
        """Test filtering certifications by type."""
        certs = service.get_employee_certifications(
            "emp-001",
            cert_type=CertificationType.FORKLIFT,
        )
        assert len(certs) == 1
    
    def test_get_expiring_certifications(self, service):
        """Test getting expiring certifications."""
        # Add cert expiring in 30 days
        service.add_certification(
            employee_id="emp-002",
            certification_type=CertificationType.LOTO,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
        )
        
        expiring = service.get_expiring_certifications(days_ahead=60)
        assert len(expiring) >= 1
    
    def test_renew_certification(self, service, sample_certification):
        """Test renewing a certification."""
        new_expiry = datetime.now(timezone.utc) + timedelta(days=730)
        
        renewed = service.renew_certification(
            sample_certification.id,
            new_expiry_date=new_expiry,
            training_hours=Decimal("4"),
        )
        
        assert renewed.expiry_date == new_expiry
        assert renewed.status == CertificationStatus.ACTIVE
    
    def test_verify_certification(self, service, sample_certification):
        """Test verifying a certification."""
        verified = service.verify_certification(
            sample_certification.id,
            verified_by="hr-mgr",
        )
        
        assert verified.verified_by == "hr-mgr"
        assert verified.verified_date is not None
    
    def test_get_training_matrix(self, service, sample_certification):
        """Test getting training matrix."""
        matrix = service.get_training_matrix(
            employee_ids=["emp-001"],
            cert_types=[CertificationType.FORKLIFT, CertificationType.LOTO],
        )
        
        assert "emp-001" in matrix
        assert matrix["emp-001"][CertificationType.FORKLIFT.value] == CertificationStatus.ACTIVE.value
        assert matrix["emp-001"][CertificationType.LOTO.value] == CertificationStatus.NOT_CERTIFIED.value


# =============================================================================
# TEST: SAFETY GATING
# =============================================================================


class TestSafetyGating:
    """Tests for safety gating functions."""
    
    def test_check_operator_clearance_no_jsa(self, service):
        """Test clearance check when no JSA exists."""
        result = service.check_operator_safety_clearance("emp-001", "station-999")
        
        assert result["cleared"] is True
        assert "No JSA defined" in result["warnings"][0]
    
    def test_check_operator_clearance_missing_acknowledgment(self, service, sample_jsa):
        """Test clearance check when JSA not acknowledged."""
        result = service.check_operator_safety_clearance("emp-001", "station-001")
        
        assert result["cleared"] is False
        assert any("acknowledgment required" in m for m in result["missing"])
    
    def test_check_operator_clearance_missing_training(self, service, sample_jsa):
        """Test clearance check when training is missing."""
        # Acknowledge JSA
        service.acknowledge_jsa("emp-001", sample_jsa.id)
        
        # Require LOTO training
        service.set_jsa_training_requirements(
            sample_jsa.id,
            training_required=[CertificationType.LOTO],
        )
        
        result = service.check_operator_safety_clearance("emp-001", "station-001")
        
        assert result["cleared"] is False
        assert any("Training required" in m for m in result["missing"])
    
    def test_check_operator_clearance_all_good(self, service, sample_jsa):
        """Test clearance check when all requirements met."""
        # Acknowledge JSA
        service.acknowledge_jsa("emp-001", sample_jsa.id)
        
        # Require and provide LOTO training
        service.set_jsa_training_requirements(
            sample_jsa.id,
            training_required=[CertificationType.LOTO],
        )
        service.add_certification(
            employee_id="emp-001",
            certification_type=CertificationType.LOTO,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
        )
        
        result = service.check_operator_safety_clearance("emp-001", "station-001")
        
        assert result["cleared"] is True
        assert len(result["missing"]) == 0
    
    def test_acknowledge_jsa(self, service, sample_jsa):
        """Test acknowledging a JSA."""
        ack = service.acknowledge_jsa(
            "emp-001",
            sample_jsa.id,
            signature_data="base64-signature-data",
        )
        
        assert ack is not None
        assert ack.employee_id == "emp-001"
        assert ack.jsa_revision == sample_jsa.revision


# =============================================================================
# TEST: SAFETY ALERTS
# =============================================================================


class TestSafetyAlerts:
    """Tests for safety alert functions."""
    
    def test_create_safety_alert(self, service):
        """Test creating a safety alert."""
        alert = service.create_safety_alert(
            priority=AlertPriority.URGENT,
            title="Chemical Spill",
            message="Chemical spill in building A, evacuate immediately",
            triggered_by="safety-officer",
            location_ids=["building-a"],
            expires_in_hours=4,
        )
        
        assert alert.id is not None
        assert alert.alert_number.startswith("ALERT-")
        assert alert.is_active is True
        assert alert.expires_at is not None
    
    def test_get_alert(self, service):
        """Test getting alert by ID."""
        alert = service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Test Alert",
            message="Test message",
        )
        
        fetched = service.get_alert(alert.id)
        assert fetched is not None
        assert fetched.id == alert.id
    
    def test_get_active_alerts(self, service):
        """Test getting active alerts."""
        service.create_safety_alert(
            priority=AlertPriority.URGENT,
            title="Alert 1",
            message="Message 1",
        )
        service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Alert 2",
            message="Message 2",
        )
        
        alerts = service.get_active_alerts()
        assert len(alerts) == 2
        # Sorted by priority (urgent first)
        assert alerts[0].priority == AlertPriority.URGENT
    
    def test_get_alerts_by_location(self, service):
        """Test filtering alerts by location."""
        service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Location Alert",
            message="Message",
            location_ids=["area-1"],
        )
        
        alerts = service.get_active_alerts(location_id="area-1")
        assert len(alerts) == 1
    
    def test_acknowledge_alert(self, service):
        """Test acknowledging an alert."""
        alert = service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Test",
            message="Test",
        )
        
        updated = service.acknowledge_alert(alert.id, "emp-001")
        
        assert "emp-001" in updated.acknowledged_by
    
    def test_clear_alert(self, service):
        """Test clearing an alert."""
        alert = service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Test",
            message="Test",
        )
        
        cleared = service.clear_alert(alert.id, "safety-mgr")
        
        assert cleared.is_active is False
        assert cleared.cleared_at is not None
        assert cleared.cleared_by == "safety-mgr"
    
    def test_expired_alerts_not_active(self, service):
        """Test that expired alerts are not returned as active."""
        alert = service.create_safety_alert(
            priority=AlertPriority.WARNING,
            title="Expiring",
            message="Test",
            expires_in_hours=1,
        )
        
        # Manually expire
        alert.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        alerts = service.get_active_alerts()
        assert alert not in alerts


# =============================================================================
# TEST: AUDIT PACK GENERATION
# =============================================================================


class TestAuditPackGeneration:
    """Tests for audit pack generation functions."""
    
    def test_generate_audit_pack(self, service, sample_incident, sample_jsa, sample_certification):
        """Test generating an audit pack."""
        pack = service.generate_audit_pack(
            pack_name="Q1 2025 Safety Audit",
            generated_by="safety-mgr",
            include_incidents=True,
            include_jsas=True,
            include_training=True,
            include_alerts=True,
        )
        
        assert pack.id is not None
        assert pack.pack_name == "Q1 2025 Safety Audit"
        assert len(pack.documents) > 0
        assert "incidents" in pack.categories_included
        assert "job_safety_analyses" in pack.categories_included
        assert "training_records" in pack.categories_included
    
    def test_generate_audit_pack_with_date_range(self, service, sample_incident):
        """Test generating audit pack with date filtering."""
        pack = service.generate_audit_pack(
            pack_name="January Incidents",
            date_range_start=datetime.now(timezone.utc) - timedelta(days=30),
            date_range_end=datetime.now(timezone.utc),
            include_incidents=True,
            include_jsas=False,
            include_training=False,
            include_alerts=False,
        )
        
        assert pack.date_range_start is not None
        assert pack.date_range_end is not None
        # Should include our sample incident (created today)
        incident_docs = [d for d in pack.documents if d["type"] == "incident_report"]
        assert len(incident_docs) >= 1
    
    def test_get_audit_pack(self, service, sample_incident):
        """Test getting audit pack by ID."""
        pack = service.generate_audit_pack(
            pack_name="Test Pack",
            include_incidents=True,
        )
        
        fetched = service.get_audit_pack(pack.id)
        assert fetched is not None
        assert fetched.id == pack.id


# =============================================================================
# TEST: STATISTICS
# =============================================================================


class TestStatistics:
    """Tests for statistics functions."""
    
    def test_get_statistics(self, service, sample_incident, sample_near_miss, sample_jsa, sample_certification):
        """Test getting EHS statistics."""
        stats = service.get_statistics()
        
        assert stats["total_incidents"] >= 2
        assert stats["near_miss_count"] >= 1
        assert stats["total_jsas"] >= 1
        assert stats["total_certifications"] >= 1
        assert "incidents_by_severity" in stats
        assert "certifications_by_status" in stats


# =============================================================================
# TEST: FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_ehs_safety_service(self):
        """Test factory function creates service."""
        service = create_ehs_safety_service()
        
        assert service is not None
        assert isinstance(service, EHSSafetyService)
    
    def test_factory_creates_fresh_instance(self):
        """Test factory creates independent instances."""
        service1 = create_ehs_safety_service()
        service2 = create_ehs_safety_service()
        
        service1.report_near_miss("Test", location_id="test")
        
        assert len(service1.get_incidents()) == 1
        assert len(service2.get_incidents()) == 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_get_nonexistent_incident(self, service):
        """Test getting non-existent incident."""
        result = service.get_incident("nonexistent")
        assert result is None
    
    def test_get_nonexistent_incident_by_number(self, service):
        """Test getting non-existent incident by number."""
        result = service.get_incident_by_number("INC-999999")
        assert result is None
    
    def test_start_investigation_nonexistent(self, service):
        """Test starting investigation on non-existent incident."""
        result = service.start_investigation("nonexistent", "user")
        assert result is None
    
    def test_add_five_why_nonexistent(self, service):
        """Test adding 5-Why to non-existent incident."""
        result = service.add_five_why("nonexistent", "why", "answer")
        assert result is None
    
    def test_close_nonexistent_incident(self, service):
        """Test closing non-existent incident."""
        result = service.close_incident("nonexistent", "user")
        assert result is None
    
    def test_get_nonexistent_jsa(self, service):
        """Test getting non-existent JSA."""
        result = service.get_jsa("nonexistent")
        assert result is None
    
    def test_add_hazard_to_nonexistent_jsa(self, service):
        """Test adding hazard to non-existent JSA."""
        result = service.add_hazard_to_jsa(
            "nonexistent",
            "step",
            HazardCategory.MECHANICAL,
            "desc",
            "consequences",
            RiskLevel.LOW,
        )
        assert result is None
    
    def test_approve_nonexistent_jsa(self, service):
        """Test approving non-existent JSA."""
        result = service.approve_jsa("nonexistent", "reviewer", "approver")
        assert result is None
    
    def test_revise_nonexistent_jsa(self, service):
        """Test revising non-existent JSA."""
        result = service.revise_jsa("nonexistent", "user")
        assert result is None
    
    def test_acknowledge_nonexistent_jsa(self, service):
        """Test acknowledging non-existent JSA."""
        result = service.acknowledge_jsa("emp-001", "nonexistent")
        assert result is None
    
    def test_get_nonexistent_certification(self, service):
        """Test getting non-existent certification."""
        result = service.get_certification("nonexistent")
        assert result is None
    
    def test_renew_nonexistent_certification(self, service):
        """Test renewing non-existent certification."""
        result = service.renew_certification("nonexistent", datetime.now(timezone.utc))
        assert result is None
    
    def test_verify_nonexistent_certification(self, service):
        """Test verifying non-existent certification."""
        result = service.verify_certification("nonexistent", "user")
        assert result is None
    
    def test_get_nonexistent_alert(self, service):
        """Test getting non-existent alert."""
        result = service.get_alert("nonexistent")
        assert result is None
    
    def test_acknowledge_nonexistent_alert(self, service):
        """Test acknowledging non-existent alert."""
        result = service.acknowledge_alert("nonexistent", "user")
        assert result is None
    
    def test_clear_nonexistent_alert(self, service):
        """Test clearing non-existent alert."""
        result = service.clear_alert("nonexistent", "user")
        assert result is None
    
    def test_ppe_matrix_no_jsa(self, service):
        """Test PPE matrix for station with no JSA."""
        result = service.get_ppe_matrix_for_station("no-jsa-station")
        assert result == []
