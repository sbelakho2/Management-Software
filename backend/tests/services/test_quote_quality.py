"""
Tests for Quote Quality Pre-Release Checks Service.

Comprehensive tests for quote validation before release to customers.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sensei.services.sales.quote_quality import (
    QuoteQualityService,
    QuoteData,
    QualityCheckResult,
    QualityCheckItem,
    CheckConfig,
    CheckSeverity,
    CheckCategory,
    CheckResult,
    check_quote_for_release,
    get_blocking_issues,
    get_warnings,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def service() -> QuoteQualityService:
    """Create a service with default config."""
    return QuoteQualityService()


@pytest.fixture
def custom_config() -> CheckConfig:
    """Create custom configuration."""
    return CheckConfig(
        min_margin_percent=Decimal("20.0"),
        margin_floor_percent=Decimal("12.0"),
        min_validity_days=45,
        max_validity_days=120,
        supplier_quote_validity_buffer_days=14,
        require_at_least_one_line_item=True,
        require_line_item_descriptions=True,
        require_payment_terms=True,
        require_delivery_terms=True,
        require_terms_and_conditions=True,
        min_assumptions_count=2,
        require_assumptions=True,
        require_ctq_links=True,
        require_valid_supplier_quotes=True,
        required_custom_fields=["project_type", "complexity"],
    )


@pytest.fixture
def valid_quote() -> QuoteData:
    """Create a fully valid quote."""
    now = datetime.now()
    return QuoteData(
        id=str(uuid4()),
        quote_number="Q-2025-0001",
        status="draft",
        subtotal=Decimal("10000.00"),
        total=Decimal("11000.00"),
        total_cost=Decimal("7000.00"),
        target_margin=Decimal("30.0"),
        actual_margin=Decimal("36.36"),
        currency="USD",
        valid_from=now,
        valid_until=now + timedelta(days=90),
        created_at=now - timedelta(days=1),
        payment_terms="Net 30",
        delivery_terms="FOB Origin",
        lead_time_days=14,
        warranty_terms="1 year standard warranty",
        terms_and_conditions="Standard T&C apply",
        rfq_id=str(uuid4()),
        account_id=str(uuid4()),
        account_name="Acme Corp",
        line_items=[
            {
                "line_number": 1,
                "description": "Widget A",
                "quantity": 10,
                "unit_price": Decimal("500.00"),
                "total": Decimal("5000.00"),
            },
            {
                "line_number": 2,
                "description": "Widget B",
                "quantity": 20,
                "unit_price": Decimal("250.00"),
                "total": Decimal("5000.00"),
            },
        ],
        assumptions=[
            {"id": "a1", "text": "Prices based on current supplier quotes"},
            {"id": "a2", "text": "Delivery within continental US"},
        ],
        supplier_quotes=[
            {
                "supplier_name": "Supplier A",
                "status": "received",
                "valid_until": now + timedelta(days=60),
            },
        ],
        ctq_links=[
            {"id": "c1", "name": "Material Quality", "status": "verified"},
        ],
        custom_fields={"project_type": "standard", "complexity": "medium"},
    )


@pytest.fixture
def minimal_quote() -> QuoteData:
    """Create a minimal quote with issues."""
    return QuoteData(
        id=str(uuid4()),
        quote_number="Q-2025-0002",
        status="draft",
    )


# --------------------------------------------------------------------------
# Basic Service Tests
# --------------------------------------------------------------------------

class TestQuoteQualityServiceBasics:
    """Test basic service functionality."""
    
    def test_service_creation_default_config(self):
        """Test service creation with default config."""
        service = QuoteQualityService()
        assert service.config is not None
        assert service.config.min_margin_percent == Decimal("15.0")
        assert service.config.min_validity_days == 30
    
    def test_service_creation_custom_config(self, custom_config: CheckConfig):
        """Test service creation with custom config."""
        service = QuoteQualityService(custom_config)
        assert service.config.min_margin_percent == Decimal("20.0")
        assert service.config.min_validity_days == 45
        assert "project_type" in service.config.required_custom_fields
    
    def test_check_quote_returns_result(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test that check_quote returns a result."""
        result = service.check_quote(valid_quote)
        
        assert isinstance(result, QualityCheckResult)
        assert result.quote_id == valid_quote.id
        assert result.quote_number == valid_quote.quote_number
        assert result.checked_at is not None
        assert len(result.checks) > 0
    
    def test_valid_quote_can_release(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test that a valid quote can be released."""
        result = service.check_quote(valid_quote)
        
        assert result.can_release is True
        assert result.error_count == 0
    
    def test_minimal_quote_cannot_release(self, service: QuoteQualityService, minimal_quote: QuoteData):
        """Test that a minimal quote cannot be released."""
        result = service.check_quote(minimal_quote)
        
        assert result.can_release is False
        assert result.error_count > 0


# --------------------------------------------------------------------------
# Line Item Checks
# --------------------------------------------------------------------------

class TestLineItemChecks:
    """Test line item validation."""
    
    def test_no_line_items_error(self, service: QuoteQualityService):
        """Test error when no line items."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            line_items=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "line_items_exist"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_has_line_items_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when line items exist."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "line_items_exist"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_missing_descriptions_warning(self, service: QuoteQualityService):
        """Test warning when line items missing descriptions."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            line_items=[
                {"line_number": 1, "quantity": 10, "unit_price": Decimal("100")},
                {"line_number": 2, "description": "Item 2", "quantity": 5, "unit_price": Decimal("50")},
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "line_item_descriptions"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
        assert 1 in check.details["missing_lines"]
    
    def test_zero_price_error(self, service: QuoteQualityService):
        """Test error when line item has zero price."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            line_items=[
                {"line_number": 1, "description": "Free item", "quantity": 10, "unit_price": 0},
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "line_item_prices"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_zero_quantity_error(self, service: QuoteQualityService):
        """Test error when line item has zero quantity."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            line_items=[
                {"line_number": 1, "description": "Item", "quantity": 0, "unit_price": Decimal("100")},
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "line_item_quantities"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR


# --------------------------------------------------------------------------
# Pricing Checks
# --------------------------------------------------------------------------

class TestPricingChecks:
    """Test pricing validation."""
    
    def test_zero_subtotal_error(self, service: QuoteQualityService):
        """Test error when subtotal is zero."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            subtotal=Decimal("0"),
            total=Decimal("0"),
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "subtotal_valid"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_missing_subtotal_error(self, service: QuoteQualityService, minimal_quote: QuoteData):
        """Test error when subtotal is missing."""
        result = service.check_quote(minimal_quote)
        
        check = next((c for c in result.checks if c.check_id == "subtotal_valid"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_valid_subtotal_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when subtotal is valid."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "subtotal_valid"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_valid_total_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when total is valid."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "total_valid"), None)
        assert check is not None
        assert check.result == CheckResult.PASS


# --------------------------------------------------------------------------
# Margin Checks
# --------------------------------------------------------------------------

class TestMarginChecks:
    """Test margin validation."""
    
    def test_margin_not_calculated_warning(self, service: QuoteQualityService):
        """Test warning when margin not calculated."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_calculated"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_margin_below_floor_error(self, service: QuoteQualityService):
        """Test error when margin below floor."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=Decimal("5.0"),  # Below 10% floor
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_floor"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_margin_below_target_warning(self, service: QuoteQualityService):
        """Test warning when margin below target."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=Decimal("12.0"),  # Below 15% target, above 10% floor
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_target"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_margin_meets_target_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when margin meets target."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_target"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_margin_vs_custom_target(self, service: QuoteQualityService):
        """Test margin vs quote-specific target."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=Decimal("25.0"),
            target_margin=Decimal("30.0"),  # Custom target not met
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_vs_target"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL


# --------------------------------------------------------------------------
# Validity Checks
# --------------------------------------------------------------------------

class TestValidityChecks:
    """Test validity period validation."""
    
    def test_missing_valid_from_warning(self, service: QuoteQualityService):
        """Test warning when valid_from not set."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            valid_from=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "validity_from_set"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_missing_valid_until_error(self, service: QuoteQualityService):
        """Test error when valid_until not set."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            valid_until=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "validity_until_set"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_already_expired_error(self, service: QuoteQualityService):
        """Test error when quote already expired."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            valid_until=datetime.now() - timedelta(days=1),
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "not_expired"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_validity_too_short_warning(self, service: QuoteQualityService):
        """Test warning when validity period too short."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            valid_until=datetime.now() + timedelta(days=15),  # Only 15 days, need 30
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "validity_duration"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_valid_validity_period_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when validity period is adequate."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "validity_duration"), None)
        assert check is not None
        assert check.result == CheckResult.PASS


# --------------------------------------------------------------------------
# Terms Checks
# --------------------------------------------------------------------------

class TestTermsChecks:
    """Test terms and conditions validation."""
    
    def test_missing_payment_terms_warning(self, service: QuoteQualityService):
        """Test warning when payment terms missing."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            payment_terms=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "payment_terms"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_missing_delivery_terms_warning(self, service: QuoteQualityService):
        """Test warning when delivery terms missing."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            delivery_terms=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "delivery_terms"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_missing_tandc_warning(self, service: QuoteQualityService):
        """Test warning when T&C missing."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            terms_and_conditions=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "terms_and_conditions"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_missing_lead_time_info(self, service: QuoteQualityService):
        """Test info when lead time missing."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            lead_time_days=None,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "lead_time"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.INFO
    
    def test_all_terms_present_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when all terms present."""
        result = service.check_quote(valid_quote)
        
        for check_id in ["payment_terms", "delivery_terms", "terms_and_conditions", "lead_time"]:
            check = next((c for c in result.checks if c.check_id == check_id), None)
            assert check is not None
            assert check.result == CheckResult.PASS


# --------------------------------------------------------------------------
# Assumption Checks
# --------------------------------------------------------------------------

class TestAssumptionChecks:
    """Test assumption validation."""
    
    def test_no_assumptions_warning(self, service: QuoteQualityService):
        """Test warning when no assumptions documented."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            assumptions=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "assumptions_exist"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_insufficient_assumptions(self, custom_config: CheckConfig):
        """Test warning when not enough assumptions."""
        service = QuoteQualityService(custom_config)  # Requires min 2 assumptions
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            assumptions=[{"id": "a1", "text": "Only one assumption"}],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "assumptions_count"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_assumptions_disabled_skip(self):
        """Test skip when assumptions not required."""
        config = CheckConfig(require_assumptions=False)
        service = QuoteQualityService(config)
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            assumptions=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "assumptions"), None)
        assert check is not None
        assert check.result == CheckResult.SKIP
    
    def test_assumptions_present_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when assumptions present."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "assumptions_exist"), None)
        assert check is not None
        assert check.result == CheckResult.PASS


# --------------------------------------------------------------------------
# Supplier Quote Checks
# --------------------------------------------------------------------------

class TestSupplierQuoteChecks:
    """Test supplier quote validation."""
    
    def test_no_supplier_quotes_skip(self, service: QuoteQualityService):
        """Test skip when no supplier quotes."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes"), None)
        assert check is not None
        assert check.result == CheckResult.SKIP
    
    def test_expired_supplier_quote_error(self, service: QuoteQualityService):
        """Test error when supplier quote expired."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[
                {
                    "supplier_name": "Supplier A",
                    "status": "received",
                    "valid_until": datetime.now() - timedelta(days=5),
                },
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes_expired"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
        assert "Supplier A" in check.details["expired"]
    
    def test_expiring_soon_supplier_quote_warning(self, service: QuoteQualityService):
        """Test warning when supplier quote expiring soon."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[
                {
                    "supplier_name": "Supplier B",
                    "status": "received",
                    "valid_until": datetime.now() + timedelta(days=3),  # Within 7 day buffer
                },
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes_expiring"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_pending_supplier_quote_warning(self, service: QuoteQualityService):
        """Test warning when supplier quote pending."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[
                {
                    "supplier_name": "Supplier C",
                    "status": "pending",
                },
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes_pending"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_valid_supplier_quotes_pass(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test pass when supplier quotes valid."""
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes_expired"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_supplier_quote_iso_date_string(self, service: QuoteQualityService):
        """Test parsing ISO date string in supplier quote."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[
                {
                    "supplier_name": "Supplier D",
                    "status": "received",
                    "valid_until": (datetime.now() - timedelta(days=1)).isoformat(),
                },
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "supplier_quotes_expired"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL


# --------------------------------------------------------------------------
# CTQ Link Checks
# --------------------------------------------------------------------------

class TestCTQLinkChecks:
    """Test CTQ link validation."""
    
    def test_ctq_disabled_skip(self, service: QuoteQualityService):
        """Test skip when CTQ not required (default)."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            ctq_links=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "ctq_links"), None)
        assert check is not None
        assert check.result == CheckResult.SKIP
    
    def test_no_ctq_links_warning_when_required(self, custom_config: CheckConfig):
        """Test warning when CTQ required but not linked."""
        service = QuoteQualityService(custom_config)
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            ctq_links=[],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "ctq_links"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.WARNING
    
    def test_ctq_links_present_pass(self, custom_config: CheckConfig):
        """Test pass when CTQ links present."""
        service = QuoteQualityService(custom_config)
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            ctq_links=[
                {"id": "c1", "name": "Quality Spec", "status": "verified"},
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "ctq_links"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_open_ctqs_info(self, custom_config: CheckConfig):
        """Test info about open CTQs."""
        service = QuoteQualityService(custom_config)
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            ctq_links=[
                {"id": "c1", "name": "Quality Spec", "status": "open"},
                {"id": "c2", "name": "Dimension Check", "status": "verified"},
            ],
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "ctq_status"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.INFO
        assert "Quality Spec" in check.message


# --------------------------------------------------------------------------
# Approval Checks
# --------------------------------------------------------------------------

class TestApprovalChecks:
    """Test approval validation."""
    
    def test_no_approval_required_pass(self, service: QuoteQualityService):
        """Test pass when no approval required."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            requires_approval=False,
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "approval_required"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_approval_required_not_obtained_error(self, service: QuoteQualityService):
        """Test error when approval required but not obtained."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            requires_approval=True,
            approval_status="pending",
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "approval_obtained"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR
    
    def test_approval_obtained_pass(self, service: QuoteQualityService):
        """Test pass when approval obtained."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            requires_approval=True,
            approval_status="approved",
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "approval_obtained"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_over_threshold_not_approved_error(self, service: QuoteQualityService):
        """Test error when over threshold and not approved."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            total=Decimal("100000"),
            requires_approval=True,
            approval_status="pending",
            approval_threshold=Decimal("50000"),
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "approval_threshold"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert check.severity == CheckSeverity.ERROR


# --------------------------------------------------------------------------
# Custom Field Checks
# --------------------------------------------------------------------------

class TestCustomFieldChecks:
    """Test custom field validation."""
    
    def test_no_required_custom_fields(self, service: QuoteQualityService):
        """Test no checks when no required custom fields."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "custom_fields"), None)
        assert check is None  # No check added
    
    def test_missing_required_custom_fields(self, custom_config: CheckConfig):
        """Test warning when required custom fields missing."""
        service = QuoteQualityService(custom_config)
        
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            custom_fields={"project_type": "standard"},  # Missing "complexity"
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "custom_fields"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
        assert "complexity" in check.details["missing"]
    
    def test_all_custom_fields_present(self, custom_config: CheckConfig, valid_quote: QuoteData):
        """Test pass when all required custom fields present."""
        service = QuoteQualityService(custom_config)
        
        result = service.check_quote(valid_quote)
        
        check = next((c for c in result.checks if c.check_id == "custom_fields"), None)
        assert check is not None
        assert check.result == CheckResult.PASS


# --------------------------------------------------------------------------
# Score Calculation
# --------------------------------------------------------------------------

class TestScoreCalculation:
    """Test quality score calculation."""
    
    def test_perfect_score(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test perfect score for valid quote."""
        result = service.check_quote(valid_quote)
        
        # Should have high score
        assert result.score >= 90.0
    
    def test_low_score_for_many_issues(self, service: QuoteQualityService, minimal_quote: QuoteData):
        """Test low score for quote with many issues."""
        result = service.check_quote(minimal_quote)
        
        # Should have low score due to errors
        assert result.score < 50.0
    
    def test_score_weights_errors_heavily(self, service: QuoteQualityService):
        """Test that errors are weighted more than warnings."""
        # Quote with one error
        quote_error = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            subtotal=Decimal("1000"),
            total=Decimal("1100"),
            actual_margin=Decimal("20"),
            valid_until=datetime.now() + timedelta(days=60),
            payment_terms="Net 30",
            delivery_terms="FOB",
            terms_and_conditions="T&C",
            line_items=[{"line_number": 1, "description": "Item", "quantity": 1, "unit_price": 0}],  # Error: zero price
            assumptions=[{"id": "a1", "text": "Assumption"}],
        )
        
        result = service.check_quote(quote_error)
        
        # Should have score penalty but not catastrophic
        assert result.score < 100
        assert result.error_count >= 1


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_check_quote_for_release(self):
        """Test convenience function."""
        quote_dict = {
            "id": str(uuid4()),
            "quote_number": "Q-001",
            "status": "draft",
            "subtotal": 1000,
            "total": 1100,
            "actual_margin": 20,
            "valid_until": datetime.now() + timedelta(days=60),
            "payment_terms": "Net 30",
            "delivery_terms": "FOB",
            "terms_and_conditions": "T&C",
            "line_items": [{"line_number": 1, "description": "Item", "quantity": 10, "unit_price": 100}],
            "assumptions": [{"id": "a1", "text": "Assumption"}],
        }
        
        result = check_quote_for_release(quote_dict)
        
        assert isinstance(result, QualityCheckResult)
        assert result.quote_number == "Q-001"
    
    def test_check_quote_for_release_with_config(self):
        """Test convenience function with custom config."""
        quote_dict = {
            "id": str(uuid4()),
            "quote_number": "Q-002",
            "status": "draft",
            "actual_margin": 18,  # Below 20% target in custom config
        }
        
        config = CheckConfig(min_margin_percent=Decimal("20.0"))
        result = check_quote_for_release(quote_dict, config)
        
        check = next((c for c in result.checks if c.check_id == "margin_target"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_get_blocking_issues(self, service: QuoteQualityService, minimal_quote: QuoteData):
        """Test getting only blocking issues."""
        result = service.check_quote(minimal_quote)
        blocking = get_blocking_issues(result)
        
        assert len(blocking) > 0
        for issue in blocking:
            assert issue.severity == CheckSeverity.ERROR
            assert issue.result == CheckResult.FAIL
    
    def test_get_warnings(self, service: QuoteQualityService, minimal_quote: QuoteData):
        """Test getting only warnings."""
        result = service.check_quote(minimal_quote)
        warnings = get_warnings(result)
        
        for warning in warnings:
            assert warning.severity == CheckSeverity.WARNING
            assert warning.result == CheckResult.FAIL


# --------------------------------------------------------------------------
# Quality Check Result
# --------------------------------------------------------------------------

class TestQualityCheckResult:
    """Test QualityCheckResult operations."""
    
    def test_add_check_updates_counters(self):
        """Test that add_check updates counters."""
        result = QualityCheckResult(
            quote_id="q1",
            quote_number="Q-001",
            checked_at=datetime.now(),
            checks=[],
        )
        
        # Add error
        result.add_check(QualityCheckItem(
            check_id="test1",
            name="Test 1",
            description="Test check",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.ERROR,
            result=CheckResult.FAIL,
        ))
        
        assert result.error_count == 1
        assert result.can_release is False
        
        # Add warning
        result.add_check(QualityCheckItem(
            check_id="test2",
            name="Test 2",
            description="Test check",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.WARNING,
            result=CheckResult.FAIL,
        ))
        
        assert result.warning_count == 1
        
        # Add info
        result.add_check(QualityCheckItem(
            check_id="test3",
            name="Test 3",
            description="Test check",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.INFO,
            result=CheckResult.FAIL,
        ))
        
        assert result.info_count == 1
    
    def test_passing_check_doesnt_block(self):
        """Test that passing checks don't block release."""
        result = QualityCheckResult(
            quote_id="q1",
            quote_number="Q-001",
            checked_at=datetime.now(),
            checks=[],
        )
        
        result.add_check(QualityCheckItem(
            check_id="test1",
            name="Test 1",
            description="Test check",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.ERROR,
            result=CheckResult.PASS,
        ))
        
        assert result.error_count == 0
        assert result.can_release is True


# --------------------------------------------------------------------------
# Edge Cases
# --------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string_terms_treated_as_missing(self, service: QuoteQualityService):
        """Test empty strings treated as missing."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            payment_terms="",
            delivery_terms="",
            terms_and_conditions="",
        )
        
        result = service.check_quote(quote)
        
        for check_id in ["payment_terms", "delivery_terms", "terms_and_conditions"]:
            check = next((c for c in result.checks if c.check_id == check_id), None)
            assert check is not None
            assert check.result == CheckResult.FAIL
    
    def test_zero_margin_below_floor(self, service: QuoteQualityService):
        """Test zero margin is below floor."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=Decimal("0"),
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_floor"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_negative_margin_below_floor(self, service: QuoteQualityService):
        """Test negative margin is below floor."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            actual_margin=Decimal("-5"),
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "margin_floor"), None)
        assert check is not None
        assert check.result == CheckResult.FAIL
    
    def test_exactly_at_validity_threshold(self, service: QuoteQualityService):
        """Test validity exactly at threshold."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            valid_until=datetime.now() + timedelta(days=31),  # Just over 30 days
        )
        
        result = service.check_quote(quote)
        
        check = next((c for c in result.checks if c.check_id == "validity_duration"), None)
        assert check is not None
        assert check.result == CheckResult.PASS
    
    def test_multiple_suppliers_mixed_status(self, service: QuoteQualityService):
        """Test multiple supplier quotes with mixed status."""
        now = datetime.now()
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            supplier_quotes=[
                {"supplier_name": "Good", "status": "received", "valid_until": now + timedelta(days=60)},
                {"supplier_name": "Expired", "status": "received", "valid_until": now - timedelta(days=5)},
                {"supplier_name": "Pending", "status": "pending"},
                {"supplier_name": "Expiring", "status": "received", "valid_until": now + timedelta(days=3)},
            ],
        )
        
        result = service.check_quote(quote)
        
        # Should have expired error
        expired_check = next((c for c in result.checks if c.check_id == "supplier_quotes_expired"), None)
        assert expired_check is not None
        assert expired_check.result == CheckResult.FAIL
        assert "Expired" in expired_check.details["expired"]
        
        # Should have pending warning
        pending_check = next((c for c in result.checks if c.check_id == "supplier_quotes_pending"), None)
        assert pending_check is not None
        assert pending_check.result == CheckResult.FAIL


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete scenarios."""
    
    def test_full_validation_workflow(self, service: QuoteQualityService, valid_quote: QuoteData):
        """Test complete validation workflow."""
        # Run checks
        result = service.check_quote(valid_quote)
        
        # Should pass all critical checks
        assert result.can_release is True
        assert result.error_count == 0
        
        # Should have reasonable score
        assert result.score >= 80.0
        
        # Should have timestamp
        assert result.checked_at is not None
    
    def test_blocking_prevents_release(self, service: QuoteQualityService):
        """Test that blocking issues prevent release."""
        # Quote with blocking issue (no line items)
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            subtotal=Decimal("1000"),
            total=Decimal("1100"),
            actual_margin=Decimal("20"),
            valid_until=datetime.now() + timedelta(days=60),
            payment_terms="Net 30",
            delivery_terms="FOB",
            terms_and_conditions="T&C",
            line_items=[],  # Missing line items - blocking
            assumptions=[{"id": "a1", "text": "Assumption"}],
        )
        
        result = service.check_quote(quote)
        
        # Should not be releasable
        assert result.can_release is False
        
        # Should identify specific blocking issue
        blocking = get_blocking_issues(result)
        check_ids = [c.check_id for c in blocking]
        assert "line_items_exist" in check_ids
    
    def test_warnings_allow_release_with_caution(self, service: QuoteQualityService):
        """Test that warnings allow release but are tracked."""
        quote = QuoteData(
            id="q1",
            quote_number="Q-001",
            status="draft",
            subtotal=Decimal("1000"),
            total=Decimal("1100"),
            actual_margin=Decimal("12"),  # Below target but above floor
            valid_until=datetime.now() + timedelta(days=60),
            payment_terms=None,  # Warning: missing
            delivery_terms="FOB",
            terms_and_conditions="T&C",
            line_items=[{"line_number": 1, "description": "Item", "quantity": 10, "unit_price": 100}],
            assumptions=[{"id": "a1", "text": "Assumption"}],
        )
        
        result = service.check_quote(quote)
        
        # Should be releasable (no errors)
        assert result.can_release is True
        
        # But should have warnings
        assert result.warning_count > 0
        
        warnings = get_warnings(result)
        assert len(warnings) > 0
