"""
GM Onboarding Service

Provides Day-1 onboarding functionality for new GM users,
including setup wizards, progress tracking, and guided tours.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4


class OnboardingStatus(str, Enum):
    """Status of onboarding process."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class OnboardingStepType(str, Enum):
    """Types of onboarding steps."""
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    TEAM_INTRO = "team_intro"
    DASHBOARD_TOUR = "dashboard_tour"
    KEY_METRICS = "key_metrics"
    WORKFLOW_OVERVIEW = "workflow_overview"
    TOOL_TRAINING = "tool_training"
    FIRST_ACTIONS = "first_actions"
    COMPLETION = "completion"


@dataclass
class OnboardingStep:
    """Represents a single onboarding step."""
    id: str
    step_type: OnboardingStepType
    title: str
    description: str
    order: int
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    required: bool = True
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if step is complete."""
        return self.status == OnboardingStatus.COMPLETED
    
    @property
    def can_skip(self) -> bool:
        """Check if step can be skipped."""
        return not self.required


@dataclass
class OnboardingChecklistItem:
    """A checklist item within an onboarding step."""
    id: str
    title: str
    description: str
    completed: bool = False
    completed_at: Optional[datetime] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None


@dataclass
class OnboardingProgress:
    """Tracks overall onboarding progress."""
    user_id: str
    user_name: str
    role: str
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    steps: list[OnboardingStep] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    completion_percentage: float = 0.0
    estimated_remaining_minutes: int = 0
    
    @property
    def current_step_index(self) -> int:
        """Get index of current step."""
        for i, step in enumerate(self.steps):
            if step.status in (OnboardingStatus.NOT_STARTED, OnboardingStatus.IN_PROGRESS):
                return i
        return len(self.steps) - 1
    
    @property
    def current_step(self) -> Optional[OnboardingStep]:
        """Get current step."""
        idx = self.current_step_index
        if 0 <= idx < len(self.steps):
            return self.steps[idx]
        return None
    
    @property
    def completed_steps(self) -> list[OnboardingStep]:
        """Get completed steps."""
        return [s for s in self.steps if s.is_complete]
    
    @property
    def remaining_steps(self) -> list[OnboardingStep]:
        """Get remaining steps."""
        return [s for s in self.steps if not s.is_complete]


@dataclass
class GMDashboardTourSpot:
    """A tour spot in the GM dashboard tour."""
    id: str
    element_selector: str
    title: str
    description: str
    order: int
    position: str = "bottom"  # top, bottom, left, right
    highlight: bool = True
    action: Optional[str] = None
    action_label: Optional[str] = None


@dataclass
class GMKeyMetric:
    """A key metric for GM onboarding."""
    id: str
    name: str
    description: str
    current_value: Any
    target_value: Optional[Any] = None
    unit: str = ""
    trend: str = "stable"  # up, down, stable
    importance: str = "high"  # high, medium, low


@dataclass
class GMFirstAction:
    """A first action for new GM."""
    id: str
    title: str
    description: str
    priority: int
    completed: bool = False
    url: str = ""
    icon: str = ""
    category: str = "general"
    estimated_minutes: int = 5


class GMOnboardingService:
    """
    Manages GM onboarding process.
    
    Provides:
    - Onboarding step management
    - Progress tracking
    - Dashboard tour
    - Key metrics introduction
    - First action recommendations
    """
    
    def __init__(self):
        self._user_progress: dict[str, OnboardingProgress] = {}
        self._step_templates: list[OnboardingStep] = self._create_step_templates()
        self._tour_spots: list[GMDashboardTourSpot] = self._create_tour_spots()
        self._listeners: list[Callable[[OnboardingProgress], None]] = []
    
    def _create_step_templates(self) -> list[OnboardingStep]:
        """Create default onboarding step templates."""
        return [
            OnboardingStep(
                id="welcome",
                step_type=OnboardingStepType.WELCOME,
                title="Welcome to Sensei OS",
                description="Get started with your new management platform",
                order=1,
                required=True,
            ),
            OnboardingStep(
                id="profile_setup",
                step_type=OnboardingStepType.PROFILE_SETUP,
                title="Complete Your Profile",
                description="Set up your profile, preferences, and notification settings",
                order=2,
                required=True,
            ),
            OnboardingStep(
                id="team_intro",
                step_type=OnboardingStepType.TEAM_INTRO,
                title="Meet Your Team",
                description="Review your team structure and key contacts",
                order=3,
                required=False,
            ),
            OnboardingStep(
                id="dashboard_tour",
                step_type=OnboardingStepType.DASHBOARD_TOUR,
                title="Dashboard Tour",
                description="Explore the main dashboard and navigation",
                order=4,
                required=True,
            ),
            OnboardingStep(
                id="key_metrics",
                step_type=OnboardingStepType.KEY_METRICS,
                title="Key Metrics Overview",
                description="Understand the metrics that matter for your role",
                order=5,
                required=True,
            ),
            OnboardingStep(
                id="workflow_overview",
                step_type=OnboardingStepType.WORKFLOW_OVERVIEW,
                title="Daily Workflow",
                description="Learn about your daily workflow and routines",
                order=6,
                required=True,
            ),
            OnboardingStep(
                id="tool_training",
                step_type=OnboardingStepType.TOOL_TRAINING,
                title="Tool Training",
                description="Quick training on essential tools and features",
                order=7,
                required=False,
            ),
            OnboardingStep(
                id="first_actions",
                step_type=OnboardingStepType.FIRST_ACTIONS,
                title="First Actions",
                description="Complete your first set of tasks to get started",
                order=8,
                required=True,
            ),
            OnboardingStep(
                id="completion",
                step_type=OnboardingStepType.COMPLETION,
                title="You're Ready!",
                description="Onboarding complete - start managing your operations",
                order=9,
                required=True,
            ),
        ]
    
    def _create_tour_spots(self) -> list[GMDashboardTourSpot]:
        """Create dashboard tour spots."""
        return [
            GMDashboardTourSpot(
                id="sidebar_nav",
                element_selector="[data-testid='sidebar-navigation']",
                title="Main Navigation",
                description="Access all modules from here: Today, Approvals, RFQs, Quotes, Quality, and more.",
                order=1,
                position="right",
            ),
            GMDashboardTourSpot(
                id="today_screen",
                element_selector="[data-testid='nav-today']",
                title="Today Screen",
                description="Your daily command center. See priorities, risks, and commitments at a glance.",
                order=2,
                position="right",
                action="/today",
                action_label="Go to Today",
            ),
            GMDashboardTourSpot(
                id="approvals",
                element_selector="[data-testid='nav-approvals']",
                title="Approvals Queue",
                description="Review and approve items requiring your attention. Aim for < 60 second decisions.",
                order=3,
                position="right",
                action="/approvals",
                action_label="View Approvals",
            ),
            GMDashboardTourSpot(
                id="exceptions",
                element_selector="[data-testid='nav-exceptions']",
                title="Exceptions Dashboard",
                description="All red/warning items across the system. Prioritized by urgency.",
                order=4,
                position="right",
                action="/exceptions",
                action_label="View Exceptions",
            ),
            GMDashboardTourSpot(
                id="quick_actions",
                element_selector="[data-testid='quick-actions']",
                title="Quick Actions",
                description="Frequently used actions are just one click away.",
                order=5,
                position="bottom",
            ),
            GMDashboardTourSpot(
                id="search",
                element_selector="[data-testid='global-search']",
                title="Global Search",
                description="Search anything: RFQs, quotes, customers, parts. AI-powered suggestions.",
                order=6,
                position="bottom",
            ),
            GMDashboardTourSpot(
                id="notifications",
                element_selector="[data-testid='notifications-bell']",
                title="Notifications",
                description="Real-time alerts for approvals, escalations, and important updates.",
                order=7,
                position="left",
            ),
            GMDashboardTourSpot(
                id="user_menu",
                element_selector="[data-testid='user-menu']",
                title="Your Profile",
                description="Access settings, preferences, and sign out.",
                order=8,
                position="left",
            ),
        ]
    
    def start_onboarding(
        self,
        user_id: str,
        user_name: str,
        role: str = "GM",
    ) -> OnboardingProgress:
        """Start onboarding for a new user."""
        # Create steps from templates
        steps = [
            OnboardingStep(
                id=t.id,
                step_type=t.step_type,
                title=t.title,
                description=t.description,
                order=t.order,
                required=t.required,
            )
            for t in self._step_templates
        ]
        
        # Estimate remaining time (5 minutes per required step)
        required_steps = [s for s in steps if s.required]
        estimated_minutes = len(required_steps) * 5
        
        progress = OnboardingProgress(
            user_id=user_id,
            user_name=user_name,
            role=role,
            status=OnboardingStatus.IN_PROGRESS,
            steps=steps,
            started_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            estimated_remaining_minutes=estimated_minutes,
        )
        
        self._user_progress[user_id] = progress
        self._notify_listeners(progress)
        
        return progress
    
    def get_progress(self, user_id: str) -> Optional[OnboardingProgress]:
        """Get onboarding progress for a user."""
        return self._user_progress.get(user_id)
    
    def start_step(self, user_id: str, step_id: str) -> Optional[OnboardingStep]:
        """Start a specific onboarding step."""
        progress = self._user_progress.get(user_id)
        if not progress:
            return None
        
        for step in progress.steps:
            if step.id == step_id:
                step.status = OnboardingStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc)
                
                progress.last_activity = datetime.now(timezone.utc)
                self._update_completion(progress)
                self._notify_listeners(progress)
                
                return step
        return None
    
    def complete_step(
        self,
        user_id: str,
        step_id: str,
        data: Optional[dict[str, Any]] = None,
    ) -> Optional[OnboardingStep]:
        """Mark a step as completed."""
        progress = self._user_progress.get(user_id)
        if not progress:
            return None
        
        for step in progress.steps:
            if step.id == step_id:
                now = datetime.now(timezone.utc)
                step.status = OnboardingStatus.COMPLETED
                step.completed_at = now
                
                if step.started_at:
                    step.time_spent_seconds = int(
                        (now - step.started_at).total_seconds()
                    )
                
                if data:
                    step.data = data
                
                progress.last_activity = now
                self._update_completion(progress)
                
                # Check if all steps are complete
                all_required_complete = all(
                    s.is_complete for s in progress.steps if s.required
                )
                if all_required_complete:
                    progress.status = OnboardingStatus.COMPLETED
                    progress.completed_at = now
                
                self._notify_listeners(progress)
                return step
        return None
    
    def skip_step(self, user_id: str, step_id: str) -> Optional[OnboardingStep]:
        """Skip a non-required step."""
        progress = self._user_progress.get(user_id)
        if not progress:
            return None
        
        for step in progress.steps:
            if step.id == step_id:
                if step.required:
                    return None  # Cannot skip required steps
                
                step.status = OnboardingStatus.SKIPPED
                step.completed_at = datetime.now(timezone.utc)
                
                progress.last_activity = datetime.now(timezone.utc)
                self._update_completion(progress)
                self._notify_listeners(progress)
                
                return step
        return None
    
    def _update_completion(self, progress: OnboardingProgress) -> None:
        """Update completion percentage and remaining time."""
        total_steps = len(progress.steps)
        completed = len([s for s in progress.steps if s.is_complete])
        skipped = len([s for s in progress.steps if s.status == OnboardingStatus.SKIPPED])
        
        if total_steps > 0:
            progress.completion_percentage = (completed + skipped) / total_steps * 100
        
        remaining = len([
            s for s in progress.steps 
            if s.required and not s.is_complete
        ])
        progress.estimated_remaining_minutes = remaining * 5
    
    def get_dashboard_tour(self) -> list[GMDashboardTourSpot]:
        """Get dashboard tour spots."""
        return sorted(self._tour_spots, key=lambda s: s.order)
    
    def get_key_metrics(self, user_id: str) -> list[GMKeyMetric]:
        """Get key metrics for GM onboarding."""
        # In production, these would be fetched from actual data
        return [
            GMKeyMetric(
                id="open_rfqs",
                name="Open RFQs",
                description="RFQs awaiting response or action",
                current_value=12,
                target_value=None,
                unit="",
                importance="high",
            ),
            GMKeyMetric(
                id="pending_approvals",
                name="Pending Approvals",
                description="Items waiting for your approval",
                current_value=5,
                target_value=0,
                unit="",
                importance="high",
            ),
            GMKeyMetric(
                id="active_quotes",
                name="Active Quotes",
                description="Quotes in progress or pending",
                current_value=28,
                target_value=None,
                unit="",
                importance="medium",
            ),
            GMKeyMetric(
                id="win_rate",
                name="Quote Win Rate",
                description="Percentage of quotes won this month",
                current_value=67.5,
                target_value=70.0,
                unit="%",
                trend="up",
                importance="high",
            ),
            GMKeyMetric(
                id="oee",
                name="OEE",
                description="Overall Equipment Effectiveness",
                current_value=82.3,
                target_value=85.0,
                unit="%",
                trend="stable",
                importance="high",
            ),
            GMKeyMetric(
                id="open_a3s",
                name="Open A3 Reports",
                description="Active problem-solving initiatives",
                current_value=3,
                target_value=None,
                unit="",
                importance="medium",
            ),
            GMKeyMetric(
                id="andon_open",
                name="Open Andons",
                description="Unresolved production issues",
                current_value=1,
                target_value=0,
                unit="",
                importance="high",
            ),
            GMKeyMetric(
                id="training_compliance",
                name="Training Compliance",
                description="Team training certification rate",
                current_value=94.2,
                target_value=100.0,
                unit="%",
                trend="up",
                importance="medium",
            ),
        ]
    
    def get_first_actions(self, user_id: str) -> list[GMFirstAction]:
        """Get recommended first actions for new GM."""
        return [
            GMFirstAction(
                id="review_today",
                title="Review Today Screen",
                description="Check your priorities, risks, and commitments for today",
                priority=1,
                url="/today",
                icon="calendar",
                category="daily",
                estimated_minutes=5,
            ),
            GMFirstAction(
                id="clear_approvals",
                title="Clear Pending Approvals",
                description="Process any items waiting for your approval",
                priority=2,
                url="/approvals",
                icon="check-circle",
                category="approvals",
                estimated_minutes=10,
            ),
            GMFirstAction(
                id="review_exceptions",
                title="Review Exceptions",
                description="Check for any critical or overdue items needing attention",
                priority=3,
                url="/exceptions",
                icon="alert-triangle",
                category="exceptions",
                estimated_minutes=5,
            ),
            GMFirstAction(
                id="meet_team",
                title="Review Team Structure",
                description="Familiarize yourself with your team and their roles",
                priority=4,
                url="/team",
                icon="users",
                category="team",
                estimated_minutes=10,
            ),
            GMFirstAction(
                id="check_open_rfqs",
                title="Review Open RFQs",
                description="See what customer requests are in progress",
                priority=5,
                url="/rfqs",
                icon="file-text",
                category="sales",
                estimated_minutes=10,
            ),
            GMFirstAction(
                id="production_overview",
                title="Check Production Status",
                description="Review current work orders and production metrics",
                priority=6,
                url="/production",
                icon="factory",
                category="production",
                estimated_minutes=5,
            ),
            GMFirstAction(
                id="quality_status",
                title="Quality Dashboard",
                description="Review quality metrics and any open NCRs",
                priority=7,
                url="/quality",
                icon="shield-check",
                category="quality",
                estimated_minutes=5,
            ),
            GMFirstAction(
                id="set_preferences",
                title="Set Your Preferences",
                description="Configure notifications and display preferences",
                priority=8,
                url="/settings",
                icon="settings",
                category="setup",
                estimated_minutes=5,
            ),
        ]
    
    def complete_first_action(
        self,
        user_id: str,
        action_id: str,
    ) -> Optional[GMFirstAction]:
        """Mark a first action as completed."""
        progress = self._user_progress.get(user_id)
        if not progress:
            return None
        
        # Track in step data
        first_actions_step = None
        for step in progress.steps:
            if step.step_type == OnboardingStepType.FIRST_ACTIONS:
                first_actions_step = step
                break
        
        if first_actions_step:
            if "completed_actions" not in first_actions_step.data:
                first_actions_step.data["completed_actions"] = []
            first_actions_step.data["completed_actions"].append(action_id)
            
            progress.last_activity = datetime.now(timezone.utc)
            self._notify_listeners(progress)
        
        # Return the action with updated status
        actions = self.get_first_actions(user_id)
        for action in actions:
            if action.id == action_id:
                action.completed = True
                return action
        return None
    
    def get_workflow_checklist(self) -> list[OnboardingChecklistItem]:
        """Get daily workflow checklist for GM."""
        return [
            OnboardingChecklistItem(
                id="check_today",
                title="Review Today Screen",
                description="Start each day by checking your priorities and risks",
                action_url="/today",
                action_label="Go to Today",
            ),
            OnboardingChecklistItem(
                id="process_approvals",
                title="Process Pending Approvals",
                description="Clear your approval queue (target: < 60s per item)",
                action_url="/approvals",
                action_label="View Approvals",
            ),
            OnboardingChecklistItem(
                id="check_exceptions",
                title="Review Critical Exceptions",
                description="Address any critical or escalated items",
                action_url="/exceptions",
                action_label="View Exceptions",
            ),
            OnboardingChecklistItem(
                id="review_metrics",
                title="Review Key Metrics",
                description="Check OEE, win rate, and other KPIs",
                action_url="/analytics",
                action_label="View Analytics",
            ),
            OnboardingChecklistItem(
                id="team_standup",
                title="Team Standup/Check-in",
                description="Brief sync with team leads on blockers",
                action_url="/obeya",
                action_label="View Obeya",
            ),
            OnboardingChecklistItem(
                id="export_snapshot",
                title="Export Daily Snapshot",
                description="Save end-of-day status report",
                action_url="/reports/daily",
                action_label="Generate Report",
            ),
        ]
    
    def add_listener(
        self,
        listener: Callable[[OnboardingProgress], None],
    ) -> None:
        """Add a progress update listener."""
        self._listeners.append(listener)
    
    def remove_listener(
        self,
        listener: Callable[[OnboardingProgress], None],
    ) -> None:
        """Remove a progress update listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def _notify_listeners(self, progress: OnboardingProgress) -> None:
        """Notify all listeners of progress update."""
        for listener in self._listeners:
            try:
                listener(progress)
            except Exception:
                pass
    
    def reset_onboarding(self, user_id: str) -> bool:
        """Reset onboarding for a user (for testing/re-onboarding)."""
        if user_id in self._user_progress:
            del self._user_progress[user_id]
            return True
        return False
    
    def get_onboarding_summary(self, user_id: str) -> dict[str, Any]:
        """Get a summary of onboarding progress."""
        progress = self._user_progress.get(user_id)
        if not progress:
            return {
                "status": OnboardingStatus.NOT_STARTED.value,
                "has_started": False,
            }
        
        return {
            "status": progress.status.value,
            "has_started": True,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "completion_percentage": progress.completion_percentage,
            "current_step": progress.current_step.title if progress.current_step else None,
            "steps_completed": len(progress.completed_steps),
            "steps_remaining": len(progress.remaining_steps),
            "estimated_remaining_minutes": progress.estimated_remaining_minutes,
        }


# Singleton instance
_gm_onboarding_service: Optional[GMOnboardingService] = None


def get_gm_onboarding_service() -> GMOnboardingService:
    """Get the singleton GM onboarding service."""
    global _gm_onboarding_service
    if _gm_onboarding_service is None:
        _gm_onboarding_service = GMOnboardingService()
    return _gm_onboarding_service
