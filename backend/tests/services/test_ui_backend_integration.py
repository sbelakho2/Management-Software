"""
Tests for UI/Backend Integration Service.

Tests error mapping, schema export, action auditing, and connection health.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sensei.services.utils.ui_backend_integration import (
    # Enums
    ErrorCategory,
    RecoveryAction,
    FieldType,
    ConnectionState,
    # Data models
    ErrorMapping,
    SchemaField,
    ValidationSchema,
    ActionAuditEntry,
    ConnectionHealthStatus,
    # Classes
    ErrorMappingService,
    ValidationSchemaExportService,
    ActionAuditService,
    ConnectionHealthService,
    UIBackendIntegration,
    # Factory functions
    create_ui_backend_integration,
    create_error_mapping_service,
    create_schema_export_service,
    create_action_audit_service,
    create_connection_health_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def error_mapping_service() -> ErrorMappingService:
    """Create error mapping service."""
    return create_error_mapping_service()


@pytest.fixture
def schema_export_service() -> ValidationSchemaExportService:
    """Create schema export service."""
    return create_schema_export_service()


@pytest.fixture
def action_audit_service() -> ActionAuditService:
    """Create action audit service."""
    return create_action_audit_service()


@pytest.fixture
def connection_health_service() -> ConnectionHealthService:
    """Create connection health service."""
    return create_connection_health_service()


@pytest.fixture
def integration() -> UIBackendIntegration:
    """Create UI/Backend Integration."""
    return create_ui_backend_integration()


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.SERVER_ERROR.value == "server_error"
    
    def test_recovery_action_values(self):
        """Test RecoveryAction enum values."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.LOGIN.value == "login"
        assert RecoveryAction.FIX_INPUT.value == "fix_input"
        assert RecoveryAction.CONTACT_ADMIN.value == "contact_admin"
    
    def test_field_type_values(self):
        """Test FieldType enum values."""
        assert FieldType.STRING.value == "string"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.UUID.value == "uuid"
        assert FieldType.EMAIL.value == "email"
        assert FieldType.ARRAY.value == "array"
    
    def test_connection_state_values(self):
        """Test ConnectionState enum values."""
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.DISCONNECTED.value == "disconnected"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_error_mapping_creation(self):
        """Test ErrorMapping creation."""
        mapping = ErrorMapping(
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION,
            title="Test Error",
            message="This is a test error",
            recovery_actions=[RecoveryAction.FIX_INPUT],
            recovery_instructions="Fix the input",
        )
        
        assert mapping.error_code == "TEST_ERROR"
        assert mapping.category == ErrorCategory.VALIDATION
    
    def test_error_mapping_to_dict(self):
        """Test ErrorMapping to_dict conversion."""
        mapping = ErrorMapping(
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION,
            title="Test Error",
            message="This is a test error",
            recovery_actions=[RecoveryAction.FIX_INPUT, RecoveryAction.RETRY],
            recovery_instructions="Fix the input",
            support_link="/support",
        )
        
        result = mapping.to_dict()
        
        assert result["error_code"] == "TEST_ERROR"
        assert result["category"] == "validation"
        assert len(result["recovery_actions"]) == 2
        assert result["support_link"] == "/support"
    
    def test_schema_field_to_typescript(self):
        """Test SchemaField TypeScript generation."""
        field = SchemaField(
            name="email",
            field_type=FieldType.EMAIL,
            required=True,
        )
        
        ts = field.to_typescript()
        assert ts == "email: string"
    
    def test_schema_field_optional_typescript(self):
        """Test optional field TypeScript generation."""
        field = SchemaField(
            name="phone",
            field_type=FieldType.STRING,
            required=False,
            nullable=True,
        )
        
        ts = field.to_typescript()
        assert "phone?" in ts
        assert "| null" in ts
    
    def test_schema_field_enum_typescript(self):
        """Test enum field TypeScript generation."""
        field = SchemaField(
            name="priority",
            field_type=FieldType.ENUM,
            enum_values=["low", "medium", "high"],
        )
        
        ts = field.to_typescript()
        assert '"low"' in ts
        assert '"medium"' in ts
        assert '"high"' in ts
    
    def test_schema_field_to_zod(self):
        """Test SchemaField Zod generation."""
        field = SchemaField(
            name="name",
            field_type=FieldType.STRING,
            min_length=2,
            max_length=100,
        )
        
        zod = field.to_zod()
        assert "z.string()" in zod
        assert ".min(2)" in zod
        assert ".max(100)" in zod
    
    def test_schema_field_array_zod(self):
        """Test array field Zod generation."""
        field = SchemaField(
            name="tags",
            field_type=FieldType.ARRAY,
            array_item_type=FieldType.STRING,
            required=False,
        )
        
        zod = field.to_zod()
        assert "z.array(z.string())" in zod
        assert ".optional()" in zod
    
    def test_validation_schema_creation(self):
        """Test ValidationSchema creation."""
        schema = ValidationSchema(
            name="TestSchema",
            description="Test schema",
            fields=[
                SchemaField("name", FieldType.STRING),
                SchemaField("age", FieldType.INTEGER, required=False),
            ],
        )
        
        assert schema.name == "TestSchema"
        assert len(schema.fields) == 2
    
    def test_validation_schema_to_typescript_interface(self):
        """Test TypeScript interface generation."""
        schema = ValidationSchema(
            name="User",
            description="User schema",
            fields=[
                SchemaField("id", FieldType.UUID),
                SchemaField("email", FieldType.EMAIL),
                SchemaField("name", FieldType.STRING),
            ],
        )
        
        ts = schema.to_typescript_interface()
        
        assert "export interface User {" in ts
        assert "id: string;" in ts
        assert "email: string;" in ts
    
    def test_validation_schema_to_zod_schema(self):
        """Test Zod schema generation."""
        schema = ValidationSchema(
            name="User",
            description="User schema",
            fields=[
                SchemaField("email", FieldType.EMAIL),
                SchemaField("name", FieldType.STRING, min_length=1),
            ],
        )
        
        zod = schema.to_zod_schema()
        
        assert "export const UserSchema = z.object({" in zod
        assert "z.string().email()" in zod
        assert "export type User = z.infer<typeof UserSchema>;" in zod
    
    def test_action_audit_entry_creation(self):
        """Test ActionAuditEntry creation."""
        entry = ActionAuditEntry(
            entry_id="audit_001",
            action_type="create",
            entity_type="rfq",
            entity_id="rfq_001",
            user_id="user_001",
            timestamp=datetime.now(timezone.utc),
            ui_context={"page": "/rfqs"},
            backend_response={"id": "rfq_001"},
            duration_ms=150,
            success=True,
        )
        
        assert entry.success
        assert entry.duration_ms == 150
    
    def test_connection_health_status_healthy(self):
        """Test ConnectionHealthStatus is_healthy check."""
        status = ConnectionHealthStatus(
            connection_id="conn_001",
            connection_type="sse",
            state=ConnectionState.CONNECTED,
            last_ping=datetime.now(timezone.utc),
            last_message=datetime.now(timezone.utc),
            reconnect_attempts=0,
            latency_ms=50.0,
        )
        
        assert status.is_healthy
    
    def test_connection_health_status_unhealthy(self):
        """Test ConnectionHealthStatus unhealthy cases."""
        # Disconnected
        status1 = ConnectionHealthStatus(
            connection_id="conn_001",
            connection_type="sse",
            state=ConnectionState.DISCONNECTED,
            last_ping=None,
            last_message=None,
            reconnect_attempts=3,
        )
        assert not status1.is_healthy
        
        # High latency
        status2 = ConnectionHealthStatus(
            connection_id="conn_002",
            connection_type="websocket",
            state=ConnectionState.CONNECTED,
            last_ping=datetime.now(timezone.utc),
            last_message=datetime.now(timezone.utc),
            reconnect_attempts=0,
            latency_ms=1500.0,  # > 1000ms threshold
        )
        assert not status2.is_healthy


# =============================================================================
# ERROR MAPPING SERVICE TESTS
# =============================================================================


class TestErrorMappingService:
    """Test ErrorMappingService."""
    
    def test_service_initialization(self, error_mapping_service):
        """Test service initializes with default mappings."""
        assert len(error_mapping_service.mappings) > 0
    
    def test_default_mappings_exist(self, error_mapping_service):
        """Test default mappings are registered."""
        assert "UNAUTHORIZED" in error_mapping_service.mappings
        assert "FORBIDDEN" in error_mapping_service.mappings
        assert "NOT_FOUND" in error_mapping_service.mappings
        assert "VALIDATION_ERROR" in error_mapping_service.mappings
        assert "INTERNAL_SERVER_ERROR" in error_mapping_service.mappings
    
    def test_register_mapping(self, error_mapping_service):
        """Test registering a new mapping."""
        mapping = ErrorMapping(
            error_code="CUSTOM_ERROR",
            category=ErrorCategory.BUSINESS_RULE,
            title="Custom Error",
            message="Custom error message",
            recovery_actions=[RecoveryAction.GO_BACK],
            recovery_instructions="Go back",
        )
        
        error_mapping_service.register(mapping)
        
        assert "CUSTOM_ERROR" in error_mapping_service.mappings
    
    def test_get_mapping_existing(self, error_mapping_service):
        """Test getting an existing mapping."""
        mapping = error_mapping_service.get_mapping("NOT_FOUND")
        
        assert mapping.error_code == "NOT_FOUND"
        assert mapping.category == ErrorCategory.NOT_FOUND
    
    def test_get_mapping_fallback(self, error_mapping_service):
        """Test fallback for unknown error code."""
        mapping = error_mapping_service.get_mapping("UNKNOWN_ERROR")
        
        assert mapping.error_code == "UNKNOWN_ERROR"
        assert mapping.category == ErrorCategory.SERVER_ERROR
    
    def test_get_mapping_pattern_based(self, error_mapping_service):
        """Test pattern-based error code matching."""
        mapping = error_mapping_service.get_mapping("BUSINESS_RULE_VIOLATION:MAX_QUANTITY")
        
        assert mapping.category == ErrorCategory.BUSINESS_RULE
    
    def test_get_user_friendly_error(self, error_mapping_service):
        """Test getting user-friendly error response."""
        response = error_mapping_service.get_user_friendly_error(
            "VALIDATION_ERROR",
            http_status=400,
            details={"field_errors": {"email": "Invalid email format"}},
        )
        
        assert response["error_code"] == "VALIDATION_ERROR"
        assert response["http_status"] == 400
        assert "email" in response["field_errors"]
    
    def test_get_all_mappings(self, error_mapping_service):
        """Test getting all mappings for frontend sync."""
        mappings = error_mapping_service.get_all_mappings()
        
        assert len(mappings) > 0
        assert all("error_code" in m for m in mappings)


# =============================================================================
# VALIDATION SCHEMA EXPORT SERVICE TESTS
# =============================================================================


class TestValidationSchemaExportService:
    """Test ValidationSchemaExportService."""
    
    def test_service_initialization(self, schema_export_service):
        """Test service initializes with core schemas."""
        assert len(schema_export_service.schemas) > 0
    
    def test_core_schemas_exist(self, schema_export_service):
        """Test core schemas are registered."""
        assert "RFQCreate" in schema_export_service.schemas
        assert "QuoteCreate" in schema_export_service.schemas
        assert "CustomerCreate" in schema_export_service.schemas
        assert "UserCreate" in schema_export_service.schemas
    
    def test_register_schema(self, schema_export_service):
        """Test registering a new schema."""
        schema = ValidationSchema(
            name="CustomSchema",
            description="Custom schema",
            fields=[
                SchemaField("field1", FieldType.STRING),
            ],
        )
        
        schema_export_service.register(schema)
        
        assert "CustomSchema" in schema_export_service.schemas
    
    def test_get_schema(self, schema_export_service):
        """Test getting a schema."""
        schema = schema_export_service.get_schema("RFQCreate")
        
        assert schema is not None
        assert schema.name == "RFQCreate"
        assert len(schema.fields) > 0
    
    def test_export_typescript(self, schema_export_service):
        """Test exporting TypeScript interfaces."""
        ts = schema_export_service.export_typescript(["RFQCreate"])
        
        assert "export interface RFQCreate {" in ts
        assert "title:" in ts
    
    def test_export_zod(self, schema_export_service):
        """Test exporting Zod schemas."""
        zod = schema_export_service.export_zod(["RFQCreate"])
        
        assert 'import { z } from "zod"' in zod
        assert "export const RFQCreateSchema = z.object({" in zod
    
    def test_export_json_schema(self, schema_export_service):
        """Test exporting JSON Schema."""
        json_schema = schema_export_service.export_json_schema("RFQCreate")
        
        assert json_schema is not None
        assert json_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert json_schema["title"] == "RFQCreate"
        assert "properties" in json_schema
        assert "required" in json_schema
    
    def test_get_schema_list(self, schema_export_service):
        """Test getting list of available schemas."""
        schema_list = schema_export_service.get_schema_list()
        
        assert len(schema_list) > 0
        assert all("name" in s and "description" in s for s in schema_list)


# =============================================================================
# ACTION AUDIT SERVICE TESTS
# =============================================================================


class TestActionAuditService:
    """Test ActionAuditService."""
    
    def test_start_action(self, action_audit_service):
        """Test starting an action."""
        action_id = action_audit_service.start_action(
            action_type="create",
            entity_type="rfq",
            entity_id="rfq_001",
            user_id="user_001",
            ui_context={"page": "/rfqs/new"},
        )
        
        assert action_id
        assert action_id in action_audit_service.pending_actions
    
    def test_complete_action_success(self, action_audit_service):
        """Test completing a successful action."""
        action_id = action_audit_service.start_action(
            action_type="create",
            entity_type="rfq",
            entity_id="rfq_001",
            user_id="user_001",
        )
        
        entry = action_audit_service.complete_action(
            action_id,
            success=True,
            backend_response={"id": "rfq_001"},
        )
        
        assert entry is not None
        assert entry.success
        assert entry.duration_ms >= 0
        assert action_id not in action_audit_service.pending_actions
    
    def test_complete_action_failure(self, action_audit_service):
        """Test completing a failed action."""
        action_id = action_audit_service.start_action(
            action_type="update",
            entity_type="quote",
            entity_id="quote_001",
            user_id="user_001",
        )
        
        entry = action_audit_service.complete_action(
            action_id,
            success=False,
            error_code="VALIDATION_ERROR",
        )
        
        assert entry is not None
        assert not entry.success
        assert entry.error_code == "VALIDATION_ERROR"
    
    def test_get_entries_filtered(self, action_audit_service):
        """Test getting filtered entries."""
        # Create some entries
        for i in range(3):
            action_id = action_audit_service.start_action(
                action_type="create",
                entity_type="rfq",
                entity_id=f"rfq_{i}",
                user_id="user_001",
            )
            action_audit_service.complete_action(action_id, success=True)
        
        action_id = action_audit_service.start_action(
            action_type="create",
            entity_type="quote",
            entity_id="quote_001",
            user_id="user_001",
        )
        action_audit_service.complete_action(action_id, success=True)
        
        # Filter by entity type
        rfq_entries = action_audit_service.get_entries(entity_type="rfq")
        assert len(rfq_entries) == 3
        
        quote_entries = action_audit_service.get_entries(entity_type="quote")
        assert len(quote_entries) == 1
    
    def test_verify_consistency(self, action_audit_service):
        """Test verifying action consistency."""
        for i in range(5):
            action_id = action_audit_service.start_action(
                action_type="update",
                entity_type="order",
                entity_id="order_001",
                user_id="user_001",
            )
            action_audit_service.complete_action(action_id, success=i < 3)
        
        result = action_audit_service.verify_consistency("order", "order_001")
        
        assert result["total_actions"] == 5
        assert result["successful_actions"] == 3
        assert result["failed_actions"] == 2
        assert result["consistency_score"] == 1.0


# =============================================================================
# CONNECTION HEALTH SERVICE TESTS
# =============================================================================


class TestConnectionHealthService:
    """Test ConnectionHealthService."""
    
    def test_register_connection(self, connection_health_service):
        """Test registering a connection."""
        status = connection_health_service.register_connection(
            "conn_001",
            "sse",
        )
        
        assert status.connection_id == "conn_001"
        assert status.state == ConnectionState.CONNECTING
    
    def test_update_state(self, connection_health_service):
        """Test updating connection state."""
        connection_health_service.register_connection("conn_001", "websocket")
        
        status = connection_health_service.update_state(
            "conn_001",
            ConnectionState.CONNECTED,
        )
        
        assert status.state == ConnectionState.CONNECTED
    
    def test_reconnect_attempts_tracked(self, connection_health_service):
        """Test reconnect attempts are tracked."""
        connection_health_service.register_connection("conn_001", "sse")
        
        connection_health_service.update_state("conn_001", ConnectionState.RECONNECTING)
        connection_health_service.update_state("conn_001", ConnectionState.RECONNECTING)
        status = connection_health_service.update_state("conn_001", ConnectionState.RECONNECTING)
        
        assert status.reconnect_attempts == 3
        
        # Reset on successful connect
        status = connection_health_service.update_state("conn_001", ConnectionState.CONNECTED)
        assert status.reconnect_attempts == 0
    
    def test_record_ping(self, connection_health_service):
        """Test recording ping."""
        connection_health_service.register_connection("conn_001", "websocket")
        connection_health_service.update_state("conn_001", ConnectionState.CONNECTED)
        
        status = connection_health_service.record_ping("conn_001", 45.5)
        
        assert status.latency_ms == 45.5
        assert status.last_ping is not None
    
    def test_record_message(self, connection_health_service):
        """Test recording message."""
        connection_health_service.register_connection("conn_001", "sse")
        connection_health_service.update_state("conn_001", ConnectionState.CONNECTED)
        
        status = connection_health_service.record_message("conn_001")
        
        assert status.last_message is not None
    
    def test_remove_connection(self, connection_health_service):
        """Test removing a connection."""
        connection_health_service.register_connection("conn_001", "sse")
        
        result = connection_health_service.remove_connection("conn_001")
        
        assert result
        assert "conn_001" not in connection_health_service.connections
    
    def test_get_health_summary_empty(self, connection_health_service):
        """Test health summary with no connections."""
        summary = connection_health_service.get_health_summary()
        
        assert summary["total_connections"] == 0
        assert summary["health_percentage"] == 100.0
    
    def test_get_health_summary_mixed(self, connection_health_service):
        """Test health summary with mixed connections."""
        # Healthy connection
        connection_health_service.register_connection("conn_001", "sse")
        connection_health_service.update_state("conn_001", ConnectionState.CONNECTED)
        connection_health_service.record_ping("conn_001", 50.0)
        
        # Unhealthy connection
        connection_health_service.register_connection("conn_002", "websocket")
        connection_health_service.update_state("conn_002", ConnectionState.RECONNECTING)
        
        summary = connection_health_service.get_health_summary()
        
        assert summary["total_connections"] == 2
        assert summary["healthy"] == 1
        assert summary["unhealthy"] == 1
        assert summary["reconnecting"] == 1
        assert summary["health_percentage"] == 50.0


# =============================================================================
# UI BACKEND INTEGRATION TESTS
# =============================================================================


class TestUIBackendIntegration:
    """Test UIBackendIntegration orchestrator."""
    
    def test_creation(self, integration):
        """Test integration creation."""
        assert integration.error_mapping is not None
        assert integration.schema_export is not None
        assert integration.action_audit is not None
        assert integration.connection_health is not None
    
    def test_get_error_response(self, integration):
        """Test getting error response."""
        response = integration.get_error_response("NOT_FOUND", 404)
        
        assert response["error_code"] == "NOT_FOUND"
        assert response["http_status"] == 404
    
    def test_export_schemas_zod(self, integration):
        """Test exporting schemas as Zod."""
        schemas = integration.export_schemas("zod", ["RFQCreate"])
        
        assert "z.object" in schemas
    
    def test_export_schemas_typescript(self, integration):
        """Test exporting schemas as TypeScript."""
        schemas = integration.export_schemas("typescript", ["RFQCreate"])
        
        assert "export interface" in schemas
    
    def test_track_action_flow(self, integration):
        """Test complete action tracking flow."""
        # Start action
        action_id = integration.track_action(
            action_type="create",
            entity_type="customer",
            entity_id="cust_001",
            user_id="user_001",
            ui_context={"form": "customer_create"},
        )
        
        assert action_id
        
        # Complete action
        entry = integration.complete_action(
            action_id,
            success=True,
            backend_response={"id": "cust_001"},
        )
        
        assert entry is not None
        assert entry.success
    
    def test_get_integration_status(self, integration):
        """Test getting integration status."""
        status = integration.get_integration_status()
        
        assert "error_mappings" in status
        assert "validation_schemas" in status
        assert "connection_health" in status
        assert "pending_actions" in status
        assert "audit_entries" in status


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_ui_backend_integration(self):
        """Test creating UI/Backend Integration."""
        integration = create_ui_backend_integration()
        assert isinstance(integration, UIBackendIntegration)
    
    def test_create_error_mapping_service(self):
        """Test creating error mapping service."""
        service = create_error_mapping_service()
        assert isinstance(service, ErrorMappingService)
    
    def test_create_schema_export_service(self):
        """Test creating schema export service."""
        service = create_schema_export_service()
        assert isinstance(service, ValidationSchemaExportService)
    
    def test_create_action_audit_service(self):
        """Test creating action audit service."""
        service = create_action_audit_service()
        assert isinstance(service, ActionAuditService)
    
    def test_create_connection_health_service(self):
        """Test creating connection health service."""
        service = create_connection_health_service()
        assert isinstance(service, ConnectionHealthService)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestUIBackendIntegrationScenarios:
    """Integration tests for UI/Backend scenarios."""
    
    def test_complete_action_with_error_mapping(self, integration):
        """Test complete action flow with error mapping."""
        # Start action
        action_id = integration.track_action(
            action_type="create",
            entity_type="rfq",
            entity_id="rfq_new",
            user_id="user_001",
        )
        
        # Simulate failure
        error_response = integration.get_error_response("VALIDATION_ERROR", 400)
        
        entry = integration.complete_action(
            action_id,
            success=False,
            error_code="VALIDATION_ERROR",
        )
        
        assert entry is not None
        assert not entry.success
        assert error_response["recovery_actions"] == ["fix_input"]
    
    def test_schema_export_for_frontend_sync(self, integration):
        """Test exporting schemas for frontend synchronization."""
        # Get all schemas
        schema_list = integration.schema_export.get_schema_list()
        
        # Export specific schemas
        for schema_info in schema_list[:3]:
            zod = integration.export_schemas("zod", [schema_info["name"]])
            assert "z.object" in zod
            
            ts = integration.export_schemas("typescript", [schema_info["name"]])
            assert "export interface" in ts
    
    def test_connection_lifecycle(self, integration):
        """Test connection lifecycle management."""
        # Register connection
        conn = integration.connection_health.register_connection("conn_1", "sse")
        assert conn.state == ConnectionState.CONNECTING
        
        # Connect
        integration.connection_health.update_state("conn_1", ConnectionState.CONNECTED)
        integration.connection_health.record_ping("conn_1", 25.0)
        
        # Verify healthy
        summary = integration.connection_health.get_health_summary()
        assert summary["healthy"] == 1
        
        # Simulate disconnect
        integration.connection_health.update_state("conn_1", ConnectionState.DISCONNECTED)
        
        summary = integration.connection_health.get_health_summary()
        assert summary["unhealthy"] == 1
    
    def test_audit_action_consistency_check(self, integration):
        """Test action consistency checking."""
        # Create multiple actions for same entity
        for i in range(10):
            action_id = integration.track_action(
                action_type="update",
                entity_type="order",
                entity_id="order_123",
                user_id="user_001",
            )
            integration.complete_action(action_id, success=i % 3 != 0)
        
        # Check consistency
        result = integration.action_audit.verify_consistency("order", "order_123")
        
        assert result["total_actions"] == 10
        assert result["consistency_score"] == 1.0  # All have entries
    
    def test_full_error_handling_flow(self, integration):
        """Test complete error handling flow."""
        # Start action
        action_id = integration.track_action(
            action_type="delete",
            entity_type="quote",
            entity_id="quote_to_delete",
            user_id="user_admin",
            ui_context={"confirmation_shown": True},
        )
        
        # Simulate error
        error_code = "BUSINESS_RULE_VIOLATION:QUOTE_IN_PROGRESS"
        error_response = integration.get_error_response(error_code, 422)
        
        # Complete with error
        entry = integration.complete_action(
            action_id,
            success=False,
            error_code=error_code,
            backend_response={"error": error_response},
        )
        
        # Verify
        assert entry is not None
        assert entry.error_code == error_code
        assert error_response["category"] == "business_rule"
        assert RecoveryAction.GO_BACK.value in error_response["recovery_actions"]
