"""
Tests for TPS (Toyota Production System) Teacher.

Tests PDCA Coaching, Improvement Kata, Muda Detection, and Jidoka.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sensei.services.tps_teacher import (
    # Enums
    PDCAPhase,
    PhaseGateStatus,
    MudaType,
    KataStep,
    AndonStatus,
    JidokaAction,
    # Data models
    PDCACycle,
    PhaseGateRequirement,
    CoachingPrompt,
    KataSession,
    MudaDetection,
    AndonEvent,
    JidokaResponse,
    # Classes
    PDCACoachingEngine,
    ImprovementKataAssistant,
    MudaDetectionEngine,
    JidokaMentor,
    TPSTeacher,
    # Factory functions
    create_tps_teacher,
    create_pdca_engine,
    create_kata_assistant,
    create_muda_detector,
    create_jidoka_mentor,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def pdca_engine() -> PDCACoachingEngine:
    """Create PDCA engine."""
    return create_pdca_engine()


@pytest.fixture
def kata_assistant() -> ImprovementKataAssistant:
    """Create Kata assistant."""
    return create_kata_assistant()


@pytest.fixture
def muda_detector() -> MudaDetectionEngine:
    """Create Muda detector."""
    return create_muda_detector()


@pytest.fixture
def jidoka_mentor() -> JidokaMentor:
    """Create Jidoka mentor."""
    return create_jidoka_mentor()


@pytest.fixture
def tps_teacher() -> TPSTeacher:
    """Create TPS teacher."""
    return create_tps_teacher()


@pytest.fixture
def sample_process_data() -> dict:
    """Create sample process data with waste indicators."""
    return {
        "location": "Assembly Line A",
        "output_qty": 120,
        "demand_qty": 100,
        "unit_cost": 50,
        "idle_time_pct": 20,
        "hourly_cost": 100,
        "wip_days": 7,
        "wip_value": 10000,
        "defect_rate": 3,
        "steps_per_unit": 15,
        "standard_steps": 10,
    }


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_pdca_phase_values(self):
        """Test PDCAPhase enum values."""
        assert PDCAPhase.PLAN == "plan"
        assert PDCAPhase.DO == "do"
        assert PDCAPhase.CHECK == "check"
        assert PDCAPhase.ACT == "act"
    
    def test_phase_gate_status_values(self):
        """Test PhaseGateStatus enum values."""
        assert PhaseGateStatus.NOT_STARTED == "not_started"
        assert PhaseGateStatus.IN_PROGRESS == "in_progress"
        assert PhaseGateStatus.PENDING_REVIEW == "pending_review"
        assert PhaseGateStatus.APPROVED == "approved"
        assert PhaseGateStatus.BLOCKED == "blocked"
        assert PhaseGateStatus.COMPLETED == "completed"
    
    def test_muda_type_values(self):
        """Test MudaType enum values."""
        assert MudaType.OVERPRODUCTION == "overproduction"
        assert MudaType.WAITING == "waiting"
        assert MudaType.TRANSPORT == "transport"
        assert MudaType.OVERPROCESSING == "overprocessing"
        assert MudaType.INVENTORY == "inventory"
        assert MudaType.MOTION == "motion"
        assert MudaType.DEFECTS == "defects"
        assert MudaType.UNDERUTILIZED_TALENT == "underutilized_talent"
    
    def test_kata_step_values(self):
        """Test KataStep enum values."""
        assert KataStep.DIRECTION == "direction"
        assert KataStep.GRASP_CURRENT == "grasp_current"
        assert KataStep.TARGET_CONDITION == "target_condition"
        assert KataStep.EXPERIMENT == "experiment"
        assert KataStep.REFLECT == "reflect"
    
    def test_andon_status_values(self):
        """Test AndonStatus enum values."""
        assert AndonStatus.GREEN == "green"
        assert AndonStatus.YELLOW == "yellow"
        assert AndonStatus.RED == "red"
        assert AndonStatus.BLUE == "blue"
    
    def test_jidoka_action_values(self):
        """Test JidokaAction enum values."""
        assert JidokaAction.CONTINUE == "continue"
        assert JidokaAction.ALERT == "alert"
        assert JidokaAction.SLOW_DOWN == "slow_down"
        assert JidokaAction.STOP == "stop"
        assert JidokaAction.ESCALATE == "escalate"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_pdca_cycle_creation(self):
        """Test PDCACycle creation."""
        cycle = PDCACycle(
            cycle_id="cycle_001",
            title="Reduce Setup Time",
            problem_statement="Setup takes 60 minutes, target is 30 minutes",
            current_phase=PDCAPhase.PLAN,
            phase_statuses={p: PhaseGateStatus.NOT_STARTED for p in PDCAPhase},
            owner="john_doe",
            team_members=["alice", "bob"],
            started_at=datetime.now(),
            target_completion=datetime.now() + timedelta(days=30),
        )
        assert cycle.cycle_id == "cycle_001"
        assert cycle.current_phase == PDCAPhase.PLAN
    
    def test_phase_gate_requirement_creation(self):
        """Test PhaseGateRequirement creation."""
        req = PhaseGateRequirement(
            requirement_id="req_001",
            phase=PDCAPhase.PLAN,
            description="Root cause analysis completed",
            is_mandatory=True,
            verification_method="manual",
        )
        assert req.is_mandatory
        assert req.phase == PDCAPhase.PLAN
    
    def test_coaching_prompt_creation(self):
        """Test CoachingPrompt creation."""
        prompt = CoachingPrompt(
            prompt_id="prompt_001",
            phase=PDCAPhase.DO,
            prompt_text="Are you implementing as planned?",
            guidance="Check for deviations",
            examples=["Example 1"],
        )
        assert prompt.phase == PDCAPhase.DO
    
    def test_kata_session_creation(self):
        """Test KataSession creation."""
        session = KataSession(
            session_id="kata_001",
            challenge="Improve throughput",
            current_step=KataStep.DIRECTION,
            current_condition="Current throughput is 100/hour",
            target_condition="",
            obstacles=[],
            experiments=[],
            learnings=[],
        )
        assert session.current_step == KataStep.DIRECTION
    
    def test_muda_detection_creation(self):
        """Test MudaDetection creation."""
        detection = MudaDetection(
            detection_id="muda_001",
            muda_type=MudaType.WAITING,
            location="Station 5",
            description="Operators waiting for material",
            estimated_impact=500.0,
            detected_at=datetime.now(),
            evidence=["Idle time log"],
            severity=3,
            suggested_countermeasure="Implement kanban",
        )
        assert detection.muda_type == MudaType.WAITING
        assert detection.severity == 3
    
    def test_andon_event_creation(self):
        """Test AndonEvent creation."""
        event = AndonEvent(
            event_id="andon_001",
            station_id="station_A",
            status=AndonStatus.YELLOW,
            issue_description="Quality deviation detected",
            detected_at=datetime.now(),
        )
        assert event.status == AndonStatus.YELLOW
        assert event.resolved_at is None
    
    def test_jidoka_response_creation(self):
        """Test JidokaResponse creation."""
        response = JidokaResponse(
            response_id="jidoka_001",
            trigger="Defect detected",
            action=JidokaAction.STOP,
            details="Line stopped for quality issue",
            affected_process="Assembly",
            timestamp=datetime.now(),
            quality_impact="Critical",
        )
        assert response.action == JidokaAction.STOP


# =============================================================================
# PDCA COACHING ENGINE TESTS
# =============================================================================


class TestPDCACoachingEngine:
    """Test PDCACoachingEngine."""
    
    def test_create_cycle(self, pdca_engine):
        """Test creating a PDCA cycle."""
        cycle = pdca_engine.create_cycle(
            title="Reduce Defects",
            problem_statement="Defect rate is 5%, target is 1%",
            owner="manager_1",
            team_members=["worker_1", "worker_2"],
        )
        
        assert cycle.cycle_id
        assert cycle.current_phase == PDCAPhase.PLAN
        assert cycle.phase_statuses[PDCAPhase.PLAN] == PhaseGateStatus.IN_PROGRESS
    
    def test_get_phase_requirements(self, pdca_engine):
        """Test getting phase requirements."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        requirements = pdca_engine.get_phase_requirements(cycle.cycle_id)
        
        assert len(requirements) > 0
        assert all(r.phase == PDCAPhase.PLAN for r in requirements)
    
    def test_get_coaching_prompts(self, pdca_engine):
        """Test getting coaching prompts."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        prompts = pdca_engine.get_coaching_prompts(cycle.cycle_id)
        
        assert len(prompts) > 0
        for prompt in prompts:
            assert prompt.prompt_text
            assert prompt.phase == PDCAPhase.PLAN
    
    def test_add_artifact(self, pdca_engine):
        """Test adding artifacts."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        result = pdca_engine.add_artifact(
            cycle.cycle_id,
            PDCAPhase.PLAN,
            "Root cause analysis document",
        )
        
        assert result
        assert len(pdca_engine.cycles[cycle.cycle_id].artifacts[PDCAPhase.PLAN]) == 1
    
    def test_check_gate_readiness_not_ready(self, pdca_engine):
        """Test gate readiness check when not ready."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        result = pdca_engine.check_gate_readiness(cycle.cycle_id, [])
        
        assert not result["ready"]
        assert "missing" in result
    
    def test_check_gate_readiness_ready(self, pdca_engine):
        """Test gate readiness check when ready."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        # Complete all mandatory requirements for PLAN phase
        completed = ["plan_1", "plan_2", "plan_3", "plan_4"]
        result = pdca_engine.check_gate_readiness(cycle.cycle_id, completed)
        
        assert result["ready"]
        assert result["next_phase"] == "do"
    
    def test_advance_phase(self, pdca_engine):
        """Test advancing phase."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        assert cycle.current_phase == PDCAPhase.PLAN
        
        cycle = pdca_engine.advance_phase(cycle.cycle_id)
        
        assert cycle.current_phase == PDCAPhase.DO
        assert cycle.phase_statuses[PDCAPhase.PLAN] == PhaseGateStatus.COMPLETED
        assert cycle.phase_statuses[PDCAPhase.DO] == PhaseGateStatus.IN_PROGRESS
    
    def test_full_cycle(self, pdca_engine):
        """Test completing a full PDCA cycle."""
        cycle = pdca_engine.create_cycle(
            "Test", "Problem", "owner", [],
        )
        
        # Advance through all phases
        pdca_engine.advance_phase(cycle.cycle_id)  # PLAN -> DO
        pdca_engine.advance_phase(cycle.cycle_id)  # DO -> CHECK
        pdca_engine.advance_phase(cycle.cycle_id)  # CHECK -> ACT
        cycle = pdca_engine.advance_phase(cycle.cycle_id)  # ACT -> Complete
        
        assert cycle.actual_completion is not None
        assert cycle.cycle_id in pdca_engine.completed_cycles
    
    def test_get_cycle_status(self, pdca_engine):
        """Test getting cycle status."""
        cycle = pdca_engine.create_cycle(
            "Test Cycle", "Problem", "owner", [],
        )
        
        status = pdca_engine.get_cycle_status(cycle.cycle_id)
        
        assert status["title"] == "Test Cycle"
        assert status["current_phase"] == "plan"
        assert status["progress_pct"] == 0


# =============================================================================
# IMPROVEMENT KATA ASSISTANT TESTS
# =============================================================================


class TestImprovementKataAssistant:
    """Test ImprovementKataAssistant."""
    
    def test_start_session(self, kata_assistant):
        """Test starting a Kata session."""
        session = kata_assistant.start_session(
            challenge="Improve cycle time",
            current_condition="Current cycle time is 10 minutes",
            coach="sensei_1",
        )
        
        assert session.session_id
        assert session.current_step == KataStep.DIRECTION
        assert session.coach == "sensei_1"
    
    def test_get_daily_coaching(self, kata_assistant):
        """Test getting daily coaching prompts."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        prompts = kata_assistant.get_daily_coaching(session.session_id)
        
        assert len(prompts) > 0
        for prompt in prompts:
            assert prompt.phase == KataStep.DIRECTION
    
    def test_record_obstacle(self, kata_assistant):
        """Test recording obstacles."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        result = kata_assistant.record_obstacle(
            session.session_id,
            "Machine breakdown frequency",
        )
        
        assert result
        assert len(kata_assistant.sessions[session.session_id].obstacles) == 1
    
    def test_record_experiment(self, kata_assistant):
        """Test recording experiments."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        result = kata_assistant.record_experiment(
            session.session_id,
            "Add preventive maintenance checklist",
            "Reduce breakdown by 50%",
        )
        
        assert result
        assert len(kata_assistant.sessions[session.session_id].experiments) == 1
    
    def test_set_target_condition(self, kata_assistant):
        """Test setting target condition."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        result = kata_assistant.set_target_condition(
            session.session_id,
            "Cycle time reduced to 7 minutes by end of month",
        )
        
        assert result
        assert kata_assistant.sessions[session.session_id].target_condition
    
    def test_record_learning(self, kata_assistant):
        """Test recording learnings."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        result = kata_assistant.record_learning(
            session.session_id,
            "Small batches reduce waiting waste",
        )
        
        assert result
        assert len(kata_assistant.sessions[session.session_id].learnings) == 1
    
    def test_advance_step(self, kata_assistant):
        """Test advancing Kata steps."""
        session = kata_assistant.start_session(
            "Challenge", "Current state",
        )
        
        assert session.current_step == KataStep.DIRECTION
        
        session = kata_assistant.advance_step(session.session_id)
        assert session.current_step == KataStep.GRASP_CURRENT
        
        session = kata_assistant.advance_step(session.session_id)
        assert session.current_step == KataStep.TARGET_CONDITION
    
    def test_get_session_summary(self, kata_assistant):
        """Test getting session summary."""
        session = kata_assistant.start_session(
            "Improve Quality", "Current defect rate 5%",
        )
        kata_assistant.record_obstacle(session.session_id, "Training gap")
        kata_assistant.record_experiment(session.session_id, "Train team", "Reduce errors")
        
        summary = kata_assistant.get_session_summary(session.session_id)
        
        assert summary["challenge"] == "Improve Quality"
        assert summary["obstacles_count"] == 1
        assert summary["experiments_count"] == 1


# =============================================================================
# MUDA DETECTION ENGINE TESTS
# =============================================================================


class TestMudaDetectionEngine:
    """Test MudaDetectionEngine."""
    
    def test_analyze_overproduction(self, muda_detector):
        """Test detecting overproduction waste."""
        data = {
            "location": "Line A",
            "output_qty": 150,
            "demand_qty": 100,
            "unit_cost": 10,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        overproduction = [d for d in detections if d.muda_type == MudaType.OVERPRODUCTION]
        assert len(overproduction) == 1
        assert overproduction[0].estimated_impact == 500.0  # (150-100) * 10
    
    def test_analyze_waiting(self, muda_detector):
        """Test detecting waiting waste."""
        data = {
            "location": "Line B",
            "idle_time_pct": 25,
            "hourly_cost": 100,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        waiting = [d for d in detections if d.muda_type == MudaType.WAITING]
        assert len(waiting) == 1
        assert waiting[0].severity == 3  # <30%
    
    def test_analyze_waiting_high_severity(self, muda_detector):
        """Test high severity waiting waste."""
        data = {
            "location": "Line B",
            "idle_time_pct": 40,
            "hourly_cost": 100,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        waiting = [d for d in detections if d.muda_type == MudaType.WAITING]
        assert len(waiting) == 1
        assert waiting[0].severity == 5  # >=30%
    
    def test_analyze_inventory(self, muda_detector):
        """Test detecting inventory waste."""
        data = {
            "location": "Warehouse",
            "wip_days": 10,
            "wip_value": 50000,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        inventory = [d for d in detections if d.muda_type == MudaType.INVENTORY]
        assert len(inventory) == 1
        assert inventory[0].estimated_impact == 1000.0  # 50000 * 2%
    
    def test_analyze_defects(self, muda_detector):
        """Test detecting defect waste."""
        data = {
            "location": "QC Station",
            "defect_rate": 4,
            "unit_cost": 100,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        defects = [d for d in detections if d.muda_type == MudaType.DEFECTS]
        assert len(defects) == 1
        assert defects[0].severity == 4  # <5%
    
    def test_analyze_motion(self, muda_detector):
        """Test detecting motion waste."""
        data = {
            "location": "Assembly",
            "steps_per_unit": 20,
            "standard_steps": 10,
        }
        
        detections = muda_detector.analyze_process_data(data)
        
        motion = [d for d in detections if d.muda_type == MudaType.MOTION]
        assert len(motion) == 1
    
    def test_analyze_multiple_wastes(self, muda_detector, sample_process_data):
        """Test detecting multiple types of waste."""
        detections = muda_detector.analyze_process_data(sample_process_data)
        
        # Should detect multiple waste types
        muda_types = {d.muda_type for d in detections}
        assert len(muda_types) >= 3
    
    def test_get_waste_summary(self, muda_detector, sample_process_data):
        """Test getting waste summary."""
        muda_detector.analyze_process_data(sample_process_data)
        
        summary = muda_detector.get_waste_summary()
        
        assert summary["total_detections"] > 0
        assert summary["total_impact"] > 0
        assert "by_type" in summary
    
    def test_get_high_severity_waste(self, muda_detector, sample_process_data):
        """Test getting high severity waste."""
        muda_detector.analyze_process_data(sample_process_data)
        
        high_severity = muda_detector.get_high_severity_waste(threshold=4)
        
        for detection in high_severity:
            assert detection.severity >= 4
    
    def test_clear_detections(self, muda_detector, sample_process_data):
        """Test clearing detections."""
        muda_detector.analyze_process_data(sample_process_data)
        assert len(muda_detector.detections) > 0
        
        count = muda_detector.clear_detections()
        
        assert count > 0
        assert len(muda_detector.detections) == 0


# =============================================================================
# JIDOKA MENTOR TESTS
# =============================================================================


class TestJidokaMentor:
    """Test JidokaMentor."""
    
    def test_trigger_andon(self, jidoka_mentor):
        """Test triggering Andon."""
        event = jidoka_mentor.trigger_andon(
            station_id="station_1",
            status=AndonStatus.YELLOW,
            issue_description="Quality deviation detected",
        )
        
        assert event.event_id
        assert event.status == AndonStatus.YELLOW
        assert jidoka_mentor.station_status["station_1"] == AndonStatus.YELLOW
    
    def test_trigger_andon_creates_jidoka_response(self, jidoka_mentor):
        """Test that triggering Andon creates Jidoka response."""
        jidoka_mentor.trigger_andon(
            "station_1", AndonStatus.RED, "Critical issue",
        )
        
        assert len(jidoka_mentor.jidoka_responses) == 1
        assert jidoka_mentor.jidoka_responses[0].action == JidokaAction.STOP
    
    def test_respond_to_andon(self, jidoka_mentor):
        """Test responding to Andon."""
        event = jidoka_mentor.trigger_andon(
            "station_1", AndonStatus.YELLOW, "Issue",
        )
        
        updated = jidoka_mentor.respond_to_andon(event.event_id, "operator_1")
        
        assert updated.responded_at is not None
        assert updated.responder == "operator_1"
    
    def test_resolve_andon(self, jidoka_mentor):
        """Test resolving Andon."""
        event = jidoka_mentor.trigger_andon(
            "station_1", AndonStatus.YELLOW, "Issue",
        )
        jidoka_mentor.respond_to_andon(event.event_id, "operator_1")
        
        resolved = jidoka_mentor.resolve_andon(
            event.event_id,
            "Material defect",
            "Replaced supplier",
        )
        
        assert resolved.resolved_at is not None
        assert resolved.root_cause == "Material defect"
        assert jidoka_mentor.station_status["station_1"] == AndonStatus.GREEN
    
    def test_get_active_andons(self, jidoka_mentor):
        """Test getting active Andons."""
        jidoka_mentor.trigger_andon("station_1", AndonStatus.YELLOW, "Issue 1")
        event2 = jidoka_mentor.trigger_andon("station_2", AndonStatus.RED, "Issue 2")
        
        # Resolve one
        jidoka_mentor.resolve_andon(event2.event_id, "Root", "Fix")
        
        active = jidoka_mentor.get_active_andons()
        
        assert len(active) == 1
        assert active[0].station_id == "station_1"
    
    def test_get_station_status(self, jidoka_mentor):
        """Test getting station status."""
        # Default should be green
        assert jidoka_mentor.get_station_status("unknown") == AndonStatus.GREEN
        
        jidoka_mentor.trigger_andon("station_1", AndonStatus.RED, "Issue")
        assert jidoka_mentor.get_station_status("station_1") == AndonStatus.RED
    
    def test_get_response_metrics(self, jidoka_mentor):
        """Test getting response metrics."""
        event1 = jidoka_mentor.trigger_andon("s1", AndonStatus.YELLOW, "Issue 1")
        event2 = jidoka_mentor.trigger_andon("s2", AndonStatus.RED, "Issue 2")
        
        jidoka_mentor.respond_to_andon(event1.event_id, "op1")
        jidoka_mentor.resolve_andon(event2.event_id, "Root", "Fix")
        
        metrics = jidoka_mentor.get_response_metrics()
        
        assert metrics["total_events"] == 2
        assert metrics["responded"] == 1
        assert metrics["resolved"] == 1
        assert "by_status" in metrics
    
    def test_get_quality_loop_summary(self, jidoka_mentor):
        """Test getting quality loop summary."""
        # Create and resolve some events
        for i in range(3):
            event = jidoka_mentor.trigger_andon(f"s{i}", AndonStatus.YELLOW, f"Issue {i}")
            jidoka_mentor.resolve_andon(event.event_id, "Material issue", "Improve inspection")
        
        summary = jidoka_mentor.get_quality_loop_summary()
        
        assert summary["resolved_count"] == 3
        assert len(summary["top_root_causes"]) > 0
    
    def test_andon_status_to_action_mapping(self, jidoka_mentor):
        """Test Andon status to Jidoka action mapping."""
        # GREEN -> CONTINUE
        jidoka_mentor.trigger_andon("s1", AndonStatus.GREEN, "Normal")
        assert jidoka_mentor.jidoka_responses[-1].action == JidokaAction.CONTINUE
        
        # YELLOW -> ALERT
        jidoka_mentor.trigger_andon("s2", AndonStatus.YELLOW, "Warning")
        assert jidoka_mentor.jidoka_responses[-1].action == JidokaAction.ALERT
        
        # RED -> STOP
        jidoka_mentor.trigger_andon("s3", AndonStatus.RED, "Critical")
        assert jidoka_mentor.jidoka_responses[-1].action == JidokaAction.STOP
        
        # BLUE -> SLOW_DOWN
        jidoka_mentor.trigger_andon("s4", AndonStatus.BLUE, "Quality check")
        assert jidoka_mentor.jidoka_responses[-1].action == JidokaAction.SLOW_DOWN


# =============================================================================
# TPS TEACHER TESTS
# =============================================================================


class TestTPSTeacher:
    """Test TPSTeacher orchestrator."""
    
    def test_teacher_creation(self, tps_teacher):
        """Test TPS teacher creation."""
        assert tps_teacher.pdca_engine is not None
        assert tps_teacher.kata_assistant is not None
        assert tps_teacher.muda_detector is not None
        assert tps_teacher.jidoka_mentor is not None
    
    def test_start_improvement_cycle(self, tps_teacher):
        """Test starting improvement cycle."""
        result = tps_teacher.start_improvement_cycle(
            title="Reduce Lead Time",
            problem="Lead time is 10 days, target is 5 days",
            owner="manager_1",
            team=["worker_1", "worker_2"],
        )
        
        assert "pdca_cycle_id" in result
        assert "kata_session_id" in result
        assert "coaching_prompts" in result
    
    def test_get_daily_teaching(self, tps_teacher):
        """Test getting daily teaching."""
        result = tps_teacher.start_improvement_cycle(
            "Test", "Problem", "owner", [],
        )
        
        teaching = tps_teacher.get_daily_teaching(
            pdca_cycle_id=result["pdca_cycle_id"],
            kata_session_id=result["kata_session_id"],
        )
        
        assert "pdca_prompts" in teaching
        assert "kata_prompts" in teaching
        assert "waste_summary" in teaching
        assert "active_andons" in teaching
    
    def test_analyze_for_waste(self, tps_teacher, sample_process_data):
        """Test analyzing for waste."""
        detections = tps_teacher.analyze_for_waste(sample_process_data)
        
        assert len(detections) > 0
        for detection in detections:
            assert isinstance(detection, MudaDetection)
    
    def test_trigger_quality_stop(self, tps_teacher):
        """Test triggering quality stop."""
        event = tps_teacher.trigger_quality_stop(
            station_id="assembly_1",
            issue="Dimension out of spec",
            severity="red",
        )
        
        assert event.status == AndonStatus.RED
    
    def test_get_tps_metrics(self, tps_teacher, sample_process_data):
        """Test getting TPS metrics."""
        # Create some activity
        tps_teacher.start_improvement_cycle("Test", "Problem", "owner", [])
        tps_teacher.analyze_for_waste(sample_process_data)
        tps_teacher.trigger_quality_stop("s1", "Issue", "yellow")
        
        metrics = tps_teacher.get_tps_metrics()
        
        assert "pdca_cycles" in metrics
        assert "kata_sessions" in metrics
        assert "muda" in metrics
        assert "jidoka" in metrics
        assert metrics["pdca_cycles"]["active"] == 1


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_tps_teacher(self):
        """Test creating TPS teacher."""
        teacher = create_tps_teacher()
        assert isinstance(teacher, TPSTeacher)
    
    def test_create_pdca_engine(self):
        """Test creating PDCA engine."""
        engine = create_pdca_engine()
        assert isinstance(engine, PDCACoachingEngine)
    
    def test_create_kata_assistant(self):
        """Test creating Kata assistant."""
        assistant = create_kata_assistant()
        assert isinstance(assistant, ImprovementKataAssistant)
    
    def test_create_muda_detector(self):
        """Test creating Muda detector."""
        detector = create_muda_detector()
        assert isinstance(detector, MudaDetectionEngine)
    
    def test_create_jidoka_mentor(self):
        """Test creating Jidoka mentor."""
        mentor = create_jidoka_mentor()
        assert isinstance(mentor, JidokaMentor)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestTPSIntegration:
    """Integration tests for TPS system."""
    
    def test_full_pdca_with_waste_detection(self, tps_teacher, sample_process_data):
        """Test PDCA cycle with waste detection integration."""
        # 1. Start improvement cycle
        cycle = tps_teacher.start_improvement_cycle(
            title="Reduce Waiting Waste",
            problem="High idle time in assembly",
            owner="lean_manager",
            team=["team_lead", "operator_1"],
        )
        
        # 2. Analyze for waste in PLAN phase
        detections = tps_teacher.analyze_for_waste(sample_process_data)
        waiting_waste = [d for d in detections if d.muda_type == MudaType.WAITING]
        
        assert len(waiting_waste) > 0
        
        # 3. Get teaching prompts
        teaching = tps_teacher.get_daily_teaching(
            pdca_cycle_id=cycle["pdca_cycle_id"],
        )
        
        assert len(teaching["pdca_prompts"]) > 0
        assert teaching["waste_summary"]["total_detections"] > 0
    
    def test_jidoka_andon_workflow(self, tps_teacher):
        """Test Jidoka Andon workflow."""
        # 1. Trigger Andon (quality issue detected)
        event = tps_teacher.trigger_quality_stop(
            "machining_01",
            "Surface finish out of tolerance",
            "red",
        )
        
        # 2. Check active Andons appear in daily teaching
        teaching = tps_teacher.get_daily_teaching()
        assert len(teaching["active_andons"]) == 1
        
        # 3. Respond and resolve
        tps_teacher.jidoka_mentor.respond_to_andon(event.event_id, "operator_1")
        tps_teacher.jidoka_mentor.resolve_andon(
            event.event_id,
            "Tool wear",
            "Replaced cutting tool, added wear monitoring",
        )
        
        # 4. Check metrics
        metrics = tps_teacher.get_tps_metrics()
        assert metrics["jidoka"]["resolved"] == 1
    
    def test_kata_experiment_cycle(self, tps_teacher):
        """Test Kata experiment cycle."""
        # 1. Start improvement cycle
        cycle = tps_teacher.start_improvement_cycle(
            "Improve Setup Time",
            "Setup takes 60 minutes",
            "engineer",
            ["technician_1"],
        )
        
        kata_id = cycle["kata_session_id"]
        
        # 2. Set target condition
        tps_teacher.kata_assistant.set_target_condition(
            kata_id,
            "Setup time reduced to 30 minutes within 2 weeks",
        )
        
        # 3. Record obstacles
        tps_teacher.kata_assistant.record_obstacle(
            kata_id,
            "Tool changeover takes 20 minutes",
        )
        
        # 4. Record experiment
        tps_teacher.kata_assistant.record_experiment(
            kata_id,
            "Pre-stage tools before changeover",
            "Reduce tool changeover to 10 minutes",
            "Achieved 12 minute tool changeover",
        )
        
        # 5. Record learning
        tps_teacher.kata_assistant.record_learning(
            kata_id,
            "External setup activities can be done while machine is running",
        )
        
        # 6. Check summary
        summary = tps_teacher.kata_assistant.get_session_summary(kata_id)
        assert summary["obstacles_count"] == 1
        assert summary["experiments_count"] == 1
        assert summary["learnings_count"] == 1
    
    def test_comprehensive_tps_dashboard(self, tps_teacher, sample_process_data):
        """Test comprehensive TPS dashboard data."""
        # Create activity across all components
        tps_teacher.start_improvement_cycle("PDCA 1", "Problem 1", "owner", [])
        tps_teacher.start_improvement_cycle("PDCA 2", "Problem 2", "owner", [])
        tps_teacher.analyze_for_waste(sample_process_data)
        tps_teacher.trigger_quality_stop("s1", "Issue 1", "yellow")
        tps_teacher.trigger_quality_stop("s2", "Issue 2", "red")
        
        # Complete one cycle
        cycle_id = list(tps_teacher.pdca_engine.cycles.keys())[0]
        for _ in range(4):
            tps_teacher.pdca_engine.advance_phase(cycle_id)
        
        # Get comprehensive metrics
        metrics = tps_teacher.get_tps_metrics()
        
        # "active" counts all cycles in dict, "completed" counts those finished
        assert metrics["pdca_cycles"]["active"] == 2  # All cycles in dict
        assert metrics["pdca_cycles"]["completed"] == 1  # One completed
        assert metrics["kata_sessions"]["active"] == 2
        assert metrics["muda"]["total_detections"] > 0
        assert metrics["jidoka"]["total_events"] == 2
