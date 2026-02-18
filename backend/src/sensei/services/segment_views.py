"""
Segment Views Service.

Provides workspace segmentation - saved list filters by module and user
with sharing, collaboration, and real-time filter updates.

For production use, see segment_views_db.py which provides
database-backed persistence with SQLAlchemy.

Features:
- Saved filter sets per module (RFQ, Quote, Opportunity, etc.)
- Personal, team, and shared segments
- Smart segments with dynamic criteria
- Segment sharing and collaboration
- Usage analytics and popular segments
- Quick-apply segment switching
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

# Re-export models/enums from the model module
from sensei.models.segment import (
    Segment,
    SegmentShare,
    SegmentUsage,
    SegmentModule,
    SegmentVisibility,
)
from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class FilterOperator(str, Enum):
    """Filter operators for criteria."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    DATE_BEFORE = "date_before"
    DATE_AFTER = "date_after"
    DATE_BETWEEN = "date_between"
    RELATIVE_DATE = "relative_date"


class LogicalOperator(str, Enum):
    """Logical operators for combining criteria."""
    AND = "and"
    OR = "or"


@dataclass
class FilterCriterion:
    """A single filter criterion."""
    field: str
    operator: FilterOperator
    value: Any
    display_name: str | None = None


@dataclass
class FilterGroup:
    """A group of filter criteria with a logical operator."""
    criteria: list[FilterCriterion]
    operator: LogicalOperator = LogicalOperator.AND


@dataclass
class SegmentSort:
    """Sorting configuration for a segment."""
    field: str
    direction: str = "asc"


@dataclass
class SegmentColumn:
    """Column configuration for segment display."""
    field: str
    label: str
    width: int | None = None
    visible: bool = True
    order: int = 0


@dataclass
class LegacySegment:
    """Legacy segment dataclass for backward compatibility."""
    id: UUID
    name: str
    description: str
    module: SegmentModule
    owner_id: UUID
    visibility: SegmentVisibility
    filter_groups: list[FilterGroup]
    columns: list[SegmentColumn]
    sort: SegmentSort | None
    color: str | None
    icon: str | None
    is_default: bool
    is_pinned: bool
    is_smart: bool
    created_at: datetime
    updated_at: datetime
    use_count: int = 0
    last_used_at: datetime | None = None
    shared_with: list[UUID] = field(default_factory=list)
    team_id: UUID | None = None
    department_id: UUID | None = None


@dataclass
class LegacySegmentShare:
    """Legacy segment share record."""
    id: UUID
    segment_id: UUID
    shared_by: UUID
    shared_with: UUID
    can_edit: bool
    created_at: datetime


@dataclass
class LegacySegmentUsage:
    """Usage analytics for a segment."""
    segment_id: UUID
    user_id: UUID
    used_at: datetime
    result_count: int


@dataclass
class SegmentApplyResult:
    """Result of applying a segment to data."""
    segment_id: UUID
    module: SegmentModule
    applied_criteria: list[FilterCriterion]
    result_count: int
    execution_time_ms: float


class SegmentViewsService(PersistentServiceMixin):
    """In-memory segment views service for testing and development.
    
    For production, use the database-backed service from segment_views_db.py.
    """

    SERVICE_NAME = "segment_views"
    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

    def __init__(self) -> None:
        """Initialize the segment views service."""
        self._segments: dict[UUID, LegacySegment] = {}
        self._shares: dict[UUID, LegacySegmentShare] = {}
        self._usage: list[LegacySegmentUsage] = []
        self._state_loaded = False
        self._initialize_default_segments()

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        segments_data = await self.load_state(self._DEFAULT_TENANT_ID, "segments")
        shares_data = await self.load_state(self._DEFAULT_TENANT_ID, "shares")
        usage_data = await self.load_state(self._DEFAULT_TENANT_ID, "usage")

        if segments_data is None and shares_data is None and usage_data is None:
            self._state_loaded = True
            return

        segments_data = segments_data or {}
        shares_data = shares_data or {}
        usage_data = usage_data or []

        self._segments = {
            UUID(segment_id): decode_dataclass(segment, LegacySegment)
            for segment_id, segment in segments_data.items()
        }
        self._shares = {
            UUID(share_id): decode_dataclass(share, LegacySegmentShare)
            for share_id, share in shares_data.items()
        }
        self._usage = [decode_dataclass(entry, LegacySegmentUsage) for entry in usage_data]
        self._state_loaded = True

    async def persist_all(self) -> None:
        segments_data = {
            str(segment_id): encode_dataclass(segment) for segment_id, segment in self._segments.items()
        }
        shares_data = {
            str(share_id): encode_dataclass(share) for share_id, share in self._shares.items()
        }
        usage_data = [encode_dataclass(entry) for entry in self._usage]

        await self.save_state(self._DEFAULT_TENANT_ID, "segments", segments_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "shares", shares_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "usage", usage_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    def _initialize_default_segments(self) -> None:
        """Initialize default system segments."""
        system_user_id = UUID("00000000-0000-0000-0000-000000000001")

        # RFQ Default Segments
        self._create_default_segment(
            name="Open RFQs",
            description="All RFQs that are not yet quoted",
            module=SegmentModule.RFQ,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.IN,
                            value=["new", "in_review", "awaiting_info"],
                        )
                    ]
                )
            ],
            color="#3B82F6",
            icon="inbox",
        )

        self._create_default_segment(
            name="High Priority RFQs",
            description="RFQs marked as high priority",
            module=SegmentModule.RFQ,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="priority",
                            operator=FilterOperator.EQUALS,
                            value="high",
                        ),
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.NOT_EQUALS,
                            value="closed",
                        ),
                    ]
                )
            ],
            color="#EF4444",
            icon="flag",
        )

        self._create_default_segment(
            name="Overdue RFQs",
            description="RFQs past their due date",
            module=SegmentModule.RFQ,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="due_date",
                            operator=FilterOperator.DATE_BEFORE,
                            value="today",
                        ),
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.NOT_IN,
                            value=["completed", "closed", "cancelled"],
                        ),
                    ]
                )
            ],
            color="#DC2626",
            icon="clock",
            is_smart=True,
        )

        # Quote Default Segments
        self._create_default_segment(
            name="Draft Quotes",
            description="Quotes in draft status",
            module=SegmentModule.QUOTE,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="draft",
                        )
                    ]
                )
            ],
            color="#F59E0B",
            icon="pencil",
        )

        self._create_default_segment(
            name="Low Margin Quotes",
            description="Quotes with margin below 15%",
            module=SegmentModule.QUOTE,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="margin",
                            operator=FilterOperator.LESS_THAN,
                            value=15.0,
                        )
                    ]
                )
            ],
            color="#DC2626",
            icon="trending-down",
        )

        self._create_default_segment(
            name="Pending Approval",
            description="Quotes awaiting approval",
            module=SegmentModule.QUOTE,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="pending_approval",
                        )
                    ]
                )
            ],
            color="#8B5CF6",
            icon="hourglass",
        )

        # Opportunity Default Segments
        self._create_default_segment(
            name="Hot Opportunities",
            description="High probability opportunities",
            module=SegmentModule.OPPORTUNITY,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="probability",
                            operator=FilterOperator.GREATER_THAN_OR_EQUAL,
                            value=70,
                        ),
                        FilterCriterion(
                            field="stage",
                            operator=FilterOperator.NOT_IN,
                            value=["won", "lost", "cancelled"],
                        ),
                    ]
                )
            ],
            color="#F59E0B",
            icon="fire",
        )

        self._create_default_segment(
            name="Closing This Month",
            description="Opportunities expected to close this month",
            module=SegmentModule.OPPORTUNITY,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="expected_close_date",
                            operator=FilterOperator.RELATIVE_DATE,
                            value="this_month",
                        ),
                        FilterCriterion(
                            field="stage",
                            operator=FilterOperator.NOT_IN,
                            value=["won", "lost"],
                        ),
                    ]
                )
            ],
            color="#10B981",
            icon="calendar",
            is_smart=True,
        )

        # Work Order Default Segments
        self._create_default_segment(
            name="Open Work Orders",
            description="Work orders in progress",
            module=SegmentModule.WORK_ORDER,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.IN,
                            value=["open", "in_progress"],
                        )
                    ]
                )
            ],
            color="#3B82F6",
            icon="wrench",
        )

        self._create_default_segment(
            name="Behind Schedule",
            description="Work orders behind schedule",
            module=SegmentModule.WORK_ORDER,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="scheduled_end_date",
                            operator=FilterOperator.DATE_BEFORE,
                            value="today",
                        ),
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.NOT_EQUALS,
                            value="completed",
                        ),
                    ]
                )
            ],
            color="#DC2626",
            icon="alert-triangle",
            is_smart=True,
        )

        # Andon Default Segments
        self._create_default_segment(
            name="Active Andons",
            description="Currently active Andon events",
            module=SegmentModule.ANDON,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="active",
                        )
                    ]
                )
            ],
            color="#DC2626",
            icon="bell",
        )

        self._create_default_segment(
            name="Escalated Issues",
            description="Andon events that have been escalated",
            module=SegmentModule.ANDON,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="is_escalated",
                            operator=FilterOperator.EQUALS,
                            value=True,
                        )
                    ]
                )
            ],
            color="#8B5CF6",
            icon="arrow-up",
        )

        # CAPA Default Segments
        self._create_default_segment(
            name="Open CAPAs",
            description="CAPAs in progress",
            module=SegmentModule.CAPA,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.IN,
                            value=["open", "investigation", "action_required"],
                        )
                    ]
                )
            ],
            color="#F59E0B",
            icon="clipboard-check",
        )

        self._create_default_segment(
            name="Overdue CAPAs",
            description="CAPAs past their due date",
            module=SegmentModule.CAPA,
            owner_id=system_user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="due_date",
                            operator=FilterOperator.DATE_BEFORE,
                            value="today",
                        ),
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.NOT_EQUALS,
                            value="closed",
                        ),
                    ]
                )
            ],
            color="#DC2626",
            icon="clock",
            is_smart=True,
        )

    def _create_default_segment(
        self,
        name: str,
        description: str,
        module: SegmentModule,
        owner_id: UUID,
        filter_groups: list[FilterGroup],
        color: str | None = None,
        icon: str | None = None,
        is_smart: bool = False,
    ) -> LegacySegment:
        """Create a default segment."""
        now = datetime.now(timezone.utc)
        segment = LegacySegment(
            id=uuid4(),
            name=name,
            description=description,
            module=module,
            owner_id=owner_id,
            visibility=SegmentVisibility.ORGANIZATION,
            filter_groups=filter_groups,
            columns=[],
            sort=None,
            color=color,
            icon=icon,
            is_default=True,
            is_pinned=False,
            is_smart=is_smart,
            created_at=now,
            updated_at=now,
        )
        self._segments[segment.id] = segment
        return segment

    def create_segment(
        self,
        name: str,
        description: str,
        module: SegmentModule,
        owner_id: UUID,
        filter_groups: list[FilterGroup],
        visibility: SegmentVisibility = SegmentVisibility.PRIVATE,
        columns: list[SegmentColumn] | None = None,
        sort: SegmentSort | None = None,
        color: str | None = None,
        icon: str | None = None,
        is_pinned: bool = False,
        is_smart: bool = False,
        team_id: UUID | None = None,
        department_id: UUID | None = None,
    ) -> LegacySegment:
        """Create a new segment."""
        now = datetime.now(timezone.utc)
        segment = LegacySegment(
            id=uuid4(),
            name=name,
            description=description,
            module=module,
            owner_id=owner_id,
            visibility=visibility,
            filter_groups=filter_groups,
            columns=columns or [],
            sort=sort,
            color=color,
            icon=icon,
            is_default=False,
            is_pinned=is_pinned,
            is_smart=is_smart,
            created_at=now,
            updated_at=now,
            team_id=team_id,
            department_id=department_id,
        )
        self._segments[segment.id] = segment
        return segment

    async def create_segment_async(self, **kwargs: Any) -> LegacySegment:
        await self._ensure_loaded()
        segment = self.create_segment(**kwargs)
        await self.persist_all()
        return segment

    def get_segment(self, segment_id: UUID) -> LegacySegment | None:
        """Get a segment by ID."""
        return self._segments.get(segment_id)

    async def get_segment_async(self, segment_id: UUID) -> LegacySegment | None:
        await self._ensure_loaded()
        return self.get_segment(segment_id)

    def get_segment_by_name(
        self, name: str, module: SegmentModule, owner_id: UUID | None = None
    ) -> LegacySegment | None:
        """Get a segment by name and module."""
        for segment in self._segments.values():
            if segment.name == name and segment.module == module:
                if owner_id is None or segment.owner_id == owner_id:
                    return segment
        return None

    async def get_segment_by_name_async(
        self,
        name: str,
        module: SegmentModule,
        owner_id: UUID | None = None,
    ) -> LegacySegment | None:
        await self._ensure_loaded()
        return self.get_segment_by_name(name=name, module=module, owner_id=owner_id)

    def get_segments(
        self,
        module: SegmentModule | None = None,
        owner_id: UUID | None = None,
        visibility: SegmentVisibility | None = None,
        include_shared: bool = True,
        include_defaults: bool = True,
        pinned_only: bool = False,
        smart_only: bool = False,
    ) -> list[LegacySegment]:
        """Get segments with optional filtering."""
        segments = []
        for segment in self._segments.values():
            if module and segment.module != module:
                continue
            if visibility and segment.visibility != visibility:
                continue
            if not include_defaults and segment.is_default:
                continue
            if owner_id:
                is_owner = segment.owner_id == owner_id
                is_shared = owner_id in segment.shared_with
                if not is_owner and not (include_shared and is_shared):
                    if segment.visibility not in [
                        SegmentVisibility.ORGANIZATION,
                        SegmentVisibility.DEPARTMENT,
                    ]:
                        continue
            if pinned_only and not segment.is_pinned:
                continue
            if smart_only and not segment.is_smart:
                continue
            segments.append(segment)
        return segments

    async def get_segments_async(self, **kwargs: Any) -> list[LegacySegment]:
        await self._ensure_loaded()
        return self.get_segments(**kwargs)

    def update_segment(
        self,
        segment_id: UUID,
        name: str | None = None,
        description: str | None = None,
        filter_groups: list[FilterGroup] | None = None,
        columns: list[SegmentColumn] | None = None,
        sort: SegmentSort | None = None,
        visibility: SegmentVisibility | None = None,
        color: str | None = None,
        icon: str | None = None,
        is_pinned: bool | None = None,
        is_smart: bool | None = None,
    ) -> LegacySegment | None:
        """Update a segment."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        if name is not None:
            segment.name = name
        if description is not None:
            segment.description = description
        if filter_groups is not None:
            segment.filter_groups = filter_groups
        if columns is not None:
            segment.columns = columns
        if sort is not None:
            segment.sort = sort
        if visibility is not None:
            segment.visibility = visibility
        if color is not None:
            segment.color = color
        if icon is not None:
            segment.icon = icon
        if is_pinned is not None:
            segment.is_pinned = is_pinned
        if is_smart is not None:
            segment.is_smart = is_smart
        segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def update_segment_async(self, **kwargs: Any) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.update_segment(**kwargs)
        await self.persist_all()
        return segment

    def delete_segment(self, segment_id: UUID) -> bool:
        """Delete a segment."""
        if segment_id in self._segments:
            shares_to_remove = [
                s_id for s_id, s in self._shares.items() if s.segment_id == segment_id
            ]
            for share_id in shares_to_remove:
                del self._shares[share_id]
            del self._segments[segment_id]
            return True
        return False

    async def delete_segment_async(self, segment_id: UUID) -> bool:
        await self._ensure_loaded()
        result = self.delete_segment(segment_id)
        await self.persist_all()
        return result

    def duplicate_segment(
        self,
        segment_id: UUID,
        new_name: str,
        new_owner_id: UUID,
    ) -> LegacySegment | None:
        """Duplicate a segment for a user."""
        original = self._segments.get(segment_id)
        if not original:
            return None
        return self.create_segment(
            name=new_name,
            description=original.description,
            module=original.module,
            owner_id=new_owner_id,
            filter_groups=original.filter_groups.copy(),
            visibility=SegmentVisibility.PRIVATE,
            columns=original.columns.copy(),
            sort=original.sort,
            color=original.color,
            icon=original.icon,
            is_smart=original.is_smart,
        )

    async def duplicate_segment_async(self, **kwargs: Any) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.duplicate_segment(**kwargs)
        await self.persist_all()
        return segment

    def share_segment(
        self,
        segment_id: UUID,
        shared_by: UUID,
        shared_with: UUID,
        can_edit: bool = False,
    ) -> LegacySegmentShare | None:
        """Share a segment with another user."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        for share in self._shares.values():
            if share.segment_id == segment_id and share.shared_with == shared_with:
                share.can_edit = can_edit
                return share
        share = LegacySegmentShare(
            id=uuid4(),
            segment_id=segment_id,
            shared_by=shared_by,
            shared_with=shared_with,
            can_edit=can_edit,
            created_at=datetime.now(timezone.utc),
        )
        self._shares[share.id] = share
        segment.shared_with.append(shared_with)
        return share

    async def share_segment_async(self, **kwargs: Any) -> LegacySegmentShare | None:
        await self._ensure_loaded()
        share = self.share_segment(**kwargs)
        await self.persist_all()
        return share

    def unshare_segment(self, segment_id: UUID, user_id: UUID) -> bool:
        """Remove segment share for a user."""
        segment = self._segments.get(segment_id)
        if not segment:
            return False
        share_to_remove = None
        for share_id, share in self._shares.items():
            if share.segment_id == segment_id and share.shared_with == user_id:
                share_to_remove = share_id
                break
        if share_to_remove:
            del self._shares[share_to_remove]
            if user_id in segment.shared_with:
                segment.shared_with.remove(user_id)
            return True
        return False

    async def unshare_segment_async(self, segment_id: UUID, user_id: UUID) -> bool:
        await self._ensure_loaded()
        result = self.unshare_segment(segment_id, user_id)
        await self.persist_all()
        return result

    def get_shares(
        self, segment_id: UUID | None = None, user_id: UUID | None = None
    ) -> list[LegacySegmentShare]:
        """Get shares for a segment or user."""
        shares = []
        for share in self._shares.values():
            if segment_id and share.segment_id != segment_id:
                continue
            if user_id and share.shared_with != user_id:
                continue
            shares.append(share)
        return shares

    async def get_shares_async(self, **kwargs: Any) -> list[LegacySegmentShare]:
        await self._ensure_loaded()
        return self.get_shares(**kwargs)

    def set_default_segment(
        self, segment_id: UUID, user_id: UUID, module: SegmentModule
    ) -> bool:
        """Set a segment as the default for a user/module."""
        segment = self._segments.get(segment_id)
        if not segment or segment.module != module:
            return False
        for s in self._segments.values():
            if s.module == module and s.owner_id == user_id and s.is_default:
                s.is_default = False
        segment.is_default = True
        return True

    async def set_default_segment_async(self, **kwargs: Any) -> bool:
        await self._ensure_loaded()
        result = self.set_default_segment(**kwargs)
        await self.persist_all()
        return result

    def get_default_segment(
        self, user_id: UUID, module: SegmentModule
    ) -> LegacySegment | None:
        """Get the default segment for a user/module."""
        for segment in self._segments.values():
            if (
                segment.module == module
                and segment.owner_id == user_id
                and segment.is_default
            ):
                return segment
        return None

    async def get_default_segment_async(
        self, user_id: UUID, module: SegmentModule
    ) -> LegacySegment | None:
        await self._ensure_loaded()
        return self.get_default_segment(user_id, module)

    def pin_segment(self, segment_id: UUID) -> LegacySegment | None:
        """Pin a segment for quick access."""
        segment = self._segments.get(segment_id)
        if segment:
            segment.is_pinned = True
            segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def pin_segment_async(self, segment_id: UUID) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.pin_segment(segment_id)
        await self.persist_all()
        return segment

    def unpin_segment(self, segment_id: UUID) -> LegacySegment | None:
        """Unpin a segment."""
        segment = self._segments.get(segment_id)
        if segment:
            segment.is_pinned = False
            segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def unpin_segment_async(self, segment_id: UUID) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.unpin_segment(segment_id)
        await self.persist_all()
        return segment

    def record_usage(
        self, segment_id: UUID, user_id: UUID, result_count: int
    ) -> LegacySegmentUsage | None:
        """Record usage of a segment."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        now = datetime.now(timezone.utc)
        usage = LegacySegmentUsage(
            segment_id=segment_id,
            user_id=user_id,
            used_at=now,
            result_count=result_count,
        )
        self._usage.append(usage)
        segment.use_count += 1
        segment.last_used_at = now
        return usage

    async def record_usage_async(
        self, segment_id: UUID, user_id: UUID, result_count: int
    ) -> LegacySegmentUsage | None:
        await self._ensure_loaded()
        usage = self.record_usage(segment_id, user_id, result_count)
        await self.persist_all()
        return usage

    def get_usage_stats(
        self,
        segment_id: UUID | None = None,
        user_id: UUID | None = None,
        limit: int = 100,
    ) -> list[LegacySegmentUsage]:
        """Get usage statistics."""
        usages = []
        for usage in self._usage:
            if segment_id and usage.segment_id != segment_id:
                continue
            if user_id and usage.user_id != user_id:
                continue
            usages.append(usage)
        usages.sort(key=lambda u: u.used_at, reverse=True)
        return usages[:limit]

    async def get_usage_stats_async(self, **kwargs: Any) -> list[LegacySegmentUsage]:
        await self._ensure_loaded()
        return self.get_usage_stats(**kwargs)

    def get_popular_segments(
        self, module: SegmentModule | None = None, limit: int = 10
    ) -> list[LegacySegment]:
        """Get most popular segments by usage."""
        segments = self.get_segments(module=module)
        segments.sort(key=lambda s: s.use_count, reverse=True)
        return segments[:limit]

    async def get_popular_segments_async(self, **kwargs: Any) -> list[LegacySegment]:
        await self._ensure_loaded()
        return self.get_popular_segments(**kwargs)

    def get_recent_segments(
        self, user_id: UUID, module: SegmentModule | None = None, limit: int = 5
    ) -> list[LegacySegment]:
        """Get recently used segments for a user."""
        user_usage = [u for u in self._usage if u.user_id == user_id]
        user_usage.sort(key=lambda u: u.used_at, reverse=True)
        seen: set[UUID] = set()
        segments = []
        for usage in user_usage:
            if usage.segment_id in seen:
                continue
            segment = self._segments.get(usage.segment_id)
            if segment and (module is None or segment.module == module):
                segments.append(segment)
                seen.add(usage.segment_id)
                if len(segments) >= limit:
                    break
        return segments

    async def get_recent_segments_async(self, **kwargs: Any) -> list[LegacySegment]:
        await self._ensure_loaded()
        return self.get_recent_segments(**kwargs)

    def apply_segment(
        self, segment_id: UUID, data: list[dict[str, Any]]
    ) -> SegmentApplyResult:
        """Apply a segment's filters to data and return matching items."""
        import time
        start_time = time.time()
        segment = self._segments.get(segment_id)
        if not segment:
            return SegmentApplyResult(
                segment_id=segment_id,
                module=SegmentModule.RFQ,
                applied_criteria=[],
                result_count=0,
                execution_time_ms=0.0,
            )
        all_criteria: list[FilterCriterion] = []
        for group in segment.filter_groups:
            all_criteria.extend(group.criteria)
        filtered_data = self._apply_filters(data, segment.filter_groups)
        execution_time = (time.time() - start_time) * 1000
        return SegmentApplyResult(
            segment_id=segment_id,
            module=segment.module,
            applied_criteria=all_criteria,
            result_count=len(filtered_data),
            execution_time_ms=execution_time,
        )

    async def apply_segment_async(self, **kwargs: Any) -> SegmentApplyResult:
        await self._ensure_loaded()
        return self.apply_segment(**kwargs)

    def _apply_filters(
        self, data: list[dict[str, Any]], filter_groups: list[FilterGroup]
    ) -> list[dict[str, Any]]:
        """Apply filter groups to data."""
        if not filter_groups:
            return data
        result = []
        for item in data:
            matches_all_groups = True
            for group in filter_groups:
                group_match = self._evaluate_group(item, group)
                if not group_match:
                    matches_all_groups = False
                    break
            if matches_all_groups:
                result.append(item)
        return result

    def _evaluate_group(self, item: dict[str, Any], group: FilterGroup) -> bool:
        """Evaluate a filter group against an item."""
        if not group.criteria:
            return True
        if group.operator == LogicalOperator.AND:
            return all(self._evaluate_criterion(item, c) for c in group.criteria)
        else:
            return any(self._evaluate_criterion(item, c) for c in group.criteria)

    def _evaluate_criterion(self, item: dict[str, Any], criterion: FilterCriterion) -> bool:
        """Evaluate a single criterion against an item."""
        value = item.get(criterion.field)
        target = criterion.value
        match criterion.operator:
            case FilterOperator.EQUALS:
                return value == target
            case FilterOperator.NOT_EQUALS:
                return value != target
            case FilterOperator.CONTAINS:
                return str(target).lower() in str(value).lower() if value else False
            case FilterOperator.NOT_CONTAINS:
                return str(target).lower() not in str(value).lower() if value else True
            case FilterOperator.STARTS_WITH:
                return str(value).startswith(target) if value else False
            case FilterOperator.ENDS_WITH:
                return str(value).endswith(target) if value else False
            case FilterOperator.GREATER_THAN:
                return value > target if value is not None else False
            case FilterOperator.GREATER_THAN_OR_EQUAL:
                return value >= target if value is not None else False
            case FilterOperator.LESS_THAN:
                return value < target if value is not None else False
            case FilterOperator.LESS_THAN_OR_EQUAL:
                return value <= target if value is not None else False
            case FilterOperator.IN:
                return value in target if isinstance(target, list) else value == target
            case FilterOperator.NOT_IN:
                return value not in target if isinstance(target, list) else value != target
            case FilterOperator.IS_NULL:
                return value is None
            case FilterOperator.IS_NOT_NULL:
                return value is not None
            case FilterOperator.BETWEEN:
                if isinstance(target, list) and len(target) == 2:
                    return target[0] <= value <= target[1] if value is not None else False
                return False
            case _:
                return True

    def add_criterion_to_segment(
        self, segment_id: UUID, group_index: int, criterion: FilterCriterion
    ) -> LegacySegment | None:
        """Add a criterion to a filter group."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        if 0 <= group_index < len(segment.filter_groups):
            segment.filter_groups[group_index].criteria.append(criterion)
            segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def add_criterion_to_segment_async(self, **kwargs: Any) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.add_criterion_to_segment(**kwargs)
        await self.persist_all()
        return segment

    def remove_criterion_from_segment(
        self, segment_id: UUID, group_index: int, criterion_index: int
    ) -> LegacySegment | None:
        """Remove a criterion from a filter group."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        if 0 <= group_index < len(segment.filter_groups):
            group = segment.filter_groups[group_index]
            if 0 <= criterion_index < len(group.criteria):
                group.criteria.pop(criterion_index)
                segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def remove_criterion_from_segment_async(self, **kwargs: Any) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.remove_criterion_from_segment(**kwargs)
        await self.persist_all()
        return segment

    def add_filter_group(
        self, segment_id: UUID, operator: LogicalOperator = LogicalOperator.AND
    ) -> LegacySegment | None:
        """Add a new filter group to a segment."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        segment.filter_groups.append(FilterGroup(criteria=[], operator=operator))
        segment.updated_at = datetime.now(timezone.utc)
        return segment

    async def add_filter_group_async(self, **kwargs: Any) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.add_filter_group(**kwargs)
        await self.persist_all()
        return segment

    def export_segment(self, segment_id: UUID) -> dict[str, Any] | None:
        """Export a segment to a portable format."""
        segment = self._segments.get(segment_id)
        if not segment:
            return None
        return {
            "name": segment.name,
            "description": segment.description,
            "module": segment.module.value,
            "visibility": segment.visibility.value,
            "filter_groups": [
                {
                    "operator": group.operator.value,
                    "criteria": [
                        {
                            "field": c.field,
                            "operator": c.operator.value,
                            "value": c.value,
                            "display_name": c.display_name,
                        }
                        for c in group.criteria
                    ],
                }
                for group in segment.filter_groups
            ],
            "columns": [
                {
                    "field": col.field,
                    "label": col.label,
                    "width": col.width,
                    "visible": col.visible,
                    "order": col.order,
                }
                for col in segment.columns
            ],
            "sort": {"field": segment.sort.field, "direction": segment.sort.direction}
            if segment.sort else None,
            "color": segment.color,
            "icon": segment.icon,
            "is_smart": segment.is_smart,
        }

    async def export_segment_async(self, segment_id: UUID) -> dict[str, Any] | None:
        await self._ensure_loaded()
        return self.export_segment(segment_id)

    def import_segment(self, data: dict[str, Any], owner_id: UUID) -> LegacySegment | None:
        """Import a segment from exported data."""
        try:
            filter_groups = []
            for group_data in data.get("filter_groups", []):
                criteria = []
                for c in group_data.get("criteria", []):
                    criteria.append(
                        FilterCriterion(
                            field=c["field"],
                            operator=FilterOperator(c["operator"]),
                            value=c["value"],
                            display_name=c.get("display_name"),
                        )
                    )
                filter_groups.append(
                    FilterGroup(
                        criteria=criteria,
                        operator=LogicalOperator(group_data.get("operator", "and")),
                    )
                )
            columns = []
            for col in data.get("columns", []):
                columns.append(
                    SegmentColumn(
                        field=col["field"],
                        label=col["label"],
                        width=col.get("width"),
                        visible=col.get("visible", True),
                        order=col.get("order", 0),
                    )
                )
            sort = None
            if data.get("sort"):
                sort = SegmentSort(
                    field=data["sort"]["field"],
                    direction=data["sort"].get("direction", "asc"),
                )
            return self.create_segment(
                name=data["name"],
                description=data.get("description", ""),
                module=SegmentModule(data["module"]),
                owner_id=owner_id,
                filter_groups=filter_groups,
                visibility=SegmentVisibility(data.get("visibility", "private")),
                columns=columns,
                sort=sort,
                color=data.get("color"),
                icon=data.get("icon"),
                is_smart=data.get("is_smart", False),
            )
        except (KeyError, ValueError):
            return None

    async def import_segment_async(
        self, data: dict[str, Any], owner_id: UUID
    ) -> LegacySegment | None:
        await self._ensure_loaded()
        segment = self.import_segment(data, owner_id)
        await self.persist_all()
        return segment

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of segments in the system."""
        by_module: dict[str, int] = {}
        by_visibility: dict[str, int] = {}
        total_usage = 0
        for segment in self._segments.values():
            module = segment.module.value
            visibility = segment.visibility.value
            by_module[module] = by_module.get(module, 0) + 1
            by_visibility[visibility] = by_visibility.get(visibility, 0) + 1
            total_usage += segment.use_count
        return {
            "total_segments": len(self._segments),
            "default_segments": len([s for s in self._segments.values() if s.is_default]),
            "smart_segments": len([s for s in self._segments.values() if s.is_smart]),
            "by_module": by_module,
            "by_visibility": by_visibility,
            "total_shares": len(self._shares),
            "total_usage": total_usage,
        }

    async def get_summary_async(self) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.get_summary()


# Re-export database-backed service for production use
from sensei.services.segment_views_db import (
    SegmentViewsService as DBSegmentViewsService,
    get_segment_views_service,
)


__all__ = [
    # In-memory service (for testing)
    "SegmentViewsService",
    # DB-backed service (for production)
    "DBSegmentViewsService",
    "get_segment_views_service",
    # Data classes
    "FilterCriterion",
    "FilterGroup",
    "FilterOperator",
    "LogicalOperator",
    "SegmentSort",
    "SegmentColumn",
    "SegmentApplyResult",
    # Models
    "Segment",
    "SegmentShare",
    "SegmentUsage",
    "SegmentModule",
    "SegmentVisibility",
]
