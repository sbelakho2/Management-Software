"""
AI Learning Recommendations Service.

Provides AI-powered personalized learning recommendations:
- Personalized Learning Paths
- Content Recommendations based on user activity
- Skill Gap Analysis
- Spaced Repetition Scheduling
- Adaptive Difficulty
- Just-in-Time Learning suggestions

Key Features:
- Context-aware recommendations
- Performance-based adaptation
- Spaced repetition scheduling
- Role-based learning paths
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4


# ============================================================================
# Enums
# ============================================================================

class RecommendationType(str, Enum):
    """Type of learning recommendation."""
    
    NEXT_UNIT = "next_unit"
    REVIEW = "review"
    SKILL_GAP = "skill_gap"
    ROLE_BASED = "role_based"
    PREREQUISITE = "prerequisite"
    TRENDING = "trending"
    SIMILAR = "similar"
    JUST_IN_TIME = "just_in_time"
    CERTIFICATION = "certification"
    REFRESHER = "refresher"


class RecommendationPriority(str, Enum):
    """Priority of recommendation."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class LearningGoal(str, Enum):
    """User learning goal."""
    
    ONBOARDING = "onboarding"
    SKILL_DEVELOPMENT = "skill_development"
    CERTIFICATION = "certification"
    COMPLIANCE = "compliance"
    CAREER_GROWTH = "career_growth"
    PROBLEM_SOLVING = "problem_solving"
    REFRESHER = "refresher"


class SkillLevel(str, Enum):
    """User skill level."""
    
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStyle(str, Enum):
    """Preferred learning style."""
    
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING = "reading"
    KINESTHETIC = "kinesthetic"
    MIXED = "mixed"


class ContextTrigger(str, Enum):
    """Context that triggers recommendations."""
    
    LOGIN = "login"
    TASK_COMPLETION = "task_completion"
    ERROR_ENCOUNTERED = "error_encountered"
    LOW_PERFORMANCE = "low_performance"
    NEW_FEATURE = "new_feature"
    ROLE_CHANGE = "role_change"
    CERTIFICATION_EXPIRING = "certification_expiring"
    MANUAL_REQUEST = "manual_request"


class ContentCategory(str, Enum):
    """Learning content category."""
    
    TPS = "tps"
    LEAN = "lean"
    QUALITY = "quality"
    SAFETY = "safety"
    PROCESS = "process"
    TOOL = "tool"
    CONCEPT = "concept"
    BEST_PRACTICE = "best_practice"


class DifficultyLevel(str, Enum):
    """Content difficulty level."""
    
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class UserProfile:
    """User profile for learning recommendations."""
    
    user_id: UUID
    role: str = "user"
    department: str = ""
    tenure_months: int = 0
    skill_level: SkillLevel = SkillLevel.BEGINNER
    learning_style: LearningStyle = LearningStyle.MIXED
    preferred_duration_minutes: int = 15
    goals: list[LearningGoal] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)


@dataclass
class LearningUnitInfo:
    """Learning unit information."""
    
    id: UUID
    code: str
    title: str
    category: ContentCategory
    difficulty: DifficultyLevel
    content_type: str = "text"
    duration_minutes: int = 10
    tags: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    related_units: list[str] = field(default_factory=list)


@dataclass
class ProgressData:
    """User progress data."""
    
    user_id: UUID
    unit_id: UUID
    unit_code: str
    status: str = "not_started"
    progress_percentage: int = 0
    score: Optional[Decimal] = None
    time_spent_seconds: int = 0
    completed_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    review_count: int = 0


@dataclass
class SkillAssessment:
    """Assessment of user skill in a category."""
    
    category: ContentCategory
    level: SkillLevel
    score: Decimal = Decimal("50.0")
    units_completed: int = 0
    units_available: int = 0
    last_activity: Optional[datetime] = None
    trend: str = "stable"  # improving, stable, declining


@dataclass
class LearningRecommendation:
    """Individual learning recommendation."""
    
    id: UUID = field(default_factory=uuid4)
    recommendation_type: RecommendationType = RecommendationType.NEXT_UNIT
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    
    # Target unit
    unit_id: UUID = field(default_factory=uuid4)
    unit_code: str = ""
    unit_title: str = ""
    
    # Metadata
    category: ContentCategory = ContentCategory.TPS
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    estimated_duration_minutes: int = 10
    
    # Recommendation details
    reason: str = ""
    relevance_score: Decimal = Decimal("0.5")
    confidence: Decimal = Decimal("0.5")
    
    # Context
    context_trigger: Optional[ContextTrigger] = None
    related_task: Optional[str] = None
    
    # Due date for reviews/certifications
    due_date: Optional[datetime] = None
    
    # Action
    call_to_action: str = "Start Learning"
    deep_link: Optional[str] = None


@dataclass
class SkillGap:
    """Identified skill gap."""
    
    id: UUID = field(default_factory=uuid4)
    category: ContentCategory = ContentCategory.TPS
    current_level: SkillLevel = SkillLevel.NOVICE
    target_level: SkillLevel = SkillLevel.INTERMEDIATE
    gap_score: Decimal = Decimal("0")
    description: str = ""
    recommended_units: list[str] = field(default_factory=list)
    estimated_hours_to_close: float = 0.0
    priority: RecommendationPriority = RecommendationPriority.MEDIUM


@dataclass
class LearningPath:
    """Recommended learning path."""
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    description: str = ""
    goal: LearningGoal = LearningGoal.SKILL_DEVELOPMENT
    
    # Units in order
    unit_sequence: list[str] = field(default_factory=list)
    
    # Progress
    units_completed: int = 0
    total_units: int = 0
    progress_percentage: int = 0
    
    # Duration
    estimated_total_hours: float = 0.0
    estimated_remaining_hours: float = 0.0
    
    # Target
    target_completion_date: Optional[datetime] = None


@dataclass
class SpacedRepetitionSchedule:
    """Spaced repetition schedule for a unit."""
    
    unit_id: UUID
    unit_code: str
    unit_title: str
    
    # Schedule
    next_review_date: datetime
    interval_days: int = 1
    ease_factor: Decimal = Decimal("2.5")
    review_count: int = 0
    
    # Performance
    last_score: Optional[Decimal] = None
    streak: int = 0
    
    # Priority
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    overdue_days: int = 0


@dataclass
class RecommendationSet:
    """Complete set of recommendations for a user."""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    
    # Recommendations
    recommendations: list[LearningRecommendation] = field(default_factory=list)
    
    # Skill Gaps
    skill_gaps: list[SkillGap] = field(default_factory=list)
    
    # Learning Path
    active_path: Optional[LearningPath] = None
    
    # Reviews Due
    reviews_due: list[SpacedRepetitionSchedule] = field(default_factory=list)
    
    # Summary
    summary: str = ""
    primary_focus: str = ""
    
    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Optional[ContextTrigger] = None


# ============================================================================
# Constants
# ============================================================================

# Skill level progression
SKILL_LEVEL_ORDER = [
    SkillLevel.NOVICE,
    SkillLevel.BEGINNER,
    SkillLevel.INTERMEDIATE,
    SkillLevel.ADVANCED,
    SkillLevel.EXPERT,
]

# Difficulty to skill level mapping
DIFFICULTY_SKILL_MAP = {
    DifficultyLevel.BEGINNER: [SkillLevel.NOVICE, SkillLevel.BEGINNER],
    DifficultyLevel.INTERMEDIATE: [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE],
    DifficultyLevel.ADVANCED: [SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED],
    DifficultyLevel.EXPERT: [SkillLevel.ADVANCED, SkillLevel.EXPERT],
}

# Spaced repetition intervals (days)
SR_INTERVALS = [1, 3, 7, 14, 30, 60, 90]

# Role-based recommended categories
ROLE_CATEGORIES = {
    "production": [ContentCategory.PROCESS, ContentCategory.SAFETY, ContentCategory.LEAN],
    "quality": [ContentCategory.QUALITY, ContentCategory.TPS, ContentCategory.PROCESS],
    "engineering": [ContentCategory.PROCESS, ContentCategory.TOOL, ContentCategory.CONCEPT],
    "management": [ContentCategory.TPS, ContentCategory.LEAN, ContentCategory.BEST_PRACTICE],
    "sales": [ContentCategory.PROCESS, ContentCategory.QUALITY, ContentCategory.CONCEPT],
}

# New user onboarding units by role
ONBOARDING_UNITS = {
    "default": ["TPS-001", "LEAN-001", "SAFETY-001"],
    "production": ["SAFETY-001", "PROCESS-001", "TPS-001"],
    "quality": ["QUAL-001", "TPS-001", "PROCESS-001"],
    "engineering": ["CONCEPT-001", "TOOL-001", "TPS-001"],
}


# ============================================================================
# Service Class
# ============================================================================

class AILearningRecommendationsService:
    """
    AI-powered learning recommendations service.
    
    Provides personalized learning recommendations based on:
    - User profile and role
    - Learning progress and performance
    - Skill gaps and goals
    - Spaced repetition for retention
    - Context-aware just-in-time learning
    """
    
    def __init__(
        self,
        review_reminder_days: int = 7,
        max_recommendations: int = 10,
        min_relevance_score: Decimal = Decimal("0.3"),
        enable_spaced_repetition: bool = True,
    ):
        """
        Initialize the service.
        
        Args:
            review_reminder_days: Days before review is due to remind
            max_recommendations: Maximum recommendations to return
            min_relevance_score: Minimum relevance score to include
            enable_spaced_repetition: Whether to use spaced repetition
        """
        self.review_reminder_days = review_reminder_days
        self.max_recommendations = max_recommendations
        self.min_relevance_score = min_relevance_score
        self.enable_spaced_repetition = enable_spaced_repetition
        
        self._recommendation_sets: dict[UUID, RecommendationSet] = {}
        self._user_schedules: dict[UUID, list[SpacedRepetitionSchedule]] = {}
    
    # ========================================================================
    # Recommendation Generation
    # ========================================================================
    
    def generate_recommendations(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_data: list[ProgressData],
        context: Optional[ContextTrigger] = None,
    ) -> RecommendationSet:
        """
        Generate personalized learning recommendations.
        
        Args:
            user_profile: User profile information
            available_units: Available learning units
            progress_data: User's progress data
            context: Context that triggered recommendation
            
        Returns:
            RecommendationSet with all recommendations
        """
        recommendations = []
        
        # Build lookup maps
        progress_map = {p.unit_code: p for p in progress_data}
        units_map = {u.code: u for u in available_units}
        
        # 1. Check for reviews due (spaced repetition)
        if self.enable_spaced_repetition:
            review_recs = self._generate_review_recommendations(
                user_profile, progress_data, units_map
            )
            recommendations.extend(review_recs)
        
        # 2. Continue in-progress units
        in_progress_recs = self._generate_continue_recommendations(
            user_profile, available_units, progress_map
        )
        recommendations.extend(in_progress_recs)
        
        # 3. Next unit in sequence
        next_unit_recs = self._generate_next_unit_recommendations(
            user_profile, available_units, progress_map
        )
        recommendations.extend(next_unit_recs)
        
        # 4. Skill gap recommendations
        skill_gaps, gap_recs = self._analyze_skill_gaps(
            user_profile, available_units, progress_data
        )
        recommendations.extend(gap_recs)
        
        # 5. Role-based recommendations
        role_recs = self._generate_role_based_recommendations(
            user_profile, available_units, progress_map
        )
        recommendations.extend(role_recs)
        
        # 6. Context-aware recommendations
        if context:
            context_recs = self._generate_context_recommendations(
                user_profile, available_units, progress_map, context
            )
            recommendations.extend(context_recs)
        
        # Deduplicate and rank
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations = self._rank_recommendations(recommendations, user_profile)
        
        # Limit results
        recommendations = recommendations[:self.max_recommendations]
        
        # Build learning path
        active_path = self._build_learning_path(
            user_profile, available_units, progress_data
        )
        
        # Get review schedule
        reviews_due = self._get_due_reviews(user_profile.user_id, progress_data, units_map)
        
        # Generate summary
        summary, primary_focus = self._generate_summary(
            recommendations, skill_gaps, active_path
        )
        
        # Create recommendation set
        rec_set = RecommendationSet(
            user_id=user_profile.user_id,
            recommendations=recommendations,
            skill_gaps=skill_gaps,
            active_path=active_path,
            reviews_due=reviews_due,
            summary=summary,
            primary_focus=primary_focus,
            context=context,
        )
        
        # Store for retrieval
        self._recommendation_sets[rec_set.id] = rec_set
        
        return rec_set
    
    def _generate_review_recommendations(
        self,
        user_profile: UserProfile,
        progress_data: list[ProgressData],
        units_map: dict[str, LearningUnitInfo],
    ) -> list[LearningRecommendation]:
        """Generate recommendations for units due for review."""
        recommendations = []
        now = datetime.now(timezone.utc)
        
        for progress in progress_data:
            if progress.status != "completed":
                continue
            
            if progress.next_review_date and progress.next_review_date <= now:
                unit = units_map.get(progress.unit_code)
                if not unit:
                    continue
                
                overdue_days = (now - progress.next_review_date).days
                priority = self._calculate_review_priority(overdue_days)
                
                recommendations.append(LearningRecommendation(
                    recommendation_type=RecommendationType.REVIEW,
                    priority=priority,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    unit_title=unit.title,
                    category=unit.category,
                    difficulty=unit.difficulty,
                    estimated_duration_minutes=max(5, unit.duration_minutes // 2),
                    reason=f"Review due - {'overdue by ' + str(overdue_days) + ' days' if overdue_days > 0 else 'due today'}",
                    relevance_score=Decimal("0.9"),
                    confidence=Decimal("0.95"),
                    due_date=progress.next_review_date,
                    call_to_action="Review Now",
                ))
        
        return recommendations
    
    def _generate_continue_recommendations(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_map: dict[str, ProgressData],
    ) -> list[LearningRecommendation]:
        """Generate recommendations to continue in-progress units."""
        recommendations = []
        
        for unit in available_units:
            progress = progress_map.get(unit.code)
            if progress and progress.status == "in_progress":
                remaining_percent = 100 - progress.progress_percentage
                estimated_time = int(unit.duration_minutes * remaining_percent / 100)
                
                recommendations.append(LearningRecommendation(
                    recommendation_type=RecommendationType.NEXT_UNIT,
                    priority=RecommendationPriority.HIGH,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    unit_title=unit.title,
                    category=unit.category,
                    difficulty=unit.difficulty,
                    estimated_duration_minutes=estimated_time,
                    reason=f"Continue where you left off ({progress.progress_percentage}% complete)",
                    relevance_score=Decimal("0.95"),
                    confidence=Decimal("0.9"),
                    call_to_action="Continue Learning",
                ))
        
        return recommendations
    
    def _generate_next_unit_recommendations(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_map: dict[str, ProgressData],
    ) -> list[LearningRecommendation]:
        """Generate recommendations for next units in sequence."""
        recommendations = []
        completed_codes = {
            p.unit_code for p in progress_map.values()
            if p.status == "completed"
        }
        in_progress_codes = {
            p.unit_code for p in progress_map.values()
            if p.status == "in_progress"
        }
        
        for unit in available_units:
            # Skip if already started or completed
            if unit.code in completed_codes or unit.code in in_progress_codes:
                continue
            
            # Check prerequisites
            prereqs_met = all(
                prereq in completed_codes
                for prereq in unit.prerequisites
            )
            
            if not prereqs_met:
                continue
            
            # Check difficulty match
            difficulty_match = self._check_difficulty_match(
                unit.difficulty, user_profile.skill_level
            )
            
            if difficulty_match < Decimal("0.3"):
                continue
            
            relevance = self._calculate_unit_relevance(
                unit, user_profile, completed_codes
            )
            
            recommendations.append(LearningRecommendation(
                recommendation_type=RecommendationType.NEXT_UNIT,
                priority=self._priority_from_relevance(relevance),
                unit_id=unit.id,
                unit_code=unit.code,
                unit_title=unit.title,
                category=unit.category,
                difficulty=unit.difficulty,
                estimated_duration_minutes=unit.duration_minutes,
                reason="Next recommended unit based on your progress",
                relevance_score=relevance,
                confidence=difficulty_match,
                call_to_action="Start Learning",
            ))
        
        return recommendations
    
    def _analyze_skill_gaps(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_data: list[ProgressData],
    ) -> tuple[list[SkillGap], list[LearningRecommendation]]:
        """Analyze skill gaps and generate recommendations."""
        skill_gaps = []
        recommendations = []
        
        # Group units by category
        units_by_category: dict[ContentCategory, list[LearningUnitInfo]] = {}
        for unit in available_units:
            if unit.category not in units_by_category:
                units_by_category[unit.category] = []
            units_by_category[unit.category].append(unit)
        
        # Analyze each category
        completed_codes = {
            p.unit_code for p in progress_data
            if p.status == "completed"
        }
        
        for category, units in units_by_category.items():
            total_units = len(units)
            completed_units = sum(
                1 for u in units if u.code in completed_codes
            )
            completion_rate = completed_units / total_units if total_units > 0 else 0
            
            # Determine current and target levels
            current_level = self._estimate_skill_level(completion_rate)
            target_level = self._get_target_level(user_profile, category)
            
            if SKILL_LEVEL_ORDER.index(current_level) < SKILL_LEVEL_ORDER.index(target_level):
                gap_score = Decimal(str(
                    (SKILL_LEVEL_ORDER.index(target_level) - SKILL_LEVEL_ORDER.index(current_level)) / 4
                ))
                
                # Find recommended units to close gap
                gap_units = [
                    u.code for u in units
                    if u.code not in completed_codes
                    and self._check_difficulty_match(u.difficulty, current_level) >= Decimal("0.5")
                ][:3]
                
                skill_gaps.append(SkillGap(
                    category=category,
                    current_level=current_level,
                    target_level=target_level,
                    gap_score=gap_score,
                    description=f"Improve {category.value} skills from {current_level.value} to {target_level.value}",
                    recommended_units=gap_units,
                    estimated_hours_to_close=len(gap_units) * 0.5,
                    priority=self._priority_from_relevance(gap_score),
                ))
                
                # Generate recommendations for gap units
                for unit_code in gap_units[:2]:
                    unit = next((u for u in units if u.code == unit_code), None)
                    if unit:
                        recommendations.append(LearningRecommendation(
                            recommendation_type=RecommendationType.SKILL_GAP,
                            priority=RecommendationPriority.HIGH,
                            unit_id=unit.id,
                            unit_code=unit.code,
                            unit_title=unit.title,
                            category=unit.category,
                            difficulty=unit.difficulty,
                            estimated_duration_minutes=unit.duration_minutes,
                            reason=f"Address skill gap in {category.value}",
                            relevance_score=Decimal("0.85"),
                            confidence=Decimal("0.8"),
                            call_to_action="Build Skills",
                        ))
        
        return skill_gaps, recommendations
    
    def _generate_role_based_recommendations(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_map: dict[str, ProgressData],
    ) -> list[LearningRecommendation]:
        """Generate role-based learning recommendations."""
        recommendations = []
        
        # Get recommended categories for role
        role = user_profile.role.lower()
        recommended_categories = ROLE_CATEGORIES.get(role, [ContentCategory.TPS])
        
        completed_codes = {
            code for code, p in progress_map.items()
            if p.status == "completed"
        }
        
        for unit in available_units:
            if unit.code in completed_codes:
                continue
            
            if unit.category in recommended_categories:
                relevance = Decimal("0.7")
                if unit.category == recommended_categories[0]:
                    relevance = Decimal("0.8")
                
                recommendations.append(LearningRecommendation(
                    recommendation_type=RecommendationType.ROLE_BASED,
                    priority=RecommendationPriority.MEDIUM,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    unit_title=unit.title,
                    category=unit.category,
                    difficulty=unit.difficulty,
                    estimated_duration_minutes=unit.duration_minutes,
                    reason=f"Recommended for your role as {user_profile.role}",
                    relevance_score=relevance,
                    confidence=Decimal("0.75"),
                    call_to_action="Start Learning",
                ))
        
        return recommendations
    
    def _generate_context_recommendations(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_map: dict[str, ProgressData],
        context: ContextTrigger,
    ) -> list[LearningRecommendation]:
        """Generate context-aware recommendations."""
        recommendations = []
        
        completed_codes = {
            code for code, p in progress_map.items()
            if p.status == "completed"
        }
        
        # Context-specific logic
        if context == ContextTrigger.LOGIN:
            # Suggest quick refreshers on login
            for unit in available_units[:3]:
                if unit.code not in completed_codes and unit.duration_minutes <= 10:
                    recommendations.append(LearningRecommendation(
                        recommendation_type=RecommendationType.JUST_IN_TIME,
                        priority=RecommendationPriority.LOW,
                        unit_id=unit.id,
                        unit_code=unit.code,
                        unit_title=unit.title,
                        category=unit.category,
                        difficulty=unit.difficulty,
                        estimated_duration_minutes=unit.duration_minutes,
                        reason="Quick learning opportunity",
                        relevance_score=Decimal("0.5"),
                        confidence=Decimal("0.6"),
                        context_trigger=context,
                        call_to_action="Learn Now",
                    ))
        
        elif context == ContextTrigger.ERROR_ENCOUNTERED:
            # Suggest problem-solving content
            problem_units = [
                u for u in available_units
                if ContentCategory.PROCESS in [u.category]
                or "problem" in u.title.lower()
                or "troubleshoot" in u.title.lower()
            ]
            for unit in problem_units[:2]:
                if unit.code not in completed_codes:
                    recommendations.append(LearningRecommendation(
                        recommendation_type=RecommendationType.JUST_IN_TIME,
                        priority=RecommendationPriority.HIGH,
                        unit_id=unit.id,
                        unit_code=unit.code,
                        unit_title=unit.title,
                        category=unit.category,
                        difficulty=unit.difficulty,
                        estimated_duration_minutes=unit.duration_minutes,
                        reason="Related to issue you encountered",
                        relevance_score=Decimal("0.9"),
                        confidence=Decimal("0.7"),
                        context_trigger=context,
                        call_to_action="Learn How to Fix",
                    ))
        
        elif context == ContextTrigger.CERTIFICATION_EXPIRING:
            # Suggest certification refresher
            cert_units = [
                u for u in available_units
                if "certification" in u.title.lower()
                or "compliance" in u.title.lower()
            ]
            for unit in cert_units[:3]:
                recommendations.append(LearningRecommendation(
                    recommendation_type=RecommendationType.CERTIFICATION,
                    priority=RecommendationPriority.CRITICAL,
                    unit_id=unit.id,
                    unit_code=unit.code,
                    unit_title=unit.title,
                    category=unit.category,
                    difficulty=unit.difficulty,
                    estimated_duration_minutes=unit.duration_minutes,
                    reason="Required for certification renewal",
                    relevance_score=Decimal("1.0"),
                    confidence=Decimal("1.0"),
                    context_trigger=context,
                    call_to_action="Complete Now",
                ))
        
        return recommendations
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _calculate_review_priority(self, overdue_days: int) -> RecommendationPriority:
        """Calculate priority based on overdue days."""
        if overdue_days > 14:
            return RecommendationPriority.CRITICAL
        elif overdue_days > 7:
            return RecommendationPriority.HIGH
        elif overdue_days > 0:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    def _check_difficulty_match(
        self,
        difficulty: DifficultyLevel,
        skill_level: SkillLevel,
    ) -> Decimal:
        """Check how well difficulty matches skill level."""
        appropriate_skills = DIFFICULTY_SKILL_MAP.get(difficulty, [])
        
        if skill_level in appropriate_skills:
            return Decimal("1.0")
        
        # Check adjacent levels
        skill_idx = SKILL_LEVEL_ORDER.index(skill_level)
        for appropriate_skill in appropriate_skills:
            appropriate_idx = SKILL_LEVEL_ORDER.index(appropriate_skill)
            if abs(skill_idx - appropriate_idx) == 1:
                return Decimal("0.7")
            if abs(skill_idx - appropriate_idx) == 2:
                return Decimal("0.4")
        
        return Decimal("0.2")
    
    def _calculate_unit_relevance(
        self,
        unit: LearningUnitInfo,
        user_profile: UserProfile,
        completed_codes: set[str],
    ) -> Decimal:
        """Calculate relevance score for a unit."""
        relevance = Decimal("0.5")  # Base relevance
        
        # Category match
        role = user_profile.role.lower()
        preferred_categories = ROLE_CATEGORIES.get(role, [])
        if unit.category in preferred_categories:
            relevance += Decimal("0.2")
        
        # Interest match
        for interest in user_profile.interests:
            if interest.lower() in unit.title.lower() or interest.lower() in unit.tags:
                relevance += Decimal("0.1")
        
        # Prerequisite completion bonus
        prereqs_completed = sum(
            1 for prereq in unit.prerequisites if prereq in completed_codes
        )
        if unit.prerequisites and prereqs_completed == len(unit.prerequisites):
            relevance += Decimal("0.1")
        
        # Duration preference match
        if abs(unit.duration_minutes - user_profile.preferred_duration_minutes) <= 5:
            relevance += Decimal("0.05")
        
        return min(relevance, Decimal("1.0"))
    
    def _priority_from_relevance(self, relevance: Decimal) -> RecommendationPriority:
        """Convert relevance score to priority."""
        if relevance >= Decimal("0.9"):
            return RecommendationPriority.CRITICAL
        elif relevance >= Decimal("0.7"):
            return RecommendationPriority.HIGH
        elif relevance >= Decimal("0.5"):
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    def _estimate_skill_level(self, completion_rate: float) -> SkillLevel:
        """Estimate skill level from completion rate."""
        if completion_rate >= 0.9:
            return SkillLevel.EXPERT
        elif completion_rate >= 0.7:
            return SkillLevel.ADVANCED
        elif completion_rate >= 0.4:
            return SkillLevel.INTERMEDIATE
        elif completion_rate >= 0.2:
            return SkillLevel.BEGINNER
        else:
            return SkillLevel.NOVICE
    
    def _get_target_level(
        self,
        user_profile: UserProfile,
        category: ContentCategory,
    ) -> SkillLevel:
        """Get target skill level for a category."""
        # For now, target one level above current or based on goals
        if LearningGoal.CERTIFICATION in user_profile.goals:
            return SkillLevel.ADVANCED
        elif LearningGoal.CAREER_GROWTH in user_profile.goals:
            return SkillLevel.ADVANCED
        elif LearningGoal.SKILL_DEVELOPMENT in user_profile.goals:
            return SkillLevel.INTERMEDIATE
        else:
            # Default: one level above current
            current_idx = SKILL_LEVEL_ORDER.index(user_profile.skill_level)
            target_idx = min(current_idx + 1, len(SKILL_LEVEL_ORDER) - 1)
            return SKILL_LEVEL_ORDER[target_idx]
    
    def _deduplicate_recommendations(
        self,
        recommendations: list[LearningRecommendation],
    ) -> list[LearningRecommendation]:
        """Remove duplicate recommendations."""
        seen_codes = set()
        unique_recs = []
        
        for rec in recommendations:
            if rec.unit_code not in seen_codes:
                seen_codes.add(rec.unit_code)
                unique_recs.append(rec)
        
        return unique_recs
    
    def _rank_recommendations(
        self,
        recommendations: list[LearningRecommendation],
        user_profile: UserProfile,
    ) -> list[LearningRecommendation]:
        """Rank recommendations by priority and relevance."""
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
            RecommendationPriority.OPTIONAL: 4,
        }
        
        return sorted(
            recommendations,
            key=lambda r: (
                priority_order.get(r.priority, 5),
                -float(r.relevance_score),
            ),
        )
    
    def _build_learning_path(
        self,
        user_profile: UserProfile,
        available_units: list[LearningUnitInfo],
        progress_data: list[ProgressData],
    ) -> Optional[LearningPath]:
        """Build a learning path for the user."""
        completed_codes = {
            p.unit_code for p in progress_data if p.status == "completed"
        }
        
        # Determine goal
        goal = (
            user_profile.goals[0]
            if user_profile.goals
            else LearningGoal.SKILL_DEVELOPMENT
        )
        
        # Select units for path
        path_units = []
        for unit in available_units:
            if unit.code not in completed_codes:
                match = self._check_difficulty_match(
                    unit.difficulty, user_profile.skill_level
                )
                if match >= Decimal("0.5"):
                    path_units.append(unit.code)
                    if len(path_units) >= 10:
                        break
        
        if not path_units:
            return None
        
        total_duration = sum(
            u.duration_minutes for u in available_units
            if u.code in path_units
        )
        
        return LearningPath(
            title=f"Learning Path: {goal.value.replace('_', ' ').title()}",
            description=f"Personalized learning path for {user_profile.role}",
            goal=goal,
            unit_sequence=path_units,
            units_completed=0,
            total_units=len(path_units),
            progress_percentage=0,
            estimated_total_hours=total_duration / 60,
            estimated_remaining_hours=total_duration / 60,
        )
    
    def _get_due_reviews(
        self,
        user_id: UUID,
        progress_data: list[ProgressData],
        units_map: dict[str, LearningUnitInfo],
    ) -> list[SpacedRepetitionSchedule]:
        """Get reviews that are due or coming up."""
        reviews = []
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(days=self.review_reminder_days)
        
        for progress in progress_data:
            if progress.status != "completed":
                continue
            
            if not progress.next_review_date:
                continue
            
            if progress.next_review_date <= threshold:
                unit = units_map.get(progress.unit_code)
                if not unit:
                    continue
                
                overdue = max(0, (now - progress.next_review_date).days)
                priority = self._calculate_review_priority(overdue)
                
                reviews.append(SpacedRepetitionSchedule(
                    unit_id=unit.id,
                    unit_code=unit.code,
                    unit_title=unit.title,
                    next_review_date=progress.next_review_date,
                    review_count=progress.review_count,
                    last_score=progress.score,
                    priority=priority,
                    overdue_days=overdue,
                ))
        
        # Sort by due date
        reviews.sort(key=lambda r: r.next_review_date)
        
        return reviews
    
    def _generate_summary(
        self,
        recommendations: list[LearningRecommendation],
        skill_gaps: list[SkillGap],
        active_path: Optional[LearningPath],
    ) -> tuple[str, str]:
        """Generate summary text."""
        parts = []
        primary_focus = "Continue learning"
        
        # Reviews due
        review_count = sum(
            1 for r in recommendations
            if r.recommendation_type == RecommendationType.REVIEW
        )
        if review_count > 0:
            parts.append(f"{review_count} review(s) due")
            primary_focus = "Complete pending reviews"
        
        # In-progress
        in_progress_count = sum(
            1 for r in recommendations
            if "continue" in r.reason.lower()
        )
        if in_progress_count > 0:
            parts.append(f"{in_progress_count} unit(s) in progress")
            if not review_count:
                primary_focus = "Continue in-progress units"
        
        # Skill gaps
        if skill_gaps:
            critical_gaps = sum(
                1 for g in skill_gaps
                if g.priority == RecommendationPriority.HIGH
            )
            if critical_gaps:
                parts.append(f"{critical_gaps} skill gap(s) to address")
        
        # Path progress
        if active_path:
            parts.append(f"Learning path: {active_path.progress_percentage}% complete")
        
        summary = ". ".join(parts) if parts else "No pending items"
        
        return summary, primary_focus
    
    # ========================================================================
    # Spaced Repetition
    # ========================================================================
    
    def calculate_next_review(
        self,
        current_interval: int,
        ease_factor: Decimal,
        performance: Decimal,
    ) -> tuple[int, Decimal]:
        """
        Calculate next review interval using SM-2 algorithm.
        
        Args:
            current_interval: Current interval in days
            ease_factor: Current ease factor (2.5 default)
            performance: Performance score 0-5 (3+ is passing)
            
        Returns:
            Tuple of (new_interval, new_ease_factor)
        """
        # Adjust ease factor based on performance
        new_ease = ease_factor + (
            Decimal("0.1") - (Decimal("5") - performance) * (
                Decimal("0.08") + (Decimal("5") - performance) * Decimal("0.02")
            )
        )
        new_ease = max(Decimal("1.3"), new_ease)
        
        # Calculate new interval
        if performance < Decimal("3"):
            # Failed - reset to 1 day
            new_interval = 1
        elif current_interval == 0:
            new_interval = 1
        elif current_interval == 1:
            new_interval = 6
        else:
            new_interval = int(current_interval * float(new_ease))
        
        return new_interval, new_ease
    
    def schedule_review(
        self,
        user_id: UUID,
        unit_id: UUID,
        unit_code: str,
        unit_title: str,
        performance: Decimal,
        current_schedule: Optional[SpacedRepetitionSchedule] = None,
    ) -> SpacedRepetitionSchedule:
        """
        Schedule next review for a unit.
        
        Args:
            user_id: User ID
            unit_id: Unit ID
            unit_code: Unit code
            unit_title: Unit title
            performance: Performance score 0-5
            current_schedule: Current schedule if exists
            
        Returns:
            Updated SpacedRepetitionSchedule
        """
        if current_schedule:
            interval = current_schedule.interval_days
            ease = current_schedule.ease_factor
            review_count = current_schedule.review_count + 1
            streak = current_schedule.streak + 1 if performance >= Decimal("3") else 0
        else:
            interval = 0
            ease = Decimal("2.5")
            review_count = 1
            streak = 1 if performance >= Decimal("3") else 0
        
        new_interval, new_ease = self.calculate_next_review(
            interval, ease, performance
        )
        
        schedule = SpacedRepetitionSchedule(
            unit_id=unit_id,
            unit_code=unit_code,
            unit_title=unit_title,
            next_review_date=datetime.now(timezone.utc) + timedelta(days=new_interval),
            interval_days=new_interval,
            ease_factor=new_ease,
            review_count=review_count,
            last_score=performance,
            streak=streak,
        )
        
        # Store schedule
        if user_id not in self._user_schedules:
            self._user_schedules[user_id] = []
        
        # Update or add
        existing_idx = next(
            (i for i, s in enumerate(self._user_schedules[user_id])
             if s.unit_code == unit_code),
            None
        )
        if existing_idx is not None:
            self._user_schedules[user_id][existing_idx] = schedule
        else:
            self._user_schedules[user_id].append(schedule)
        
        return schedule
    
    # ========================================================================
    # Retrieval Methods
    # ========================================================================
    
    def get_recommendation_set(
        self,
        recommendation_set_id: UUID,
    ) -> Optional[RecommendationSet]:
        """Get stored recommendation set by ID."""
        return self._recommendation_sets.get(recommendation_set_id)
    
    def get_user_schedule(
        self,
        user_id: UUID,
    ) -> list[SpacedRepetitionSchedule]:
        """Get user's spaced repetition schedule."""
        return self._user_schedules.get(user_id, [])
    
    def get_onboarding_units(
        self,
        role: str = "default",
    ) -> list[str]:
        """Get recommended onboarding units for a role."""
        return ONBOARDING_UNITS.get(role.lower(), ONBOARDING_UNITS["default"])
    
    def get_recommended_categories(
        self,
        role: str,
    ) -> list[ContentCategory]:
        """Get recommended learning categories for a role."""
        return ROLE_CATEGORIES.get(role.lower(), [ContentCategory.TPS])
