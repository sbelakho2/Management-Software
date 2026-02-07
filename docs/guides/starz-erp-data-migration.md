# StarzERP Data Migration Guide

## Overview

The StarzERP Import Service (`starz_import_service.py`) provides comprehensive data migration from the legacy StarzERP MySQL database into Sensei OS PostgreSQL. This unified service handles all 56 entity types with proper dependency ordering, conflict resolution, and audit logging.

## Architecture: Merge, Not Parallel

**IMPORTANT**: StarzERP data is **merged into existing Sensei OS tables** - no parallel tables are created.

```
┌─────────────────────────┐                    ┌─────────────────────────┐
│    StarzERP MySQL       │                    │   Sensei OS PostgreSQL  │
│    (Source Database)    │                    │   (Target Database)     │
├─────────────────────────┤                    ├─────────────────────────┤
│ wms_warehouse           │ ─── Transform ───> │ warehouses              │
│ employee_info           │ ─── Transform ───> │ hr_employees            │
│ supplier                │ ─── Transform ───> │ accounts (type=SUPPLIER)│
│ article                 │ ─── Transform ───> │ products                │
│ ...62 source tables     │                    │ ...307 Sensei tables    │
└─────────────────────────┘                    └─────────────────────────┘
        READ ONLY                                     WRITE TO
```

### Technical Implementation

- **StarzBase**: Separate `DeclarativeBase` for MySQL source models (62 tables)
- **Base**: Sensei OS `DeclarativeBase` for PostgreSQL target models (307 tables)
- **No Metadata Overlap**: StarzBase and Base are completely isolated
- **No Alembic Migrations**: StarzERP models are excluded from migrations

The import service:
1. Connects to StarzERP MySQL using `StarzBase` models (read-only)
2. Transforms data and maps StarzERP integer IDs → Sensei OS UUIDs
3. Writes to Sensei OS PostgreSQL using `Base` models
4. Handles conflicts (skip/update existing records)

## Key Features

- **Full Entity Coverage**: 56 entity types across all modules
- **Dependency-Aware Ordering**: Imports entities in correct FK order
- **Conflict Resolution**: Skip, update, or fail on duplicates
- **Progress Tracking**: Real-time import status
- **Error Handling**: Comprehensive error capture with rollback
- **Audit Logging**: Full import history

## Entity Type Mappings

### Direct Model Mappings (44 entities)

These StarzERP entities map directly to Sensei OS database models:

#### Inventory/WMS Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzWarehouse` | `Warehouse` | `warehouses` |
| `StarzStockLocation` | `Location` | `locations` |
| `StarzLicensePlate` | `LicensePlate` | `license_plates` |
| `StarzWmsDevice` | `WmsDevice` | `wms_devices` |
| `StarzWmsWorkstation` | `WmsWorkstation` | `wms_workstations` |
| `StarzWmsTransaction` | `StockMove` | `stock_moves` |
| `StarzInventoryCount` | `InventoryLevel` | `inventory_levels` |

#### HR Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzEmployee` | `EmployeeProfile` | `hr_employees` |
| `StarzEmployeeCNSS` | `HRSocialSecurityRecord` | `hr_social_security_records` |
| `StarzEmployeeContract` | `HREmployeeContract` | `hr_employee_contracts` |
| `StarzEmployeeAddress` | `HREmployeeAddress` | `hr_employee_addresses` |
| `StarzEmployeeBankAccount` | `HREmployeeBankAccount` | `hr_employee_bank_accounts` |
| `StarzEmployeeDiploma` | `HREmployeeDiploma` | `hr_employee_diplomas` |
| `StarzEmployeeLeave` | `HRLeaveRequest` | `hr_leave_requests` |
| `StarzEmployeeLeaveAnnual` | `HRLeaveBalance` | `hr_leave_balances` |
| `StarzEmployeeClocking` | `HRTimeClockEvent` | `hr_time_clock_events` |
| `StarzEmployeeAbsence` | `HREmployeeAbsence` | `hr_employee_absences` |
| `StarzEmployeeSalary` | `HREmployeeSalary` | `hr_employee_salaries` |
| `StarzEmployeeAdvance` | `HREmployeeAdvance` | `hr_employee_advances` |
| `StarzEmployeeSuspension` | `HREmployeeSuspension` | `hr_employee_suspensions` |
| `StarzEmployeePermission` | `HREmployeePermission` | `hr_employee_permissions` |
| `StarzEmployeeDocument` | `HREmployeeDocument` | `hr_employee_documents` |
| `StarzEmployeeHistory` | `HREmployeeHistory` | `hr_employee_history` |
| `StarzEmployeeNote` | `HREmployeeNote` | `hr_employee_notes` |
| `StarzPublicHoliday` | `HRPublicHoliday` | `hr_public_holidays` |

#### Training Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzTrainingProgram` | `Training` | `trainings` |
| `StarzEmployeeTraining` | `TrainingParticipant` | `training_participants` |

#### Account/Partner Module

| StarzERP Entity | Sensei OS Model | Account Type |
|-----------------|-----------------|--------------|
| `StarzSupplier` | `Account` | `SUPPLIER` |
| `StarzCustomer` | `Account` | `CUSTOMER` |
| `StarzSupplierContact` | `Contact` | - |

#### Finance Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzPaymentTerm` | `PaymentTerm` | `payment_terms` |
| `StarzTaxCode` | `TaxRate` | `tax_rates` |
| `StarzBankAccount` | `BankAccount` | `bank_accounts` |
| `StarzBankTransaction` | `BankTransaction` | `bank_transactions` |
| `StarzPayment` | `Payment` | `payments` |

#### Accounts Payable Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzConsumableRequest` | `PurchaseRequisition` | `purchase_requisitions` |
| `StarzPurchaseOrder` | `PurchaseOrder` | `purchase_orders` |
| `StarzPOReceipt` | `GoodsReceipt` | `goods_receipts` |
| `StarzSupplierInvoice` | `SupplierInvoice` | `supplier_invoices` |

#### Accounts Receivable Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzQuotation` | `SalesOrder` | `sales_orders` |
| `StarzCustomerInvoice` | `CustomerInvoice` | `customer_invoices` |
| `StarzShipment` | `Shipment` | `shipments` |

#### Product Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzArticle` | `Product` | `products` |

#### Quality Module

| StarzERP Entity | Sensei OS Model | Table |
|-----------------|-----------------|-------|
| `StarzScrapRecord` | `NonConformance` | `non_conformances` |

### Cached/Extended Data Mappings (12 entities)

These StarzERP entities don't have direct Sensei OS models and are stored as cached references or extended data:

| StarzERP Entity | Storage Method | Usage |
|-----------------|----------------|-------|
| `StarzUnit` | Cached | Unit of measure lookup for products |
| `StarzArticleGroup` | Cached | Product family classification |
| `StarzArticleCategory` | Cached | Product category classification |
| `StarzArticleType` | Cached | Product type classification |
| `StarzSupplierType` | Cached | Supplier classification |
| `StarzBank` | Cached | Bank reference lookup |
| `StarzClockingSchedule` | Cached | Work schedule reference |
| `StarzEmployeePhone` | Employee extended_data | Phone numbers stored in JSONB |
| `StarzEmployeeEmail` | Employee extended_data | Email addresses stored in JSONB |
| `StarzShiftSchedule` | Employee extended_data | Shift assignments stored in JSONB |
| `StarzSupplierPriceRequest` | Deferred | Imported via Purchasing module |
| `StarzPickList` | Deferred | Imported via WMS module |

## Import Order

The service imports entities in strict dependency order to ensure FK relationships are satisfied:

### Phase 1: Master Data (No Dependencies)
1. Units
2. Warehouses
3. Article Groups/Categories/Types
4. Supplier Types
5. Payment Terms
6. Tax Codes
7. Banks
8. Schedules
9. Public Holidays
10. Training Programs

### Phase 2: Warehouse Infrastructure
11. Stock Locations (depends on Warehouses)
12. WMS Devices (depends on Warehouses)
13. WMS Workstations (depends on Warehouses)

### Phase 3: Products
14. Articles (depends on Units, Categories)

### Phase 4: Partners
15. Suppliers
16. Supplier Contacts (depends on Suppliers)
17. Customers
18. Company Bank Accounts

### Phase 5: HR Core
19. Employees

### Phase 6: HR Details (All depend on Employees)
20-35. Employee CNSS, Contracts, Addresses, Phones, Emails, Bank Accounts, Diplomas, Leaves, Leave Balances, Clocking, Absences, Salary, Advances, Suspensions, Permissions, Training, Documents, History, Notes, Shift Schedules

### Phase 7: Inventory Transactions
36. License Plates (depends on Warehouses, Locations)
37. WMS Transactions
38. Inventory Counts

### Phase 8: Purchasing Flow
39. Price Requests
40. Purchase Orders (depends on Suppliers)
41. PO Receipts (depends on POs)
42. Consumable Requests
43. Supplier Invoices

### Phase 9: Sales Flow
44. Quotations
45. Customer Invoices

### Phase 10: Shipping
46. Shipments
47. Pick Lists

### Phase 11: Finance
48. Payments
49. Bank Transactions

### Phase 12: Quality
50. Scrap Records

## Usage

### Python API

```python
from sensei.services.external.starz_import_service import (
    StarzErpImportService,
    ImportEntityType,
)

async def run_import(sensei_db, starz_connection_string):
    service = StarzErpImportService(
        sensei_session=sensei_db,
        starz_connection_string=starz_connection_string,
        default_jurisdiction="TN",  # Tunisia
        batch_size=500,
        on_conflict="skip",  # or "update" or "fail"
    )
    
    # Import all entities
    result = await service.import_all()
    
    print(f"Total imported: {result.total_imported}")
    print(f"Total failed: {result.total_failed}")
    
    # Or import specific entities
    result = await service.import_all(
        entity_types=[
            ImportEntityType.EMPLOYEES,
            ImportEntityType.EMPLOYEE_CONTRACTS,
            ImportEntityType.EMPLOYEE_CNSS,
        ]
    )
```

### Preview Import

```python
# Preview counts without importing
preview = await service.preview_import()
for entity_type, counts in preview.items():
    print(f"{entity_type.value}: {counts['source_count']} source, {counts['existing_count']} existing")
```

### REST API

The import service is also accessible via the Admin API:

```bash
# Preview import
GET /api/v1/admin/starz-import/preview

# Start full import
POST /api/v1/admin/starz-import/start

# Import specific entities
POST /api/v1/admin/starz-import/start
{
    "entity_types": ["employees", "employee_contracts"],
    "on_conflict": "update"
}

# Check import status
GET /api/v1/admin/starz-import/status/{batch_id}
```

### Admin Dashboard

Navigate to **Admin > Data Migration > StarzERP Import** in the Sensei OS admin interface:

1. Click "Preview Import" to see record counts
2. Select entity types to import (or "All")
3. Choose conflict resolution strategy
4. Click "Start Import"
5. Monitor progress in real-time
6. Review results and any errors

## Conflict Resolution Strategies

| Strategy | Behavior |
|----------|----------|
| `skip` | Skip existing records (based on unique key match) |
| `update` | Update existing records with new values |
| `fail` | Fail the import if any duplicates found |

## Jurisdiction Handling

All StarzERP employees are imported with Tunisia (TN) jurisdiction by default, as the legacy system was used for Tunisian operations. This aligns with CNSS (Caisse Nationale de Sécurité Sociale) requirements.

The jurisdiction can be overridden:
- Via the `default_jurisdiction` parameter
- Per-employee during post-import data cleanup

## Error Handling

Import errors are captured per entity and included in the result:

```python
for entity_type, result in batch.entity_results.items():
    if result.failed > 0:
        print(f"{entity_type.value} errors:")
        for error in result.errors:
            print(f"  - {error}")
```

Common error causes:
- Missing FK references (dependency not imported)
- Data validation failures (invalid dates, null required fields)
- Unique constraint violations (duplicate codes)

## Testing

Run the import service tests:

```bash
cd backend
pytest tests/services/test_starz_verification.py -v
```

Verify model routing:

```bash
python -c "
from sensei.services.external.starz_import_service import StarzErpImportService, ImportEntityType
for et in ImportEntityType:
    starz = StarzErpImportService._get_starz_model(None, et)
    sensei = StarzErpImportService._get_sensei_model(None, et)
    print(f'{et.value}: {starz.__name__ if starz else \"N/A\"} → {sensei.__name__ if sensei else \"cached/extended\"}')"
```

## Related Documentation

- [HR Module Analysis Report](../../HR_MODULE_ANALYSIS_REPORT.md) - Legacy data migration section
- [Database Schema](../architecture/1.2-database-schema.md) - Full schema documentation
- [Admin Guide](./admin-guide.md) - Admin dashboard usage
