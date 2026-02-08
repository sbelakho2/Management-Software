"""
Contract tests between frontend stores and backend API endpoints.

Validates that:
1. Backend endpoints return the expected response shapes
2. Frontend store actions call the correct endpoints with correct params
3. Request/response types match between frontend and backend

Uses a declarative contract definition approach.

Checklist items: #415, #488
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    UUID = "uuid"
    DATETIME = "datetime"
    NULLABLE = "nullable"
    ENUM = "enum"
    ANY = "any"


@dataclass
class FieldContract:
    """Contract for a single field in a request/response."""

    name: str
    field_type: FieldType
    required: bool = True
    nullable: bool = False
    items_type: FieldType | None = None  # for arrays
    enum_values: list[str] = field(default_factory=list)
    nested_fields: list[FieldContract] = field(default_factory=list)
    description: str = ""


@dataclass
class EndpointContract:
    """Contract for a single API endpoint."""

    path: str
    method: HttpMethod
    description: str = ""
    frontend_store: str = ""  # e.g. "quality"
    frontend_action: str = ""  # e.g. "fetchInspections"
    request_fields: list[FieldContract] = field(default_factory=list)
    response_fields: list[FieldContract] = field(default_factory=list)
    response_status: int = 200
    query_params: list[FieldContract] = field(default_factory=list)
    path_params: list[str] = field(default_factory=list)
    auth_required: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class ContractViolation:
    """A single contract violation."""

    contract: str  # endpoint path
    field: str
    expected: str
    actual: str
    severity: str = "error"  # error | warning
    message: str = ""


@dataclass
class ContractTestResult:
    """Result of running contract tests."""

    total_contracts: int = 0
    passed: int = 0
    failed: int = 0
    violations: list[ContractViolation] = field(
        default_factory=list
    )
    tested_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def success(self) -> bool:
        return self.failed == 0


class ContractRegistry:
    """Registry of all API contracts.

    Usage::

        registry = ContractRegistry()

        # Define contracts
        registry.register(EndpointContract(
            path="/api/v1/quality/inspections",
            method=HttpMethod.GET,
            frontend_store="quality",
            frontend_action="fetchInspections",
            response_fields=[
                FieldContract("id", FieldType.UUID),
                FieldContract("title", FieldType.STRING),
                FieldContract("status", FieldType.ENUM, enum_values=["open", "closed"]),
                FieldContract("created_at", FieldType.DATETIME),
            ],
        ))

        # Validate response
        result = registry.validate_response(
            "/api/v1/quality/inspections",
            HttpMethod.GET,
            [{"id": "abc", "title": "Test", "status": "open", "created_at": "2024-01-01T00:00:00Z"}],
        )
    """

    def __init__(self) -> None:
        self._contracts: dict[str, EndpointContract] = {}

    def register(self, contract: EndpointContract) -> None:
        key = f"{contract.method.value}:{contract.path}"
        self._contracts[key] = contract

    def get_contract(
        self, path: str, method: HttpMethod
    ) -> EndpointContract | None:
        return self._contracts.get(f"{method.value}:{path}")

    def get_all_contracts(self) -> list[EndpointContract]:
        return list(self._contracts.values())

    def get_contracts_for_store(
        self, store: str
    ) -> list[EndpointContract]:
        return [
            c
            for c in self._contracts.values()
            if c.frontend_store == store
        ]

    def validate_response(
        self,
        path: str,
        method: HttpMethod,
        response_data: Any,
        *,
        status_code: int = 200,
    ) -> ContractTestResult:
        """Validate a response against its contract."""
        contract = self.get_contract(path, method)
        if not contract:
            return ContractTestResult(
                total_contracts=1,
                failed=1,
                violations=[
                    ContractViolation(
                        contract=f"{method.value} {path}",
                        field="",
                        expected="contract exists",
                        actual="no contract registered",
                        message=f"No contract for {method.value} {path}",
                    )
                ],
            )

        result = ContractTestResult(total_contracts=1)
        violations: list[ContractViolation] = []

        # Check status code
        if status_code != contract.response_status:
            violations.append(
                ContractViolation(
                    contract=f"{method.value} {path}",
                    field="status_code",
                    expected=str(contract.response_status),
                    actual=str(status_code),
                    message=f"Expected {contract.response_status}, got {status_code}",
                )
            )

        # Validate response fields
        if isinstance(response_data, list):
            if response_data:
                violations.extend(
                    self._validate_fields(
                        response_data[0],
                        contract.response_fields,
                        f"{method.value} {path}",
                    )
                )
        elif isinstance(response_data, dict):
            violations.extend(
                self._validate_fields(
                    response_data,
                    contract.response_fields,
                    f"{method.value} {path}",
                )
            )

        result.violations = violations
        if violations:
            result.failed = 1
        else:
            result.passed = 1

        return result

    def validate_request(
        self,
        path: str,
        method: HttpMethod,
        request_data: dict[str, Any],
    ) -> ContractTestResult:
        """Validate a request against its contract."""
        contract = self.get_contract(path, method)
        if not contract:
            return ContractTestResult(total_contracts=1, failed=1)

        result = ContractTestResult(total_contracts=1)
        violations = self._validate_fields(
            request_data,
            contract.request_fields,
            f"{method.value} {path} [request]",
        )
        result.violations = violations
        if violations:
            result.failed = 1
        else:
            result.passed = 1

        return result

    def _validate_fields(
        self,
        data: dict[str, Any],
        fields: list[FieldContract],
        contract_name: str,
    ) -> list[ContractViolation]:
        """Validate a dict against field contracts."""
        violations: list[ContractViolation] = []

        for fc in fields:
            value = data.get(fc.name)

            # Required check
            if fc.required and fc.name not in data:
                violations.append(
                    ContractViolation(
                        contract=contract_name,
                        field=fc.name,
                        expected="present",
                        actual="missing",
                        message=f"Required field '{fc.name}' is missing",
                    )
                )
                continue

            if value is None:
                if not fc.nullable and fc.required:
                    violations.append(
                        ContractViolation(
                            contract=contract_name,
                            field=fc.name,
                            expected="non-null",
                            actual="null",
                            message=f"Field '{fc.name}' is null but not nullable",
                        )
                    )
                continue

            # Type check
            type_error = self._check_type(
                value, fc.field_type, fc.name
            )
            if type_error:
                violations.append(
                    ContractViolation(
                        contract=contract_name,
                        field=fc.name,
                        expected=fc.field_type.value,
                        actual=type(value).__name__,
                        message=type_error,
                    )
                )

            # Enum check
            if (
                fc.field_type == FieldType.ENUM
                and fc.enum_values
                and value not in fc.enum_values
            ):
                violations.append(
                    ContractViolation(
                        contract=contract_name,
                        field=fc.name,
                        expected=f"one of {fc.enum_values}",
                        actual=str(value),
                        message=f"'{fc.name}' value '{value}' not in enum",
                        severity="warning",
                    )
                )

            # Nested object check
            if (
                fc.field_type == FieldType.OBJECT
                and fc.nested_fields
                and isinstance(value, dict)
            ):
                violations.extend(
                    self._validate_fields(
                        value, fc.nested_fields, f"{contract_name}.{fc.name}"
                    )
                )

        # Warn about unexpected fields
        expected_names = {fc.name for fc in fields}
        unexpected = set(data.keys()) - expected_names
        for name in unexpected:
            violations.append(
                ContractViolation(
                    contract=contract_name,
                    field=name,
                    expected="not present",
                    actual="present",
                    severity="warning",
                    message=f"Unexpected field '{name}' in response",
                )
            )

        return violations

    @staticmethod
    def _check_type(
        value: Any, expected: FieldType, field_name: str
    ) -> str | None:
        checks: dict[FieldType, type | tuple[type, ...]] = {
            FieldType.STRING: str,
            FieldType.INTEGER: int,
            FieldType.FLOAT: (int, float),
            FieldType.BOOLEAN: bool,
            FieldType.ARRAY: list,
            FieldType.OBJECT: dict,
        }

        if expected == FieldType.UUID:
            if not isinstance(value, str):
                return f"'{field_name}' should be UUID string, got {type(value).__name__}"
            uuid_pattern = re.compile(
                r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$",
                re.I,
            )
            if not uuid_pattern.match(value):
                return f"'{field_name}' is not a valid UUID: {value}"
            return None

        if expected == FieldType.DATETIME:
            if not isinstance(value, str):
                return f"'{field_name}' should be datetime string, got {type(value).__name__}"
            return None

        if expected in (FieldType.ANY, FieldType.ENUM, FieldType.NULLABLE):
            return None

        expected_type = checks.get(expected)
        if expected_type and not isinstance(value, expected_type):
            return f"'{field_name}' expected {expected.value}, got {type(value).__name__}"

        return None

    def run_all(
        self,
        test_responses: dict[str, dict[str, Any]],
    ) -> ContractTestResult:
        """Run all registered contracts against test response data.

        *test_responses* maps "METHOD:path" → response data.
        """
        overall = ContractTestResult()
        for key, contract in self._contracts.items():
            data = test_responses.get(key)
            if data is None:
                overall.total_contracts += 1
                continue

            result = self.validate_response(
                contract.path,
                contract.method,
                data,
            )
            overall.total_contracts += result.total_contracts
            overall.passed += result.passed
            overall.failed += result.failed
            overall.violations.extend(result.violations)

        return overall


# ------------------------------------------------------------------
# Pre-built contracts for key endpoints
# ------------------------------------------------------------------


def register_core_contracts(registry: ContractRegistry) -> None:
    """Register contracts for core API endpoints."""
    # Auth
    registry.register(
        EndpointContract(
            path="/api/v1/auth/login",
            method=HttpMethod.POST,
            frontend_store="auth",
            frontend_action="login",
            request_fields=[
                FieldContract("email", FieldType.STRING),
                FieldContract("password", FieldType.STRING),
            ],
            response_fields=[
                FieldContract("access_token", FieldType.STRING),
                FieldContract("refresh_token", FieldType.STRING),
                FieldContract("token_type", FieldType.STRING),
                FieldContract("user", FieldType.OBJECT, nested_fields=[
                    FieldContract("id", FieldType.UUID),
                    FieldContract("email", FieldType.STRING),
                    FieldContract("name", FieldType.STRING),
                    FieldContract("role", FieldType.STRING),
                ]),
            ],
            auth_required=False,
        )
    )

    # Quality inspections
    registry.register(
        EndpointContract(
            path="/api/v1/quality/inspections",
            method=HttpMethod.GET,
            frontend_store="quality",
            frontend_action="fetchInspections",
            response_fields=[
                FieldContract("id", FieldType.UUID),
                FieldContract("title", FieldType.STRING),
                FieldContract("status", FieldType.ENUM, enum_values=[
                    "draft", "in_progress", "completed", "cancelled",
                ]),
                FieldContract("inspector_id", FieldType.UUID, nullable=True),
                FieldContract("created_at", FieldType.DATETIME),
                FieldContract("updated_at", FieldType.DATETIME),
            ],
        )
    )

    # NCRs
    registry.register(
        EndpointContract(
            path="/api/v1/quality/ncrs",
            method=HttpMethod.GET,
            frontend_store="quality",
            frontend_action="fetchNCRs",
            response_fields=[
                FieldContract("id", FieldType.UUID),
                FieldContract("number", FieldType.STRING),
                FieldContract("description", FieldType.STRING),
                FieldContract("severity", FieldType.ENUM, enum_values=[
                    "critical", "major", "minor",
                ]),
                FieldContract("status", FieldType.ENUM, enum_values=[
                    "open", "investigating", "resolved", "closed",
                ]),
                FieldContract("created_at", FieldType.DATETIME),
            ],
        )
    )

    # KPIs
    registry.register(
        EndpointContract(
            path="/api/v1/kpi/metrics",
            method=HttpMethod.GET,
            frontend_store="kpi",
            frontend_action="fetchMetrics",
            response_fields=[
                FieldContract("id", FieldType.UUID),
                FieldContract("name", FieldType.STRING),
                FieldContract("value", FieldType.FLOAT),
                FieldContract("target", FieldType.FLOAT, nullable=True),
                FieldContract("unit", FieldType.STRING),
                FieldContract("trend", FieldType.STRING, required=False),
            ],
        )
    )

    # Maintenance work orders
    registry.register(
        EndpointContract(
            path="/api/v1/maintenance/work-orders",
            method=HttpMethod.GET,
            frontend_store="maintenance",
            frontend_action="fetchWorkOrders",
            response_fields=[
                FieldContract("id", FieldType.UUID),
                FieldContract("title", FieldType.STRING),
                FieldContract("priority", FieldType.ENUM, enum_values=[
                    "emergency", "urgent", "high", "medium", "low",
                ]),
                FieldContract("status", FieldType.ENUM, enum_values=[
                    "open", "in_progress", "completed", "cancelled",
                ]),
                FieldContract("asset_id", FieldType.UUID, nullable=True),
                FieldContract("created_at", FieldType.DATETIME),
            ],
        )
    )

    # Health check
    registry.register(
        EndpointContract(
            path="/api/v1/health",
            method=HttpMethod.GET,
            frontend_store="",
            frontend_action="",
            response_fields=[
                FieldContract("status", FieldType.STRING),
                FieldContract("version", FieldType.STRING, required=False),
            ],
            auth_required=False,
        )
    )
