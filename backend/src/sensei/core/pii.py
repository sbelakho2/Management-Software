from typing import Any
from sensei.services.core.pii_controls import PIIControlsService, PIICategory, MaskingType

_pii_service = PIIControlsService()

def get_pii_service() -> PIIControlsService:
    return _pii_service

async def mask_analytics_data(data: Any, roles: list[str]) -> Any:
    """Mask PII in analytics data based on user roles with granular control."""
    # admin, ceo, gm usually see everything
    is_top_exec = any(role in ["admin", "ceo", "gm"] for role in roles)
    is_hr = "hr" in roles
    is_finance = "finance" in roles
    
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
                    new_data[k] = await service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
            
            # Finance related PII
            elif k in ["salary", "budget_remaining", "unit_cost"]:
                if is_top_exec or is_finance:
                    new_data[k] = v
                else:
                    new_data[k] = "***" if k == "salary" else 0.0
            
            # Customer related PII
            elif k in ["customer_name", "contact_name"]:
                if is_top_exec or any(r in ["sales", "exec"] for r in roles):
                    new_data[k] = v
                else:
                    new_data[k] = await service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
                    
            elif isinstance(v, (dict, list)):
                new_data[k] = await mask_analytics_data(v, roles)
            else:
                new_data[k] = v
        return new_data
        
    return data
