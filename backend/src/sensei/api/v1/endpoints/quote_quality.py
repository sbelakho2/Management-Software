"""
Quote Quality Pre-Release Checks API Endpoints.

Provides REST API endpoints for validating quotes before release to customers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

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

router = APIRouter(prefix="/quote-quality", tags=["Quote Quality"])


# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class LineItemInput(BaseModel):
    """Line item data for quality check."""
    
    line_number: int = 1
    description: str | None = None
    quantity: int = 0
    unit_price: float = 0.0
    total: float | None = None


class AssumptionInput(BaseModel):
    """Assumption data for quality check."""
    
    id: str
    text: str


class SupplierQuoteInput(BaseModel):
    """Supplier quote data for quality check."""
    
    supplier_name: str
    status: str = "pending"
    valid_until: datetime | None = None


class CTQLinkInput(BaseModel):
    """CTQ link data for quality check."""
    
    id: str
    name: str
    status: str = "open"


class QuoteQualityCheckRequest(BaseModel):
    """Request to check quote quality."""
    
    id: str = Field(..., description="Quote ID")
    quote_number: str = Field(..., description="Quote number")
    status: str = Field(default="draft", description="Quote status")
    
    # Pricing
    subtotal: float | None = Field(default=None, description="Quote subtotal")
    total: float | None = Field(default=None, description="Quote total")
    total_cost: float | None = Field(default=None, description="Total cost")
    target_margin: float | None = Field(default=None, description="Target margin percentage")
    actual_margin: float | None = Field(default=None, description="Actual margin percentage")
    currency: str = Field(default="USD", description="Currency code")
    
    # Dates
    valid_from: datetime | None = Field(default=None, description="Valid from date")
    valid_until: datetime | None = Field(default=None, description="Expiration date")
    created_at: datetime | None = Field(default=None, description="Creation date")
    
    # Terms
    payment_terms: str | None = Field(default=None, description="Payment terms")
    delivery_terms: str | None = Field(default=None, description="Delivery terms")
    lead_time_days: int | None = Field(default=None, description="Lead time in days")
    warranty_terms: str | None = Field(default=None, description="Warranty terms")
    terms_and_conditions: str | None = Field(default=None, description="Terms and conditions")
    
    # Notes
    internal_notes: str | None = Field(default=None, description="Internal notes")
    customer_notes: str | None = Field(default=None, description="Customer notes")
    
    # Approval
    requires_approval: bool = Field(default=False, description="Requires approval")
    approval_status: str = Field(default="not_required", description="Approval status")
    approval_threshold: float | None = Field(default=None, description="Approval threshold")
    
    # Related entities
    rfq_id: str | None = Field(default=None, description="RFQ ID")
    opportunity_id: str | None = Field(default=None, description="Opportunity ID")
    account_id: str | None = Field(default=None, description="Account ID")
    account_name: str | None = Field(default=None, description="Account name")
    
    # Line items
    line_items: list[LineItemInput] = Field(default_factory=list, description="Quote line items")
    
    # Assumptions
    assumptions: list[AssumptionInput] = Field(default_factory=list, description="Quote assumptions")
    
    # Supplier quotes
    supplier_quotes: list[SupplierQuoteInput] = Field(default_factory=list, description="Supplier quotes")
    
    # CTQ links
    ctq_links: list[CTQLinkInput] = Field(default_factory=list, description="CTQ links")
    
    # Custom fields
    custom_fields: dict[str, Any] = Field(default_factory=dict, description="Custom fields")


class CheckConfigInput(BaseModel):
    """Configuration for quality checks."""
    
    min_margin_percent: float = Field(default=15.0, description="Minimum target margin percentage")
    margin_floor_percent: float = Field(default=10.0, description="Absolute minimum margin percentage")
    min_validity_days: int = Field(default=30, description="Minimum validity period in days")
    max_validity_days: int = Field(default=180, description="Maximum validity period in days")
    supplier_quote_validity_buffer_days: int = Field(default=7, description="Buffer days for supplier quote validity")
    require_at_least_one_line_item: bool = Field(default=True, description="Require at least one line item")
    require_line_item_descriptions: bool = Field(default=True, description="Require descriptions on line items")
    require_payment_terms: bool = Field(default=True, description="Require payment terms")
    require_delivery_terms: bool = Field(default=True, description="Require delivery terms")
    require_terms_and_conditions: bool = Field(default=True, description="Require T&C")
    min_assumptions_count: int = Field(default=0, description="Minimum number of assumptions")
    require_assumptions: bool = Field(default=True, description="Require assumptions")
    require_ctq_links: bool = Field(default=False, description="Require CTQ links")
    require_valid_supplier_quotes: bool = Field(default=True, description="Require valid supplier quotes")
    required_custom_fields: list[str] = Field(default_factory=list, description="Required custom field names")


class CheckWithConfigRequest(BaseModel):
    """Request to check quote with custom configuration."""
    
    quote: QuoteQualityCheckRequest
    config: CheckConfigInput | None = None


class CheckItemResponse(BaseModel):
    """A single quality check result."""
    
    check_id: str
    name: str
    description: str
    category: str
    severity: str
    result: str
    message: str
    details: dict[str, Any]
    fix_suggestion: str


class QualityCheckResponse(BaseModel):
    """Quality check result response."""
    
    quote_id: str
    quote_number: str
    checked_at: datetime
    can_release: bool
    error_count: int
    warning_count: int
    info_count: int
    score: float
    checks: list[CheckItemResponse]


class BlockingIssuesResponse(BaseModel):
    """Response with only blocking issues."""
    
    quote_id: str
    quote_number: str
    can_release: bool
    blocking_count: int
    blocking_issues: list[CheckItemResponse]


class QuickCheckResponse(BaseModel):
    """Quick check response (summary only)."""
    
    quote_id: str
    quote_number: str
    can_release: bool
    score: float
    error_count: int
    warning_count: int


class CheckCategoriesResponse(BaseModel):
    """Available check categories."""
    
    categories: list[dict[str, str]]


class CheckSeveritiesResponse(BaseModel):
    """Available check severities."""
    
    severities: list[dict[str, str]]


class DefaultConfigResponse(BaseModel):
    """Default configuration values."""
    
    config: dict[str, Any]


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _convert_check_item(item: QualityCheckItem) -> CheckItemResponse:
    """Convert internal check item to response."""
    return CheckItemResponse(
        check_id=item.check_id,
        name=item.name,
        description=item.description,
        category=item.category.value,
        severity=item.severity.value,
        result=item.result.value,
        message=item.message,
        details=item.details,
        fix_suggestion=item.fix_suggestion,
    )


def _convert_result(result: QualityCheckResult) -> QualityCheckResponse:
    """Convert internal result to response."""
    return QualityCheckResponse(
        quote_id=result.quote_id,
        quote_number=result.quote_number,
        checked_at=result.checked_at,
        can_release=result.can_release,
        error_count=result.error_count,
        warning_count=result.warning_count,
        info_count=result.info_count,
        score=result.score,
        checks=[_convert_check_item(c) for c in result.checks],
    )


def _request_to_quote_data(request: QuoteQualityCheckRequest) -> QuoteData:
    """Convert request to QuoteData."""
    return QuoteData(
        id=request.id,
        quote_number=request.quote_number,
        status=request.status,
        subtotal=Decimal(str(request.subtotal)) if request.subtotal else None,
        total=Decimal(str(request.total)) if request.total else None,
        total_cost=Decimal(str(request.total_cost)) if request.total_cost else None,
        target_margin=Decimal(str(request.target_margin)) if request.target_margin else None,
        actual_margin=Decimal(str(request.actual_margin)) if request.actual_margin else None,
        currency=request.currency,
        valid_from=request.valid_from,
        valid_until=request.valid_until,
        created_at=request.created_at,
        payment_terms=request.payment_terms,
        delivery_terms=request.delivery_terms,
        lead_time_days=request.lead_time_days,
        warranty_terms=request.warranty_terms,
        terms_and_conditions=request.terms_and_conditions,
        internal_notes=request.internal_notes,
        customer_notes=request.customer_notes,
        requires_approval=request.requires_approval,
        approval_status=request.approval_status,
        approval_threshold=Decimal(str(request.approval_threshold)) if request.approval_threshold else None,
        rfq_id=request.rfq_id,
        opportunity_id=request.opportunity_id,
        account_id=request.account_id,
        account_name=request.account_name,
        line_items=[
            {
                "line_number": li.line_number,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": Decimal(str(li.unit_price)),
                "total": Decimal(str(li.total)) if li.total else None,
            }
            for li in request.line_items
        ],
        assumptions=[
            {"id": a.id, "text": a.text}
            for a in request.assumptions
        ],
        supplier_quotes=[
            {
                "supplier_name": sq.supplier_name,
                "status": sq.status,
                "valid_until": sq.valid_until,
            }
            for sq in request.supplier_quotes
        ],
        ctq_links=[
            {"id": ctq.id, "name": ctq.name, "status": ctq.status}
            for ctq in request.ctq_links
        ],
        custom_fields=request.custom_fields,
    )


def _request_to_config(config_input: CheckConfigInput) -> CheckConfig:
    """Convert config input to CheckConfig."""
    return CheckConfig(
        min_margin_percent=Decimal(str(config_input.min_margin_percent)),
        margin_floor_percent=Decimal(str(config_input.margin_floor_percent)),
        min_validity_days=config_input.min_validity_days,
        max_validity_days=config_input.max_validity_days,
        supplier_quote_validity_buffer_days=config_input.supplier_quote_validity_buffer_days,
        require_at_least_one_line_item=config_input.require_at_least_one_line_item,
        require_line_item_descriptions=config_input.require_line_item_descriptions,
        require_payment_terms=config_input.require_payment_terms,
        require_delivery_terms=config_input.require_delivery_terms,
        require_terms_and_conditions=config_input.require_terms_and_conditions,
        min_assumptions_count=config_input.min_assumptions_count,
        require_assumptions=config_input.require_assumptions,
        require_ctq_links=config_input.require_ctq_links,
        require_valid_supplier_quotes=config_input.require_valid_supplier_quotes,
        required_custom_fields=config_input.required_custom_fields,
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/check",
    response_model=QualityCheckResponse,
    summary="Check quote quality",
    description="Perform pre-release quality checks on a quote.",
)
async def check_quote_quality(
    request: QuoteQualityCheckRequest,
) -> QualityCheckResponse:
    """Check quote quality with default configuration."""
    quote_data = _request_to_quote_data(request)
    service = QuoteQualityService()
    result = service.check_quote(quote_data)
    return _convert_result(result)


@router.post(
    "/check-with-config",
    response_model=QualityCheckResponse,
    summary="Check quote quality with custom config",
    description="Perform pre-release quality checks with custom configuration.",
)
async def check_quote_quality_with_config(
    request: CheckWithConfigRequest,
) -> QualityCheckResponse:
    """Check quote quality with custom configuration."""
    quote_data = _request_to_quote_data(request.quote)
    
    config = None
    if request.config:
        config = _request_to_config(request.config)
    
    service = QuoteQualityService(config)
    result = service.check_quote(quote_data)
    return _convert_result(result)


@router.post(
    "/quick-check",
    response_model=QuickCheckResponse,
    summary="Quick quality check",
    description="Get a quick summary of quote quality without full details.",
)
async def quick_check_quality(
    request: QuoteQualityCheckRequest,
) -> QuickCheckResponse:
    """Perform quick quality check returning summary only."""
    quote_data = _request_to_quote_data(request)
    service = QuoteQualityService()
    result = service.check_quote(quote_data)
    
    return QuickCheckResponse(
        quote_id=result.quote_id,
        quote_number=result.quote_number,
        can_release=result.can_release,
        score=result.score,
        error_count=result.error_count,
        warning_count=result.warning_count,
    )


@router.post(
    "/blocking-issues",
    response_model=BlockingIssuesResponse,
    summary="Get blocking issues",
    description="Get only the issues that block quote release.",
)
async def get_blocking_issues_endpoint(
    request: QuoteQualityCheckRequest,
) -> BlockingIssuesResponse:
    """Get only blocking issues that prevent release."""
    quote_data = _request_to_quote_data(request)
    service = QuoteQualityService()
    result = service.check_quote(quote_data)
    blocking = get_blocking_issues(result)
    
    return BlockingIssuesResponse(
        quote_id=result.quote_id,
        quote_number=result.quote_number,
        can_release=result.can_release,
        blocking_count=len(blocking),
        blocking_issues=[_convert_check_item(c) for c in blocking],
    )


@router.post(
    "/warnings",
    response_model=BlockingIssuesResponse,
    summary="Get warnings",
    description="Get warning issues that should be reviewed.",
)
async def get_warnings_endpoint(
    request: QuoteQualityCheckRequest,
) -> BlockingIssuesResponse:
    """Get warning issues."""
    quote_data = _request_to_quote_data(request)
    service = QuoteQualityService()
    result = service.check_quote(quote_data)
    warnings = get_warnings(result)
    
    return BlockingIssuesResponse(
        quote_id=result.quote_id,
        quote_number=result.quote_number,
        can_release=result.can_release,
        blocking_count=len(warnings),
        blocking_issues=[_convert_check_item(c) for c in warnings],
    )


@router.get(
    "/categories",
    response_model=CheckCategoriesResponse,
    summary="Get check categories",
    description="Get list of available quality check categories.",
)
async def get_check_categories() -> CheckCategoriesResponse:
    """Get available check categories."""
    categories = [
        {"value": cat.value, "name": cat.name, "description": _get_category_description(cat)}
        for cat in CheckCategory
    ]
    return CheckCategoriesResponse(categories=categories)


@router.get(
    "/severities",
    response_model=CheckSeveritiesResponse,
    summary="Get check severities",
    description="Get list of available check severity levels.",
)
async def get_check_severities() -> CheckSeveritiesResponse:
    """Get available check severities."""
    severities = [
        {"value": sev.value, "name": sev.name, "description": _get_severity_description(sev)}
        for sev in CheckSeverity
    ]
    return CheckSeveritiesResponse(severities=severities)


@router.get(
    "/default-config",
    response_model=DefaultConfigResponse,
    summary="Get default configuration",
    description="Get the default quality check configuration values.",
)
async def get_default_config() -> DefaultConfigResponse:
    """Get default configuration."""
    config = CheckConfig()
    return DefaultConfigResponse(
        config={
            "min_margin_percent": float(config.min_margin_percent),
            "margin_floor_percent": float(config.margin_floor_percent),
            "min_validity_days": config.min_validity_days,
            "max_validity_days": config.max_validity_days,
            "supplier_quote_validity_buffer_days": config.supplier_quote_validity_buffer_days,
            "require_at_least_one_line_item": config.require_at_least_one_line_item,
            "require_line_item_descriptions": config.require_line_item_descriptions,
            "require_payment_terms": config.require_payment_terms,
            "require_delivery_terms": config.require_delivery_terms,
            "require_terms_and_conditions": config.require_terms_and_conditions,
            "min_assumptions_count": config.min_assumptions_count,
            "require_assumptions": config.require_assumptions,
            "require_ctq_links": config.require_ctq_links,
            "require_valid_supplier_quotes": config.require_valid_supplier_quotes,
            "required_custom_fields": config.required_custom_fields,
        }
    )


@router.post(
    "/validate-config",
    response_model=dict[str, bool],
    summary="Validate configuration",
    description="Validate a custom quality check configuration.",
)
async def validate_config(
    config: CheckConfigInput,
) -> dict[str, bool]:
    """Validate custom configuration."""
    errors = []
    
    if config.min_margin_percent < 0:
        errors.append("min_margin_percent cannot be negative")
    
    if config.margin_floor_percent < 0:
        errors.append("margin_floor_percent cannot be negative")
    
    if config.margin_floor_percent > config.min_margin_percent:
        errors.append("margin_floor_percent cannot be greater than min_margin_percent")
    
    if config.min_validity_days < 0:
        errors.append("min_validity_days cannot be negative")
    
    if config.max_validity_days < config.min_validity_days:
        errors.append("max_validity_days cannot be less than min_validity_days")
    
    if config.min_assumptions_count < 0:
        errors.append("min_assumptions_count cannot be negative")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"valid": False, "errors": errors},
        )
    
    return {"valid": True}


@router.get(
    "/check-types",
    response_model=dict[str, list[dict[str, str]]],
    summary="Get available check types",
    description="Get all available quality check types and their descriptions.",
)
async def get_check_types() -> dict[str, list[dict[str, str]]]:
    """Get all available check types."""
    return {
        "checks": [
            # Completeness checks
            {"id": "line_items_exist", "name": "Line Items Present", "category": "completeness"},
            {"id": "line_item_descriptions", "name": "Line Item Descriptions", "category": "completeness"},
            {"id": "assumptions_exist", "name": "Assumptions Documented", "category": "completeness"},
            {"id": "assumptions_count", "name": "Sufficient Assumptions", "category": "completeness"},
            {"id": "custom_fields", "name": "Required Custom Fields", "category": "completeness"},
            # Pricing checks
            {"id": "subtotal_valid", "name": "Subtotal Valid", "category": "pricing"},
            {"id": "total_valid", "name": "Total Valid", "category": "pricing"},
            {"id": "line_item_prices", "name": "Line Item Prices", "category": "pricing"},
            {"id": "line_item_quantities", "name": "Line Item Quantities", "category": "pricing"},
            {"id": "margin_calculated", "name": "Margin Calculated", "category": "pricing"},
            {"id": "margin_floor", "name": "Margin Above Floor", "category": "pricing"},
            {"id": "margin_target", "name": "Margin Meets Target", "category": "pricing"},
            {"id": "margin_vs_target", "name": "Margin vs. Target", "category": "pricing"},
            # Validity checks
            {"id": "validity_from_set", "name": "Valid From Date Set", "category": "validity"},
            {"id": "validity_until_set", "name": "Valid Until Date Set", "category": "validity"},
            {"id": "not_expired", "name": "Quote Not Expired", "category": "validity"},
            {"id": "validity_duration", "name": "Adequate Validity Period", "category": "validity"},
            # Terms checks
            {"id": "payment_terms", "name": "Payment Terms Defined", "category": "terms"},
            {"id": "delivery_terms", "name": "Delivery Terms Defined", "category": "terms"},
            {"id": "terms_and_conditions", "name": "Terms and Conditions", "category": "terms"},
            {"id": "lead_time", "name": "Lead Time Defined", "category": "terms"},
            # Supplier checks
            {"id": "supplier_quotes", "name": "Supplier Quotes", "category": "supplier"},
            {"id": "supplier_quotes_expired", "name": "Supplier Quotes Not Expired", "category": "supplier"},
            {"id": "supplier_quotes_expiring", "name": "Supplier Quotes Not Expiring Soon", "category": "supplier"},
            {"id": "supplier_quotes_pending", "name": "No Pending Supplier Quotes", "category": "supplier"},
            # CTQ checks
            {"id": "ctq_links", "name": "CTQ Links", "category": "ctq"},
            {"id": "ctq_status", "name": "CTQs Verified", "category": "ctq"},
            # Approval checks
            {"id": "approval_required", "name": "Approval Status", "category": "approval"},
            {"id": "approval_obtained", "name": "Approval Obtained", "category": "approval"},
            {"id": "approval_threshold", "name": "Threshold Approval", "category": "approval"},
        ]
    }


# --------------------------------------------------------------------------
# Description Helpers
# --------------------------------------------------------------------------

def _get_category_description(category: CheckCategory) -> str:
    """Get description for a category."""
    descriptions = {
        CheckCategory.COMPLETENESS: "Checks for missing required data",
        CheckCategory.PRICING: "Pricing and margin validation",
        CheckCategory.VALIDITY: "Expiration and validity period checks",
        CheckCategory.COMPLIANCE: "Compliance requirement checks",
        CheckCategory.APPROVAL: "Approval requirement checks",
        CheckCategory.CTQ: "Critical to Quality linkage",
        CheckCategory.SUPPLIER: "Supplier quote validation",
        CheckCategory.TERMS: "Terms and conditions checks",
    }
    return descriptions.get(category, "")


def _get_severity_description(severity: CheckSeverity) -> str:
    """Get description for a severity."""
    descriptions = {
        CheckSeverity.ERROR: "Must be fixed before release",
        CheckSeverity.WARNING: "Should be reviewed but not blocking",
        CheckSeverity.INFO: "Informational only",
    }
    return descriptions.get(severity, "")
