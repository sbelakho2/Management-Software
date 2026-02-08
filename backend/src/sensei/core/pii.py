"""
PII (Personally Identifiable Information) masking utilities (#43, #280).

Provides role-aware PII masking for analytics/reporting data. Field
classifications are stored in a configurable registry rather than
hard-coded ``if k in [...]`` checks, and the module-level singleton
is created lazily to avoid import-time side effects.

Key improvements over initial version:
- Configurable PII field registry (add fields without editing this file)
- Lazy singleton via ``get_pii_service()`` (no module-level instantiation)
- Recursion depth guard (``MAX_RECURSION_DEPTH = 32``) to prevent stack
  overflow on deeply nested / circular structures
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, FrozenSet, Optional, Set
import inspect
import logging

from sensei.services.core.pii_controls import PIIControlsService, PIICategory, MaskingType
from sensei.models.user import RoleType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton (#280 — avoid module-level instantiation)
# ---------------------------------------------------------------------------

_pii_service: Optional[PIIControlsService] = None

MAX_RECURSION_DEPTH = 32  # guard against circular / deeply nested structures


def get_pii_service() -> PIIControlsService:
    """Return (and lazily create) the PII controls singleton."""
    global _pii_service
    if _pii_service is None:
        _pii_service = PIIControlsService()
    return _pii_service


# ---------------------------------------------------------------------------
# Configurable PII field registry (#43 — no more hardcoded field lists)
# ---------------------------------------------------------------------------

class PIIFieldCategory(str, Enum):
    """Categories of PII fields and the role groups allowed to view them."""
    HR = "hr"
    FINANCE = "finance"
    CUSTOMER = "customer"


# Default masking value for finance fields that aren't "salary"
_FINANCE_NUMERIC_MASK = 0.0

# Registry: category → set of field names
_PII_FIELD_REGISTRY: Dict[PIIFieldCategory, Set[str]] = {
    PIIFieldCategory.HR: {
        "employee_name", "operator_name", "email", "phone",
        "home_address", "emergency_contact", "ssn", "national_id",
        "date_of_birth", "personal_email", "mobile_phone",
    },
    PIIFieldCategory.FINANCE: {
        "salary", "budget_remaining", "unit_cost",
        "bonus", "compensation", "bank_account", "tax_id",
    },
    PIIFieldCategory.CUSTOMER: {
        "customer_name", "contact_name",
        "customer_email", "customer_phone", "billing_address",
    },
}

# Precomputed frozen sets for O(1) lookup
_HR_FIELDS: FrozenSet[str] = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.HR])
_FINANCE_FIELDS: FrozenSet[str] = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.FINANCE])
_CUSTOMER_FIELDS: FrozenSet[str] = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.CUSTOMER])


def register_pii_field(category: PIIFieldCategory, field_name: str) -> None:
    """Add a field to the PII registry at runtime (e.g. from plugin config)."""
    global _HR_FIELDS, _FINANCE_FIELDS, _CUSTOMER_FIELDS

    _PII_FIELD_REGISTRY[category].add(field_name)
    # Rebuild frozen lookup sets
    _HR_FIELDS = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.HR])
    _FINANCE_FIELDS = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.FINANCE])
    _CUSTOMER_FIELDS = frozenset(_PII_FIELD_REGISTRY[PIIFieldCategory.CUSTOMER])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _normalize_role(raw: str) -> str:
    cleaned = raw.strip().lower().replace(" ", "_")
    if cleaned == "general_manager":
        return RoleType.GM.value
    if cleaned == "executive":
        return RoleType.EXEC.value
    return cleaned


# ---------------------------------------------------------------------------
# Main masking function
# ---------------------------------------------------------------------------

async def mask_analytics_data(
    data: Any,
    roles: list[str],
    *,
    _depth: int = 0,
) -> Any:
    """Mask PII in analytics data based on user roles with granular control.

    Uses the configurable ``_PII_FIELD_REGISTRY`` for field classification
    and includes a recursion depth guard (``MAX_RECURSION_DEPTH``).
    """
    # Recursion guard (#280)
    if _depth > MAX_RECURSION_DEPTH:
        logger.warning("PII masking hit max recursion depth (%d); returning data unmasked", MAX_RECURSION_DEPTH)
        return data

    normalized_roles = {_normalize_role(r) for r in roles if isinstance(r, str)}

    # admin, ceo, gm usually see everything
    is_top_exec = any(
        role in {RoleType.ADMIN.value, RoleType.CEO.value, RoleType.GM.value}
        for role in normalized_roles
    )
    is_hr = RoleType.HR.value in normalized_roles
    is_finance = RoleType.FINANCE.value in normalized_roles
    is_sales = any(
        r in {RoleType.SALES.value, RoleType.EXEC.value}
        for r in normalized_roles
    )

    service = get_pii_service()

    if isinstance(data, list):
        return [await mask_analytics_data(item, roles, _depth=_depth + 1) for item in data]

    if isinstance(data, dict):
        new_data: dict[str, Any] = {}
        for k, v in data.items():
            # HR related PII
            if k in _HR_FIELDS:
                if is_top_exec or is_hr:
                    new_data[k] = v
                else:
                    new_data[k] = await _maybe_await(
                        service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
                    )

            # Finance related PII
            elif k in _FINANCE_FIELDS:
                if is_top_exec or is_finance:
                    new_data[k] = v
                else:
                    new_data[k] = "***" if k == "salary" else _FINANCE_NUMERIC_MASK

            # Customer related PII
            elif k in _CUSTOMER_FIELDS:
                if is_top_exec or is_sales:
                    new_data[k] = v
                else:
                    new_data[k] = await _maybe_await(
                        service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
                    )

            elif isinstance(v, (dict, list)):
                new_data[k] = await mask_analytics_data(v, roles, _depth=_depth + 1)
            else:
                new_data[k] = v
        return new_data

    return data
