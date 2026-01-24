"""
Access Review Service.

Implements periodic access reviews for privileged roles (GM/Admin).
Tracks review campaigns, user access attestations, and compliance reporting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.core.entity_providers import build_user_access_provider


class ReviewFrequency(str, Enum):
    """Access review frequency options."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class ReviewStatus(str, Enum):
    """Access review campaign status."""

    DRAFT = "draft"
    ACTIVE = "active"
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttestationStatus(str, Enum):
    """Individual attestation status."""

    PENDING = "pending"
    APPROVED = "approved"
    REVOKED = "revoked"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class AccessType(str, Enum):
    """Type of access being reviewed."""

    ROLE = "role"
    PERMISSION = "permission"
    RESOURCE = "resource"
    SENSITIVE_DATA = "sensitive_data"


class RiskLevel(str, Enum):
    """Risk level for access."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AccessItem:
    """Individual access item under review."""

    id: UUID
    access_type: AccessType
    name: str
    description: str
    risk_level: RiskLevel
    granted_at: datetime
    granted_by: UUID | None
    last_used: datetime | None
    usage_count: int
    is_active: bool


@dataclass
class UserAccess:
    """User's access profile for review."""

    user_id: UUID
    user_name: str
    user_email: str
    department: str | None
    manager_id: UUID | None
    access_items: list[AccessItem]
    total_risk_score: float


@dataclass
class Attestation:
    """Attestation for a user's access."""

    id: UUID
    review_id: UUID
    user_id: UUID
    access_item_id: UUID
    reviewer_id: UUID
    status: AttestationStatus
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None
    expires_at: datetime


@dataclass
class ReviewCampaign:
    """Access review campaign."""

    id: UUID
    name: str
    description: str
    frequency: ReviewFrequency
    status: ReviewStatus
    target_roles: list[str]
    reviewer_ids: list[UUID]
    start_date: datetime
    end_date: datetime
    created_by: UUID
    created_at: datetime
    completed_at: datetime | None
    attestation_count: int
    completed_count: int


@dataclass
class ReviewReminder:
    """Reminder for pending reviews."""

    id: UUID
    review_id: UUID
    reviewer_id: UUID
    sent_at: datetime
    reminder_type: str  # initial, first_reminder, final_warning
    pending_count: int


@dataclass
class AccessViolation:
    """Detected access violation."""

    id: UUID
    user_id: UUID
    violation_type: str
    description: str
    detected_at: datetime
    resolved_at: datetime | None
    resolved_by: UUID | None
    resolution_notes: str | None


class AccessReviewService:
    """Service for managing periodic access reviews."""

    def __init__(self, user_access_provider: callable | None = None) -> None:
        """Initialize the access review service."""
        self._campaigns: dict[UUID, ReviewCampaign] = {}
        self._attestations: dict[UUID, Attestation] = {}
        self._user_access: dict[UUID, UserAccess] = {}
        self._reminders: list[ReviewReminder] = []
        self._violations: list[AccessViolation] = []
        self._user_access_provider = user_access_provider

        # Configuration
        self._privileged_roles = ["GM", "Admin", "Finance_Manager", "Quality_Manager"]
        self._review_window_days = 30
        self._reminder_intervals = [7, 3, 1]  # Days before deadline

        # Initialize default schedule
        self._review_schedules: dict[str, ReviewFrequency] = {
            "Admin": ReviewFrequency.MONTHLY,
            "GM": ReviewFrequency.QUARTERLY,
            "Finance_Manager": ReviewFrequency.QUARTERLY,
            "Quality_Manager": ReviewFrequency.SEMI_ANNUAL,
        }

    # Campaign Management

    def create_campaign(
        self,
        name: str,
        description: str,
        target_roles: list[str],
        reviewer_ids: list[UUID],
        frequency: ReviewFrequency,
        start_date: datetime | None = None,
        duration_days: int = 30,
        created_by: UUID | None = None,
    ) -> ReviewCampaign:
        """Create a new access review campaign."""
        now = datetime.now(timezone.utc)
        start = start_date or now
        end = start + timedelta(days=duration_days)

        campaign = ReviewCampaign(
            id=uuid4(),
            name=name,
            description=description,
            frequency=frequency,
            status=ReviewStatus.DRAFT,
            target_roles=target_roles,
            reviewer_ids=reviewer_ids,
            start_date=start,
            end_date=end,
            created_by=created_by or uuid4(),
            created_at=now,
            completed_at=None,
            attestation_count=0,
            completed_count=0,
        )

        self._campaigns[campaign.id] = campaign
        return campaign

    def get_campaign(self, campaign_id: UUID) -> ReviewCampaign | None:
        """Get a campaign by ID."""
        return self._campaigns.get(campaign_id)

    def get_campaigns(
        self,
        status: ReviewStatus | None = None,
        frequency: ReviewFrequency | None = None,
    ) -> list[ReviewCampaign]:
        """Get campaigns with optional filters."""
        campaigns = []

        for campaign in self._campaigns.values():
            if status and campaign.status != status:
                continue
            if frequency and campaign.frequency != frequency:
                continue
            campaigns.append(campaign)

        return sorted(campaigns, key=lambda c: c.start_date, reverse=True)

    def start_campaign(self, campaign_id: UUID) -> ReviewCampaign | None:
        """Start a review campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        if campaign.status != ReviewStatus.DRAFT:
            return None

        campaign.status = ReviewStatus.ACTIVE
        campaign.start_date = datetime.now(timezone.utc)

        # Generate attestations for all users with target roles
        self._generate_attestations(campaign)

        return campaign

    def _generate_attestations(self, campaign: ReviewCampaign) -> None:
        """Generate attestations for a campaign."""
        # Get users with target roles
        users = self._get_users_with_roles(campaign.target_roles)

        for user in users:
            for access_item in user.access_items:
                attestation = Attestation(
                    id=uuid4(),
                    review_id=campaign.id,
                    user_id=user.user_id,
                    access_item_id=access_item.id,
                    reviewer_id=campaign.reviewer_ids[0] if campaign.reviewer_ids else uuid4(),
                    status=AttestationStatus.PENDING,
                    decision_reason=None,
                    created_at=datetime.now(timezone.utc),
                    decided_at=None,
                    expires_at=campaign.end_date,
                )

                self._attestations[attestation.id] = attestation
                campaign.attestation_count += 1

    def _get_users_with_roles(self, roles: list[str]) -> list[UserAccess]:
        """Get users with specified roles."""
        if self._user_access_provider:
            return self._user_access_provider(roles)
        return list(self._user_access.values())

    def complete_campaign(self, campaign_id: UUID) -> ReviewCampaign | None:
        """Mark a campaign as complete."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        if campaign.status != ReviewStatus.ACTIVE:
            return None

        # Check all attestations are decided
        pending = self._get_pending_attestations(campaign_id)
        if pending:
            campaign.status = ReviewStatus.PENDING_APPROVAL
            return campaign

        campaign.status = ReviewStatus.COMPLETED
        campaign.completed_at = datetime.now(timezone.utc)

        return campaign

    def cancel_campaign(self, campaign_id: UUID, reason: str) -> ReviewCampaign | None:
        """Cancel a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        if campaign.status == ReviewStatus.COMPLETED:
            return None

        campaign.status = ReviewStatus.CANCELLED
        return campaign

    # User Access Management

    def register_user_access(
        self,
        user_id: UUID,
        user_name: str,
        user_email: str,
        department: str | None = None,
        manager_id: UUID | None = None,
    ) -> UserAccess:
        """Register a user for access reviews."""
        user_access = UserAccess(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            department=department,
            manager_id=manager_id,
            access_items=[],
            total_risk_score=0.0,
        )

        self._user_access[user_id] = user_access
        return user_access

    def get_user_access(self, user_id: UUID) -> UserAccess | None:
        """Get a user's access profile."""
        return self._user_access.get(user_id)

    def add_access_item(
        self,
        user_id: UUID,
        access_type: AccessType,
        name: str,
        description: str = "",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        granted_by: UUID | None = None,
    ) -> AccessItem | None:
        """Add an access item to a user."""
        user_access = self._user_access.get(user_id)
        if not user_access:
            return None

        item = AccessItem(
            id=uuid4(),
            access_type=access_type,
            name=name,
            description=description,
            risk_level=risk_level,
            granted_at=datetime.now(timezone.utc),
            granted_by=granted_by,
            last_used=None,
            usage_count=0,
            is_active=True,
        )

        user_access.access_items.append(item)
        user_access.total_risk_score = self._calculate_risk_score(user_access)

        return item

    def _calculate_risk_score(self, user_access: UserAccess) -> float:
        """Calculate total risk score for a user."""
        risk_weights = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 4,
            RiskLevel.CRITICAL: 8,
        }

        total = 0.0
        for item in user_access.access_items:
            if item.is_active:
                total += risk_weights.get(item.risk_level, 1)

        return total

    def remove_access_item(self, user_id: UUID, access_item_id: UUID) -> bool:
        """Remove an access item from a user."""
        user_access = self._user_access.get(user_id)
        if not user_access:
            return False

        for item in user_access.access_items:
            if item.id == access_item_id:
                item.is_active = False
                user_access.total_risk_score = self._calculate_risk_score(user_access)
                return True

        return False

    def get_high_risk_users(self, threshold: float = 10.0) -> list[UserAccess]:
        """Get users with high risk scores."""
        return [
            u for u in self._user_access.values()
            if u.total_risk_score >= threshold
        ]

    # Attestation Management

    def get_attestation(self, attestation_id: UUID) -> Attestation | None:
        """Get an attestation by ID."""
        return self._attestations.get(attestation_id)

    def get_attestations_for_review(
        self,
        campaign_id: UUID,
        status: AttestationStatus | None = None,
    ) -> list[Attestation]:
        """Get attestations for a campaign."""
        attestations = []

        for att in self._attestations.values():
            if att.review_id != campaign_id:
                continue
            if status and att.status != status:
                continue
            attestations.append(att)

        return attestations

    def get_attestations_for_reviewer(
        self,
        reviewer_id: UUID,
        pending_only: bool = True,
    ) -> list[Attestation]:
        """Get attestations assigned to a reviewer."""
        attestations = []

        for att in self._attestations.values():
            if att.reviewer_id != reviewer_id:
                continue
            if pending_only and att.status != AttestationStatus.PENDING:
                continue
            attestations.append(att)

        return attestations

    def _get_pending_attestations(self, campaign_id: UUID) -> list[Attestation]:
        """Get pending attestations for a campaign."""
        return self.get_attestations_for_review(campaign_id, AttestationStatus.PENDING)

    def approve_access(
        self,
        attestation_id: UUID,
        reviewer_id: UUID,
        reason: str | None = None,
    ) -> Attestation | None:
        """Approve continued access."""
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            return None

        if attestation.reviewer_id != reviewer_id:
            return None

        attestation.status = AttestationStatus.APPROVED
        attestation.decision_reason = reason or "Access approved - still required"
        attestation.decided_at = datetime.now(timezone.utc)

        self._update_campaign_progress(attestation.review_id)

        return attestation

    def revoke_access(
        self,
        attestation_id: UUID,
        reviewer_id: UUID,
        reason: str,
    ) -> Attestation | None:
        """Revoke access."""
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            return None

        if attestation.reviewer_id != reviewer_id:
            return None

        if not reason:
            return None

        attestation.status = AttestationStatus.REVOKED
        attestation.decision_reason = reason
        attestation.decided_at = datetime.now(timezone.utc)

        # Mark the access item as inactive
        self.remove_access_item(attestation.user_id, attestation.access_item_id)

        self._update_campaign_progress(attestation.review_id)

        return attestation

    def escalate_attestation(
        self,
        attestation_id: UUID,
        escalate_to: UUID,
        reason: str,
    ) -> Attestation | None:
        """Escalate an attestation to another reviewer."""
        attestation = self._attestations.get(attestation_id)
        if not attestation:
            return None

        attestation.status = AttestationStatus.ESCALATED
        attestation.reviewer_id = escalate_to
        attestation.decision_reason = f"Escalated: {reason}"

        return attestation

    def _update_campaign_progress(self, campaign_id: UUID) -> None:
        """Update campaign progress counts."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return

        attestations = self.get_attestations_for_review(campaign_id)
        completed = [
            a for a in attestations
            if a.status in [AttestationStatus.APPROVED, AttestationStatus.REVOKED]
        ]

        campaign.completed_count = len(completed)

    # Reminders

    def generate_reminders(self, campaign_id: UUID) -> list[ReviewReminder]:
        """Generate reminders for pending attestations."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status != ReviewStatus.ACTIVE:
            return []

        now = datetime.now(timezone.utc)
        days_left = (campaign.end_date - now).days
        reminders = []

        # Determine reminder type
        if days_left <= self._reminder_intervals[2]:
            reminder_type = "final_warning"
        elif days_left <= self._reminder_intervals[1]:
            reminder_type = "first_reminder"
        else:
            reminder_type = "initial"

        # Group pending attestations by reviewer
        pending_by_reviewer: dict[UUID, int] = {}
        for att in self._get_pending_attestations(campaign_id):
            pending_by_reviewer[att.reviewer_id] = pending_by_reviewer.get(att.reviewer_id, 0) + 1

        for reviewer_id, pending_count in pending_by_reviewer.items():
            reminder = ReviewReminder(
                id=uuid4(),
                review_id=campaign_id,
                reviewer_id=reviewer_id,
                sent_at=now,
                reminder_type=reminder_type,
                pending_count=pending_count,
            )
            self._reminders.append(reminder)
            reminders.append(reminder)

        return reminders

    def get_reminders(
        self,
        campaign_id: UUID | None = None,
        reviewer_id: UUID | None = None,
    ) -> list[ReviewReminder]:
        """Get reminders with optional filters."""
        reminders = self._reminders

        if campaign_id:
            reminders = [r for r in reminders if r.review_id == campaign_id]
        if reviewer_id:
            reminders = [r for r in reminders if r.reviewer_id == reviewer_id]

        return sorted(reminders, key=lambda r: r.sent_at, reverse=True)

    # Violations

    def record_violation(
        self,
        user_id: UUID,
        violation_type: str,
        description: str,
    ) -> AccessViolation:
        """Record an access violation."""
        violation = AccessViolation(
            id=uuid4(),
            user_id=user_id,
            violation_type=violation_type,
            description=description,
            detected_at=datetime.now(timezone.utc),
            resolved_at=None,
            resolved_by=None,
            resolution_notes=None,
        )

        self._violations.append(violation)
        return violation

    def resolve_violation(
        self,
        violation_id: UUID,
        resolved_by: UUID,
        notes: str,
    ) -> AccessViolation | None:
        """Resolve an access violation."""
        for violation in self._violations:
            if violation.id == violation_id:
                violation.resolved_at = datetime.now(timezone.utc)
                violation.resolved_by = resolved_by
                violation.resolution_notes = notes
                return violation
        return None

    def get_violations(
        self,
        user_id: UUID | None = None,
        unresolved_only: bool = False,
    ) -> list[AccessViolation]:
        """Get violations with optional filters."""
        violations = self._violations

        if user_id:
            violations = [v for v in violations if v.user_id == user_id]
        if unresolved_only:
            violations = [v for v in violations if v.resolved_at is None]

        return sorted(violations, key=lambda v: v.detected_at, reverse=True)

    # Automatic Checks

    def check_expired_attestations(self) -> list[Attestation]:
        """Check for expired attestations."""
        now = datetime.now(timezone.utc)
        expired = []

        for attestation in self._attestations.values():
            if attestation.status == AttestationStatus.PENDING:
                if attestation.expires_at < now:
                    attestation.status = AttestationStatus.EXPIRED
                    expired.append(attestation)

        return expired

    def check_unused_access(self, days_threshold: int = 90) -> list[tuple[UUID, AccessItem]]:
        """Find access items that haven't been used recently."""
        threshold = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        unused = []

        for user_id, user_access in self._user_access.items():
            for item in user_access.access_items:
                if item.is_active:
                    if item.last_used is None or item.last_used < threshold:
                        unused.append((user_id, item))

        return unused

    def check_excessive_access(self, max_items: int = 10) -> list[UserAccess]:
        """Find users with excessive access items."""
        return [
            u for u in self._user_access.values()
            if len([i for i in u.access_items if i.is_active]) > max_items
        ]

    # Reporting

    def get_campaign_summary(self, campaign_id: UUID) -> dict[str, Any] | None:
        """Get summary for a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        attestations = self.get_attestations_for_review(campaign_id)

        by_status = {}
        for status in AttestationStatus:
            by_status[status.value] = len([a for a in attestations if a.status == status])

        return {
            "campaign_id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status.value,
            "total_attestations": campaign.attestation_count,
            "completed": campaign.completed_count,
            "pending": by_status.get("pending", 0),
            "approved": by_status.get("approved", 0),
            "revoked": by_status.get("revoked", 0),
            "escalated": by_status.get("escalated", 0),
            "completion_rate": (
                campaign.completed_count / campaign.attestation_count
                if campaign.attestation_count > 0 else 0
            ),
            "days_remaining": max(0, (campaign.end_date - datetime.now(timezone.utc)).days),
        }

    def get_compliance_report(self) -> dict[str, Any]:
        """Generate a compliance report."""
        total_users = len(self._user_access)
        high_risk_users = len(self.get_high_risk_users())

        active_campaigns = self.get_campaigns(status=ReviewStatus.ACTIVE)
        completed_campaigns = self.get_campaigns(status=ReviewStatus.COMPLETED)

        total_violations = len(self._violations)
        open_violations = len(self.get_violations(unresolved_only=True))

        unused_access = len(self.check_unused_access())
        excessive_access = len(self.check_excessive_access())

        return {
            "total_users_reviewed": total_users,
            "high_risk_users": high_risk_users,
            "active_campaigns": len(active_campaigns),
            "completed_campaigns": len(completed_campaigns),
            "total_violations": total_violations,
            "open_violations": open_violations,
            "unused_access_items": unused_access,
            "users_with_excessive_access": excessive_access,
            "compliance_score": self._calculate_compliance_score(),
        }

    def _calculate_compliance_score(self) -> float:
        """Calculate overall compliance score (0-100)."""
        score = 100.0

        # Deduct for high risk users
        high_risk = len(self.get_high_risk_users())
        total_users = max(1, len(self._user_access))
        score -= (high_risk / total_users) * 20

        # Deduct for open violations
        open_violations = len(self.get_violations(unresolved_only=True))
        score -= min(30, open_violations * 5)

        # Deduct for unused access
        unused = len(self.check_unused_access())
        score -= min(20, unused * 2)

        # Deduct for overdue campaigns
        active = self.get_campaigns(status=ReviewStatus.ACTIVE)
        now = datetime.now(timezone.utc)
        overdue = [c for c in active if c.end_date < now]
        score -= len(overdue) * 10

        return max(0, score)

    def get_user_access_summary(self, user_id: UUID) -> dict[str, Any] | None:
        """Get access summary for a user."""
        user_access = self._user_access.get(user_id)
        if not user_access:
            return None

        active_items = [i for i in user_access.access_items if i.is_active]

        by_type = {}
        for access_type in AccessType:
            by_type[access_type.value] = len([
                i for i in active_items if i.access_type == access_type
            ])

        by_risk = {}
        for risk_level in RiskLevel:
            by_risk[risk_level.value] = len([
                i for i in active_items if i.risk_level == risk_level
            ])

        return {
            "user_id": str(user_id),
            "user_name": user_access.user_name,
            "total_access_items": len(active_items),
            "total_risk_score": user_access.total_risk_score,
            "by_type": by_type,
            "by_risk": by_risk,
            "violations": len(self.get_violations(user_id=user_id)),
        }

    # Schedule Management

    def get_schedule(self) -> dict[str, str]:
        """Get the review schedule for privileged roles."""
        return {role: freq.value for role, freq in self._review_schedules.items()}

    def update_schedule(self, role: str, frequency: ReviewFrequency) -> None:
        """Update review schedule for a role."""
        self._review_schedules[role] = frequency

    def get_due_reviews(self) -> list[str]:
        """Get roles due for review."""
        # In production, this would check last review dates
        return list(self._review_schedules.keys())

    def auto_create_campaigns(self) -> list[ReviewCampaign]:
        """Auto-create campaigns based on schedule."""
        campaigns = []

        for role, frequency in self._review_schedules.items():
            # Check if campaign already exists for this period
            existing = [
                c for c in self._campaigns.values()
                if role in c.target_roles and c.status in [ReviewStatus.DRAFT, ReviewStatus.ACTIVE]
            ]

            if not existing:
                campaign = self.create_campaign(
                    name=f"{role} Access Review",
                    description=f"Periodic access review for {role} users",
                    target_roles=[role],
                    reviewer_ids=[],
                    frequency=frequency,
                )
                campaigns.append(campaign)

        return campaigns


def get_access_review_service(session: AsyncSession) -> AccessReviewService:
    """Create an access review service wired to the database."""
    sync_session = session.sync_session
    return AccessReviewService(
        user_access_provider=build_user_access_provider(sync_session),
    )
