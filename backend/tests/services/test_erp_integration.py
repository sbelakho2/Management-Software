"""
Tests for ERP Integration Layer Service.

Comprehensive tests covering:
- Field mapping and transformation
- Entity synchronization
- UoM conversions
- Tax code management
- Reconciliation queue
- Circuit breaker patterns
- Webhook handling
- Sync job management
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sensei.services.erp_integration import (
    ERPIntegrationService,
    ERPSystem,
    EntityType,
    SyncDirection,
    SyncStatus,
    ReconciliationStatus,
    CircuitState,
    MappingType,
    UoMType,
    FieldMapping,
    EntityMapping,
    UoMConversion,
    TaxCode,
    SyncRecord,
    ReconciliationItem,
    CircuitBreaker,
    WebhookConfig,
    SyncJob,
    SyncStatistics,
    FieldTransformer,
    create_erp_integration_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def erp_service():
    """Create an ERP integration service."""
    return ERPIntegrationService(ERPSystem.SAP, "https://sap.example.com", "api-key-123")


@pytest.fixture
def erp_service_with_factory():
    """Create an ERP service using factory function."""
    return create_erp_integration_service(ERPSystem.SAP)


@pytest.fixture
def sample_customer_data():
    """Sample customer data from ERP."""
    return {
        "KUNNR": "CUST001",
        "NAME1": "Acme Corporation",
        "STRAS": "123 Main Street",
        "ORT01": "Casablanca",
        "PSTLZ": "20000",
        "LAND1": "MA",
        "TELF1": "+212 522 123456",
    }


@pytest.fixture
def sample_sensei_customer():
    """Sample customer data in Sensei format."""
    return {
        "erp_customer_id": "CUST001",
        "name": "Acme Corporation",
        "address_line1": "123 Main Street",
        "city": "Casablanca",
        "postal_code": "20000",
        "country_code": "MA",
        "phone": "(212) 522-123456",
    }


@pytest.fixture
def field_transformer():
    """Create a field transformer."""
    return FieldTransformer()


# =============================================================================
# FIELD TRANSFORMER TESTS
# =============================================================================


class TestFieldTransformer:
    """Tests for FieldTransformer class."""
    
    def test_uppercase(self, field_transformer):
        """Test uppercase transformation."""
        assert field_transformer.uppercase("hello") == "HELLO"
        assert field_transformer.uppercase("") == ""
        assert field_transformer.uppercase(None) == ""
    
    def test_lowercase(self, field_transformer):
        """Test lowercase transformation."""
        assert field_transformer.lowercase("HELLO") == "hello"
        assert field_transformer.lowercase("MiXeD") == "mixed"
    
    def test_trim(self, field_transformer):
        """Test trim transformation."""
        assert field_transformer.trim("  hello  ") == "hello"
        assert field_transformer.trim("no spaces") == "no spaces"
    
    def test_date_to_iso(self, field_transformer):
        """Test date to ISO conversion."""
        dt = datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc)
        result = field_transformer.date_to_iso(dt)
        assert "2026-01-09" in result
    
    def test_iso_to_date(self, field_transformer):
        """Test ISO to date conversion."""
        result = field_transformer.iso_to_date("2026-01-09T12:00:00Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 9
    
    def test_iso_to_date_invalid(self, field_transformer):
        """Test ISO to date with invalid input."""
        assert field_transformer.iso_to_date("") is None
        assert field_transformer.iso_to_date("invalid") is None
    
    def test_number_to_string(self, field_transformer):
        """Test number to string conversion."""
        assert field_transformer.number_to_string(123) == "123"
        assert field_transformer.number_to_string(45.67) == "45.67"
        assert field_transformer.number_to_string(None) == ""
    
    def test_string_to_number(self, field_transformer):
        """Test string to number conversion."""
        assert field_transformer.string_to_number("123") == 123.0
        assert field_transformer.string_to_number("45.67") == 45.67
        assert field_transformer.string_to_number("") is None
        assert field_transformer.string_to_number("invalid") is None
    
    def test_boolean_to_string(self, field_transformer):
        """Test boolean to string conversion."""
        assert field_transformer.boolean_to_string(True) == "Y"
        assert field_transformer.boolean_to_string(False) == "N"
    
    def test_string_to_boolean(self, field_transformer):
        """Test string to boolean conversion."""
        assert field_transformer.string_to_boolean("Y") is True
        assert field_transformer.string_to_boolean("YES") is True
        assert field_transformer.string_to_boolean("true") is True
        assert field_transformer.string_to_boolean("1") is True
        assert field_transformer.string_to_boolean("N") is False
        assert field_transformer.string_to_boolean("NO") is False
    
    def test_normalize_phone(self, field_transformer):
        """Test phone number normalization."""
        assert field_transformer.normalize_phone("1234567890") == "(123) 456-7890"
        assert field_transformer.normalize_phone("123-456-7890") == "(123) 456-7890"
        assert field_transformer.normalize_phone("") == ""
    
    def test_morocco_ice_format(self, field_transformer):
        """Test Morocco ICE number formatting."""
        assert field_transformer.morocco_ice_format("123456789012345") == "123456789012345"
        assert field_transformer.morocco_ice_format("123") == "000000000000123"
        assert field_transformer.morocco_ice_format("") == ""


# =============================================================================
# ENTITY MAPPING TESTS
# =============================================================================


class TestEntityMapping:
    """Tests for entity mapping functionality."""
    
    def test_register_entity_mapping(self, erp_service):
        """Test registering an entity mapping."""
        mapping = erp_service.register_entity_mapping(
            EntityType.CUSTOMER,
            "KNA1",
            "customers",
            sync_direction=SyncDirection.BIDIRECTIONAL,
        )
        
        assert mapping.entity_type == EntityType.CUSTOMER
        assert mapping.erp_entity_name == "KNA1"
        assert mapping.sensei_entity_name == "customers"
        assert mapping.sync_direction == SyncDirection.BIDIRECTIONAL
        assert mapping.is_active is True
    
    def test_add_field_mapping(self, erp_service):
        """Test adding a field mapping."""
        erp_service.register_entity_mapping(
            EntityType.CUSTOMER,
            "KNA1",
            "customers",
        )
        
        field_map = erp_service.add_field_mapping(
            EntityType.CUSTOMER,
            "KUNNR",
            "erp_customer_id",
            MappingType.DIRECT,
            is_required=True,
        )
        
        assert field_map.source_field == "KUNNR"
        assert field_map.target_field == "erp_customer_id"
        assert field_map.is_required is True
    
    def test_add_transform_field_mapping(self, erp_service):
        """Test adding a transform field mapping."""
        erp_service.register_entity_mapping(
            EntityType.CUSTOMER,
            "KNA1",
            "customers",
        )
        
        field_map = erp_service.add_field_mapping(
            EntityType.CUSTOMER,
            "NAME1",
            "name",
            MappingType.TRANSFORM,
            transform_function="uppercase",
        )
        
        assert field_map.mapping_type == MappingType.TRANSFORM
        assert field_map.transform_function == "uppercase"
    
    def test_get_entity_mapping(self, erp_service):
        """Test getting an entity mapping."""
        erp_service.register_entity_mapping(
            EntityType.SUPPLIER,
            "LFA1",
            "suppliers",
        )
        
        mapping = erp_service.get_entity_mapping(EntityType.SUPPLIER)
        assert mapping is not None
        assert mapping.entity_type == EntityType.SUPPLIER
    
    def test_get_nonexistent_mapping(self, erp_service):
        """Test getting a non-existent mapping."""
        mapping = erp_service.get_entity_mapping(EntityType.PART)
        assert mapping is None
    
    def test_get_all_entity_mappings(self, erp_service):
        """Test getting all entity mappings."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        erp_service.register_entity_mapping(EntityType.SUPPLIER, "LFA1", "suppliers")
        
        mappings = erp_service.get_all_entity_mappings()
        assert len(mappings) == 2


# =============================================================================
# LOOKUP TABLE TESTS
# =============================================================================


class TestLookupTables:
    """Tests for lookup table functionality."""
    
    def test_register_lookup_table(self, erp_service):
        """Test registering a lookup table."""
        erp_service.register_lookup_table(
            "material_types",
            {"ROH": "Raw Material", "HALB": "Semi-Finished", "FERT": "Finished"},
        )
        
        assert erp_service.get_lookup_value("material_types", "ROH") == "Raw Material"
        assert erp_service.get_lookup_value("material_types", "FERT") == "Finished"
    
    def test_lookup_missing_value(self, erp_service):
        """Test looking up a missing value."""
        erp_service.register_lookup_table("types", {"A": "Type A"})
        
        assert erp_service.get_lookup_value("types", "X") is None
    
    def test_lookup_missing_table(self, erp_service):
        """Test looking up from a missing table."""
        assert erp_service.get_lookup_value("nonexistent", "key") is None


# =============================================================================
# UOM CONVERSION TESTS
# =============================================================================


class TestUoMConversion:
    """Tests for Unit of Measure conversion."""
    
    def test_register_uom_conversion(self, erp_service):
        """Test registering a UoM conversion."""
        conversion = erp_service.register_uom_conversion("kg", "lb", 2.20462)
        
        assert conversion.from_uom == "kg"
        assert conversion.to_uom == "lb"
        assert conversion.conversion_factor == 2.20462
    
    def test_bidirectional_uom_conversion(self, erp_service):
        """Test bidirectional UoM conversion is auto-created."""
        erp_service.register_uom_conversion("kg", "lb", 2.20462, is_bidirectional=True)
        
        # Check both directions exist
        assert erp_service.convert_uom(1.0, "kg", "lb") == pytest.approx(2.20462)
        assert erp_service.convert_uom(2.20462, "lb", "kg") == pytest.approx(1.0)
    
    def test_convert_uom(self, erp_service):
        """Test UoM conversion."""
        erp_service.register_uom_conversion("m", "ft", 3.28084)
        
        result = erp_service.convert_uom(10.0, "m", "ft")
        assert result == pytest.approx(32.8084)
    
    def test_convert_same_uom(self, erp_service):
        """Test converting to the same UoM."""
        result = erp_service.convert_uom(100.0, "kg", "kg")
        assert result == 100.0
    
    def test_convert_missing_uom(self, erp_service):
        """Test converting with missing conversion."""
        result = erp_service.convert_uom(100.0, "xyz", "abc")
        assert result is None
    
    def test_factory_default_uom_conversions(self, erp_service_with_factory):
        """Test factory creates default UoM conversions."""
        service = erp_service_with_factory
        
        assert service.convert_uom(1.0, "kg", "g") == 1000.0
        assert service.convert_uom(1.0, "m", "cm") == 100.0
        assert service.convert_uom(1.0, "l", "ml") == 1000.0


# =============================================================================
# TAX CODE TESTS
# =============================================================================


class TestTaxCodes:
    """Tests for tax code management."""
    
    def test_register_tax_code(self, erp_service):
        """Test registering a tax code."""
        tax = erp_service.register_tax_code(
            "ICE",
            "Internal Consumption Tax",
            5.0,
            "ICE",
            "ICE001",
        )
        
        assert tax.code == "ICE"
        assert tax.rate == 5.0
        assert tax.tax_type == "ICE"
    
    def test_get_tax_code(self, erp_service):
        """Test getting a tax code."""
        erp_service.register_tax_code("VAT20", "Standard VAT", 20.0, "VAT")
        
        tax = erp_service.get_tax_code("VAT20")
        assert tax is not None
        assert tax.rate == 20.0
    
    def test_get_tax_rate(self, erp_service):
        """Test getting tax rate."""
        erp_service.register_tax_code("VAT14", "Reduced VAT", 14.0, "VAT")
        
        rate = erp_service.get_tax_rate("VAT14")
        assert rate == 14.0
    
    def test_get_missing_tax_rate(self, erp_service):
        """Test getting missing tax rate returns 0."""
        rate = erp_service.get_tax_rate("NONEXISTENT")
        assert rate == 0.0
    
    def test_calculate_tax(self, erp_service):
        """Test tax calculation."""
        erp_service.register_tax_code("VAT20", "Standard VAT", 20.0, "VAT")
        
        tax_amount = erp_service.calculate_tax(100.0, "VAT20")
        assert tax_amount == 20.0
    
    def test_factory_default_tax_codes(self, erp_service_with_factory):
        """Test factory creates default Morocco tax codes."""
        service = erp_service_with_factory
        
        assert service.get_tax_rate("VAT20") == 20.0
        assert service.get_tax_rate("VAT14") == 14.0
        assert service.get_tax_rate("VAT10") == 10.0
        assert service.get_tax_rate("VAT7") == 7.0
        assert service.get_tax_rate("VAT0") == 0.0


# =============================================================================
# DATA TRANSFORMATION TESTS
# =============================================================================


class TestDataTransformation:
    """Tests for data transformation."""
    
    def test_transform_field_direct(self, erp_service):
        """Test direct field transformation."""
        field_map = FieldMapping(
            id="fm_1",
            source_field="NAME1",
            target_field="name",
            mapping_type=MappingType.DIRECT,
        )
        
        result = erp_service.transform_field("Test Company", field_map)
        assert result == "Test Company"
    
    def test_transform_field_with_function(self, erp_service):
        """Test field transformation with function."""
        field_map = FieldMapping(
            id="fm_1",
            source_field="NAME1",
            target_field="name",
            mapping_type=MappingType.TRANSFORM,
            transform_function="uppercase",
        )
        
        result = erp_service.transform_field("test company", field_map)
        assert result == "TEST COMPANY"
    
    def test_transform_field_with_lookup(self, erp_service):
        """Test field transformation with lookup."""
        erp_service.register_lookup_table(
            "countries",
            {"MA": "Morocco", "FR": "France", "US": "United States"},
        )
        
        field_map = FieldMapping(
            id="fm_1",
            source_field="LAND1",
            target_field="country",
            mapping_type=MappingType.LOOKUP,
            lookup_table="countries",
        )
        
        result = erp_service.transform_field("MA", field_map)
        assert result == "Morocco"
    
    def test_transform_field_null_with_default(self, erp_service):
        """Test field transformation with null value and default."""
        field_map = FieldMapping(
            id="fm_1",
            source_field="OPTIONAL",
            target_field="optional",
            mapping_type=MappingType.DIRECT,
            default_value="N/A",
        )
        
        result = erp_service.transform_field(None, field_map)
        assert result == "N/A"
    
    def test_transform_field_validation_success(self, erp_service):
        """Test field validation with valid value."""
        field_map = FieldMapping(
            id="fm_1",
            source_field="PSTLZ",
            target_field="postal_code",
            mapping_type=MappingType.DIRECT,
            validation_regex=r"^\d{5}$",
        )
        
        result = erp_service.transform_field("20000", field_map)
        assert result == "20000"
    
    def test_transform_field_validation_failure_required(self, erp_service):
        """Test field validation failure for required field."""
        field_map = FieldMapping(
            id="fm_1",
            source_field="PSTLZ",
            target_field="postal_code",
            mapping_type=MappingType.DIRECT,
            validation_regex=r"^\d{5}$",
            is_required=True,
        )
        
        with pytest.raises(ValueError, match="failed validation"):
            erp_service.transform_field("invalid", field_map)
    
    def test_transform_entity(self, erp_service, sample_customer_data):
        """Test full entity transformation."""
        # Set up mapping
        erp_service.register_entity_mapping(
            EntityType.CUSTOMER,
            "KNA1",
            "customers",
        )
        erp_service.add_field_mapping(
            EntityType.CUSTOMER, "KUNNR", "erp_customer_id", MappingType.DIRECT
        )
        erp_service.add_field_mapping(
            EntityType.CUSTOMER, "NAME1", "name", MappingType.DIRECT
        )
        erp_service.add_field_mapping(
            EntityType.CUSTOMER, "ORT01", "city", MappingType.DIRECT
        )
        
        result = erp_service.transform_entity(
            EntityType.CUSTOMER,
            sample_customer_data,
            SyncDirection.INBOUND,
        )
        
        assert result["erp_customer_id"] == "CUST001"
        assert result["name"] == "Acme Corporation"
        assert result["city"] == "Casablanca"
    
    def test_compute_data_hash(self, erp_service):
        """Test data hash computation."""
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}  # Same data, different order
        data3 = {"a": 1, "b": 3}  # Different data
        
        hash1 = erp_service.compute_data_hash(data1)
        hash2 = erp_service.compute_data_hash(data2)
        hash3 = erp_service.compute_data_hash(data3)
        
        assert hash1 == hash2  # Same data should have same hash
        assert hash1 != hash3  # Different data should have different hash


# =============================================================================
# SYNCHRONIZATION TESTS
# =============================================================================


class TestSynchronization:
    """Tests for entity synchronization."""
    
    def test_sync_entity_success(self, erp_service):
        """Test successful entity synchronization."""
        erp_service.register_entity_mapping(
            EntityType.CUSTOMER,
            "KNA1",
            "customers",
        )
        
        record = erp_service.sync_entity(
            EntityType.CUSTOMER,
            "cust_123",
            {"name": "Test Customer"},
            SyncDirection.OUTBOUND,
        )
        
        assert record.status == SyncStatus.COMPLETED
        assert record.entity_id == "cust_123"
        assert record.direction == SyncDirection.OUTBOUND
    
    def test_sync_entity_generates_erp_id(self, erp_service):
        """Test sync generates ERP ID if not provided."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        
        record = erp_service.sync_entity(
            EntityType.CUSTOMER,
            "cust_456",
            {"name": "Another Customer"},
        )
        
        assert record.erp_id is not None
        assert "ERP_cust_456" in record.erp_id
    
    def test_sync_entity_skips_unchanged(self, erp_service):
        """Test sync skips unchanged data."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        data = {"name": "Same Data"}
        
        # First sync
        record1 = erp_service.sync_entity(
            EntityType.CUSTOMER, "cust_789", data
        )
        assert record1.status == SyncStatus.COMPLETED
        
        # Second sync with same data
        record2 = erp_service.sync_entity(
            EntityType.CUSTOMER, "cust_789", data
        )
        assert record2.status == SyncStatus.SKIPPED
    
    def test_sync_batch(self, erp_service):
        """Test batch synchronization."""
        erp_service.register_entity_mapping(EntityType.SUPPLIER, "LFA1", "suppliers")
        
        entities = [
            ("sup_1", {"name": "Supplier 1"}),
            ("sup_2", {"name": "Supplier 2"}),
            ("sup_3", {"name": "Supplier 3"}),
        ]
        
        records = erp_service.sync_batch(
            EntityType.SUPPLIER,
            entities,
            SyncDirection.OUTBOUND,
        )
        
        assert len(records) == 3
        assert all(r.status == SyncStatus.COMPLETED for r in records)
    
    def test_get_sync_records(self, erp_service):
        """Test getting sync records with filters."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        erp_service.register_entity_mapping(EntityType.SUPPLIER, "LFA1", "suppliers")
        
        # Create some records
        erp_service.sync_entity(EntityType.CUSTOMER, "c1", {"name": "C1"})
        erp_service.sync_entity(EntityType.SUPPLIER, "s1", {"name": "S1"})
        erp_service.sync_entity(EntityType.CUSTOMER, "c2", {"name": "C2"})
        
        # Filter by entity type
        customer_records = erp_service.get_sync_records(entity_type=EntityType.CUSTOMER)
        assert len(customer_records) == 2
    
    def test_get_sync_statistics(self, erp_service):
        """Test sync statistics."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        
        # Sync some entities
        for i in range(5):
            erp_service.sync_entity(EntityType.CUSTOMER, f"c{i}", {"name": f"C{i}"})
        
        stats = erp_service.get_sync_statistics(EntityType.CUSTOMER)
        assert stats.total_synced == 5
        assert stats.successful == 5
        assert stats.error_rate == 0.0


# =============================================================================
# RECONCILIATION QUEUE TESTS
# =============================================================================


class TestReconciliationQueue:
    """Tests for reconciliation queue."""
    
    def test_add_to_reconciliation_queue(self, erp_service):
        """Test adding item to reconciliation queue."""
        item = erp_service.add_to_reconciliation_queue(
            EntityType.CUSTOMER,
            "sensei_123",
            "erp_456",
            "data_mismatch",
            {"name": "Sensei Name"},
            {"name": "ERP Name"},
            priority=3,
        )
        
        assert item.entity_type == EntityType.CUSTOMER
        assert item.conflict_type == "data_mismatch"
        assert "name" in item.differences
        assert item.priority == 3
    
    def test_get_reconciliation_queue(self, erp_service):
        """Test getting reconciliation queue."""
        erp_service.add_to_reconciliation_queue(
            EntityType.CUSTOMER, "s1", "e1", "mismatch",
            {"a": 1}, {"a": 2}, priority=5,
        )
        erp_service.add_to_reconciliation_queue(
            EntityType.CUSTOMER, "s2", "e2", "mismatch",
            {"b": 1}, {"b": 2}, priority=1,
        )
        
        queue = erp_service.get_reconciliation_queue()
        assert len(queue) == 2
        # Should be sorted by priority (1 before 5)
        assert queue[0].priority == 1
    
    def test_filter_reconciliation_queue_by_status(self, erp_service):
        """Test filtering queue by status."""
        erp_service.add_to_reconciliation_queue(
            EntityType.CUSTOMER, "s1", "e1", "mismatch",
            {"a": 1}, {"a": 2},
        )
        
        pending = erp_service.get_reconciliation_queue(
            status=ReconciliationStatus.PENDING
        )
        assert len(pending) == 1
        
        resolved = erp_service.get_reconciliation_queue(
            status=ReconciliationStatus.RESOLVED
        )
        assert len(resolved) == 0
    
    def test_resolve_reconciliation_item(self, erp_service):
        """Test resolving a reconciliation item."""
        item = erp_service.add_to_reconciliation_queue(
            EntityType.SUPPLIER, "s1", "e1", "mismatch",
            {"x": 1}, {"x": 2},
        )
        
        resolved = erp_service.resolve_reconciliation_item(
            item.id,
            "use_sensei",
            "user@example.com",
            "Sensei data is more recent",
        )
        
        assert resolved is not None
        assert resolved.status == ReconciliationStatus.RESOLVED
        assert resolved.resolved_by == "user@example.com"
        assert resolved.resolution_notes == "Sensei data is more recent"
    
    def test_resolve_nonexistent_item(self, erp_service):
        """Test resolving non-existent item returns None."""
        result = erp_service.resolve_reconciliation_item(
            "nonexistent", "use_erp", "user@example.com"
        )
        assert result is None
    
    def test_get_pending_reconciliation_count(self, erp_service):
        """Test pending count."""
        for i in range(3):
            erp_service.add_to_reconciliation_queue(
                EntityType.PART, f"s{i}", f"e{i}", "mismatch",
                {"val": i}, {"val": i + 1},
            )
        
        count = erp_service.get_pending_reconciliation_count()
        assert count == 3


# =============================================================================
# CIRCUIT BREAKER TESTS
# =============================================================================


class TestCircuitBreaker:
    """Tests for circuit breaker functionality."""
    
    def test_default_circuit_breaker_created(self, erp_service):
        """Test default circuit breaker is created."""
        breakers = erp_service.get_all_circuit_breakers()
        assert len(breakers) == 1
        assert breakers[0].state == CircuitState.CLOSED
    
    def test_register_circuit_breaker(self, erp_service):
        """Test registering a circuit breaker."""
        breaker = erp_service.register_circuit_breaker(
            EntityType.CUSTOMER,
            failure_threshold=3,
            error_rate_threshold=0.2,
            timeout_seconds=30,
        )
        
        assert breaker.entity_type == EntityType.CUSTOMER
        assert breaker.failure_threshold == 3
        assert breaker.state == CircuitState.CLOSED
    
    def test_get_circuit_breaker_state(self, erp_service):
        """Test getting circuit breaker state."""
        state = erp_service.get_circuit_breaker_state()
        assert state == CircuitState.CLOSED
    
    def test_circuit_breaker_opens_on_failures(self, erp_service):
        """Test circuit breaker opens after failures."""
        erp_service.register_circuit_breaker(
            EntityType.CUSTOMER,
            failure_threshold=2,
        )
        
        # Get the breaker and simulate failures
        breaker = erp_service._get_circuit_breaker(EntityType.CUSTOMER)
        erp_service._record_failure(breaker)
        assert breaker.state == CircuitState.CLOSED
        
        erp_service._record_failure(breaker)
        assert breaker.state == CircuitState.OPEN
    
    def test_circuit_breaker_half_open_after_timeout(self, erp_service):
        """Test circuit breaker transitions to half-open after timeout."""
        erp_service.register_circuit_breaker(
            EntityType.SUPPLIER,
            failure_threshold=1,
            timeout_seconds=0,  # Immediate timeout for testing
        )
        
        breaker = erp_service._get_circuit_breaker(EntityType.SUPPLIER)
        erp_service._record_failure(breaker)
        assert breaker.state == CircuitState.OPEN
        
        # Check state - should transition to half-open
        breaker.last_failure_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        state = erp_service.get_circuit_breaker_state(EntityType.SUPPLIER)
        assert state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_on_success(self, erp_service):
        """Test circuit breaker closes on successes in half-open."""
        erp_service.register_circuit_breaker(
            EntityType.PART,
            failure_threshold=1,
            success_threshold=2,
        )
        
        breaker = erp_service._get_circuit_breaker(EntityType.PART)
        
        # Open the breaker
        erp_service._record_failure(breaker)
        breaker.state = CircuitState.HALF_OPEN  # Manually set for test
        
        # Record successes
        erp_service._record_success(breaker)
        assert breaker.state == CircuitState.HALF_OPEN
        
        erp_service._record_success(breaker)
        assert breaker.state == CircuitState.CLOSED
    
    def test_reset_circuit_breaker(self, erp_service):
        """Test manual circuit breaker reset."""
        breaker = erp_service._get_circuit_breaker()
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 10
        
        erp_service.reset_circuit_breaker()
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_sync_blocked_when_circuit_open(self, erp_service):
        """Test sync is blocked when circuit is open."""
        erp_service.register_entity_mapping(EntityType.BOM, "MAST", "boms")
        erp_service.register_circuit_breaker(EntityType.BOM, failure_threshold=1)
        
        # Open the breaker
        breaker = erp_service._get_circuit_breaker(EntityType.BOM)
        erp_service._record_failure(breaker)
        
        # Try to sync
        record = erp_service.sync_entity(EntityType.BOM, "bom_1", {"name": "BOM 1"})
        
        assert record.status == SyncStatus.FAILED
        assert "Circuit breaker is OPEN" in record.error_message


# =============================================================================
# WEBHOOK TESTS
# =============================================================================


class TestWebhooks:
    """Tests for webhook management."""
    
    def test_register_webhook(self, erp_service):
        """Test registering a webhook."""
        webhook = erp_service.register_webhook(
            "customer_created",
            "https://api.sensei.local/webhooks/customer",
            "secret123",
            retry_count=5,
        )
        
        assert webhook.event_type == "customer_created"
        assert webhook.endpoint_url == "https://api.sensei.local/webhooks/customer"
        assert webhook.retry_count == 5
    
    def test_get_webhook(self, erp_service):
        """Test getting a webhook."""
        erp_service.register_webhook(
            "order_updated",
            "https://api.example.com/hook",
            "secret",
        )
        
        webhook = erp_service.get_webhook("order_updated")
        assert webhook is not None
        assert webhook.event_type == "order_updated"
    
    def test_get_nonexistent_webhook(self, erp_service):
        """Test getting non-existent webhook."""
        webhook = erp_service.get_webhook("nonexistent")
        assert webhook is None
    
    def test_process_webhook_event_success(self, erp_service):
        """Test processing webhook event with valid signature."""
        import hashlib
        
        secret = "mysecret"
        erp_service.register_webhook("test_event", "https://api.example.com", secret)
        
        payload = {"data": "test"}
        signature = hashlib.sha256((secret + str(payload)).encode()).hexdigest()
        
        result = erp_service.process_webhook_event("test_event", payload, signature)
        assert result is True
    
    def test_process_webhook_event_invalid_signature(self, erp_service):
        """Test processing webhook event with invalid signature."""
        erp_service.register_webhook("test_event", "https://api.example.com", "secret")
        
        result = erp_service.process_webhook_event(
            "test_event", {"data": "test"}, "invalid_signature"
        )
        assert result is False
    
    def test_process_webhook_unregistered_event(self, erp_service):
        """Test processing unregistered webhook event."""
        result = erp_service.process_webhook_event(
            "unknown_event", {"data": "test"}, "signature"
        )
        assert result is False


# =============================================================================
# SYNC JOB TESTS
# =============================================================================


class TestSyncJobs:
    """Tests for sync job management."""
    
    def test_register_sync_job(self, erp_service):
        """Test registering a sync job."""
        job = erp_service.register_sync_job(
            "Daily Customer Sync",
            EntityType.CUSTOMER,
            SyncDirection.BIDIRECTIONAL,
            "0 2 * * *",  # 2 AM daily
        )
        
        assert job.name == "Daily Customer Sync"
        assert job.schedule_cron == "0 2 * * *"
        assert job.is_active is True
    
    def test_get_sync_job(self, erp_service):
        """Test getting a sync job."""
        erp_service.register_sync_job(
            "Hourly Parts Sync",
            EntityType.PART,
            SyncDirection.INBOUND,
            "0 * * * *",
        )
        
        job = erp_service.get_sync_job("job_part_inbound")
        assert job is not None
        assert job.entity_type == EntityType.PART
    
    def test_get_all_sync_jobs(self, erp_service):
        """Test getting all sync jobs."""
        erp_service.register_sync_job("J1", EntityType.CUSTOMER, SyncDirection.OUTBOUND, "* * * * *")
        erp_service.register_sync_job("J2", EntityType.SUPPLIER, SyncDirection.INBOUND, "* * * * *")
        
        jobs = erp_service.get_all_sync_jobs()
        assert len(jobs) == 2
    
    def test_update_sync_job_status(self, erp_service):
        """Test updating sync job status."""
        erp_service.register_sync_job(
            "Test Job",
            EntityType.BOM,
            SyncDirection.OUTBOUND,
            "0 0 * * *",
        )
        
        updated = erp_service.update_sync_job_status(
            "job_bom_outbound",
            SyncStatus.COMPLETED,
            records_processed=100,
            records_failed=2,
        )
        
        assert updated is not None
        assert updated.last_status == SyncStatus.COMPLETED
        assert updated.records_processed == 100
        assert updated.records_failed == 2


# =============================================================================
# TRANSACTIONAL SYNC TESTS
# =============================================================================


class TestTransactionalSync:
    """Tests for transactional synchronization helpers."""
    
    def test_sync_sales_order(self, erp_service):
        """Test sales order sync."""
        erp_service.register_entity_mapping(EntityType.SALES_ORDER, "VBAK", "quotes")
        
        record = erp_service.sync_sales_order("q_123", {"total": 1000.0})
        assert record.entity_type == EntityType.SALES_ORDER
        assert record.status == SyncStatus.COMPLETED
    
    def test_sync_purchase_order(self, erp_service):
        """Test purchase order sync."""
        erp_service.register_entity_mapping(EntityType.PURCHASE_ORDER, "EKKO", "purchase_orders")
        
        record = erp_service.sync_purchase_order("po_456", {"supplier": "SUP001"})
        assert record.entity_type == EntityType.PURCHASE_ORDER
    
    def test_sync_goods_receipt(self, erp_service):
        """Test goods receipt sync."""
        erp_service.register_entity_mapping(EntityType.GOODS_RECEIPT, "MKPF", "goods_receipts")
        
        record = erp_service.sync_goods_receipt("gr_789", {"quantity": 100})
        assert record.entity_type == EntityType.GOODS_RECEIPT
    
    def test_sync_inventory_movement(self, erp_service):
        """Test inventory movement sync."""
        erp_service.register_entity_mapping(EntityType.INVENTORY_MOVEMENT, "MSEG", "movements")
        
        record = erp_service.sync_inventory_movement("mov_001", {"from": "WH01", "to": "WH02"})
        assert record.entity_type == EntityType.INVENTORY_MOVEMENT
    
    def test_sync_work_order_completion(self, erp_service):
        """Test work order completion sync."""
        erp_service.register_entity_mapping(EntityType.WORK_ORDER, "AFKO", "work_orders")
        
        record = erp_service.sync_work_order_completion("wo_111", {"labor_hours": 8.5})
        assert record.entity_type == EntityType.WORK_ORDER
    
    def test_sync_quality_cost(self, erp_service):
        """Test quality cost sync."""
        erp_service.register_entity_mapping(EntityType.QUALITY_COST, "QCOST", "quality_costs")
        
        record = erp_service.sync_quality_cost("qc_222", {"scrap_cost": 500.0})
        assert record.entity_type == EntityType.QUALITY_COST
    
    def test_sync_employee_labor(self, erp_service):
        """Test employee labor sync."""
        erp_service.register_entity_mapping(EntityType.EMPLOYEE_LABOR, "CATS", "labor_entries")
        
        record = erp_service.sync_employee_labor("lab_333", {"hours": 40.0})
        assert record.entity_type == EntityType.EMPLOYEE_LABOR


# =============================================================================
# CONFLICT DETECTION TESTS
# =============================================================================


class TestConflictDetection:
    """Tests for conflict detection."""
    
    def test_detect_conflicts(self, erp_service):
        """Test conflict detection."""
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        erp_service.add_field_mapping(EntityType.CUSTOMER, "NAME1", "name", MappingType.DIRECT)
        erp_service.add_field_mapping(EntityType.CUSTOMER, "ORT01", "city", MappingType.DIRECT)
        
        sensei_data = {"name": "Company A", "city": "Casablanca"}
        erp_data = {"NAME1": "Company A", "ORT01": "Rabat"}  # Different city
        
        conflicts = erp_service.detect_conflicts(EntityType.CUSTOMER, sensei_data, erp_data)
        
        assert "city" in conflicts
        assert "name" not in conflicts
    
    def test_check_revision_mismatch_bom(self, erp_service):
        """Test BOM revision mismatch detection."""
        result = erp_service.check_revision_mismatch(
            EntityType.BOM,
            "REV_A",
            "REV_B",
        )
        assert result is True
    
    def test_check_revision_match(self, erp_service):
        """Test matching revisions."""
        result = erp_service.check_revision_mismatch(
            EntityType.BOM,
            "REV_A",
            "REV_A",
        )
        assert result is False
    
    def test_check_revision_non_bom_entity(self, erp_service):
        """Test revision check for non-BOM entity."""
        result = erp_service.check_revision_mismatch(
            EntityType.CUSTOMER,
            "REV_A",
            "REV_B",
        )
        assert result is False  # Only BOM/ROUTING have revision checks


# =============================================================================
# HEALTH & DIAGNOSTICS TESTS
# =============================================================================


class TestHealthDiagnostics:
    """Tests for health and diagnostics."""
    
    def test_get_integration_health_healthy(self, erp_service):
        """Test healthy integration status."""
        health = erp_service.get_integration_health()
        
        assert health["status"] == "healthy"
        assert health["erp_system"] == "sap"
        assert health["circuit_breakers"]["open"] == 0
    
    def test_get_integration_health_degraded(self, erp_service):
        """Test degraded integration status."""
        # Open a circuit breaker
        breaker = erp_service._get_circuit_breaker()
        breaker.state = CircuitState.OPEN
        
        health = erp_service.get_integration_health()
        
        assert health["status"] == "degraded"
        assert health["circuit_breakers"]["open"] == 1
    
    def test_get_integration_health_with_data(self, erp_service):
        """Test health with sync data."""
        # Create some data
        erp_service.register_entity_mapping(EntityType.CUSTOMER, "KNA1", "customers")
        for i in range(10):
            erp_service.sync_entity(EntityType.CUSTOMER, f"c{i}", {"name": f"C{i}"})
        
        erp_service.add_to_reconciliation_queue(
            EntityType.CUSTOMER, "s1", "e1", "mismatch", {"a": 1}, {"a": 2}
        )
        
        health = erp_service.get_integration_health()
        
        assert health["sync_statistics"]["total_syncs"] == 10
        assert health["reconciliation_queue"]["pending"] == 1


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_erp_integration_service(self):
        """Test factory creates service with defaults."""
        service = create_erp_integration_service(ERPSystem.ORACLE)
        
        assert service.erp_system == ERPSystem.ORACLE
        
        # Check default tax codes
        assert len(service.get_all_tax_codes()) == 5
        
        # Check default UoM conversions
        conversions = service.get_all_uom_conversions()
        assert len(conversions) >= 6  # 3 bidirectional = 6 total
    
    def test_create_service_with_custom_url(self):
        """Test factory with custom URL."""
        service = create_erp_integration_service(
            ERPSystem.DYNAMICS,
            base_url="https://dynamics.example.com",
            api_key="key123",
        )
        
        assert service.base_url == "https://dynamics.example.com"
        assert service.api_key == "key123"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Tests for data model classes."""
    
    def test_field_mapping_creation(self):
        """Test FieldMapping creation."""
        mapping = FieldMapping(
            id="fm_1",
            source_field="SRC",
            target_field="TGT",
            mapping_type=MappingType.DIRECT,
        )
        assert mapping.is_required is False
        assert mapping.default_value is None
    
    def test_entity_mapping_creation(self):
        """Test EntityMapping creation."""
        mapping = EntityMapping(
            id="em_1",
            entity_type=EntityType.CUSTOMER,
            erp_system=ERPSystem.SAP,
            erp_entity_name="KNA1",
            sensei_entity_name="customers",
        )
        assert mapping.is_active is True
        assert len(mapping.field_mappings) == 0
    
    def test_sync_record_creation(self):
        """Test SyncRecord creation."""
        record = SyncRecord(
            id="sr_1",
            entity_type=EntityType.SUPPLIER,
            entity_id="sup_1",
            erp_id="ERP_SUP_1",
            direction=SyncDirection.OUTBOUND,
            status=SyncStatus.COMPLETED,
            data_hash="abc123",
            started_at=datetime.now(timezone.utc),
        )
        assert record.retry_count == 0
        assert record.error_message is None
    
    def test_reconciliation_item_creation(self):
        """Test ReconciliationItem creation."""
        item = ReconciliationItem(
            id="ri_1",
            entity_type=EntityType.PART,
            sensei_id="s_1",
            erp_id="e_1",
            conflict_type="data_mismatch",
            sensei_data={"a": 1},
            erp_data={"a": 2},
            differences=["a"],
        )
        assert item.status == ReconciliationStatus.PENDING
        assert item.priority == 5
    
    def test_circuit_breaker_creation(self):
        """Test CircuitBreaker creation."""
        breaker = CircuitBreaker(
            id="cb_1",
            name="Test Breaker",
            erp_system=ERPSystem.SAP,
        )
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    def test_webhook_config_creation(self):
        """Test WebhookConfig creation."""
        webhook = WebhookConfig(
            id="wh_1",
            erp_system=ERPSystem.ORACLE,
            event_type="order_created",
            endpoint_url="https://example.com/hook",
            secret_key="secret",
        )
        assert webhook.is_active is True
        assert webhook.failure_count == 0
    
    def test_sync_job_creation(self):
        """Test SyncJob creation."""
        job = SyncJob(
            id="job_1",
            name="Daily Sync",
            entity_type=EntityType.CUSTOMER,
            direction=SyncDirection.BIDIRECTIONAL,
            schedule_cron="0 0 * * *",
        )
        assert job.is_active is True
        assert job.last_run is None
    
    def test_sync_statistics_creation(self):
        """Test SyncStatistics creation."""
        stats = SyncStatistics()
        assert stats.total_synced == 0
        assert stats.error_rate == 0.0


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Tests for enum values."""
    
    def test_erp_system_values(self):
        """Test ERPSystem enum values."""
        assert ERPSystem.SAP.value == "sap"
        assert ERPSystem.ORACLE.value == "oracle"
        assert ERPSystem.DYNAMICS.value == "dynamics"
    
    def test_entity_type_values(self):
        """Test EntityType enum values."""
        assert EntityType.CUSTOMER.value == "customer"
        assert EntityType.BOM.value == "bom"
        assert EntityType.WORK_ORDER.value == "work_order"
    
    def test_sync_direction_values(self):
        """Test SyncDirection enum values."""
        assert SyncDirection.INBOUND.value == "inbound"
        assert SyncDirection.OUTBOUND.value == "outbound"
        assert SyncDirection.BIDIRECTIONAL.value == "bidirectional"
    
    def test_circuit_state_values(self):
        """Test CircuitState enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"
    
    def test_mapping_type_values(self):
        """Test MappingType enum values."""
        assert MappingType.DIRECT.value == "direct"
        assert MappingType.TRANSFORM.value == "transform"
        assert MappingType.LOOKUP.value == "lookup"
