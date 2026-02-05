from typing import Any
import inspect
from sensei.services.core.pii_controls import PIIControlsService, PIICategory, MaskingType
from sensei.models.user import RoleType

_pii_service = PIIControlsService()

def get_pii_service() -> PIIControlsService:
    return _pii_service


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value

async def mask_analytics_data(data: Any, roles: list[str]) -> Any:
    """Mask PII in analytics data based on user roles with granular control."""
    def _normalize_role(raw: str) -> str:
        cleaned = raw.strip().lower().replace(" ", "_")
        if cleaned == "general_manager":
            return RoleType.GM.value
        if cleaned == "executive":
            return RoleType.EXEC.value
        return cleaned

    normalized_roles = {_normalize_role(r) for r in roles if isinstance(r, str)}

    # admin, ceo, gm usually see everything
    is_top_exec = any(role in {RoleType.ADMIN.value, RoleType.CEO.value, RoleType.GM.value} for role in normalized_roles)
    is_hr = RoleType.HR.value in normalized_roles
    is_finance = RoleType.FINANCE.value in normalized_roles
    
    service = get_pii_service()
    
    if isinstance(data, list):
        return [await mask_analytics_data(item, roles) for item in data]
        
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # HR related PII
            if k in ["employee_name", "operator_name", "email", "phone"]:
                if is_top_exec or is_hr:
                    new_data[k] = v
                else:
                    new_data[k] = await _maybe_await(service.mask_value(str(v), masking_type=MaskingType.PARTIAL))
            
            # Finance related PII
            elif k in ["salary", "budget_remaining", "unit_cost"]:
                if is_top_exec or is_finance:
                    new_data[k] = v
                else:
                    new_data[k] = "***" if k == "salary" else 0.0
            
            # Customer related PII
            elif k in ["customer_name", "contact_name"]:
                if is_top_exec or any(r in {RoleType.SALES.value, RoleType.EXEC.value} for r in normalized_roles):
                    new_data[k] = v
                else:
                    new_data[k] = await _maybe_await(service.mask_value(str(v), masking_type=MaskingType.PARTIAL))
                    
            elif isinstance(v, (dict, list)):
                new_data[k] = await mask_analytics_data(v, roles)
            else:
                new_data[k] = v
        return new_data
        
    return data
