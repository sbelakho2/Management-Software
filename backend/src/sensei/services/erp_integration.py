"""
ERP Integration Layer Service.

Provides bi-directional REST/Webhook API integration with external ERP systems.
Includes master data synchronization, transactional sync, field mapping,
reconciliation queues, and circuit breaker patterns.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import hashlib
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class ERPSystem(str, Enum):
    """Supported ERP systems."""
    SAP = "sap"
    ORACLE = "oracle"
    DYNAMICS = "dynamics"
    SAGE = "sage"
    ODOO = "odoo"
    CUSTOM = "custom"


class EntityType(str, Enum):
    """Entity types for synchronization."""
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PART = "part"
    BOM = "bom"
    ROUTING = "routing"
    SALES_ORDER = "sales_order"
    PURCHASE_ORDER = "purchase_order"
    GOODS_RECEIPT = "goods_receipt"
    INVENTORY_MOVEMENT = "inventory_movement"
    WORK_ORDER = "work_order"
    QUALITY_COST = "quality_cost"
    EMPLOYEE_LABOR = "employee_labor"


class SyncDirection(str, Enum):
    """Synchronization direction."""
    INBOUND = "inbound"  # ERP -> Sensei
    OUTBOUND = "outbound"  # Sensei -> ERP
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Synchronization status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    SKIPPED = "skipped"


class ReconciliationStatus(str, Enum):
    """Reconciliation queue item status."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    AUTO_RESOLVED = "auto_resolved"
    ESCALATED = "escalated"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, no requests allowed
    HALF_OPEN = "half_open"  # Testing if system recovered


class MappingType(str, Enum):
    """Field mapping types."""
    DIRECT = "direct"  # 1:1 mapping
    TRANSFORM = "transform"  # Requires transformation
    LOOKUP = "lookup"  # Lookup from reference table
    COMPUTED = "computed"  # Computed from multiple fields
    CONSTANT = "constant"  # Fixed value
    CONDITIONAL = "conditional"  # Based on condition


class UoMType(str, Enum):
    """Unit of Measure types."""
    EACH = "ea"
    KILOGRAM = "kg"
    GRAM = "g"
    METER = "m"
    CENTIMETER = "cm"
    LITER = "l"
    MILLILITER = "ml"
    PIECE = "pc"
    BOX = "box"
    PALLET = "pallet"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class FieldMapping:
    """Field mapping configuration."""
    id: str
    source_field: str
    target_field: str
    mapping_type: MappingType
    transform_function: str | None = None
    lookup_table: str | None = None
    default_value: Any = None
    is_required: bool = False
    validation_regex: str | None = None
    description: str | None = None


@dataclass
class EntityMapping:
    """Entity-level mapping configuration."""
    id: str
    entity_type: EntityType
    erp_system: ERPSystem
    erp_entity_name: str
    sensei_entity_name: str
    field_mappings: list[FieldMapping] = field(default_factory=list)
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UoMConversion:
    """Unit of Measure conversion rule."""
    id: str
    from_uom: str
    to_uom: str
    conversion_factor: float
    is_bidirectional: bool = True
    erp_system: ERPSystem | None = None
    notes: str | None = None


@dataclass
class TaxCode:
    """Tax code normalization for Morocco (ICE/IF)."""
    id: str
    code: str
    description: str
    rate: float  # Percentage (e.g., 20.0 for 20%)
    tax_type: str  # VAT, ICE, IF, etc.
    erp_code: str | None = None  # Code in ERP system
    is_active: bool = True
    effective_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    effective_to: datetime | None = None


@dataclass
class SyncRecord:
    """Record of a synchronization event."""
    id: str
    entity_type: EntityType
    entity_id: str
    erp_id: str | None
    direction: SyncDirection
    status: SyncStatus
    data_hash: str
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationItem:
    """Item in the reconciliation queue for manual resolution."""
    id: str
    entity_type: EntityType
    sensei_id: str
    erp_id: str
    conflict_type: str
    sensei_data: dict[str, Any]
    erp_data: dict[str, Any]
    differences: list[str]
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    priority: int = 5  # 1-10, 1 being highest
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_notes: str | None = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for an integration endpoint."""
    id: str
    name: str
    erp_system: ERPSystem
    entity_type: EntityType | None = None
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    failure_threshold: int = 5
    success_threshold: int = 3  # Successes needed to close from half-open
    error_rate_threshold: float = 0.1  # 10% error rate triggers open
    timeout_seconds: int = 60
    last_failure_at: datetime | None = None
    last_state_change: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_requests: int = 0


@dataclass
class WebhookConfig:
    """Webhook configuration for ERP events."""
    id: str
    erp_system: ERPSystem
    event_type: str
    endpoint_url: str
    secret_key: str
    is_active: bool = True
    retry_count: int = 3
    retry_delay_seconds: int = 60
    last_triggered: datetime | None = None
    failure_count: int = 0


@dataclass
class SyncJob:
    """Scheduled synchronization job."""
    id: str
    name: str
    entity_type: EntityType
    direction: SyncDirection
    schedule_cron: str  # Cron expression
    is_active: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    last_status: SyncStatus | None = None
    records_processed: int = 0
    records_failed: int = 0


@dataclass
class SyncStatistics:
    """Statistics for synchronization operations."""
    total_synced: int = 0
    successful: int = 0
    failed: int = 0
    conflicts: int = 0
    skipped: int = 0
    avg_duration_ms: float = 0.0
    last_sync_at: datetime | None = None
    error_rate: float = 0.0


# =============================================================================
# FIELD TRANSFORMATION FUNCTIONS
# =============================================================================


class FieldTransformer:
    """Provides field transformation functions."""
    
    @staticmethod
    def uppercase(value: str) -> str:
        """Convert to uppercase."""
        return value.upper() if value else ""
    
    @staticmethod
    def lowercase(value: str) -> str:
        """Convert to lowercase."""
        return value.lower() if value else ""
    
    @staticmethod
    def trim(value: str) -> str:
        """Trim whitespace."""
        return value.strip() if value else ""
    
    @staticmethod
    def date_to_iso(value: datetime | str) -> str:
        """Convert date to ISO format."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value
    
    @staticmethod
    def iso_to_date(value: str) -> datetime | None:
        """Convert ISO string to datetime."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    @staticmethod
    def number_to_string(value: int | float) -> str:
        """Convert number to string."""
        return str(value) if value is not None else ""
    
    @staticmethod
    def string_to_number(value: str) -> float | None:
        """Convert string to number."""
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    @staticmethod
    def boolean_to_string(value: bool) -> str:
        """Convert boolean to Y/N."""
        return "Y" if value else "N"
    
    @staticmethod
    def string_to_boolean(value: str) -> bool:
        """Convert Y/N to boolean."""
        return value.upper() in ("Y", "YES", "TRUE", "1")
    
    @staticmethod
    def normalize_phone(value: str) -> str:
        """Normalize phone number format."""
        if not value:
            return ""
        # Remove all non-digits
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return digits
    
    @staticmethod
    def morocco_ice_format(value: str) -> str:
        """Format Morocco ICE number."""
        if not value:
            return ""
        # ICE format: 15 digits
        digits = re.sub(r"\D", "", value)
        return digits.zfill(15)[:15]


# =============================================================================
# ERP INTEGRATION SERVICE
# =============================================================================


class ERPIntegrationService:
    """
    Bi-directional ERP integration service.
    
    Provides:
    - Master data synchronization
    - Transactional synchronization
    - Semantic field mapping
    - Reconciliation queue
    - Circuit breaker patterns
    - Webhook handling
    """
    
    # Default mapping templates for common ERP systems
    DEFAULT_FIELD_MAPPINGS = {
        ERPSystem.SAP: {
            EntityType.CUSTOMER: [
                ("KUNNR", "erp_customer_id", MappingType.DIRECT),
                ("NAME1", "name", MappingType.DIRECT),
                ("STRAS", "address_line1", MappingType.DIRECT),
                ("ORT01", "city", MappingType.DIRECT),
                ("PSTLZ", "postal_code", MappingType.DIRECT),
                ("LAND1", "country_code", MappingType.DIRECT),
                ("TELF1", "phone", MappingType.TRANSFORM),
            ],
            EntityType.SUPPLIER: [
                ("LIFNR", "erp_supplier_id", MappingType.DIRECT),
                ("NAME1", "name", MappingType.DIRECT),
                ("STRAS", "address_line1", MappingType.DIRECT),
                ("WAERS", "currency", MappingType.DIRECT),
            ],
            EntityType.PART: [
                ("MATNR", "erp_part_id", MappingType.DIRECT),
                ("MAKTX", "description", MappingType.DIRECT),
                ("MEINS", "base_uom", MappingType.LOOKUP),
                ("MTART", "material_type", MappingType.LOOKUP),
            ],
        },
        ERPSystem.ORACLE: {
            EntityType.CUSTOMER: [
                ("CUSTOMER_ID", "erp_customer_id", MappingType.DIRECT),
                ("CUSTOMER_NAME", "name", MappingType.DIRECT),
                ("ADDRESS1", "address_line1", MappingType.DIRECT),
                ("CITY", "city", MappingType.DIRECT),
            ],
        },
    }
    
    def __init__(
        self,
        erp_system: ERPSystem,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.erp_system = erp_system
        self.base_url = base_url
        self.api_key = api_key
        
        # Storage
        self._entity_mappings: dict[str, EntityMapping] = {}
        self._uom_conversions: dict[str, UoMConversion] = {}
        self._tax_codes: dict[str, TaxCode] = {}
        self._sync_records: list[SyncRecord] = []
        self._reconciliation_queue: list[ReconciliationItem] = []
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._webhooks: dict[str, WebhookConfig] = {}
        self._sync_jobs: dict[str, SyncJob] = {}
        
        # Transformer
        self._transformer = FieldTransformer()
        self._transform_functions: dict[str, Callable] = {
            "uppercase": self._transformer.uppercase,
            "lowercase": self._transformer.lowercase,
            "trim": self._transformer.trim,
            "date_to_iso": self._transformer.date_to_iso,
            "iso_to_date": self._transformer.iso_to_date,
            "number_to_string": self._transformer.number_to_string,
            "string_to_number": self._transformer.string_to_number,
            "boolean_to_string": self._transformer.boolean_to_string,
            "string_to_boolean": self._transformer.string_to_boolean,
            "normalize_phone": self._transformer.normalize_phone,
            "morocco_ice_format": self._transformer.morocco_ice_format,
        }
        
        # Lookup tables for field mappings
        self._lookup_tables: dict[str, dict[str, str]] = {}
        
        # Statistics
        self._statistics: dict[EntityType, SyncStatistics] = {}
        
        # Initialize default circuit breaker
        self._init_default_circuit_breaker()
    
    def _init_default_circuit_breaker(self) -> None:
        """Initialize default circuit breaker for the ERP system."""
        breaker = CircuitBreaker(
            id=f"cb_{self.erp_system.value}_default",
            name=f"Default {self.erp_system.value} Circuit Breaker",
            erp_system=self.erp_system,
        )
        self._circuit_breakers[breaker.id] = breaker
    
    # =========================================================================
    # FIELD MAPPING MANAGEMENT
    # =========================================================================
    
    def register_entity_mapping(
        self,
        entity_type: EntityType,
        erp_entity_name: str,
        sensei_entity_name: str,
        field_mappings: list[FieldMapping] | None = None,
        sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
    ) -> EntityMapping:
        """Register an entity mapping configuration."""
        mapping_id = f"em_{entity_type.value}_{self.erp_system.value}"
        
        mapping = EntityMapping(
            id=mapping_id,
            entity_type=entity_type,
            erp_system=self.erp_system,
            erp_entity_name=erp_entity_name,
            sensei_entity_name=sensei_entity_name,
            field_mappings=field_mappings or [],
            sync_direction=sync_direction,
        )
        
        self._entity_mappings[mapping_id] = mapping
        logger.info(f"Registered entity mapping: {mapping_id}")
        return mapping
    
    def add_field_mapping(
        self,
        entity_type: EntityType,
        source_field: str,
        target_field: str,
        mapping_type: MappingType = MappingType.DIRECT,
        transform_function: str | None = None,
        lookup_table: str | None = None,
        default_value: Any = None,
        is_required: bool = False,
        validation_regex: str | None = None,
    ) -> FieldMapping:
        """Add a field mapping to an entity."""
        mapping_id = f"fm_{source_field}_{target_field}"
        
        field_map = FieldMapping(
            id=mapping_id,
            source_field=source_field,
            target_field=target_field,
            mapping_type=mapping_type,
            transform_function=transform_function,
            lookup_table=lookup_table,
            default_value=default_value,
            is_required=is_required,
            validation_regex=validation_regex,
        )
        
        # Find entity mapping and add field
        entity_mapping_id = f"em_{entity_type.value}_{self.erp_system.value}"
        if entity_mapping_id in self._entity_mappings:
            self._entity_mappings[entity_mapping_id].field_mappings.append(field_map)
        
        return field_map
    
    def get_entity_mapping(self, entity_type: EntityType) -> EntityMapping | None:
        """Get entity mapping configuration."""
        mapping_id = f"em_{entity_type.value}_{self.erp_system.value}"
        return self._entity_mappings.get(mapping_id)
    
    def get_all_entity_mappings(self) -> list[EntityMapping]:
        """Get all entity mappings."""
        return list(self._entity_mappings.values())
    
    def register_lookup_table(
        self,
        table_name: str,
        mappings: dict[str, str],
    ) -> None:
        """Register a lookup table for field transformations."""
        self._lookup_tables[table_name] = mappings
        logger.info(f"Registered lookup table: {table_name} with {len(mappings)} entries")
    
    def get_lookup_value(self, table_name: str, key: str) -> str | None:
        """Get a value from a lookup table."""
        table = self._lookup_tables.get(table_name, {})
        return table.get(key)
    
    # =========================================================================
    # UNIT OF MEASURE CONVERSION
    # =========================================================================
    
    def register_uom_conversion(
        self,
        from_uom: str,
        to_uom: str,
        conversion_factor: float,
        is_bidirectional: bool = True,
    ) -> UoMConversion:
        """Register a UoM conversion rule."""
        conversion_id = f"uom_{from_uom}_{to_uom}"
        
        conversion = UoMConversion(
            id=conversion_id,
            from_uom=from_uom,
            to_uom=to_uom,
            conversion_factor=conversion_factor,
            is_bidirectional=is_bidirectional,
            erp_system=self.erp_system,
        )
        
        self._uom_conversions[conversion_id] = conversion
        
        # If bidirectional, add reverse
        if is_bidirectional:
            reverse_id = f"uom_{to_uom}_{from_uom}"
            reverse = UoMConversion(
                id=reverse_id,
                from_uom=to_uom,
                to_uom=from_uom,
                conversion_factor=1.0 / conversion_factor,
                is_bidirectional=True,
                erp_system=self.erp_system,
            )
            self._uom_conversions[reverse_id] = reverse
        
        return conversion
    
    def convert_uom(
        self,
        value: float,
        from_uom: str,
        to_uom: str,
    ) -> float | None:
        """Convert a value between units of measure."""
        if from_uom == to_uom:
            return value
        
        conversion_id = f"uom_{from_uom}_{to_uom}"
        conversion = self._uom_conversions.get(conversion_id)
        
        if not conversion:
            logger.warning(f"No UoM conversion found: {from_uom} -> {to_uom}")
            return None
        
        return value * conversion.conversion_factor
    
    def get_all_uom_conversions(self) -> list[UoMConversion]:
        """Get all UoM conversions."""
        return list(self._uom_conversions.values())
    
    # =========================================================================
    # TAX CODE MANAGEMENT (Morocco ICE/IF)
    # =========================================================================
    
    def register_tax_code(
        self,
        code: str,
        description: str,
        rate: float,
        tax_type: str,
        erp_code: str | None = None,
    ) -> TaxCode:
        """Register a tax code for Morocco compliance."""
        tax = TaxCode(
            id=f"tax_{code}",
            code=code,
            description=description,
            rate=rate,
            tax_type=tax_type,
            erp_code=erp_code,
        )
        
        self._tax_codes[tax.id] = tax
        logger.info(f"Registered tax code: {code} ({rate}%)")
        return tax
    
    def get_tax_code(self, code: str) -> TaxCode | None:
        """Get a tax code by code."""
        return self._tax_codes.get(f"tax_{code}")
    
    def get_tax_rate(self, code: str) -> float:
        """Get the tax rate for a code."""
        tax = self.get_tax_code(code)
        return tax.rate if tax else 0.0
    
    def calculate_tax(self, amount: float, tax_code: str) -> float:
        """Calculate tax amount."""
        rate = self.get_tax_rate(tax_code)
        return amount * (rate / 100.0)
    
    def get_all_tax_codes(self) -> list[TaxCode]:
        """Get all tax codes."""
        return list(self._tax_codes.values())
    
    # =========================================================================
    # DATA TRANSFORMATION
    # =========================================================================
    
    def transform_field(
        self,
        value: Any,
        field_mapping: FieldMapping,
    ) -> Any:
        """Transform a field value according to mapping rules."""
        if value is None:
            return field_mapping.default_value
        
        result = value
        
        # Apply transformation function
        if field_mapping.mapping_type == MappingType.TRANSFORM:
            if field_mapping.transform_function:
                func = self._transform_functions.get(field_mapping.transform_function)
                if func:
                    result = func(value)
        
        # Apply lookup
        elif field_mapping.mapping_type == MappingType.LOOKUP:
            if field_mapping.lookup_table:
                lookup_result = self.get_lookup_value(
                    field_mapping.lookup_table,
                    str(value),
                )
                result = lookup_result if lookup_result else field_mapping.default_value
        
        # Validate if regex provided
        if field_mapping.validation_regex and result:
            if not re.match(field_mapping.validation_regex, str(result)):
                logger.warning(
                    f"Validation failed for {field_mapping.target_field}: "
                    f"'{result}' does not match '{field_mapping.validation_regex}'"
                )
                if field_mapping.is_required:
                    raise ValueError(
                        f"Required field {field_mapping.target_field} "
                        f"failed validation"
                    )
        
        return result
    
    def transform_entity(
        self,
        entity_type: EntityType,
        source_data: dict[str, Any],
        direction: SyncDirection = SyncDirection.INBOUND,
    ) -> dict[str, Any]:
        """Transform an entire entity according to mapping rules."""
        mapping = self.get_entity_mapping(entity_type)
        if not mapping:
            logger.warning(f"No mapping found for {entity_type.value}")
            return source_data
        
        result: dict[str, Any] = {}
        
        for field_map in mapping.field_mappings:
            # Determine source and target based on direction
            if direction == SyncDirection.INBOUND:
                source_key = field_map.source_field
                target_key = field_map.target_field
            else:
                source_key = field_map.target_field
                target_key = field_map.source_field
            
            source_value = source_data.get(source_key)
            
            # Check required fields
            if field_map.is_required and source_value is None:
                raise ValueError(f"Required field missing: {source_key}")
            
            # Transform
            transformed = self.transform_field(source_value, field_map)
            result[target_key] = transformed
        
        return result
    
    def compute_data_hash(self, data: dict[str, Any]) -> str:
        """Compute a hash of the data for change detection."""
        # Sort keys for consistent hashing
        sorted_items = sorted(data.items())
        data_str = str(sorted_items)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    # =========================================================================
    # SYNCHRONIZATION
    # =========================================================================
    
    def sync_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
        data: dict[str, Any],
        direction: SyncDirection = SyncDirection.OUTBOUND,
        erp_id: str | None = None,
    ) -> SyncRecord:
        """Synchronize a single entity."""
        # Check circuit breaker
        breaker = self._get_circuit_breaker(entity_type)
        if breaker.state == CircuitState.OPEN:
            return self._create_failed_sync_record(
                entity_type,
                entity_id,
                direction,
                "Circuit breaker is OPEN",
            )
        
        started_at = datetime.now(timezone.utc)
        record_id = str(uuid4())
        
        try:
            # Transform data
            transformed = self.transform_entity(entity_type, data, direction)
            data_hash = self.compute_data_hash(transformed)
            
            # Check if data has changed
            last_record = self._get_last_sync_record(entity_type, entity_id)
            if last_record and last_record.data_hash == data_hash:
                return SyncRecord(
                    id=record_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    erp_id=erp_id,
                    direction=direction,
                    status=SyncStatus.SKIPPED,
                    data_hash=data_hash,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    metadata={"reason": "No changes detected"},
                )
            
            # Simulate API call (in real implementation, this would call the ERP API)
            # For now, we mark it as completed
            record = SyncRecord(
                id=record_id,
                entity_type=entity_type,
                entity_id=entity_id,
                erp_id=erp_id or f"ERP_{entity_id}",
                direction=direction,
                status=SyncStatus.COMPLETED,
                data_hash=data_hash,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                metadata={"transformed_data": transformed},
            )
            
            self._sync_records.append(record)
            self._record_success(breaker)
            self._update_statistics(entity_type, record)
            
            logger.info(
                f"Synced {entity_type.value} {entity_id} "
                f"({direction.value}) - {record.status.value}"
            )
            
            return record
            
        except Exception as e:
            self._record_failure(breaker)
            record = self._create_failed_sync_record(
                entity_type,
                entity_id,
                direction,
                str(e),
            )
            self._sync_records.append(record)
            self._update_statistics(entity_type, record)
            return record
    
    def sync_batch(
        self,
        entity_type: EntityType,
        entities: list[tuple[str, dict[str, Any]]],
        direction: SyncDirection = SyncDirection.OUTBOUND,
    ) -> list[SyncRecord]:
        """Synchronize a batch of entities."""
        results = []
        
        for entity_id, data in entities:
            record = self.sync_entity(entity_type, entity_id, data, direction)
            results.append(record)
            
            # Check circuit breaker after each sync
            breaker = self._get_circuit_breaker(entity_type)
            if breaker.state == CircuitState.OPEN:
                # Mark remaining as failed
                for remaining_id, _ in entities[len(results):]:
                    failed = self._create_failed_sync_record(
                        entity_type,
                        remaining_id,
                        direction,
                        "Circuit breaker opened during batch",
                    )
                    results.append(failed)
                break
        
        return results
    
    def _get_last_sync_record(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> SyncRecord | None:
        """Get the last sync record for an entity."""
        for record in reversed(self._sync_records):
            if (
                record.entity_type == entity_type
                and record.entity_id == entity_id
                and record.status == SyncStatus.COMPLETED
            ):
                return record
        return None
    
    def _create_failed_sync_record(
        self,
        entity_type: EntityType,
        entity_id: str,
        direction: SyncDirection,
        error_message: str,
    ) -> SyncRecord:
        """Create a failed sync record."""
        return SyncRecord(
            id=str(uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            erp_id=None,
            direction=direction,
            status=SyncStatus.FAILED,
            data_hash="",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            error_message=error_message,
        )
    
    def get_sync_records(
        self,
        entity_type: EntityType | None = None,
        status: SyncStatus | None = None,
        since: datetime | None = None,
    ) -> list[SyncRecord]:
        """Get sync records with optional filters."""
        records = self._sync_records
        
        if entity_type:
            records = [r for r in records if r.entity_type == entity_type]
        
        if status:
            records = [r for r in records if r.status == status]
        
        if since:
            records = [r for r in records if r.started_at >= since]
        
        return records
    
    def get_sync_statistics(self, entity_type: EntityType) -> SyncStatistics:
        """Get synchronization statistics for an entity type."""
        return self._statistics.get(entity_type, SyncStatistics())
    
    def _update_statistics(
        self,
        entity_type: EntityType,
        record: SyncRecord,
    ) -> None:
        """Update statistics after a sync."""
        if entity_type not in self._statistics:
            self._statistics[entity_type] = SyncStatistics()
        
        stats = self._statistics[entity_type]
        stats.total_synced += 1
        
        if record.status == SyncStatus.COMPLETED:
            stats.successful += 1
        elif record.status == SyncStatus.FAILED:
            stats.failed += 1
        elif record.status == SyncStatus.CONFLICT:
            stats.conflicts += 1
        elif record.status == SyncStatus.SKIPPED:
            stats.skipped += 1
        
        stats.last_sync_at = record.started_at
        
        # Calculate error rate
        if stats.total_synced > 0:
            stats.error_rate = stats.failed / stats.total_synced
    
    # =========================================================================
    # RECONCILIATION QUEUE
    # =========================================================================
    
    def add_to_reconciliation_queue(
        self,
        entity_type: EntityType,
        sensei_id: str,
        erp_id: str,
        conflict_type: str,
        sensei_data: dict[str, Any],
        erp_data: dict[str, Any],
        priority: int = 5,
    ) -> ReconciliationItem:
        """Add an item to the reconciliation queue."""
        # Calculate differences
        differences = []
        all_keys = set(sensei_data.keys()) | set(erp_data.keys())
        for key in all_keys:
            sensei_val = sensei_data.get(key)
            erp_val = erp_data.get(key)
            if sensei_val != erp_val:
                differences.append(key)
        
        item = ReconciliationItem(
            id=str(uuid4()),
            entity_type=entity_type,
            sensei_id=sensei_id,
            erp_id=erp_id,
            conflict_type=conflict_type,
            sensei_data=sensei_data,
            erp_data=erp_data,
            differences=differences,
            priority=priority,
        )
        
        self._reconciliation_queue.append(item)
        logger.info(
            f"Added to reconciliation queue: {entity_type.value} "
            f"({sensei_id} vs {erp_id})"
        )
        
        return item
    
    def get_reconciliation_queue(
        self,
        status: ReconciliationStatus | None = None,
        entity_type: EntityType | None = None,
    ) -> list[ReconciliationItem]:
        """Get items from the reconciliation queue."""
        items = self._reconciliation_queue
        
        if status:
            items = [i for i in items if i.status == status]
        
        if entity_type:
            items = [i for i in items if i.entity_type == entity_type]
        
        # Sort by priority (lower = higher priority)
        return sorted(items, key=lambda x: (x.priority, x.created_at))
    
    def resolve_reconciliation_item(
        self,
        item_id: str,
        resolution: str,  # "use_sensei", "use_erp", "merge", "skip"
        resolved_by: str,
        notes: str | None = None,
    ) -> ReconciliationItem | None:
        """Resolve a reconciliation item."""
        for item in self._reconciliation_queue:
            if item.id == item_id:
                item.status = ReconciliationStatus.RESOLVED
                item.resolved_at = datetime.now(timezone.utc)
                item.resolved_by = resolved_by
                item.resolution_notes = notes or f"Resolved using: {resolution}"
                
                logger.info(
                    f"Resolved reconciliation item {item_id} "
                    f"using {resolution} by {resolved_by}"
                )
                
                return item
        
        return None
    
    def get_pending_reconciliation_count(self) -> int:
        """Get count of pending reconciliation items."""
        return len([
            i for i in self._reconciliation_queue
            if i.status == ReconciliationStatus.PENDING
        ])
    
    # =========================================================================
    # CIRCUIT BREAKER
    # =========================================================================
    
    def _get_circuit_breaker(
        self,
        entity_type: EntityType | None = None,
    ) -> CircuitBreaker:
        """Get the circuit breaker for an entity type."""
        if entity_type:
            breaker_id = f"cb_{self.erp_system.value}_{entity_type.value}"
            if breaker_id in self._circuit_breakers:
                return self._circuit_breakers[breaker_id]
        
        # Return default breaker
        default_id = f"cb_{self.erp_system.value}_default"
        return self._circuit_breakers[default_id]
    
    def register_circuit_breaker(
        self,
        entity_type: EntityType,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        error_rate_threshold: float = 0.1,
        timeout_seconds: int = 60,
    ) -> CircuitBreaker:
        """Register a circuit breaker for an entity type."""
        breaker_id = f"cb_{self.erp_system.value}_{entity_type.value}"
        
        breaker = CircuitBreaker(
            id=breaker_id,
            name=f"{entity_type.value} Circuit Breaker",
            erp_system=self.erp_system,
            entity_type=entity_type,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            error_rate_threshold=error_rate_threshold,
            timeout_seconds=timeout_seconds,
        )
        
        self._circuit_breakers[breaker_id] = breaker
        return breaker
    
    def get_circuit_breaker_state(
        self,
        entity_type: EntityType | None = None,
    ) -> CircuitState:
        """Get the current state of a circuit breaker."""
        breaker = self._get_circuit_breaker(entity_type)
        
        # Check if we should transition from OPEN to HALF_OPEN
        if breaker.state == CircuitState.OPEN:
            if breaker.last_failure_at:
                elapsed = (
                    datetime.now(timezone.utc) - breaker.last_failure_at
                ).total_seconds()
                if elapsed >= breaker.timeout_seconds:
                    breaker.state = CircuitState.HALF_OPEN
                    breaker.last_state_change = datetime.now(timezone.utc)
        
        return breaker.state
    
    def _record_success(self, breaker: CircuitBreaker) -> None:
        """Record a successful operation."""
        breaker.success_count += 1
        breaker.total_requests += 1
        
        if breaker.state == CircuitState.HALF_OPEN:
            if breaker.success_count >= breaker.success_threshold:
                breaker.state = CircuitState.CLOSED
                breaker.failure_count = 0
                breaker.last_state_change = datetime.now(timezone.utc)
                logger.info(f"Circuit breaker {breaker.id} CLOSED")
    
    def _record_failure(self, breaker: CircuitBreaker) -> None:
        """Record a failed operation."""
        breaker.failure_count += 1
        breaker.total_requests += 1
        breaker.last_failure_at = datetime.now(timezone.utc)
        
        # Check if we should open the circuit
        should_open = False
        
        if breaker.failure_count >= breaker.failure_threshold:
            should_open = True
        
        if breaker.total_requests >= 10:  # Minimum requests before checking error rate
            error_rate = breaker.failure_count / breaker.total_requests
            if error_rate >= breaker.error_rate_threshold:
                should_open = True
        
        if breaker.state == CircuitState.HALF_OPEN:
            should_open = True  # Any failure in half-open reopens
        
        if should_open:
            breaker.state = CircuitState.OPEN
            breaker.success_count = 0
            breaker.last_state_change = datetime.now(timezone.utc)
            logger.warning(f"Circuit breaker {breaker.id} OPENED")
    
    def reset_circuit_breaker(
        self,
        entity_type: EntityType | None = None,
    ) -> None:
        """Manually reset a circuit breaker."""
        breaker = self._get_circuit_breaker(entity_type)
        breaker.state = CircuitState.CLOSED
        breaker.failure_count = 0
        breaker.success_count = 0
        breaker.last_state_change = datetime.now(timezone.utc)
        logger.info(f"Circuit breaker {breaker.id} manually reset")
    
    def get_all_circuit_breakers(self) -> list[CircuitBreaker]:
        """Get all circuit breakers."""
        return list(self._circuit_breakers.values())
    
    # =========================================================================
    # WEBHOOK MANAGEMENT
    # =========================================================================
    
    def register_webhook(
        self,
        event_type: str,
        endpoint_url: str,
        secret_key: str,
        retry_count: int = 3,
    ) -> WebhookConfig:
        """Register a webhook for ERP events."""
        webhook_id = f"wh_{self.erp_system.value}_{event_type}"
        
        webhook = WebhookConfig(
            id=webhook_id,
            erp_system=self.erp_system,
            event_type=event_type,
            endpoint_url=endpoint_url,
            secret_key=secret_key,
            retry_count=retry_count,
        )
        
        self._webhooks[webhook_id] = webhook
        logger.info(f"Registered webhook: {event_type} -> {endpoint_url}")
        return webhook
    
    def get_webhook(self, event_type: str) -> WebhookConfig | None:
        """Get a webhook by event type."""
        webhook_id = f"wh_{self.erp_system.value}_{event_type}"
        return self._webhooks.get(webhook_id)
    
    def process_webhook_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: str,
    ) -> bool:
        """Process an incoming webhook event."""
        webhook = self.get_webhook(event_type)
        if not webhook:
            logger.warning(f"No webhook registered for event: {event_type}")
            return False
        
        # Verify signature (simplified)
        expected_signature = hashlib.sha256(
            (webhook.secret_key + str(payload)).encode()
        ).hexdigest()
        
        if signature != expected_signature:
            logger.warning(f"Webhook signature verification failed: {event_type}")
            webhook.failure_count += 1
            return False
        
        webhook.last_triggered = datetime.now(timezone.utc)
        logger.info(f"Processed webhook event: {event_type}")
        return True
    
    def get_all_webhooks(self) -> list[WebhookConfig]:
        """Get all webhooks."""
        return list(self._webhooks.values())
    
    # =========================================================================
    # SYNC JOB MANAGEMENT
    # =========================================================================
    
    def register_sync_job(
        self,
        name: str,
        entity_type: EntityType,
        direction: SyncDirection,
        schedule_cron: str,
    ) -> SyncJob:
        """Register a scheduled sync job."""
        job_id = f"job_{entity_type.value}_{direction.value}"
        
        job = SyncJob(
            id=job_id,
            name=name,
            entity_type=entity_type,
            direction=direction,
            schedule_cron=schedule_cron,
        )
        
        self._sync_jobs[job_id] = job
        logger.info(f"Registered sync job: {name} ({schedule_cron})")
        return job
    
    def get_sync_job(self, job_id: str) -> SyncJob | None:
        """Get a sync job by ID."""
        return self._sync_jobs.get(job_id)
    
    def get_all_sync_jobs(self) -> list[SyncJob]:
        """Get all sync jobs."""
        return list(self._sync_jobs.values())
    
    def update_sync_job_status(
        self,
        job_id: str,
        status: SyncStatus,
        records_processed: int = 0,
        records_failed: int = 0,
    ) -> SyncJob | None:
        """Update a sync job's status after execution."""
        job = self._sync_jobs.get(job_id)
        if job:
            job.last_run = datetime.now(timezone.utc)
            job.last_status = status
            job.records_processed = records_processed
            job.records_failed = records_failed
        return job
    
    # =========================================================================
    # TRANSACTIONAL SYNC (ERP-SPECIFIC)
    # =========================================================================
    
    def sync_sales_order(
        self,
        quote_id: str,
        quote_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync a quote/sales order to ERP."""
        return self.sync_entity(
            EntityType.SALES_ORDER,
            quote_id,
            quote_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_purchase_order(
        self,
        po_id: str,
        po_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync a purchase order to ERP."""
        return self.sync_entity(
            EntityType.PURCHASE_ORDER,
            po_id,
            po_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_goods_receipt(
        self,
        gr_id: str,
        gr_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync a goods receipt to ERP (triggers incoming inspection)."""
        return self.sync_entity(
            EntityType.GOODS_RECEIPT,
            gr_id,
            gr_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_inventory_movement(
        self,
        movement_id: str,
        movement_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync an inventory movement (Kanban replenishment)."""
        return self.sync_entity(
            EntityType.INVENTORY_MOVEMENT,
            movement_id,
            movement_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_work_order_completion(
        self,
        wo_id: str,
        wo_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync work order completion (labor booking, backflushing)."""
        return self.sync_entity(
            EntityType.WORK_ORDER,
            wo_id,
            wo_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_quality_cost(
        self,
        cost_id: str,
        cost_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync NC-related quality costs (Scrap/Rework)."""
        return self.sync_entity(
            EntityType.QUALITY_COST,
            cost_id,
            cost_data,
            SyncDirection.OUTBOUND,
        )
    
    def sync_employee_labor(
        self,
        labor_id: str,
        labor_data: dict[str, Any],
    ) -> SyncRecord:
        """Sync employee labor to ERP Payroll/Cost-Accounting."""
        return self.sync_entity(
            EntityType.EMPLOYEE_LABOR,
            labor_id,
            labor_data,
            SyncDirection.OUTBOUND,
        )
    
    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================
    
    def detect_conflicts(
        self,
        entity_type: EntityType,
        sensei_data: dict[str, Any],
        erp_data: dict[str, Any],
    ) -> list[str]:
        """Detect conflicts between Sensei and ERP data."""
        conflicts = []
        
        # Get field mappings for comparison
        mapping = self.get_entity_mapping(entity_type)
        if not mapping:
            return conflicts
        
        for field_map in mapping.field_mappings:
            sensei_val = sensei_data.get(field_map.target_field)
            erp_val = erp_data.get(field_map.source_field)
            
            # Transform ERP value for comparison
            transformed_erp = self.transform_field(erp_val, field_map)
            
            if sensei_val != transformed_erp:
                conflicts.append(field_map.target_field)
        
        return conflicts
    
    def check_revision_mismatch(
        self,
        entity_type: EntityType,
        sensei_revision: str,
        erp_revision: str,
    ) -> bool:
        """Check for BOM/Routing revision mismatch (hard-stop rule)."""
        if entity_type in (EntityType.BOM, EntityType.ROUTING):
            if sensei_revision != erp_revision:
                logger.error(
                    f"Revision mismatch detected: "
                    f"Sensei={sensei_revision}, ERP={erp_revision}"
                )
                return True
        return False
    
    # =========================================================================
    # HEALTH & DIAGNOSTICS
    # =========================================================================
    
    def get_integration_health(self) -> dict[str, Any]:
        """Get overall integration health status."""
        open_breakers = [
            b for b in self._circuit_breakers.values()
            if b.state == CircuitState.OPEN
        ]
        
        pending_reconciliation = self.get_pending_reconciliation_count()
        
        # Calculate overall error rate
        total_syncs = sum(s.total_synced for s in self._statistics.values())
        total_failures = sum(s.failed for s in self._statistics.values())
        overall_error_rate = (
            total_failures / total_syncs if total_syncs > 0 else 0.0
        )
        
        return {
            "status": "healthy" if not open_breakers else "degraded",
            "erp_system": self.erp_system.value,
            "circuit_breakers": {
                "total": len(self._circuit_breakers),
                "open": len(open_breakers),
                "open_list": [b.id for b in open_breakers],
            },
            "reconciliation_queue": {
                "pending": pending_reconciliation,
                "total": len(self._reconciliation_queue),
            },
            "sync_statistics": {
                "total_syncs": total_syncs,
                "successful": sum(s.successful for s in self._statistics.values()),
                "failed": total_failures,
                "error_rate": overall_error_rate,
            },
            "webhooks_active": len([w for w in self._webhooks.values() if w.is_active]),
            "sync_jobs_active": len([j for j in self._sync_jobs.values() if j.is_active]),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_erp_integration_service(
    erp_system: ERPSystem,
    base_url: str | None = None,
    api_key: str | None = None,
) -> ERPIntegrationService:
    """Factory function to create an ERP integration service."""
    service = ERPIntegrationService(erp_system, base_url, api_key)
    
    # Register default Morocco tax codes
    service.register_tax_code("VAT20", "Standard VAT", 20.0, "VAT")
    service.register_tax_code("VAT14", "Reduced VAT", 14.0, "VAT")
    service.register_tax_code("VAT10", "Reduced VAT", 10.0, "VAT")
    service.register_tax_code("VAT7", "Super Reduced VAT", 7.0, "VAT")
    service.register_tax_code("VAT0", "Zero Rate", 0.0, "VAT")
    
    # Register default UoM conversions
    service.register_uom_conversion("kg", "g", 1000.0)
    service.register_uom_conversion("m", "cm", 100.0)
    service.register_uom_conversion("l", "ml", 1000.0)
    service.register_uom_conversion("box", "ea", 12.0)  # Default box = 12 each
    
    return service
