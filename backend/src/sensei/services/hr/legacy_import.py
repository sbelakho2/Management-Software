"""HR Legacy Data Import Service.

Provides safe import functionality for legacy HR data into the new
jurisdiction-aware HR module. All legacy employees default to Tunisia (TN)
jurisdiction as they were hired under Tunisian CNSS regulations.

Supported Import Sources:
- CSV files (employee lists)
- Excel spreadsheets
- Direct database migration from legacy tables
- JSON data exports

Compatible Field Mappings:
- Legacy table columns → New EmployeeProfile model
- Missing jurisdiction → Defaults to "TN" (Tunisia)
- Missing status → Defaults to "active"
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, TextIO
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.hr import (
    EmployeeProfile,
    HRSocialSecurityRecord,
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
)
from sensei.models.migration import ImportBatch as ImportBatchModel
from sensei.services.production.productionization import (
    EntityType,
    ImportStatus,
)

logger = logging.getLogger(__name__)

# Valid jurisdiction codes
VALID_JURISDICTIONS = frozenset({"TN", "MA", "EG"})
DEFAULT_JURISDICTION = "TN"  # Tunisia for all legacy data

# Legacy table column mappings
# Maps legacy column names to new EmployeeProfile field names
# Includes erpStarz (Symfony/PHP) legacy table columns
LEGACY_COLUMN_MAPPING = {
    # Standard mappings
    "first_name": "first_name",

    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "department": "department",
    "job_title": "job_title",
    "site_id": "site_id",
    "cost_center_code": "cost_center_code",
    "status": "status",
    "hire_date": "hire_date",
    "termination_date": "termination_date",
    "manager_id": "manager_id",
    "user_id": "user_id",
    
    # ========================================
    # erpStarz legacy table mappings
    # Source: /home/aaron/IdeaProjects/erpStarz/src/Entity/
    # ========================================
    
    # employee_info table
    "registration_nbr": "employee_code",  # Unique employee registration number
    "cin_nbr": "national_id",  # Tunisian CIN (Carte d'Identité Nationale)
    "category": "job_category",  # Employee category
    "salary_type": "salary_type",  # Salary type (hourly/monthly)
    "salary_base": "base_salary",  # Base salary in TND
    "is_active": "is_active",  # Boolean active status
    "birth_date": "birth_date",  # Date of birth
    "gender": "gender",  # M/F
    "photo": "photo_url",  # Employee photo path
    
    # employee_cnss table (Tunisian Social Security)
    "id_cnss": "ss_number",  # CNSS social security number
    "id_compta": "accounting_id",  # Accounting identifier
    "civil_status": "civil_status",  # Marital status
    "children_nbr": "dependents_count",  # Number of dependent children
    
    # employee_contract table
    "c_nbr": "contract_number",  # Contract number
    "started_at": "hire_date",  # Contract start = hire date
    "ends_at": "contract_end_date",  # Contract end date
    "company": "company_name",  # Employing company
    
    # employee_leave table
    "start_at": "leave_start",  # Leave start date
    "end_at": "leave_end",  # Leave end date
    "is_payed": "leave_paid",  # Paid leave flag
    "nbr_h": "leave_hours",  # Leave hours
    "is_afternoon": "leave_afternoon",  # Half-day afternoon flag
    
    # ========================================
    # Common legacy aliases (French/English)
    # ========================================
    "firstname": "first_name",
    "first": "first_name",
    "prenom": "first_name",  # French
    "lastname": "last_name",
    "last": "last_name",
    "nom": "last_name",  # French
    "surname": "last_name",
    "email_address": "email",
    "mail": "email",
    "telephone": "phone",
    "phone_number": "phone",
    "tel": "phone",
    "dept": "department",
    "departement": "department",  # French
    "title": "job_title",
    "position": "job_title",
    "poste": "job_title",  # French
    "fonction": "job_title",  # French
    "site": "site_id",
    "location": "site_id",
    "cost_center": "cost_center_code",
    "cc_code": "cost_center_code",
    "centre_cout": "cost_center_code",  # French
    "employee_status": "status",
    "statut": "status",  # French
    "date_embauche": "hire_date",  # French
    "start_date": "hire_date",
    "employment_date": "hire_date",
    "end_date": "termination_date",
    "date_depart": "termination_date",  # French
    "manager": "manager_id",
    "responsable": "manager_id",  # French
    "supervisor": "manager_id",
    "supervisor_id": "manager_id",
    
    # Jurisdiction (defaults to TN for all erpStarz data)
    "jurisdiction": "jurisdiction",
    "pays": "jurisdiction",  # French (country)
    "country": "jurisdiction",
    "country_code": "jurisdiction",
}

# erpStarz table names for direct database migration
# Full mapping of all erpStarz Employee* entities to Sensei HR models
ERPSTARZ_TABLES = {
    # Core employee data
    "employees": "employee_info",           # → EmployeeProfile
    "social_security": "employee_cnss",     # → HRSocialSecurityRecord
    "contracts": "employee_contract",       # → HREmployeeContract
    
    # Time and attendance
    "leave": "employee_leave",              # → HRLeaveRequest
    "leave_annual": "employee_leave_annual",# → HRLeaveBalance
    "clocking": "employee_clocking",        # → HRTimeClockEvent
    "permissions": "employee_permission",   # → HREmployeePermission
    "absences": "employee_absence",         # → HREmployeeAbsence
    
    # Payroll and compensation
    "salary": "employee_salary",            # → HREmployeeSalary
    "advances": "employee_advance",         # → HREmployeeAdvance
    "bank_accounts": "employee_bank_acc",   # → HREmployeeBankAccount
    
    # Training and education
    "training": "employee_training",        # → Training module
    "diplomas": "employee_diploma",         # → HREmployeeDiploma
    
    # Contact information
    "addresses": "employee_address",        # → HREmployeeAddress
    "phones": "employee_phone",             # → EmployeeProfile.phone (primary)
    "emails": "employee_email",             # → EmployeeProfile.email (primary)
    
    # HR management
    "suspensions": "employee_suspension",   # → HREmployeeSuspension
    "notes": "employee_note",               # → HREmployeeNote
    "files": "employee_files",              # → HREmployeeDocument
    "history": "employee_history",          # → HREmployeeHistory
    
    # Calendar
    "public_holidays": "employee_public_holiday",  # → HRPublicHoliday
}


class ImportSourceType(str, Enum):
    """Type of import source."""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    LEGACY_DB = "legacy_db"


@dataclass
class LegacyImportConfig:
    """Configuration for legacy HR data import."""
    
    source_type: ImportSourceType
    source_name: str  # filename or table name
    default_jurisdiction: str = DEFAULT_JURISDICTION
    skip_header: bool = True  # For CSV
    column_mapping: dict[str, str] = field(default_factory=dict)
    # Optional: Create SS records for imported employees
    create_ss_records: bool = True
    # Date format for parsing
    date_format: str = "%Y-%m-%d"
    # Encoding for CSV files
    encoding: str = "utf-8"
    
    def __post_init__(self):
        # Merge custom mapping with defaults
        full_mapping = LEGACY_COLUMN_MAPPING.copy()
        full_mapping.update(self.column_mapping)
        self.column_mapping = full_mapping


@dataclass
class LegacyImportResult:
    """Result of a legacy HR data import."""
    
    batch_id: UUID
    source_file: str
    total_records: int
    imported_count: int
    skipped_count: int
    error_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    created_employee_ids: list[UUID] = field(default_factory=list)
    created_ss_record_ids: list[UUID] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        return self.error_count == 0
    
    @property
    def partial_success(self) -> bool:
        return self.imported_count > 0 and self.error_count > 0


class HRLegacyImportService:
    """Service for importing legacy HR data into the new jurisdiction-aware system.
    
    This service handles the complexities of migrating from the old US-centric
    HR model to the new North Africa (Tunisia, Morocco, Egypt) model.
    
    Key Features:
    - Automatic column name normalization
    - Default jurisdiction assignment (TN for legacy)
    - Optional social security record creation
    - Comprehensive validation and error reporting
    - Transaction safety with rollback on failure
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def import_from_csv(
        self,
        file_content: str | TextIO,
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        config: LegacyImportConfig | None = None,
    ) -> LegacyImportResult:
        """Import employees from a CSV file.
        
        Args:
            file_content: CSV content as string or file-like object
            actor_id: ID of the user performing the import
            actor_roles: Roles of the user
            correlation_id: Request correlation ID for tracing
            config: Import configuration (optional)
        
        Returns:
            LegacyImportResult with details of the import
        """
        config = config or LegacyImportConfig(
            source_type=ImportSourceType.CSV,
            source_name="csv_upload",
        )
        
        # Parse CSV
        if isinstance(file_content, str):
            reader = csv.DictReader(io.StringIO(file_content))
        else:
            reader = csv.DictReader(file_content)
        
        records = []
        for row in reader:
            normalized = self._normalize_record(row, config)
            records.append(normalized)
        
        return await self._execute_import(
            records=records,
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            config=config,
        )
    
    async def import_from_json(
        self,
        json_content: str | list[dict[str, Any]],
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        config: LegacyImportConfig | None = None,
    ) -> LegacyImportResult:
        """Import employees from JSON data.
        
        Args:
            json_content: JSON string or list of dicts
            actor_id: ID of the user performing the import
            actor_roles: Roles of the user
            correlation_id: Request correlation ID for tracing
            config: Import configuration (optional)
        
        Returns:
            LegacyImportResult with details of the import
        """
        config = config or LegacyImportConfig(
            source_type=ImportSourceType.JSON,
            source_name="json_upload",
        )
        
        if isinstance(json_content, str):
            data = json.loads(json_content)
        else:
            data = json_content
        
        if not isinstance(data, list):
            raise ValueError("JSON content must be a list of employee records")
        
        records = []
        for item in data:
            normalized = self._normalize_record(item, config)
            records.append(normalized)
        
        return await self._execute_import(
            records=records,
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            config=config,
        )
    
    async def import_from_legacy_table(
        self,
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        legacy_table_name: str = "legacy_employees",
        config: LegacyImportConfig | None = None,
    ) -> LegacyImportResult:
        """Import employees directly from a legacy database table.
        
        This method queries an existing legacy table and migrates
        records to the new jurisdiction-aware schema.
        
        Args:
            actor_id: ID of the user performing the import
            actor_roles: Roles of the user
            correlation_id: Request correlation ID for tracing
            legacy_table_name: Name of the legacy table to import from
            config: Import configuration (optional)
        
        Returns:
            LegacyImportResult with details of the import
        """
        config = config or LegacyImportConfig(
            source_type=ImportSourceType.LEGACY_DB,
            source_name=legacy_table_name,
        )
        
        # Check if legacy table exists
        try:
            check_stmt = text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """)
            result = await self.db.execute(check_stmt, {"table_name": legacy_table_name})
            exists = result.scalar()
            
            if not exists:
                # Table doesn't exist - this is okay, return empty result
                logger.info(f"Legacy table '{legacy_table_name}' does not exist, nothing to import")
                return LegacyImportResult(
                    batch_id=uuid4(),
                    source_file=legacy_table_name,
                    total_records=0,
                    imported_count=0,
                    skipped_count=0,
                    error_count=0,
                    warnings=[f"Legacy table '{legacy_table_name}' does not exist"],
                )
            
            # Query legacy table
            # Note: We use raw SQL to handle unknown column structure
            select_stmt = text(f"SELECT * FROM {legacy_table_name}")
            result = await self.db.execute(select_stmt)
            rows = result.mappings().all()
            
            records = []
            for row in rows:
                normalized = self._normalize_record(dict(row), config)
                records.append(normalized)
            
        except Exception as e:
            logger.exception(f"Failed to query legacy table: {e}")
            return LegacyImportResult(
                batch_id=uuid4(),
                source_file=legacy_table_name,
                total_records=0,
                imported_count=0,
                skipped_count=0,
                error_count=1,
                errors=[{"error": str(e), "row": 0}],
            )
        
        return await self._execute_import(
            records=records,
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            config=config,
        )
    
    async def import_from_erpstarz(
        self,
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        include_cnss: bool = True,
        include_contracts: bool = True,
        config: LegacyImportConfig | None = None,
    ) -> LegacyImportResult:
        """Import employees from erpStarz legacy database.
        
        This method queries the erpStarz employee_info table and joins with
        employee_cnss for social security data. All employees are assigned
        to Tunisia (TN) jurisdiction since erpStarz was exclusively Tunisian.
        
        erpStarz Tables:
        - employee_info: Core employee data (first_name, last_name, cin_nbr, etc.)
        - employee_cnss: Tunisian CNSS social security (id_cnss, id_compta, etc.)
        - employee_contract: Employment contracts
        - employee_email: Contact emails
        - employee_phone: Contact phones
        
        Args:
            actor_id: ID of the user performing the import
            actor_roles: Roles of the user
            correlation_id: Request correlation ID for tracing
            include_cnss: Whether to join CNSS data (default True)
            include_contracts: Whether to include active contract data (default True)
            config: Import configuration (optional)
        
        Returns:
            LegacyImportResult with details of the import
        """
        config = config or LegacyImportConfig(
            source_type=ImportSourceType.LEGACY_DB,
            source_name="erpstarz_employee_info",
            default_jurisdiction="TN",  # erpStarz was Tunisia-only
        )
        
        try:
            # Build query with optional joins
            # Base query: employee_info
            query_parts = ["""
                SELECT 
                    ei.id as legacy_id,
                    ei.registration_nbr,
                    ei.first_name,
                    ei.last_name,
                    ei.birth_date,
                    ei.gender,
                    ei.cin_nbr,
                    ei.category,
                    ei.salary_type,
                    ei.salary_base,
                    ei.is_active
            """]
            
            if include_cnss:
                query_parts.append(""",
                    ec.id_cnss,
                    ec.id_compta,
                    ec.civil_status,
                    ec.children_nbr
                """)
            
            if include_contracts:
                query_parts.append(""",
                    econ.started_at as hire_date,
                    econ.ends_at as contract_end_date,
                    econ.type as contract_type,
                    econ.status as contract_status,
                    econ.company
                """)
            
            # Add first email and phone if they exist
            query_parts.append(""",
                (SELECT email FROM employee_email WHERE employee_id = ei.id LIMIT 1) as email,
                (SELECT phone FROM employee_phone WHERE employee_id = ei.id LIMIT 1) as phone
            """)
            
            query_parts.append("FROM employee_info ei")
            
            if include_cnss:
                query_parts.append("""
                    LEFT JOIN employee_cnss ec ON ec.employee_id = ei.id
                """)
            
            if include_contracts:
                query_parts.append("""
                    LEFT JOIN employee_contract econ ON econ.employee_id = ei.id
                        AND econ.status = 'active'
                """)
            
            query_parts.append("ORDER BY ei.id")
            
            full_query = " ".join(query_parts)
            
            # Check if erpStarz tables exist
            check_stmt = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'employee_info'
                )
            """)
            result = await self.db.execute(check_stmt)
            exists = result.scalar()
            
            if not exists:
                logger.info("erpStarz employee_info table not found, nothing to import")
                return LegacyImportResult(
                    batch_id=uuid4(),
                    source_file="erpstarz_employee_info",
                    total_records=0,
                    imported_count=0,
                    skipped_count=0,
                    error_count=0,
                    warnings=["erpStarz employee_info table does not exist"],
                )
            
            # Execute query
            result = await self.db.execute(text(full_query))
            rows = result.mappings().all()
            
            records = []
            for row in rows:
                normalized = self._normalize_record(dict(row), config)
                # Force TN jurisdiction for all erpStarz data
                normalized["jurisdiction"] = "TN"
                records.append(normalized)
            
            logger.info(f"Found {len(records)} employees in erpStarz database")
            
        except Exception as e:
            logger.exception(f"Failed to query erpStarz database: {e}")
            return LegacyImportResult(
                batch_id=uuid4(),
                source_file="erpstarz_employee_info",
                total_records=0,
                imported_count=0,
                skipped_count=0,
                error_count=1,
                errors=[{"error": str(e), "row": 0}],
            )
        
        return await self._execute_import(
            records=records,
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
            config=config,
        )
    
    async def import_erpstarz_contracts(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],  # Maps legacy employee_id to new UUID
    ) -> int:
        """Import employee contracts from erpStarz.
        
        Returns count of imported contracts.
        """
        imported = 0
        try:
            query = text("""
                SELECT 
                    ec.id, ec.employee_id, ec.c_nbr, ec.type, 
                    ec.started_at, ec.ends_at, ec.status, ec.company
                FROM employee_contract ec
                ORDER BY ec.started_at
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                contract = HREmployeeContract(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    contract_number=row.get("c_nbr") or f"LEGACY-{row.get('id')}",
                    contract_type=row.get("type") or "CDI",
                    started_at=row.get("started_at") or date.today(),
                    ends_at=row.get("ends_at"),
                    company=row.get("company"),
                    status=row.get("status") or "active",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(contract)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} contracts from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import contracts: {e}")
        
        return imported
    
    async def import_erpstarz_bank_accounts(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],
    ) -> int:
        """Import employee bank accounts from erpStarz."""
        imported = 0
        try:
            query = text("""
                SELECT id, employee_id, bank_name, rib
                FROM employee_bank_acc
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                bank = HREmployeeBankAccount(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    bank_name=row.get("bank_name") or "Unknown",
                    rib=row.get("rib") or "",
                    is_primary=True,
                    is_active=True,
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(bank)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} bank accounts from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import bank accounts: {e}")
        
        return imported
    
    async def import_erpstarz_salaries(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],
    ) -> int:
        """Import salary records from erpStarz."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    es.id, es.employee_id, es.base_salary, es.overtime_hours,
                    es.overtime_amount, es.payroll_month, es.payroll_year
                FROM employee_salary es
                ORDER BY es.payroll_year, es.payroll_month
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                base = Decimal(str(row.get("base_salary") or 0))
                overtime = Decimal(str(row.get("overtime_amount") or 0))
                gross = base + overtime
                
                salary = HREmployeeSalary(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    payroll_month=row.get("payroll_month") or 1,
                    payroll_year=row.get("payroll_year") or date.today().year,
                    base_salary=base,
                    overtime_hours=Decimal(str(row.get("overtime_hours") or 0)),
                    overtime_amount=overtime,
                    gross_salary=gross,
                    total_deductions=Decimal("0"),
                    net_salary=gross,  # Will need adjustment with actual deductions
                    status="imported",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(salary)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} salary records from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import salaries: {e}")
        
        return imported
    
    async def import_erpstarz_absences(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],
    ) -> int:
        """Import absence records from erpStarz."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    ea.id, ea.employee_id, ea.start_date, ea.end_date,
                    ea.type, ea.reason, ea.is_excused, ea.status
                FROM employee_absence ea
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                absence = HREmployeeAbsence(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    start_date=row.get("start_date") or date.today(),
                    end_date=row.get("end_date"),
                    absence_type=row.get("type") or "unexcused",
                    reason=row.get("reason"),
                    is_excused=bool(row.get("is_excused", False)),
                    status=row.get("status") or "recorded",
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(absence)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} absences from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import absences: {e}")
        
        return imported
    
    async def import_erpstarz_advances(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],
    ) -> int:
        """Import salary advance records from erpStarz."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    ea.id, ea.employee_id, ea.amount, ea.request_date,
                    ea.approved_date, ea.status, ea.installments
                FROM employee_advance ea
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                amount = Decimal(str(row.get("amount") or 0))
                advance = HREmployeeAdvance(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    amount=amount,
                    request_date=row.get("request_date") or date.today(),
                    status=row.get("status") or "pending",
                    installments=row.get("installments") or 1,
                    remaining_balance=amount,
                    approved_at=row.get("approved_date"),
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(advance)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} advances from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import advances: {e}")
        
        return imported
    
    async def import_erpstarz_diplomas(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        employee_id_map: dict[str, UUID],
    ) -> int:
        """Import diploma/education records from erpStarz."""
        imported = 0
        try:
            query = text("""
                SELECT 
                    ed.id, ed.employee_id, ed.name, ed.category, ed.obtained_at
                FROM employee_diploma ed
            """)
            result = await self.db.execute(query)
            rows = result.mappings().all()
            
            for row in rows:
                legacy_emp_id = str(row.get("employee_id", ""))
                if legacy_emp_id not in employee_id_map:
                    continue
                
                diploma = HREmployeeDiploma(
                    id=uuid4(),
                    employee_id=employee_id_map[legacy_emp_id],
                    name=row.get("name") or "Unknown Diploma",
                    category=row.get("category"),
                    obtained_at=row.get("obtained_at"),
                    verified=False,
                    created_by_id=self._parse_uuid(actor_id),
                )
                self.db.add(diploma)
                imported += 1
            
            await self.db.flush()
            logger.info(f"Imported {imported} diplomas from erpStarz")
            
        except Exception as e:
            logger.exception(f"Failed to import diplomas: {e}")
        
        return imported
    
    async def import_erpstarz_full(
        self,
        *,
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
    ) -> dict[str, Any]:
        """Perform full erpStarz migration including all related tables.
        
        This method imports:
        1. Employees (employee_info + employee_cnss)
        2. Contracts (employee_contract)
        3. Bank accounts (employee_bank_acc)
        4. Salary records (employee_salary)
        5. Absences (employee_absence)
        6. Salary advances (employee_advance)
        7. Diplomas (employee_diploma)
        
        Returns a summary dict with counts for each entity type.
        """
        summary = {
            "employees": 0,
            "contracts": 0,
            "bank_accounts": 0,
            "salaries": 0,
            "absences": 0,
            "advances": 0,
            "diplomas": 0,
            "errors": [],
        }
        
        # Step 1: Import employees and build ID mapping
        emp_result = await self.import_from_erpstarz(
            actor_id=actor_id,
            actor_roles=actor_roles,
            correlation_id=correlation_id,
        )
        summary["employees"] = emp_result.imported_count
        
        if emp_result.errors:
            summary["errors"].extend([str(e) for e in emp_result.errors])
        
        # Build mapping from legacy IDs to new UUIDs
        # Query to get mapping based on registration_nbr or other legacy identifiers
        employee_id_map: dict[str, UUID] = {}
        try:
            # Get all imported employees with their legacy identifiers
            query = text("""
                SELECT ei.id as legacy_id, hp.id as new_id
                FROM employee_info ei
                JOIN hr_employees hp ON hp.first_name = ei.first_name 
                    AND hp.last_name = ei.last_name
            """)
            result = await self.db.execute(query)
            for row in result.mappings():
                employee_id_map[str(row["legacy_id"])] = row["new_id"]
        except Exception as e:
            logger.warning(f"Could not build employee ID map: {e}")
        
        if not employee_id_map:
            logger.warning("No employee ID mappings found, skipping related imports")
            return summary
        
        # Step 2: Import related entities
        summary["contracts"] = await self.import_erpstarz_contracts(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        summary["bank_accounts"] = await self.import_erpstarz_bank_accounts(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        summary["salaries"] = await self.import_erpstarz_salaries(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        summary["absences"] = await self.import_erpstarz_absences(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        summary["advances"] = await self.import_erpstarz_advances(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        summary["diplomas"] = await self.import_erpstarz_diplomas(
            actor_id=actor_id,
            correlation_id=correlation_id,
            employee_id_map=employee_id_map,
        )
        
        logger.info(f"erpStarz full migration complete: {summary}")
        return summary
    
    def _normalize_record(
        self,
        raw_record: dict[str, Any],
        config: LegacyImportConfig,
    ) -> dict[str, Any]:
        """Normalize a legacy record to match new schema.
        
        - Maps legacy column names to new field names
        - Sets default jurisdiction if missing
        - Normalizes date formats
        - Cleans up string values
        - Handles erpStarz-specific fields (is_active, id_cnss, etc.)
        """
        normalized: dict[str, Any] = {}
        
        # Extended field set including erpStarz columns
        ALLOWED_FIELDS = {
            # Core employee fields
            "first_name", "last_name", "email", "phone",
            "department", "job_title", "site_id", "cost_center_code",
            "status", "hire_date", "termination_date", "manager_id",
            "user_id", "jurisdiction",
            # erpStarz employee_info fields
            "employee_code", "national_id", "job_category", "salary_type",
            "base_salary", "is_active", "birth_date", "gender", "photo_url",
            # erpStarz employee_cnss fields
            "ss_number", "accounting_id", "civil_status", "dependents_count",
            # erpStarz employee_contract fields
            "contract_number", "contract_end_date", "company_name",
        }
        
        for raw_key, value in raw_record.items():
            # Normalize key (lowercase, strip whitespace)
            clean_key = raw_key.lower().strip().replace(" ", "_")
            
            # Look up mapping
            mapped_key = config.column_mapping.get(clean_key, clean_key)
            
            # Skip unknown columns
            if mapped_key not in ALLOWED_FIELDS:
                continue
            
            # Clean and store value
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                    if value == "":
                        value = None
                normalized[mapped_key] = value
        
        # erpStarz: Convert is_active boolean to status string
        if "is_active" in normalized:
            is_active = normalized.pop("is_active")
            if "status" not in normalized:
                if is_active in (True, 1, "1", "true", "True", "TRUE"):
                    normalized["status"] = "active"
                else:
                    normalized["status"] = "terminated"
        
        # Apply defaults
        if "jurisdiction" not in normalized or normalized.get("jurisdiction") not in VALID_JURISDICTIONS:
            normalized["jurisdiction"] = config.default_jurisdiction
        
        if "status" not in normalized or not normalized.get("status"):
            normalized["status"] = "active"
        
        # Parse dates
        for date_field in ("hire_date", "termination_date"):
            if date_field in normalized and normalized[date_field]:
                value = normalized[date_field]
                if isinstance(value, str):
                    try:
                        parsed = datetime.strptime(value, config.date_format)
                        normalized[date_field] = parsed.date()
                    except ValueError:
                        # Try ISO format as fallback
                        try:
                            normalized[date_field] = date.fromisoformat(value[:10])
                        except ValueError:
                            normalized[date_field] = None
                elif isinstance(value, datetime):
                    normalized[date_field] = value.date()
        
        return normalized
    
    async def _execute_import(
        self,
        records: list[dict[str, Any]],
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        config: LegacyImportConfig,
    ) -> LegacyImportResult:
        """Execute the actual import of normalized records."""
        
        batch_id = uuid4()
        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors: list[dict[str, Any]] = []
        warnings: list[str] = []
        created_employee_ids: list[UUID] = []
        created_ss_record_ids: list[UUID] = []
        
        # Validate all records first
        for i, record in enumerate(records, start=1):
            validation_errors = self._validate_record(record, i)
            if validation_errors:
                error_count += 1
                errors.append({
                    "row": i,
                    "data": record,
                    "errors": validation_errors,
                })
        
        # If validation errors, don't proceed
        if error_count > 0:
            return LegacyImportResult(
                batch_id=batch_id,
                source_file=config.source_name,
                total_records=len(records),
                imported_count=0,
                skipped_count=len(records),
                error_count=error_count,
                errors=errors,
                warnings=warnings,
            )
        
        # Import records
        for i, record in enumerate(records, start=1):
            try:
                employee_id = await self._import_single_employee(
                    record=record,
                    actor_id=actor_id,
                    actor_roles=actor_roles,
                    correlation_id=correlation_id,
                    config=config,
                )
                created_employee_ids.append(employee_id)
                imported_count += 1
                
                # Create social security record if configured
                if config.create_ss_records:
                    try:
                        ss_record_id = await self._create_ss_record(
                            employee_id=employee_id,
                            jurisdiction=record.get("jurisdiction", DEFAULT_JURISDICTION),
                            hire_date=record.get("hire_date"),
                            actor_id=actor_id,
                        )
                        if ss_record_id:
                            created_ss_record_ids.append(ss_record_id)
                    except Exception as ss_err:
                        # SS record failure is a warning, not error
                        warnings.append(
                            f"Row {i}: Failed to create SS record: {ss_err}"
                        )
                
            except Exception as e:
                logger.exception(f"Failed to import row {i}: {e}")
                error_count += 1
                errors.append({
                    "row": i,
                    "data": record,
                    "error": str(e),
                })
        
        # Create import batch record
        batch = ImportBatchModel(
            id=batch_id,
            entity_type=EntityType.EMPLOYEE.value,
            source_file=config.source_name,
            total_records=len(records),
            valid_records=imported_count,
            error_records=error_count,
            status=(
                ImportStatus.COMPLETED.value if error_count == 0
                else ImportStatus.FAILED.value
            ),
            imported_by=actor_id,
            error_log=errors if errors else None,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(batch)
        await self.db.flush()
        
        return LegacyImportResult(
            batch_id=batch_id,
            source_file=config.source_name,
            total_records=len(records),
            imported_count=imported_count,
            skipped_count=skipped_count,
            error_count=error_count,
            errors=errors,
            warnings=warnings,
            created_employee_ids=created_employee_ids,
            created_ss_record_ids=created_ss_record_ids,
        )
    
    def _validate_record(
        self,
        record: dict[str, Any],
        row_number: int,
    ) -> list[str]:
        """Validate a single employee record."""
        errors = []
        
        if not record.get("first_name"):
            errors.append("first_name is required")
        if not record.get("last_name"):
            errors.append("last_name is required")
        
        status = record.get("status", "active")
        if status not in ("active", "onboarding", "offboarding", "terminated"):
            errors.append(f"Invalid status: {status}")
        
        jurisdiction = record.get("jurisdiction", DEFAULT_JURISDICTION)
        if jurisdiction not in VALID_JURISDICTIONS:
            # This is normalized to default, so just warn
            pass
        
        return errors
    
    async def _import_single_employee(
        self,
        record: dict[str, Any],
        actor_id: str,
        actor_roles: list[str],
        correlation_id: str,
        config: LegacyImportConfig,
    ) -> UUID:
        """Import a single employee record."""
        
        employee = EmployeeProfile(
            id=uuid4(),
            first_name=record["first_name"],
            last_name=record["last_name"],
            email=record.get("email"),
            phone=record.get("phone"),
            department=record.get("department"),
            job_title=record.get("job_title"),
            site_id=record.get("site_id"),
            cost_center_code=record.get("cost_center_code"),
            jurisdiction=record.get("jurisdiction", DEFAULT_JURISDICTION),
            status=record.get("status", "active"),
            hire_date=record.get("hire_date"),
            termination_date=record.get("termination_date"),
            user_id=self._parse_uuid(record.get("user_id")),
            manager_id=self._parse_uuid(record.get("manager_id")),
            created_by_id=self._parse_uuid(actor_id),
        )
        
        self.db.add(employee)
        await self.db.flush()
        
        logger.info(
            "Imported employee %s %s (ID: %s, jurisdiction: %s)",
            employee.first_name,
            employee.last_name,
            employee.id,
            employee.jurisdiction,
        )
        
        return employee.id
    
    async def _create_ss_record(
        self,
        employee_id: UUID,
        jurisdiction: str,
        hire_date: date | None,
        actor_id: str,
    ) -> UUID | None:
        """Create a placeholder social security record for an imported employee."""
        
        # Generate placeholder SS number (to be updated with real number later)
        ss_number = f"PENDING-{str(employee_id)[:8].upper()}"
        
        ss_record = HRSocialSecurityRecord(
            id=uuid4(),
            employee_id=employee_id,
            jurisdiction=jurisdiction,
            ss_number=ss_number,
            registration_date=hire_date or date.today(),
            status="pending",  # Needs to be verified
            created_by_id=self._parse_uuid(actor_id),
        )
        
        self.db.add(ss_record)
        await self.db.flush()
        
        return ss_record.id
    
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
    
    async def get_import_status(self, batch_id: UUID) -> ImportBatchModel | None:
        """Get the status of an import batch."""
        stmt = select(ImportBatchModel).where(ImportBatchModel.id == batch_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_import_batches(
        self,
        *,
        entity_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ImportBatchModel]:
        """List import batches with optional filtering."""
        stmt = select(ImportBatchModel)
        
        if entity_type:
            stmt = stmt.where(ImportBatchModel.entity_type == entity_type)
        if status:
            stmt = stmt.where(ImportBatchModel.status == status)
        
        stmt = stmt.order_by(ImportBatchModel.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# =============================================================================
# Convenience function for script usage
# =============================================================================

async def migrate_legacy_employees(
    db: AsyncSession,
    *,
    actor_id: str = "system",
    actor_roles: list[str] | None = None,
    legacy_table: str = "legacy_employees",
    default_jurisdiction: str = "TN",
) -> LegacyImportResult:
    """Convenience function to migrate legacy employees.
    
    Usage in scripts:
        async with async_session_factory() as db:
            result = await migrate_legacy_employees(db)
            print(f"Imported {result.imported_count} employees")
            await db.commit()
    """
    service = HRLegacyImportService(db)
    config = LegacyImportConfig(
        source_type=ImportSourceType.LEGACY_DB,
        source_name=legacy_table,
        default_jurisdiction=default_jurisdiction,
        create_ss_records=True,
    )
    
    return await service.import_from_legacy_table(
        actor_id=actor_id,
        actor_roles=actor_roles or ["admin"],
        correlation_id=f"legacy-migration-{uuid4()}",
        legacy_table_name=legacy_table,
        config=config,
    )
