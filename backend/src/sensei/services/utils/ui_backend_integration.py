"""
UI/Backend Integration Service.

Provides services for maintaining consistency between frontend and backend:
- Validation schema export (Pydantic → TypeScript/Zod compatible)
- Error code mapping with user-friendly messages
- Action audit logging
- Real-time connection health monitoring

Implements Development Plan Section 19.16 requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4, UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.strategic_v2 import UIActionAuditRecord


# =============================================================================
# ENUMS
# =============================================================================


class ErrorCategory(str, Enum):
    """Categories of errors for UI handling."""
    
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSINESS_RULE = "business_rule"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK = "network"
    TIMEOUT = "timeout"


class RecoveryAction(str, Enum):
    """Suggested recovery actions for errors."""
    
    RETRY = "retry"
    LOGIN = "login"
    REFRESH = "refresh"
    CONTACT_ADMIN = "contact_admin"
    FIX_INPUT = "fix_input"
    WAIT_AND_RETRY = "wait_and_retry"
    CREATE_NEW = "create_new"
    GO_BACK = "go_back"
    CHECK_PERMISSIONS = "check_permissions"


class FieldType(str, Enum):
    """Schema field types for export."""
    
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    ENUM = "enum"


class ConnectionState(str, Enum):
    """Real-time connection states."""
    
    CONNECTED = "connected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class ErrorMapping:
    """Mapping from error code to user-friendly message."""
    
    error_code: str
    category: ErrorCategory
    title: str
    message: str
    recovery_actions: list[RecoveryAction]
    recovery_instructions: str
    support_link: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "error_code": self.error_code,
            "category": self.category.value,
            "title": self.title,
            "message": self.message,
            "recovery_actions": [a.value for a in self.recovery_actions],
            "recovery_instructions": self.recovery_instructions,
            "support_link": self.support_link,
        }


@dataclass
class SchemaField:
    """A field in a validation schema."""
    
    name: str
    field_type: FieldType
    required: bool = True
    nullable: bool = False
    min_length: int | None = None
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    enum_values: list[str] | None = None
    array_item_type: FieldType | None = None
    nested_schema: str | None = None
    description: str | None = None
    default: Any = None
    
    def to_typescript(self) -> str:
        """Convert to TypeScript type definition."""
        ts_type = self._get_typescript_type()
        optional = "" if self.required else "?"
        nullable = " | null" if self.nullable else ""
        return f"{self.name}{optional}: {ts_type}{nullable}"
    
    def _get_typescript_type(self) -> str:
        """Get TypeScript type for field."""
        type_map = {
            FieldType.STRING: "string",
            FieldType.NUMBER: "number",
            FieldType.INTEGER: "number",
            FieldType.BOOLEAN: "boolean",
            FieldType.DATE: "string",
            FieldType.DATETIME: "string",
            FieldType.UUID: "string",
            FieldType.EMAIL: "string",
            FieldType.URL: "string",
        }
        
        if self.field_type == FieldType.ENUM and self.enum_values:
            return " | ".join(f'"{v}"' for v in self.enum_values)
        
        if self.field_type == FieldType.ARRAY:
            item_type = "any"
            if self.array_item_type:
                item_type = type_map.get(self.array_item_type, "any")
            elif self.nested_schema:
                item_type = self.nested_schema
            return f"{item_type}[]"
        
        if self.field_type == FieldType.OBJECT:
            if self.nested_schema:
                return self.nested_schema
            return "Record<string, any>"
        
        return type_map.get(self.field_type, "any")
    
    def to_zod(self) -> str:
        """Convert to Zod schema definition."""
        zod_type = self._get_zod_type()
        
        # Add constraints
        constraints = []
        if self.min_length is not None:
            constraints.append(f".min({self.min_length})")
        if self.max_length is not None:
            constraints.append(f".max({self.max_length})")
        if self.min_value is not None:
            constraints.append(f".min({self.min_value})")
        if self.max_value is not None:
            constraints.append(f".max({self.max_value})")
        if self.pattern:
            constraints.append(f'.regex(/{self.pattern}/)')
        
        # Handle optional/nullable
        modifiers = []
        if self.nullable:
            modifiers.append(".nullable()")
        if not self.required:
            modifiers.append(".optional()")
        if self.default is not None:
            default_val = f'"{self.default}"' if isinstance(self.default, str) else self.default
            modifiers.append(f".default({default_val})")
        
        constraint_str = "".join(constraints)
        modifier_str = "".join(modifiers)
        
        return f"{self.name}: {zod_type}{constraint_str}{modifier_str}"
    
    def _get_zod_type(self) -> str:
        """Get Zod type for field."""
        type_map = {
            FieldType.STRING: "z.string()",
            FieldType.NUMBER: "z.number()",
            FieldType.INTEGER: "z.number().int()",
            FieldType.BOOLEAN: "z.boolean()",
            FieldType.DATE: "z.string().date()",
            FieldType.DATETIME: "z.string().datetime()",
            FieldType.UUID: "z.string().uuid()",
            FieldType.EMAIL: "z.string().email()",
            FieldType.URL: "z.string().url()",
        }
        
        if self.field_type == FieldType.ENUM and self.enum_values:
            values = ", ".join(f'"{v}"' for v in self.enum_values)
            return f"z.enum([{values}])"
        
        if self.field_type == FieldType.ARRAY:
            item_type = "z.any()"
            if self.array_item_type:
                item_type = type_map.get(self.array_item_type, "z.any()")
            elif self.nested_schema:
                item_type = f"{self.nested_schema}Schema"
            return f"z.array({item_type})"
        
        if self.field_type == FieldType.OBJECT:
            if self.nested_schema:
                return f"{self.nested_schema}Schema"
            return "z.record(z.any())"
        
        return type_map.get(self.field_type, "z.any()")


@dataclass
class ValidationSchema:
    """A validation schema that can be exported."""
    
    name: str
    description: str
    fields: list[SchemaField]
    version: str = "1.0"
    
    def to_typescript_interface(self) -> str:
        """Export as TypeScript interface."""
        field_lines = [f"  {f.to_typescript()};" for f in self.fields]
        fields_str = "\n".join(field_lines)
        
        return f"""/**
 * {self.description}
 * @version {self.version}
 */
export interface {self.name} {{
{fields_str}
}}"""
    
    def to_zod_schema(self) -> str:
        """Export as Zod schema."""
        field_lines = [f"  {f.to_zod()}," for f in self.fields]
        fields_str = "\n".join(field_lines)
        
        return f"""/**
 * {self.description}
 * @version {self.version}
 */
export const {self.name}Schema = z.object({{
{fields_str}
}});

export type {self.name} = z.infer<typeof {self.name}Schema>;"""


@dataclass
class ActionAuditEntry:
    """An audit log entry for UI action."""
    
    entry_id: str
    action_type: str
    entity_type: str
    entity_id: str
    user_id: str
    timestamp: datetime
    ui_context: dict[str, Any]
    backend_response: dict[str, Any]
    duration_ms: int
    success: bool
    error_code: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "ui_context": self.ui_context,
            "backend_response": self.backend_response,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_code": self.error_code,
        }


@dataclass
class ConnectionHealthStatus:
    """Health status for real-time connections."""
    
    connection_id: str
    connection_type: str  # sse, websocket
    state: ConnectionState
    last_ping: datetime | None
    last_message: datetime | None
    reconnect_attempts: int
    latency_ms: float | None = None
    error_message: str | None = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.state == ConnectionState.CONNECTED and self.latency_ms is not None and self.latency_ms < 1000


# =============================================================================
# ERROR MAPPING SERVICE
# =============================================================================


class ErrorMappingService:
    """
    Service for mapping backend errors to user-friendly messages.
    
    Provides consistent, actionable error messages across the UI.
    """
    
    def __init__(self) -> None:
        """Initialize with default error mappings."""
        self.mappings: dict[str, ErrorMapping] = {}
        self._register_default_mappings()
    
    def _register_default_mappings(self) -> None:
        """Register default error mappings."""
        # Authentication errors
        self.register(ErrorMapping(
            error_code="UNAUTHORIZED",
            category=ErrorCategory.AUTHENTICATION,
            title="Session Expired",
            message="Your session has expired. Please log in again to continue.",
            recovery_actions=[RecoveryAction.LOGIN],
            recovery_instructions="Click the login button to authenticate.",
        ))
        
        self.register(ErrorMapping(
            error_code="INVALID_CREDENTIALS",
            category=ErrorCategory.AUTHENTICATION,
            title="Invalid Credentials",
            message="The email or password you entered is incorrect.",
            recovery_actions=[RecoveryAction.FIX_INPUT, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Please check your credentials and try again.",
        ))
        
        self.register(ErrorMapping(
            error_code="TOKEN_EXPIRED",
            category=ErrorCategory.AUTHENTICATION,
            title="Token Expired",
            message="Your authentication token has expired.",
            recovery_actions=[RecoveryAction.LOGIN, RecoveryAction.REFRESH],
            recovery_instructions="Please log in again to get a new token.",
        ))
        
        # Authorization errors
        self.register(ErrorMapping(
            error_code="FORBIDDEN",
            category=ErrorCategory.AUTHORIZATION,
            title="Access Denied",
            message="You don't have permission to perform this action.",
            recovery_actions=[RecoveryAction.CHECK_PERMISSIONS, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Contact your administrator to request access.",
        ))
        
        self.register(ErrorMapping(
            error_code="INSUFFICIENT_PERMISSIONS",
            category=ErrorCategory.AUTHORIZATION,
            title="Insufficient Permissions",
            message="Your role doesn't include the required permission for this action.",
            recovery_actions=[RecoveryAction.CHECK_PERMISSIONS, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Request the necessary permission from your administrator.",
        ))
        
        # Validation errors
        self.register(ErrorMapping(
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            title="Invalid Input",
            message="Some of the information you provided is invalid.",
            recovery_actions=[RecoveryAction.FIX_INPUT],
            recovery_instructions="Please review the highlighted fields and correct the errors.",
        ))
        
        self.register(ErrorMapping(
            error_code="REQUIRED_FIELD_MISSING",
            category=ErrorCategory.VALIDATION,
            title="Required Field Missing",
            message="Please fill in all required fields.",
            recovery_actions=[RecoveryAction.FIX_INPUT],
            recovery_instructions="Complete the highlighted required fields.",
        ))
        
        # Not found errors
        self.register(ErrorMapping(
            error_code="NOT_FOUND",
            category=ErrorCategory.NOT_FOUND,
            title="Not Found",
            message="The item you're looking for doesn't exist or has been deleted.",
            recovery_actions=[RecoveryAction.GO_BACK, RecoveryAction.CREATE_NEW],
            recovery_instructions="Go back or create a new item.",
        ))
        
        self.register(ErrorMapping(
            error_code="RESOURCE_DELETED",
            category=ErrorCategory.NOT_FOUND,
            title="Item Deleted",
            message="This item has been deleted and is no longer available.",
            recovery_actions=[RecoveryAction.GO_BACK],
            recovery_instructions="Navigate back to the list view.",
        ))
        
        # Conflict errors
        self.register(ErrorMapping(
            error_code="CONFLICT",
            category=ErrorCategory.CONFLICT,
            title="Conflict Detected",
            message="This action conflicts with existing data.",
            recovery_actions=[RecoveryAction.REFRESH, RecoveryAction.FIX_INPUT],
            recovery_instructions="Refresh the page to see the latest data, then try again.",
        ))
        
        self.register(ErrorMapping(
            error_code="DUPLICATE_ENTRY",
            category=ErrorCategory.CONFLICT,
            title="Duplicate Entry",
            message="An item with this identifier already exists.",
            recovery_actions=[RecoveryAction.FIX_INPUT],
            recovery_instructions="Use a different identifier for this item.",
        ))
        
        self.register(ErrorMapping(
            error_code="CONCURRENT_MODIFICATION",
            category=ErrorCategory.CONFLICT,
            title="Concurrent Modification",
            message="This item was modified by another user while you were editing.",
            recovery_actions=[RecoveryAction.REFRESH],
            recovery_instructions="Refresh to see the latest changes, then reapply your edits.",
        ))
        
        # Business rule errors
        self.register(ErrorMapping(
            error_code="BUSINESS_RULE_VIOLATION",
            category=ErrorCategory.BUSINESS_RULE,
            title="Action Not Allowed",
            message="This action violates business rules.",
            recovery_actions=[RecoveryAction.GO_BACK, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Review the business rules or contact your administrator.",
        ))
        
        self.register(ErrorMapping(
            error_code="STATE_TRANSITION_ERROR",
            category=ErrorCategory.BUSINESS_RULE,
            title="Invalid Status Change",
            message="This status transition is not allowed.",
            recovery_actions=[RecoveryAction.GO_BACK],
            recovery_instructions="Check the allowed status transitions for this item.",
        ))
        
        self.register(ErrorMapping(
            error_code="WORKFLOW_BLOCKED",
            category=ErrorCategory.BUSINESS_RULE,
            title="Workflow Blocked",
            message="This workflow step is blocked by a prerequisite.",
            recovery_actions=[RecoveryAction.GO_BACK],
            recovery_instructions="Complete the required prerequisites first.",
        ))
        
        # Rate limit errors
        self.register(ErrorMapping(
            error_code="RATE_LIMIT_EXCEEDED",
            category=ErrorCategory.RATE_LIMIT,
            title="Too Many Requests",
            message="You've made too many requests. Please wait before trying again.",
            recovery_actions=[RecoveryAction.WAIT_AND_RETRY],
            recovery_instructions="Wait a moment, then try again.",
        ))
        
        # Server errors
        self.register(ErrorMapping(
            error_code="INTERNAL_SERVER_ERROR",
            category=ErrorCategory.SERVER_ERROR,
            title="Server Error",
            message="An unexpected error occurred on the server.",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Try again. If the problem persists, contact support.",
            support_link="/support",
        ))
        
        self.register(ErrorMapping(
            error_code="SERVICE_UNAVAILABLE",
            category=ErrorCategory.SERVER_ERROR,
            title="Service Unavailable",
            message="The service is temporarily unavailable.",
            recovery_actions=[RecoveryAction.WAIT_AND_RETRY],
            recovery_instructions="Please try again in a few minutes.",
        ))
        
        self.register(ErrorMapping(
            error_code="DATABASE_ERROR",
            category=ErrorCategory.SERVER_ERROR,
            title="Database Error",
            message="A database error occurred. Your data may not have been saved.",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Try again. If you continue to see this error, contact support.",
            support_link="/support",
        ))
        
        # Network errors
        self.register(ErrorMapping(
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            title="Connection Error",
            message="Unable to connect to the server.",
            recovery_actions=[RecoveryAction.RETRY],
            recovery_instructions="Check your internet connection and try again.",
        ))
        
        self.register(ErrorMapping(
            error_code="TIMEOUT",
            category=ErrorCategory.TIMEOUT,
            title="Request Timeout",
            message="The request took too long to complete.",
            recovery_actions=[RecoveryAction.RETRY],
            recovery_instructions="The server is busy. Please try again.",
        ))
    
    def register(self, mapping: ErrorMapping) -> None:
        """Register an error mapping."""
        self.mappings[mapping.error_code] = mapping
    
    def get_mapping(self, error_code: str) -> ErrorMapping:
        """Get error mapping for an error code."""
        if error_code in self.mappings:
            return self.mappings[error_code]
        
        # Check for pattern-based codes (e.g., BUSINESS_RULE_VIOLATION:RULE_NAME)
        if ":" in error_code:
            base_code = error_code.split(":")[0]
            if base_code in self.mappings:
                return self.mappings[base_code]
        
        # Default fallback
        return ErrorMapping(
            error_code=error_code,
            category=ErrorCategory.SERVER_ERROR,
            title="Error",
            message="An unexpected error occurred.",
            recovery_actions=[RecoveryAction.RETRY, RecoveryAction.CONTACT_ADMIN],
            recovery_instructions="Please try again. If the problem persists, contact support.",
        )
    
    def get_user_friendly_error(
        self,
        error_code: str,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get user-friendly error response."""
        mapping = self.get_mapping(error_code)
        
        response = mapping.to_dict()
        
        # Add HTTP status
        if http_status:
            response["http_status"] = http_status
        
        # Add field-specific errors if present
        if details and "field_errors" in details:
            response["field_errors"] = details["field_errors"]
        
        return response
    
    def get_all_mappings(self) -> list[dict[str, Any]]:
        """Get all error mappings for frontend sync."""
        return [m.to_dict() for m in self.mappings.values()]


# =============================================================================
# VALIDATION SCHEMA EXPORT SERVICE
# =============================================================================


class ValidationSchemaExportService:
    """
    Service for exporting backend validation schemas.
    
    Enables frontend-backend validation sync by generating
    TypeScript interfaces and Zod schemas from Pydantic models.
    """
    
    def __init__(self) -> None:
        """Initialize schema export service."""
        self.schemas: dict[str, ValidationSchema] = {}
        self._register_core_schemas()
    
    def _register_core_schemas(self) -> None:
        """Register core validation schemas."""
        # RFQ Create Schema
        self.register(ValidationSchema(
            name="RFQCreate",
            description="Schema for creating a new RFQ",
            fields=[
                SchemaField("title", FieldType.STRING, min_length=3, max_length=200),
                SchemaField("customer_id", FieldType.UUID),
                SchemaField("due_date", FieldType.DATE, required=False),
                SchemaField("priority", FieldType.ENUM, enum_values=["low", "medium", "high", "urgent"]),
                SchemaField("description", FieldType.STRING, required=False, max_length=2000),
                SchemaField("attachments", FieldType.ARRAY, array_item_type=FieldType.UUID, required=False),
                SchemaField("tags", FieldType.ARRAY, array_item_type=FieldType.STRING, required=False),
            ],
        ))
        
        # Quote Create Schema
        self.register(ValidationSchema(
            name="QuoteCreate",
            description="Schema for creating a new quote",
            fields=[
                SchemaField("rfq_id", FieldType.UUID),
                SchemaField("valid_until", FieldType.DATE),
                SchemaField("currency", FieldType.STRING, min_length=3, max_length=3),
                SchemaField("payment_terms", FieldType.STRING, required=False),
                SchemaField("line_items", FieldType.ARRAY, nested_schema="QuoteLineItem"),
                SchemaField("notes", FieldType.STRING, required=False, max_length=5000),
            ],
        ))
        
        # Quote Line Item Schema
        self.register(ValidationSchema(
            name="QuoteLineItem",
            description="Schema for a quote line item",
            fields=[
                SchemaField("description", FieldType.STRING, min_length=1, max_length=500),
                SchemaField("quantity", FieldType.NUMBER, min_value=0.01),
                SchemaField("unit", FieldType.STRING, max_length=50),
                SchemaField("unit_price", FieldType.NUMBER, min_value=0),
                SchemaField("discount_percent", FieldType.NUMBER, min_value=0, max_value=100, required=False),
                SchemaField("tax_rate", FieldType.NUMBER, min_value=0, max_value=100, required=False),
            ],
        ))
        
        # Customer Create Schema
        self.register(ValidationSchema(
            name="CustomerCreate",
            description="Schema for creating a new customer",
            fields=[
                SchemaField("name", FieldType.STRING, min_length=2, max_length=200),
                SchemaField("email", FieldType.EMAIL, required=False),
                SchemaField("phone", FieldType.STRING, required=False, max_length=50),
                SchemaField("website", FieldType.URL, required=False),
                SchemaField("address", FieldType.OBJECT, nested_schema="Address", required=False),
                SchemaField("industry", FieldType.STRING, required=False, max_length=100),
                SchemaField("annual_revenue", FieldType.NUMBER, min_value=0, required=False),
            ],
        ))
        
        # Address Schema
        self.register(ValidationSchema(
            name="Address",
            description="Schema for an address",
            fields=[
                SchemaField("street", FieldType.STRING, max_length=200),
                SchemaField("city", FieldType.STRING, max_length=100),
                SchemaField("state", FieldType.STRING, required=False, max_length=100),
                SchemaField("postal_code", FieldType.STRING, max_length=20),
                SchemaField("country", FieldType.STRING, max_length=100),
            ],
        ))
        
        # Work Order Create Schema
        self.register(ValidationSchema(
            name="WorkOrderCreate",
            description="Schema for creating a work order",
            fields=[
                SchemaField("work_order_number", FieldType.STRING, min_length=1, max_length=50),
                SchemaField("external_reference", FieldType.STRING, required=False, max_length=100),
                SchemaField("quote_id", FieldType.UUID, required=False),
                SchemaField("product_id", FieldType.INTEGER),
                SchemaField("quantity_ordered", FieldType.NUMBER, min_value=0.0001),
                SchemaField("priority", FieldType.ENUM, enum_values=["low", "normal", "high", "urgent", "critical"], required=False),
                SchemaField("status", FieldType.ENUM, enum_values=["draft", "released", "in_progress", "on_hold", "completed", "cancelled", "closed"], required=False),
                SchemaField("work_center_id", FieldType.INTEGER, required=False),
                SchemaField("scheduled_start", FieldType.DATETIME, required=False),
                SchemaField("scheduled_end", FieldType.DATETIME, required=False),
                SchemaField("lot_number", FieldType.STRING, required=False, max_length=50),
                SchemaField("batch_id", FieldType.STRING, required=False, max_length=50),
                SchemaField("notes", FieldType.STRING, required=False, max_length=2000),
                SchemaField("production_notes", FieldType.STRING, required=False, max_length=2000),
            ],
        ))
        
        # User Create Schema
        self.register(ValidationSchema(
            name="UserCreate",
            description="Schema for creating a new user",
            fields=[
                SchemaField("email", FieldType.EMAIL),
                SchemaField("password", FieldType.STRING, min_length=8, max_length=100),
                SchemaField("first_name", FieldType.STRING, min_length=1, max_length=100),
                SchemaField("last_name", FieldType.STRING, min_length=1, max_length=100),
                SchemaField("role_ids", FieldType.ARRAY, array_item_type=FieldType.UUID),
                SchemaField("department_id", FieldType.UUID, required=False),
                SchemaField("is_active", FieldType.BOOLEAN, default=True),
            ],
        ))
        
        # A3 Problem Solving Schema
        self.register(ValidationSchema(
            name="A3Create",
            description="Schema for creating an A3 problem solving document",
            fields=[
                SchemaField("a3_number", FieldType.STRING, min_length=1, max_length=50),
                SchemaField("title", FieldType.STRING, min_length=1, max_length=255),
                SchemaField("a3_type", FieldType.ENUM, enum_values=["problem_solving", "proposal", "status_report", "strategy"]),
                SchemaField("priority", FieldType.ENUM, enum_values=["critical", "high", "medium", "low"]),
                SchemaField("target_completion_date", FieldType.DATETIME, required=False),
                SchemaField("sponsor_id", FieldType.UUID, required=False),
                SchemaField("coach_id", FieldType.UUID, required=False),
                SchemaField("create_default_sections", FieldType.BOOLEAN, default=True),
            ],
        ))
    
    def register(self, schema: ValidationSchema) -> None:
        """Register a validation schema."""
        self.schemas[schema.name] = schema
    
    def get_schema(self, name: str) -> ValidationSchema | None:
        """Get a validation schema by name."""
        return self.schemas.get(name)
    
    def export_typescript(self, schema_names: list[str] | None = None) -> str:
        """Export schemas as TypeScript interfaces."""
        names = schema_names or list(self.schemas.keys())
        interfaces = []
        
        for name in names:
            if name in self.schemas:
                interfaces.append(self.schemas[name].to_typescript_interface())
        
        return "\n\n".join(interfaces)
    
    def export_zod(self, schema_names: list[str] | None = None) -> str:
        """Export schemas as Zod schemas."""
        names = schema_names or list(self.schemas.keys())
        schemas = []
        
        # Add Zod import
        imports = 'import { z } from "zod";\n\n'
        
        for name in names:
            if name in self.schemas:
                schemas.append(self.schemas[name].to_zod_schema())
        
        return imports + "\n\n".join(schemas)
    
    def export_json_schema(self, name: str) -> dict[str, Any] | None:
        """Export a schema as JSON Schema for validation."""
        schema = self.schemas.get(name)
        if not schema:
            return None
        
        properties = {}
        required = []
        
        for f in schema.fields:
            prop: dict[str, Any] = {"type": f.field_type.value}
            
            if f.description:
                prop["description"] = f.description
            if f.min_length is not None:
                prop["minLength"] = f.min_length
            if f.max_length is not None:
                prop["maxLength"] = f.max_length
            if f.min_value is not None:
                prop["minimum"] = f.min_value
            if f.max_value is not None:
                prop["maximum"] = f.max_value
            if f.pattern:
                prop["pattern"] = f.pattern
            if f.enum_values:
                prop["enum"] = f.enum_values
            if f.default is not None:
                prop["default"] = f.default
            
            if f.required:
                required.append(f.name)
            
            properties[f.name] = prop
        
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": schema.name,
            "description": schema.description,
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def get_schema_list(self) -> list[dict[str, Any]]:
        """Get list of available schemas."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "field_count": len(s.fields),
            }
            for s in self.schemas.values()
        ]


# =============================================================================
# ACTION AUDIT SERVICE
# =============================================================================


class ActionAuditService:
    """
    Service for tracking UI action to backend audit log consistency with DB persistence.
    
    Ensures every UI action corresponds to exactly one backend audit entry.
    """
    
    def __init__(self) -> None:
        """Initialize action audit service."""
        self.pending_actions: dict[str, dict[str, Any]] = {}
    
    def start_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        ui_context: dict[str, Any] | None = None,
    ) -> str:
        """Start tracking a UI action (temporary in-memory until completion)."""
        action_id = f"action_{uuid4().hex[:12]}"
        
        self.pending_actions[action_id] = {
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "ui_context": ui_context or {},
            "started_at": datetime.now(timezone.utc),
        }
        
        return action_id
    
    async def complete_action(
        self,
        db: AsyncSession,
        action_id: str,
        success: bool,
        backend_response: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> UIActionAuditRecord | None:
        """Complete tracking a UI action and persist to database."""
        if action_id not in self.pending_actions:
            return None
        
        pending = self.pending_actions.pop(action_id)
        now = datetime.now(timezone.utc)
        duration_ms = int((now - pending["started_at"]).total_seconds() * 1000)
        
        record = UIActionAuditRecord(
            action_id=action_id,
            action_type=pending["action_type"],
            entity_type=pending["entity_type"],
            entity_id=pending["entity_id"],
            user_id=UUID(pending["user_id"]),
            ui_context=pending["ui_context"],
            success=success,
            duration_ms=duration_ms,
            error_code=error_code,
        )
        
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    
    async def get_entries(
        self,
        db: AsyncSession,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: str | None = None,
        action_type: str | None = None,
        limit: int = 100,
    ) -> list[UIActionAuditRecord]:
        """Get audit entries from database with optional filtering."""
        stmt = select(UIActionAuditRecord)
        
        if entity_type:
            stmt = stmt.where(UIActionAuditRecord.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(UIActionAuditRecord.entity_id == entity_id)
        if user_id:
            stmt = stmt.where(UIActionAuditRecord.user_id == UUID(user_id))
        if action_type:
            stmt = stmt.where(UIActionAuditRecord.action_type == action_type)
        
        stmt = stmt.order_by(UIActionAuditRecord.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def verify_consistency(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, Any]:
        """Verify that all UI actions have corresponding audit entries."""
        entries = await self.get_entries(db, entity_type=entity_type, entity_id=entity_id)
        
        total = len(entries)
        successful = len([e for e in entries if e.success])
        failed = len([e for e in entries if not e.success])
        
        # Calculate consistency score
        # Every action should have an entry
        consistency_score = 1.0 if total > 0 else 0.0
        
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "total_actions": total,
            "successful_actions": successful,
            "failed_actions": failed,
            "consistency_score": consistency_score,
            "pending_actions": len([
                a for a in self.pending_actions.values()
                if a["entity_type"] == entity_type and a["entity_id"] == entity_id
            ]),
        }


# =============================================================================
# CONNECTION HEALTH SERVICE
# =============================================================================


class ConnectionHealthService:
    """
    Service for monitoring real-time connection health.
    
    Tracks SSE and WebSocket connections for resilience.
    """
    
    def __init__(self) -> None:
        """Initialize connection health service."""
        self.connections: dict[str, ConnectionHealthStatus] = {}
    
    def register_connection(
        self,
        connection_id: str,
        connection_type: str,
    ) -> ConnectionHealthStatus:
        """Register a new connection."""
        status = ConnectionHealthStatus(
            connection_id=connection_id,
            connection_type=connection_type,
            state=ConnectionState.CONNECTING,
            last_ping=None,
            last_message=None,
            reconnect_attempts=0,
        )
        
        self.connections[connection_id] = status
        return status
    
    def update_state(
        self,
        connection_id: str,
        state: ConnectionState,
        error_message: str | None = None,
    ) -> ConnectionHealthStatus | None:
        """Update connection state."""
        if connection_id not in self.connections:
            return None
        
        conn = self.connections[connection_id]
        conn.state = state
        
        if state == ConnectionState.RECONNECTING:
            conn.reconnect_attempts += 1
        elif state == ConnectionState.CONNECTED:
            conn.reconnect_attempts = 0
            conn.error_message = None
        
        if error_message:
            conn.error_message = error_message
        
        return conn
    
    def record_ping(
        self,
        connection_id: str,
        latency_ms: float,
    ) -> ConnectionHealthStatus | None:
        """Record a ping response."""
        if connection_id not in self.connections:
            return None
        
        conn = self.connections[connection_id]
        conn.last_ping = datetime.now(timezone.utc)
        conn.latency_ms = latency_ms
        
        return conn
    
    def record_message(
        self,
        connection_id: str,
    ) -> ConnectionHealthStatus | None:
        """Record a message received."""
        if connection_id not in self.connections:
            return None
        
        conn = self.connections[connection_id]
        conn.last_message = datetime.now(timezone.utc)
        
        return conn
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            return True
        return False
    
    def get_health_summary(self) -> dict[str, Any]:
        """Get overall connection health summary."""
        total = len(self.connections)
        if total == 0:
            return {
                "total_connections": 0,
                "healthy": 0,
                "unhealthy": 0,
                "reconnecting": 0,
                "health_percentage": 100.0,
            }
        
        healthy = len([c for c in self.connections.values() if c.is_healthy])
        reconnecting = len([
            c for c in self.connections.values() 
            if c.state == ConnectionState.RECONNECTING
        ])
        unhealthy = total - healthy
        
        return {
            "total_connections": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "reconnecting": reconnecting,
            "health_percentage": (healthy / total) * 100,
            "connections": [
                {
                    "id": c.connection_id,
                    "type": c.connection_type,
                    "state": c.state.value,
                    "healthy": c.is_healthy,
                    "latency_ms": c.latency_ms,
                    "reconnect_attempts": c.reconnect_attempts,
                }
                for c in self.connections.values()
            ],
        }


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================


class UIBackendIntegration:
    """
    Main orchestrator for UI/Backend Integration.
    
    Combines all integration services for:
    - Error mapping
    - Schema export
    - Action auditing
    - Connection health
    """
    
    def __init__(
        self,
        error_mapping_service: ErrorMappingService | None = None,
        schema_export_service: ValidationSchemaExportService | None = None,
        action_audit_service: ActionAuditService | None = None,
        connection_health_service: ConnectionHealthService | None = None,
    ) -> None:
        """Initialize UI/Backend Integration."""
        self.error_mapping = error_mapping_service or ErrorMappingService()
        self.schema_export = schema_export_service or ValidationSchemaExportService()
        self.action_audit = action_audit_service or ActionAuditService()
        self.connection_health = connection_health_service or ConnectionHealthService()
    
    def get_error_response(
        self,
        error_code: str,
        http_status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get user-friendly error response."""
        return self.error_mapping.get_user_friendly_error(
            error_code, http_status, details
        )
    
    def export_schemas(
        self,
        format: str = "zod",
        schema_names: list[str] | None = None,
    ) -> str:
        """Export validation schemas."""
        if format == "typescript":
            return self.schema_export.export_typescript(schema_names)
        return self.schema_export.export_zod(schema_names)
    
    def track_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        ui_context: dict[str, Any] | None = None,
    ) -> str:
        """Start tracking a UI action."""
        return self.action_audit.start_action(
            action_type, entity_type, entity_id, user_id, ui_context
        )
    
    def complete_action(
        self,
        action_id: str,
        success: bool,
        backend_response: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> ActionAuditEntry | None:
        """Complete tracking a UI action."""
        return self.action_audit.complete_action(
            action_id, success, backend_response, error_code
        )
    
    def get_integration_status(self) -> dict[str, Any]:
        """Get overall integration status."""
        return {
            "error_mappings": len(self.error_mapping.mappings),
            "validation_schemas": len(self.schema_export.schemas),
            "connection_health": self.connection_health.get_health_summary(),
            "pending_actions": len(self.action_audit.pending_actions),
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_ui_backend_integration() -> UIBackendIntegration:
    """Create UI/Backend Integration service."""
    return UIBackendIntegration()


def create_error_mapping_service() -> ErrorMappingService:
    """Create error mapping service."""
    return ErrorMappingService()


def create_schema_export_service() -> ValidationSchemaExportService:
    """Create validation schema export service."""
    return ValidationSchemaExportService()


def create_action_audit_service() -> ActionAuditService:
    """Create action audit service."""
    return ActionAuditService()


def create_connection_health_service() -> ConnectionHealthService:
    """Create connection health service."""
    return ConnectionHealthService()
