"""
Tests for Digest & Snapshot Export Service.
"""

from datetime import datetime, date, time, timedelta
from uuid import uuid4

import pytest

from sensei.services.digest_export import (
    # Enums
    DigestType,
    DigestFrequency,
    DigestDeliveryChannel,
    DigestStatus,
    DigestFormat,
    WeekDay,
    # Data classes
    DigestSchedule,
    DigestRecipient,
    DigestSection,
    TodayDigestContent,
    WeekInReviewContent,
    ObeyaDigestContent,
    DigestConfiguration,
    GeneratedDigest,
    DigestJob,
    DigestDeliveryResult,
    # Service
    DigestExportService,
    # Section builders
    _build_priorities_section,
    _build_risks_section,
    _build_commitments_section,
    _build_abnormalities_section,
    _build_lsw_section,
    _build_metrics_section,
    _build_pipeline_section,
    _build_obeya_section,
    _build_a3_section,
    # Convenience functions
    create_daily_today_schedule,
    create_weekly_review_schedule,
    create_monthly_summary_schedule,
    create_email_recipient,
    create_in_app_recipient,
)


# --------------------------------------------------------------------------
# Tests for Enums
# --------------------------------------------------------------------------

class TestDigestType:
    """Tests for DigestType enum."""
    
    def test_all_types_exist(self) -> None:
        """All expected digest types should exist."""
        assert DigestType.TODAY_SNAPSHOT == "today_snapshot"
        assert DigestType.WEEK_IN_REVIEW == "week_in_review"
        assert DigestType.OBEYA_SNAPSHOT == "obeya_snapshot"
        assert DigestType.HQ_SHARE_PACK == "hq_share_pack"
        assert DigestType.MONTHLY_SUMMARY == "monthly_summary"
        assert DigestType.CUSTOM == "custom"
    
    def test_type_count(self) -> None:
        """Should have exactly 6 digest types."""
        assert len(DigestType) == 6


class TestDigestFrequency:
    """Tests for DigestFrequency enum."""
    
    def test_all_frequencies_exist(self) -> None:
        """All expected frequencies should exist."""
        assert DigestFrequency.DAILY == "daily"
        assert DigestFrequency.WEEKLY == "weekly"
        assert DigestFrequency.BIWEEKLY == "biweekly"
        assert DigestFrequency.MONTHLY == "monthly"
        assert DigestFrequency.ON_DEMAND == "on_demand"
    
    def test_frequency_count(self) -> None:
        """Should have exactly 5 frequencies."""
        assert len(DigestFrequency) == 5


class TestDigestDeliveryChannel:
    """Tests for DigestDeliveryChannel enum."""
    
    def test_all_channels_exist(self) -> None:
        """All expected channels should exist."""
        assert DigestDeliveryChannel.IN_APP == "in_app"
        assert DigestDeliveryChannel.EMAIL == "email"
        assert DigestDeliveryChannel.STORAGE == "storage"
        assert DigestDeliveryChannel.WEBHOOK == "webhook"


class TestDigestStatus:
    """Tests for DigestStatus enum."""
    
    def test_all_statuses_exist(self) -> None:
        """All expected statuses should exist."""
        assert DigestStatus.SCHEDULED == "scheduled"
        assert DigestStatus.PENDING == "pending"
        assert DigestStatus.GENERATING == "generating"
        assert DigestStatus.COMPLETED == "completed"
        assert DigestStatus.FAILED == "failed"
        assert DigestStatus.CANCELLED == "cancelled"
        assert DigestStatus.EXPIRED == "expired"


class TestWeekDay:
    """Tests for WeekDay enum."""
    
    def test_all_days_exist(self) -> None:
        """All days of the week should exist."""
        assert len(WeekDay) == 7
        assert WeekDay.MONDAY == "monday"
        assert WeekDay.SUNDAY == "sunday"


# --------------------------------------------------------------------------
# Tests for DigestSchedule
# --------------------------------------------------------------------------

class TestDigestSchedule:
    """Tests for DigestSchedule dataclass."""
    
    def test_default_creation(self) -> None:
        """Should create schedule with defaults."""
        schedule = DigestSchedule()
        
        assert schedule.id is not None
        assert schedule.frequency == DigestFrequency.DAILY
        assert schedule.time_of_day == time(6, 0)
        assert schedule.timezone == "Africa/Casablanca"
        assert schedule.is_active is True
        assert schedule.skip_weekends is False
    
    def test_weekly_schedule(self) -> None:
        """Should create weekly schedule."""
        schedule = DigestSchedule(
            name="Weekly Review",
            frequency=DigestFrequency.WEEKLY,
            day_of_week=WeekDay.FRIDAY,
            time_of_day=time(17, 0),
        )
        
        assert schedule.frequency == DigestFrequency.WEEKLY
        assert schedule.day_of_week == WeekDay.FRIDAY
        assert schedule.time_of_day == time(17, 0)
    
    def test_monthly_schedule(self) -> None:
        """Should create monthly schedule."""
        schedule = DigestSchedule(
            name="Monthly Summary",
            frequency=DigestFrequency.MONTHLY,
            day_of_month=15,
            time_of_day=time(9, 0),
        )
        
        assert schedule.frequency == DigestFrequency.MONTHLY
        assert schedule.day_of_month == 15


# --------------------------------------------------------------------------
# Tests for DigestRecipient
# --------------------------------------------------------------------------

class TestDigestRecipient:
    """Tests for DigestRecipient dataclass."""
    
    def test_default_creation(self) -> None:
        """Should create recipient with defaults."""
        recipient = DigestRecipient()
        
        assert recipient.id is not None
        assert recipient.channels == [DigestDeliveryChannel.IN_APP]
        assert recipient.format_preference == DigestFormat.PDF
        assert recipient.is_active is True
    
    def test_email_recipient(self) -> None:
        """Should create email recipient."""
        user_id = uuid4()
        recipient = DigestRecipient(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            channels=[DigestDeliveryChannel.EMAIL, DigestDeliveryChannel.IN_APP],
        )
        
        assert recipient.user_id == user_id
        assert recipient.email == "test@example.com"
        assert DigestDeliveryChannel.EMAIL in recipient.channels
    
    def test_section_filters(self) -> None:
        """Should support section filters."""
        recipient = DigestRecipient(
            include_sections=["priorities", "risks"],
            exclude_sections=["metrics"],
        )
        
        assert "priorities" in recipient.include_sections
        assert "metrics" in recipient.exclude_sections


# --------------------------------------------------------------------------
# Tests for DigestSection
# --------------------------------------------------------------------------

class TestDigestSection:
    """Tests for DigestSection dataclass."""
    
    def test_creation(self) -> None:
        """Should create section."""
        section = DigestSection(
            id="priorities",
            title="Top Priorities",
            content_type="priorities",
            order=1,
        )
        
        assert section.id == "priorities"
        assert section.title == "Top Priorities"
        assert section.order == 1
        assert section.include_in_toc is True
        assert section.is_empty is False
    
    def test_empty_section(self) -> None:
        """Should track empty sections."""
        section = DigestSection(
            id="risks",
            title="Risks",
            content_type="risks",
            order=2,
            is_empty=True,
        )
        
        assert section.is_empty is True
    
    def test_page_break(self) -> None:
        """Should support page break config."""
        section = DigestSection(
            id="obeya",
            title="Obeya",
            content_type="obeya",
            order=10,
            page_break_before=True,
        )
        
        assert section.page_break_before is True


# --------------------------------------------------------------------------
# Tests for TodayDigestContent
# --------------------------------------------------------------------------

class TestTodayDigestContent:
    """Tests for TodayDigestContent dataclass."""
    
    def test_creation(self) -> None:
        """Should create Today content."""
        user_id = uuid4()
        content = TodayDigestContent(
            user_id=user_id,
            user_name="John Doe",
            snapshot_date=date.today(),
        )
        
        assert content.user_id == user_id
        assert content.user_name == "John Doe"
        assert content.top_priorities == []
        assert content.greeting == ""
    
    def test_with_data(self) -> None:
        """Should hold all content data."""
        content = TodayDigestContent(
            user_id=uuid4(),
            user_name="Jane",
            snapshot_date=date.today(),
            top_priorities=[{"id": "1", "title": "Priority 1"}],
            risks_by_category={"delivery": [{"id": "r1"}]},
            abnormality_counts={"late_quote": 3},
            lsw_completion_rate=85.0,
        )
        
        assert len(content.top_priorities) == 1
        assert "delivery" in content.risks_by_category
        assert content.abnormality_counts["late_quote"] == 3
        assert content.lsw_completion_rate == 85.0


# --------------------------------------------------------------------------
# Tests for WeekInReviewContent
# --------------------------------------------------------------------------

class TestWeekInReviewContent:
    """Tests for WeekInReviewContent dataclass."""
    
    def test_creation(self) -> None:
        """Should create Week in Review content."""
        content = WeekInReviewContent(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
        )
        
        assert content.period_start == date(2026, 1, 1)
        assert content.period_end == date(2026, 1, 7)
        assert content.key_highlights == []
    
    def test_with_metrics(self) -> None:
        """Should hold business metrics."""
        content = WeekInReviewContent(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
            new_opportunities=5,
            closed_won=2,
            pipeline_value=100000.0,
            win_rate=0.65,
            quotes_issued=10,
        )
        
        assert content.new_opportunities == 5
        assert content.closed_won == 2
        assert content.pipeline_value == 100000.0
        assert content.win_rate == 0.65


# --------------------------------------------------------------------------
# Tests for ObeyaDigestContent
# --------------------------------------------------------------------------

class TestObeyaDigestContent:
    """Tests for ObeyaDigestContent dataclass."""
    
    def test_creation(self) -> None:
        """Should create Obeya content."""
        content = ObeyaDigestContent(snapshot_date=date.today())
        
        assert content.safety_items == []
        assert content.quality_items == []
        assert content.red_item_count == 0
    
    def test_with_sqdcp_items(self) -> None:
        """Should hold SQDCP items."""
        red_items = [{"id": "q1", "is_red": True}]
        content = ObeyaDigestContent(
            snapshot_date=date.today(),
            safety_items=[{"id": "s1", "title": "Safety issue"}],
            quality_items=[{"id": "q1", "is_red": True}],
            red_items=red_items,
            red_item_count=len(red_items),  # Must be set explicitly
        )
        
        assert len(content.safety_items) == 1
        assert len(content.quality_items) == 1
        assert content.red_item_count == 1


# --------------------------------------------------------------------------
# Tests for Section Builders
# --------------------------------------------------------------------------

class TestSectionBuilders:
    """Tests for section builder functions."""
    
    def test_build_priorities_section(self) -> None:
        """Should build priorities section."""
        priorities = [
            {"id": "1", "title": "P1"},
            {"id": "2", "title": "P2"},
            {"id": "3", "title": "P3"},
            {"id": "4", "title": "P4"},
        ]
        
        section = _build_priorities_section(priorities, max_items=3)
        
        assert section.id == "priorities"
        assert section.title == "Top Priorities"
        assert len(section.data["items"]) == 3
        assert section.data["total_count"] == 4
        assert section.is_empty is False
    
    def test_build_priorities_section_empty(self) -> None:
        """Should mark empty priorities section."""
        section = _build_priorities_section([])
        
        assert section.is_empty is True
    
    def test_build_risks_section(self) -> None:
        """Should build risks section."""
        risks = [{"id": "r1", "title": "Risk 1"}]
        by_category = {"delivery": risks}
        
        section = _build_risks_section(risks, by_category)
        
        assert section.id == "risks"
        assert section.data["items"] == risks
        assert section.data["by_category"] == by_category
    
    def test_build_commitments_section(self) -> None:
        """Should build commitments section."""
        overdue = [{"id": "c1"}]
        due_today = [{"id": "c2"}, {"id": "c3"}]
        upcoming = [{"id": "c4"}]
        
        section = _build_commitments_section(overdue, due_today, upcoming)
        
        assert section.id == "commitments"
        assert section.data["overdue_count"] == 1
        assert section.data["due_today_count"] == 2
        assert section.data["upcoming_count"] == 1
    
    def test_build_abnormalities_section(self) -> None:
        """Should build abnormalities section."""
        counts = {"late_quote": 3, "stalled_rfq": 2}
        critical = [{"id": "a1", "type": "late_quote"}]
        
        section = _build_abnormalities_section(counts, critical)
        
        assert section.id == "abnormalities"
        assert section.data["total_count"] == 5
        assert section.data["critical"] == critical
    
    def test_build_lsw_section(self) -> None:
        """Should build LSW section."""
        overdue = [{"id": "l1", "title": "Daily standup"}]
        
        section = _build_lsw_section(85.5, overdue)
        
        assert section.id == "lsw"
        assert section.data["completion_rate"] == 85.5
        assert section.data["overdue_count"] == 1
        assert section.is_empty is False  # LSW never empty
    
    def test_build_metrics_section(self) -> None:
        """Should build metrics section."""
        metrics = [
            {"name": "Win Rate", "value": 65.0, "unit": "%"},
            {"name": "Pipeline", "value": 100000, "unit": "USD"},
        ]
        
        section = _build_metrics_section(metrics)
        
        assert section.id == "metrics"
        assert len(section.data["items"]) == 2
    
    def test_build_pipeline_section(self) -> None:
        """Should build pipeline section."""
        summary = {"new": 5, "won": 2, "lost": 1}
        
        section = _build_pipeline_section(summary)
        
        assert section.id == "pipeline"
        assert section.data == summary
        assert section.is_empty is False
    
    def test_build_obeya_section(self) -> None:
        """Should build obeya section."""
        red_items = [{"id": "o1", "is_red": True}]
        by_category = {"quality": red_items}
        
        section = _build_obeya_section(red_items, by_category)
        
        assert section.id == "obeya"
        assert section.data["red_count"] == 1
    
    def test_build_a3_section(self) -> None:
        """Should build A3 section."""
        open_a3s = [{"id": "a1"}, {"id": "a2"}]
        
        section = _build_a3_section(open_a3s, opened=1, closed=3)
        
        assert section.id == "a3"
        assert section.data["open_count"] == 2
        assert section.data["opened_this_period"] == 1
        assert section.data["closed_this_period"] == 3


# --------------------------------------------------------------------------
# Tests for DigestExportService - Configuration
# --------------------------------------------------------------------------

class TestDigestExportServiceConfiguration:
    """Tests for configuration management."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_create_configuration(self, service: DigestExportService) -> None:
        """Should create configuration."""
        schedule = DigestSchedule(frequency=DigestFrequency.DAILY)
        recipient = DigestRecipient(name="Test User")
        
        config = service.create_configuration(
            name="Daily Snapshot",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=schedule,
            recipients=[recipient],
            description="Daily manager snapshot",
            created_by=uuid4(),
        )
        
        assert config.id is not None
        assert config.name == "Daily Snapshot"
        assert config.digest_type == DigestType.TODAY_SNAPSHOT
        assert len(config.recipients) == 1
        assert config.schedule.next_run_at is not None
    
    def test_get_configuration(self, service: DigestExportService) -> None:
        """Should retrieve configuration by ID."""
        schedule = DigestSchedule()
        config = service.create_configuration(
            name="Test",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=schedule,
            recipients=[],
        )
        
        retrieved = service.get_configuration(config.id)
        
        assert retrieved is not None
        assert retrieved.id == config.id
    
    def test_get_nonexistent_configuration(self, service: DigestExportService) -> None:
        """Should return None for nonexistent config."""
        result = service.get_configuration(uuid4())
        assert result is None
    
    def test_update_configuration(self, service: DigestExportService) -> None:
        """Should update configuration."""
        config = service.create_configuration(
            name="Original",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
        
        updated = service.update_configuration(
            config.id,
            {"name": "Updated", "description": "New description"},
        )
        
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.description == "New description"
        assert updated.updated_at is not None
    
    def test_delete_configuration(self, service: DigestExportService) -> None:
        """Should delete configuration."""
        config = service.create_configuration(
            name="To Delete",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
        
        result = service.delete_configuration(config.id)
        
        assert result is True
        assert service.get_configuration(config.id) is None
    
    def test_delete_nonexistent_configuration(self, service: DigestExportService) -> None:
        """Should return False for nonexistent config."""
        result = service.delete_configuration(uuid4())
        assert result is False
    
    def test_list_configurations(self, service: DigestExportService) -> None:
        """Should list configurations."""
        service.create_configuration(
            name="Config 1",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
        service.create_configuration(
            name="Config 2",
            digest_type=DigestType.WEEK_IN_REVIEW,
            schedule=DigestSchedule(),
            recipients=[],
        )
        
        all_configs = service.list_configurations()
        
        assert len(all_configs) == 2
    
    def test_list_configurations_by_type(self, service: DigestExportService) -> None:
        """Should filter configurations by type."""
        service.create_configuration(
            name="Today 1",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
        service.create_configuration(
            name="Week Review",
            digest_type=DigestType.WEEK_IN_REVIEW,
            schedule=DigestSchedule(),
            recipients=[],
        )
        
        today_configs = service.list_configurations(
            digest_type=DigestType.TODAY_SNAPSHOT
        )
        
        assert len(today_configs) == 1
        assert today_configs[0].name == "Today 1"
    
    def test_list_active_only(self, service: DigestExportService) -> None:
        """Should filter by active status."""
        config = service.create_configuration(
            name="Inactive",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
        service.update_configuration(config.id, {"is_active": False})
        
        active_configs = service.list_configurations(active_only=True)
        
        assert len(active_configs) == 0


# --------------------------------------------------------------------------
# Tests for DigestExportService - Recipients
# --------------------------------------------------------------------------

class TestDigestExportServiceRecipients:
    """Tests for recipient management."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    @pytest.fixture
    def config(self, service: DigestExportService) -> DigestConfiguration:
        """Create a test configuration."""
        return service.create_configuration(
            name="Test Config",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[],
        )
    
    def test_add_recipient(
        self, service: DigestExportService, config: DigestConfiguration
    ) -> None:
        """Should add recipient to configuration."""
        recipient = DigestRecipient(
            email="test@example.com",
            name="Test User",
        )
        
        updated = service.add_recipient(config.id, recipient)
        
        assert updated is not None
        assert len(updated.recipients) == 1
        assert updated.recipients[0].email == "test@example.com"
    
    def test_remove_recipient(
        self, service: DigestExportService, config: DigestConfiguration
    ) -> None:
        """Should remove recipient from configuration."""
        recipient = DigestRecipient(name="To Remove")
        service.add_recipient(config.id, recipient)
        
        updated = service.remove_recipient(config.id, recipient.id)
        
        assert updated is not None
        assert len(updated.recipients) == 0
    
    def test_update_recipient(
        self, service: DigestExportService, config: DigestConfiguration
    ) -> None:
        """Should update recipient settings."""
        recipient = DigestRecipient(name="Original", email="old@test.com")
        service.add_recipient(config.id, recipient)
        
        updated = service.update_recipient(
            config.id,
            recipient.id,
            {"email": "new@test.com", "is_active": False},
        )
        
        assert updated is not None
        assert updated.email == "new@test.com"
        assert updated.is_active is False


# --------------------------------------------------------------------------
# Tests for DigestExportService - Schedule
# --------------------------------------------------------------------------

class TestDigestExportServiceSchedule:
    """Tests for schedule management."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_calculate_next_run_daily(self, service: DigestExportService) -> None:
        """Should calculate next daily run."""
        schedule = DigestSchedule(
            frequency=DigestFrequency.DAILY,
            time_of_day=time(8, 0),
        )
        
        # From a specific time
        from_time = datetime(2026, 1, 6, 6, 0)  # 6 AM
        next_run = service._calculate_next_run(schedule, from_time)
        
        # Should be today at 8 AM
        assert next_run.date() == date(2026, 1, 6)
        assert next_run.hour == 8
    
    def test_calculate_next_run_daily_past_time(self, service: DigestExportService) -> None:
        """Should go to next day if time passed."""
        schedule = DigestSchedule(
            frequency=DigestFrequency.DAILY,
            time_of_day=time(8, 0),
        )
        
        from_time = datetime(2026, 1, 6, 10, 0)  # 10 AM (past 8 AM)
        next_run = service._calculate_next_run(schedule, from_time)
        
        # Should be tomorrow at 8 AM
        assert next_run.date() == date(2026, 1, 7)
    
    def test_calculate_next_run_skip_weekends(self, service: DigestExportService) -> None:
        """Should skip weekends when configured."""
        schedule = DigestSchedule(
            frequency=DigestFrequency.DAILY,
            time_of_day=time(8, 0),
            skip_weekends=True,
        )
        
        # Friday evening
        from_time = datetime(2026, 1, 9, 20, 0)  # Friday 8 PM
        next_run = service._calculate_next_run(schedule, from_time)
        
        # Should skip Saturday/Sunday, land on Monday
        assert next_run.weekday() == 0  # Monday
    
    def test_calculate_next_run_weekly(self, service: DigestExportService) -> None:
        """Should calculate next weekly run."""
        schedule = DigestSchedule(
            frequency=DigestFrequency.WEEKLY,
            day_of_week=WeekDay.FRIDAY,
            time_of_day=time(17, 0),
        )
        
        # Monday
        from_time = datetime(2026, 1, 5, 10, 0)  # Monday
        next_run = service._calculate_next_run(schedule, from_time)
        
        # Should be Friday
        assert next_run.weekday() == 4  # Friday
    
    def test_calculate_next_run_monthly(self, service: DigestExportService) -> None:
        """Should calculate next monthly run."""
        schedule = DigestSchedule(
            frequency=DigestFrequency.MONTHLY,
            day_of_month=15,
            time_of_day=time(9, 0),
        )
        
        from_time = datetime(2026, 1, 10, 10, 0)
        next_run = service._calculate_next_run(schedule, from_time)
        
        # Should be 15th of current month
        assert next_run.day == 15
        assert next_run.month == 1
    
    def test_get_pending_jobs(self, service: DigestExportService) -> None:
        """Should get configurations due to run."""
        # Create config with past next_run
        schedule = DigestSchedule(
            frequency=DigestFrequency.DAILY,
            time_of_day=time(6, 0),
        )
        config = service.create_configuration(
            name="Pending",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=schedule,
            recipients=[],
        )
        
        # Manually set next_run to past
        config.schedule.next_run_at = datetime.utcnow() - timedelta(hours=1)
        
        pending = service.get_pending_jobs()
        
        assert len(pending) == 1
        assert pending[0].id == config.id
    
    def test_update_schedule_after_run(self, service: DigestExportService) -> None:
        """Should update schedule after run."""
        config = service.create_configuration(
            name="Test",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(frequency=DigestFrequency.DAILY),
            recipients=[],
        )
        
        # Verify initial state
        assert config.schedule.last_run_at is None
        
        updated = service.update_schedule_after_run(config.id)
        
        assert updated is not None
        assert updated.last_run_at is not None
        assert updated.next_run_at is not None
        # After a run, last_run_at should be set
        # Next run should be calculated (either same or future)


# --------------------------------------------------------------------------
# Tests for DigestExportService - Content Building
# --------------------------------------------------------------------------

class TestDigestExportServiceContentBuilding:
    """Tests for content building."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_build_today_digest_content(self, service: DigestExportService) -> None:
        """Should build Today digest content."""
        user_id = uuid4()
        
        content = service.build_today_digest_content(
            user_id=user_id,
            user_name="John Doe",
            snapshot_date=date(2026, 1, 6),
            priorities=[{"id": "1", "title": "P1"}],
            risks=[{"id": "r1"}],
            lsw_completion_rate=90.0,
        )
        
        assert content.user_id == user_id
        assert content.user_name == "John Doe"
        assert len(content.top_priorities) == 1
        assert content.lsw_completion_rate == 90.0
        assert "John Doe" in content.greeting
    
    def test_build_week_in_review_content(self, service: DigestExportService) -> None:
        """Should build Week in Review content."""
        content = service.build_week_in_review_content(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
            executive_summary="Good week overall",
            new_opportunities=5,
            win_rate=0.65,
        )
        
        assert content.period_start == date(2026, 1, 1)
        assert content.executive_summary == "Good week overall"
        assert content.new_opportunities == 5
        assert content.win_rate == 0.65
    
    def test_build_obeya_digest_content(self, service: DigestExportService) -> None:
        """Should build Obeya digest content."""
        content = service.build_obeya_digest_content(
            snapshot_date=date.today(),
            safety_items=[{"id": "s1"}],
            red_items=[{"id": "r1", "is_red": True}],
            countermeasures_overdue=[{"id": "c1"}],
        )
        
        assert len(content.safety_items) == 1
        assert content.red_item_count == 1
        assert len(content.countermeasures_overdue) == 1
    
    def test_build_sections_from_today_content(self, service: DigestExportService) -> None:
        """Should build sections from Today content."""
        content = TodayDigestContent(
            user_id=uuid4(),
            user_name="Test",
            snapshot_date=date.today(),
            top_priorities=[{"id": "1"}],
            top_risks=[{"id": "r1"}],
            lsw_completion_rate=80.0,
        )
        
        sections = service.build_sections_from_today_content(content)
        
        # Should have sections for priorities, risks, lsw, metrics
        section_ids = [s.id for s in sections]
        assert "priorities" in section_ids
        assert "risks" in section_ids
        assert "lsw" in section_ids
    
    def test_build_sections_from_week_content(self, service: DigestExportService) -> None:
        """Should build sections from Week content."""
        content = WeekInReviewContent(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
            executive_summary="Summary here",
        )
        
        sections = service.build_sections_from_week_content(content)
        
        section_ids = [s.id for s in sections]
        assert "executive_summary" in section_ids
        assert "pipeline" in section_ids
        assert "quoting" in section_ids


# --------------------------------------------------------------------------
# Tests for DigestExportService - Generation
# --------------------------------------------------------------------------

class TestDigestExportServiceGeneration:
    """Tests for digest generation."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_generate_today_digest(self, service: DigestExportService) -> None:
        """Should generate Today digest."""
        content = TodayDigestContent(
            user_id=uuid4(),
            user_name="Test User",
            snapshot_date=date(2026, 1, 6),
            top_priorities=[{"id": "1", "title": "P1"}],
            lsw_completion_rate=85.0,
        )
        
        digest = service.generate_today_digest(content)
        
        assert digest.id is not None
        assert digest.digest_type == DigestType.TODAY_SNAPSHOT
        assert digest.status == DigestStatus.COMPLETED
        assert digest.content_base64 != ""
        assert digest.content_hash != ""
        assert digest.page_count >= 1
        assert digest.generation_time_ms >= 0
    
    def test_generate_week_in_review_digest(self, service: DigestExportService) -> None:
        """Should generate Week in Review digest."""
        content = WeekInReviewContent(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
            quotes_issued=10,
        )
        
        digest = service.generate_week_in_review_digest(content)
        
        assert digest.digest_type == DigestType.WEEK_IN_REVIEW
        assert digest.period_start == date(2026, 1, 1)
        assert digest.period_end == date(2026, 1, 7)
        assert digest.status == DigestStatus.COMPLETED
    
    def test_generate_obeya_digest(self, service: DigestExportService) -> None:
        """Should generate Obeya digest."""
        content = ObeyaDigestContent(
            snapshot_date=date(2026, 1, 6),
            quality_items=[{"id": "q1", "is_red": True}],
            red_items=[{"id": "q1"}],
        )
        
        digest = service.generate_obeya_digest(content)
        
        assert digest.digest_type == DigestType.OBEYA_SNAPSHOT
        assert digest.status == DigestStatus.COMPLETED
    
    def test_generate_hq_share_pack(self, service: DigestExportService) -> None:
        """Should generate HQ Share Pack (combined)."""
        week_content = WeekInReviewContent(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="Admin",
        )
        obeya_content = ObeyaDigestContent(
            snapshot_date=date(2026, 1, 7),
            red_items=[{"id": "r1"}],
        )
        
        digest = service.generate_hq_share_pack(week_content, obeya_content)
        
        assert digest.digest_type == DigestType.HQ_SHARE_PACK
        assert digest.page_count >= 4


# --------------------------------------------------------------------------
# Tests for DigestExportService - Digest Retrieval
# --------------------------------------------------------------------------

class TestDigestExportServiceRetrieval:
    """Tests for digest retrieval."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_get_digest(self, service: DigestExportService) -> None:
        """Should retrieve digest by ID."""
        content = TodayDigestContent(
            user_id=uuid4(),
            user_name="Test",
            snapshot_date=date.today(),
        )
        digest = service.generate_today_digest(content)
        
        retrieved = service.get_digest(digest.id)
        
        assert retrieved is not None
        assert retrieved.id == digest.id
    
    def test_get_nonexistent_digest(self, service: DigestExportService) -> None:
        """Should return None for nonexistent digest."""
        result = service.get_digest(uuid4())
        assert result is None
    
    def test_list_digests(self, service: DigestExportService) -> None:
        """Should list digests."""
        # Generate some digests
        for i in range(3):
            content = TodayDigestContent(
                user_id=uuid4(),
                user_name=f"User {i}",
                snapshot_date=date.today() - timedelta(days=i),
            )
            service.generate_today_digest(content)
        
        digests = service.list_digests()
        
        assert len(digests) == 3
    
    def test_list_digests_by_type(self, service: DigestExportService) -> None:
        """Should filter digests by type."""
        # Today digest
        service.generate_today_digest(TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        ))
        
        # Obeya digest
        service.generate_obeya_digest(ObeyaDigestContent(
            snapshot_date=date.today()
        ))
        
        today_digests = service.list_digests(digest_type=DigestType.TODAY_SNAPSHOT)
        
        assert len(today_digests) == 1
    
    def test_list_digests_by_date_range(self, service: DigestExportService) -> None:
        """Should filter by date range."""
        # Old digest
        old_content = TodayDigestContent(
            user_id=uuid4(), user_name="Old",
            snapshot_date=date(2025, 12, 1),
        )
        old_digest = service.generate_today_digest(old_content)
        old_digest.period_start = date(2025, 12, 1)
        
        # Recent digest
        new_content = TodayDigestContent(
            user_id=uuid4(), user_name="New",
            snapshot_date=date(2026, 1, 5),
        )
        new_digest = service.generate_today_digest(new_content)
        new_digest.period_start = date(2026, 1, 5)
        
        recent = service.list_digests(start_date=date(2026, 1, 1))
        
        assert len(recent) == 1
    
    def test_delete_digest(self, service: DigestExportService) -> None:
        """Should delete digest."""
        content = TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        )
        digest = service.generate_today_digest(content)
        
        result = service.delete_digest(digest.id)
        
        assert result is True
        assert service.get_digest(digest.id) is None
    
    def test_cleanup_expired_digests(self, service: DigestExportService) -> None:
        """Should cleanup expired digests."""
        content = TodayDigestContent(
            user_id=uuid4(), user_name="Expired", snapshot_date=date.today()
        )
        digest = service.generate_today_digest(content)
        
        # Set to expired
        digest.expires_at = datetime.utcnow() - timedelta(days=1)
        
        count = service.cleanup_expired_digests()
        
        assert count == 1
        assert service.get_digest(digest.id) is None


# --------------------------------------------------------------------------
# Tests for DigestExportService - Jobs
# --------------------------------------------------------------------------

class TestDigestExportServiceJobs:
    """Tests for job management."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_create_job(self, service: DigestExportService) -> None:
        """Should create job."""
        config_id = uuid4()
        scheduled_at = datetime.utcnow() + timedelta(hours=1)
        
        job = service.create_job(config_id, scheduled_at)
        
        assert job.id is not None
        assert job.configuration_id == config_id
        assert job.status == DigestStatus.SCHEDULED
    
    def test_start_job(self, service: DigestExportService) -> None:
        """Should start job."""
        job = service.create_job(uuid4(), datetime.utcnow())
        
        started = service.start_job(job.id)
        
        assert started is not None
        assert started.status == DigestStatus.GENERATING
        assert started.started_at is not None
    
    def test_complete_job(self, service: DigestExportService) -> None:
        """Should complete job."""
        job = service.create_job(uuid4(), datetime.utcnow())
        service.start_job(job.id)
        
        digest_id = uuid4()
        completed = service.complete_job(job.id, digest_id)
        
        assert completed is not None
        assert completed.status == DigestStatus.COMPLETED
        assert completed.digest_id == digest_id
        assert completed.completed_at is not None
    
    def test_fail_job_with_retry(self, service: DigestExportService) -> None:
        """Should fail job with retry."""
        job = service.create_job(uuid4(), datetime.utcnow())
        service.start_job(job.id)
        
        failed = service.fail_job(job.id, "Network error")
        
        assert failed is not None
        assert failed.status == DigestStatus.PENDING  # Will retry
        assert failed.retry_count == 1
        assert failed.error_message == "Network error"
    
    def test_fail_job_max_retries(self, service: DigestExportService) -> None:
        """Should mark as failed after max retries."""
        job = service.create_job(uuid4(), datetime.utcnow())
        
        # Exhaust retries
        for _ in range(3):
            service.fail_job(job.id, "Error")
        
        assert job.status == DigestStatus.FAILED
        assert job.retry_count == 3
    
    def test_list_jobs(self, service: DigestExportService) -> None:
        """Should list jobs."""
        config_id = uuid4()
        service.create_job(config_id, datetime.utcnow())
        service.create_job(config_id, datetime.utcnow() + timedelta(hours=1))
        
        jobs = service.list_jobs(config_id=config_id)
        
        assert len(jobs) == 2


# --------------------------------------------------------------------------
# Tests for DigestExportService - Delivery
# --------------------------------------------------------------------------

class TestDigestExportServiceDelivery:
    """Tests for delivery tracking."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_record_delivery_success(self, service: DigestExportService) -> None:
        """Should record successful delivery."""
        # Generate a digest first
        content = TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        )
        digest = service.generate_today_digest(content)
        
        recipient_id = uuid4()
        result = service.record_delivery(
            digest.id,
            recipient_id,
            DigestDeliveryChannel.EMAIL,
            success=True,
            email_message_id="msg-123",
        )
        
        assert result.success is True
        assert result.delivered_at is not None
        assert result.email_message_id == "msg-123"
        
        # Check digest status updated
        assert digest.delivery_status[str(recipient_id)] == "delivered"
    
    def test_record_delivery_failure(self, service: DigestExportService) -> None:
        """Should record failed delivery."""
        content = TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        )
        digest = service.generate_today_digest(content)
        
        recipient_id = uuid4()
        result = service.record_delivery(
            digest.id,
            recipient_id,
            DigestDeliveryChannel.EMAIL,
            success=False,
            error_message="SMTP error",
        )
        
        assert result.success is False
        assert result.error_message == "SMTP error"
        assert digest.delivery_status[str(recipient_id)] == "failed"
    
    def test_get_delivery_results(self, service: DigestExportService) -> None:
        """Should get delivery results for digest."""
        content = TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        )
        digest = service.generate_today_digest(content)
        
        # Record multiple deliveries
        service.record_delivery(digest.id, uuid4(), DigestDeliveryChannel.EMAIL, True)
        service.record_delivery(digest.id, uuid4(), DigestDeliveryChannel.IN_APP, True)
        
        results = service.get_delivery_results(digest.id)
        
        assert len(results) == 2


# --------------------------------------------------------------------------
# Tests for DigestExportService - Statistics
# --------------------------------------------------------------------------

class TestDigestExportServiceStatistics:
    """Tests for statistics."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_get_statistics(self, service: DigestExportService) -> None:
        """Should get statistics."""
        # Generate various digests
        service.generate_today_digest(TodayDigestContent(
            user_id=uuid4(), user_name="T1", snapshot_date=date.today()
        ))
        service.generate_today_digest(TodayDigestContent(
            user_id=uuid4(), user_name="T2", snapshot_date=date.today()
        ))
        service.generate_obeya_digest(ObeyaDigestContent(
            snapshot_date=date.today()
        ))
        
        stats = service.get_statistics()
        
        assert stats["total_digests"] == 3
        assert stats["by_type"]["today_snapshot"] == 2
        assert stats["by_type"]["obeya_snapshot"] == 1
        assert stats["by_status"]["completed"] == 3
        assert stats["average_generation_time_ms"] >= 0
    
    def test_get_statistics_with_date_filter(self, service: DigestExportService) -> None:
        """Should filter statistics by date."""
        # Generate digest today
        service.generate_today_digest(TodayDigestContent(
            user_id=uuid4(), user_name="Test", snapshot_date=date.today()
        ))
        
        # Get stats for future (should be empty)
        stats = service.get_statistics(
            start_date=date.today() + timedelta(days=1)
        )
        
        assert stats["total_digests"] == 0


# --------------------------------------------------------------------------
# Tests for Convenience Functions
# --------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_create_daily_today_schedule(self) -> None:
        """Should create daily schedule."""
        schedule = create_daily_today_schedule(
            time_of_day=time(7, 0),
            skip_weekends=True,
        )
        
        assert schedule.frequency == DigestFrequency.DAILY
        assert schedule.time_of_day == time(7, 0)
        assert schedule.skip_weekends is True
        assert schedule.timezone == "Africa/Casablanca"
    
    def test_create_weekly_review_schedule(self) -> None:
        """Should create weekly schedule."""
        schedule = create_weekly_review_schedule(
            day_of_week=WeekDay.MONDAY,
            time_of_day=time(9, 0),
        )
        
        assert schedule.frequency == DigestFrequency.WEEKLY
        assert schedule.day_of_week == WeekDay.MONDAY
    
    def test_create_monthly_summary_schedule(self) -> None:
        """Should create monthly schedule."""
        schedule = create_monthly_summary_schedule(
            day_of_month=15,
        )
        
        assert schedule.frequency == DigestFrequency.MONTHLY
        assert schedule.day_of_month == 15
    
    def test_create_email_recipient(self) -> None:
        """Should create email recipient."""
        user_id = uuid4()
        recipient = create_email_recipient(
            email="test@example.com",
            name="Test User",
            user_id=user_id,
        )
        
        assert recipient.email == "test@example.com"
        assert recipient.user_id == user_id
        assert DigestDeliveryChannel.EMAIL in recipient.channels
        assert DigestDeliveryChannel.IN_APP in recipient.channels
    
    def test_create_in_app_recipient(self) -> None:
        """Should create in-app only recipient."""
        user_id = uuid4()
        recipient = create_in_app_recipient(user_id, "Test User")
        
        assert recipient.user_id == user_id
        assert recipient.channels == [DigestDeliveryChannel.IN_APP]


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestDigestExportIntegration:
    """Integration tests for full workflows."""
    
    @pytest.fixture
    def service(self) -> DigestExportService:
        """Create a service instance."""
        return DigestExportService()
    
    def test_full_daily_digest_workflow(self, service: DigestExportService) -> None:
        """Test complete daily digest workflow."""
        # 1. Create configuration
        schedule = create_daily_today_schedule()
        recipient = create_email_recipient("gm@company.com", "General Manager")
        
        config = service.create_configuration(
            name="GM Daily Snapshot",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=schedule,
            recipients=[recipient],
        )
        
        # 2. Create job
        job = service.create_job(config.id, datetime.utcnow())
        
        # 3. Start job
        service.start_job(job.id)
        
        # 4. Build content
        content = service.build_today_digest_content(
            user_id=uuid4(),
            user_name="General Manager",
            snapshot_date=date.today(),
            priorities=[{"id": "1", "title": "Close Q1 deals"}],
            risks=[{"id": "r1", "title": "Supply chain delay"}],
            lsw_completion_rate=92.0,
        )
        
        # 5. Generate digest
        digest = service.generate_today_digest(content, config)
        
        # 6. Complete job
        service.complete_job(job.id, digest.id)
        
        # 7. Record delivery
        service.record_delivery(
            digest.id,
            recipient.id,
            DigestDeliveryChannel.EMAIL,
            success=True,
        )
        
        # 8. Update schedule
        service.update_schedule_after_run(config.id)
        
        # Verify final state
        assert job.status == DigestStatus.COMPLETED
        assert digest.status == DigestStatus.COMPLETED
        assert config.schedule.last_run_at is not None
        assert len(service.get_delivery_results(digest.id)) == 1
    
    def test_full_weekly_review_workflow(self, service: DigestExportService) -> None:
        """Test complete weekly review workflow."""
        # Create Week in Review content
        week_content = service.build_week_in_review_content(
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 7),
            generated_by=uuid4(),
            generated_by_name="CEO",
            executive_summary="Strong week with 5 new opportunities",
            key_highlights=["Closed $200K deal", "3 quotes approved"],
            new_opportunities=5,
            closed_won=2,
            pipeline_value=500000.0,
            win_rate=0.68,
        )
        
        # Create Obeya content
        obeya_content = service.build_obeya_digest_content(
            snapshot_date=date(2026, 1, 7),
            quality_items=[{"id": "q1", "is_red": True, "title": "NCR pending"}],
            red_items=[{"id": "q1", "is_red": True}],
        )
        
        # Generate HQ Share Pack (combined)
        digest = service.generate_hq_share_pack(week_content, obeya_content)
        
        assert digest.digest_type == DigestType.HQ_SHARE_PACK
        assert digest.status == DigestStatus.COMPLETED
        assert digest.page_count >= 4
        assert "Week of" in digest.title
    
    def test_multiple_recipient_delivery(self, service: DigestExportService) -> None:
        """Test delivery to multiple recipients."""
        config = service.create_configuration(
            name="Team Digest",
            digest_type=DigestType.TODAY_SNAPSHOT,
            schedule=DigestSchedule(),
            recipients=[
                create_email_recipient("user1@test.com", "User 1"),
                create_email_recipient("user2@test.com", "User 2"),
                create_in_app_recipient(uuid4(), "User 3"),
            ],
        )
        
        content = TodayDigestContent(
            user_id=uuid4(),
            user_name="Team",
            snapshot_date=date.today(),
        )
        digest = service.generate_today_digest(content, config)
        
        # Deliver to all recipients
        for recipient in config.recipients:
            for channel in recipient.channels:
                service.record_delivery(
                    digest.id,
                    recipient.id,
                    channel,
                    success=True,
                )
        
        results = service.get_delivery_results(digest.id)
        
        # User 1 and 2 have 2 channels each, User 3 has 1
        assert len(results) == 5
        assert all(r.success for r in results)
