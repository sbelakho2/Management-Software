"""
Tests for Segment Views Service.

Verifies:
- Default segment creation
- Segment CRUD operations
- Filtering and visibility
- Sharing and collaboration
- Usage tracking
- Filter evaluation
- Export/Import
"""

from uuid import uuid4

import pytest

from sensei.services.segment_views import (
    FilterCriterion,
    FilterGroup,
    FilterOperator,
    LogicalOperator,
    SegmentColumn,
    SegmentModule,
    SegmentSort,
    SegmentViewsService,
    SegmentVisibility,
)


class TestDefaultSegments:
    """Tests for default segment creation."""

    def test_default_segments_exist(self) -> None:
        """Test that default segments are created."""
        service = SegmentViewsService()

        segments = service.get_segments()

        assert len(segments) > 0

    def test_open_rfqs_segment(self) -> None:
        """Test Open RFQs default segment."""
        service = SegmentViewsService()

        segment = service.get_segment_by_name("Open RFQs", SegmentModule.RFQ)

        assert segment is not None
        assert segment.module == SegmentModule.RFQ
        assert segment.is_default is True

    def test_high_priority_rfqs_segment(self) -> None:
        """Test High Priority RFQs segment."""
        service = SegmentViewsService()

        segment = service.get_segment_by_name("High Priority RFQs", SegmentModule.RFQ)

        assert segment is not None
        assert len(segment.filter_groups) > 0

    def test_overdue_rfqs_is_smart(self) -> None:
        """Test that Overdue RFQs is a smart segment."""
        service = SegmentViewsService()

        segment = service.get_segment_by_name("Overdue RFQs", SegmentModule.RFQ)

        assert segment is not None
        assert segment.is_smart is True

    def test_quote_segments_exist(self) -> None:
        """Test that quote segments exist."""
        service = SegmentViewsService()

        draft = service.get_segment_by_name("Draft Quotes", SegmentModule.QUOTE)
        low_margin = service.get_segment_by_name("Low Margin Quotes", SegmentModule.QUOTE)

        assert draft is not None
        assert low_margin is not None

    def test_opportunity_segments_exist(self) -> None:
        """Test that opportunity segments exist."""
        service = SegmentViewsService()

        hot = service.get_segment_by_name("Hot Opportunities", SegmentModule.OPPORTUNITY)

        assert hot is not None

    def test_andon_segments_exist(self) -> None:
        """Test that Andon segments exist."""
        service = SegmentViewsService()

        active = service.get_segment_by_name("Active Andons", SegmentModule.ANDON)

        assert active is not None


class TestSegmentCreation:
    """Tests for segment creation."""

    def test_create_segment(self) -> None:
        """Test creating a new segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="My Segment",
            description="Test segment",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        )
                    ]
                )
            ],
        )

        assert segment.id is not None
        assert segment.name == "My Segment"
        assert segment.owner_id == user_id
        assert segment.is_default is False

    def test_create_segment_with_visibility(self) -> None:
        """Test creating segment with visibility."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Team Segment",
            description="Shared with team",
            module=SegmentModule.QUOTE,
            owner_id=user_id,
            filter_groups=[],
            visibility=SegmentVisibility.TEAM,
        )

        assert segment.visibility == SegmentVisibility.TEAM

    def test_create_segment_with_columns(self) -> None:
        """Test creating segment with column configuration."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="With Columns",
            description="Has columns",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
            columns=[
                SegmentColumn(field="name", label="Name", order=0),
                SegmentColumn(field="status", label="Status", order=1),
            ],
        )

        assert len(segment.columns) == 2

    def test_create_segment_with_sort(self) -> None:
        """Test creating segment with sorting."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Sorted",
            description="Has sorting",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
            sort=SegmentSort(field="created_at", direction="desc"),
        )

        assert segment.sort is not None
        assert segment.sort.direction == "desc"


class TestSegmentRetrieval:
    """Tests for segment retrieval."""

    def test_get_segment(self) -> None:
        """Test getting segment by ID."""
        service = SegmentViewsService()
        user_id = uuid4()

        created = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        retrieved = service.get_segment(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_segment_by_name(self) -> None:
        """Test getting segment by name."""
        service = SegmentViewsService()
        user_id = uuid4()

        service.create_segment(
            name="Unique Name",
            description="Test",
            module=SegmentModule.QUOTE,
            owner_id=user_id,
            filter_groups=[],
        )

        retrieved = service.get_segment_by_name("Unique Name", SegmentModule.QUOTE)

        assert retrieved is not None

    def test_get_nonexistent_segment(self) -> None:
        """Test getting non-existent segment."""
        service = SegmentViewsService()

        result = service.get_segment(uuid4())

        assert result is None


class TestSegmentFiltering:
    """Tests for segment filtering."""

    def test_filter_by_module(self) -> None:
        """Test filtering segments by module."""
        service = SegmentViewsService()

        rfq_segments = service.get_segments(module=SegmentModule.RFQ)
        quote_segments = service.get_segments(module=SegmentModule.QUOTE)

        assert all(s.module == SegmentModule.RFQ for s in rfq_segments)
        assert all(s.module == SegmentModule.QUOTE for s in quote_segments)

    def test_filter_by_visibility(self) -> None:
        """Test filtering by visibility."""
        service = SegmentViewsService()

        org_segments = service.get_segments(visibility=SegmentVisibility.ORGANIZATION)

        assert all(
            s.visibility == SegmentVisibility.ORGANIZATION for s in org_segments
        )

    def test_exclude_defaults(self) -> None:
        """Test excluding default segments."""
        service = SegmentViewsService()
        user_id = uuid4()

        # Create a non-default segment
        service.create_segment(
            name="Custom",
            description="Custom segment",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        with_defaults = service.get_segments(include_defaults=True)
        without_defaults = service.get_segments(include_defaults=False)

        assert len(without_defaults) < len(with_defaults)

    def test_filter_pinned(self) -> None:
        """Test filtering pinned segments."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Pinned",
            description="Pinned segment",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
            is_pinned=True,
        )

        pinned = service.get_segments(pinned_only=True)

        assert segment.id in [s.id for s in pinned]

    def test_filter_smart(self) -> None:
        """Test filtering smart segments."""
        service = SegmentViewsService()

        smart = service.get_segments(smart_only=True)

        assert len(smart) > 0
        assert all(s.is_smart for s in smart)


class TestSegmentUpdate:
    """Tests for segment update."""

    def test_update_segment_name(self) -> None:
        """Test updating segment name."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Original",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        updated = service.update_segment(segment.id, name="Updated Name")

        assert updated is not None
        assert updated.name == "Updated Name"

    def test_update_segment_filters(self) -> None:
        """Test updating segment filters."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        new_filters = [
            FilterGroup(
                criteria=[
                    FilterCriterion(
                        field="priority",
                        operator=FilterOperator.EQUALS,
                        value="high",
                    )
                ]
            )
        ]

        updated = service.update_segment(segment.id, filter_groups=new_filters)

        assert updated is not None
        assert len(updated.filter_groups) == 1

    def test_update_nonexistent_segment(self) -> None:
        """Test updating non-existent segment."""
        service = SegmentViewsService()

        result = service.update_segment(uuid4(), name="New Name")

        assert result is None


class TestSegmentDeletion:
    """Tests for segment deletion."""

    def test_delete_segment(self) -> None:
        """Test deleting a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="To Delete",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        result = service.delete_segment(segment.id)

        assert result is True
        assert service.get_segment(segment.id) is None

    def test_delete_nonexistent_segment(self) -> None:
        """Test deleting non-existent segment."""
        service = SegmentViewsService()

        result = service.delete_segment(uuid4())

        assert result is False


class TestSegmentDuplication:
    """Tests for segment duplication."""

    def test_duplicate_segment(self) -> None:
        """Test duplicating a segment."""
        service = SegmentViewsService()
        user_id = uuid4()
        new_user_id = uuid4()

        original = service.create_segment(
            name="Original",
            description="Original segment",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        )
                    ]
                )
            ],
            color="#FF0000",
        )

        duplicate = service.duplicate_segment(
            original.id, "Copy of Original", new_user_id
        )

        assert duplicate is not None
        assert duplicate.name == "Copy of Original"
        assert duplicate.owner_id == new_user_id
        assert duplicate.color == original.color

    def test_duplicate_nonexistent_segment(self) -> None:
        """Test duplicating non-existent segment."""
        service = SegmentViewsService()

        result = service.duplicate_segment(uuid4(), "Copy", uuid4())

        assert result is None


class TestSegmentSharing:
    """Tests for segment sharing."""

    def test_share_segment(self) -> None:
        """Test sharing a segment."""
        service = SegmentViewsService()
        owner_id = uuid4()
        share_user_id = uuid4()

        segment = service.create_segment(
            name="Shared Segment",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=owner_id,
            filter_groups=[],
        )

        share = service.share_segment(
            segment.id, owner_id, share_user_id, can_edit=True
        )

        assert share is not None
        assert share.shared_with == share_user_id
        assert share.can_edit is True

    def test_share_updates_segment(self) -> None:
        """Test that sharing updates segment shared_with list."""
        service = SegmentViewsService()
        owner_id = uuid4()
        share_user_id = uuid4()

        segment = service.create_segment(
            name="Shared Segment",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=owner_id,
            filter_groups=[],
        )

        service.share_segment(segment.id, owner_id, share_user_id)

        updated = service.get_segment(segment.id)
        assert share_user_id in updated.shared_with

    def test_unshare_segment(self) -> None:
        """Test unsharing a segment."""
        service = SegmentViewsService()
        owner_id = uuid4()
        share_user_id = uuid4()

        segment = service.create_segment(
            name="Shared",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=owner_id,
            filter_groups=[],
        )

        service.share_segment(segment.id, owner_id, share_user_id)
        result = service.unshare_segment(segment.id, share_user_id)

        assert result is True
        updated = service.get_segment(segment.id)
        assert share_user_id not in updated.shared_with

    def test_get_shares(self) -> None:
        """Test getting shares for a segment."""
        service = SegmentViewsService()
        owner_id = uuid4()
        user1 = uuid4()
        user2 = uuid4()

        segment = service.create_segment(
            name="Shared",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=owner_id,
            filter_groups=[],
        )

        service.share_segment(segment.id, owner_id, user1)
        service.share_segment(segment.id, owner_id, user2)

        shares = service.get_shares(segment_id=segment.id)

        assert len(shares) == 2


class TestPinning:
    """Tests for segment pinning."""

    def test_pin_segment(self) -> None:
        """Test pinning a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="To Pin",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        pinned = service.pin_segment(segment.id)

        assert pinned is not None
        assert pinned.is_pinned is True

    def test_unpin_segment(self) -> None:
        """Test unpinning a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Pinned",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
            is_pinned=True,
        )

        unpinned = service.unpin_segment(segment.id)

        assert unpinned is not None
        assert unpinned.is_pinned is False


class TestDefaultSegment:
    """Tests for default segment management."""

    def test_set_default_segment(self) -> None:
        """Test setting a default segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="My Default",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        result = service.set_default_segment(segment.id, user_id, SegmentModule.RFQ)

        assert result is True
        assert service.get_segment(segment.id).is_default is True

    def test_get_default_segment(self) -> None:
        """Test getting default segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="My Default",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )
        service.set_default_segment(segment.id, user_id, SegmentModule.RFQ)

        default = service.get_default_segment(user_id, SegmentModule.RFQ)

        assert default is not None
        assert default.id == segment.id


class TestUsageTracking:
    """Tests for usage tracking."""

    def test_record_usage(self) -> None:
        """Test recording segment usage."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Used Segment",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        usage = service.record_usage(segment.id, user_id, result_count=25)

        assert usage is not None
        assert usage.result_count == 25

    def test_usage_updates_segment(self) -> None:
        """Test that usage updates segment stats."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Used Segment",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        service.record_usage(segment.id, user_id, result_count=25)

        updated = service.get_segment(segment.id)
        assert updated.use_count == 1
        assert updated.last_used_at is not None

    def test_get_usage_stats(self) -> None:
        """Test getting usage stats."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Used Segment",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        service.record_usage(segment.id, user_id, result_count=25)
        service.record_usage(segment.id, user_id, result_count=30)

        stats = service.get_usage_stats(segment_id=segment.id)

        assert len(stats) == 2

    def test_get_popular_segments(self) -> None:
        """Test getting popular segments."""
        service = SegmentViewsService()
        user_id = uuid4()

        # Create and use a segment
        segment = service.create_segment(
            name="Popular",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        for _ in range(5):
            service.record_usage(segment.id, user_id, result_count=10)

        popular = service.get_popular_segments(module=SegmentModule.RFQ, limit=5)

        assert len(popular) > 0

    def test_get_recent_segments(self) -> None:
        """Test getting recently used segments."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Recent",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        service.record_usage(segment.id, user_id, result_count=10)

        recent = service.get_recent_segments(user_id)

        assert segment.id in [s.id for s in recent]


class TestFilterEvaluation:
    """Tests for filter evaluation."""

    def test_apply_segment_equals(self) -> None:
        """Test applying segment with equals filter."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Status Filter",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "status": "new"},
            {"id": 2, "status": "closed"},
            {"id": 3, "status": "new"},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_apply_segment_in(self) -> None:
        """Test applying segment with IN filter."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="In Filter",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.IN,
                            value=["new", "in_progress"],
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "status": "new"},
            {"id": 2, "status": "closed"},
            {"id": 3, "status": "in_progress"},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_apply_segment_greater_than(self) -> None:
        """Test applying segment with greater than filter."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="GT Filter",
            description="Test",
            module=SegmentModule.QUOTE,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="margin",
                            operator=FilterOperator.GREATER_THAN,
                            value=20,
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "margin": 25},
            {"id": 2, "margin": 15},
            {"id": 3, "margin": 30},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_apply_segment_contains(self) -> None:
        """Test applying segment with contains filter."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Contains Filter",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="name",
                            operator=FilterOperator.CONTAINS,
                            value="urgent",
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "name": "Urgent RFQ"},
            {"id": 2, "name": "Normal RFQ"},
            {"id": 3, "name": "Another urgent request"},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_apply_segment_or_logic(self) -> None:
        """Test applying segment with OR logic."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="OR Filter",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        ),
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="urgent",
                        ),
                    ],
                    operator=LogicalOperator.OR,
                )
            ],
        )

        data = [
            {"id": 1, "status": "new"},
            {"id": 2, "status": "closed"},
            {"id": 3, "status": "urgent"},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_apply_segment_multiple_groups(self) -> None:
        """Test applying segment with multiple filter groups."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Multi Group",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        )
                    ]
                ),
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="priority",
                            operator=FilterOperator.EQUALS,
                            value="high",
                        )
                    ]
                ),
            ],
        )

        data = [
            {"id": 1, "status": "new", "priority": "high"},
            {"id": 2, "status": "new", "priority": "low"},
            {"id": 3, "status": "closed", "priority": "high"},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 1  # Only id=1 matches both


class TestCriteriaManagement:
    """Tests for criteria management."""

    def test_add_criterion(self) -> None:
        """Test adding a criterion to a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[FilterGroup(criteria=[])],
        )

        updated = service.add_criterion_to_segment(
            segment.id,
            0,
            FilterCriterion(
                field="status",
                operator=FilterOperator.EQUALS,
                value="new",
            ),
        )

        assert updated is not None
        assert len(updated.filter_groups[0].criteria) == 1

    def test_remove_criterion(self) -> None:
        """Test removing a criterion from a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        ),
                        FilterCriterion(
                            field="priority",
                            operator=FilterOperator.EQUALS,
                            value="high",
                        ),
                    ]
                )
            ],
        )

        updated = service.remove_criterion_from_segment(segment.id, 0, 0)

        assert updated is not None
        assert len(updated.filter_groups[0].criteria) == 1

    def test_add_filter_group(self) -> None:
        """Test adding a filter group."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        updated = service.add_filter_group(segment.id)

        assert updated is not None
        assert len(updated.filter_groups) == 1


class TestExportImport:
    """Tests for export/import."""

    def test_export_segment(self) -> None:
        """Test exporting a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Export Me",
            description="Test export",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="status",
                            operator=FilterOperator.EQUALS,
                            value="new",
                        )
                    ]
                )
            ],
            color="#FF0000",
        )

        exported = service.export_segment(segment.id)

        assert exported is not None
        assert exported["name"] == "Export Me"
        assert exported["color"] == "#FF0000"
        assert len(exported["filter_groups"]) == 1

    def test_import_segment(self) -> None:
        """Test importing a segment."""
        service = SegmentViewsService()
        user_id = uuid4()

        data = {
            "name": "Imported",
            "description": "Imported segment",
            "module": "rfq",
            "visibility": "private",
            "filter_groups": [
                {
                    "operator": "and",
                    "criteria": [
                        {
                            "field": "status",
                            "operator": "equals",
                            "value": "new",
                        }
                    ],
                }
            ],
            "columns": [],
            "color": "#00FF00",
        }

        imported = service.import_segment(data, user_id)

        assert imported is not None
        assert imported.name == "Imported"
        assert imported.color == "#00FF00"

    def test_export_nonexistent_segment(self) -> None:
        """Test exporting non-existent segment."""
        service = SegmentViewsService()

        result = service.export_segment(uuid4())

        assert result is None

    def test_import_invalid_data(self) -> None:
        """Test importing invalid data."""
        service = SegmentViewsService()

        result = service.import_segment({"invalid": "data"}, uuid4())

        assert result is None


class TestSummary:
    """Tests for summary statistics."""

    def test_get_summary(self) -> None:
        """Test getting summary."""
        service = SegmentViewsService()

        summary = service.get_summary()

        assert "total_segments" in summary
        assert "by_module" in summary
        assert "by_visibility" in summary
        assert summary["total_segments"] > 0

    def test_summary_counts_defaults(self) -> None:
        """Test that summary counts default segments."""
        service = SegmentViewsService()

        summary = service.get_summary()

        assert summary["default_segments"] > 0

    def test_summary_counts_smart(self) -> None:
        """Test that summary counts smart segments."""
        service = SegmentViewsService()

        summary = service.get_summary()

        assert summary["smart_segments"] > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_share_nonexistent_segment(self) -> None:
        """Test sharing non-existent segment."""
        service = SegmentViewsService()

        result = service.share_segment(uuid4(), uuid4(), uuid4())

        assert result is None

    def test_unshare_nonexistent(self) -> None:
        """Test unsharing non-existent share."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Test",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[],
        )

        result = service.unshare_segment(segment.id, uuid4())

        assert result is False

    def test_apply_nonexistent_segment(self) -> None:
        """Test applying non-existent segment."""
        service = SegmentViewsService()

        result = service.apply_segment(uuid4(), [])

        assert result.result_count == 0

    def test_record_usage_nonexistent(self) -> None:
        """Test recording usage for non-existent segment."""
        service = SegmentViewsService()

        result = service.record_usage(uuid4(), uuid4(), 10)

        assert result is None

    def test_pin_nonexistent_segment(self) -> None:
        """Test pinning non-existent segment."""
        service = SegmentViewsService()

        result = service.pin_segment(uuid4())

        assert result is None

    def test_is_null_filter(self) -> None:
        """Test IS_NULL filter operator."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Null Filter",
            description="Test",
            module=SegmentModule.RFQ,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="assignee",
                            operator=FilterOperator.IS_NULL,
                            value=None,
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "assignee": None},
            {"id": 2, "assignee": "John"},
            {"id": 3, "assignee": None},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2

    def test_between_filter(self) -> None:
        """Test BETWEEN filter operator."""
        service = SegmentViewsService()
        user_id = uuid4()

        segment = service.create_segment(
            name="Between Filter",
            description="Test",
            module=SegmentModule.QUOTE,
            owner_id=user_id,
            filter_groups=[
                FilterGroup(
                    criteria=[
                        FilterCriterion(
                            field="margin",
                            operator=FilterOperator.BETWEEN,
                            value=[10, 20],
                        )
                    ]
                )
            ],
        )

        data = [
            {"id": 1, "margin": 15},
            {"id": 2, "margin": 5},
            {"id": 3, "margin": 25},
            {"id": 4, "margin": 18},
        ]

        result = service.apply_segment(segment.id, data)

        assert result.result_count == 2
