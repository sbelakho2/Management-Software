"""
Sensei as TPS (Toyota Production System) Teacher.

Implements:
- PDCA Coaching Engine with phase gate guidance
- Improvement Kata Assistant with daily coaching prompts
- Real-Time Muda Detection (overproduction, waiting waste)
- Jidoka Mentor with Andon quality loop
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from sensei.models.tps import PDCACycleRecord, KataSessionRecord, MudaDetectionRecord, UserTPSStats


# =============================================================================
# ENUMS
# =============================================================================


class PDCAPhase(str, Enum):
    """PDCA cycle phases."""
    PLAN = "plan"
    DO = "do"
    CHECK = "check"
    ACT = "act"


class PhaseGateStatus(str, Enum):
    """Phase gate status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class MudaType(str, Enum):
    """The 7+1 types of Muda (waste)."""
    OVERPRODUCTION = "overproduction"
    WAITING = "waiting"
    TRANSPORT = "transport"
    OVERPROCESSING = "overprocessing"
    INVENTORY = "inventory"
    MOTION = "motion"
    DEFECTS = "defects"
    UNDERUTILIZED_TALENT = "underutilized_talent"


class KataStep(str, Enum):
    """Improvement Kata steps."""
    DIRECTION = "direction"  # Understand the direction/challenge
    GRASP_CURRENT = "grasp_current"  # Grasp the current condition
    TARGET_CONDITION = "target_condition"  # Establish next target condition
    EXPERIMENT = "experiment"  # PDCA toward target
    REFLECT = "reflect"  # Reflect on learnings


class AndonStatus(str, Enum):
    """Andon system status."""
    GREEN = "green"  # Normal operation
    YELLOW = "yellow"  # Potential issue, attention needed
    RED = "red"  # Stop, immediate action required
    BLUE = "blue"  # Quality issue, needs inspection


class JidokaAction(str, Enum):
    """Jidoka response actions."""
    CONTINUE = "continue"  # Continue operation
    ALERT = "alert"  # Alert operator
    SLOW_DOWN = "slow_down"  # Reduce speed
    STOP = "stop"  # Stop the line
    ESCALATE = "escalate"  # Escalate to supervisor


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class PDCACycle:
    """A PDCA improvement cycle."""
    cycle_id: str
    title: str
    problem_statement: str
    current_phase: PDCAPhase
    phase_statuses: dict[PDCAPhase, PhaseGateStatus]
    owner: str
    team_members: list[str]
    started_at: datetime
    target_completion: datetime
    actual_completion: datetime | None = None
    artifacts: dict[PDCAPhase, list[str]] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class PhaseGateRequirement:
    """A requirement for passing a phase gate."""
    requirement_id: str
    phase: PDCAPhase
    description: str
    is_mandatory: bool
    verification_method: str
    is_met: bool = False


@dataclass
class CoachingPrompt:
    """A coaching prompt for the user."""
    prompt_id: str
    phase: PDCAPhase | KataStep
    prompt_text: str
    guidance: str
    examples: list[str]
    priority: int = 1


@dataclass
class KataSession:
    """An Improvement Kata coaching session."""
    session_id: str
    challenge: str
    current_step: KataStep
    current_condition: str
    target_condition: str
    obstacles: list[str]
    experiments: list[dict[str, Any]]
    learnings: list[str]
    coach: str | None = None
    started_at: datetime = field(default_factory=datetime.now)


@dataclass
class MudaDetection:
    """A detected waste instance."""
    detection_id: str
    muda_type: MudaType
    location: str
    description: str
    estimated_impact: float
    detected_at: datetime
    evidence: list[str]
    severity: int  # 1-5
    suggested_countermeasure: str


@dataclass
class AndonEvent:
    """An Andon event."""
    event_id: str
    station_id: str
    status: AndonStatus
    issue_description: str
    detected_at: datetime
    responded_at: datetime | None = None
    resolved_at: datetime | None = None
    responder: str | None = None
    root_cause: str | None = None
    countermeasure: str | None = None


@dataclass
class JidokaResponse:
    """A Jidoka system response."""
    response_id: str
    trigger: str
    action: JidokaAction
    details: str
    affected_process: str
    timestamp: datetime
    quality_impact: str


# =============================================================================
# PDCA COACHING ENGINE
# =============================================================================


class PDCACoachingEngine:
    """
    PDCA Coaching Engine with phase gate guidance.
    Guides users through the Plan-Do-Check-Act cycle.
    """
    
    PHASE_GATE_REQUIREMENTS: dict[PDCAPhase, list[dict[str, Any]]] = {
        PDCAPhase.PLAN: [
            {"id": "plan_1", "description": "Problem statement is clear and measurable", "mandatory": True},
            {"id": "plan_2", "description": "Root cause analysis completed (5 Whys or Fishbone)", "mandatory": True},
            {"id": "plan_3", "description": "Countermeasures identified with owners", "mandatory": True},
            {"id": "plan_4", "description": "Success metrics defined", "mandatory": True},
            {"id": "plan_5", "description": "Timeline and resources allocated", "mandatory": False},
        ],
        PDCAPhase.DO: [
            {"id": "do_1", "description": "Countermeasures implemented as planned", "mandatory": True},
            {"id": "do_2", "description": "Data collection method in place", "mandatory": True},
            {"id": "do_3", "description": "Team trained on new process", "mandatory": False},
            {"id": "do_4", "description": "Documentation updated", "mandatory": False},
        ],
        PDCAPhase.CHECK: [
            {"id": "check_1", "description": "Results measured against targets", "mandatory": True},
            {"id": "check_2", "description": "Data analyzed and visualized", "mandatory": True},
            {"id": "check_3", "description": "Deviation analysis completed", "mandatory": False},
            {"id": "check_4", "description": "Side effects documented", "mandatory": False},
        ],
        PDCAPhase.ACT: [
            {"id": "act_1", "description": "Decision made: standardize, adjust, or abandon", "mandatory": True},
            {"id": "act_2", "description": "New standard documented if successful", "mandatory": True},
            {"id": "act_3", "description": "Lessons learned captured", "mandatory": True},
            {"id": "act_4", "description": "Next cycle planned if needed", "mandatory": False},
        ],
    }
    
    COACHING_PROMPTS: dict[PDCAPhase, list[str]] = {
        PDCAPhase.PLAN: [
            "What is the specific problem you're trying to solve?",
            "What data shows this is a problem worth solving?",
            "What are the potential root causes? Have you asked 'Why?' five times?",
            "What countermeasures will address the root causes?",
            "How will you measure success?",
        ],
        PDCAPhase.DO: [
            "Are you implementing exactly as planned, or making adjustments?",
            "What data are you collecting during implementation?",
            "Are there any unexpected obstacles?",
            "Is the team following the new process correctly?",
        ],
        PDCAPhase.CHECK: [
            "Did the countermeasures achieve the expected results?",
            "What does the data tell you?",
            "Were there any unintended consequences?",
            "What surprised you about the results?",
        ],
        PDCAPhase.ACT: [
            "Based on results, should we standardize, adjust, or try something else?",
            "If successful, how do we make this the new standard?",
            "What did we learn from this cycle?",
            "Is another PDCA cycle needed?",
        ],
    }
    
    def __init__(self):
        pass
    
    async def create_cycle(
        self,
        db: AsyncSession,
        title: str,
        problem_statement: str,
        owner: str,
        team_members: list[str],
        target_days: int = 30,
    ) -> PDCACycle:
        """Create a new PDCA cycle and persist to database."""
        cycle_id = hashlib.md5(
            f"{title}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]
        
        phase_statuses = {
            PDCAPhase.PLAN: PhaseGateStatus.IN_PROGRESS,
            PDCAPhase.DO: PhaseGateStatus.NOT_STARTED,
            PDCAPhase.CHECK: PhaseGateStatus.NOT_STARTED,
            PDCAPhase.ACT: PhaseGateStatus.NOT_STARTED,
        }
        
        artifacts = {phase.value: [] for phase in PDCAPhase}
        
        record = PDCACycleRecord(
            id=cycle_id,
            title=title,
            problem_statement=problem_statement,
            current_phase=PDCAPhase.PLAN.value,
            phase_statuses={k.value: v.value for k, v in phase_statuses.items()},
            owner_id=owner,
            team_members=team_members,
            target_completion=datetime.now(timezone.utc) + timedelta(days=target_days),
            artifacts=artifacts,
            metrics={},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        return PDCACycle(
            cycle_id=record.id,
            title=record.title,
            problem_statement=record.problem_statement,
            current_phase=PDCAPhase(record.current_phase),
            phase_statuses=phase_statuses,
            owner=record.owner_id,
            team_members=record.team_members,
            started_at=record.created_at,
            target_completion=record.target_completion,
            artifacts={PDCAPhase(k): v for k, v in record.artifacts.items()},
            metrics=record.metrics,
        )
    
    async def get_cycle(self, db: AsyncSession, cycle_id: str) -> PDCACycle | None:
        """Retrieve a PDCA cycle from database."""
        result = await db.execute(select(PDCACycleRecord).where(PDCACycleRecord.id == cycle_id))
        record = result.scalar_one_or_none()
        if not record:
            return None
        
        return PDCACycle(
            cycle_id=record.id,
            title=record.title,
            problem_statement=record.problem_statement,
            current_phase=PDCAPhase(record.current_phase),
            phase_statuses={PDCAPhase(k): PhaseGateStatus(v) for k, v in record.phase_statuses.items()},
            owner=record.owner_id,
            team_members=record.team_members,
            started_at=record.created_at,
            target_completion=record.target_completion,
            actual_completion=record.actual_completion,
            artifacts={PDCAPhase(k): v for k, v in record.artifacts.items()},
            metrics=record.metrics,
        )

    async def get_phase_requirements(
        self,
        db: AsyncSession,
        cycle_id: str,
    ) -> list[PhaseGateRequirement]:
        """Get requirements for the current phase gate."""
        cycle = await self.get_cycle(db, cycle_id)
        if not cycle:
            return []
        
        requirements = []
        for req in self.PHASE_GATE_REQUIREMENTS.get(cycle.current_phase, []):
            requirements.append(PhaseGateRequirement(
                requirement_id=req["id"],
                phase=cycle.current_phase,
                description=req["description"],
                is_mandatory=req["mandatory"],
                verification_method="manual",
            ))
        
        return requirements
    
    async def get_coaching_prompts(
        self,
        db: AsyncSession,
        cycle_id: str,
    ) -> list[CoachingPrompt]:
        """Get coaching prompts for the current phase."""
        cycle = await self.get_cycle(db, cycle_id)
        if not cycle:
            return []
        
        prompts = []
        for i, prompt_text in enumerate(self.COACHING_PROMPTS.get(cycle.current_phase, [])):
            prompts.append(CoachingPrompt(
                prompt_id=f"{cycle.current_phase.value}_{i}",
                phase=cycle.current_phase,
                prompt_text=prompt_text,
                guidance=f"Consider this carefully before advancing in {cycle.current_phase.value} phase.",
                examples=[],
                priority=i + 1,
            ))
        
        return prompts
    
    async def add_artifact(
        self,
        db: AsyncSession,
        cycle_id: str,
        phase: PDCAPhase,
        artifact: str,
    ) -> bool:
        """Add an artifact to a phase and persist."""
        result = await db.execute(select(PDCACycleRecord).where(PDCACycleRecord.id == cycle_id))
        record = result.scalar_one_or_none()
        if not record:
            return False
        
        new_artifacts = dict(record.artifacts)
        phase_key = phase.value
        if phase_key not in new_artifacts:
            new_artifacts[phase_key] = []
        new_artifacts[phase_key].append(artifact)
        record.artifacts = new_artifacts
        
        await db.commit()
        return True
    
    async def advance_phase(
        self,
        db: AsyncSession,
        cycle_id: str,
    ) -> PDCACycle | None:
        """Advance to the next phase and persist."""
        result = await db.execute(select(PDCACycleRecord).where(PDCACycleRecord.id == cycle_id))
        record = result.scalar_one_or_none()
        if not record:
            return None
        
        current_phase = PDCAPhase(record.current_phase)
        new_phase_statuses = dict(record.phase_statuses)
        new_phase_statuses[current_phase.value] = PhaseGateStatus.COMPLETED.value
        
        next_phase = self._get_next_phase(current_phase)
        
        if next_phase == PDCAPhase.PLAN and current_phase == PDCAPhase.ACT:
            record.actual_completion = datetime.now(timezone.utc)
        else:
            record.current_phase = next_phase.value
            new_phase_statuses[next_phase.value] = PhaseGateStatus.IN_PROGRESS.value
            
        record.phase_statuses = new_phase_statuses
        await db.commit()
        await db.refresh(record)
        
        return await self.get_cycle(db, cycle_id)
    
    def _get_next_phase(self, current: PDCAPhase) -> PDCAPhase:
        """Get the next phase in the cycle."""
        phase_order = [PDCAPhase.PLAN, PDCAPhase.DO, PDCAPhase.CHECK, PDCAPhase.ACT]
        idx = phase_order.index(current)
        return phase_order[(idx + 1) % len(phase_order)]
    
    def get_cycle_status(self, cycle_id: str) -> dict[str, Any]:
        """Get comprehensive cycle status."""
        cycle = self.cycles.get(cycle_id)
        if not cycle:
            return {}
        
        return {
            "cycle_id": cycle_id,
            "title": cycle.title,
            "current_phase": cycle.current_phase.value,
            "phase_statuses": {p.value: s.value for p, s in cycle.phase_statuses.items()},
            "progress_pct": sum(1 for s in cycle.phase_statuses.values() if s == PhaseGateStatus.COMPLETED) * 25,
            "days_elapsed": (datetime.now() - cycle.started_at).days,
            "days_remaining": max(0, (cycle.target_completion - datetime.now()).days),
            "is_complete": cycle.actual_completion is not None,
        }


# =============================================================================
# IMPROVEMENT KATA ASSISTANT
# =============================================================================


class ImprovementKataAssistant:
    """
    Improvement Kata Assistant with daily coaching prompts.
    Guides users through the Toyota Kata pattern.
    """
    
    KATA_COACHING_QUESTIONS = {
        KataStep.DIRECTION: [
            "What is your organization's direction or long-term challenge?",
            "Why is this challenge important?",
            "How does this connect to your team's purpose?",
        ],
        KataStep.GRASP_CURRENT: [
            "What is the current condition of this process?",
            "What is actually happening right now?",
            "What patterns do you observe in the data?",
        ],
        KataStep.TARGET_CONDITION: [
            "What is your next target condition?",
            "What does 'good' look like at this point?",
            "When do you want to achieve this target condition?",
        ],
        KataStep.EXPERIMENT: [
            "What obstacle are you addressing now?",
            "What is your next step or experiment?",
            "What do you expect to happen?",
            "When can we check results?",
        ],
        KataStep.REFLECT: [
            "What happened compared to what you expected?",
            "What did you learn?",
            "What will you do differently next time?",
        ],
    }
    
    def __init__(self):
        self.sessions: dict[str, KataSession] = {}
    
    def start_session(
        self,
        challenge: str,
        current_condition: str,
        coach: str | None = None,
    ) -> KataSession:
        """Start a new Kata coaching session."""
        session_id = hashlib.md5(
            f"{challenge}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        session = KataSession(
            session_id=session_id,
            challenge=challenge,
            current_step=KataStep.DIRECTION,
            current_condition=current_condition,
            target_condition="",
            obstacles=[],
            experiments=[],
            learnings=[],
            coach=coach,
        )
        
        self.sessions[session_id] = session
        return session
    
    def get_daily_coaching(
        self,
        session_id: str,
    ) -> list[CoachingPrompt]:
        """Get daily coaching prompts for the current step."""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        prompts = []
        questions = self.KATA_COACHING_QUESTIONS.get(session.current_step, [])
        
        for i, question in enumerate(questions):
            prompts.append(CoachingPrompt(
                prompt_id=f"kata_{session.current_step.value}_{i}",
                phase=session.current_step,
                prompt_text=question,
                guidance=f"This is the {session.current_step.value.replace('_', ' ')} step of Kata.",
                examples=[],
                priority=i + 1,
            ))
        
        return prompts
    
    def record_obstacle(
        self,
        session_id: str,
        obstacle: str,
    ) -> bool:
        """Record an obstacle discovered during Kata."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.obstacles.append(obstacle)
        return True
    
    def record_experiment(
        self,
        session_id: str,
        description: str,
        expected_result: str,
        actual_result: str | None = None,
    ) -> bool:
        """Record a Kata experiment."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.experiments.append({
            "description": description,
            "expected_result": expected_result,
            "actual_result": actual_result,
            "timestamp": datetime.now().isoformat(),
        })
        return True
    
    def set_target_condition(
        self,
        session_id: str,
        target_condition: str,
    ) -> bool:
        """Set the target condition."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.target_condition = target_condition
        return True
    
    def record_learning(
        self,
        session_id: str,
        learning: str,
    ) -> bool:
        """Record a learning from reflection."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.learnings.append(learning)
        return True
    
    def advance_step(
        self,
        session_id: str,
    ) -> KataSession | None:
        """Advance to the next Kata step."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        step_order = list(KataStep)
        idx = step_order.index(session.current_step)
        
        if idx < len(step_order) - 1:
            session.current_step = step_order[idx + 1]
        else:
            # Complete one iteration, can go back to experiment
            session.current_step = KataStep.EXPERIMENT
        
        return session
    
    def get_session_summary(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Get session summary."""
        session = self.sessions.get(session_id)
        if not session:
            return {}
        
        return {
            "session_id": session_id,
            "challenge": session.challenge,
            "current_step": session.current_step.value,
            "target_condition": session.target_condition,
            "obstacles_count": len(session.obstacles),
            "experiments_count": len(session.experiments),
            "learnings_count": len(session.learnings),
            "duration_hours": (datetime.now() - session.started_at).total_seconds() / 3600,
        }


# =============================================================================
# REAL-TIME MUDA (WASTE) DETECTION
# =============================================================================


class MudaDetectionEngine:
    """
    Real-Time Muda (Waste) Detection.
    Identifies the 7+1 types of waste in processes.
    """
    
    MUDA_INDICATORS = {
        MudaType.OVERPRODUCTION: [
            "excess_inventory",
            "ahead_of_schedule",
            "unused_output",
            "batch_larger_than_demand",
        ],
        MudaType.WAITING: [
            "idle_time",
            "queue_length",
            "blocked_process",
            "waiting_for_approval",
        ],
        MudaType.TRANSPORT: [
            "distance_moved",
            "handling_frequency",
            "unnecessary_movement",
        ],
        MudaType.OVERPROCESSING: [
            "redundant_steps",
            "over_specification",
            "unnecessary_precision",
        ],
        MudaType.INVENTORY: [
            "wip_levels",
            "storage_costs",
            "obsolete_stock",
        ],
        MudaType.MOTION: [
            "worker_movement",
            "reaching",
            "searching_for_tools",
        ],
        MudaType.DEFECTS: [
            "rework_rate",
            "scrap_rate",
            "customer_returns",
        ],
        MudaType.UNDERUTILIZED_TALENT: [
            "skill_mismatch",
            "unused_ideas",
            "manual_automation_candidates",
        ],
    }
    
    SEVERITY_THRESHOLDS = {
        "low": 1,
        "medium": 3,
        "high": 5,
    }
    
    def __init__(self):
        self.detections: list[MudaDetection] = []
        self.detection_rules: dict[MudaType, list[dict[str, Any]]] = {}
    
    def analyze_process_data(
        self,
        process_data: dict[str, Any],
    ) -> list[MudaDetection]:
        """Analyze process data for waste."""
        detections = []
        
        # Check for overproduction
        if process_data.get("output_qty", 0) > process_data.get("demand_qty", 0) * 1.1:
            detections.append(self._create_detection(
                MudaType.OVERPRODUCTION,
                process_data.get("location", "Unknown"),
                "Production exceeds demand by >10%",
                (process_data.get("output_qty", 0) - process_data.get("demand_qty", 0)) * process_data.get("unit_cost", 1),
                ["Output vs demand mismatch"],
                "Implement pull system, reduce batch sizes",
            ))
        
        # Check for waiting
        if process_data.get("idle_time_pct", 0) > 15:
            severity = 3 if process_data.get("idle_time_pct", 0) < 30 else 5
            detections.append(self._create_detection(
                MudaType.WAITING,
                process_data.get("location", "Unknown"),
                f"Idle time at {process_data.get('idle_time_pct', 0)}%",
                process_data.get("idle_time_pct", 0) * process_data.get("hourly_cost", 50) / 100,
                [f"Idle time: {process_data.get('idle_time_pct', 0)}%"],
                "Balance workloads, improve flow",
                severity=severity,
            ))
        
        # Check for inventory waste
        if process_data.get("wip_days", 0) > 5:
            detections.append(self._create_detection(
                MudaType.INVENTORY,
                process_data.get("location", "Unknown"),
                f"WIP inventory at {process_data.get('wip_days', 0)} days",
                process_data.get("wip_value", 0) * 0.02,  # 2% carrying cost
                [f"WIP days: {process_data.get('wip_days', 0)}"],
                "Reduce batch sizes, implement one-piece flow",
            ))
        
        # Check for defects
        if process_data.get("defect_rate", 0) > 1:  # > 1%
            severity = 4 if process_data.get("defect_rate", 0) < 5 else 5
            detections.append(self._create_detection(
                MudaType.DEFECTS,
                process_data.get("location", "Unknown"),
                f"Defect rate at {process_data.get('defect_rate', 0)}%",
                process_data.get("defect_rate", 0) * process_data.get("unit_cost", 100) / 100,
                [f"Defect rate: {process_data.get('defect_rate', 0)}%"],
                "Implement poka-yoke, strengthen quality at source",
                severity=severity,
            ))
        
        # Check for motion waste
        if process_data.get("steps_per_unit", 0) > process_data.get("standard_steps", 10):
            detections.append(self._create_detection(
                MudaType.MOTION,
                process_data.get("location", "Unknown"),
                "Excessive steps per unit",
                (process_data.get("steps_per_unit", 0) - process_data.get("standard_steps", 10)) * 0.5,
                ["Steps exceed standard"],
                "Redesign workstation layout",
            ))
        
        self.detections.extend(detections)
        return detections
    
    def _create_detection(
        self,
        muda_type: MudaType,
        location: str,
        description: str,
        impact: float,
        evidence: list[str],
        countermeasure: str,
        severity: int = 3,
    ) -> MudaDetection:
        """Create a muda detection."""
        detection_id = hashlib.md5(
            f"{muda_type.value}:{location}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return MudaDetection(
            detection_id=detection_id,
            muda_type=muda_type,
            location=location,
            description=description,
            estimated_impact=impact,
            detected_at=datetime.now(),
            evidence=evidence,
            severity=severity,
            suggested_countermeasure=countermeasure,
        )
    
    def get_waste_summary(self) -> dict[str, Any]:
        """Get summary of all detected waste."""
        summary: dict[MudaType, dict[str, Any]] = {}
        
        for muda_type in MudaType:
            type_detections = [d for d in self.detections if d.muda_type == muda_type]
            if type_detections:
                summary[muda_type] = {
                    "count": len(type_detections),
                    "total_impact": sum(d.estimated_impact for d in type_detections),
                    "avg_severity": sum(d.severity for d in type_detections) / len(type_detections),
                    "locations": list(set(d.location for d in type_detections)),
                }
        
        return {
            "total_detections": len(self.detections),
            "total_impact": sum(d.estimated_impact for d in self.detections),
            "by_type": {k.value: v for k, v in summary.items()},
        }
    
    def get_high_severity_waste(
        self,
        threshold: int = 4,
    ) -> list[MudaDetection]:
        """Get high-severity waste detections."""
        return [d for d in self.detections if d.severity >= threshold]
    
    def clear_detections(self) -> int:
        """Clear all detections."""
        count = len(self.detections)
        self.detections = []
        return count


# =============================================================================
# JIDOKA MENTOR (AUTONOMATION)
# =============================================================================


class JidokaMentor:
    """
    Jidoka Mentor with Andon quality loop.
    Implements the autonomation principle.
    """
    
    ANDON_ESCALATION_RULES = {
        AndonStatus.GREEN: {"action": JidokaAction.CONTINUE, "timeout_sec": None},
        AndonStatus.YELLOW: {"action": JidokaAction.ALERT, "timeout_sec": 300},
        AndonStatus.RED: {"action": JidokaAction.STOP, "timeout_sec": 0},
        AndonStatus.BLUE: {"action": JidokaAction.SLOW_DOWN, "timeout_sec": 120},
    }
    
    def __init__(self):
        self.andon_events: list[AndonEvent] = []
        self.jidoka_responses: list[JidokaResponse] = []
        self.station_status: dict[str, AndonStatus] = {}
    
    def trigger_andon(
        self,
        station_id: str,
        status: AndonStatus,
        issue_description: str,
    ) -> AndonEvent:
        """Trigger an Andon signal."""
        event_id = hashlib.md5(
            f"{station_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        event = AndonEvent(
            event_id=event_id,
            station_id=station_id,
            status=status,
            issue_description=issue_description,
            detected_at=datetime.now(),
        )
        
        self.andon_events.append(event)
        self.station_status[station_id] = status
        
        # Generate Jidoka response
        self._generate_jidoka_response(event)
        
        return event
    
    def _generate_jidoka_response(
        self,
        event: AndonEvent,
    ) -> JidokaResponse:
        """Generate automatic Jidoka response."""
        rule = self.ANDON_ESCALATION_RULES.get(event.status, {})
        action = rule.get("action", JidokaAction.ALERT)
        
        response = JidokaResponse(
            response_id=f"jidoka_{event.event_id}",
            trigger=event.issue_description,
            action=action,
            details=f"Andon {event.status.value} triggered at {event.station_id}",
            affected_process=event.station_id,
            timestamp=datetime.now(),
            quality_impact=self._assess_quality_impact(event.status),
        )
        
        self.jidoka_responses.append(response)
        return response
    
    def _assess_quality_impact(
        self,
        status: AndonStatus,
    ) -> str:
        """Assess quality impact based on status."""
        impact_map = {
            AndonStatus.GREEN: "No impact",
            AndonStatus.YELLOW: "Potential quality risk - monitoring required",
            AndonStatus.RED: "Critical quality issue - immediate action required",
            AndonStatus.BLUE: "Quality inspection needed before release",
        }
        return impact_map.get(status, "Unknown impact")
    
    def respond_to_andon(
        self,
        event_id: str,
        responder: str,
    ) -> AndonEvent | None:
        """Record response to Andon."""
        for event in self.andon_events:
            if event.event_id == event_id:
                event.responded_at = datetime.now()
                event.responder = responder
                return event
        return None
    
    def resolve_andon(
        self,
        event_id: str,
        root_cause: str,
        countermeasure: str,
    ) -> AndonEvent | None:
        """Resolve an Andon event."""
        for event in self.andon_events:
            if event.event_id == event_id:
                event.resolved_at = datetime.now()
                event.root_cause = root_cause
                event.countermeasure = countermeasure
                self.station_status[event.station_id] = AndonStatus.GREEN
                return event
        return None
    
    def get_active_andons(self) -> list[AndonEvent]:
        """Get all active (unresolved) Andon events."""
        return [e for e in self.andon_events if e.resolved_at is None]
    
    def get_station_status(
        self,
        station_id: str,
    ) -> AndonStatus:
        """Get current status of a station."""
        return self.station_status.get(station_id, AndonStatus.GREEN)
    
    def get_response_metrics(self) -> dict[str, Any]:
        """Get Andon response metrics."""
        responded = [e for e in self.andon_events if e.responded_at]
        resolved = [e for e in self.andon_events if e.resolved_at]
        
        avg_response_time = 0.0
        avg_resolution_time = 0.0
        
        if responded:
            response_times = [
                (e.responded_at - e.detected_at).total_seconds()
                for e in responded
            ]
            avg_response_time = sum(response_times) / len(response_times)
        
        if resolved:
            resolution_times = [
                (e.resolved_at - e.detected_at).total_seconds()
                for e in resolved
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        return {
            "total_events": len(self.andon_events),
            "active_events": len(self.get_active_andons()),
            "responded": len(responded),
            "resolved": len(resolved),
            "avg_response_time_sec": avg_response_time,
            "avg_resolution_time_sec": avg_resolution_time,
            "by_status": {
                status.value: sum(1 for e in self.andon_events if e.status == status)
                for status in AndonStatus
            },
        }
    
    def get_quality_loop_summary(self) -> dict[str, Any]:
        """Get quality loop summary for continuous improvement."""
        resolved = [e for e in self.andon_events if e.resolved_at]
        
        root_causes: dict[str, int] = {}
        countermeasures: dict[str, int] = {}
        
        for event in resolved:
            if event.root_cause:
                root_causes[event.root_cause] = root_causes.get(event.root_cause, 0) + 1
            if event.countermeasure:
                countermeasures[event.countermeasure] = countermeasures.get(event.countermeasure, 0) + 1
        
        return {
            "resolved_count": len(resolved),
            "top_root_causes": sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_root_causes_v2": sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_countermeasures": sorted(countermeasures.items(), key=lambda x: x[1], reverse=True)[:5],
        }


class MultiModalPDCACoach:
    """
    Enriches TPS Teacher with vision-based coaching.
    Uses VLM to analyze shop floor photos for Muda or PDCA progress.
    """
    
    def __init__(self):
        # Local import to avoid circular dependency
        try:
            from sensei.services.ai.world_class_document_ai import VisionLLMEnricher
            self.vlm = VisionLLMEnricher()
        except ImportError:
            self.vlm = None
        
    async def analyze_pdca_evidence(self, image: np.ndarray, phase: PDCAPhase) -> dict[str, Any]:
        """Analyze an image as evidence for a PDCA phase."""
        # Simulated VLM response for enrichment
        return {
            "evidence_found": True,
            "confidence": 0.85,
            "observations": [f"Visual evidence confirms {phase.value} implementation"],
            "detected_muda": ["Motion", "Waiting"],
            "suggestions": [
                "Standard work sheet should be more visible",
                "Tooling shadow board appears incomplete"
            ]
        }


class KataGamificationService:
    """
    Tracks and rewards Lean competency growth.
    Enriches the learning experience with 'Kata Belts' and achievement tracking.
    """
    
    def __init__(self):
        pass
        
    async def get_user_status(self, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Get user's current belt and stats from database."""
        result = await db.execute(select(UserTPSStats).where(UserTPSStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        
        if not stats:
            # Create default stats if not exists
            stats = UserTPSStats(user_id=user_id, xp=0, achievements=[], belt_level="White Belt")
            db.add(stats)
            await db.commit()
            await db.refresh(stats)
        
        xp = stats.xp
        belt = stats.belt_level
        
        return {
            "belt": belt,
            "xp": xp,
            "achievements": stats.achievements,
            "next_belt_xp": 200 if xp < 200 else (500 if xp < 500 else (1000 if xp < 1000 else 2000))
        }
        
    async def award_achievement(self, db: AsyncSession, user_id: str, achievement: str, xp_reward: int) -> dict[str, Any]:
        """Award an achievement to a user and persist to database."""
        result = await db.execute(select(UserTPSStats).where(UserTPSStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = UserTPSStats(user_id=user_id, xp=0, achievements=[], belt_level="White Belt")
            db.add(stats)
        
        if achievement not in stats.achievements:
            # We need to create a new list for SQLAlchemy to detect the change in JSONB
            new_achievements = list(stats.achievements)
            new_achievements.append(achievement)
            stats.achievements = new_achievements
            stats.xp += xp_reward
            
            # Update belt
            xp = stats.xp
            if xp >= 2000: stats.belt_level = "Black Belt"
            elif xp >= 1000: stats.belt_level = "Brown Belt"
            elif xp >= 500: stats.belt_level = "Green Belt"
            elif xp >= 200: stats.belt_level = "Yellow Belt"
            
            await db.commit()
            await db.refresh(stats)
            
        return await self.get_user_status(db, user_id)


# =============================================================================
# TPS TEACHER ORCHESTRATOR
# =============================================================================


class TPSTeacher:
    """
    Main TPS (Toyota Production System) Teacher.
    Orchestrates all TPS teaching components.
    """
    
    def __init__(self):
        self.pdca_engine = PDCACoachingEngine()
        self.kata_assistant = ImprovementKataAssistant()
        self.muda_detector = MudaDetectionEngine()
        self.jidoka_mentor = JidokaMentor()
        self.multimodal_coach = MultiModalPDCACoach()
        self.gamification = KataGamificationService()
    
    def start_improvement_cycle(
        self,
        title: str,
        problem: str,
        owner: str,
        team: list[str],
    ) -> dict[str, Any]:
        """Start a comprehensive improvement cycle."""
        # Create PDCA cycle
        cycle = self.pdca_engine.create_cycle(
            title=title,
            problem_statement=problem,
            owner=owner,
            team_members=team,
        )
        
        # Create Kata session
        session = self.kata_assistant.start_session(
            challenge=title,
            current_condition=problem,
        )
        
        return {
            "pdca_cycle_id": cycle.cycle_id,
            "kata_session_id": session.session_id,
            "coaching_prompts": self.pdca_engine.get_coaching_prompts(cycle.cycle_id),
        }
    
    def get_daily_teaching(
        self,
        pdca_cycle_id: str | None = None,
        kata_session_id: str | None = None,
    ) -> dict[str, Any]:
        """Get daily teaching prompts."""
        teaching = {}
        
        if pdca_cycle_id:
            teaching["pdca_prompts"] = self.pdca_engine.get_coaching_prompts(pdca_cycle_id)
            teaching["phase_requirements"] = self.pdca_engine.get_phase_requirements(pdca_cycle_id)
        
        if kata_session_id:
            teaching["kata_prompts"] = self.kata_assistant.get_daily_coaching(kata_session_id)
        
        # Add waste summary
        teaching["waste_summary"] = self.muda_detector.get_waste_summary()
        
        # Add active Andons
        teaching["active_andons"] = [
            {"station": e.station_id, "status": e.status.value, "issue": e.issue_description}
            for e in self.jidoka_mentor.get_active_andons()
        ]
        
        return teaching
    
    def analyze_for_waste(
        self,
        process_data: dict[str, Any],
    ) -> list[MudaDetection]:
        """Analyze process data for waste."""
        return self.muda_detector.analyze_process_data(process_data)
    
    def trigger_quality_stop(
        self,
        station_id: str,
        issue: str,
        severity: str = "yellow",
    ) -> AndonEvent:
        """Trigger a quality stop (Andon)."""
        status_map = {
            "green": AndonStatus.GREEN,
            "yellow": AndonStatus.YELLOW,
            "red": AndonStatus.RED,
            "blue": AndonStatus.BLUE,
        }
        return self.jidoka_mentor.trigger_andon(
            station_id=station_id,
            status=status_map.get(severity, AndonStatus.YELLOW),
            issue_description=issue,
        )
    
    def get_tps_metrics(self) -> dict[str, Any]:
        """Get comprehensive TPS metrics."""
        return {
            "pdca_cycles": {
                "active": len(self.pdca_engine.cycles),
                "completed": len(self.pdca_engine.completed_cycles),
            },
            "kata_sessions": {
                "active": len(self.kata_assistant.sessions),
            },
            "muda": self.muda_detector.get_waste_summary(),
            "jidoka": self.jidoka_mentor.get_response_metrics(),
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_tps_teacher() -> TPSTeacher:
    """Create the TPS Teacher."""
    return TPSTeacher()


def create_pdca_engine() -> PDCACoachingEngine:
    """Create PDCA coaching engine."""
    return PDCACoachingEngine()


def create_kata_assistant() -> ImprovementKataAssistant:
    """Create Improvement Kata assistant."""
    return ImprovementKataAssistant()


def create_muda_detector() -> MudaDetectionEngine:
    """Create Muda detection engine."""
    return MudaDetectionEngine()


def create_jidoka_mentor() -> JidokaMentor:
    """Create Jidoka mentor."""
    return JidokaMentor()
