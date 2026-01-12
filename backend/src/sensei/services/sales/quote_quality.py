"""
Quote Quality Pre-Release Checks Service.

Validates quotes before release to customers by checking:
- Missing assumptions
- Supplier quote validity
- CTQ links
- Margin compliance
- Required approvals
- Missing line items
- Invalid pricing
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class CheckSeverity(str, Enum):
    """Severity level for quality checks."""
    
    ERROR = "error"  # Must be fixed before release
    WARNING = "warning"  # Should be reviewed but not blocking
    INFO = "info"  # Informational only


class CheckCategory(str, Enum):
    """Category of quality check."""
    
    COMPLETENESS = "completeness"  # Missing required data
    PRICING = "pricing"  # Pricing/margin issues
    VALIDITY = "validity"  # Expiration/validity issues
    COMPLIANCE = "compliance"  # Compliance requirements
    APPROVAL = "approval"  # Approval requirements
    CTQ = "ctq"  # CTQ linkage
    SUPPLIER = "supplier"  # Supplier quote issues
    TERMS = "terms"  # Terms and conditions


class CheckResult(str, Enum):
    """Result of a quality check."""
    
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"  # Not applicable


@dataclass
class QualityCheckItem:
    """A single quality check result."""
    
    check_id: str
    name: str
    description: str
    category: CheckCategory
    severity: CheckSeverity
    result: CheckResult
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    fix_suggestion: str = ""


@dataclass
class QualityCheckResult:
    """Overall quality check result for a quote."""
    
    quote_id: str
    quote_number: str
    checked_at: datetime
    checks: list[QualityCheckItem]
    can_release: bool = True
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    score: float = 100.0  # 0-100 quality score
    
    def add_check(self, check: QualityCheckItem) -> None:
        """Add a check result and update counters."""
        self.checks.append(check)
        
        if check.result == CheckResult.FAIL:
            if check.severity == CheckSeverity.ERROR:
                self.error_count += 1
                self.can_release = False
            elif check.severity == CheckSeverity.WARNING:
                self.warning_count += 1
            else:
                self.info_count += 1
    
    def calculate_score(self) -> None:
        """Calculate quality score based on check results."""
        if not self.checks:
            self.score = 100.0
            return
        
        total_weight = 0.0
        weighted_score = 0.0
        
        weights = {
            CheckSeverity.ERROR: 10.0,
            CheckSeverity.WARNING: 3.0,
            CheckSeverity.INFO: 1.0,
        }
        
        for check in self.checks:
            if check.result == CheckResult.SKIP:
                continue
            
            weight = weights.get(check.severity, 1.0)
            total_weight += weight
            
            if check.result == CheckResult.PASS:
                weighted_score += weight
        
        if total_weight > 0:
            self.score = (weighted_score / total_weight) * 100.0
        else:
            self.score = 100.0


@dataclass
class QuoteData:
    """Input data for quote quality checks."""
    
    id: str
    quote_number: str
    status: str
    
    # Pricing
    subtotal: Decimal | None = None
    total: Decimal | None = None
    total_cost: Decimal | None = None
    target_margin: Decimal | None = None
    actual_margin: Decimal | None = None
    currency: str = "USD"
    
    # Dates
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    created_at: datetime | None = None
    
    # Terms
    payment_terms: str | None = None
    delivery_terms: str | None = None
    lead_time_days: int | None = None
    warranty_terms: str | None = None
    terms_and_conditions: str | None = None
    
    # Notes
    internal_notes: str | None = None
    customer_notes: str | None = None
    
    # Approval
    requires_approval: bool = False
    approval_status: str = "not_required"
    approval_threshold: Decimal | None = None
    
    # Related entities
    rfq_id: str | None = None
    opportunity_id: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    
    # Line items
    line_items: list[dict[str, Any]] = field(default_factory=list)
    
    # Assumptions
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    
    # Supplier quotes
    supplier_quotes: list[dict[str, Any]] = field(default_factory=list)
    
    # CTQ links
    ctq_links: list[dict[str, Any]] = field(default_factory=list)
    
    # Custom fields
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckConfig:
    """Configuration for quality checks."""
    
    # Margin thresholds
    min_margin_percent: Decimal = Decimal("15.0")
    margin_floor_percent: Decimal = Decimal("10.0")
    
    # Validity
    min_validity_days: int = 30
    max_validity_days: int = 180
    supplier_quote_validity_buffer_days: int = 7
    
    # Line items
    require_at_least_one_line_item: bool = True
    require_line_item_descriptions: bool = True
    
    # Terms
    require_payment_terms: bool = True
    require_delivery_terms: bool = True
    require_terms_and_conditions: bool = True
    
    # Assumptions
    min_assumptions_count: int = 0
    require_assumptions: bool = True
    
    # CTQ
    require_ctq_links: bool = False
    
    # Supplier quotes
    require_valid_supplier_quotes: bool = True
    
    # Custom required fields
    required_custom_fields: list[str] = field(default_factory=list)


class QuoteQualityService:
    """Service for performing quote quality pre-release checks."""
    
    def __init__(self, config: CheckConfig | None = None) -> None:
        """Initialize the service with configuration."""
        self.config = config or CheckConfig()
    
    def check_quote(self, quote: QuoteData) -> QualityCheckResult:
        """Perform all quality checks on a quote."""
        result = QualityCheckResult(
            quote_id=quote.id,
            quote_number=quote.quote_number,
            checked_at=datetime.now(),
            checks=[],
        )
        
        # Run all checks
        self._check_line_items(quote, result)
        self._check_pricing(quote, result)
        self._check_margins(quote, result)
        self._check_validity(quote, result)
        self._check_terms(quote, result)
        self._check_assumptions(quote, result)
        self._check_supplier_quotes(quote, result)
        self._check_ctq_links(quote, result)
        self._check_approval(quote, result)
        self._check_custom_fields(quote, result)
        
        # Calculate final score
        result.calculate_score()
        
        return result
    
    def _check_line_items(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check line items for completeness."""
        # Check for at least one line item
        if self.config.require_at_least_one_line_item:
            check = QualityCheckItem(
                check_id="line_items_exist",
                name="Line Items Present",
                description="Quote has at least one line item",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.ERROR,
                result=CheckResult.PASS if quote.line_items else CheckResult.FAIL,
                message="" if quote.line_items else "Quote has no line items",
                fix_suggestion="Add at least one line item to the quote",
                details={"line_item_count": len(quote.line_items)},
            )
            result.add_check(check)
        
        # Check line item details
        if quote.line_items:
            missing_descriptions = []
            zero_price_items = []
            zero_quantity_items = []
            
            for i, item in enumerate(quote.line_items):
                line_num = item.get("line_number", i + 1)
                
                if self.config.require_line_item_descriptions:
                    if not item.get("description"):
                        missing_descriptions.append(line_num)
                
                if item.get("unit_price") is None or Decimal(str(item.get("unit_price", 0))) <= 0:
                    zero_price_items.append(line_num)
                
                if item.get("quantity") is None or int(item.get("quantity", 0)) <= 0:
                    zero_quantity_items.append(line_num)
            
            # Missing descriptions
            if self.config.require_line_item_descriptions:
                check = QualityCheckItem(
                    check_id="line_item_descriptions",
                    name="Line Item Descriptions",
                    description="All line items have descriptions",
                    category=CheckCategory.COMPLETENESS,
                    severity=CheckSeverity.WARNING,
                    result=CheckResult.FAIL if missing_descriptions else CheckResult.PASS,
                    message=f"Lines {missing_descriptions} missing descriptions" if missing_descriptions else "",
                    fix_suggestion="Add descriptions to all line items",
                    details={"missing_lines": missing_descriptions},
                )
                result.add_check(check)
            
            # Zero prices
            check = QualityCheckItem(
                check_id="line_item_prices",
                name="Line Item Prices",
                description="All line items have valid prices",
                category=CheckCategory.PRICING,
                severity=CheckSeverity.ERROR,
                result=CheckResult.FAIL if zero_price_items else CheckResult.PASS,
                message=f"Lines {zero_price_items} have zero or missing prices" if zero_price_items else "",
                fix_suggestion="Set valid prices for all line items",
                details={"zero_price_lines": zero_price_items},
            )
            result.add_check(check)
            
            # Zero quantities
            check = QualityCheckItem(
                check_id="line_item_quantities",
                name="Line Item Quantities",
                description="All line items have valid quantities",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.ERROR,
                result=CheckResult.FAIL if zero_quantity_items else CheckResult.PASS,
                message=f"Lines {zero_quantity_items} have zero or missing quantities" if zero_quantity_items else "",
                fix_suggestion="Set valid quantities for all line items",
                details={"zero_quantity_lines": zero_quantity_items},
            )
            result.add_check(check)
    
    def _check_pricing(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check pricing validity."""
        # Check subtotal
        has_subtotal = quote.subtotal is not None and quote.subtotal > 0
        check = QualityCheckItem(
            check_id="subtotal_valid",
            name="Subtotal Valid",
            description="Quote has a valid subtotal",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.ERROR,
            result=CheckResult.PASS if has_subtotal else CheckResult.FAIL,
            message="" if has_subtotal else "Quote subtotal is zero or missing",
            fix_suggestion="Ensure line items are priced correctly",
            details={"subtotal": str(quote.subtotal) if quote.subtotal else "0"},
        )
        result.add_check(check)
        
        # Check total
        has_total = quote.total is not None and quote.total > 0
        check = QualityCheckItem(
            check_id="total_valid",
            name="Total Valid",
            description="Quote has a valid total",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.ERROR,
            result=CheckResult.PASS if has_total else CheckResult.FAIL,
            message="" if has_total else "Quote total is zero or missing",
            fix_suggestion="Calculate quote totals",
            details={"total": str(quote.total) if quote.total else "0"},
        )
        result.add_check(check)
    
    def _check_margins(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check margin compliance."""
        # Check if margin is calculated
        if quote.actual_margin is None:
            check = QualityCheckItem(
                check_id="margin_calculated",
                name="Margin Calculated",
                description="Quote margin has been calculated",
                category=CheckCategory.PRICING,
                severity=CheckSeverity.WARNING,
                result=CheckResult.FAIL,
                message="Margin has not been calculated",
                fix_suggestion="Enter cost data and calculate margin",
            )
            result.add_check(check)
            return
        
        margin = quote.actual_margin
        
        # Check margin floor
        below_floor = margin < self.config.margin_floor_percent
        check = QualityCheckItem(
            check_id="margin_floor",
            name="Margin Above Floor",
            description=f"Margin is above minimum floor of {self.config.margin_floor_percent}%",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.ERROR,
            result=CheckResult.FAIL if below_floor else CheckResult.PASS,
            message=f"Margin {margin}% is below floor of {self.config.margin_floor_percent}%" if below_floor else "",
            fix_suggestion="Increase pricing or reduce costs to meet minimum margin",
            details={"actual_margin": str(margin), "floor": str(self.config.margin_floor_percent)},
        )
        result.add_check(check)
        
        # Check target margin
        below_target = margin < self.config.min_margin_percent
        check = QualityCheckItem(
            check_id="margin_target",
            name="Margin Meets Target",
            description=f"Margin meets target of {self.config.min_margin_percent}%",
            category=CheckCategory.PRICING,
            severity=CheckSeverity.WARNING,
            result=CheckResult.FAIL if below_target else CheckResult.PASS,
            message=f"Margin {margin}% is below target of {self.config.min_margin_percent}%" if below_target else "",
            fix_suggestion="Consider increasing pricing to meet target margin",
            details={"actual_margin": str(margin), "target": str(self.config.min_margin_percent)},
        )
        result.add_check(check)
        
        # Check if target was set
        if quote.target_margin is not None:
            meets_own_target = margin >= quote.target_margin
            check = QualityCheckItem(
                check_id="margin_vs_target",
                name="Margin vs. Target",
                description=f"Margin meets quote-specific target of {quote.target_margin}%",
                category=CheckCategory.PRICING,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if meets_own_target else CheckResult.FAIL,
                message=f"Margin {margin}% is below target of {quote.target_margin}%" if not meets_own_target else "",
                fix_suggestion="Adjust pricing to meet your target margin",
                details={"actual_margin": str(margin), "target_margin": str(quote.target_margin)},
            )
            result.add_check(check)
    
    def _check_validity(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check validity period."""
        now = datetime.now()
        
        # Check valid_from is set
        has_valid_from = quote.valid_from is not None
        check = QualityCheckItem(
            check_id="validity_from_set",
            name="Valid From Date Set",
            description="Quote has a valid from date",
            category=CheckCategory.VALIDITY,
            severity=CheckSeverity.WARNING,
            result=CheckResult.PASS if has_valid_from else CheckResult.FAIL,
            message="" if has_valid_from else "Valid from date not set",
            fix_suggestion="Set the valid from date",
        )
        result.add_check(check)
        
        # Check valid_until is set
        has_valid_until = quote.valid_until is not None
        check = QualityCheckItem(
            check_id="validity_until_set",
            name="Valid Until Date Set",
            description="Quote has an expiration date",
            category=CheckCategory.VALIDITY,
            severity=CheckSeverity.ERROR,
            result=CheckResult.PASS if has_valid_until else CheckResult.FAIL,
            message="" if has_valid_until else "Expiration date not set",
            fix_suggestion="Set the quote expiration date",
        )
        result.add_check(check)
        
        if quote.valid_until:
            # Check not already expired
            is_expired = quote.valid_until < now
            check = QualityCheckItem(
                check_id="not_expired",
                name="Quote Not Expired",
                description="Quote validity has not passed",
                category=CheckCategory.VALIDITY,
                severity=CheckSeverity.ERROR,
                result=CheckResult.FAIL if is_expired else CheckResult.PASS,
                message="Quote has already expired" if is_expired else "",
                fix_suggestion="Update the expiration date",
                details={"valid_until": quote.valid_until.isoformat()},
            )
            result.add_check(check)
            
            # Check minimum validity period
            days_valid = (quote.valid_until - now).days
            min_days = self.config.min_validity_days
            too_short = days_valid < min_days
            check = QualityCheckItem(
                check_id="validity_duration",
                name="Adequate Validity Period",
                description=f"Quote valid for at least {min_days} days",
                category=CheckCategory.VALIDITY,
                severity=CheckSeverity.WARNING,
                result=CheckResult.FAIL if too_short else CheckResult.PASS,
                message=f"Only {days_valid} days validity (minimum {min_days})" if too_short else "",
                fix_suggestion=f"Extend validity to at least {min_days} days",
                details={"days_valid": days_valid, "min_days": min_days},
            )
            result.add_check(check)
    
    def _check_terms(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check terms and conditions."""
        # Payment terms
        if self.config.require_payment_terms:
            has_payment = bool(quote.payment_terms)
            check = QualityCheckItem(
                check_id="payment_terms",
                name="Payment Terms Defined",
                description="Quote has payment terms",
                category=CheckCategory.TERMS,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if has_payment else CheckResult.FAIL,
                message="" if has_payment else "Payment terms not defined",
                fix_suggestion="Add payment terms (e.g., Net 30)",
            )
            result.add_check(check)
        
        # Delivery terms
        if self.config.require_delivery_terms:
            has_delivery = bool(quote.delivery_terms)
            check = QualityCheckItem(
                check_id="delivery_terms",
                name="Delivery Terms Defined",
                description="Quote has delivery terms",
                category=CheckCategory.TERMS,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if has_delivery else CheckResult.FAIL,
                message="" if has_delivery else "Delivery terms not defined",
                fix_suggestion="Add delivery terms (e.g., FOB, CIF)",
            )
            result.add_check(check)
        
        # Terms and conditions
        if self.config.require_terms_and_conditions:
            has_terms = bool(quote.terms_and_conditions)
            check = QualityCheckItem(
                check_id="terms_and_conditions",
                name="Terms and Conditions",
                description="Quote has terms and conditions",
                category=CheckCategory.TERMS,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if has_terms else CheckResult.FAIL,
                message="" if has_terms else "Terms and conditions not defined",
                fix_suggestion="Add standard terms and conditions",
            )
            result.add_check(check)
        
        # Lead time
        has_lead_time = quote.lead_time_days is not None and quote.lead_time_days > 0
        check = QualityCheckItem(
            check_id="lead_time",
            name="Lead Time Defined",
            description="Quote has lead time specified",
            category=CheckCategory.TERMS,
            severity=CheckSeverity.INFO,
            result=CheckResult.PASS if has_lead_time else CheckResult.FAIL,
            message="" if has_lead_time else "Lead time not specified",
            fix_suggestion="Specify expected lead time in days",
        )
        result.add_check(check)
    
    def _check_assumptions(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check assumptions are documented."""
        if not self.config.require_assumptions:
            check = QualityCheckItem(
                check_id="assumptions",
                name="Assumptions Documented",
                description="Quote assumptions are documented",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.INFO,
                result=CheckResult.SKIP,
                message="Assumptions check disabled",
            )
            result.add_check(check)
            return
        
        has_assumptions = len(quote.assumptions) > 0
        min_count = self.config.min_assumptions_count
        
        if min_count > 0:
            enough_assumptions = len(quote.assumptions) >= min_count
            check = QualityCheckItem(
                check_id="assumptions_count",
                name="Sufficient Assumptions",
                description=f"Quote has at least {min_count} documented assumptions",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if enough_assumptions else CheckResult.FAIL,
                message="" if enough_assumptions else f"Only {len(quote.assumptions)} assumptions (minimum {min_count})",
                fix_suggestion="Document key assumptions for the quote",
                details={"count": len(quote.assumptions), "minimum": min_count},
            )
            result.add_check(check)
        else:
            check = QualityCheckItem(
                check_id="assumptions_exist",
                name="Assumptions Documented",
                description="Quote has documented assumptions",
                category=CheckCategory.COMPLETENESS,
                severity=CheckSeverity.WARNING,
                result=CheckResult.PASS if has_assumptions else CheckResult.FAIL,
                message="" if has_assumptions else "No assumptions documented",
                fix_suggestion="Document key assumptions for the quote",
                details={"count": len(quote.assumptions)},
            )
            result.add_check(check)
    
    def _check_supplier_quotes(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check supplier quote validity."""
        if not self.config.require_valid_supplier_quotes:
            return
        
        if not quote.supplier_quotes:
            # No supplier quotes to check - this might be okay
            check = QualityCheckItem(
                check_id="supplier_quotes",
                name="Supplier Quotes",
                description="Supplier quotes are valid",
                category=CheckCategory.SUPPLIER,
                severity=CheckSeverity.INFO,
                result=CheckResult.SKIP,
                message="No supplier quotes attached",
            )
            result.add_check(check)
            return
        
        now = datetime.now()
        buffer_days = self.config.supplier_quote_validity_buffer_days
        
        expired_quotes = []
        expiring_soon = []
        pending_quotes = []
        
        for sq in quote.supplier_quotes:
            supplier_name = sq.get("supplier_name", "Unknown")
            status = sq.get("status", "")
            valid_until = sq.get("valid_until")
            
            # Parse valid_until if it's a string
            if isinstance(valid_until, str):
                try:
                    valid_until = datetime.fromisoformat(valid_until.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    valid_until = None
            
            if status == "pending" or status == "requested":
                pending_quotes.append(supplier_name)
            elif valid_until:
                if valid_until < now:
                    expired_quotes.append(supplier_name)
                elif valid_until < now + timedelta(days=buffer_days):
                    expiring_soon.append(supplier_name)
        
        # Expired supplier quotes
        check = QualityCheckItem(
            check_id="supplier_quotes_expired",
            name="Supplier Quotes Not Expired",
            description="All supplier quotes are still valid",
            category=CheckCategory.SUPPLIER,
            severity=CheckSeverity.ERROR,
            result=CheckResult.FAIL if expired_quotes else CheckResult.PASS,
            message=f"Expired quotes from: {', '.join(expired_quotes)}" if expired_quotes else "",
            fix_suggestion="Request updated quotes from suppliers",
            details={"expired": expired_quotes},
        )
        result.add_check(check)
        
        # Expiring soon
        if expiring_soon:
            check = QualityCheckItem(
                check_id="supplier_quotes_expiring",
                name="Supplier Quotes Not Expiring Soon",
                description=f"Supplier quotes valid for at least {buffer_days} days",
                category=CheckCategory.SUPPLIER,
                severity=CheckSeverity.WARNING,
                result=CheckResult.FAIL,
                message=f"Expiring soon from: {', '.join(expiring_soon)}",
                fix_suggestion="Consider requesting extended quotes",
                details={"expiring_soon": expiring_soon, "buffer_days": buffer_days},
            )
            result.add_check(check)
        
        # Pending quotes
        if pending_quotes:
            check = QualityCheckItem(
                check_id="supplier_quotes_pending",
                name="No Pending Supplier Quotes",
                description="All supplier quotes have been received",
                category=CheckCategory.SUPPLIER,
                severity=CheckSeverity.WARNING,
                result=CheckResult.FAIL,
                message=f"Pending quotes from: {', '.join(pending_quotes)}",
                fix_suggestion="Wait for or follow up on pending quotes",
                details={"pending": pending_quotes},
            )
            result.add_check(check)
    
    def _check_ctq_links(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check CTQ (Critical to Quality) links."""
        if not self.config.require_ctq_links:
            check = QualityCheckItem(
                check_id="ctq_links",
                name="CTQ Links",
                description="Quote is linked to CTQ requirements",
                category=CheckCategory.CTQ,
                severity=CheckSeverity.INFO,
                result=CheckResult.SKIP,
                message="CTQ check disabled",
            )
            result.add_check(check)
            return
        
        has_ctq_links = len(quote.ctq_links) > 0
        check = QualityCheckItem(
            check_id="ctq_links",
            name="CTQ Links",
            description="Quote is linked to CTQ requirements",
            category=CheckCategory.CTQ,
            severity=CheckSeverity.WARNING,
            result=CheckResult.PASS if has_ctq_links else CheckResult.FAIL,
            message="" if has_ctq_links else "No CTQ links defined",
            fix_suggestion="Link relevant CTQ requirements to this quote",
            details={"ctq_count": len(quote.ctq_links)},
        )
        result.add_check(check)
        
        # Check for open CTQs
        if quote.ctq_links:
            open_ctqs = [
                ctq.get("name", "Unknown")
                for ctq in quote.ctq_links
                if ctq.get("status") not in ["verified", "closed", "n/a"]
            ]
            
            if open_ctqs:
                check = QualityCheckItem(
                    check_id="ctq_status",
                    name="CTQs Verified",
                    description="All linked CTQs are verified",
                    category=CheckCategory.CTQ,
                    severity=CheckSeverity.INFO,
                    result=CheckResult.FAIL,
                    message=f"Open CTQs: {', '.join(open_ctqs[:5])}",
                    fix_suggestion="Verify or close open CTQ items",
                    details={"open_count": len(open_ctqs), "open": open_ctqs[:10]},
                )
                result.add_check(check)
    
    def _check_approval(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check approval requirements."""
        if not quote.requires_approval:
            check = QualityCheckItem(
                check_id="approval_required",
                name="Approval Status",
                description="Quote approval requirements",
                category=CheckCategory.APPROVAL,
                severity=CheckSeverity.INFO,
                result=CheckResult.PASS,
                message="No approval required",
            )
            result.add_check(check)
            return
        
        # Approval is required
        is_approved = quote.approval_status == "approved"
        check = QualityCheckItem(
            check_id="approval_obtained",
            name="Approval Obtained",
            description="Required approval has been obtained",
            category=CheckCategory.APPROVAL,
            severity=CheckSeverity.ERROR,
            result=CheckResult.PASS if is_approved else CheckResult.FAIL,
            message="" if is_approved else f"Approval status: {quote.approval_status}",
            fix_suggestion="Submit for approval before releasing",
            details={"approval_status": quote.approval_status},
        )
        result.add_check(check)
        
        # Check if threshold triggered
        if quote.approval_threshold and quote.total:
            over_threshold = quote.total >= quote.approval_threshold
            if over_threshold and not is_approved:
                check = QualityCheckItem(
                    check_id="approval_threshold",
                    name="Threshold Approval",
                    description=f"Quote over {quote.approval_threshold} requires approval",
                    category=CheckCategory.APPROVAL,
                    severity=CheckSeverity.ERROR,
                    result=CheckResult.FAIL,
                    message=f"Total {quote.total} exceeds threshold {quote.approval_threshold}",
                    fix_suggestion="Obtain approval for high-value quote",
                    details={
                        "total": str(quote.total),
                        "threshold": str(quote.approval_threshold),
                    },
                )
                result.add_check(check)
    
    def _check_custom_fields(self, quote: QuoteData, result: QualityCheckResult) -> None:
        """Check required custom fields."""
        if not self.config.required_custom_fields:
            return
        
        missing_fields = []
        for field_name in self.config.required_custom_fields:
            if field_name not in quote.custom_fields or not quote.custom_fields.get(field_name):
                missing_fields.append(field_name)
        
        check = QualityCheckItem(
            check_id="custom_fields",
            name="Required Custom Fields",
            description="All required custom fields are filled",
            category=CheckCategory.COMPLETENESS,
            severity=CheckSeverity.WARNING,
            result=CheckResult.FAIL if missing_fields else CheckResult.PASS,
            message=f"Missing: {', '.join(missing_fields)}" if missing_fields else "",
            fix_suggestion="Fill in all required custom fields",
            details={"missing": missing_fields},
        )
        result.add_check(check)


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def check_quote_for_release(
    quote_data: dict[str, Any],
    config: CheckConfig | None = None,
) -> QualityCheckResult:
    """Convenience function to check a quote from dict data."""
    quote = QuoteData(
        id=quote_data.get("id", ""),
        quote_number=quote_data.get("quote_number", ""),
        status=quote_data.get("status", ""),
        subtotal=Decimal(str(quote_data.get("subtotal", 0))) if quote_data.get("subtotal") else None,
        total=Decimal(str(quote_data.get("total", 0))) if quote_data.get("total") else None,
        total_cost=Decimal(str(quote_data.get("total_cost", 0))) if quote_data.get("total_cost") else None,
        target_margin=Decimal(str(quote_data.get("target_margin", 0))) if quote_data.get("target_margin") else None,
        actual_margin=Decimal(str(quote_data.get("actual_margin", 0))) if quote_data.get("actual_margin") else None,
        currency=quote_data.get("currency", "USD"),
        valid_from=quote_data.get("valid_from"),
        valid_until=quote_data.get("valid_until"),
        created_at=quote_data.get("created_at"),
        payment_terms=quote_data.get("payment_terms"),
        delivery_terms=quote_data.get("delivery_terms"),
        lead_time_days=quote_data.get("lead_time_days"),
        warranty_terms=quote_data.get("warranty_terms"),
        terms_and_conditions=quote_data.get("terms_and_conditions"),
        internal_notes=quote_data.get("internal_notes"),
        customer_notes=quote_data.get("customer_notes"),
        requires_approval=quote_data.get("requires_approval", False),
        approval_status=quote_data.get("approval_status", "not_required"),
        approval_threshold=Decimal(str(quote_data.get("approval_threshold", 0))) if quote_data.get("approval_threshold") else None,
        rfq_id=quote_data.get("rfq_id"),
        opportunity_id=quote_data.get("opportunity_id"),
        account_id=quote_data.get("account_id"),
        account_name=quote_data.get("account_name"),
        line_items=quote_data.get("line_items", []),
        assumptions=quote_data.get("assumptions", []),
        supplier_quotes=quote_data.get("supplier_quotes", []),
        ctq_links=quote_data.get("ctq_links", []),
        custom_fields=quote_data.get("custom_fields", {}),
    )
    
    service = QuoteQualityService(config)
    return service.check_quote(quote)


def get_blocking_issues(result: QualityCheckResult) -> list[QualityCheckItem]:
    """Get only the blocking (error severity) issues."""
    return [
        check
        for check in result.checks
        if check.result == CheckResult.FAIL and check.severity == CheckSeverity.ERROR
    ]


def get_warnings(result: QualityCheckResult) -> list[QualityCheckItem]:
    """Get only the warning issues."""
    return [
        check
        for check in result.checks
        if check.result == CheckResult.FAIL and check.severity == CheckSeverity.WARNING
    ]
