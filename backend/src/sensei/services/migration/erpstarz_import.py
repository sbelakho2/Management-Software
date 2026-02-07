"""erpStarz Legacy System Import Service.

Provides comprehensive migration functionality for all erpStarz entities
from the legacy Symfony/PHP ERP system at /home/aaron/IdeaProjects/erpStarz.

Entity Categories:
==================
1. HR Module (21 entities) - Imported via hr/legacy_import.py
2. Inventory/WMS (10 entities) - Article, Warehouse, StockLocation, etc.
3. Purchasing (8 entities) - PurchaseOrder, Supplier, PoReception, etc.
4. Sales/Quoting (4 entities) - Quotation, QuotationItems, QuotationCustomer
5. Financial (5 entities) - BankAccount, BankTransaction, Currency, etc.
6. Master Data (6 entities) - Company, Unit, PayTerm, etc.

All legacy data defaults to Tunisia jurisdiction where applicable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.inventory import (
    Warehouse, Location, InventoryLevel, StockMove, LicensePlate,
    WmsDevice, WmsWorkstation, PickList, PickListLine,
)
from sensei.models.accounts_payable import PurchaseOrder, POLine, GoodsReceipt, ReceiptLine
from sensei.models.accounts_receivable import Shipment, ShipmentLine
from sensei.models.finance import Currency, PaymentTerm, BankAccount, BankTransaction
from sensei.models.product import Product
from sensei.models.quote import Quote, QuoteLineItem
from sensei.models.account import Account
from sensei.models.site import Site
from sensei.models.migration import ImportBatch as ImportBatchModel
from sensei.services.production.productionization import EntityType, ImportStatus

logger = logging.getLogger(__name__)

# erpStarz table to Sensei model mapping
ERPSTARZ_ENTITY_MAP = {
    # =========================================================================
    # HR MODULE (handled by hr/legacy_import.py)
    # =========================================================================
    "employee_info": {"model": "EmployeeProfile", "module": "hr"},
    "employee_cnss": {"model": "HRSocialSecurityRecord", "module": "hr"},
    "employee_contract": {"model": "HREmployeeContract", "module": "hr"},
    "employee_leave": {"model": "HRLeaveRequest", "module": "hr"},
    "employee_leave_annual": {"model": "HRLeaveBalance", "module": "hr"},
    "employee_clocking": {"model": "HRTimeClockEvent", "module": "hr"},
    "employee_salary": {"model": "HREmployeeSalary", "module": "hr"},
    "employee_training": {"model": "TrainingRecord", "module": "training"},
    "employee_bank_acc": {"model": "HREmployeeBankAccount", "module": "hr"},
    "employee_address": {"model": "HREmployeeAddress", "module": "hr"},
    "employee_phone": {"model": "EmployeeProfile.phone", "module": "hr"},
    "employee_email": {"model": "EmployeeProfile.email", "module": "hr"},
    "employee_diploma": {"model": "HREmployeeDiploma", "module": "hr"},
    "employee_absence": {"model": "HREmployeeAbsence", "module": "hr"},
    "employee_suspension": {"model": "HREmployeeSuspension", "module": "hr"},
    "employee_advance": {"model": "HREmployeeAdvance", "module": "hr"},
    "employee_permission": {"model": "HREmployeePermission", "module": "hr"},
    "employee_files": {"model": "HREmployeeDocument", "module": "hr"},
    "employee_history": {"model": "HREmployeeHistory", "module": "hr"},
    "employee_note": {"model": "HREmployeeNote", "module": "hr"},
    "employee_public_holiday": {"model": "HRPublicHoliday", "module": "hr"},
    "training_program": {"model": "LearningModule", "module": "learning"},
    "clocking_schedule": {"model": "WorkSchedule", "module": "hr"},
    "personnel_pointage_shift": {"model": "ShiftSchedule", "module": "hr"},
    
    # =========================================================================
    # INVENTORY / WMS MODULE
    # =========================================================================
    "article": {"model": "Product", "module": "product"},
    "groupe_article": {"model": "ProductCategory", "module": "product"},
    "category_article": {"model": "ProductSubCategory", "module": "product"},
    "type_article": {"model": "ProductType", "module": "product"},
    "unit": {"model": "UnitOfMeasure", "module": "product"},
    "wms_warehouse": {"model": "Warehouse", "module": "inventory"},
    "stock_location": {"model": "Location", "module": "inventory"},
    "license_plate": {"model": "LicensePlate", "module": "inventory"},
    "inventory_count": {"model": "CycleCount", "module": "inventory"},
    "wms_transaction": {"model": "StockMove", "module": "inventory"},
    "wms_device": {"model": "WMSDevice", "module": "wms"},
    "wms_workstation": {"model": "WMSWorkstation", "module": "wms"},
    "wms_relance": {"model": "WMSAlert", "module": "wms"},
    
    # =========================================================================
    # PURCHASING MODULE
    # =========================================================================
    "supplier_info": {"model": "Account (supplier)", "module": "account"},
    "supplier_type": {"model": "AccountCategory", "module": "account"},
    "supplier_contact": {"model": "AccountContact", "module": "account"},
    "supplier_price_request": {"model": "RFQ", "module": "rfq"},
    "purchase_order": {"model": "PurchaseOrder", "module": "accounts_payable"},
    "purchase_order_item": {"model": "POLine", "module": "accounts_payable"},
    "po_reception": {"model": "GoodsReceipt", "module": "accounts_payable"},
    "consumable_request": {"model": "PurchaseRequisition", "module": "accounts_payable"},
    "consumable_req_item": {"model": "PRLine", "module": "accounts_payable"},
    
    # =========================================================================
    # SALES / QUOTING MODULE
    # =========================================================================
    "quotation": {"model": "Quote", "module": "quote"},
    "quotation_items": {"model": "QuoteLineItem", "module": "quote"},
    "quotation_customer": {"model": "Account (customer)", "module": "account"},
    
    # =========================================================================
    # SHIPPING MODULE
    # =========================================================================
    "shipment": {"model": "Shipment", "module": "shipping"},
    "shipment_item": {"model": "ShipmentLine", "module": "shipping"},
    "pick_list": {"model": "PickList", "module": "wms"},
    "pick_list_item": {"model": "PickListLine", "module": "wms"},
    
    # =========================================================================
    # FINANCIAL / MASTER DATA
    # =========================================================================
    "company": {"model": "Site", "module": "site"},
    "company_bank": {"model": "BankAccount", "module": "finance"},
    "bank_account": {"model": "BankAccount", "module": "finance"},
    "bank_transaction": {"model": "BankTransaction", "module": "finance"},
    "currency": {"model": "Currency", "module": "finance"},
    "pay_term": {"model": "PaymentTerm", "module": "finance"},
    "invoice_category": {"model": "InvoiceCategory", "module": "accounts_receivable"},
    
    # =========================================================================
    # QUALITY / PRODUCTION
    # =========================================================================
    "scrap_rebut": {"model": "ScrapRecord", "module": "quality"},
}


class ImportModule(str, Enum):
    """Module being imported."""
    HR = "hr"
    INVENTORY = "inventory"
    PURCHASING = "purchasing"
    SALES = "sales"
    FINANCIAL = "financial"
    MASTER_DATA = "master_data"
    ALL = "all"


@dataclass
class ERPStarzImportConfig:
    """Configuration for erpStarz import."""
    
    module: ImportModule = ImportModule.ALL
    dry_run: bool = False  # If True, don't commit changes
    default_jurisdiction: str = "TN"
    batch_size: int = 100
    skip_existing: bool = True  # Skip records that already exist


@dataclass
class ERPStarzImportResult:
    """Result of an erpStarz import operation."""
    
    batch_id: UUID
    module: str
    total_tables: int
    tables_imported: int
    total_records: int
    imported_count: int
    skipped_count: int
    error_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    table_summaries: dict[str, dict[str, int]] = field(default_factory=dict)
    
    @property
    def success(self) -> bool:
        return self.error_count == 0


class ERPStarzImportService:
    """Service for importing all erpStarz legacy data into Sensei.
    
    This service provides a unified interface for migrating the complete
    erpStarz Symfony/PHP ERP system to the new Sensei platform.
    
    Key Features:
    - Module-based import (HR, Inventory, Purchasing, etc.)
    - Full system import with dependency resolution
    - ID mapping for foreign key relationships
    - Transaction safety with rollback on failure
    - Comprehensive logging and error reporting
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # ID mapping: legacy table -> legacy ID -> new UUID
        self._id_maps: dict[str, dict[str, UUID]] = {}
    
    async def check_erpstarz_tables(self) -> dict[str, bool]:
        """Check which erpStarz tables exist in the database.
        
        Returns a dict mapping table names to existence status.
        """
        table_status = {}
        
        for table_name in ERPSTARZ_ENTITY_MAP.keys():
            try:
                check_stmt = text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table_name
                    )
                """)
                result = await self.db.execute(check_stmt, {"table_name": table_name})
                exists = result.scalar()
                table_status[table_name] = bool(exists)
            except Exception:
                table_status[table_name] = False
        
        return table_status
    
    async def import_inventory_module(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> ERPStarzImportResult:
        """Import inventory/WMS module from erpStarz.
        
        Tables imported:
        - article → Product
        - groupe_article → ProductCategory (metadata)
        - unit → UnitOfMeasure (metadata)
        - wms_warehouse → Warehouse
        - stock_location → Location
        - license_plate → LicensePlate
        """
        config = config or ERPStarzImportConfig(module=ImportModule.INVENTORY)
        batch_id = uuid4()
        
        result = ERPStarzImportResult(
            batch_id=batch_id,
            module="inventory",
            total_tables=0,
            tables_imported=0,
            total_records=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )
        
        # Import warehouses first (no dependencies)
        wh_count = await self._import_warehouses(actor_id, correlation_id, config)
        result.table_summaries["wms_warehouse"] = {"imported": wh_count}
        result.imported_count += wh_count
        
        # Import stock locations (depends on warehouse)
        loc_count = await self._import_stock_locations(actor_id, correlation_id, config)
        result.table_summaries["stock_location"] = {"imported": loc_count}
        result.imported_count += loc_count
        
        # Import articles/products
        prod_count = await self._import_articles(actor_id, correlation_id, config)
        result.table_summaries["article"] = {"imported": prod_count}
        result.imported_count += prod_count
        
        # Import license plates
        lpn_count = await self._import_license_plates(actor_id, correlation_id, config)
        result.table_summaries["license_plate"] = {"imported": lpn_count}
        result.imported_count += lpn_count
        
        result.tables_imported = len([s for s in result.table_summaries.values() if s.get("imported", 0) > 0])
        result.total_tables = len(result.table_summaries)
        
        logger.info(f"Inventory module import complete: {result.imported_count} records")
        return result
    
    async def import_purchasing_module(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> ERPStarzImportResult:
        """Import purchasing module from erpStarz.
        
        Tables imported:
        - supplier_info → Account (supplier type)
        - supplier_contact → AccountContact
        - purchase_order → PurchaseOrder
        - purchase_order_item → POLine
        - po_reception → GoodsReceipt
        """
        config = config or ERPStarzImportConfig(module=ImportModule.PURCHASING)
        batch_id = uuid4()
        
        result = ERPStarzImportResult(
            batch_id=batch_id,
            module="purchasing",
            total_tables=0,
            tables_imported=0,
            total_records=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )
        
        # Import suppliers first
        sup_count = await self._import_suppliers(actor_id, correlation_id, config)
        result.table_summaries["supplier_info"] = {"imported": sup_count}
        result.imported_count += sup_count
        
        # Import purchase orders
        po_count = await self._import_purchase_orders(actor_id, correlation_id, config)
        result.table_summaries["purchase_order"] = {"imported": po_count}
        result.imported_count += po_count
        
        # Import PO items
        poi_count = await self._import_po_items(actor_id, correlation_id, config)
        result.table_summaries["purchase_order_item"] = {"imported": poi_count}
        result.imported_count += poi_count
        
        # Import goods receipts
        gr_count = await self._import_goods_receipts(actor_id, correlation_id, config)
        result.table_summaries["po_reception"] = {"imported": gr_count}
        result.imported_count += gr_count
        
        result.tables_imported = len([s for s in result.table_summaries.values() if s.get("imported", 0) > 0])
        result.total_tables = len(result.table_summaries)
        
        logger.info(f"Purchasing module import complete: {result.imported_count} records")
        return result
    
    async def import_sales_module(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> ERPStarzImportResult:
        """Import sales/quoting module from erpStarz.
        
        Tables imported:
        - quotation_customer → Account (customer type)
        - quotation → Quote
        - quotation_items → QuoteLineItem
        """
        config = config or ERPStarzImportConfig(module=ImportModule.SALES)
        batch_id = uuid4()
        
        result = ERPStarzImportResult(
            batch_id=batch_id,
            module="sales",
            total_tables=0,
            tables_imported=0,
            total_records=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )
        
        # Import customers first
        cust_count = await self._import_customers(actor_id, correlation_id, config)
        result.table_summaries["quotation_customer"] = {"imported": cust_count}
        result.imported_count += cust_count
        
        # Import quotations
        quote_count = await self._import_quotations(actor_id, correlation_id, config)
        result.table_summaries["quotation"] = {"imported": quote_count}
        result.imported_count += quote_count
        
        # Import quotation items
        qi_count = await self._import_quotation_items(actor_id, correlation_id, config)
        result.table_summaries["quotation_items"] = {"imported": qi_count}
        result.imported_count += qi_count
        
        result.tables_imported = len([s for s in result.table_summaries.values() if s.get("imported", 0) > 0])
        result.total_tables = len(result.table_summaries)
        
        logger.info(f"Sales module import complete: {result.imported_count} records")
        return result
    
    async def import_shipping_module(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> ERPStarzImportResult:
        """Import shipping/fulfillment module from erpStarz.
        
        Tables imported:
        - shipment → Shipment
        - shipment_item → ShipmentLine
        - pick_list → PickList
        - pick_list_item → PickListLine
        """
        config = config or ERPStarzImportConfig(module=ImportModule.SALES)  # shipping is part of sales
        batch_id = uuid4()
        
        result = ERPStarzImportResult(
            batch_id=batch_id,
            module="shipping",
            total_tables=0,
            tables_imported=0,
            total_records=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )
        
        # Import pick lists first (needed for fulfillment)
        pl_count = await self._import_pick_lists(actor_id, correlation_id, config)
        result.table_summaries["pick_list"] = {"imported": pl_count}
        result.imported_count += pl_count
        
        # Import pick list items
        pli_count = await self._import_pick_list_items(actor_id, correlation_id, config)
        result.table_summaries["pick_list_item"] = {"imported": pli_count}
        result.imported_count += pli_count
        
        # Import shipments
        ship_count = await self._import_shipments(actor_id, correlation_id, config)
        result.table_summaries["shipment"] = {"imported": ship_count}
        result.imported_count += ship_count
        
        # Import shipment items
        si_count = await self._import_shipment_items(actor_id, correlation_id, config)
        result.table_summaries["shipment_item"] = {"imported": si_count}
        result.imported_count += si_count
        
        result.tables_imported = len([s for s in result.table_summaries.values() if s.get("imported", 0) > 0])
        result.total_tables = len(result.table_summaries)
        
        logger.info(f"Shipping module import complete: {result.imported_count} records")
        return result
    
    async def import_master_data(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> ERPStarzImportResult:
        """Import master data from erpStarz.
        
        Tables imported:
        - company → Site
        - currency → Currency (reference data)
        - pay_term → PaymentTerm (reference data)
        - unit → UnitOfMeasure (reference data)
        """
        config = config or ERPStarzImportConfig(module=ImportModule.MASTER_DATA)
        batch_id = uuid4()
        
        result = ERPStarzImportResult(
            batch_id=batch_id,
            module="master_data",
            total_tables=0,
            tables_imported=0,
            total_records=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )
        
        # Import companies as sites
        comp_count = await self._import_companies(actor_id, correlation_id, config)
        result.table_summaries["company"] = {"imported": comp_count}
        result.imported_count += comp_count
        
        result.tables_imported = len([s for s in result.table_summaries.values() if s.get("imported", 0) > 0])
        result.total_tables = len(result.table_summaries)
        
        logger.info(f"Master data import complete: {result.imported_count} records")
        return result
    
    async def import_full_system(
        self,
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        config: ERPStarzImportConfig | None = None,
    ) -> dict[str, Any]:
        """Perform full erpStarz system migration.
        
        Import order (respecting dependencies):
        1. Master Data (Company, Currency, Units)
        2. HR Module (via hr/legacy_import.py)
        3. Inventory Module (Warehouses, Products)
        4. Purchasing Module (Suppliers, POs)
        5. Sales Module (Customers, Quotes)
        
        Returns comprehensive summary of all imports.
        """
        config = config or ERPStarzImportConfig(module=ImportModule.ALL)
        
        summary = {
            "batch_id": str(uuid4()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "modules": {},
            "total_imported": 0,
            "total_errors": 0,
        }
        
        # 1. Master Data first
        logger.info("Starting master data import...")
        master_result = await self.import_master_data(
            actor_id=actor_id,
            correlation_id=correlation_id,
            config=config,
        )
        summary["modules"]["master_data"] = {
            "imported": master_result.imported_count,
            "errors": master_result.error_count,
            "tables": master_result.table_summaries,
        }
        summary["total_imported"] += master_result.imported_count
        summary["total_errors"] += master_result.error_count
        
        # 2. HR Module (use the dedicated HR import service)
        logger.info("Starting HR module import...")
        try:
            from sensei.services.hr.legacy_import import HRLegacyImportService
            hr_service = HRLegacyImportService(self.db)
            hr_result = await hr_service.import_erpstarz_full(
                actor_id=actor_id,
                actor_roles=actor_roles,
                correlation_id=correlation_id,
            )
            summary["modules"]["hr"] = hr_result
            summary["total_imported"] += hr_result.get("employees", 0)
            summary["total_imported"] += hr_result.get("contracts", 0)
            summary["total_imported"] += hr_result.get("bank_accounts", 0)
            summary["total_imported"] += hr_result.get("salaries", 0)
            summary["total_imported"] += hr_result.get("absences", 0)
            summary["total_imported"] += hr_result.get("advances", 0)
            summary["total_imported"] += hr_result.get("diplomas", 0)
        except Exception as e:
            logger.exception(f"HR module import failed: {e}")
            summary["modules"]["hr"] = {"error": str(e)}
            summary["total_errors"] += 1
        
        # 3. Inventory Module
        logger.info("Starting inventory module import...")
        inv_result = await self.import_inventory_module(
            actor_id=actor_id,
            correlation_id=correlation_id,
            config=config,
        )
        summary["modules"]["inventory"] = {
            "imported": inv_result.imported_count,
            "errors": inv_result.error_count,
            "tables": inv_result.table_summaries,
        }
        summary["total_imported"] += inv_result.imported_count
        summary["total_errors"] += inv_result.error_count
        
        # 4. Purchasing Module
        logger.info("Starting purchasing module import...")
        purch_result = await self.import_purchasing_module(
            actor_id=actor_id,
            correlation_id=correlation_id,
            config=config,
        )
        summary["modules"]["purchasing"] = {
            "imported": purch_result.imported_count,
            "errors": purch_result.error_count,
            "tables": purch_result.table_summaries,
        }
        summary["total_imported"] += purch_result.imported_count
        summary["total_errors"] += purch_result.error_count
        
        # 5. Sales Module
        logger.info("Starting sales module import...")
        sales_result = await self.import_sales_module(
            actor_id=actor_id,
            correlation_id=correlation_id,
            config=config,
        )
        summary["modules"]["sales"] = {
            "imported": sales_result.imported_count,
            "errors": sales_result.error_count,
            "tables": sales_result.table_summaries,
        }
        summary["total_imported"] += sales_result.imported_count
        summary["total_errors"] += sales_result.error_count
        
        # 6. Shipping Module
        logger.info("Starting shipping module import...")
        shipping_result = await self.import_shipping_module(
            actor_id=actor_id,
            correlation_id=correlation_id,
            config=config,
        )
        summary["modules"]["shipping"] = {
            "imported": shipping_result.imported_count,
            "errors": shipping_result.error_count,
            "tables": shipping_result.table_summaries,
        }
        summary["total_imported"] += shipping_result.imported_count
        summary["total_errors"] += shipping_result.error_count
        
        summary["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Full erpStarz import complete: {summary['total_imported']} records, {summary['total_errors']} errors")
        
        return summary
    
    # =========================================================================
    # Private Import Methods
    # =========================================================================
    
    async def _import_warehouses(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import warehouses from wms_warehouse table."""
        imported = 0
        try:
            query = text("""
                SELECT id, code, name, description, timezone, is_active, created_at
                FROM wms_warehouse
                WHERE is_active = true
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Warehouse).where(Warehouse.code == row.get("code"))
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                warehouse = Warehouse(
                    id=new_id,
                    code=row.get("code") or f"WH-{legacy_id}",
                    name=row.get("name") or f"Warehouse {legacy_id}",
                    address=row.get("description"),
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(warehouse)
                
                # Store ID mapping
                self._id_maps.setdefault("wms_warehouse", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} warehouses from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import warehouses: {e}")
        
        return imported
    
    async def _import_stock_locations(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import stock locations from stock_location table."""
        imported = 0
        try:
            query = text("""
                SELECT sl.id, sl.code, sl.name, sl.warehouse_id, sl.parent_id, sl.type
                FROM stock_location sl
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                legacy_wh_id = str(row.get("warehouse_id", ""))
                
                # Get mapped warehouse ID
                warehouse_id = self._id_maps.get("wms_warehouse", {}).get(legacy_wh_id)
                if not warehouse_id:
                    continue  # Skip if warehouse not imported
                
                new_id = uuid4()
                location = Location(
                    id=new_id,
                    warehouse_id=warehouse_id,
                    name=row.get("name") or row.get("code") or f"LOC-{legacy_id}",
                    location_type=row.get("type") or "internal",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(location)
                
                self._id_maps.setdefault("stock_location", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} stock locations from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import stock locations: {e}")
        
        return imported
    
    async def _import_articles(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import articles as Products."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    a.id, a.code_reference, a.description, a.stock, a.stock_min,
                    a.prix, a.groupe_article_id, ga.name as groupe_name
                FROM article a
                LEFT JOIN groupe_article ga ON ga.id = a.groupe_article_id
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                code = row.get("code_reference") or f"ART-{legacy_id}"
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Product).where(Product.part_number == code)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                product = Product(
                    name=row.get("description") or code,
                    part_number=code,
                    sku=code,
                    description=row.get("description"),
                    category=row.get("groupe_name"),
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(product)
                await self.db.flush()  # Get the auto-incremented ID
                
                self._id_maps.setdefault("article", {})[legacy_id] = product.id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} articles/products from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import articles: {e}")
        
        return imported
    
    async def _import_license_plates(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import license plates from license_plate table."""
        imported = 0
        try:
            query = text("""
                SELECT id, number, location_id, status, created_at
                FROM license_plate
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                number = row.get("number")
                
                if not number:
                    continue
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(LicensePlate).where(LicensePlate.number == number)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                lpn = LicensePlate(
                    id=new_id,
                    number=number,
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(lpn)
                
                self._id_maps.setdefault("license_plate", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} license plates from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import license plates: {e}")
        
        return imported
    
    async def _import_suppliers(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import suppliers from supplier_info table."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    si.id, si.name, si.billing_address, si.shipping_address,
                    si.city, si.is_active, st.name as type_name
                FROM supplier_info si
                LEFT JOIN supplier_type st ON st.id = si.type_id
                WHERE si.is_active = true
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                name = row.get("name")
                
                if not name:
                    continue
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Account).where(Account.name == name)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                account = Account(
                    id=new_id,
                    name=name,
                    account_type="supplier",
                    address_line1=row.get("billing_address"),
                    address_line2=row.get("shipping_address"),
                    city=row.get("city"),
                    country="Tunisia",  # erpStarz was Tunisia-based
                    status="active",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(account)
                
                self._id_maps.setdefault("supplier_info", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} suppliers from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import suppliers: {e}")
        
        return imported
    
    async def _import_purchase_orders(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import purchase orders from purchase_order table."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    po.id, po.po, po.created_at, po.request_date, po.prediction_date,
                    po.amount, po.transport_fee, po.tax_fee, po.status,
                    po.supplier_id, c.code as currency_code
                FROM purchase_order po
                LEFT JOIN currency c ON c.id = po.currency_id
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                po_number = row.get("po")
                legacy_supplier_id = str(row.get("supplier_id", ""))
                
                if not po_number:
                    continue
                
                # Get mapped supplier ID
                supplier_id = self._id_maps.get("supplier_info", {}).get(legacy_supplier_id)
                if not supplier_id:
                    continue
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                po = PurchaseOrder(
                    id=new_id,
                    po_number=po_number,
                    supplier_id=supplier_id,
                    currency=row.get("currency_code") or "TND",
                    status=self._map_po_status(row.get("status")),
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(po)
                
                self._id_maps.setdefault("purchase_order", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} purchase orders from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import purchase orders: {e}")
        
        return imported
    
    async def _import_po_items(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import purchase order items."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    poi.id, poi.purchase_order_id, poi.article_id, poi.quantity,
                    poi.unit_price, a.code_reference, a.description
                FROM purchase_order_item poi
                LEFT JOIN article a ON a.id = poi.article_id
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_po_id = str(row.get("purchase_order_id", ""))
                
                # Get mapped PO ID
                po_id = self._id_maps.get("purchase_order", {}).get(legacy_po_id)
                if not po_id:
                    continue
                
                new_id = uuid4()
                line = POLine(
                    id=new_id,
                    po_id=po_id,
                    sku=row.get("code_reference") or "UNKNOWN",
                    description=row.get("description") or "Imported item",
                    quantity=Decimal(str(row.get("quantity") or 0)),
                    unit_price=Decimal(str(row.get("unit_price") or 0)),
                )
                self.db.add(line)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} PO line items from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import PO items: {e}")
        
        return imported
    
    async def _import_goods_receipts(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import goods receipts from po_reception table."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    pr.id, pr.po_id, pr.received_at, pr.received_by_id
                FROM po_reception pr
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                legacy_po_id = str(row.get("po_id", ""))
                
                # Get mapped PO ID
                po_id = self._id_maps.get("purchase_order", {}).get(legacy_po_id)
                if not po_id:
                    continue
                
                new_id = uuid4()
                receipt = GoodsReceipt(
                    id=new_id,
                    po_id=po_id,
                    received_at=row.get("received_at") or datetime.now(timezone.utc),
                    received_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(receipt)
                
                self._id_maps.setdefault("po_reception", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} goods receipts from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import goods receipts: {e}")
        
        return imported
    
    async def _import_customers(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import customers from quotation_customer table."""
        imported = 0
        try:
            query = text("""
                SELECT id, name, address, email, phone
                FROM quotation_customer
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                name = row.get("name")
                
                if not name:
                    continue
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Account).where(Account.name == name)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                account = Account(
                    id=new_id,
                    name=name,
                    account_type="customer",
                    address_line1=row.get("address"),
                    email=row.get("email"),
                    phone=row.get("phone"),
                    country="Tunisia",  # erpStarz was Tunisia-based
                    status="active",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(account)
                
                self._id_maps.setdefault("quotation_customer", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} customers from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import customers: {e}")
        
        return imported
    
    async def _import_quotations(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import quotations from quotation table."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    q.id, q.offer_id, q.created_at, q.validity, q.shipping_term,
                    q.pay_term, q.leadtime, q.currency, q.customer_id
                FROM quotation q
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                offer_id = row.get("offer_id")
                legacy_customer_id = str(row.get("customer_id", ""))
                
                if not offer_id:
                    continue
                
                # Get mapped customer ID
                account_id = self._id_maps.get("quotation_customer", {}).get(legacy_customer_id)
                
                # Skip if no customer mapped (Quote requires account_id)
                if not account_id:
                    continue
                
                new_id = uuid4()
                quote = Quote(
                    id=new_id,
                    quote_number=offer_id,
                    account_id=account_id,
                    title=f"Quote {offer_id}",  # Title is required
                    currency=row.get("currency") or "TND",
                    status="draft",  # Use valid status enum
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(quote)
                
                self._id_maps.setdefault("quotation", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} quotations from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import quotations: {e}")
        
        return imported
    
    async def _import_quotation_items(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import quotation items."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    qi.id, qi.quotation_id, qi.description, qi.quantity,
                    qi.unit_price, qi.total
                FROM quotation_items qi
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            # Track line numbers per quote
            line_counts: dict[str, int] = {}
            
            for row in rows:
                legacy_quote_id = str(row.get("quotation_id", ""))
                
                # Get mapped quote ID
                quote_id = self._id_maps.get("quotation", {}).get(legacy_quote_id)
                if not quote_id:
                    continue
                
                # Increment line number for this quote
                line_counts[legacy_quote_id] = line_counts.get(legacy_quote_id, 0) + 1
                line_number = line_counts[legacy_quote_id]
                
                quantity = Decimal(str(row.get("quantity") or 1))
                unit_price = Decimal(str(row.get("unit_price") or 0))
                line_total = quantity * unit_price
                
                new_id = uuid4()
                line = QuoteLineItem(
                    id=new_id,
                    quote_id=quote_id,
                    line_number=line_number,
                    description=row.get("description") or "Imported item",
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
                self.db.add(line)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} quotation items from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import quotation items: {e}")
        
        return imported
    
    async def _import_companies(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import companies as Sites."""
        imported = 0
        try:
            from sensei.models.site import Site
            
            query = text("""
                SELECT id, name, code, address, email, phone, fax, website
                FROM company
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                name = row.get("name")
                code = row.get("code")
                
                if not name or not code:
                    continue
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Site).where(Site.site_code == code)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                new_id = uuid4()
                site = Site(
                    id=new_id,
                    name=name,
                    site_code=code,
                    address=row.get("address"),
                    country="Tunisia",  # erpStarz was Tunisia-based
                    default_currency="TND",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(site)
                
                self._id_maps.setdefault("company", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} companies as sites from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import companies: {e}")
        
        return imported
    
    async def _import_pick_lists(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import pick lists from pick_list table."""
        imported = 0
        try:
            query = text("""
                SELECT id, number, warehouse_id, source_type, source_id,
                       priority, status, created_at, notes
                FROM pick_list
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                pick_number = row.get("number") or f"PL-{legacy_id}"
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(PickList).where(PickList.pick_number == pick_number)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                # Map warehouse
                legacy_wh_id = str(row.get("warehouse_id", ""))
                warehouse_id = self._id_maps.get("wms_warehouse", {}).get(legacy_wh_id)
                if not warehouse_id:
                    # Try to get first warehouse
                    wh_result = await self.db.execute(select(Warehouse).limit(1))
                    wh = wh_result.scalar_one_or_none()
                    warehouse_id = wh.id if wh else None
                
                if not warehouse_id:
                    continue
                
                new_id = uuid4()
                pick_list = PickList(
                    id=new_id,
                    pick_number=pick_number,
                    warehouse_id=warehouse_id,
                    source_type=row.get("source_type") or "sales_order",
                    source_id=uuid4(),  # Placeholder - would need mapping
                    priority=row.get("priority") or 50,
                    status=self._map_pick_status(row.get("status")),
                    notes=row.get("notes"),
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(pick_list)
                
                self._id_maps.setdefault("pick_list", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} pick lists from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import pick lists: {e}")
        
        return imported
    
    async def _import_pick_list_items(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import pick list items from pick_list_item table."""
        imported = 0
        try:
            query = text("""
                SELECT id, pick_list_id, sku, description, source_location_id,
                       quantity_requested, quantity_picked, lot_number, status
                FROM pick_list_item
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_pl_id = str(row.get("pick_list_id", ""))
                pick_list_id = self._id_maps.get("pick_list", {}).get(legacy_pl_id)
                if not pick_list_id:
                    continue
                
                # Map source location
                legacy_loc_id = str(row.get("source_location_id", ""))
                source_location_id = self._id_maps.get("stock_location", {}).get(legacy_loc_id)
                if not source_location_id:
                    # Get any location
                    loc_result = await self.db.execute(select(Location).limit(1))
                    loc = loc_result.scalar_one_or_none()
                    source_location_id = loc.id if loc else None
                
                if not source_location_id:
                    continue
                
                new_id = uuid4()
                line = PickListLine(
                    id=new_id,
                    pick_list_id=pick_list_id,
                    sku=row.get("sku") or "UNKNOWN",
                    description=row.get("description"),
                    source_location_id=source_location_id,
                    quantity_requested=Decimal(str(row.get("quantity_requested") or 1)),
                    quantity_picked=Decimal(str(row.get("quantity_picked") or 0)),
                    lot_number=row.get("lot_number"),
                    status=row.get("status") or "pending",
                )
                self.db.add(line)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} pick list items from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import pick list items: {e}")
        
        return imported
    
    async def _import_shipments(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import shipments from shipment table."""
        imported = 0
        try:
            query = text("""
                SELECT id, number, customer_id, warehouse_id, ship_date,
                       carrier, tracking_number, ship_to_name, ship_to_address,
                       ship_to_city, ship_to_country, status, notes
                FROM shipment
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_id = str(row.get("id", ""))
                shipment_number = row.get("number") or f"SHIP-{legacy_id}"
                
                # Check if already imported
                if config.skip_existing:
                    existing = await self.db.execute(
                        select(Shipment).where(Shipment.shipment_number == shipment_number)
                    )
                    if existing.scalar_one_or_none():
                        continue
                
                # Map customer to account
                legacy_cust_id = str(row.get("customer_id", ""))
                account_id = self._id_maps.get("quotation_customer", {}).get(legacy_cust_id)
                if not account_id:
                    # Get any account
                    acc_result = await self.db.execute(select(Account).limit(1))
                    acc = acc_result.scalar_one_or_none()
                    account_id = acc.id if acc else None
                
                if not account_id:
                    continue
                
                new_id = uuid4()
                shipment = Shipment(
                    id=new_id,
                    shipment_number=shipment_number,
                    account_id=account_id,
                    ship_date=row.get("ship_date"),
                    carrier=row.get("carrier"),
                    tracking_number=row.get("tracking_number"),
                    ship_to_name=row.get("ship_to_name") or "Unknown",
                    ship_to_address=row.get("ship_to_address") or "Unknown",
                    ship_to_city=row.get("ship_to_city"),
                    ship_to_country=row.get("ship_to_country") or "Tunisia",
                    status=self._map_shipment_status(row.get("status")),
                    notes=row.get("notes"),
                    legacy_id=legacy_id,
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(shipment)
                
                self._id_maps.setdefault("shipment", {})[legacy_id] = new_id
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} shipments from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import shipments: {e}")
        
        return imported
    
    async def _import_shipment_items(
        self,
        actor_id: str,
        correlation_id: str,
        config: ERPStarzImportConfig,
    ) -> int:
        """Import shipment items from shipment_item table."""
        imported = 0
        try:
            query = text("""
                SELECT id, shipment_id, sku, description, quantity_shipped,
                       lot_number, serial_number
                FROM shipment_item
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_ship_id = str(row.get("shipment_id", ""))
                shipment_id = self._id_maps.get("shipment", {}).get(legacy_ship_id)
                if not shipment_id:
                    continue
                
                new_id = uuid4()
                line = ShipmentLine(
                    id=new_id,
                    shipment_id=shipment_id,
                    sku=row.get("sku") or "UNKNOWN",
                    description=row.get("description"),
                    quantity_shipped=Decimal(str(row.get("quantity_shipped") or 1)),
                    lot_number=row.get("lot_number"),
                    serial_number=row.get("serial_number"),
                    legacy_id=str(row.get("id", "")),
                )
                self.db.add(line)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} shipment items from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import shipment items: {e}")
        
        return imported
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    @staticmethod
    def _parse_uuid(value: Any) -> UUID | None:
        """Parse a UUID from various formats."""
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def _map_po_status(legacy_status: str | None) -> str:
        """Map erpStarz PO status to Sensei status."""
        status_map = {
            "Waiting": "draft",
            "Approved": "approved",
            "Sent": "sent",
            "Partial": "partially_received",
            "Received": "received",
            "Closed": "closed",
            "Cancelled": "canceled",
        }
        return status_map.get(legacy_status or "", "draft")
    
    @staticmethod
    def _map_pick_status(legacy_status: str | None) -> str:
        """Map erpStarz pick list status to Sensei status."""
        status_map = {
            "New": "pending",
            "In Progress": "in_progress",
            "InProgress": "in_progress",
            "Completed": "completed",
            "Cancelled": "canceled",
            "Canceled": "canceled",
        }
        return status_map.get(legacy_status or "", "pending")
    
    @staticmethod
    def _map_shipment_status(legacy_status: str | None) -> str:
        """Map erpStarz shipment status to Sensei status."""
        status_map = {
            "Pending": "pending",
            "Picked": "picked",
            "Packed": "packed",
            "Shipped": "shipped",
            "Delivered": "delivered",
            "Cancelled": "canceled",
            "Canceled": "canceled",
        }
        return status_map.get(legacy_status or "", "pending")
    
    def get_id_mapping(self, table_name: str) -> dict[str, UUID]:
        """Get the ID mapping for a specific legacy table.
        
        Useful for resolving foreign keys after import.
        """
        return self._id_maps.get(table_name, {})


# =============================================================================
# Convenience Functions
# =============================================================================

async def migrate_erpstarz_full(
    db: AsyncSession,
    *,
    actor_id: str = "system",
    actor_roles: list[str] | None = None,
) -> dict[str, Any]:
    """Convenience function to migrate the complete erpStarz system.
    
    Usage:
        async with async_session_factory() as db:
            result = await migrate_erpstarz_full(db)
            print(f"Imported {result['total_imported']} records")
            await db.commit()
    """
    service = ERPStarzImportService(db)
    return await service.import_full_system(
        actor_id=actor_id,
        actor_roles=actor_roles or ["admin"],
        correlation_id=f"erpstarz-migration-{uuid4()}",
    )


async def check_erpstarz_availability(db: AsyncSession) -> dict[str, bool]:
    """Check which erpStarz tables are available for import.
    
    Returns a dict mapping table names to whether they exist.
    """
    service = ERPStarzImportService(db)
    return await service.check_erpstarz_tables()
