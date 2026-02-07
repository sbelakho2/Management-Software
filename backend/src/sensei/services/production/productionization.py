"""Productionization Service - DB Persistence & Data Migration (Development Plan 22.10).

Provides:
- SQLAlchemy model definitions for Finance/HR/MES entities
- Repository pattern with pagination/filtering
- Data migration utilities for CoA, opening balances, suppliers, customers, inventory
- RBAC-aware data access
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import logging
from typing import Any, Generic, Iterable, Protocol, TypeVar
from uuid import UUID, uuid4
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.models.finance import GLAccount as GLAccountModel, OpeningBalance as OpeningBalanceModel
from sensei.models.inventory import InventoryLevel as InventoryLevelModel
from sensei.models.product import Product as ProductModel
from sensei.models.account import Account as AccountModel, AccountType
from sensei.models.migration import ImportBatch as ImportBatchModel
from sensei.models.audit_log import AuditLog, AuditAction
from sensei.models.hr import EmployeeProfile as EmployeeProfileModel

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm_roles(roles: Iterable[str]) -> frozenset[str]:
    return frozenset(r.lower().strip() for r in roles if r)


def _require_any(
    roles: frozenset[str], allowed: frozenset[str], msg: str
) -> None:
    if not roles & allowed:
        raise PermissionError(msg)


# ============================================================
# Role Sets
# ============================================================

_ADMIN_ROLES = frozenset({"admin", "ceo"})
_FINANCE_WRITE_ROLES = frozenset({"admin", "finance", "accountant"})
_FINANCE_READ_ROLES = frozenset({
    "admin", "ceo", "gm", "finance", "accountant", "auditor"
})
_HR_WRITE_ROLES = frozenset({"admin", "hr"})
_HR_READ_ROLES = frozenset({"admin", "ceo", "gm", "hr", "auditor"})
_MES_WRITE_ROLES = frozenset({"admin", "ops", "quality", "supervisor"})
_MES_READ_ROLES = frozenset({
    "admin", "ceo", "gm", "ops", "quality", "supervisor", "auditor"
})


# ============================================================
# Enums
# ============================================================


class EntityType(str, Enum):
    """Types of entities for migration."""

    CHART_OF_ACCOUNTS = "chart_of_accounts"
    OPENING_BALANCE = "opening_balance"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    INVENTORY_ITEM = "inventory_item"
    EMPLOYEE = "employee"
    WORK_CENTER = "work_center"


class ImportStatus(str, Enum):
    """Status of an import batch."""

    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ValidationResult(str, Enum):
    """Result of validation."""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"


# ============================================================
# Pagination & Filtering
# ============================================================


@dataclass(frozen=True)
class PageRequest:
    """Request for paginated data."""

    page: int = 1
    page_size: int = 20
    sort_by: str | None = None
    sort_desc: bool = False


PageT = TypeVar("PageT")


@dataclass(frozen=True)
class PageResponse(Generic[PageT]):
    """Paginated response."""

    items: list[PageT]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


@dataclass(frozen=True)
class FilterSpec:
    """Filter specification for queries."""

    field: str
    operator: str  # "eq", "ne", "gt", "gte", "lt", "lte", "like", "in"
    value: Any


# ============================================================
# SQLAlchemy-like Model Definitions (In-Memory Simulation)
# ============================================================


@dataclass(frozen=True)
class GLAccountDataclass:
    """Chart of Accounts model (SQLAlchemy simulation)."""

    id: UUID
    account_code: str
    account_name: str
    account_type: str  # asset, liability, equity, revenue, expense
    parent_id: UUID | None
    is_active: bool = True
    normal_balance: str = "debit"  # or "credit"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class OpeningBalanceDataclass:
    """Opening balance model."""

    id: UUID
    account_id: UUID
    period_start: datetime
    debit_amount: Decimal
    credit_amount: Decimal
    net_amount: Decimal
    currency: str = "USD"
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class SupplierModel:
    """Supplier/Vendor model."""

    id: UUID
    supplier_code: str
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    tax_id: str | None = None
    payment_terms_days: int = 30
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class CustomerModel:
    """Customer model."""

    id: UUID
    customer_code: str
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    tax_id: str | None = None
    credit_limit: Decimal = Decimal("0")
    payment_terms_days: int = 30
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class InventoryItemModel:
    """Inventory item model."""

    id: UUID
    item_code: str
    description: str
    category: str | None = None
    unit_of_measure: str = "EA"
    unit_cost: Decimal = Decimal("0")
    reorder_point: Decimal = Decimal("0")
    reorder_quantity: Decimal = Decimal("0")
    lead_time_days: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class InventoryLevelDataclass:
    """Inventory level/on-hand model."""

    id: UUID
    item_id: UUID
    location_id: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal = Decimal("0")
    quantity_available: Decimal = Decimal("0")
    last_counted_at: datetime | None = None
    updated_at: datetime = field(default_factory=_utcnow)


# ============================================================
# Import/Migration Records
# ============================================================


@dataclass(frozen=True)
class ImportBatch:
    """A batch of imported data."""

    id: UUID
    entity_type: EntityType
    source_file: str
    total_records: int
    valid_records: int
    error_records: int
    status: ImportStatus
    imported_by: str
    error_log: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


@dataclass(frozen=True)
class ImportValidation:
    """Validation result for an import record."""

    row_number: int
    result: ValidationResult
    messages: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event."""

    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Repository Protocol
# ============================================================

T = TypeVar("T")


class Repository(Protocol[T]):
    """Generic repository protocol."""

    def get_by_id(self, entity_id: UUID) -> T | None: ...

    def list_all(self, page: PageRequest) -> PageResponse: ...

    def create(self, entity: T) -> T: ...

    def update(self, entity: T) -> T: ...

    def delete(self, entity_id: UUID) -> bool: ...


# ============================================================
# Productionization Service
# ============================================================


class AsyncProductionizationService:
    """Service for DB persistence simulation and data migration."""

    def __init__(self) -> None:
        # Simulated DB tables
        self._gl_accounts: dict[UUID, GLAccountModel] = {}
        self._opening_balances: dict[UUID, OpeningBalanceModel] = {}
        self._suppliers: dict[UUID, SupplierModel] = {}
        self._customers: dict[UUID, CustomerModel] = {}
        self._inventory_items: dict[UUID, InventoryItemModel] = {}
        self._inventory_levels: dict[UUID, InventoryLevelModel] = {}

        # Import tracking
        self._import_batches: dict[UUID, ImportBatch] = {}

        # Audit trail
        self._audit: list[AuditEvent] = []

    # ----------------------------------------------------------------
    # Internal Helpers
    # ----------------------------------------------------------------

    async def _audit_event(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        log = AuditLog(
            created_at=_utcnow(),
            user_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None,
            action=action,
            entity_type=entity_type,
            entity_id=UUID(entity_id) if isinstance(entity_id, str) and len(entity_id) == 36 else uuid4(),
            request_id=correlation_id,
            extra_data=metadata or {},
        )
        db.add(log)
        await db.flush()

    def _paginate(
        self,
        items: list[Any],
        page: PageRequest,
    ) -> PageResponse:
        """Apply pagination to a list of items."""
        total = len(items)
        total_pages = max(1, (total + page.page_size - 1) // page.page_size)

        start = (page.page - 1) * page.page_size
        end = start + page.page_size
        page_items = items[start:end]

        return PageResponse(
            items=page_items,
            total_count=total,
            page=page.page,
            page_size=page.page_size,
            total_pages=total_pages,
            has_next=page.page < total_pages,
            has_prev=page.page > 1,
        )

    def _apply_filters(
        self,
        items: list[dict[str, Any]],
        filters: list[FilterSpec],
    ) -> list[dict[str, Any]]:
        """Apply filters to a list of items."""
        result = items

        for f in filters:
            if f.operator == "eq":
                result = [i for i in result if i.get(f.field) == f.value]
            elif f.operator == "ne":
                result = [i for i in result if i.get(f.field) != f.value]
            elif f.operator == "gt":
                result = [i for i in result if i.get(f.field, 0) > f.value]
            elif f.operator == "gte":
                result = [i for i in result if i.get(f.field, 0) >= f.value]
            elif f.operator == "lt":
                result = [i for i in result if i.get(f.field, 0) < f.value]
            elif f.operator == "lte":
                result = [i for i in result if i.get(f.field, 0) <= f.value]
            elif f.operator == "like":
                result = [
                    i for i in result
                    if f.value.lower() in str(i.get(f.field, "")).lower()
                ]
            elif f.operator == "in":
                result = [i for i in result if i.get(f.field) in f.value]

        return result

    # ----------------------------------------------------------------
    # Chart of Accounts Operations
    # ----------------------------------------------------------------

    async def create_gl_account(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_code: str,
        account_name: str,
        account_type: str,
        parent_id: UUID | None = None,
        normal_balance: str = "debit",
    ) -> GLAccountModel:
        """Create a GL account."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        # Validate unique code
        stmt = select(GLAccountModel).where(GLAccountModel.account_code == account_code)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError(f"Account code {account_code} already exists")

        account = GLAccountModel(
            id=uuid4(),
            account_code=account_code,
            account_name=account_name,
            account_type=account_type,
            parent_id=parent_id,
            normal_balance=normal_balance,
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None
        )
        db.add(account)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="gl_account.create",
            entity_type="gl_account",
            entity_id=str(account.id),
            correlation_id=correlation_id,
        )

        return account

    async def list_gl_accounts(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        """List GL accounts with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        stmt = select(GLAccountModel)
        
        # In a real impl, we would apply filters to stmt. 
        # For simulation matching the old logic, we'll fetch and then filter/paginate.
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        items = [
            {
                "id": str(a.id),
                "account_code": a.account_code,
                "account_name": a.account_name,
                "account_type": a.account_type,
                "is_active": a.is_active,
            }
            for a in accounts
        ]

        if filters:
            items = self._apply_filters(items, filters)

        # Sort by account code by default
        items.sort(key=lambda x: str(x.get("account_code", "")))

        return self._paginate(items, page or PageRequest())

    async def get_gl_account(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        account_id: UUID,
    ) -> GLAccountModel | None:
        """Get a single GL account by ID."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")
        
        stmt = select(GLAccountModel).where(GLAccountModel.id == account_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ----------------------------------------------------------------
    # Supplier Operations
    # ----------------------------------------------------------------

    async def create_supplier(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        supplier_code: str,
        name: str,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        payment_terms_days: int = 30,
    ) -> AccountModel:
        """Create a supplier."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        supplier = AccountModel(
            id=uuid4(),
            account_number=supplier_code,
            name=name,
            account_type=AccountType.SUPPLIER.value,
            email=email,
            phone=phone,
            custom_fields={
                "contact_name": contact_name,
                "payment_terms_days": payment_terms_days,
            },
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None
        )
        db.add(supplier)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="supplier.create",
            entity_type="supplier",
            entity_id=str(supplier.id),
            correlation_id=correlation_id,
        )

        return supplier

    async def list_suppliers(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        """List suppliers with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        stmt = select(AccountModel).where(AccountModel.account_type == AccountType.SUPPLIER.value)
        result = await db.execute(stmt)
        suppliers = result.scalars().all()

        items = [
            {
                "id": str(s.id),
                "supplier_code": s.account_number,
                "name": s.name,
                "is_active": True, # Model has is_deleted instead of is_active
            }
            for s in suppliers
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x.get("supplier_code") or "")

        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Customer Operations
    # ----------------------------------------------------------------

    async def create_customer(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        customer_code: str,
        name: str,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        credit_limit: Decimal = Decimal("0"),
        payment_terms_days: int = 30,
    ) -> AccountModel:
        """Create a customer."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        customer = AccountModel(
            id=uuid4(),
            account_number=customer_code,
            name=name,
            account_type=AccountType.CUSTOMER.value,
            email=email,
            phone=phone,
            annual_revenue=float(credit_limit), # mapping credit_limit to annual_revenue for now or custom fields
            custom_fields={
                "contact_name": contact_name,
                "payment_terms_days": payment_terms_days,
                "credit_limit": str(credit_limit),
            },
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None
        )
        db.add(customer)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="customer.create",
            entity_type="customer",
            entity_id=str(customer.id),
            correlation_id=correlation_id,
        )

        return customer

    async def list_customers(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        """List customers with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        stmt = select(AccountModel).where(AccountModel.account_type == AccountType.CUSTOMER.value)
        result = await db.execute(stmt)
        customers = result.scalars().all()

        items = [
            {
                "id": str(c.id),
                "customer_code": c.account_number,
                "name": c.name,
                "is_active": True,
            }
            for c in customers
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x.get("customer_code") or "")

        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Inventory Operations
    # ----------------------------------------------------------------

    async def create_inventory_item(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_code: str,
        description: str,
        category: str | None = None,
        unit_of_measure: str = "EA",
        unit_cost: Decimal = Decimal("0"),
        reorder_point: Decimal = Decimal("0"),
    ) -> ProductModel:
        """Create an inventory item."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write access required")

        product = ProductModel(
            name=description,
            sku=item_code,
            category=category,
            unit_of_measure=unit_of_measure,
            standard_cost=float(unit_cost),
            # reorder_point is not in ProductModel but could be in metadata
            metadata={
                "reorder_point": str(reorder_point),
            },
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None
        )
        db.add(product)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_item.create",
            entity_type="inventory_item",
            entity_id=str(product.id),
            correlation_id=correlation_id,
        )

        return product

    async def list_inventory_items(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        """List inventory items with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read access required")

        stmt = select(ProductModel)
        result = await db.execute(stmt)
        products = result.scalars().all()

        items = [
            {
                "id": str(i.id),
                "item_code": i.sku,
                "description": i.name,
                "category": i.category,
                "is_active": True,
            }
            for i in products
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x.get("item_code") or "")

        return self._paginate(items, page or PageRequest())

    async def set_inventory_level(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: UUID,
        location_id: str,
        quantity_on_hand: Decimal,
    ) -> InventoryLevelModel:
        """Set inventory level for an item at a location."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write access required")

        # Validate product exists
        stmt = select(ProductModel).where(ProductModel.id == item_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise ValueError("item_id (product) not found")

        # Delete existing level for this item and location if any
        # (In a real system we might update, but for matching simulation logic...)
        # Wait, the model uses UUID for id, so we just add a new record?
        # Simulation logic says "Set", so we'll treat it as Upsert or just Add.
        # Let's do Add for now as per previous logic.

        level = InventoryLevelModel(
            id=uuid4(),
            product_id=item_id, # Model uses product_id
            location_id=location_id,
            quantity_on_hand=quantity_on_hand,
            quantity_available=quantity_on_hand,
            last_counted_at=_utcnow(),
        )
        db.add(level)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_level.set",
            entity_type="inventory_level",
            entity_id=str(level.id),
            correlation_id=correlation_id,
        )

        return level

    # ----------------------------------------------------------------
    # Employee Operations (HR)
    # ----------------------------------------------------------------

    async def create_employee(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        first_name: str,
        last_name: str,
        email: str | None = None,
        phone: str | None = None,
        department: str | None = None,
        job_title: str | None = None,
        site_id: str | None = None,
        cost_center_code: str | None = None,
        jurisdiction: str = "TN",  # Default Tunisia for legacy compatibility
        status: str = "active",
        hire_date: datetime | None = None,
        user_id: UUID | None = None,
        manager_id: UUID | None = None,
    ) -> EmployeeProfileModel:
        """Create an employee profile with jurisdiction support.
        
        For legacy data import, jurisdiction defaults to 'TN' (Tunisia).
        Supported jurisdictions: TN (Tunisia), MA (Morocco), EG (Egypt).
        """
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_WRITE_ROLES, "HR write access required")

        # Normalize jurisdiction (default to TN for legacy/invalid)
        if jurisdiction not in ("TN", "MA", "EG"):
            logger.warning(
                "Invalid jurisdiction '%s' for employee %s %s, defaulting to TN",
                jurisdiction, first_name, last_name
            )
            jurisdiction = "TN"

        employee = EmployeeProfileModel(
            id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            department=department,
            job_title=job_title,
            site_id=site_id,
            cost_center_code=cost_center_code,
            jurisdiction=jurisdiction,
            status=status,
            hire_date=hire_date.date() if isinstance(hire_date, datetime) else hire_date,
            user_id=user_id,
            manager_id=manager_id,
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None,
        )
        db.add(employee)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="employee.create",
            entity_type="employee",
            entity_id=str(employee.id),
            correlation_id=correlation_id,
            metadata={"jurisdiction": jurisdiction},
        )

        return employee

    async def list_employees(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
        jurisdiction: str | None = None,
    ) -> PageResponse:
        """List employees with pagination, filtering, and jurisdiction support."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read access required")

        stmt = select(EmployeeProfileModel).where(EmployeeProfileModel.deleted_at.is_(None))
        if jurisdiction:
            stmt = stmt.where(EmployeeProfileModel.jurisdiction == jurisdiction)
        
        result = await db.execute(stmt)
        employees = result.scalars().all()

        items = [
            {
                "id": str(e.id),
                "first_name": e.first_name,
                "last_name": e.last_name,
                "email": e.email,
                "department": e.department,
                "job_title": e.job_title,
                "jurisdiction": e.jurisdiction,
                "status": e.status,
            }
            for e in employees
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: (x.get("last_name", ""), x.get("first_name", "")))

        return self._paginate(items, page or PageRequest())

    async def get_employee(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        employee_id: UUID,
    ) -> EmployeeProfileModel | None:
        """Get a single employee by ID."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _HR_READ_ROLES, "HR read access required")
        
        stmt = select(EmployeeProfileModel).where(
            EmployeeProfileModel.id == employee_id,
            EmployeeProfileModel.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ----------------------------------------------------------------
    # Data Migration / Import
    # ----------------------------------------------------------------

    async def validate_import_data(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entity_type: EntityType,
        records: list[dict[str, Any]],
    ) -> tuple[list[ImportValidation], int, int]:
        """Validate import data before committing."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required for imports")

        validations: list[ImportValidation] = []
        valid_count = 0
        error_count = 0

        for i, record in enumerate(records, 1):
            messages: list[str] = []
            result = ValidationResult.VALID
            
            # Entity-specific validation
            if entity_type == EntityType.CHART_OF_ACCOUNTS:
                if not record.get("account_code"):
                    messages.append("account_code is required")
                    result = ValidationResult.ERROR
                if not record.get("account_name"):
                    messages.append("account_name is required")
                    result = ValidationResult.ERROR
                if record.get("account_type") not in (
                    "asset", "liability", "equity", "revenue", "expense"
                ):
                    messages.append("account_type must be asset/liability/equity/revenue/expense")
                    result = ValidationResult.ERROR

            elif entity_type == EntityType.SUPPLIER:
                if not record.get("supplier_code"):
                    messages.append("supplier_code is required")
                    result = ValidationResult.ERROR
                if not record.get("name"):
                    messages.append("name is required")
                    result = ValidationResult.ERROR

            elif entity_type == EntityType.CUSTOMER:
                if not record.get("customer_code"):
                    messages.append("customer_code is required")
                    result = ValidationResult.ERROR
                if not record.get("name"):
                    messages.append("name is required")
                    result = ValidationResult.ERROR

            elif entity_type == EntityType.INVENTORY_ITEM:
                if not record.get("item_code"):
                    messages.append("item_code is required")
                    result = ValidationResult.ERROR
                if not record.get("description"):
                    messages.append("description is required")
                    result = ValidationResult.ERROR

            elif entity_type == EntityType.EMPLOYEE:
                # Validate employee import data with legacy compatibility
                if not record.get("first_name"):
                    messages.append("first_name is required")
                    result = ValidationResult.ERROR
                if not record.get("last_name"):
                    messages.append("last_name is required")
                    result = ValidationResult.ERROR
                # Jurisdiction validation - default to TN if not provided (legacy compatibility)
                jurisdiction = record.get("jurisdiction", "TN")
                if jurisdiction not in ("TN", "MA", "EG"):
                    # Log warning but don't fail - we'll default to TN during import
                    logger.warning(
                        "Invalid jurisdiction '%s' for employee %s %s, will default to TN",
                        jurisdiction,
                        record.get("first_name", "?"),
                        record.get("last_name", "?"),
                    )
                # Status validation
                status = record.get("status", "active")
                if status not in ("active", "onboarding", "offboarding", "terminated"):
                    messages.append(f"invalid status '{status}', must be active/onboarding/offboarding/terminated")
                    result = ValidationResult.ERROR

            validation = ImportValidation(
                row_number=i,
                result=result,
                messages=messages,
                data=record,
            )
            validations.append(validation)

            if result == ValidationResult.VALID:
                valid_count += 1
            elif result == ValidationResult.ERROR:
                error_count += 1

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="import.validate",
            entity_type=entity_type.value,
            entity_id="validation",
            correlation_id=correlation_id,
            metadata={"valid": valid_count, "error": error_count},
        )

        return validations, valid_count, error_count

    async def execute_import(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entity_type: EntityType,
        source_file: str,
        records: list[dict[str, Any]],
    ) -> ImportBatchModel:
        """Execute an import of validated data."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required for imports")

        # Validate first
        validations, valid_count, error_count = await self.validate_import_data(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            entity_type=entity_type,
            records=records,
        )

        batch_id = uuid4()
        if error_count > 0:
            batch = ImportBatchModel(
                id=batch_id,
                entity_type=entity_type.value,
                source_file=source_file,
                total_records=len(records),
                valid_records=valid_count,
                error_records=error_count,
                status=ImportStatus.FAILED.value,
                imported_by=actor_id,
                error_log=[
                    f"Row {v.row_number}: {', '.join(v.messages)}"
                    for v in validations
                    if v.result == ValidationResult.ERROR
                ],
            )
            db.add(batch)
            await db.flush()
            return batch

        # Import valid records
        imported = 0
        error_log: list[dict[str, Any]] = []
        for v in validations:
            if v.result != ValidationResult.VALID:
                continue

            try:
                if entity_type == EntityType.CHART_OF_ACCOUNTS:
                    await self.create_gl_account(
                        db=db,
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        account_code=v.data["account_code"],
                        account_name=v.data["account_name"],
                        account_type=v.data["account_type"],
                        normal_balance=v.data.get("normal_balance", "debit"),
                    )
                elif entity_type == EntityType.SUPPLIER:
                    await self.create_supplier(
                        db=db,
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        supplier_code=v.data["supplier_code"],
                        name=v.data["name"],
                        contact_name=v.data.get("contact_name"),
                        email=v.data.get("email"),
                        phone=v.data.get("phone"),
                    )
                elif entity_type == EntityType.CUSTOMER:
                    await self.create_customer(
                        db=db,
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        customer_code=v.data["customer_code"],
                        name=v.data["name"],
                        contact_name=v.data.get("contact_name"),
                        email=v.data.get("email"),
                        phone=v.data.get("phone"),
                    )
                elif entity_type == EntityType.INVENTORY_ITEM:
                    await self.create_inventory_item(
                        db=db,
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        item_code=v.data["item_code"],
                        description=v.data["description"],
                        category=v.data.get("category"),
                        unit_of_measure=v.data.get("unit_of_measure", "EA"),
                        unit_cost=Decimal(str(v.data.get("unit_cost", "0"))),
                    )
                elif entity_type == EntityType.EMPLOYEE:
                    # Import employee with legacy compatibility
                    # Default jurisdiction to TN (Tunisia) for legacy data
                    jurisdiction = v.data.get("jurisdiction", "TN")
                    if jurisdiction not in ("TN", "MA", "EG"):
                        jurisdiction = "TN"  # Default invalid to Tunisia
                    
                    # Parse hire_date if string
                    hire_date = v.data.get("hire_date")
                    if isinstance(hire_date, str) and hire_date:
                        from datetime import datetime as dt
                        try:
                            hire_date = dt.fromisoformat(hire_date.replace("Z", "+00:00"))
                        except ValueError:
                            hire_date = None
                    
                    await self.create_employee(
                        db=db,
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        first_name=v.data["first_name"],
                        last_name=v.data["last_name"],
                        email=v.data.get("email"),
                        phone=v.data.get("phone"),
                        department=v.data.get("department"),
                        job_title=v.data.get("job_title"),
                        site_id=v.data.get("site_id"),
                        cost_center_code=v.data.get("cost_center_code"),
                        jurisdiction=jurisdiction,
                        status=v.data.get("status", "active"),
                        hire_date=hire_date,
                    )
                imported += 1
            except Exception as exc:
                logger.exception(
                    "Import failed for %s row %s",
                    entity_type.value,
                    v.row_number,
                )
                error_log.append(
                    {
                        "row": v.row_number,
                        "error": str(exc),
                        "entity_type": entity_type.value,
                    }
                )

        error_records = len(records) - imported
        batch = ImportBatchModel(
            id=batch_id,
            entity_type=entity_type.value,
            source_file=source_file,
            total_records=len(records),
            valid_records=imported,
            error_records=error_records,
            status=(ImportStatus.FAILED.value if error_records else ImportStatus.COMPLETED.value),
            imported_by=actor_id,
            error_log=error_log or None,
            completed_at=_utcnow(),
        )
        db.add(batch)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="import.execute",
            entity_type=entity_type.value,
            entity_id=str(batch.id),
            correlation_id=correlation_id,
            metadata={"imported": imported, "errors": error_records},
        )

        return batch

    async def list_import_batches(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        entity_type: EntityType | None = None,
    ) -> list[ImportBatchModel]:
        """List import batches."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        stmt = select(ImportBatchModel)
        if entity_type:
            stmt = stmt.where(ImportBatchModel.entity_type == entity_type.value)
        stmt = stmt.order_by(ImportBatchModel.created_at.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ----------------------------------------------------------------
    # Opening Balances
    # ----------------------------------------------------------------

    async def set_opening_balance(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: UUID,
        period_start: datetime,
        debit_amount: Decimal = Decimal("0"),
        credit_amount: Decimal = Decimal("0"),
        currency: str = "USD",
    ) -> OpeningBalanceModel:
        """Set opening balance for a GL account."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        # Validate account exists
        stmt = select(GLAccountModel).where(GLAccountModel.id == account_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise ValueError("account_id not found")

        balance = OpeningBalanceModel(
            id=uuid4(),
            account_id=account_id,
            period_start=period_start,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            net_amount=debit_amount - credit_amount,
            currency=currency,
            created_by_id=UUID(actor_id) if isinstance(actor_id, str) and len(actor_id) == 36 else None
        )
        db.add(balance)
        await db.flush()

        await self._audit_event(
            db=db,
            actor_id=actor_id,
            actor_roles=roles,
            action="opening_balance.set",
            entity_type="opening_balance",
            entity_id=str(balance.id),
            correlation_id=correlation_id,
        )

        return balance

    async def list_opening_balances(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        account_id: UUID | None = None,
    ) -> list[OpeningBalanceModel]:
        """List opening balances."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        stmt = select(OpeningBalanceModel)
        if account_id:
            stmt = stmt.where(OpeningBalanceModel.account_id == account_id)
        stmt = stmt.order_by(OpeningBalanceModel.period_start.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ----------------------------------------------------------------
    # Audit Trail
    # ----------------------------------------------------------------

    async def list_audit_events(
        self, 
        db: AsyncSession,
        *, 
        actor_roles: Iterable[str]
    ) -> list[AuditLog]:
        """List audit events."""
        roles = _norm_roles(actor_roles)
        _require_any(
            roles,
            frozenset({"admin", "auditor", "ceo"}),
            "Audit access required",
        )
        
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
        result = await db.execute(stmt)
        return list(result.scalars().all())


class ProductionizationService:
    """In-memory productionization service for tests and local usage."""

    def __init__(self) -> None:
        self._gl_accounts: dict[UUID, GLAccountDataclass] = {}
        self._opening_balances: dict[UUID, OpeningBalanceDataclass] = {}
        self._suppliers: dict[UUID, SupplierModel] = {}
        self._customers: dict[UUID, CustomerModel] = {}
        self._inventory_items: dict[UUID, InventoryItemModel] = {}
        self._inventory_levels: dict[UUID, InventoryLevelDataclass] = {}
        self._import_batches: dict[UUID, ImportBatch] = {}
        self._audit: list[AuditEvent] = []

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _record_audit(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(event)

    def _paginate(self, items: list[Any], page: PageRequest) -> PageResponse:
        total = len(items)
        total_pages = max(1, (total + page.page_size - 1) // page.page_size)
        start = (page.page - 1) * page.page_size
        end = start + page.page_size
        page_items = items[start:end]
        return PageResponse(
            items=page_items,
            total_count=total,
            page=page.page,
            page_size=page.page_size,
            total_pages=total_pages,
            has_next=page.page < total_pages,
            has_prev=page.page > 1,
        )

    def _apply_filters(self, items: list[dict[str, Any]], filters: list[FilterSpec]) -> list[dict[str, Any]]:
        result = items
        for f in filters:
            if f.operator == "eq":
                result = [i for i in result if i.get(f.field) == f.value]
            elif f.operator == "ne":
                result = [i for i in result if i.get(f.field) != f.value]
            elif f.operator == "gt":
                result = [i for i in result if i.get(f.field, 0) > f.value]
            elif f.operator == "gte":
                result = [i for i in result if i.get(f.field, 0) >= f.value]
            elif f.operator == "lt":
                result = [i for i in result if i.get(f.field, 0) < f.value]
            elif f.operator == "lte":
                result = [i for i in result if i.get(f.field, 0) <= f.value]
            elif f.operator == "like":
                result = [i for i in result if f.value.lower() in str(i.get(f.field, "")).lower()]
            elif f.operator == "in":
                result = [i for i in result if i.get(f.field) in f.value]
        return result

    # ----------------------------------------------------------------
    # GL Accounts
    # ----------------------------------------------------------------

    def create_gl_account(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_code: str,
        account_name: str,
        account_type: str,
        parent_id: UUID | None = None,
        normal_balance: str = "debit",
    ) -> GLAccountDataclass:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        if any(a.account_code == account_code for a in self._gl_accounts.values()):
            raise ValueError(f"Account code {account_code} already exists")

        account = GLAccountDataclass(
            id=uuid4(),
            account_code=account_code,
            account_name=account_name,
            account_type=account_type,
            parent_id=parent_id,
            normal_balance=normal_balance,
            is_active=True,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self._gl_accounts[account.id] = account
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="gl_account.create",
            entity_type="gl_account",
            entity_id=str(account.id),
            correlation_id=correlation_id,
        )
        return account

    def list_gl_accounts(
        self,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        items = [
            {
                "id": str(a.id),
                "account_code": a.account_code,
                "account_name": a.account_name,
                "account_type": a.account_type,
                "is_active": a.is_active,
            }
            for a in self._gl_accounts.values()
        ]
        if filters:
            items = self._apply_filters(items, filters)
        items.sort(key=lambda x: str(x.get("account_code", "")))
        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Suppliers
    # ----------------------------------------------------------------

    def create_supplier(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        supplier_code: str,
        name: str,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        city: str | None = None,
        country: str | None = None,
        tax_id: str | None = None,
        payment_terms_days: int = 30,
    ) -> SupplierModel:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        supplier = SupplierModel(
            id=uuid4(),
            supplier_code=supplier_code,
            name=name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            country=country,
            tax_id=tax_id,
            payment_terms_days=payment_terms_days,
            is_active=True,
        )
        self._suppliers[supplier.id] = supplier
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="supplier.create",
            entity_type="supplier",
            entity_id=str(supplier.id),
            correlation_id=correlation_id,
        )
        return supplier

    def list_suppliers(
        self,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        items = [
            {
                "id": str(s.id),
                "supplier_code": s.supplier_code,
                "name": s.name,
                "email": s.email,
                "is_active": s.is_active,
            }
            for s in self._suppliers.values()
        ]
        if filters:
            items = self._apply_filters(items, filters)
        items.sort(key=lambda x: str(x.get("supplier_code", "")))
        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Customers
    # ----------------------------------------------------------------

    def create_customer(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        customer_code: str,
        name: str,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
        city: str | None = None,
        country: str | None = None,
        tax_id: str | None = None,
        credit_limit: Decimal = Decimal("0"),
        payment_terms_days: int = 30,
    ) -> CustomerModel:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        customer = CustomerModel(
            id=uuid4(),
            customer_code=customer_code,
            name=name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            country=country,
            tax_id=tax_id,
            credit_limit=credit_limit,
            payment_terms_days=payment_terms_days,
            is_active=True,
        )
        self._customers[customer.id] = customer
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="customer.create",
            entity_type="customer",
            entity_id=str(customer.id),
            correlation_id=correlation_id,
        )
        return customer

    def list_customers(
        self,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        items = [
            {
                "id": str(c.id),
                "customer_code": c.customer_code,
                "name": c.name,
                "is_active": c.is_active,
                "credit_limit": c.credit_limit,
            }
            for c in self._customers.values()
        ]
        if filters:
            items = self._apply_filters(items, filters)
        items.sort(key=lambda x: str(x.get("customer_code", "")))
        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Inventory
    # ----------------------------------------------------------------

    def create_inventory_item(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_code: str,
        description: str,
        category: str | None = None,
        unit_of_measure: str = "EA",
        unit_cost: Decimal = Decimal("0"),
        reorder_point: Decimal = Decimal("0"),
        reorder_quantity: Decimal = Decimal("0"),
        lead_time_days: int = 0,
    ) -> InventoryItemModel:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write access required")

        item = InventoryItemModel(
            id=uuid4(),
            item_code=item_code,
            description=description,
            category=category,
            unit_of_measure=unit_of_measure,
            unit_cost=unit_cost,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
            lead_time_days=lead_time_days,
            is_active=True,
        )
        self._inventory_items[item.id] = item
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_item.create",
            entity_type="inventory_item",
            entity_id=str(item.id),
            correlation_id=correlation_id,
        )
        return item

    def set_inventory_level(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: UUID,
        location_id: str,
        quantity_on_hand: Decimal,
        quantity_reserved: Decimal = Decimal("0"),
    ) -> InventoryLevelDataclass:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_WRITE_ROLES, "MES write access required")

        if item_id not in self._inventory_items:
            raise ValueError("item_id not found")

        level = InventoryLevelDataclass(
            id=uuid4(),
            item_id=item_id,
            location_id=location_id,
            quantity_on_hand=quantity_on_hand,
            quantity_reserved=quantity_reserved,
            quantity_available=quantity_on_hand - quantity_reserved,
            updated_at=_utcnow(),
        )
        self._inventory_levels[level.id] = level
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_level.set",
            entity_type="inventory_level",
            entity_id=str(level.id),
            correlation_id=correlation_id,
        )
        return level

    # ----------------------------------------------------------------
    # Import/Migration
    # ----------------------------------------------------------------

    def validate_import_data(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entity_type: EntityType,
        records: list[dict[str, Any]],
    ) -> tuple[list[ImportValidation], int, int]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        validations: list[ImportValidation] = []
        valid_count = 0
        error_count = 0

        for idx, record in enumerate(records, start=1):
            messages: list[str] = []
            result = ValidationResult.VALID

            if entity_type == EntityType.CHART_OF_ACCOUNTS:
                if not record.get("account_code"):
                    messages.append("account_code is required")
                if not record.get("account_name"):
                    messages.append("account_name is required")
                if not record.get("account_type"):
                    messages.append("account_type is required")
            elif entity_type == EntityType.SUPPLIER:
                if not record.get("supplier_code"):
                    messages.append("supplier_code is required")
                if not record.get("name"):
                    messages.append("name is required")

            if messages:
                result = ValidationResult.ERROR
                error_count += 1
            else:
                valid_count += 1

            validations.append(
                ImportValidation(
                    row_number=idx,
                    result=result,
                    messages=messages,
                    data=record,
                )
            )

        return validations, valid_count, error_count

    def execute_import(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entity_type: EntityType,
        source_file: str,
        records: list[dict[str, Any]],
    ) -> ImportBatch:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        validations, valid_count, error_count = self.validate_import_data(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            entity_type=entity_type,
            records=records,
        )

        error_log = [
            f"Row {v.row_number}: {', '.join(v.messages)}"
            for v in validations
            if v.result == ValidationResult.ERROR
        ]

        status = ImportStatus.COMPLETED if error_count == 0 else ImportStatus.FAILED
        batch = ImportBatch(
            id=uuid4(),
            entity_type=entity_type,
            source_file=source_file,
            total_records=len(records),
            valid_records=valid_count,
            error_records=error_count,
            status=status,
            imported_by=actor_id,
            error_log=error_log,
            completed_at=_utcnow(),
        )
        self._import_batches[batch.id] = batch

        if status == ImportStatus.COMPLETED:
            for record in records:
                if entity_type == EntityType.CHART_OF_ACCOUNTS:
                    self.create_gl_account(
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        account_code=record["account_code"],
                        account_name=record["account_name"],
                        account_type=record["account_type"],
                    )
                elif entity_type == EntityType.SUPPLIER:
                    self.create_supplier(
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        supplier_code=record["supplier_code"],
                        name=record["name"],
                        email=record.get("email"),
                    )

        return batch

    def list_import_batches(
        self,
        *,
        actor_roles: Iterable[str],
        entity_type: EntityType | None = None,
    ) -> list[ImportBatch]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        batches = list(self._import_batches.values())
        if entity_type:
            batches = [b for b in batches if b.entity_type == entity_type]
        return batches

    # ----------------------------------------------------------------
    # Opening balances
    # ----------------------------------------------------------------

    def set_opening_balance(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        account_id: UUID,
        period_start: datetime,
        debit_amount: Decimal,
        credit_amount: Decimal = Decimal("0"),
        currency: str = "USD",
    ) -> OpeningBalanceDataclass:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        if account_id not in self._gl_accounts:
            raise ValueError("account_id not found")

        net_amount = debit_amount - credit_amount
        balance = OpeningBalanceDataclass(
            id=uuid4(),
            account_id=account_id,
            period_start=period_start,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            net_amount=net_amount,
            currency=currency,
        )
        self._opening_balances[balance.id] = balance
        self._record_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="opening_balance.set",
            entity_type="opening_balance",
            entity_id=str(balance.id),
            correlation_id=correlation_id,
        )
        return balance

    def list_opening_balances(
        self,
        *,
        actor_roles: Iterable[str],
        account_id: UUID | None = None,
    ) -> list[OpeningBalanceDataclass]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        balances = list(self._opening_balances.values())
        if account_id:
            balances = [b for b in balances if b.account_id == account_id]
        return balances

    # ----------------------------------------------------------------
    # Audit
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, frozenset({"admin", "auditor", "ceo"}), "Audit access required")
        return list(self._audit)
