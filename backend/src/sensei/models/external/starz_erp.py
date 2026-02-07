"""
SQLAlchemy models for starzERP (MySQL) - READ-ONLY SOURCE MODELS.

IMPORTANT: These models are ONLY for reading from the legacy starzERP MySQL
database. They use a separate DeclarativeBase (StarzBase) that is NOT connected
to Sensei OS PostgreSQL. No tables are created from these models in Sensei OS.

Data Flow:
  StarzERP MySQL → [Read via StarzBase models] → Transform → [Write to Sensei OS models] → PostgreSQL

These match the schema of the erpStarz project for data migration purposes:
- WMS/Inventory: warehouses, locations, devices, workstations, LPNs
- Products: articles, categories, units
- HR: employees, contracts, CNSS, leaves, clocking
- Purchasing: suppliers, POs, receipts
- Sales: customers, quotations, invoices
- Shipping: shipments, pick lists
- Finance: banks, payments, invoices

See starz_import_service.py for the import logic that reads from these models
and writes to the corresponding Sensei OS models.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    JSON,
    ForeignKey,
    Float,
    Numeric,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class StarzBase(DeclarativeBase):
    """
    Separate DeclarativeBase for starzERP MySQL models.
    
    This base class is intentionally ISOLATED from Sensei OS Base to ensure:
    1. StarzERP tables are NEVER created in Sensei OS PostgreSQL
    2. Alembic migrations NEVER include StarzERP models
    3. Clear separation between source (MySQL) and target (PostgreSQL)
    
    These models are READ-ONLY - used only to query the legacy database.
    """
    pass


# ============================================================================
# WMS / Inventory Models
# ============================================================================

class StarzWarehouse(StarzBase):
    __tablename__ = "wms_warehouse"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzWmsDevice(StarzBase):
    __tablename__ = "wms_device"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_identifier: Mapped[str] = mapped_column("device_identifier", String(50))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column("device_type", String(50))
    status: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON)
    registered_at: Mapped[Optional[datetime]] = mapped_column("registered_at", DateTime)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column("last_seen_at", DateTime)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzWmsWorkstation(StarzBase):
    __tablename__ = "wms_workstation"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workstation_code: Mapped[str] = mapped_column("workstation_code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    station_type: Mapped[str] = mapped_column("station_type", String(50))
    scanner_model: Mapped[str] = mapped_column("scanner_model", String(50))
    scanner_serial: Mapped[Optional[str]] = mapped_column("scanner_serial", String(100))
    connection_type: Mapped[str] = mapped_column("connection_type", String(20))
    pc_hostname: Mapped[Optional[str]] = mapped_column("pc_hostname", String(100))
    current_user: Mapped[Optional[str]] = mapped_column("current_user", String(100))
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column("registered_at", DateTime)
    last_activity: Mapped[datetime] = mapped_column("last_activity", DateTime)
    api_token_hash: Mapped[Optional[str]] = mapped_column("api_token_hash", String(255))
    token_expires_at: Mapped[Optional[datetime]] = mapped_column("token_expires_at", DateTime)


class StarzStockLocation(StarzBase):
    __tablename__ = "wms_stock_location"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column("code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    type: Mapped[str] = mapped_column("type", String(50))
    label: Mapped[Optional[str]] = mapped_column(String(120))
    zone: Mapped[Optional[str]] = mapped_column(String(50))
    aisle: Mapped[Optional[str]] = mapped_column(String(20))
    rack: Mapped[Optional[str]] = mapped_column(String(20))
    level: Mapped[Optional[str]] = mapped_column(String(20))
    bin: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzLicensePlate(StarzBase):
    __tablename__ = "wms_license_plate"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column("code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    location_id: Mapped[Optional[int]] = mapped_column("location_id", Integer)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    item_sku: Mapped[Optional[str]] = mapped_column("item_sku", String(120))
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    uom: Mapped[Optional[str]] = mapped_column(String(10))
    lot_number: Mapped[Optional[str]] = mapped_column("lot_number", String(50))
    serial_number: Mapped[Optional[str]] = mapped_column("serial_number", String(100))
    expiry_date: Mapped[Optional[date]] = mapped_column("expiry_date", Date)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)


class StarzWmsTransaction(StarzBase):
    """Inventory transaction log."""
    __tablename__ = "wms_transaction"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_type: Mapped[str] = mapped_column("transaction_type", String(30))  # receive, ship, transfer, adjust
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    from_location_id: Mapped[Optional[int]] = mapped_column("from_location_id", Integer)
    to_location_id: Mapped[Optional[int]] = mapped_column("to_location_id", Integer)
    lpn_id: Mapped[Optional[int]] = mapped_column("lpn_id", Integer)
    item_sku: Mapped[str] = mapped_column("item_sku", String(120))
    quantity: Mapped[float] = mapped_column(Float)
    uom: Mapped[str] = mapped_column(String(10))
    reference_type: Mapped[Optional[str]] = mapped_column("reference_type", String(30))  # PO, SO, WO, ADJ
    reference_id: Mapped[Optional[int]] = mapped_column("reference_id", Integer)
    user_id: Mapped[Optional[int]] = mapped_column("user_id", Integer)
    workstation_id: Mapped[Optional[int]] = mapped_column("workstation_id", Integer)
    transaction_date: Mapped[datetime] = mapped_column("transaction_date", DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzInventoryCount(StarzBase):
    """Cycle count / physical inventory."""
    __tablename__ = "inventory_count"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    location_id: Mapped[Optional[int]] = mapped_column("location_id", Integer)
    count_type: Mapped[str] = mapped_column("count_type", String(20))  # cycle, physical
    status: Mapped[str] = mapped_column(String(20))  # scheduled, in_progress, completed
    scheduled_date: Mapped[date] = mapped_column("scheduled_date", Date)
    counted_date: Mapped[Optional[date]] = mapped_column("counted_date", Date)
    counted_by_id: Mapped[Optional[int]] = mapped_column("counted_by_id", Integer)
    item_sku: Mapped[Optional[str]] = mapped_column("item_sku", String(120))
    system_quantity: Mapped[Optional[float]] = mapped_column("system_quantity", Float)
    counted_quantity: Mapped[Optional[float]] = mapped_column("counted_quantity", Float)
    variance: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ============================================================================
# Product / Article Models
# ============================================================================

class StarzUnit(StarzBase):
    """Unit of measure."""
    __tablename__ = "unit"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(255))
    base_unit_id: Mapped[Optional[int]] = mapped_column("base_unit_id", Integer)
    conversion_factor: Mapped[Optional[float]] = mapped_column("conversion_factor", Float, default=1.0)


class StarzArticleGroup(StarzBase):
    """Product group/category (niveau 1)."""
    __tablename__ = "groupe_article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzArticleCategory(StarzBase):
    """Product category (niveau 2)."""
    __tablename__ = "category_article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    group_id: Mapped[Optional[int]] = mapped_column("group_id", Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzArticleType(StarzBase):
    """Product type (niveau 3)."""
    __tablename__ = "type_article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    category_id: Mapped[Optional[int]] = mapped_column("category_id", Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzArticle(StarzBase):
    __tablename__ = "article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_reference: Mapped[str] = mapped_column("codeReference", String(100))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    prix: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(255))
    unit_id: Mapped[int] = mapped_column("unit_id", Integer)
    group_id: Mapped[Optional[int]] = mapped_column("group_id", Integer)
    category_id: Mapped[Optional[int]] = mapped_column("category_id", Integer)
    type_id: Mapped[Optional[int]] = mapped_column("type_id", Integer)
    min_stock: Mapped[Optional[float]] = mapped_column("min_stock", Float)
    max_stock: Mapped[Optional[float]] = mapped_column("max_stock", Float)
    reorder_point: Mapped[Optional[float]] = mapped_column("reorder_point", Float)
    lead_time_days: Mapped[Optional[int]] = mapped_column("lead_time_days", Integer)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(50))
    weight: Mapped[Optional[float]] = mapped_column(Float)
    weight_unit: Mapped[Optional[str]] = mapped_column("weight_unit", String(10))
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)


# ============================================================================
# HR / Employee Models
# ============================================================================

class StarzEmployee(StarzBase):
    """Core employee information."""
    __tablename__ = "employee_info"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registration_nbr: Mapped[Optional[str]] = mapped_column("registration_nbr", String(50))  # Matricule
    first_name: Mapped[str] = mapped_column("first_name", String(100))
    last_name: Mapped[str] = mapped_column("last_name", String(100))
    birth_date: Mapped[Optional[date]] = mapped_column("birth_date", Date)
    gender: Mapped[Optional[str]] = mapped_column(String(1))  # M/F
    cin_nbr: Mapped[Optional[str]] = mapped_column("cin_nbr", String(20))  # National ID (CIN)
    photo: Mapped[Optional[str]] = mapped_column(String(255))
    category: Mapped[Optional[str]] = mapped_column(String(50))
    salary_type: Mapped[Optional[str]] = mapped_column("salary_type", String(20))  # hourly/monthly
    salary_base: Mapped[Optional[float]] = mapped_column("salary_base", Float)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)


class StarzEmployeeCNSS(StarzBase):
    """Tunisian CNSS social security data."""
    __tablename__ = "employee_cnss"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    id_cnss: Mapped[Optional[str]] = mapped_column("id_cnss", String(20))  # CNSS number
    id_compta: Mapped[Optional[str]] = mapped_column("id_compta", String(20))  # Accounting ID
    civil_status: Mapped[Optional[str]] = mapped_column("civil_status", String(20))  # single/married/divorced/widowed
    children_nbr: Mapped[Optional[int]] = mapped_column("children_nbr", Integer, default=0)


class StarzEmployeeContract(StarzBase):
    """Employment contract."""
    __tablename__ = "employee_contract"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    c_nbr: Mapped[Optional[str]] = mapped_column("c_nbr", String(50))  # Contract number
    type: Mapped[Optional[str]] = mapped_column(String(30))  # CDI, CDD, etc.
    status: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[Optional[date]] = mapped_column("started_at", Date)
    ends_at: Mapped[Optional[date]] = mapped_column("ends_at", Date)
    company: Mapped[Optional[str]] = mapped_column(String(100))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    job_title: Mapped[Optional[str]] = mapped_column("job_title", String(100))
    salary: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzEmployeeLeave(StarzBase):
    """Employee leave/absence request."""
    __tablename__ = "employee_leave"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    leave_type: Mapped[Optional[str]] = mapped_column("leave_type", String(30))  # annual, sick, etc.
    start_at: Mapped[date] = mapped_column("start_at", Date)
    end_at: Mapped[date] = mapped_column("end_at", Date)
    nbr_h: Mapped[Optional[float]] = mapped_column("nbr_h", Float)  # Hours
    is_payed: Mapped[bool] = mapped_column("is_payed", Boolean, default=True)
    is_afternoon: Mapped[bool] = mapped_column("is_afternoon", Boolean, default=False)  # Half-day
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected
    approved_by_id: Mapped[Optional[int]] = mapped_column("approved_by_id", Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzEmployeeLeaveAnnual(StarzBase):
    """Annual leave balance."""
    __tablename__ = "employee_leave_annual"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    year: Mapped[int] = mapped_column(Integer)
    entitlement_days: Mapped[float] = mapped_column("entitlement_days", Float, default=0)
    used_days: Mapped[float] = mapped_column("used_days", Float, default=0)
    carried_over: Mapped[float] = mapped_column("carried_over", Float, default=0)
    balance: Mapped[float] = mapped_column(Float, default=0)


class StarzEmployeeClocking(StarzBase):
    """Time clock events."""
    __tablename__ = "employee_clocking"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    clock_date: Mapped[date] = mapped_column("clock_date", Date)
    clock_in: Mapped[Optional[datetime]] = mapped_column("clock_in", DateTime)
    clock_out: Mapped[Optional[datetime]] = mapped_column("clock_out", DateTime)
    break_start: Mapped[Optional[datetime]] = mapped_column("break_start", DateTime)
    break_end: Mapped[Optional[datetime]] = mapped_column("break_end", DateTime)
    total_hours: Mapped[Optional[float]] = mapped_column("total_hours", Float)
    overtime_hours: Mapped[Optional[float]] = mapped_column("overtime_hours", Float)
    status: Mapped[str] = mapped_column(String(20), default="recorded")  # recorded, validated, rejected
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzEmployeeSalary(StarzBase):
    """Salary payment record."""
    __tablename__ = "employee_salary"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    period_year: Mapped[int] = mapped_column("period_year", Integer)
    period_month: Mapped[int] = mapped_column("period_month", Integer)
    base_salary: Mapped[float] = mapped_column("base_salary", Float)
    overtime_amount: Mapped[float] = mapped_column("overtime_amount", Float, default=0)
    bonus_amount: Mapped[float] = mapped_column("bonus_amount", Float, default=0)
    deductions: Mapped[float] = mapped_column(Float, default=0)
    cnss_employee: Mapped[float] = mapped_column("cnss_employee", Float, default=0)  # Employee contribution
    cnss_employer: Mapped[float] = mapped_column("cnss_employer", Float, default=0)  # Employer contribution
    net_salary: Mapped[float] = mapped_column("net_salary", Float)
    paid_at: Mapped[Optional[date]] = mapped_column("paid_at", Date)
    payment_method: Mapped[Optional[str]] = mapped_column("payment_method", String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")


class StarzEmployeeBankAccount(StarzBase):
    """Employee bank account for salary payment."""
    __tablename__ = "employee_bank_acc"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    bank_name: Mapped[str] = mapped_column("bank_name", String(100))
    bank_code: Mapped[Optional[str]] = mapped_column("bank_code", String(20))
    branch_code: Mapped[Optional[str]] = mapped_column("branch_code", String(20))
    account_number: Mapped[str] = mapped_column("account_number", String(30))
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    rib: Mapped[Optional[str]] = mapped_column(String(24))  # Tunisian RIB
    is_primary: Mapped[bool] = mapped_column("is_primary", Boolean, default=True)


class StarzEmployeeAdvance(StarzBase):
    """Salary advance."""
    __tablename__ = "employee_advance"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    amount: Mapped[float] = mapped_column(Float)
    requested_at: Mapped[date] = mapped_column("requested_at", Date)
    approved_at: Mapped[Optional[date]] = mapped_column("approved_at", Date)
    approved_by_id: Mapped[Optional[int]] = mapped_column("approved_by_id", Integer)
    paid_at: Mapped[Optional[date]] = mapped_column("paid_at", Date)
    deducted_from_month: Mapped[Optional[int]] = mapped_column("deducted_from_month", Integer)
    deducted_from_year: Mapped[Optional[int]] = mapped_column("deducted_from_year", Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzEmployeeAbsence(StarzBase):
    """Unplanned absence record."""
    __tablename__ = "employee_absence"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    absence_date: Mapped[date] = mapped_column("absence_date", Date)
    absence_type: Mapped[str] = mapped_column("absence_type", String(30))  # sick, no_show, etc.
    hours: Mapped[Optional[float]] = mapped_column(Float)
    is_justified: Mapped[bool] = mapped_column("is_justified", Boolean, default=False)
    justification: Mapped[Optional[str]] = mapped_column(Text)
    document_path: Mapped[Optional[str]] = mapped_column("document_path", String(255))


class StarzEmployeeTraining(StarzBase):
    """Employee training record."""
    __tablename__ = "employee_training"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    training_program_id: Mapped[Optional[int]] = mapped_column("training_program_id", Integer)
    training_name: Mapped[str] = mapped_column("training_name", String(200))
    start_date: Mapped[date] = mapped_column("start_date", Date)
    end_date: Mapped[Optional[date]] = mapped_column("end_date", Date)
    status: Mapped[str] = mapped_column(String(20), default="enrolled")  # enrolled, completed, failed
    score: Mapped[Optional[float]] = mapped_column(Float)
    certificate_path: Mapped[Optional[str]] = mapped_column("certificate_path", String(255))


class StarzTrainingProgram(StarzBase):
    """Training program definition."""
    __tablename__ = "training_program"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    duration_hours: Mapped[Optional[int]] = mapped_column("duration_hours", Integer)
    is_mandatory: Mapped[bool] = mapped_column("is_mandatory", Boolean, default=False)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzEmployeeDiploma(StarzBase):
    """Employee educational credentials."""
    __tablename__ = "employee_diploma"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    diploma_type: Mapped[str] = mapped_column("diploma_type", String(50))
    title: Mapped[str] = mapped_column(String(200))
    institution: Mapped[Optional[str]] = mapped_column(String(200))
    obtained_date: Mapped[Optional[date]] = mapped_column("obtained_date", Date)
    document_path: Mapped[Optional[str]] = mapped_column("document_path", String(255))


class StarzEmployeeAddress(StarzBase):
    """Employee address."""
    __tablename__ = "employee_address"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    address_type: Mapped[str] = mapped_column("address_type", String(20), default="home")
    street: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column("postal_code", String(20))
    country: Mapped[str] = mapped_column(String(50), default="TN")
    is_primary: Mapped[bool] = mapped_column("is_primary", Boolean, default=True)


class StarzEmployeePhone(StarzBase):
    """Employee phone number."""
    __tablename__ = "employee_phone"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    phone_type: Mapped[str] = mapped_column("phone_type", String(20), default="mobile")
    phone: Mapped[str] = mapped_column(String(20))
    is_primary: Mapped[bool] = mapped_column("is_primary", Boolean, default=True)


class StarzEmployeeEmail(StarzBase):
    """Employee email address."""
    __tablename__ = "employee_email"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    email_type: Mapped[str] = mapped_column("email_type", String(20), default="work")
    email: Mapped[str] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column("is_primary", Boolean, default=True)


class StarzEmployeeSuspension(StarzBase):
    """Employee suspension record."""
    __tablename__ = "employee_suspension"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    suspension_type: Mapped[str] = mapped_column("suspension_type", String(30))
    start_date: Mapped[date] = mapped_column("start_date", Date)
    end_date: Mapped[Optional[date]] = mapped_column("end_date", Date)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    is_paid: Mapped[bool] = mapped_column("is_paid", Boolean, default=False)


class StarzEmployeePermission(StarzBase):
    """Employee permission/short leave."""
    __tablename__ = "employee_permission"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    permission_date: Mapped[date] = mapped_column("permission_date", Date)
    start_time: Mapped[Optional[datetime]] = mapped_column("start_time", DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column("end_time", DateTime)
    hours: Mapped[Optional[float]] = mapped_column(Float)
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")


class StarzEmployeeDocument(StarzBase):
    """Employee document/file."""
    __tablename__ = "employee_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    document_type: Mapped[str] = mapped_column("document_type", String(50))
    file_name: Mapped[str] = mapped_column("file_name", String(255))
    file_path: Mapped[str] = mapped_column("file_path", String(500))
    uploaded_at: Mapped[datetime] = mapped_column("uploaded_at", DateTime)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column("uploaded_by_id", Integer)


class StarzEmployeeHistory(StarzBase):
    """Employee change history."""
    __tablename__ = "employee_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    change_type: Mapped[str] = mapped_column("change_type", String(50))  # promotion, transfer, salary_change
    change_date: Mapped[date] = mapped_column("change_date", Date)
    old_value: Mapped[Optional[str]] = mapped_column("old_value", Text)
    new_value: Mapped[Optional[str]] = mapped_column("new_value", Text)
    changed_by_id: Mapped[Optional[int]] = mapped_column("changed_by_id", Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzEmployeeNote(StarzBase):
    """Employee note/comment."""
    __tablename__ = "employee_note"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    note_type: Mapped[str] = mapped_column("note_type", String(30), default="general")
    content: Mapped[str] = mapped_column(Text)
    is_private: Mapped[bool] = mapped_column("is_private", Boolean, default=False)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)


class StarzPublicHoliday(StarzBase):
    """Public holiday calendar."""
    __tablename__ = "employee_public_holiday"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[date] = mapped_column("holiday_date", Date)
    name: Mapped[str] = mapped_column(String(100))
    is_full_day: Mapped[bool] = mapped_column("is_full_day", Boolean, default=True)
    country: Mapped[str] = mapped_column(String(2), default="TN")
    year: Mapped[int] = mapped_column(Integer)


class StarzClockingSchedule(StarzBase):
    """Work schedule definition."""
    __tablename__ = "clocking_schedule"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[Optional[str]] = mapped_column("start_time", String(5))  # HH:MM
    end_time: Mapped[Optional[str]] = mapped_column("end_time", String(5))
    break_start: Mapped[Optional[str]] = mapped_column("break_start", String(5))
    break_end: Mapped[Optional[str]] = mapped_column("break_end", String(5))
    work_days: Mapped[Optional[str]] = mapped_column("work_days", String(20))  # "1,2,3,4,5" for Mon-Fri
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzShiftSchedule(StarzBase):
    """Shift assignment."""
    __tablename__ = "personnel_pointage_shift"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column("employee_id", Integer)
    schedule_id: Mapped[int] = mapped_column("schedule_id", Integer)
    shift_date: Mapped[date] = mapped_column("shift_date", Date)
    assigned_by_id: Mapped[Optional[int]] = mapped_column("assigned_by_id", Integer)


# ============================================================================
# Supplier / Purchasing Models
# ============================================================================

class StarzSupplier(StarzBase):
    """Supplier/vendor master."""
    __tablename__ = "supplier_info"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    type_id: Mapped[Optional[int]] = mapped_column("type_id", Integer)
    contact_name: Mapped[Optional[str]] = mapped_column("contact_name", String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(50), default="TN")
    tax_id: Mapped[Optional[str]] = mapped_column("tax_id", String(30))  # Matricule fiscal
    payment_terms_days: Mapped[int] = mapped_column("payment_terms_days", Integer, default=30)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzSupplierType(StarzBase):
    """Supplier category."""
    __tablename__ = "supplier_type"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))


class StarzSupplierContact(StarzBase):
    """Supplier contact person."""
    __tablename__ = "supplier_contact"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column("supplier_id", Integer)
    name: Mapped[str] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column("is_primary", Boolean, default=False)


class StarzSupplierPriceRequest(StarzBase):
    """RFQ to suppliers."""
    __tablename__ = "supplier_price_request"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(30))
    supplier_id: Mapped[int] = mapped_column("supplier_id", Integer)
    request_date: Mapped[date] = mapped_column("request_date", Date)
    valid_until: Mapped[Optional[date]] = mapped_column("valid_until", Date)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # draft, sent, responded, closed
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)


class StarzPurchaseOrder(StarzBase):
    """Purchase order header."""
    __tablename__ = "purchase_order"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_number: Mapped[str] = mapped_column("po_number", String(30))
    supplier_id: Mapped[int] = mapped_column("supplier_id", Integer)
    order_date: Mapped[date] = mapped_column("order_date", Date)
    expected_date: Mapped[Optional[date]] = mapped_column("expected_date", Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, approved, sent, partial, received, cancelled
    total_amount: Mapped[float] = mapped_column("total_amount", Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    payment_terms: Mapped[Optional[str]] = mapped_column("payment_terms", String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    approved_by_id: Mapped[Optional[int]] = mapped_column("approved_by_id", Integer)
    approved_at: Mapped[Optional[datetime]] = mapped_column("approved_at", DateTime)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzPurchaseOrderItem(StarzBase):
    """Purchase order line item."""
    __tablename__ = "purchase_order_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_id: Mapped[int] = mapped_column("po_id", Integer)
    article_id: Mapped[int] = mapped_column("article_id", Integer)
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column("unit_price", Float)
    tax_rate: Mapped[float] = mapped_column("tax_rate", Float, default=0)
    total_price: Mapped[float] = mapped_column("total_price", Float)
    received_qty: Mapped[float] = mapped_column("received_qty", Float, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzPOReceipt(StarzBase):
    """Purchase order goods receipt."""
    __tablename__ = "po_reception"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    po_id: Mapped[int] = mapped_column("po_id", Integer)
    receipt_number: Mapped[str] = mapped_column("receipt_number", String(30))
    receipt_date: Mapped[date] = mapped_column("receipt_date", Date)
    received_by_id: Mapped[Optional[int]] = mapped_column("received_by_id", Integer)
    warehouse_id: Mapped[Optional[int]] = mapped_column("warehouse_id", Integer)
    location_id: Mapped[Optional[int]] = mapped_column("location_id", Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzPOReceiptItem(StarzBase):
    """PO receipt line item."""
    __tablename__ = "po_reception_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column("receipt_id", Integer)
    po_item_id: Mapped[int] = mapped_column("po_item_id", Integer)
    article_id: Mapped[int] = mapped_column("article_id", Integer)
    quantity: Mapped[float] = mapped_column(Float)
    lpn_code: Mapped[Optional[str]] = mapped_column("lpn_code", String(50))
    lot_number: Mapped[Optional[str]] = mapped_column("lot_number", String(50))


class StarzConsumableRequest(StarzBase):
    """Internal purchase requisition."""
    __tablename__ = "consumable_request"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_number: Mapped[str] = mapped_column("request_number", String(30))
    requester_id: Mapped[int] = mapped_column("requester_id", Integer)
    department: Mapped[Optional[str]] = mapped_column(String(100))
    request_date: Mapped[date] = mapped_column("request_date", Date)
    needed_by: Mapped[Optional[date]] = mapped_column("needed_by", Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, ordered, received, rejected
    approved_by_id: Mapped[Optional[int]] = mapped_column("approved_by_id", Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StarzConsumableRequestItem(StarzBase):
    """Purchase requisition line."""
    __tablename__ = "consumable_req_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column("request_id", Integer)
    article_id: Mapped[Optional[int]] = mapped_column("article_id", Integer)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(10))
    estimated_price: Mapped[Optional[float]] = mapped_column("estimated_price", Float)


# ============================================================================
# Customer / Sales Models
# ============================================================================

class StarzCustomer(StarzBase):
    """Customer master."""
    __tablename__ = "quotation_customer"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[Optional[str]] = mapped_column("contact_name", String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(50), default="TN")
    tax_id: Mapped[Optional[str]] = mapped_column("tax_id", String(30))
    credit_limit: Mapped[float] = mapped_column("credit_limit", Float, default=0)
    payment_terms_days: Mapped[int] = mapped_column("payment_terms_days", Integer, default=30)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzQuotation(StarzBase):
    """Sales quotation header."""
    __tablename__ = "quotation"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_number: Mapped[str] = mapped_column("quote_number", String(30))
    customer_id: Mapped[int] = mapped_column("customer_id", Integer)
    quote_date: Mapped[date] = mapped_column("quote_date", Date)
    valid_until: Mapped[Optional[date]] = mapped_column("valid_until", Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, sent, accepted, rejected, expired
    total_amount: Mapped[float] = mapped_column("total_amount", Float, default=0)
    tax_amount: Mapped[float] = mapped_column("tax_amount", Float, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzQuotationItem(StarzBase):
    """Sales quotation line item."""
    __tablename__ = "quotation_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quotation_id: Mapped[int] = mapped_column("quotation_id", Integer)
    article_id: Mapped[Optional[int]] = mapped_column("article_id", Integer)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column("unit_price", Float)
    discount_percent: Mapped[float] = mapped_column("discount_percent", Float, default=0)
    tax_rate: Mapped[float] = mapped_column("tax_rate", Float, default=0)
    total_price: Mapped[float] = mapped_column("total_price", Float)


# ============================================================================
# Shipping Models
# ============================================================================

class StarzShipment(StarzBase):
    """Outbound shipment header."""
    __tablename__ = "shipment"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_number: Mapped[str] = mapped_column("shipment_number", String(30))
    customer_id: Mapped[int] = mapped_column("customer_id", Integer)
    ship_date: Mapped[date] = mapped_column("ship_date", Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, picking, packed, shipped, delivered
    carrier: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_number: Mapped[Optional[str]] = mapped_column("tracking_number", String(100))
    ship_to_address: Mapped[Optional[str]] = mapped_column("ship_to_address", Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    warehouse_id: Mapped[Optional[int]] = mapped_column("warehouse_id", Integer)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzShipmentItem(StarzBase):
    """Shipment line item."""
    __tablename__ = "shipment_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column("shipment_id", Integer)
    article_id: Mapped[int] = mapped_column("article_id", Integer)
    quantity: Mapped[float] = mapped_column(Float)
    lpn_code: Mapped[Optional[str]] = mapped_column("lpn_code", String(50))
    lot_number: Mapped[Optional[str]] = mapped_column("lot_number", String(50))


class StarzPickList(StarzBase):
    """Pick list for warehouse picking."""
    __tablename__ = "pick_list"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_number: Mapped[str] = mapped_column("pick_number", String(30))
    shipment_id: Mapped[Optional[int]] = mapped_column("shipment_id", Integer)
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, in_progress, completed
    assigned_to_id: Mapped[Optional[int]] = mapped_column("assigned_to_id", Integer)
    started_at: Mapped[Optional[datetime]] = mapped_column("started_at", DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column("completed_at", DateTime)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzPickListItem(StarzBase):
    """Pick list line item."""
    __tablename__ = "pick_list_item"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pick_list_id: Mapped[int] = mapped_column("pick_list_id", Integer)
    article_id: Mapped[int] = mapped_column("article_id", Integer)
    from_location_id: Mapped[int] = mapped_column("from_location_id", Integer)
    quantity: Mapped[float] = mapped_column(Float)
    picked_qty: Mapped[float] = mapped_column("picked_qty", Float, default=0)
    lpn_code: Mapped[Optional[str]] = mapped_column("lpn_code", String(50))
    picked_at: Mapped[Optional[datetime]] = mapped_column("picked_at", DateTime)


# ============================================================================
# Financial Models
# ============================================================================

class StarzBank(StarzBase):
    """Bank master."""
    __tablename__ = "company_bank"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    swift_code: Mapped[Optional[str]] = mapped_column("swift_code", String(11))
    country: Mapped[str] = mapped_column(String(2), default="TN")


class StarzBankAccount(StarzBase):
    """Company bank account."""
    __tablename__ = "bank_account"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_id: Mapped[int] = mapped_column("bank_id", Integer)
    account_name: Mapped[str] = mapped_column("account_name", String(100))
    account_number: Mapped[str] = mapped_column("account_number", String(30))
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    rib: Mapped[Optional[str]] = mapped_column(String(24))  # Tunisian RIB
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzBankTransaction(StarzBase):
    """Bank transaction record."""
    __tablename__ = "bank_transaction"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column("account_id", Integer)
    transaction_date: Mapped[date] = mapped_column("transaction_date", Date)
    transaction_type: Mapped[str] = mapped_column("transaction_type", String(20))  # deposit, withdrawal, transfer
    amount: Mapped[float] = mapped_column(Float)
    reference: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(255))
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    reconciled_at: Mapped[Optional[datetime]] = mapped_column("reconciled_at", DateTime)


class StarzPaymentTerm(StarzBase):
    """Payment terms definition."""
    __tablename__ = "pay_term"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(100))
    days: Mapped[int] = mapped_column(Integer)
    discount_percent: Mapped[float] = mapped_column("discount_percent", Float, default=0)
    discount_days: Mapped[int] = mapped_column("discount_days", Integer, default=0)


class StarzTaxCode(StarzBase):
    """Tax code definition."""
    __tablename__ = "tax_code"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100))
    rate: Mapped[float] = mapped_column(Float)  # e.g., 19 for 19%
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


class StarzSupplierInvoice(StarzBase):
    """Supplier/purchase invoice."""
    __tablename__ = "supplier_invoice"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column("invoice_number", String(50))
    supplier_id: Mapped[int] = mapped_column("supplier_id", Integer)
    invoice_date: Mapped[date] = mapped_column("invoice_date", Date)
    due_date: Mapped[date] = mapped_column("due_date", Date)
    po_id: Mapped[Optional[int]] = mapped_column("po_id", Integer)
    subtotal: Mapped[float] = mapped_column(Float)
    tax_amount: Mapped[float] = mapped_column("tax_amount", Float, default=0)
    total_amount: Mapped[float] = mapped_column("total_amount", Float)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, paid, cancelled
    paid_amount: Mapped[float] = mapped_column("paid_amount", Float, default=0)
    paid_at: Mapped[Optional[date]] = mapped_column("paid_at", Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzCustomerInvoice(StarzBase):
    """Customer/sales invoice."""
    __tablename__ = "customer_invoice"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str] = mapped_column("invoice_number", String(50))
    customer_id: Mapped[int] = mapped_column("customer_id", Integer)
    invoice_date: Mapped[date] = mapped_column("invoice_date", Date)
    due_date: Mapped[date] = mapped_column("due_date", Date)
    shipment_id: Mapped[Optional[int]] = mapped_column("shipment_id", Integer)
    subtotal: Mapped[float] = mapped_column(Float)
    tax_amount: Mapped[float] = mapped_column("tax_amount", Float, default=0)
    total_amount: Mapped[float] = mapped_column("total_amount", Float)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, sent, paid, overdue, cancelled
    paid_amount: Mapped[float] = mapped_column("paid_amount", Float, default=0)
    paid_at: Mapped[Optional[date]] = mapped_column("paid_at", Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


class StarzPayment(StarzBase):
    """Payment record."""
    __tablename__ = "payment"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_number: Mapped[str] = mapped_column("payment_number", String(30))
    payment_type: Mapped[str] = mapped_column("payment_type", String(20))  # incoming, outgoing
    payment_date: Mapped[date] = mapped_column("payment_date", Date)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="TND")
    payment_method: Mapped[str] = mapped_column("payment_method", String(30))  # cash, check, transfer, card
    bank_account_id: Mapped[Optional[int]] = mapped_column("bank_account_id", Integer)
    supplier_id: Mapped[Optional[int]] = mapped_column("supplier_id", Integer)
    customer_id: Mapped[Optional[int]] = mapped_column("customer_id", Integer)
    invoice_id: Mapped[Optional[int]] = mapped_column("invoice_id", Integer)
    reference: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[int]] = mapped_column("created_by_id", Integer)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)


# ============================================================================
# Quality / Production Models
# ============================================================================

class StarzScrapRecord(StarzBase):
    """Scrap/reject record."""
    __tablename__ = "scrap_rebut"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scrap_date: Mapped[date] = mapped_column("scrap_date", Date)
    article_id: Mapped[int] = mapped_column("article_id", Integer)
    quantity: Mapped[float] = mapped_column(Float)
    reason_code: Mapped[Optional[str]] = mapped_column("reason_code", String(30))
    reason_description: Mapped[Optional[str]] = mapped_column("reason_description", Text)
    work_order_id: Mapped[Optional[int]] = mapped_column("work_order_id", Integer)
    station_id: Mapped[Optional[int]] = mapped_column("station_id", Integer)
    operator_id: Mapped[Optional[int]] = mapped_column("operator_id", Integer)
    cost: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)
