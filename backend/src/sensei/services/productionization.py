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
from typing import Any, Generic, Iterable, Protocol, TypeVar
from uuid import UUID, uuid4


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


@dataclass(frozen=True)
class PageResponse(Generic[TypeVar("T")]):
    """Paginated response."""

    items: list[Any]
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
class GLAccountModel:
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
class OpeningBalanceModel:
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
class InventoryLevelModel:
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


class ProductionizationService:
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

    def _audit_event(
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
        ev = AuditEvent(
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
        self._audit.append(ev)

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
    ) -> GLAccountModel:
        """Create a GL account."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        # Validate unique code
        for acct in self._gl_accounts.values():
            if acct.account_code == account_code:
                raise ValueError(f"Account code {account_code} already exists")

        account = GLAccountModel(
            id=uuid4(),
            account_code=account_code,
            account_name=account_name,
            account_type=account_type,
            parent_id=parent_id,
            normal_balance=normal_balance,
        )
        self._gl_accounts[account.id] = account

        self._audit_event(
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
        """List GL accounts with pagination and filtering."""
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

        # Sort by account code by default
        items.sort(key=lambda x: x["account_code"])

        return self._paginate(items, page or PageRequest())

    def get_gl_account(
        self,
        *,
        actor_roles: Iterable[str],
        account_id: UUID,
    ) -> GLAccountModel | None:
        """Get a single GL account by ID."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")
        return self._gl_accounts.get(account_id)

    # ----------------------------------------------------------------
    # Supplier Operations
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
        payment_terms_days: int = 30,
    ) -> SupplierModel:
        """Create a supplier."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        supplier = SupplierModel(
            id=uuid4(),
            supplier_code=supplier_code,
            name=name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            payment_terms_days=payment_terms_days,
        )
        self._suppliers[supplier.id] = supplier

        self._audit_event(
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
        """List suppliers with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        items = [
            {
                "id": str(s.id),
                "supplier_code": s.supplier_code,
                "name": s.name,
                "is_active": s.is_active,
            }
            for s in self._suppliers.values()
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x["supplier_code"])

        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Customer Operations
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
        credit_limit: Decimal = Decimal("0"),
        payment_terms_days: int = 30,
    ) -> CustomerModel:
        """Create a customer."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_WRITE_ROLES, "Finance write access required")

        customer = CustomerModel(
            id=uuid4(),
            customer_code=customer_code,
            name=name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            credit_limit=credit_limit,
            payment_terms_days=payment_terms_days,
        )
        self._customers[customer.id] = customer

        self._audit_event(
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
        """List customers with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        items = [
            {
                "id": str(c.id),
                "customer_code": c.customer_code,
                "name": c.name,
                "is_active": c.is_active,
            }
            for c in self._customers.values()
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x["customer_code"])

        return self._paginate(items, page or PageRequest())

    # ----------------------------------------------------------------
    # Inventory Operations
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
    ) -> InventoryItemModel:
        """Create an inventory item."""
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
        )
        self._inventory_items[item.id] = item

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_item.create",
            entity_type="inventory_item",
            entity_id=str(item.id),
            correlation_id=correlation_id,
        )

        return item

    def list_inventory_items(
        self,
        *,
        actor_roles: Iterable[str],
        page: PageRequest | None = None,
        filters: list[FilterSpec] | None = None,
    ) -> PageResponse:
        """List inventory items with pagination and filtering."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MES_READ_ROLES, "MES read access required")

        items = [
            {
                "id": str(i.id),
                "item_code": i.item_code,
                "description": i.description,
                "category": i.category,
                "is_active": i.is_active,
            }
            for i in self._inventory_items.values()
        ]

        if filters:
            items = self._apply_filters(items, filters)

        items.sort(key=lambda x: x["item_code"])

        return self._paginate(items, page or PageRequest())

    def set_inventory_level(
        self,
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

        if item_id not in self._inventory_items:
            raise ValueError("item_id not found")

        level = InventoryLevelModel(
            id=uuid4(),
            item_id=item_id,
            location_id=location_id,
            quantity_on_hand=quantity_on_hand,
            quantity_available=quantity_on_hand,
            last_counted_at=_utcnow(),
        )
        self._inventory_levels[level.id] = level

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="inventory_level.set",
            entity_type="inventory_level",
            entity_id=str(level.id),
            correlation_id=correlation_id,
        )

        return level

    # ----------------------------------------------------------------
    # Data Migration / Import
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

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="import.validate",
            entity_type=entity_type.value,
            entity_id="validation",
            correlation_id=correlation_id,
            metadata={"valid": valid_count, "error": error_count},
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
        """Execute an import of validated data."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required for imports")

        # Validate first
        validations, valid_count, error_count = self.validate_import_data(
            actor_id=actor_id,
            actor_roles=roles,
            correlation_id=correlation_id,
            entity_type=entity_type,
            records=records,
        )

        if error_count > 0:
            batch = ImportBatch(
                id=uuid4(),
                entity_type=entity_type,
                source_file=source_file,
                total_records=len(records),
                valid_records=valid_count,
                error_records=error_count,
                status=ImportStatus.FAILED,
                imported_by=actor_id,
                error_log=[
                    f"Row {v.row_number}: {', '.join(v.messages)}"
                    for v in validations
                    if v.result == ValidationResult.ERROR
                ],
            )
            self._import_batches[batch.id] = batch
            return batch

        # Import valid records
        imported = 0
        for v in validations:
            if v.result != ValidationResult.VALID:
                continue

            try:
                if entity_type == EntityType.CHART_OF_ACCOUNTS:
                    self.create_gl_account(
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        account_code=v.data["account_code"],
                        account_name=v.data["account_name"],
                        account_type=v.data["account_type"],
                        normal_balance=v.data.get("normal_balance", "debit"),
                    )
                elif entity_type == EntityType.SUPPLIER:
                    self.create_supplier(
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
                    self.create_customer(
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        customer_code=v.data["customer_code"],
                        name=v.data["name"],
                        contact_name=v.data.get("contact_name"),
                        email=v.data.get("email"),
                    )
                elif entity_type == EntityType.INVENTORY_ITEM:
                    self.create_inventory_item(
                        actor_id=actor_id,
                        actor_roles=roles,
                        correlation_id=correlation_id,
                        item_code=v.data["item_code"],
                        description=v.data["description"],
                        category=v.data.get("category"),
                        unit_of_measure=v.data.get("unit_of_measure", "EA"),
                        unit_cost=Decimal(str(v.data.get("unit_cost", "0"))),
                    )
                imported += 1
            except Exception:
                pass  # Log errors in production

        batch = ImportBatch(
            id=uuid4(),
            entity_type=entity_type,
            source_file=source_file,
            total_records=len(records),
            valid_records=imported,
            error_records=len(records) - imported,
            status=ImportStatus.COMPLETED,
            imported_by=actor_id,
            completed_at=_utcnow(),
        )
        self._import_batches[batch.id] = batch

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="import.execute",
            entity_type=entity_type.value,
            entity_id=str(batch.id),
            correlation_id=correlation_id,
            metadata={"imported": imported},
        )

        return batch

    def list_import_batches(
        self,
        *,
        actor_roles: Iterable[str],
        entity_type: EntityType | None = None,
    ) -> list[ImportBatch]:
        """List import batches."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _ADMIN_ROLES, "Admin role required")

        result = list(self._import_batches.values())
        if entity_type:
            result = [b for b in result if b.entity_type == entity_type]
        return result

    # ----------------------------------------------------------------
    # Opening Balances
    # ----------------------------------------------------------------

    def set_opening_balance(
        self,
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

        if account_id not in self._gl_accounts:
            raise ValueError("account_id not found")

        balance = OpeningBalanceModel(
            id=uuid4(),
            account_id=account_id,
            period_start=period_start,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            net_amount=debit_amount - credit_amount,
            currency=currency,
        )
        self._opening_balances[balance.id] = balance

        self._audit_event(
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
    ) -> list[OpeningBalanceModel]:
        """List opening balances."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_READ_ROLES, "Finance read access required")

        result = list(self._opening_balances.values())
        if account_id:
            result = [b for b in result if b.account_id == account_id]
        return result

    # ----------------------------------------------------------------
    # Audit Trail
    # ----------------------------------------------------------------

    def list_audit_events(
        self, *, actor_roles: Iterable[str]
    ) -> list[AuditEvent]:
        """List audit events."""
        roles = _norm_roles(actor_roles)
        _require_any(
            roles,
            frozenset({"admin", "auditor", "ceo"}),
            "Audit access required",
        )
        return list(self._audit)
