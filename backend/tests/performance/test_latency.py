"""
Performance latency tests for Management Software.

Tests critical user flows to ensure performance targets are met:
- Today screen: <500ms for typical data, <1000ms for high volume
- Search API: Database-backed search performance (to be implemented with real DB service)
- PDF generation: Quote/A3 generation performance (to be implemented)

These tests establish performance regression gates.
"""

import pytest
import time
from uuid import uuid4
from datetime import date, timedelta

from sensei.services.today_screen import (
    get_today_screen_service,
    reset_today_screen_service,
    PriorityLevel,
    RiskCategory,
    AbnormalityType,
)


class TestTodayScreenLatency:
    """Test Today screen data aggregation performance."""
    
    def test_today_screen_empty_under_500ms(self):
        """Test Today screen with no data loads under 500ms."""
        # Setup: Fresh service with empty state
        reset_today_screen_service()
        service = get_today_screen_service()
        user_id = uuid4()
        
        # Measure: Get today screen data
        start_time = time.perf_counter()
        result = service.get_today_screen(user_id=user_id, user_name="Test User")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Result is valid
        assert result is not None
        assert len(result.unselected_priorities) == 0
        assert result.total_risk_count == 0
        assert len(result.abnormalities) == 0
        
        # Performance gate: Empty state must be <500ms
        assert latency_ms < 500, f"Today screen latency {latency_ms:.2f}ms exceeds 500ms target"
    
    def test_today_screen_with_typical_data_under_500ms(self):
        """Test Today screen with typical data volume under 500ms."""
        # Setup: Service with typical data (5 priorities, 10 risks, 8 commitments)
        reset_today_screen_service()
        service = get_today_screen_service()
        user_id = uuid4()
        
        # Add typical data
        for i in range(5):
            service.add_priority(
                user_id=user_id,
                title=f"Priority {i+1}",
                entity_type="quote",
                entity_id=uuid4(),
                priority_level=PriorityLevel.HIGH,
            )
        
        for i in range(10):
            service.add_risk(
                title=f"Risk {i+1}",
                category=RiskCategory.QUALITY,
                severity=3,
                probability=4,
            )
        
        for i in range(8):
            # Spread commitments: 3 today, 3 tomorrow, 2 overdue
            if i < 3:
                due_date = date.today()
            elif i < 6:
                due_date = date.today() + timedelta(days=1)
            else:
                due_date = date.today() - timedelta(days=1)
            
            service.add_commitment(
                title=f"Commitment {i+1}",
                commitment_type="delivery",
                due_date=due_date,
                owner_id=user_id,
            )
        
        # Measure: Get today screen data
        start_time = time.perf_counter()
        result = service.get_today_screen(user_id=user_id, user_name="Test User")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Result contains expected data
        assert result is not None
        assert len(result.unselected_priorities) == 5
        assert result.total_risk_count == 10
        # Commitments are split by due date
        total_commitments = (
            len(result.todays_commitments) +
            len(result.tomorrows_commitments) +
            len(result.overdue_commitments)
        )
        assert total_commitments == 8
        
        # Performance gate: Typical data must be <500ms
        assert latency_ms < 500, f"Today screen latency {latency_ms:.2f}ms exceeds 500ms target"
    
    def test_today_screen_with_high_volume_under_1000ms(self):
        """Test Today screen with high data volume under 1000ms."""
        # Setup: Service with high volume data (50 priorities, 100 risks, 80 commitments)
        reset_today_screen_service()
        service = get_today_screen_service()
        user_id = uuid4()
        
        # Add high volume data
        for i in range(50):
            service.add_priority(
                user_id=user_id,
                title=f"Priority {i+1}",
                entity_type="quote",
                entity_id=uuid4(),
                priority_level=PriorityLevel.MEDIUM,
            )
        
        for i in range(100):
            service.add_risk(
                title=f"Risk {i+1}",
                category=RiskCategory.DELIVERY,
                severity=2,
                probability=3,
            )
        
        for i in range(80):
            # Spread commitments across today, tomorrow, and overdue
            day_offset = (i % 30)
            if day_offset < 10:
                due_date = date.today()
            elif day_offset < 20:
                due_date = date.today() + timedelta(days=1)
            else:
                due_date = date.today() - timedelta(days=(day_offset - 19))
            
            service.add_commitment(
                title=f"Commitment {i+1}",
                commitment_type="delivery",
                due_date=due_date,
                owner_id=user_id,
            )
        
        # Measure: Get today screen data
        start_time = time.perf_counter()
        result = service.get_today_screen(user_id=user_id, user_name="Test User")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Result contains expected data
        assert result is not None
        assert len(result.unselected_priorities) == 50
        assert result.total_risk_count == 100
        # Commitments are split by due date
        total_commitments = (
            len(result.todays_commitments) +
            len(result.tomorrows_commitments) +
            len(result.overdue_commitments)
        )
        assert total_commitments == 80
        
        # Performance gate: High volume must be <1000ms
        assert latency_ms < 1000, f"Today screen latency {latency_ms:.2f}ms exceeds 1000ms high-volume target"
    
    def test_top_3_priority_selection_latency_under_100ms(self):
        """Test top 3 priority selection completes under 100ms."""
        # Setup: Service with many priorities
        reset_today_screen_service()
        service = get_today_screen_service()
        user_id = uuid4()
        
        # Add 20 priorities
        priority_ids = []
        for i in range(20):
            priority = service.add_priority(
                user_id=user_id,
                title=f"Priority {i+1}",
                entity_type="quote",
                entity_id=uuid4(),
                priority_level=PriorityLevel.HIGH,
            )
            priority_ids.append(priority.id)
        
        # Measure: Select top 3 priorities
        start_time = time.perf_counter()
        result = service.set_top_priorities(user_id=user_id, priority_ids=priority_ids[:3])
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: 3 priorities selected
        assert len(result) == 3
        assert all(p.is_user_selected for p in result)
        
        # Performance gate: Priority selection must be <100ms
        assert latency_ms < 100, f"Priority selection latency {latency_ms:.2f}ms exceeds 100ms target"
    
    def test_shop_floor_summary_under_300ms(self):
        """Test shop floor summary aggregation under 300ms."""
        # Setup: Service with shop floor data
        reset_today_screen_service()
        service = get_today_screen_service()
        user_id = uuid4()
        
        # Add some work orders at risk
        for i in range(5):
            service.add_work_order_at_risk(
                work_order_number=f"WO-{i+1:04d}",
                product_name=f"Product {i+1}",
                quantity=100 + (i * 10),
                due_date=date.today() + timedelta(days=i+1),
                estimated_completion=date.today() + timedelta(days=i+3),
                reason=f"Material shortage {i+1}",
            )
        
        # Add critical andons
        work_center_id = uuid4()
        for i in range(3):
            service.add_critical_andon(
                andon_type="quality",
                title=f"Quality issue {i+1}",
                work_center_id=work_center_id,
                work_center_name=f"Work Center {i+1}",
                description=f"Issue description {i+1}",
            )
        
        # Add station efficiencies
        for i in range(8):
            service.add_station_efficiency(
                station_id=uuid4(),
                station_name=f"Station {i+1}",
                work_center_id=work_center_id,
                work_center_name="Main Work Center",
                current_efficiency=85.0 + i,
                target_efficiency=90.0,
            )
        
        # Measure: Get shop floor summary
        start_time = time.perf_counter()
        result = service.get_shop_floor_summary(user_id=user_id)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        # Verify: Summary contains expected data
        assert result is not None
        assert len(result.work_orders_at_risk) == 5
        assert len(result.critical_andons) == 3
        assert len(result.low_efficiency_stations) > 0  # Those below target
        
        # Performance gate: Shop floor summary must be <300ms
        assert latency_ms < 300, f"Shop floor summary latency {latency_ms:.2f}ms exceeds 300ms target"
