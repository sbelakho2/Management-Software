"""
Unified StarzERP Import Service.

Comprehensive data migration service that handles importing ALL entity types
from the legacy starzERP MySQL database into Sensei OS PostgreSQL.

ARCHITECTURE:
=============
This service MERGES data into existing Sensei OS tables - NO parallel tables
are created. The StarzERP models (StarzBase) are READ-ONLY source models that
map to the legacy MySQL schema. Data is transformed and written to Sensei OS
models (Base) which use PostgreSQL.

Data Flow:
    ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
    │  StarzERP MySQL │ ──> │  Import Service  │ ──> │ Sensei OS PgSQL │
    │  (StarzBase)    │     │  (Transform)     │     │ (Base)          │
    └─────────────────┘     └──────────────────┘     └─────────────────┘

Key Points:
- StarzBase models: READ from legacy MySQL (separate connection)
- Sensei Base models: WRITE to PostgreSQL (main connection)
- ID mapping: Starz integer IDs → Sensei UUIDs (cached for FK resolution)
- Conflict resolution: Skip, update, or fail on duplicate records

Entity Categories:
- WMS/Inventory: warehouses, locations, devices, workstations, LPNs, transactions
- Products: articles, units, categories, groups, types
- HR: employees, contracts, CNSS, leaves, clocking, salary, training
- Purchasing: suppliers, POs, receipts, requisitions
- Sales: customers, quotations, invoices
- Shipping: shipments, pick lists
- Finance: banks, payments, invoices
- Quality: scrap records
"""

import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Type, TypeVar, Callable, Awaitable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from sensei.models.external.starz_erp import (
    # WMS
    StarzBase, StarzWarehouse, StarzWmsDevice, StarzWmsWorkstation,
    StarzStockLocation, StarzLicensePlate, StarzWmsTransaction, StarzInventoryCount,
    # Products
    StarzArticle, StarzUnit, StarzArticleGroup, StarzArticleCategory, StarzArticleType,
    # HR
    StarzEmployee, StarzEmployeeCNSS, StarzEmployeeContract, StarzEmployeeLeave,
    StarzEmployeeLeaveAnnual, StarzEmployeeClocking, StarzEmployeeSalary,
    StarzEmployeeBankAccount, StarzEmployeeAdvance, StarzEmployeeAbsence,
    StarzEmployeeTraining, StarzTrainingProgram, StarzEmployeeDiploma,
    StarzEmployeeAddress, StarzEmployeePhone, StarzEmployeeEmail,
    StarzEmployeeSuspension, StarzEmployeePermission, StarzEmployeeDocument,
    StarzEmployeeHistory, StarzEmployeeNote, StarzPublicHoliday,
    StarzClockingSchedule, StarzShiftSchedule,
    # Purchasing
    StarzSupplier, StarzSupplierType, StarzSupplierContact, StarzSupplierPriceRequest,
    StarzPurchaseOrder, StarzPurchaseOrderItem, StarzPOReceipt, StarzPOReceiptItem,
    StarzConsumableRequest, StarzConsumableRequestItem,
    # Sales
    StarzCustomer, StarzQuotation, StarzQuotationItem,
    # Shipping
    StarzShipment, StarzShipmentItem, StarzPickList, StarzPickListItem,
    # Finance
    StarzBank, StarzBankAccount, StarzBankTransaction, StarzPaymentTerm,
    StarzTaxCode, StarzSupplierInvoice, StarzCustomerInvoice, StarzPayment,
    # Quality
    StarzScrapRecord,
)

# =============================================================================
# Sensei OS Models - Comprehensive Import
# =============================================================================

# Inventory/WMS Models
from sensei.models.inventory import (
    Warehouse,
    Location as StockLocation,
    LicensePlate, 
    WmsDevice,
    WmsWorkstation,
    StockMove,
    InventoryLevel,
    PickList,
    PickListLine,
)

# Product Models
from sensei.models.product import Product

# HR Models - Full Suite
from sensei.models.hr import (
    EmployeeProfile as Employee,
    HRLeaveRequest as LeaveRequest,
    HRSocialSecurityRecord,
    HRContributionPeriod,
    HREmployeeContract,
    HREmployeeBankAccount,
    HREmployeeSalary,
    HREmployeeAbsence,
    HREmployeeSuspension,
    HREmployeeAdvance,
    HREmployeeDiploma,
    HREmployeeAddress,
    HREmployeePermission,
    HREmployeeDocument,
    HREmployeeHistory,
    HREmployeeNote,
    HRPublicHoliday,
    HRLeaveBalance,
    HRTimeClockEvent,
)

# Training Models
from sensei.models.training import (
    Skill,
    Training as TrainingProgram,
    TrainingParticipant,
)

# Account/Partner Models
from sensei.models.account import Account, Contact, AccountType

# Finance Models
from sensei.models.finance import (
    TaxJurisdiction,
    TaxRate,
    PaymentTerm,
    BankAccount,
    BankTransaction,
    Currency,
)

# Accounts Payable Models
from sensei.models.accounts_payable import (
    PurchaseRequisition,
    PRLine,
    PurchaseOrder,
    POLine as PurchaseOrderLine,
    GoodsReceipt,
    ReceiptLine,
    SupplierInvoice,
    SupplierInvoiceLine,
    Payment,
)

# Accounts Receivable Models
from sensei.models.accounts_receivable import (
    SalesOrder,
    SalesOrderLine,
    CustomerInvoice,
    CustomerInvoiceLine,
    Shipment,
    ShipmentLine,
    PaymentReceipt,
)

# Quality Models
from sensei.models.quality import NonConformance

# Note: StarzERP entities map to Sensei OS models as follows:
# - Some entities have direct 1:1 mappings
# - Some are stored as extended data within parent entities
# - Some StarzERP concepts map to Sensei OS enums rather than tables


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ImportEntityType(str, Enum):
    """All importable entity categories."""
    # Master Data (import first)
    UNITS = "units"
    WAREHOUSES = "warehouses"
    ARTICLE_GROUPS = "article_groups"
    ARTICLE_CATEGORIES = "article_categories"
    ARTICLE_TYPES = "article_types"
    SUPPLIER_TYPES = "supplier_types"
    PAYMENT_TERMS = "payment_terms"
    TAX_CODES = "tax_codes"
    BANKS = "banks"
    SCHEDULES = "schedules"
    PUBLIC_HOLIDAYS = "public_holidays"
    TRAINING_PROGRAMS = "training_programs"
    
    # Location/Inventory (depends on warehouses)
    STOCK_LOCATIONS = "stock_locations"
    WMS_DEVICES = "wms_devices"
    WMS_WORKSTATIONS = "wms_workstations"
    
    # Products (depends on units, categories)
    ARTICLES = "articles"
    
    # HR Core (import before details)
    EMPLOYEES = "employees"
    
    # HR Details (depends on employees)
    EMPLOYEE_CNSS = "employee_cnss"
    EMPLOYEE_CONTRACTS = "employee_contracts"
    EMPLOYEE_ADDRESSES = "employee_addresses"
    EMPLOYEE_PHONES = "employee_phones"
    EMPLOYEE_EMAILS = "employee_emails"
    EMPLOYEE_BANK_ACCOUNTS = "employee_bank_accounts"
    EMPLOYEE_DIPLOMAS = "employee_diplomas"
    EMPLOYEE_LEAVES = "employee_leaves"
    EMPLOYEE_LEAVE_BALANCES = "employee_leave_balances"
    EMPLOYEE_CLOCKING = "employee_clocking"
    EMPLOYEE_ABSENCES = "employee_absences"
    EMPLOYEE_SALARY = "employee_salary"
    EMPLOYEE_ADVANCES = "employee_advances"
    EMPLOYEE_SUSPENSIONS = "employee_suspensions"
    EMPLOYEE_PERMISSIONS = "employee_permissions"
    EMPLOYEE_TRAINING = "employee_training"
    EMPLOYEE_DOCUMENTS = "employee_documents"
    EMPLOYEE_HISTORY = "employee_history"
    EMPLOYEE_NOTES = "employee_notes"
    SHIFT_SCHEDULES = "shift_schedules"
    
    # Partners (core)
    SUPPLIERS = "suppliers"
    SUPPLIER_CONTACTS = "supplier_contacts"
    CUSTOMERS = "customers"
    COMPANY_BANK_ACCOUNTS = "company_bank_accounts"
    
    # Transactions
    LICENSE_PLATES = "license_plates"
    WMS_TRANSACTIONS = "wms_transactions"
    INVENTORY_COUNTS = "inventory_counts"
    
    # Purchasing
    PRICE_REQUESTS = "price_requests"
    PURCHASE_ORDERS = "purchase_orders"
    PO_RECEIPTS = "po_receipts"
    CONSUMABLE_REQUESTS = "consumable_requests"
    SUPPLIER_INVOICES = "supplier_invoices"
    
    # Sales
    QUOTATIONS = "quotations"
    CUSTOMER_INVOICES = "customer_invoices"
    
    # Shipping
    SHIPMENTS = "shipments"
    PICK_LISTS = "pick_lists"
    
    # Finance
    PAYMENTS = "payments"
    BANK_TRANSACTIONS = "bank_transactions"
    
    # Quality
    SCRAP_RECORDS = "scrap_records"


@dataclass
class ImportResult:
    """Result of a single entity type import."""
    entity_type: ImportEntityType
    total_source: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.imported + self.updated + self.skipped + self.failed
        if total == 0:
            return 100.0
        return ((self.imported + self.updated) / total) * 100


@dataclass
class ImportBatchResult:
    """Result of a full import batch."""
    batch_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    entity_results: Dict[ImportEntityType, ImportResult] = field(default_factory=dict)
    status: str = "in_progress"  # in_progress, completed, failed
    total_duration_seconds: float = 0.0
    
    @property
    def total_imported(self) -> int:
        return sum(r.imported for r in self.entity_results.values())
    
    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.entity_results.values())


class StarzErpImportService:
    """
    Unified service for importing ALL starzERP data into Sensei OS.
    
    Features:
    - Full entity coverage (60+ tables)
    - Dependency-aware ordering
    - Incremental/delta imports
    - Conflict resolution (skip, update, fail)
    - Progress tracking
    - Error handling and rollback
    - Audit logging
    """
    
    # Dependency graph for import ordering
    IMPORT_ORDER: List[ImportEntityType] = [
        # 1. Master data (no dependencies)
        ImportEntityType.UNITS,
        ImportEntityType.WAREHOUSES,
        ImportEntityType.ARTICLE_GROUPS,
        ImportEntityType.ARTICLE_CATEGORIES,
        ImportEntityType.ARTICLE_TYPES,
        ImportEntityType.SUPPLIER_TYPES,
        ImportEntityType.PAYMENT_TERMS,
        ImportEntityType.TAX_CODES,
        ImportEntityType.BANKS,
        ImportEntityType.SCHEDULES,
        ImportEntityType.PUBLIC_HOLIDAYS,
        ImportEntityType.TRAINING_PROGRAMS,
        
        # 2. Warehouse infrastructure
        ImportEntityType.STOCK_LOCATIONS,
        ImportEntityType.WMS_DEVICES,
        ImportEntityType.WMS_WORKSTATIONS,
        
        # 3. Products
        ImportEntityType.ARTICLES,
        
        # 4. Partners
        ImportEntityType.SUPPLIERS,
        ImportEntityType.SUPPLIER_CONTACTS,
        ImportEntityType.CUSTOMERS,
        ImportEntityType.COMPANY_BANK_ACCOUNTS,
        
        # 5. HR Core
        ImportEntityType.EMPLOYEES,
        
        # 6. HR Details
        ImportEntityType.EMPLOYEE_CNSS,
        ImportEntityType.EMPLOYEE_CONTRACTS,
        ImportEntityType.EMPLOYEE_ADDRESSES,
        ImportEntityType.EMPLOYEE_PHONES,
        ImportEntityType.EMPLOYEE_EMAILS,
        ImportEntityType.EMPLOYEE_BANK_ACCOUNTS,
        ImportEntityType.EMPLOYEE_DIPLOMAS,
        ImportEntityType.EMPLOYEE_LEAVES,
        ImportEntityType.EMPLOYEE_LEAVE_BALANCES,
        ImportEntityType.EMPLOYEE_CLOCKING,
        ImportEntityType.EMPLOYEE_ABSENCES,
        ImportEntityType.EMPLOYEE_SALARY,
        ImportEntityType.EMPLOYEE_ADVANCES,
        ImportEntityType.EMPLOYEE_SUSPENSIONS,
        ImportEntityType.EMPLOYEE_PERMISSIONS,
        ImportEntityType.EMPLOYEE_TRAINING,
        ImportEntityType.EMPLOYEE_DOCUMENTS,
        ImportEntityType.EMPLOYEE_HISTORY,
        ImportEntityType.EMPLOYEE_NOTES,
        ImportEntityType.SHIFT_SCHEDULES,
        
        # 7. Inventory transactions
        ImportEntityType.LICENSE_PLATES,
        ImportEntityType.WMS_TRANSACTIONS,
        ImportEntityType.INVENTORY_COUNTS,
        
        # 8. Purchasing flow
        ImportEntityType.PRICE_REQUESTS,
        ImportEntityType.PURCHASE_ORDERS,
        ImportEntityType.PO_RECEIPTS,
        ImportEntityType.CONSUMABLE_REQUESTS,
        ImportEntityType.SUPPLIER_INVOICES,
        
        # 9. Sales flow
        ImportEntityType.QUOTATIONS,
        ImportEntityType.CUSTOMER_INVOICES,
        
        # 10. Shipping
        ImportEntityType.SHIPMENTS,
        ImportEntityType.PICK_LISTS,
        
        # 11. Finance
        ImportEntityType.PAYMENTS,
        ImportEntityType.BANK_TRANSACTIONS,
        
        # 12. Quality
        ImportEntityType.SCRAP_RECORDS,
    ]
    
    def __init__(
        self,
        sensei_session: AsyncSession,
        starz_connection_string: Optional[str] = None,
        default_jurisdiction: str = "TN",
        batch_size: int = 500,
        on_conflict: str = "skip",  # skip, update, fail
    ):
        """
        Initialize the import service.
        
        Args:
            sensei_session: Async session for Sensei OS PostgreSQL
            starz_connection_string: MySQL connection string for starzERP
            default_jurisdiction: Default tax jurisdiction (TN for Tunisia)
            batch_size: Number of records per batch
            on_conflict: Conflict resolution strategy
        """
        self.sensei_session = sensei_session
        self.starz_connection_string = starz_connection_string
        self.default_jurisdiction = default_jurisdiction
        self.batch_size = batch_size
        self.on_conflict = on_conflict
        
        # ID mapping caches (starz_id -> sensei_uuid)
        self._id_maps: Dict[str, Dict[int, UUID]] = {}
        
        # Current batch
        self._current_batch: Optional[ImportBatchResult] = None
    
    async def _get_starz_session(self) -> async_sessionmaker:
        """Create async session factory for starzERP MySQL."""
        if not self.starz_connection_string:
            raise ValueError("starz_connection_string not configured")
        
        # Convert mysql:// to mysql+aiomysql://
        conn_str = self.starz_connection_string
        if conn_str.startswith("mysql://"):
            conn_str = conn_str.replace("mysql://", "mysql+aiomysql://", 1)
        
        engine = create_async_engine(conn_str, echo=False)
        return async_sessionmaker(engine, expire_on_commit=False)
    
    def _cache_id(self, entity_type: str, starz_id: int, sensei_id: UUID) -> None:
        """Cache ID mapping for FK resolution."""
        if entity_type not in self._id_maps:
            self._id_maps[entity_type] = {}
        self._id_maps[entity_type][starz_id] = sensei_id
    
    def _get_cached_id(self, entity_type: str, starz_id: Optional[int]) -> Optional[UUID]:
        """Get cached Sensei ID from starz ID."""
        if starz_id is None:
            return None
        return self._id_maps.get(entity_type, {}).get(starz_id)
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    async def import_all(
        self,
        entity_types: Optional[List[ImportEntityType]] = None,
        progress_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None,
    ) -> ImportBatchResult:
        """
        Import all (or selected) entity types in dependency order.
        
        Args:
            entity_types: Specific types to import (None = all)
            progress_callback: Async callback(entity_name, current, total)
        
        Returns:
            ImportBatchResult with detailed results
        """
        batch = ImportBatchResult(
            batch_id=uuid4(),
            started_at=datetime.utcnow(),
        )
        self._current_batch = batch
        
        # Determine which entities to import
        if entity_types is None:
            types_to_import = self.IMPORT_ORDER
        else:
            # Maintain dependency order
            types_to_import = [t for t in self.IMPORT_ORDER if t in entity_types]
        
        total_types = len(types_to_import)
        
        try:
            for idx, entity_type in enumerate(types_to_import):
                logger.info(f"Importing {entity_type.value} ({idx + 1}/{total_types})")
                
                if progress_callback:
                    await progress_callback(entity_type.value, idx, total_types)
                
                result = await self._import_entity_type(entity_type)
                batch.entity_results[entity_type] = result
                
                logger.info(
                    f"  Completed {entity_type.value}: "
                    f"{result.imported} imported, {result.updated} updated, "
                    f"{result.failed} failed"
                )
            
            batch.status = "completed"
        except Exception as e:
            logger.exception(f"Import batch failed: {e}")
            batch.status = "failed"
            raise
        finally:
            batch.completed_at = datetime.utcnow()
            batch.total_duration_seconds = (
                batch.completed_at - batch.started_at
            ).total_seconds()
            self._current_batch = None
        
        return batch
    
    async def preview_import(
        self,
        entity_types: Optional[List[ImportEntityType]] = None,
    ) -> Dict[ImportEntityType, Dict[str, int]]:
        """
        Preview import counts without actually importing.
        
        Returns:
            Dict mapping entity type to {source_count, existing_count, delta}
        """
        preview = {}
        starz_factory = await self._get_starz_session()
        
        types_to_preview = entity_types or self.IMPORT_ORDER
        
        async with starz_factory() as starz_session:
            for entity_type in types_to_preview:
                model_class = self._get_starz_model(entity_type)
                if model_class is None:
                    continue
                
                # Count source records
                source_count = await starz_session.scalar(
                    select(func.count()).select_from(model_class)
                )
                
                # Count existing Sensei records
                sensei_model = self._get_sensei_model(entity_type)
                existing_count = 0
                if sensei_model:
                    existing_count = await self.sensei_session.scalar(
                        select(func.count()).select_from(sensei_model)
                    ) or 0
                
                preview[entity_type] = {
                    "source_count": source_count or 0,
                    "existing_count": existing_count,
                    "delta": (source_count or 0) - existing_count,
                }
        
        return preview
    
    # =========================================================================
    # Entity Type Routing
    # =========================================================================
    
    async def _import_entity_type(self, entity_type: ImportEntityType) -> ImportResult:
        """Route to specific importer based on entity type."""
        result = ImportResult(entity_type=entity_type)
        start_time = datetime.utcnow()
        
        importers = {
            # Master Data
            ImportEntityType.UNITS: self._import_units,
            ImportEntityType.WAREHOUSES: self._import_warehouses,
            ImportEntityType.ARTICLE_GROUPS: self._import_article_groups,
            ImportEntityType.ARTICLE_CATEGORIES: self._import_article_categories,
            ImportEntityType.ARTICLE_TYPES: self._import_article_types,
            ImportEntityType.SUPPLIER_TYPES: self._import_supplier_types,
            ImportEntityType.PAYMENT_TERMS: self._import_payment_terms,
            ImportEntityType.TAX_CODES: self._import_tax_codes,
            ImportEntityType.BANKS: self._import_banks,
            ImportEntityType.SCHEDULES: self._import_schedules,
            ImportEntityType.PUBLIC_HOLIDAYS: self._import_public_holidays,
            ImportEntityType.TRAINING_PROGRAMS: self._import_training_programs,
            
            # Warehouse
            ImportEntityType.STOCK_LOCATIONS: self._import_stock_locations,
            ImportEntityType.WMS_DEVICES: self._import_wms_devices,
            ImportEntityType.WMS_WORKSTATIONS: self._import_wms_workstations,
            
            # Products
            ImportEntityType.ARTICLES: self._import_articles,
            
            # Partners
            ImportEntityType.SUPPLIERS: self._import_suppliers,
            ImportEntityType.SUPPLIER_CONTACTS: self._import_supplier_contacts,
            ImportEntityType.CUSTOMERS: self._import_customers,
            ImportEntityType.COMPANY_BANK_ACCOUNTS: self._import_company_bank_accounts,
            
            # HR Core
            ImportEntityType.EMPLOYEES: self._import_employees,
            
            # HR Details
            ImportEntityType.EMPLOYEE_CNSS: self._import_employee_cnss,
            ImportEntityType.EMPLOYEE_CONTRACTS: self._import_employee_contracts,
            ImportEntityType.EMPLOYEE_ADDRESSES: self._import_employee_addresses,
            ImportEntityType.EMPLOYEE_PHONES: self._import_employee_phones,
            ImportEntityType.EMPLOYEE_EMAILS: self._import_employee_emails,
            ImportEntityType.EMPLOYEE_BANK_ACCOUNTS: self._import_employee_bank_accounts,
            ImportEntityType.EMPLOYEE_DIPLOMAS: self._import_employee_diplomas,
            ImportEntityType.EMPLOYEE_LEAVES: self._import_employee_leaves,
            ImportEntityType.EMPLOYEE_LEAVE_BALANCES: self._import_employee_leave_balances,
            ImportEntityType.EMPLOYEE_CLOCKING: self._import_employee_clocking,
            ImportEntityType.EMPLOYEE_ABSENCES: self._import_employee_absences,
            ImportEntityType.EMPLOYEE_SALARY: self._import_employee_salary,
            ImportEntityType.EMPLOYEE_ADVANCES: self._import_employee_advances,
            ImportEntityType.EMPLOYEE_SUSPENSIONS: self._import_employee_suspensions,
            ImportEntityType.EMPLOYEE_PERMISSIONS: self._import_employee_permissions,
            ImportEntityType.EMPLOYEE_TRAINING: self._import_employee_training,
            ImportEntityType.EMPLOYEE_DOCUMENTS: self._import_employee_documents,
            ImportEntityType.EMPLOYEE_HISTORY: self._import_employee_history,
            ImportEntityType.EMPLOYEE_NOTES: self._import_employee_notes,
            ImportEntityType.SHIFT_SCHEDULES: self._import_shift_schedules,
            
            # Inventory
            ImportEntityType.LICENSE_PLATES: self._import_license_plates,
            ImportEntityType.WMS_TRANSACTIONS: self._import_wms_transactions,
            ImportEntityType.INVENTORY_COUNTS: self._import_inventory_counts,
            
            # Purchasing
            ImportEntityType.PRICE_REQUESTS: self._import_price_requests,
            ImportEntityType.PURCHASE_ORDERS: self._import_purchase_orders,
            ImportEntityType.PO_RECEIPTS: self._import_po_receipts,
            ImportEntityType.CONSUMABLE_REQUESTS: self._import_consumable_requests,
            ImportEntityType.SUPPLIER_INVOICES: self._import_supplier_invoices,
            
            # Sales
            ImportEntityType.QUOTATIONS: self._import_quotations,
            ImportEntityType.CUSTOMER_INVOICES: self._import_customer_invoices,
            
            # Shipping
            ImportEntityType.SHIPMENTS: self._import_shipments,
            ImportEntityType.PICK_LISTS: self._import_pick_lists,
            
            # Finance
            ImportEntityType.PAYMENTS: self._import_payments,
            ImportEntityType.BANK_TRANSACTIONS: self._import_bank_transactions,
            
            # Quality
            ImportEntityType.SCRAP_RECORDS: self._import_scrap_records,
        }
        
        importer = importers.get(entity_type)
        if importer is None:
            result.errors.append(f"No importer defined for {entity_type.value}")
            result.failed = 1
            return result
        
        try:
            await importer(result)
        except Exception as e:
            logger.exception(f"Error importing {entity_type.value}")
            result.errors.append(str(e))
            result.failed += 1
        
        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        return result
    
    def _get_starz_model(self, entity_type: ImportEntityType) -> Optional[Type]:
        """Get starzERP model class for entity type."""
        mapping = {
            ImportEntityType.UNITS: StarzUnit,
            ImportEntityType.WAREHOUSES: StarzWarehouse,
            ImportEntityType.ARTICLE_GROUPS: StarzArticleGroup,
            ImportEntityType.ARTICLE_CATEGORIES: StarzArticleCategory,
            ImportEntityType.ARTICLE_TYPES: StarzArticleType,
            ImportEntityType.SUPPLIER_TYPES: StarzSupplierType,
            ImportEntityType.PAYMENT_TERMS: StarzPaymentTerm,
            ImportEntityType.TAX_CODES: StarzTaxCode,
            ImportEntityType.BANKS: StarzBank,
            ImportEntityType.SCHEDULES: StarzClockingSchedule,
            ImportEntityType.PUBLIC_HOLIDAYS: StarzPublicHoliday,
            ImportEntityType.TRAINING_PROGRAMS: StarzTrainingProgram,
            ImportEntityType.STOCK_LOCATIONS: StarzStockLocation,
            ImportEntityType.WMS_DEVICES: StarzWmsDevice,
            ImportEntityType.WMS_WORKSTATIONS: StarzWmsWorkstation,
            ImportEntityType.ARTICLES: StarzArticle,
            ImportEntityType.SUPPLIERS: StarzSupplier,
            ImportEntityType.SUPPLIER_CONTACTS: StarzSupplierContact,
            ImportEntityType.CUSTOMERS: StarzCustomer,
            ImportEntityType.COMPANY_BANK_ACCOUNTS: StarzBankAccount,
            ImportEntityType.EMPLOYEES: StarzEmployee,
            ImportEntityType.EMPLOYEE_CNSS: StarzEmployeeCNSS,
            ImportEntityType.EMPLOYEE_CONTRACTS: StarzEmployeeContract,
            ImportEntityType.EMPLOYEE_ADDRESSES: StarzEmployeeAddress,
            ImportEntityType.EMPLOYEE_PHONES: StarzEmployeePhone,
            ImportEntityType.EMPLOYEE_EMAILS: StarzEmployeeEmail,
            ImportEntityType.EMPLOYEE_BANK_ACCOUNTS: StarzEmployeeBankAccount,
            ImportEntityType.EMPLOYEE_DIPLOMAS: StarzEmployeeDiploma,
            ImportEntityType.EMPLOYEE_LEAVES: StarzEmployeeLeave,
            ImportEntityType.EMPLOYEE_LEAVE_BALANCES: StarzEmployeeLeaveAnnual,
            ImportEntityType.EMPLOYEE_CLOCKING: StarzEmployeeClocking,
            ImportEntityType.EMPLOYEE_ABSENCES: StarzEmployeeAbsence,
            ImportEntityType.EMPLOYEE_SALARY: StarzEmployeeSalary,
            ImportEntityType.EMPLOYEE_ADVANCES: StarzEmployeeAdvance,
            ImportEntityType.EMPLOYEE_SUSPENSIONS: StarzEmployeeSuspension,
            ImportEntityType.EMPLOYEE_PERMISSIONS: StarzEmployeePermission,
            ImportEntityType.EMPLOYEE_TRAINING: StarzEmployeeTraining,
            ImportEntityType.EMPLOYEE_DOCUMENTS: StarzEmployeeDocument,
            ImportEntityType.EMPLOYEE_HISTORY: StarzEmployeeHistory,
            ImportEntityType.EMPLOYEE_NOTES: StarzEmployeeNote,
            ImportEntityType.SHIFT_SCHEDULES: StarzShiftSchedule,
            ImportEntityType.LICENSE_PLATES: StarzLicensePlate,
            ImportEntityType.WMS_TRANSACTIONS: StarzWmsTransaction,
            ImportEntityType.INVENTORY_COUNTS: StarzInventoryCount,
            ImportEntityType.PRICE_REQUESTS: StarzSupplierPriceRequest,
            ImportEntityType.PURCHASE_ORDERS: StarzPurchaseOrder,
            ImportEntityType.PO_RECEIPTS: StarzPOReceipt,
            ImportEntityType.CONSUMABLE_REQUESTS: StarzConsumableRequest,
            ImportEntityType.SUPPLIER_INVOICES: StarzSupplierInvoice,
            ImportEntityType.QUOTATIONS: StarzQuotation,
            ImportEntityType.CUSTOMER_INVOICES: StarzCustomerInvoice,
            ImportEntityType.SHIPMENTS: StarzShipment,
            ImportEntityType.PICK_LISTS: StarzPickList,
            ImportEntityType.PAYMENTS: StarzPayment,
            ImportEntityType.BANK_TRANSACTIONS: StarzBankTransaction,
            ImportEntityType.SCRAP_RECORDS: StarzScrapRecord,
        }
        return mapping.get(entity_type)
    
    def _get_sensei_model(self, entity_type: ImportEntityType) -> Optional[Type]:
        """Get Sensei OS model class for entity type.
        
        Maps StarzERP entity types to their corresponding Sensei OS models.
        Returns None for entities that don't have direct model mappings
        (e.g., enums, or data stored as extended_data in parent models).
        """
        mapping = {
            # Inventory/WMS
            ImportEntityType.WAREHOUSES: Warehouse,
            ImportEntityType.STOCK_LOCATIONS: StockLocation,
            ImportEntityType.WMS_DEVICES: WmsDevice,
            ImportEntityType.WMS_WORKSTATIONS: WmsWorkstation,
            ImportEntityType.LICENSE_PLATES: LicensePlate,
            ImportEntityType.WMS_TRANSACTIONS: StockMove,
            ImportEntityType.INVENTORY_COUNTS: InventoryLevel,
            
            # Products
            ImportEntityType.ARTICLES: Product,
            # Note: UNITS, ARTICLE_GROUPS, ARTICLE_CATEGORIES, ARTICLE_TYPES
            # are stored as product metadata/enums, not separate tables
            
            # HR Core
            ImportEntityType.EMPLOYEES: Employee,
            ImportEntityType.EMPLOYEE_CNSS: HRSocialSecurityRecord,
            ImportEntityType.EMPLOYEE_CONTRACTS: HREmployeeContract,
            ImportEntityType.EMPLOYEE_ADDRESSES: HREmployeeAddress,
            ImportEntityType.EMPLOYEE_BANK_ACCOUNTS: HREmployeeBankAccount,
            ImportEntityType.EMPLOYEE_DIPLOMAS: HREmployeeDiploma,
            ImportEntityType.EMPLOYEE_LEAVES: LeaveRequest,
            ImportEntityType.EMPLOYEE_LEAVE_BALANCES: HRLeaveBalance,
            ImportEntityType.EMPLOYEE_CLOCKING: HRTimeClockEvent,
            ImportEntityType.EMPLOYEE_ABSENCES: HREmployeeAbsence,
            ImportEntityType.EMPLOYEE_SALARY: HREmployeeSalary,
            ImportEntityType.EMPLOYEE_ADVANCES: HREmployeeAdvance,
            ImportEntityType.EMPLOYEE_SUSPENSIONS: HREmployeeSuspension,
            ImportEntityType.EMPLOYEE_PERMISSIONS: HREmployeePermission,
            ImportEntityType.EMPLOYEE_DOCUMENTS: HREmployeeDocument,
            ImportEntityType.EMPLOYEE_HISTORY: HREmployeeHistory,
            ImportEntityType.EMPLOYEE_NOTES: HREmployeeNote,
            ImportEntityType.PUBLIC_HOLIDAYS: HRPublicHoliday,
            
            # Training
            ImportEntityType.TRAINING_PROGRAMS: TrainingProgram,
            ImportEntityType.EMPLOYEE_TRAINING: TrainingParticipant,
            
            # Partners
            ImportEntityType.SUPPLIERS: Account,  # AccountType.SUPPLIER
            ImportEntityType.CUSTOMERS: Account,  # AccountType.CUSTOMER
            ImportEntityType.SUPPLIER_CONTACTS: Contact,
            
            # Finance
            ImportEntityType.TAX_CODES: TaxRate,
            ImportEntityType.PAYMENT_TERMS: PaymentTerm,
            ImportEntityType.COMPANY_BANK_ACCOUNTS: BankAccount,
            ImportEntityType.BANK_TRANSACTIONS: BankTransaction,
            ImportEntityType.PAYMENTS: Payment,
            
            # Purchasing
            ImportEntityType.CONSUMABLE_REQUESTS: PurchaseRequisition,
            ImportEntityType.PURCHASE_ORDERS: PurchaseOrder,
            ImportEntityType.PO_RECEIPTS: GoodsReceipt,
            ImportEntityType.SUPPLIER_INVOICES: SupplierInvoice,
            
            # Sales
            ImportEntityType.QUOTATIONS: SalesOrder,  # Quotations become Sales Orders
            ImportEntityType.CUSTOMER_INVOICES: CustomerInvoice,
            
            # Shipping
            ImportEntityType.SHIPMENTS: Shipment,
            # PICK_LISTS don't have a direct model - handled via Shipment workflow
            
            # Quality
            ImportEntityType.SCRAP_RECORDS: NonConformance,
        }
        return mapping.get(entity_type)
    
    # =========================================================================
    # Master Data Importers
    # =========================================================================
    
    async def _import_units(self, result: ImportResult) -> None:
        """Import units of measure - stored as product metadata in Sensei.
        
        Note: UnitOfMeasure in Sensei is an Enum, not a table.
        We cache the unit codes for FK resolution when importing products.
        """
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            starz_units = (await starz_session.execute(select(StarzUnit))).scalars().all()
            result.total_source = len(starz_units)
            
            for su in starz_units:
                try:
                    # Cache the unit mapping for FK resolution
                    # Generate a UUID placeholder since units are enum-based in Sensei
                    self._cache_id("unit", su.id, uuid4())
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Unit {su.code}: {e}")
    
    async def _import_warehouses(self, result: ImportResult) -> None:
        """Import warehouses."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            starz_wh = (await starz_session.execute(select(StarzWarehouse))).scalars().all()
            result.total_source = len(starz_wh)
            
            for sw in starz_wh:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Warehouse).where(Warehouse.code == sw.code)
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("warehouse", sw.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.name = sw.name
                            existing.description = sw.description
                            existing.address = sw.address
                            existing.city = sw.city
                            existing.country = sw.country
                            existing.is_active = sw.is_active
                            result.updated += 1
                            self._cache_id("warehouse", sw.id, existing.id)
                            continue
                    
                    wh = Warehouse(
                        code=sw.code,
                        name=sw.name,
                        description=sw.description,
                        address=sw.address,
                        city=sw.city,
                        country=sw.country or self.default_jurisdiction,
                        is_active=sw.is_active,
                    )
                    self.sensei_session.add(wh)
                    await self.sensei_session.flush()
                    self._cache_id("warehouse", sw.id, wh.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Warehouse {sw.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_article_groups(self, result: ImportResult) -> None:
        """Import product groups - cached for product category mapping.
        
        Note: Sensei OS stores product categories as string fields on Product,
        not as a separate table. We cache these for reference when importing products.
        """
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            groups = (await starz_session.execute(select(StarzArticleGroup))).scalars().all()
            result.total_source = len(groups)
            
            for g in groups:
                try:
                    # Cache group info for product import
                    self._cache_id("article_group", g.id, uuid4())
                    # Also cache the name for use as product_family
                    self._id_cache[f"article_group_name:{g.id}"] = g.name
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"ArticleGroup {g.code}: {e}")
    
    async def _import_article_categories(self, result: ImportResult) -> None:
        """Import product categories - cached for product category mapping.
        
        Note: Sensei OS stores product categories as string fields on Product.
        """
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            cats = (await starz_session.execute(select(StarzArticleCategory))).scalars().all()
            result.total_source = len(cats)
            
            for c in cats:
                try:
                    # Cache category info for product import
                    self._cache_id("article_category", c.id, uuid4())
                    # Also cache the name for use as product_category
                    self._id_cache[f"article_category_name:{c.id}"] = c.name
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"ArticleCategory {c.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_article_types(self, result: ImportResult) -> None:
        """Import product types - cached for product type mapping.
        
        Note: Sensei OS stores product types as string fields on Product.
        """
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            types = (await starz_session.execute(select(StarzArticleType))).scalars().all()
            result.total_source = len(types)
            
            for t in types:
                try:
                    # Cache type info for product import
                    self._cache_id("article_type", t.id, uuid4())
                    # Also cache the name for use in product.category
                    self._id_cache[f"article_type_name:{t.id}"] = t.name
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"ArticleType {t.code}: {e}")
    
    async def _import_supplier_types(self, result: ImportResult) -> None:
        """Import supplier type classifications - cached for supplier import."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            types = (await starz_session.execute(select(StarzSupplierType))).scalars().all()
            result.total_source = len(types)
            
            for t in types:
                # Cache for reference when importing suppliers
                self._cache_id("supplier_type", t.id, uuid4())
                self._id_cache[f"supplier_type_name:{t.id}"] = t.name
                result.imported += 1
    
    async def _import_payment_terms(self, result: ImportResult) -> None:
        """Import payment terms into PaymentTerm model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            terms = (await starz_session.execute(select(StarzPaymentTerm))).scalars().all()
            result.total_source = len(terms)
            
            for t in terms:
                try:
                    existing = await self.sensei_session.scalar(
                        select(PaymentTerm).where(PaymentTerm.code == t.code)
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("payment_term", t.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.name = t.name
                            existing.days = t.days
                            result.updated += 1
                            self._cache_id("payment_term", t.id, existing.id)
                            continue
                    
                    term = PaymentTerm(
                        code=t.code,
                        name=t.name,
                        days=t.days or 30,
                        description=t.description,
                    )
                    self.sensei_session.add(term)
                    await self.sensei_session.flush()
                    self._cache_id("payment_term", t.id, term.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"PaymentTerm {t.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_tax_codes(self, result: ImportResult) -> None:
        """Import tax codes into TaxRate model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            codes = (await starz_session.execute(select(StarzTaxCode))).scalars().all()
            result.total_source = len(codes)
            
            for c in codes:
                try:
                    existing = await self.sensei_session.scalar(
                        select(TaxRate).where(TaxRate.code == c.code)
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("tax_code", c.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.name = c.name
                            existing.rate = Decimal(str(c.rate))
                            result.updated += 1
                            self._cache_id("tax_code", c.id, existing.id)
                            continue
                    
                    tax = TaxRate(
                        code=c.code,
                        name=c.name,
                        rate=Decimal(str(c.rate)),
                        is_active=c.is_active if c.is_active is not None else True,
                    )
                    self.sensei_session.add(tax)
                    await self.sensei_session.flush()
                    self._cache_id("tax_code", c.id, tax.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"TaxCode {c.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_banks(self, result: ImportResult) -> None:
        """Import bank master data - stored as company bank accounts."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            banks = (await starz_session.execute(select(StarzBank))).scalars().all()
            result.total_source = len(banks)
            
            for b in banks:
                # Cache bank references for account creation
                self._cache_id("bank", b.id, uuid4())
                result.imported += 1
    
    async def _import_schedules(self, result: ImportResult) -> None:
        """Import work schedules."""
        # Work schedules - HR module handles this
        result.skipped = 0
        logger.info("Schedules imported via HR module")
    
    async def _import_public_holidays(self, result: ImportResult) -> None:
        """Import public holidays into HRPublicHoliday model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            holidays = (await starz_session.execute(select(StarzPublicHoliday))).scalars().all()
            result.total_source = len(holidays)
            
            for h in holidays:
                try:
                    existing = await self.sensei_session.scalar(
                        select(HRPublicHoliday).where(
                            HRPublicHoliday.date == h.date,
                            HRPublicHoliday.jurisdiction == (h.jurisdiction or self.default_jurisdiction)
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            continue
                        elif self.on_conflict == "update":
                            existing.name = h.name
                            existing.is_recurring = h.is_recurring
                            result.updated += 1
                            continue
                    
                    holiday = HRPublicHoliday(
                        name=h.name,
                        date=h.date,
                        jurisdiction=h.jurisdiction or self.default_jurisdiction,
                        is_recurring=h.is_recurring or False,
                    )
                    self.sensei_session.add(holiday)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Holiday {h.name}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_training_programs(self, result: ImportResult) -> None:
        """Import training programs."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            programs = (await starz_session.execute(select(StarzTrainingProgram))).scalars().all()
            result.total_source = len(programs)
            
            for p in programs:
                try:
                    existing = await self.sensei_session.scalar(
                        select(TrainingProgram).where(TrainingProgram.code == p.code)
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("training_program", p.id, existing.id)
                        continue
                    
                    prog = TrainingProgram(
                        code=p.code,
                        name=p.name,
                        description=p.description,
                        duration_hours=p.duration_hours,
                        is_mandatory=p.is_mandatory,
                        is_active=p.is_active,
                    )
                    self.sensei_session.add(prog)
                    await self.sensei_session.flush()
                    self._cache_id("training_program", p.id, prog.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"TrainingProgram {p.code}: {e}")
            
            await self.sensei_session.commit()
    
    # =========================================================================
    # Warehouse Infrastructure Importers
    # =========================================================================
    
    async def _import_stock_locations(self, result: ImportResult) -> None:
        """Import stock locations."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            locs = (await starz_session.execute(select(StarzStockLocation))).scalars().all()
            result.total_source = len(locs)
            
            for loc in locs:
                try:
                    warehouse_id = self._get_cached_id("warehouse", loc.warehouse_id)
                    if not warehouse_id:
                        result.failed += 1
                        result.errors.append(f"Location {loc.code}: warehouse not found")
                        continue
                    
                    existing = await self.sensei_session.scalar(
                        select(StockLocation).where(
                            StockLocation.code == loc.code,
                            StockLocation.warehouse_id == warehouse_id
                        )
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("location", loc.id, existing.id)
                        continue
                    
                    sl = StockLocation(
                        code=loc.code,
                        warehouse_id=warehouse_id,
                        location_type=loc.type,
                        label=loc.label,
                        zone=loc.zone,
                        aisle=loc.aisle,
                        rack=loc.rack,
                        level=loc.level,
                        bin=loc.bin,
                        is_active=loc.is_active,
                    )
                    self.sensei_session.add(sl)
                    await self.sensei_session.flush()
                    self._cache_id("location", loc.id, sl.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Location {loc.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_wms_devices(self, result: ImportResult) -> None:
        """Import WMS devices."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            devices = (await starz_session.execute(select(StarzWmsDevice))).scalars().all()
            result.total_source = len(devices)
            
            for d in devices:
                try:
                    warehouse_id = self._get_cached_id("warehouse", d.warehouse_id)
                    
                    existing = await self.sensei_session.scalar(
                        select(WmsDevice).where(
                            WmsDevice.device_identifier == d.device_identifier
                        )
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("device", d.id, existing.id)
                        continue
                    
                    dev = WmsDevice(
                        device_identifier=d.device_identifier,
                        name=d.name,
                        device_type=d.device_type,
                        status=d.status,
                        warehouse_id=warehouse_id,
                        capabilities=d.capabilities,
                        is_active=d.is_active,
                    )
                    self.sensei_session.add(dev)
                    await self.sensei_session.flush()
                    self._cache_id("device", d.id, dev.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Device {d.device_identifier}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_wms_workstations(self, result: ImportResult) -> None:
        """Import WMS workstations."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            stations = (await starz_session.execute(select(StarzWmsWorkstation))).scalars().all()
            result.total_source = len(stations)
            
            for ws in stations:
                try:
                    warehouse_id = self._get_cached_id("warehouse", ws.warehouse_id)
                    
                    existing = await self.sensei_session.scalar(
                        select(WmsWorkstation).where(
                            WmsWorkstation.workstation_code == ws.workstation_code
                        )
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("workstation", ws.id, existing.id)
                        continue
                    
                    station = WmsWorkstation(
                        workstation_code=ws.workstation_code,
                        warehouse_id=warehouse_id,
                        station_type=ws.station_type,
                        scanner_model=ws.scanner_model,
                        scanner_serial=ws.scanner_serial,
                        connection_type=ws.connection_type,
                        pc_hostname=ws.pc_hostname,
                        is_active=ws.is_active,
                    )
                    self.sensei_session.add(station)
                    await self.sensei_session.flush()
                    self._cache_id("workstation", ws.id, station.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Workstation {ws.workstation_code}: {e}")
            
            await self.sensei_session.commit()
    
    # =========================================================================
    # Product Importers
    # =========================================================================
    
    async def _import_articles(self, result: ImportResult) -> None:
        """Import products/articles."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            articles = (await starz_session.execute(select(StarzArticle))).scalars().all()
            result.total_source = len(articles)
            
            for a in articles:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Product).where(Product.sku == a.code_reference)
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("article", a.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.name = a.description
                            existing.standard_cost = Decimal(str(a.prix))
                            result.updated += 1
                            self._cache_id("article", a.id, existing.id)
                            continue
                    
                    unit_id = self._get_cached_id("unit", a.unit_id)
                    category_id = self._get_cached_id("article_type", a.type_id) or \
                                  self._get_cached_id("article_category", a.category_id) or \
                                  self._get_cached_id("article_group", a.group_id)
                    
                    product = Product(
                        sku=a.code_reference,
                        name=a.description,
                        standard_cost=Decimal(str(a.prix)) if a.prix else None,
                        unit_of_measure_id=unit_id,
                        category_id=category_id,
                        min_stock=a.min_stock,
                        max_stock=a.max_stock,
                        reorder_point=a.reorder_point,
                        lead_time_days=a.lead_time_days,
                        barcode=a.barcode,
                        is_active=a.is_active,
                    )
                    self.sensei_session.add(product)
                    await self.sensei_session.flush()
                    self._cache_id("article", a.id, product.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Article {a.code_reference}: {e}")
            
            await self.sensei_session.commit()
    
    # =========================================================================
    # Partner Importers
    # =========================================================================
    
    async def _import_suppliers(self, result: ImportResult) -> None:
        """Import suppliers as Accounts."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            suppliers = (await starz_session.execute(select(StarzSupplier))).scalars().all()
            result.total_source = len(suppliers)
            
            for s in suppliers:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Account).where(
                            Account.code == s.code,
                            Account.account_type == AccountType.SUPPLIER
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("supplier", s.id, existing.id)
                            continue
                    
                    account = Account(
                        code=s.code,
                        name=s.name,
                        account_type=AccountType.SUPPLIER,
                        phone=s.phone,
                        email=s.email,
                        address=s.address,
                        city=s.city,
                        country=s.country or self.default_jurisdiction,
                        tax_id=s.tax_id,
                        payment_terms_days=s.payment_terms_days,
                        currency=s.currency,
                        is_active=s.is_active,
                    )
                    self.sensei_session.add(account)
                    await self.sensei_session.flush()
                    self._cache_id("supplier", s.id, account.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Supplier {s.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_supplier_contacts(self, result: ImportResult) -> None:
        """Import supplier contacts."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            contacts = (await starz_session.execute(select(StarzSupplierContact))).scalars().all()
            result.total_source = len(contacts)
            
            for c in contacts:
                try:
                    account_id = self._get_cached_id("supplier", c.supplier_id)
                    if not account_id:
                        result.skipped += 1
                        continue
                    
                    contact = Contact(
                        account_id=account_id,
                        name=c.name,
                        title=c.title,
                        phone=c.phone,
                        email=c.email,
                        is_primary=c.is_primary,
                    )
                    self.sensei_session.add(contact)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"SupplierContact: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_customers(self, result: ImportResult) -> None:
        """Import customers as Accounts."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            customers = (await starz_session.execute(select(StarzCustomer))).scalars().all()
            result.total_source = len(customers)
            
            for c in customers:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Account).where(
                            Account.code == c.code,
                            Account.account_type == AccountType.CUSTOMER
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("customer", c.id, existing.id)
                            continue
                    
                    account = Account(
                        code=c.code,
                        name=c.name,
                        account_type=AccountType.CUSTOMER,
                        phone=c.phone,
                        email=c.email,
                        address=c.address,
                        city=c.city,
                        country=c.country or self.default_jurisdiction,
                        tax_id=c.tax_id,
                        credit_limit=Decimal(str(c.credit_limit)) if c.credit_limit else None,
                        payment_terms_days=c.payment_terms_days,
                        currency=c.currency,
                        is_active=c.is_active,
                    )
                    self.sensei_session.add(account)
                    await self.sensei_session.flush()
                    self._cache_id("customer", c.id, account.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Customer {c.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_company_bank_accounts(self, result: ImportResult) -> None:
        """Import company bank accounts into BankAccount model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            accounts = (await starz_session.execute(select(StarzBankAccount))).scalars().all()
            result.total_source = len(accounts)
            
            for a in accounts:
                try:
                    existing = await self.sensei_session.scalar(
                        select(BankAccount).where(
                            BankAccount.account_number == a.account_number
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("bank_account", a.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.name = a.name
                            existing.bank_name = a.bank_name
                            existing.iban = a.iban
                            result.updated += 1
                            self._cache_id("bank_account", a.id, existing.id)
                            continue
                    
                    account = BankAccount(
                        name=a.name,
                        bank_name=a.bank_name,
                        account_number=a.account_number,
                        iban=a.iban,
                        swift_code=a.swift,
                        currency=a.currency or "MAD",
                        is_active=a.is_active if a.is_active is not None else True,
                    )
                    self.sensei_session.add(account)
                    await self.sensei_session.flush()
                    self._cache_id("bank_account", a.id, account.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"BankAccount {a.account_number}: {e}")
            
            await self.sensei_session.commit()
    
    # =========================================================================
    # HR Importers
    # =========================================================================
    
    async def _import_employees(self, result: ImportResult) -> None:
        """Import employee core records."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            employees = (await starz_session.execute(select(StarzEmployee))).scalars().all()
            result.total_source = len(employees)
            
            for starz_emp in employees:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Employee).where(Employee.employee_number == starz_emp.registration_nbr)
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("employee", starz_emp.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.first_name = starz_emp.first_name
                            existing.last_name = starz_emp.last_name
                            existing.birth_date = starz_emp.birth_date
                            existing.gender = starz_emp.gender
                            existing.is_active = starz_emp.is_active
                            result.updated += 1
                            self._cache_id("employee", starz_emp.id, existing.id)
                            continue
                    
                    emp = Employee(
                        employee_number=starz_emp.registration_nbr,
                        first_name=starz_emp.first_name,
                        last_name=starz_emp.last_name,
                        birth_date=starz_emp.birth_date,
                        gender=starz_emp.gender,
                        national_id=starz_emp.cin_nbr,
                        photo_url=starz_emp.photo,
                        is_active=starz_emp.is_active,
                    )
                    self.sensei_session.add(emp)
                    await self.sensei_session.flush()
                    self._cache_id("employee", starz_emp.id, emp.id)
                    result.imported += 1
                    
                except Exception as ex:
                    result.failed += 1
                    result.errors.append(f"Employee {starz_emp.registration_nbr}: {ex}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_cnss(self, result: ImportResult) -> None:
        """Import employee CNSS data into HRSocialSecurityRecord model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            cnss_records = (await starz_session.execute(select(StarzEmployeeCNSS))).scalars().all()
            result.total_source = len(cnss_records)
            
            for c in cnss_records:
                try:
                    employee_id = self._get_cached_id("employee", c.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    existing = await self.sensei_session.scalar(
                        select(HRSocialSecurityRecord).where(
                            HRSocialSecurityRecord.employee_id == employee_id,
                            HRSocialSecurityRecord.registration_number == c.cnss_number
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            continue
                        elif self.on_conflict == "update":
                            existing.status = c.status or "active"
                            result.updated += 1
                            continue
                    
                    record = HRSocialSecurityRecord(
                        employee_id=employee_id,
                        registration_number=c.cnss_number,
                        registration_date=c.registration_date,
                        status=c.status or "active",
                        jurisdiction=self.default_jurisdiction,
                    )
                    self.sensei_session.add(record)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"CNSS {c.cnss_number}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_contracts(self, result: ImportResult) -> None:
        """Import employee contracts into HREmployeeContract model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            contracts = (await starz_session.execute(select(StarzEmployeeContract))).scalars().all()
            result.total_source = len(contracts)
            
            for c in contracts:
                try:
                    employee_id = self._get_cached_id("employee", c.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    # Check for existing contract
                    existing = await self.sensei_session.scalar(
                        select(HREmployeeContract).where(
                            HREmployeeContract.employee_id == employee_id,
                            HREmployeeContract.contract_number == c.c_nbr
                        )
                    )
                    
                    if existing:
                        if self.on_conflict == "skip":
                            result.skipped += 1
                            self._cache_id("contract", c.id, existing.id)
                            continue
                        elif self.on_conflict == "update":
                            existing.contract_type = c.type
                            existing.status = c.status
                            existing.start_date = c.started_at
                            existing.end_date = c.ends_at
                            existing.department = c.department
                            existing.job_title = c.job_title
                            existing.base_salary = Decimal(str(c.salary)) if c.salary else None
                            result.updated += 1
                            self._cache_id("contract", c.id, existing.id)
                            continue
                    
                    contract = HREmployeeContract(
                        employee_id=employee_id,
                        contract_number=c.c_nbr,
                        contract_type=c.type or "permanent",
                        status=c.status or "active",
                        start_date=c.started_at,
                        end_date=c.ends_at,
                        department=c.department,
                        job_title=c.job_title,
                        base_salary=Decimal(str(c.salary)) if c.salary else None,
                    )
                    self.sensei_session.add(contract)
                    await self.sensei_session.flush()
                    self._cache_id("contract", c.id, contract.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Contract {c.c_nbr}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_addresses(self, result: ImportResult) -> None:
        """Import employee addresses into HREmployeeAddress model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            addresses = (await starz_session.execute(select(StarzEmployeeAddress))).scalars().all()
            result.total_source = len(addresses)
            
            for a in addresses:
                try:
                    employee_id = self._get_cached_id("employee", a.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    address = HREmployeeAddress(
                        employee_id=employee_id,
                        address_type=a.type or "home",
                        street_address=a.street,
                        city=a.city,
                        state_province=a.state,
                        postal_code=a.postal_code,
                        country=a.country or self.default_jurisdiction,
                        is_primary=a.is_primary or False,
                    )
                    self.sensei_session.add(address)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Address: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_phones(self, result: ImportResult) -> None:
        """Import employee phones - stored in employee extended_data."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            phones = (await starz_session.execute(select(StarzEmployeePhone))).scalars().all()
            result.total_source = len(phones)
            
            for p in phones:
                try:
                    employee_id = self._get_cached_id("employee", p.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    # Store phones in employee extended_data (no separate phone model)
                    employee = await self.sensei_session.get(Employee, employee_id)
                    if employee:
                        if employee.extended_data is None:
                            employee.extended_data = {}
                        phones_list = employee.extended_data.get('phones', [])
                        phones_list.append({
                            'type': p.type,
                            'number': p.number,
                            'is_primary': p.is_primary,
                        })
                        employee.extended_data['phones'] = phones_list
                        result.imported += 1
                    else:
                        result.skipped += 1
                        
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Phone: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_emails(self, result: ImportResult) -> None:
        """Import employee emails - stored in employee extended_data."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            emails = (await starz_session.execute(select(StarzEmployeeEmail))).scalars().all()
            result.total_source = len(emails)
            
            for e in emails:
                try:
                    employee_id = self._get_cached_id("employee", e.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    employee = await self.sensei_session.get(Employee, employee_id)
                    if employee:
                        if employee.extended_data is None:
                            employee.extended_data = {}
                        emails_list = employee.extended_data.get('emails', [])
                        emails_list.append({
                            'type': e.type,
                            'email': e.email,
                            'is_primary': e.is_primary,
                        })
                        employee.extended_data['emails'] = emails_list
                        result.imported += 1
                    else:
                        result.skipped += 1
                        
                except Exception as ex:
                    result.failed += 1
                    result.errors.append(f"Email: {ex}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_bank_accounts(self, result: ImportResult) -> None:
        """Import employee bank accounts into HREmployeeBankAccount model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            accounts = (await starz_session.execute(select(StarzEmployeeBankAccount))).scalars().all()
            result.total_source = len(accounts)
            
            for a in accounts:
                try:
                    employee_id = self._get_cached_id("employee", a.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    bank_account = HREmployeeBankAccount(
                        employee_id=employee_id,
                        bank_name=a.bank_name,
                        account_number=a.account_number,
                        rib=a.rib,
                        iban=a.iban,
                        swift_code=a.swift,
                        is_primary=a.is_primary or True,
                    )
                    self.sensei_session.add(bank_account)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Bank Account: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_diplomas(self, result: ImportResult) -> None:
        """Import employee diplomas into HREmployeeDiploma model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            diplomas = (await starz_session.execute(select(StarzEmployeeDiploma))).scalars().all()
            result.total_source = len(diplomas)
            
            for d in diplomas:
                try:
                    employee_id = self._get_cached_id("employee", d.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    diploma = HREmployeeDiploma(
                        employee_id=employee_id,
                        diploma_type=d.type or "degree",
                        name=d.name,
                        institution=d.institution,
                        graduation_date=d.obtained_date,
                        field_of_study=d.field,
                    )
                    self.sensei_session.add(diploma)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Diploma: {e}")
            
            await self.sensei_session.commit()

    
    async def _import_employee_leaves(self, result: ImportResult) -> None:
        """Import employee leave requests."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            leaves = (await starz_session.execute(select(StarzEmployeeLeave))).scalars().all()
            result.total_source = len(leaves)
            
            for l in leaves:
                try:
                    employee_id = self._get_cached_id("employee", l.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    leave = LeaveRequest(
                        employee_id=employee_id,
                        leave_type=l.leave_type,
                        start_date=l.start_at,
                        end_date=l.end_at,
                        status=l.status,
                        notes=l.notes,
                    )
                    self.sensei_session.add(leave)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Leave: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_leave_balances(self, result: ImportResult) -> None:
        """Import employee leave balances into HRLeaveBalance model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            balances = (await starz_session.execute(select(StarzEmployeeLeaveAnnual))).scalars().all()
            result.total_source = len(balances)
            
            for b in balances:
                try:
                    employee_id = self._get_cached_id("employee", b.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    balance = HRLeaveBalance(
                        employee_id=employee_id,
                        leave_type=b.leave_type or "annual",
                        year=b.year,
                        entitled_days=Decimal(str(b.entitled)) if b.entitled else Decimal("0"),
                        used_days=Decimal(str(b.used)) if b.used else Decimal("0"),
                        remaining_days=Decimal(str(b.remaining)) if b.remaining else Decimal("0"),
                        carried_forward=Decimal(str(b.carried_forward)) if b.carried_forward else Decimal("0"),
                    )
                    self.sensei_session.add(balance)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Leave Balance: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_clocking(self, result: ImportResult) -> None:
        """Import time clock entries into HRTimeClockEvent model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            clockings = (await starz_session.execute(select(StarzEmployeeClocking))).scalars().all()
            result.total_source = len(clockings)
            
            for c in clockings:
                try:
                    employee_id = self._get_cached_id("employee", c.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    # Create clock-in event
                    if c.clock_in:
                        clock_in = HRTimeClockEvent(
                            employee_id=employee_id,
                            event_type="clock_in",
                            timestamp=datetime.combine(c.clock_date, c.clock_in) if c.clock_date and c.clock_in else datetime.now(),
                            source="legacy_import",
                            notes=c.notes,
                        )
                        self.sensei_session.add(clock_in)
                    
                    # Create clock-out event
                    if c.clock_out:
                        clock_out = HRTimeClockEvent(
                            employee_id=employee_id,
                            event_type="clock_out",
                            timestamp=datetime.combine(c.clock_date, c.clock_out) if c.clock_date and c.clock_out else datetime.now(),
                            source="legacy_import",
                        )
                        self.sensei_session.add(clock_out)
                    
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Clocking: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_absences(self, result: ImportResult) -> None:
        """Import employee absences into HREmployeeAbsence model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            absences = (await starz_session.execute(select(StarzEmployeeAbsence))).scalars().all()
            result.total_source = len(absences)
            
            for a in absences:
                try:
                    employee_id = self._get_cached_id("employee", a.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    absence = HREmployeeAbsence(
                        employee_id=employee_id,
                        absence_type=a.type or "unexcused",
                        start_date=a.start_date,
                        end_date=a.end_date,
                        reason=a.reason,
                        status=a.status or "recorded",
                    )
                    self.sensei_session.add(absence)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Absence: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_salary(self, result: ImportResult) -> None:
        """Import employee salary records into HREmployeeSalary model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            salaries = (await starz_session.execute(select(StarzEmployeeSalary))).scalars().all()
            result.total_source = len(salaries)
            
            for s in salaries:
                try:
                    employee_id = self._get_cached_id("employee", s.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    salary = HREmployeeSalary(
                        employee_id=employee_id,
                        effective_date=s.effective_date,
                        base_salary=Decimal(str(s.base_salary)) if s.base_salary else Decimal("0"),
                        currency=s.currency or "MAD",
                        pay_frequency=s.pay_frequency or "monthly",
                    )
                    self.sensei_session.add(salary)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Salary: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_advances(self, result: ImportResult) -> None:
        """Import employee advances into HREmployeeAdvance model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            advances = (await starz_session.execute(select(StarzEmployeeAdvance))).scalars().all()
            result.total_source = len(advances)
            
            for a in advances:
                try:
                    employee_id = self._get_cached_id("employee", a.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    advance = HREmployeeAdvance(
                        employee_id=employee_id,
                        request_date=a.request_date,
                        amount=Decimal(str(a.amount)) if a.amount else Decimal("0"),
                        currency=a.currency or "MAD",
                        status=a.status or "pending",
                        reason=a.reason,
                        repayment_start_date=a.repayment_start,
                        repayment_amount=Decimal(str(a.repayment_amount)) if a.repayment_amount else None,
                    )
                    self.sensei_session.add(advance)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Advance: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_suspensions(self, result: ImportResult) -> None:
        """Import employee suspensions into HREmployeeSuspension model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            suspensions = (await starz_session.execute(select(StarzEmployeeSuspension))).scalars().all()
            result.total_source = len(suspensions)
            
            for s in suspensions:
                try:
                    employee_id = self._get_cached_id("employee", s.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    suspension = HREmployeeSuspension(
                        employee_id=employee_id,
                        suspension_type=s.type or "disciplinary",
                        start_date=s.start_date,
                        end_date=s.end_date,
                        reason=s.reason,
                        status=s.status or "active",
                    )
                    self.sensei_session.add(suspension)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Suspension: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_permissions(self, result: ImportResult) -> None:
        """Import employee permissions into HREmployeePermission model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            permissions = (await starz_session.execute(select(StarzEmployeePermission))).scalars().all()
            result.total_source = len(permissions)
            
            for p in permissions:
                try:
                    employee_id = self._get_cached_id("employee", p.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    permission = HREmployeePermission(
                        employee_id=employee_id,
                        permission_type=p.type or "general",
                        permission_date=p.date,
                        start_time=p.start_time,
                        end_time=p.end_time,
                        duration_hours=Decimal(str(p.duration)) if p.duration else None,
                        reason=p.reason,
                        status=p.status or "approved",
                    )
                    self.sensei_session.add(permission)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Permission: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_training(self, result: ImportResult) -> None:
        """Import employee training enrollments using TrainingParticipant."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            trainings = (await starz_session.execute(select(StarzEmployeeTraining))).scalars().all()
            result.total_source = len(trainings)
            
            for t in trainings:
                try:
                    employee_id = self._get_cached_id("employee", t.employee_id)
                    program_id = self._get_cached_id("training_program", t.training_program_id)
                    
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    # Check if training/program exists in Sensei
                    if program_id:
                        existing = await self.sensei_session.scalar(
                            select(TrainingParticipant).where(
                                TrainingParticipant.employee_id == employee_id,
                                TrainingParticipant.training_id == program_id
                            )
                        )
                        
                        if existing:
                            if self.on_conflict == "update":
                                existing.status = t.status or "enrolled"
                                result.updated += 1
                            else:
                                result.skipped += 1
                            continue
                        
                        participant = TrainingParticipant(
                            employee_id=employee_id,
                            training_id=program_id,
                            status=t.status or "enrolled",
                            enrolled_date=t.start_date,
                            completion_date=t.end_date,
                        )
                        self.sensei_session.add(participant)
                        result.imported += 1
                    else:
                        # Store as employee extended data if no matching program
                        employee = await self.sensei_session.get(Employee, employee_id)
                        if employee:
                            if not hasattr(employee, 'extended_data') or employee.extended_data is None:
                                employee.extended_data = {}
                            training_list = employee.extended_data.get('trainings', [])
                            training_list.append({
                                'program_id': t.training_program_id,
                                'start_date': t.start_date.isoformat() if t.start_date else None,
                                'end_date': t.end_date.isoformat() if t.end_date else None,
                                'status': t.status,
                                'score': float(t.score) if t.score else None,
                            })
                            employee.extended_data['trainings'] = training_list
                            result.imported += 1
                        else:
                            result.skipped += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"EmployeeTraining: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_documents(self, result: ImportResult) -> None:
        """Import employee documents into HREmployeeDocument model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            documents = (await starz_session.execute(select(StarzEmployeeDocument))).scalars().all()
            result.total_source = len(documents)
            
            for d in documents:
                try:
                    employee_id = self._get_cached_id("employee", d.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    document = HREmployeeDocument(
                        employee_id=employee_id,
                        document_type=d.type or "other",
                        title=d.title or d.filename,
                        file_name=d.filename,
                        file_path=d.file_path,
                        upload_date=d.uploaded_at,
                        expiry_date=d.expires_at,
                    )
                    self.sensei_session.add(document)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Document: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_history(self, result: ImportResult) -> None:
        """Import employee history into HREmployeeHistory model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            history = (await starz_session.execute(select(StarzEmployeeHistory))).scalars().all()
            result.total_source = len(history)
            
            for h in history:
                try:
                    employee_id = self._get_cached_id("employee", h.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    hist = HREmployeeHistory(
                        employee_id=employee_id,
                        event_type=h.event_type or "status_change",
                        event_date=h.event_date,
                        description=h.description,
                        old_value=h.old_value,
                        new_value=h.new_value,
                    )
                    self.sensei_session.add(hist)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"History: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_employee_notes(self, result: ImportResult) -> None:
        """Import employee notes into HREmployeeNote model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            notes = (await starz_session.execute(select(StarzEmployeeNote))).scalars().all()
            result.total_source = len(notes)
            
            for n in notes:
                try:
                    employee_id = self._get_cached_id("employee", n.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    note = HREmployeeNote(
                        employee_id=employee_id,
                        note_type=n.type or "general",
                        content=n.content,
                        is_confidential=n.is_confidential or False,
                    )
                    self.sensei_session.add(note)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Note: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_shift_schedules(self, result: ImportResult) -> None:
        """Import shift schedules - stored in employee extended_data."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            schedules = (await starz_session.execute(select(StarzShiftSchedule))).scalars().all()
            result.total_source = len(schedules)
            
            for s in schedules:
                try:
                    employee_id = self._get_cached_id("employee", s.employee_id)
                    if not employee_id:
                        result.skipped += 1
                        continue
                    
                    # Store schedules in employee extended_data (no separate model)
                    employee = await self.sensei_session.get(Employee, employee_id)
                    if employee:
                        if employee.extended_data is None:
                            employee.extended_data = {}
                        schedules_list = employee.extended_data.get('schedules', [])
                        schedules_list.append({
                            'schedule_date': s.date.isoformat() if s.date else None,
                            'shift_type': s.shift_type,
                            'start_time': s.start_time.isoformat() if s.start_time else None,
                            'end_time': s.end_time.isoformat() if s.end_time else None,
                        })
                        employee.extended_data['schedules'] = schedules_list
                        result.imported += 1
                    else:
                        result.skipped += 1
                        
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Schedule: {e}")
            
            await self.sensei_session.commit()
    
    # =========================================================================
    # Inventory Transaction Importers
    # =========================================================================
    
    async def _import_license_plates(self, result: ImportResult) -> None:
        """Import license plate numbers (LPNs)."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            lpns = (await starz_session.execute(select(StarzLicensePlate))).scalars().all()
            result.total_source = len(lpns)
            
            for l in lpns:
                try:
                    warehouse_id = self._get_cached_id("warehouse", l.warehouse_id)
                    location_id = self._get_cached_id("location", l.location_id)
                    
                    existing = await self.sensei_session.scalar(
                        select(LicensePlate).where(LicensePlate.code == l.code)
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("lpn", l.id, existing.id)
                        continue
                    
                    lpn = LicensePlate(
                        code=l.code,
                        warehouse_id=warehouse_id,
                        location_id=location_id,
                        status=l.status,
                        item_sku=l.item_sku,
                        quantity=l.quantity,
                        uom=l.uom,
                        lot_number=l.lot_number,
                        serial_number=l.serial_number,
                        expiry_date=l.expiry_date,
                    )
                    self.sensei_session.add(lpn)
                    await self.sensei_session.flush()
                    self._cache_id("lpn", l.id, lpn.id)
                    result.imported += 1
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"LPN {l.code}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_wms_transactions(self, result: ImportResult) -> None:
        """Import WMS transactions as StockMove records."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            txns = (await starz_session.execute(select(StarzWmsTransaction))).scalars().all()
            result.total_source = len(txns)

            for t in txns:
                try:
                    # Resolve FKs
                    product_id = self._get_cached_id("article", None)  # look up by item_sku
                    # Try to find product by SKU
                    if t.item_sku:
                        prod = await self.sensei_session.scalar(
                            select(Product).where(Product.part_number == t.item_sku)
                        )
                        if prod:
                            product_id = prod.id

                    if not product_id:
                        result.skipped += 1
                        continue

                    from_loc = self._get_cached_id("location", t.from_location_id)
                    to_loc = self._get_cached_id("location", t.to_location_id)

                    if not from_loc or not to_loc:
                        result.skipped += 1
                        continue

                    move = StockMove(
                        product_id=product_id,
                        source_location_id=from_loc,
                        destination_location_id=to_loc,
                        quantity=Decimal(str(t.quantity)),
                        status="done",
                        reference=f"STARZ-WMS-{t.id}",
                        lpn_id=self._get_cached_id("lpn", t.lpn_id),
                    )
                    self.sensei_session.add(move)
                    await self.sensei_session.flush()
                    self._cache_id("wms_txn", t.id, move.id)
                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"WMS Txn {t.id}: {e}")

            await self.sensei_session.commit()

    async def _import_inventory_counts(self, result: ImportResult) -> None:
        """Import inventory counts, updating InventoryLevel records."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            counts = (await starz_session.execute(select(StarzInventoryCount))).scalars().all()
            result.total_source = len(counts)

            for c in counts:
                try:
                    # Resolve product by SKU
                    product_id = None
                    if c.item_sku:
                        prod = await self.sensei_session.scalar(
                            select(Product).where(Product.part_number == c.item_sku)
                        )
                        if prod:
                            product_id = prod.id

                    if not product_id:
                        result.skipped += 1
                        continue

                    location_id = self._get_cached_id("location", c.location_id)
                    if not location_id:
                        # Fall back to warehouse default location
                        wh_id = self._get_cached_id("warehouse", c.warehouse_id)
                        if wh_id:
                            loc = await self.sensei_session.scalar(
                                select(StockLocation).where(StockLocation.warehouse_id == wh_id).limit(1)
                            )
                            if loc:
                                location_id = loc.id

                    if not location_id:
                        result.skipped += 1
                        continue

                    # Upsert inventory level
                    existing = await self.sensei_session.scalar(
                        select(InventoryLevel).where(
                            InventoryLevel.product_id == product_id,
                            InventoryLevel.location_id == location_id,
                        )
                    )

                    if existing:
                        if c.counted_quantity is not None:
                            existing.quantity_on_hand = Decimal(str(c.counted_quantity))
                            existing.last_counted_at = c.counted_date or c.scheduled_date
                        result.updated += 1
                    else:
                        level = InventoryLevel(
                            product_id=product_id,
                            location_id=location_id,
                            quantity_on_hand=Decimal(str(c.counted_quantity or c.system_quantity or 0)),
                            last_counted_at=c.counted_date or c.scheduled_date,
                        )
                        self.sensei_session.add(level)
                        result.imported += 1

                    await self.sensei_session.flush()

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"InvCount {c.id}: {e}")

            await self.sensei_session.commit()
    
    # =========================================================================
    # Purchasing Importers
    # =========================================================================
    
    async def _import_price_requests(self, result: ImportResult) -> None:
        """Import supplier price requests as PurchaseRequisitions."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            reqs = (await starz_session.execute(select(StarzSupplierPriceRequest))).scalars().all()
            result.total_source = len(reqs)

            for r in reqs:
                try:
                    pr_number = f"PR-{r.reference}"
                    existing = await self.sensei_session.scalar(
                        select(PurchaseRequisition).where(PurchaseRequisition.pr_number == pr_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("price_request", r.id, existing.id)
                        continue

                    supplier_id = self._get_cached_id("supplier", r.supplier_id)
                    pr = PurchaseRequisition(
                        pr_number=pr_number,
                        requested_by_id=None,  # Legacy import — no user mapping
                        supplier_id=supplier_id,
                        currency="MAD",
                        status=r.status or "draft",
                    )
                    self.sensei_session.add(pr)
                    await self.sensei_session.flush()
                    self._cache_id("price_request", r.id, pr.id)
                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"PriceReq {r.reference}: {e}")

            await self.sensei_session.commit()
    
    async def _import_purchase_orders(self, result: ImportResult) -> None:
        """Import purchase orders."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            pos = (await starz_session.execute(select(StarzPurchaseOrder))).scalars().all()
            result.total_source = len(pos)
            
            for p in pos:
                try:
                    supplier_id = self._get_cached_id("supplier", p.supplier_id)
                    
                    existing = await self.sensei_session.scalar(
                        select(PurchaseOrder).where(PurchaseOrder.po_number == p.po_number)
                    )
                    
                    if existing:
                        result.skipped += 1
                        self._cache_id("po", p.id, existing.id)
                        continue
                    
                    po = PurchaseOrder(
                        po_number=p.po_number,
                        supplier_id=supplier_id,
                        order_date=p.order_date,
                        expected_date=p.expected_date,
                        status=p.status,
                        total_amount=Decimal(str(p.total_amount)),
                        currency=p.currency,
                        notes=p.notes,
                    )
                    self.sensei_session.add(po)
                    await self.sensei_session.flush()
                    self._cache_id("po", p.id, po.id)
                    result.imported += 1
                    
                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzPurchaseOrderItem).where(
                            StarzPurchaseOrderItem.po_id == p.id
                        )
                    )).scalars().all()
                    
                    for item in items:
                        article_id = self._get_cached_id("article", item.article_id)
                        line = PurchaseOrderLine(
                            po_id=po.id,
                            product_id=article_id,
                            quantity=item.quantity,
                            unit_price=Decimal(str(item.unit_price)),
                            tax_rate=Decimal(str(item.tax_rate)),
                            total_price=Decimal(str(item.total_price)),
                        )
                        self.sensei_session.add(line)
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"PO {p.po_number}: {e}")
            
            await self.sensei_session.commit()
    
    async def _import_po_receipts(self, result: ImportResult) -> None:
        """Import PO receipts as GoodsReceipt + ReceiptLine records."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            receipts = (await starz_session.execute(select(StarzPOReceipt))).scalars().all()
            result.total_source = len(receipts)

            for r in receipts:
                try:
                    po_id = self._get_cached_id("po", r.po_id)
                    if not po_id:
                        result.skipped += 1
                        continue

                    existing = await self.sensei_session.scalar(
                        select(GoodsReceipt).where(GoodsReceipt.reference == r.receipt_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("po_receipt", r.id, existing.id)
                        continue

                    receipt = GoodsReceipt(
                        po_id=po_id,
                        received_at=datetime.combine(r.receipt_date, datetime.min.time()) if r.receipt_date else datetime.utcnow(),
                        received_by_id=None,  # Legacy import
                        reference=r.receipt_number,
                    )
                    self.sensei_session.add(receipt)
                    await self.sensei_session.flush()
                    self._cache_id("po_receipt", r.id, receipt.id)

                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzPOReceiptItem).where(StarzPOReceiptItem.receipt_id == r.id)
                    )).scalars().all()

                    for item in items:
                        article_id = self._get_cached_id("article", item.article_id)
                        # Resolve SKU from product if available
                        sku = f"STARZ-{item.article_id}"
                        if article_id:
                            prod = await self.sensei_session.scalar(
                                select(Product).where(Product.id == article_id)
                            )
                            if prod:
                                sku = prod.part_number

                        line = ReceiptLine(
                            receipt_id=receipt.id,
                            sku=sku,
                            quantity_received=Decimal(str(item.quantity)),
                        )
                        self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"POReceipt {r.receipt_number}: {e}")

            await self.sensei_session.commit()

    async def _import_consumable_requests(self, result: ImportResult) -> None:
        """Import consumable requests as PurchaseRequisitions with PRLines."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            reqs = (await starz_session.execute(select(StarzConsumableRequest))).scalars().all()
            result.total_source = len(reqs)

            for r in reqs:
                try:
                    pr_number = f"CR-{r.request_number}"
                    existing = await self.sensei_session.scalar(
                        select(PurchaseRequisition).where(PurchaseRequisition.pr_number == pr_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("consumable_req", r.id, existing.id)
                        continue

                    pr = PurchaseRequisition(
                        pr_number=pr_number,
                        requested_by_id=None,  # Legacy import
                        currency="MAD",
                        status=r.status or "draft",
                        cost_center=r.department,
                    )
                    self.sensei_session.add(pr)
                    await self.sensei_session.flush()
                    self._cache_id("consumable_req", r.id, pr.id)

                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzConsumableRequestItem).where(
                            StarzConsumableRequestItem.request_id == r.id
                        )
                    )).scalars().all()

                    for item in items:
                        sku = f"STARZ-{item.article_id}" if item.article_id else "MISC"
                        if item.article_id:
                            article_id = self._get_cached_id("article", item.article_id)
                            if article_id:
                                prod = await self.sensei_session.scalar(
                                    select(Product).where(Product.id == article_id)
                                )
                                if prod:
                                    sku = prod.part_number

                        line = PRLine(
                            pr_id=pr.id,
                            sku=sku,
                            description=item.description or sku,
                            quantity=Decimal(str(item.quantity)),
                            unit_price=Decimal(str(item.estimated_price or 0)),
                        )
                        self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"ConsumableReq {r.request_number}: {e}")

            await self.sensei_session.commit()

    async def _import_supplier_invoices(self, result: ImportResult) -> None:
        """Import supplier invoices into SupplierInvoice model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            invoices = (await starz_session.execute(select(StarzSupplierInvoice))).scalars().all()
            result.total_source = len(invoices)

            for inv in invoices:
                try:
                    existing = await self.sensei_session.scalar(
                        select(SupplierInvoice).where(
                            SupplierInvoice.supplier_invoice_number == inv.invoice_number
                        )
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("supplier_invoice", inv.id, existing.id)
                        continue

                    supplier_id = self._get_cached_id("supplier", inv.supplier_id)
                    if not supplier_id:
                        result.skipped += 1
                        continue

                    po_id = self._get_cached_id("po", inv.po_id) if inv.po_id else None

                    # Map status
                    status_map = {"pending": "draft", "approved": "approved", "paid": "paid"}
                    status = status_map.get(inv.status, "draft")

                    si = SupplierInvoice(
                        supplier_invoice_number=inv.invoice_number,
                        supplier_id=supplier_id,
                        invoice_date=inv.invoice_date,
                        due_date=inv.due_date,
                        currency=inv.currency or "MAD",
                        status=status,
                        po_id=po_id,
                        memo=inv.notes,
                        paid_at=datetime.combine(inv.paid_at, datetime.min.time()) if inv.paid_at else None,
                    )
                    self.sensei_session.add(si)
                    await self.sensei_session.flush()
                    self._cache_id("supplier_invoice", inv.id, si.id)

                    # Create a single summary line item
                    line = SupplierInvoiceLine(
                        invoice_id=si.id,
                        sku="LEGACY-TOTAL",
                        description=f"Legacy invoice total — {inv.invoice_number}",
                        quantity=Decimal("1"),
                        unit_price=Decimal(str(inv.total_amount or 0)),
                    )
                    self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"SupplierInv {inv.invoice_number}: {e}")

            await self.sensei_session.commit()
    
    # =========================================================================
    # Sales Importers
    # =========================================================================
    
    async def _import_quotations(self, result: ImportResult) -> None:
        """Import quotations as SalesOrders with SalesOrderLines."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            quotes = (await starz_session.execute(select(StarzQuotation))).scalars().all()
            result.total_source = len(quotes)

            for q in quotes:
                try:
                    so_number = f"SO-{q.quote_number}"
                    existing = await self.sensei_session.scalar(
                        select(SalesOrder).where(SalesOrder.so_number == so_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("quotation", q.id, existing.id)
                        continue

                    account_id = self._get_cached_id("customer", q.customer_id)
                    if not account_id:
                        result.skipped += 1
                        continue

                    # Map status
                    status_map = {"draft": "draft", "sent": "draft", "accepted": "approved", "rejected": "cancelled"}
                    status = status_map.get(q.status, "draft")

                    so = SalesOrder(
                        so_number=so_number,
                        account_id=account_id,
                        currency=q.currency or "MAD",
                        status=status,
                    )
                    self.sensei_session.add(so)
                    await self.sensei_session.flush()
                    self._cache_id("quotation", q.id, so.id)

                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzQuotationItem).where(StarzQuotationItem.quotation_id == q.id)
                    )).scalars().all()

                    for item in items:
                        sku = f"STARZ-{item.article_id}" if item.article_id else "MISC"
                        if item.article_id:
                            article_id = self._get_cached_id("article", item.article_id)
                            if article_id:
                                prod = await self.sensei_session.scalar(
                                    select(Product).where(Product.id == article_id)
                                )
                                if prod:
                                    sku = prod.part_number

                        line = SalesOrderLine(
                            so_id=so.id,
                            sku=sku,
                            description=item.description or sku,
                            quantity=Decimal(str(item.quantity)),
                            unit_price=Decimal(str(item.unit_price)),
                        )
                        self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Quotation {q.quote_number}: {e}")

            await self.sensei_session.commit()

    async def _import_customer_invoices(self, result: ImportResult) -> None:
        """Import customer invoices into CustomerInvoice model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            invoices = (await starz_session.execute(select(StarzCustomerInvoice))).scalars().all()
            result.total_source = len(invoices)

            for inv in invoices:
                try:
                    existing = await self.sensei_session.scalar(
                        select(CustomerInvoice).where(
                            CustomerInvoice.invoice_number == inv.invoice_number
                        )
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("customer_invoice", inv.id, existing.id)
                        continue

                    account_id = self._get_cached_id("customer", inv.customer_id)
                    if not account_id:
                        result.skipped += 1
                        continue

                    # Map status
                    status_map = {"draft": "draft", "sent": "issued", "paid": "paid", "overdue": "overdue"}
                    status = status_map.get(inv.status, "issued")

                    ci = CustomerInvoice(
                        invoice_number=inv.invoice_number,
                        account_id=account_id,
                        currency=inv.currency or "MAD",
                        issued_at=datetime.combine(inv.invoice_date, datetime.min.time()),
                        due_date=inv.due_date,
                        status=status,
                        memo=inv.notes,
                    )
                    self.sensei_session.add(ci)
                    await self.sensei_session.flush()
                    self._cache_id("customer_invoice", inv.id, ci.id)

                    # Create a single summary line item
                    line = CustomerInvoiceLine(
                        invoice_id=ci.id,
                        sku="LEGACY-TOTAL",
                        description=f"Legacy invoice total — {inv.invoice_number}",
                        quantity=Decimal("1"),
                        unit_price=Decimal(str(inv.total_amount or 0)),
                    )
                    self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"CustInv {inv.invoice_number}: {e}")

            await self.sensei_session.commit()
    
    # =========================================================================
    # Shipping Importers
    # =========================================================================
    
    async def _import_shipments(self, result: ImportResult) -> None:
        """Import shipments into Shipment + ShipmentLine models."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            shipments = (await starz_session.execute(select(StarzShipment))).scalars().all()
            result.total_source = len(shipments)

            for s in shipments:
                try:
                    existing = await self.sensei_session.scalar(
                        select(Shipment).where(Shipment.shipment_number == s.shipment_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("shipment", s.id, existing.id)
                        continue

                    account_id = self._get_cached_id("customer", s.customer_id)
                    if not account_id:
                        result.skipped += 1
                        continue

                    warehouse_id = self._get_cached_id("warehouse", s.warehouse_id) if s.warehouse_id else None

                    shipment = Shipment(
                        shipment_number=s.shipment_number,
                        account_id=account_id,
                        ship_from_warehouse_id=warehouse_id,
                        ship_date=s.ship_date,
                        carrier=s.carrier,
                        tracking_number=s.tracking_number,
                        ship_to_name=s.ship_to_address or "N/A",
                        ship_to_address=s.ship_to_address or "N/A",
                        status=s.status or "pending",
                        notes=s.notes,
                        legacy_id=str(s.id),
                    )
                    self.sensei_session.add(shipment)
                    await self.sensei_session.flush()
                    self._cache_id("shipment", s.id, shipment.id)

                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzShipmentItem).where(StarzShipmentItem.shipment_id == s.id)
                    )).scalars().all()

                    for item in items:
                        article_id = self._get_cached_id("article", item.article_id)
                        sku = f"STARZ-{item.article_id}"
                        if article_id:
                            prod = await self.sensei_session.scalar(
                                select(Product).where(Product.id == article_id)
                            )
                            if prod:
                                sku = prod.part_number

                        line = ShipmentLine(
                            shipment_id=shipment.id,
                            sku=sku,
                            quantity_shipped=Decimal(str(item.quantity)),
                            lot_number=item.lot_number,
                            legacy_id=str(item.id),
                        )
                        self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Shipment {s.shipment_number}: {e}")

            await self.sensei_session.commit()

    async def _import_pick_lists(self, result: ImportResult) -> None:
        """Import pick lists into PickList + PickListLine models."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            picks = (await starz_session.execute(select(StarzPickList))).scalars().all()
            result.total_source = len(picks)

            for p in picks:
                try:
                    existing = await self.sensei_session.scalar(
                        select(PickList).where(PickList.pick_number == p.pick_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("pick_list", p.id, existing.id)
                        continue

                    warehouse_id = self._get_cached_id("warehouse", p.warehouse_id)
                    if not warehouse_id:
                        result.skipped += 1
                        continue

                    shipment_id = self._get_cached_id("shipment", p.shipment_id) if p.shipment_id else None

                    pick = PickList(
                        pick_number=p.pick_number,
                        warehouse_id=warehouse_id,
                        source_type="shipment" if shipment_id else "manual",
                        source_id=shipment_id or uuid4(),
                        status=p.status or "pending",
                        started_at=p.started_at,
                        completed_at=p.completed_at,
                        legacy_id=str(p.id),
                    )
                    self.sensei_session.add(pick)
                    await self.sensei_session.flush()
                    self._cache_id("pick_list", p.id, pick.id)

                    # Import line items
                    items = (await starz_session.execute(
                        select(StarzPickListItem).where(StarzPickListItem.pick_list_id == p.id)
                    )).scalars().all()

                    for item in items:
                        article_id = self._get_cached_id("article", item.article_id)
                        sku = f"STARZ-{item.article_id}"
                        if article_id:
                            prod = await self.sensei_session.scalar(
                                select(Product).where(Product.id == article_id)
                            )
                            if prod:
                                sku = prod.part_number

                        from_loc = self._get_cached_id("location", item.from_location_id)
                        if not from_loc:
                            continue  # Skip line — no location

                        line = PickListLine(
                            pick_list_id=pick.id,
                            sku=sku,
                            source_location_id=from_loc,
                            quantity_requested=Decimal(str(item.quantity)),
                            quantity_picked=Decimal(str(item.picked_qty or 0)),
                            picked_at=item.picked_at,
                            status="picked" if item.picked_qty and item.picked_qty >= item.quantity else "pending",
                            legacy_id=str(item.id),
                        )
                        self.sensei_session.add(line)

                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"PickList {p.pick_number}: {e}")

            await self.sensei_session.commit()
    
    # =========================================================================
    # Finance Importers
    # =========================================================================
    
    async def _import_payments(self, result: ImportResult) -> None:
        """Import payments — outgoing → Payment (AP), incoming → PaymentReceipt (AR)."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            payments = (await starz_session.execute(select(StarzPayment))).scalars().all()
            result.total_source = len(payments)

            for p in payments:
                try:
                    is_incoming = (p.payment_type or "").lower() in ("incoming", "receipt", "customer")

                    if is_incoming:
                        # Import as PaymentReceipt (Accounts Receivable)
                        account_id = self._get_cached_id("customer", p.customer_id) if p.customer_id else None
                        if not account_id:
                            result.skipped += 1
                            continue

                        existing = await self.sensei_session.scalar(
                            select(PaymentReceipt).where(PaymentReceipt.reference == p.payment_number)
                        )
                        if existing:
                            result.skipped += 1
                            continue

                        receipt = PaymentReceipt(
                            account_id=account_id,
                            received_at=datetime.combine(p.payment_date, datetime.min.time()),
                            received_by_id=None,  # Legacy import
                            currency=p.currency or "MAD",
                            amount=Decimal(str(p.amount)),
                            reference=p.payment_number,
                            notes=p.notes,
                        )
                        self.sensei_session.add(receipt)
                        result.imported += 1
                    else:
                        # Import as Payment (Accounts Payable)
                        supplier_id = self._get_cached_id("supplier", p.supplier_id) if p.supplier_id else None
                        if not supplier_id:
                            result.skipped += 1
                            continue

                        existing = await self.sensei_session.scalar(
                            select(Payment).where(Payment.reference == p.payment_number)
                        )
                        if existing:
                            result.skipped += 1
                            continue

                        payment = Payment(
                            payment_run_id=None,  # Legacy import — no payment run
                            supplier_id=supplier_id,
                            amount=Decimal(str(p.amount)),
                            currency=p.currency or "MAD",
                            executed_at=datetime.combine(p.payment_date, datetime.min.time()),
                            reference=p.payment_number,
                        )
                        self.sensei_session.add(payment)
                        result.imported += 1

                    await self.sensei_session.flush()

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Payment {p.payment_number}: {e}")

            await self.sensei_session.commit()

    async def _import_bank_transactions(self, result: ImportResult) -> None:
        """Import bank transactions into BankTransaction model."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            txns = (await starz_session.execute(select(StarzBankTransaction))).scalars().all()
            result.total_source = len(txns)

            for t in txns:
                try:
                    bank_account_id = self._get_cached_id("bank_account", t.account_id)
                    if not bank_account_id:
                        result.skipped += 1
                        continue

                    legacy_id = f"STARZ-BT-{t.id}"
                    existing = await self.sensei_session.scalar(
                        select(BankTransaction).where(BankTransaction.legacy_id == legacy_id)
                    )
                    if existing:
                        result.skipped += 1
                        continue

                    bt = BankTransaction(
                        bank_account_id=bank_account_id,
                        transaction_date=t.transaction_date,
                        transaction_type=t.transaction_type or "transfer",
                        reference=t.reference,
                        description=t.description or f"Legacy transaction {t.id}",
                        amount=Decimal(str(t.amount)),
                        currency="MAD",
                        status="reconciled" if t.reconciled else "posted",
                        reconciled_at=t.reconciled_at,
                        legacy_id=legacy_id,
                    )
                    self.sensei_session.add(bt)
                    await self.sensei_session.flush()
                    self._cache_id("bank_txn", t.id, bt.id)
                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"BankTxn {t.id}: {e}")

            await self.sensei_session.commit()
    
    # =========================================================================
    # Quality Importers
    # =========================================================================
    
    async def _import_scrap_records(self, result: ImportResult) -> None:
        """Import scrap records as NonConformance records."""
        starz_factory = await self._get_starz_session()
        async with starz_factory() as starz_session:
            scraps = (await starz_session.execute(select(StarzScrapRecord))).scalars().all()
            result.total_source = len(scraps)

            for s in scraps:
                try:
                    nc_number = f"NC-SCRAP-{s.id}"
                    existing = await self.sensei_session.scalar(
                        select(NonConformance).where(NonConformance.nc_number == nc_number)
                    )
                    if existing:
                        result.skipped += 1
                        self._cache_id("scrap", s.id, existing.id)
                        continue

                    product_id = self._get_cached_id("article", s.article_id) if s.article_id else None

                    nc = NonConformance(
                        nc_number=nc_number,
                        nc_type="process",       # Scrap is a process NC
                        source="production",     # Scrap originates from production
                        severity="minor",
                        product_id=product_id,
                        quantity_affected=int(s.quantity) if s.quantity else 1,
                        title=f"Scrap — {s.reason_code or 'Unknown'}",
                        description=s.reason_description or s.notes or f"Legacy scrap record #{s.id}",
                        detected_by_id=None,     # Legacy import — no user mapping
                        detected_at=datetime.combine(s.scrap_date, datetime.min.time()) if s.scrap_date else datetime.utcnow(),
                        status="closed",         # Historical records are closed
                        disposition="scrap",
                        disposition_notes=s.notes,
                    )
                    self.sensei_session.add(nc)
                    await self.sensei_session.flush()
                    self._cache_id("scrap", s.id, nc.id)
                    result.imported += 1

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Scrap {s.id}: {e}")

            await self.sensei_session.commit()
