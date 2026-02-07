"""
StarzERP Data Import API Endpoints.

Provides comprehensive API for importing data from legacy starzERP system
into Sensei OS with full entity coverage, preview, validation, and progress tracking.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser, CurrentSuperuser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response, now_utc
from sensei.services.external.starz_import_service import (
    StarzErpImportService,
    ImportEntityType,
    ImportResult,
    ImportBatchResult,
)
from sensei.core.config import settings

router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================


class EntityTypeInfo(BaseModel):
    """Information about a single entity type."""
    value: str
    label: str
    category: str
    description: str
    has_dependencies: bool = False
    dependencies: List[str] = Field(default_factory=list)


class EntityTypesResponse(BaseModel):
    """List of all available entity types for import."""
    categories: Dict[str, List[EntityTypeInfo]]
    total_types: int
    import_order: List[str]


class ImportPreviewItem(BaseModel):
    """Preview for a single entity type."""
    entity_type: str
    source_count: int
    existing_count: int
    delta: int
    estimated_imports: int
    estimated_updates: int


class ImportPreviewResponse(BaseModel):
    """Full import preview response."""
    previews: List[ImportPreviewItem]
    total_source_records: int
    total_existing_records: int
    estimated_duration_minutes: int


class ImportConfigRequest(BaseModel):
    """Configuration for an import batch."""
    entity_types: Optional[List[str]] = None  # None = all
    on_conflict: str = Field(
        default="skip",
        description="Conflict resolution: skip, update, or fail"
    )
    batch_size: int = Field(default=500, ge=50, le=5000)
    dry_run: bool = Field(default=False, description="Validate without importing")


class ImportResultItem(BaseModel):
    """Result for a single entity type."""
    entity_type: str
    total_source: int
    imported: int
    updated: int
    skipped: int
    failed: int
    success_rate: float
    duration_seconds: float
    errors: List[str]


class ImportBatchResponse(BaseModel):
    """Full import batch result."""
    batch_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_seconds: float
    total_imported: int
    total_updated: int
    total_failed: int
    entity_results: List[ImportResultItem]


class ImportStatusResponse(BaseModel):
    """Status of a running import."""
    batch_id: str
    status: str  # pending, in_progress, completed, failed
    current_entity: Optional[str]
    progress_percent: float
    entities_completed: int
    entities_total: int
    records_processed: int
    started_at: datetime
    estimated_completion: Optional[datetime]


class ConnectionTestRequest(BaseModel):
    """Request to test starzERP connection."""
    connection_string: Optional[str] = None  # Use default if not provided


class ConnectionTestResponse(BaseModel):
    """Result of connection test."""
    success: bool
    message: str
    database_name: Optional[str]
    tables_found: Optional[int]
    version: Optional[str]


# =============================================================================
# In-memory state for tracking imports
# =============================================================================

# Track running imports (in production, use Redis or similar)
_active_imports: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Entity Type Metadata
# =============================================================================

ENTITY_CATEGORIES = {
    "master_data": [
        EntityTypeInfo(
            value="units", label="Units of Measure", category="master_data",
            description="Product units (pieces, kg, meters, etc.)"
        ),
        EntityTypeInfo(
            value="warehouses", label="Warehouses", category="master_data",
            description="Warehouse/facility definitions"
        ),
        EntityTypeInfo(
            value="article_groups", label="Product Groups", category="master_data",
            description="Top-level product categorization (level 1)"
        ),
        EntityTypeInfo(
            value="article_categories", label="Product Categories", category="master_data",
            description="Mid-level product categorization (level 2)",
            has_dependencies=True, dependencies=["article_groups"]
        ),
        EntityTypeInfo(
            value="article_types", label="Product Types", category="master_data",
            description="Detailed product categorization (level 3)",
            has_dependencies=True, dependencies=["article_categories"]
        ),
        EntityTypeInfo(
            value="supplier_types", label="Supplier Types", category="master_data",
            description="Supplier classification categories"
        ),
        EntityTypeInfo(
            value="payment_terms", label="Payment Terms", category="master_data",
            description="Payment term definitions (Net 30, etc.)"
        ),
        EntityTypeInfo(
            value="tax_codes", label="Tax Codes", category="master_data",
            description="VAT/tax rate definitions"
        ),
        EntityTypeInfo(
            value="banks", label="Banks", category="master_data",
            description="Bank master data"
        ),
        EntityTypeInfo(
            value="schedules", label="Work Schedules", category="master_data",
            description="Employee work schedule templates"
        ),
        EntityTypeInfo(
            value="public_holidays", label="Public Holidays", category="master_data",
            description="Holiday calendar entries"
        ),
        EntityTypeInfo(
            value="training_programs", label="Training Programs", category="master_data",
            description="Training/certification program definitions"
        ),
    ],
    "warehouse": [
        EntityTypeInfo(
            value="stock_locations", label="Stock Locations", category="warehouse",
            description="Warehouse bin/rack locations",
            has_dependencies=True, dependencies=["warehouses"]
        ),
        EntityTypeInfo(
            value="wms_devices", label="WMS Devices", category="warehouse",
            description="Handheld scanners and devices",
            has_dependencies=True, dependencies=["warehouses"]
        ),
        EntityTypeInfo(
            value="wms_workstations", label="WMS Workstations", category="warehouse",
            description="Pick/pack workstations",
            has_dependencies=True, dependencies=["warehouses"]
        ),
        EntityTypeInfo(
            value="license_plates", label="License Plates (LPNs)", category="warehouse",
            description="Container/pallet tracking numbers",
            has_dependencies=True, dependencies=["warehouses", "stock_locations"]
        ),
        EntityTypeInfo(
            value="wms_transactions", label="WMS Transactions", category="warehouse",
            description="Inventory movement history",
            has_dependencies=True, dependencies=["warehouses", "stock_locations", "articles"]
        ),
        EntityTypeInfo(
            value="inventory_counts", label="Inventory Counts", category="warehouse",
            description="Cycle count and physical inventory records",
            has_dependencies=True, dependencies=["warehouses", "stock_locations"]
        ),
    ],
    "products": [
        EntityTypeInfo(
            value="articles", label="Products/Articles", category="products",
            description="Product master data (SKUs)",
            has_dependencies=True, dependencies=["units", "article_groups", "article_categories"]
        ),
    ],
    "hr": [
        EntityTypeInfo(
            value="employees", label="Employees", category="hr",
            description="Core employee records"
        ),
        EntityTypeInfo(
            value="employee_cnss", label="Employee CNSS", category="hr",
            description="Tunisian social security data",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_contracts", label="Employment Contracts", category="hr",
            description="Contract details and history",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_addresses", label="Employee Addresses", category="hr",
            description="Home/work addresses",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_phones", label="Employee Phones", category="hr",
            description="Contact phone numbers",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_emails", label="Employee Emails", category="hr",
            description="Email addresses",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_bank_accounts", label="Employee Bank Accounts", category="hr",
            description="Salary payment accounts",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_diplomas", label="Employee Diplomas", category="hr",
            description="Educational credentials",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_leaves", label="Leave Requests", category="hr",
            description="Leave/absence requests",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_leave_balances", label="Leave Balances", category="hr",
            description="Annual leave entitlements",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_clocking", label="Time Clock Entries", category="hr",
            description="Clock in/out records",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_absences", label="Absences", category="hr",
            description="Unplanned absence records",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_salary", label="Salary Records", category="hr",
            description="Monthly salary payments",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_advances", label="Salary Advances", category="hr",
            description="Advance payment records",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_suspensions", label="Suspensions", category="hr",
            description="Suspension records",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_permissions", label="Short Leave/Permissions", category="hr",
            description="Short-duration leave",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_training", label="Training Enrollments", category="hr",
            description="Employee training history",
            has_dependencies=True, dependencies=["employees", "training_programs"]
        ),
        EntityTypeInfo(
            value="employee_documents", label="Employee Documents", category="hr",
            description="Uploaded files and documents",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_history", label="Employment History", category="hr",
            description="Change history (promotions, etc.)",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="employee_notes", label="Employee Notes", category="hr",
            description="HR notes and comments",
            has_dependencies=True, dependencies=["employees"]
        ),
        EntityTypeInfo(
            value="shift_schedules", label="Shift Assignments", category="hr",
            description="Employee shift assignments",
            has_dependencies=True, dependencies=["employees", "schedules"]
        ),
    ],
    "partners": [
        EntityTypeInfo(
            value="suppliers", label="Suppliers", category="partners",
            description="Vendor/supplier accounts"
        ),
        EntityTypeInfo(
            value="supplier_contacts", label="Supplier Contacts", category="partners",
            description="Supplier contact persons",
            has_dependencies=True, dependencies=["suppliers"]
        ),
        EntityTypeInfo(
            value="customers", label="Customers", category="partners",
            description="Customer accounts"
        ),
        EntityTypeInfo(
            value="company_bank_accounts", label="Company Bank Accounts", category="partners",
            description="Company banking information",
            has_dependencies=True, dependencies=["banks"]
        ),
    ],
    "purchasing": [
        EntityTypeInfo(
            value="price_requests", label="RFQs/Price Requests", category="purchasing",
            description="Requests for quotation",
            has_dependencies=True, dependencies=["suppliers"]
        ),
        EntityTypeInfo(
            value="purchase_orders", label="Purchase Orders", category="purchasing",
            description="PO headers and lines",
            has_dependencies=True, dependencies=["suppliers", "articles"]
        ),
        EntityTypeInfo(
            value="po_receipts", label="PO Receipts", category="purchasing",
            description="Goods receipt records",
            has_dependencies=True, dependencies=["purchase_orders", "warehouses"]
        ),
        EntityTypeInfo(
            value="consumable_requests", label="Purchase Requisitions", category="purchasing",
            description="Internal material requests",
            has_dependencies=True, dependencies=["employees", "articles"]
        ),
        EntityTypeInfo(
            value="supplier_invoices", label="Supplier Invoices", category="purchasing",
            description="AP invoices from suppliers",
            has_dependencies=True, dependencies=["suppliers", "purchase_orders"]
        ),
    ],
    "sales": [
        EntityTypeInfo(
            value="quotations", label="Sales Quotations", category="sales",
            description="Customer quotes",
            has_dependencies=True, dependencies=["customers", "articles"]
        ),
        EntityTypeInfo(
            value="customer_invoices", label="Customer Invoices", category="sales",
            description="AR invoices to customers",
            has_dependencies=True, dependencies=["customers"]
        ),
    ],
    "shipping": [
        EntityTypeInfo(
            value="shipments", label="Shipments", category="shipping",
            description="Outbound shipment headers",
            has_dependencies=True, dependencies=["customers", "warehouses"]
        ),
        EntityTypeInfo(
            value="pick_lists", label="Pick Lists", category="shipping",
            description="Warehouse pick instructions",
            has_dependencies=True, dependencies=["shipments", "stock_locations"]
        ),
    ],
    "finance": [
        EntityTypeInfo(
            value="payments", label="Payments", category="finance",
            description="Payment records (in/out)",
            has_dependencies=True, dependencies=["suppliers", "customers", "company_bank_accounts"]
        ),
        EntityTypeInfo(
            value="bank_transactions", label="Bank Transactions", category="finance",
            description="Bank statement entries",
            has_dependencies=True, dependencies=["company_bank_accounts"]
        ),
    ],
    "quality": [
        EntityTypeInfo(
            value="scrap_records", label="Scrap/Reject Records", category="quality",
            description="Quality rejection records",
            has_dependencies=True, dependencies=["articles"]
        ),
    ],
}


def _get_all_entity_types() -> List[str]:
    """Get ordered list of all entity types."""
    return [e.value for e in ImportEntityType]


# =============================================================================
# Endpoints - Configuration & Metadata
# =============================================================================


@router.get("/entity-types", response_model=EntityTypesResponse)
async def get_entity_types(current_user: CurrentSuperuser) -> Any:
    """
    Get all available entity types for import.
    Returns categorized list with dependency information.
    """
    total = sum(len(items) for items in ENTITY_CATEGORIES.values())
    
    return EntityTypesResponse(
        categories=ENTITY_CATEGORIES,
        total_types=total,
        import_order=_get_all_entity_types()
    )


@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_starz_connection(
    request: ConnectionTestRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Test connection to starzERP MySQL database.
    Uses configured connection if not provided.
    """
    try:
        conn_string = request.connection_string or getattr(settings, 'STARZ_ERP_CONNECTION', None)
        
        if not conn_string:
            return ConnectionTestResponse(
                success=False,
                message="No starzERP connection string configured",
                database_name=None,
                tables_found=None,
                version=None
            )
        
        # Create temporary service to test connection
        service = StarzErpImportService(
            sensei_session=db,
            starz_connection_string=conn_string
        )
        
        # Attempt connection and basic query
        starz_factory = await service._get_starz_session()
        async with starz_factory() as starz_session:
            # Get database info
            result = await starz_session.execute("SELECT DATABASE(), VERSION()")
            row = result.fetchone()
            db_name = row[0] if row else "unknown"
            version = row[1] if row else "unknown"
            
            # Count tables
            result = await starz_session.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"
            )
            table_count = result.scalar()
        
        return ConnectionTestResponse(
            success=True,
            message="Successfully connected to starzERP",
            database_name=db_name,
            tables_found=table_count,
            version=version
        )
        
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            database_name=None,
            tables_found=None,
            version=None
        )


# =============================================================================
# Endpoints - Preview & Validation
# =============================================================================


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Preview import without making changes.
    Returns counts and estimated duration.
    """
    conn_string = getattr(settings, 'STARZ_ERP_CONNECTION', None)
    if not conn_string:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="starzERP connection not configured"
        )
    
    service = StarzErpImportService(
        sensei_session=db,
        starz_connection_string=conn_string,
        batch_size=config.batch_size,
        on_conflict=config.on_conflict,
    )
    
    # Convert string types to enums
    entity_types = None
    if config.entity_types:
        entity_types = [ImportEntityType(t) for t in config.entity_types]
    
    preview_data = await service.preview_import(entity_types)
    
    previews = []
    total_source = 0
    total_existing = 0
    
    for entity_type, counts in preview_data.items():
        source = counts["source_count"]
        existing = counts["existing_count"]
        delta = counts["delta"]
        
        # Estimate based on conflict strategy
        if config.on_conflict == "skip":
            estimated_imports = max(0, delta)
            estimated_updates = 0
        elif config.on_conflict == "update":
            estimated_imports = max(0, delta)
            estimated_updates = min(source, existing)
        else:
            estimated_imports = source
            estimated_updates = 0
        
        previews.append(ImportPreviewItem(
            entity_type=entity_type.value,
            source_count=source,
            existing_count=existing,
            delta=delta,
            estimated_imports=estimated_imports,
            estimated_updates=estimated_updates
        ))
        
        total_source += source
        total_existing += existing
    
    # Rough estimate: 100 records/second
    estimated_minutes = max(1, total_source // 6000)
    
    return ImportPreviewResponse(
        previews=previews,
        total_source_records=total_source,
        total_existing_records=total_existing,
        estimated_duration_minutes=estimated_minutes
    )


# =============================================================================
# Endpoints - Import Execution
# =============================================================================


@router.post("/execute", response_model=ImportBatchResponse)
async def execute_import(
    config: ImportConfigRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Execute a full import batch.
    
    For large imports, runs in background and returns batch ID
    for status polling.
    """
    conn_string = getattr(settings, 'STARZ_ERP_CONNECTION', None)
    if not conn_string:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="starzERP connection not configured"
        )
    
    if config.dry_run:
        # Dry run - just validate and return preview
        return await preview_import(config, db, current_user)
    
    service = StarzErpImportService(
        sensei_session=db,
        starz_connection_string=conn_string,
        batch_size=config.batch_size,
        on_conflict=config.on_conflict,
    )
    
    # Convert string types to enums
    entity_types = None
    if config.entity_types:
        entity_types = [ImportEntityType(t) for t in config.entity_types]
    
    # Execute import
    result = await service.import_all(entity_types=entity_types)
    
    # Convert to response
    entity_results = []
    total_updated = 0
    
    for entity_type, er in result.entity_results.items():
        entity_results.append(ImportResultItem(
            entity_type=entity_type.value,
            total_source=er.total_source,
            imported=er.imported,
            updated=er.updated,
            skipped=er.skipped,
            failed=er.failed,
            success_rate=er.success_rate,
            duration_seconds=er.duration_seconds,
            errors=er.errors[:10]  # Limit errors in response
        ))
        total_updated += er.updated
    
    return ImportBatchResponse(
        batch_id=str(result.batch_id),
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        total_duration_seconds=result.total_duration_seconds,
        total_imported=result.total_imported,
        total_updated=total_updated,
        total_failed=result.total_failed,
        entity_results=entity_results
    )


@router.get("/status/{batch_id}", response_model=ImportStatusResponse)
async def get_import_status(
    batch_id: str,
    current_user: CurrentSuperuser
) -> Any:
    """
    Get status of a running or completed import batch.
    """
    if batch_id not in _active_imports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import batch {batch_id} not found"
        )
    
    state = _active_imports[batch_id]
    
    return ImportStatusResponse(
        batch_id=batch_id,
        status=state.get("status", "unknown"),
        current_entity=state.get("current_entity"),
        progress_percent=state.get("progress_percent", 0),
        entities_completed=state.get("entities_completed", 0),
        entities_total=state.get("entities_total", 0),
        records_processed=state.get("records_processed", 0),
        started_at=state.get("started_at", now_utc()),
        estimated_completion=state.get("estimated_completion")
    )


# =============================================================================
# Endpoints - Category-Specific Imports
# =============================================================================


@router.post("/import/master-data", response_model=ImportBatchResponse)
async def import_master_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import only master data entities (units, warehouses, categories, etc.).
    Quick import with no transactional dependencies.
    """
    master_types = [
        "units", "warehouses", "article_groups", "article_categories",
        "article_types", "supplier_types", "payment_terms", "tax_codes",
        "banks", "schedules", "public_holidays", "training_programs"
    ]
    
    config.entity_types = master_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


@router.post("/import/hr", response_model=ImportBatchResponse)
async def import_hr_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import HR entities (employees, contracts, leaves, clocking, etc.).
    """
    hr_types = [
        "employees", "employee_cnss", "employee_contracts",
        "employee_addresses", "employee_phones", "employee_emails",
        "employee_bank_accounts", "employee_diplomas", "employee_leaves",
        "employee_leave_balances", "employee_clocking", "employee_absences",
        "employee_salary", "employee_advances", "employee_suspensions",
        "employee_permissions", "employee_training", "employee_documents",
        "employee_history", "employee_notes", "shift_schedules"
    ]
    
    config.entity_types = hr_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


@router.post("/import/inventory", response_model=ImportBatchResponse)
async def import_inventory_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import inventory/WMS entities (locations, articles, LPNs, etc.).
    """
    inv_types = [
        "warehouses", "stock_locations", "wms_devices", "wms_workstations",
        "articles", "license_plates", "wms_transactions", "inventory_counts"
    ]
    
    config.entity_types = inv_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


@router.post("/import/purchasing", response_model=ImportBatchResponse)
async def import_purchasing_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import purchasing entities (suppliers, POs, receipts, etc.).
    """
    purch_types = [
        "suppliers", "supplier_contacts", "price_requests",
        "purchase_orders", "po_receipts", "consumable_requests",
        "supplier_invoices"
    ]
    
    config.entity_types = purch_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


@router.post("/import/sales", response_model=ImportBatchResponse)
async def import_sales_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import sales entities (customers, quotations, invoices, etc.).
    """
    sales_types = [
        "customers", "quotations", "customer_invoices",
        "shipments", "pick_lists"
    ]
    
    config.entity_types = sales_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


@router.post("/import/finance", response_model=ImportBatchResponse)
async def import_finance_data(
    config: ImportConfigRequest,
    db: DBSession,
    current_user: CurrentSuperuser
) -> Any:
    """
    Import financial entities (banks, payments, transactions, etc.).
    """
    fin_types = [
        "banks", "company_bank_accounts", "payments",
        "bank_transactions", "supplier_invoices", "customer_invoices"
    ]
    
    config.entity_types = fin_types
    return await execute_import(config, BackgroundTasks(), db, current_user)


# =============================================================================
# Endpoints - Utilities
# =============================================================================


@router.delete("/clear-cache")
async def clear_import_cache(current_user: CurrentSuperuser) -> Any:
    """
    Clear the import ID mapping cache.
    Use this if you need to re-import entities that were previously cached.
    """
    _active_imports.clear()
    return {"message": "Import cache cleared", "timestamp": now_utc()}


@router.get("/history")
async def get_import_history(
    db: DBSession,
    current_user: CurrentSuperuser,
    limit: int = Query(default=10, ge=1, le=100)
) -> Any:
    """
    Get history of recent import batches.
    """
    # In production, this would query a persistent store
    # For now, return in-memory data
    history = []
    for batch_id, state in list(_active_imports.items())[:limit]:
        history.append({
            "batch_id": batch_id,
            "status": state.get("status"),
            "started_at": state.get("started_at"),
            "completed_at": state.get("completed_at"),
            "total_imported": state.get("total_imported", 0),
            "total_failed": state.get("total_failed", 0)
        })
    
    return {"history": history, "total": len(history)}
