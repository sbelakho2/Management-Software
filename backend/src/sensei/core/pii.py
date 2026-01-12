from typing import Any
from sensei.services.core.pii_controls import PIIControlsService, PIICategory, MaskingType

_pii_service = PIIControlsService()

def get_pii_service() -> PIIControlsService:
    return _pii_service

def mask_analytics_data(data: Any, roles: list[str]) -> Any:
    """Mask PII in analytics data based on user roles."""
    # High-level roles can see everything
    if any(role in ["admin", "ceo", "gm", "exec"] for role in roles):
        return data
        
    service = get_pii_service()
    
    if isinstance(data, list):
        return [mask_analytics_data(item, roles) for item in data]
        
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # Mask known PII fields
            if k in ["employee_name", "operator_name", "customer_name", "contact_name"]:
                new_data[k] = service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
            elif k in ["email", "phone"]:
                new_data[k] = service.mask_value(str(v), masking_type=MaskingType.PARTIAL)
            elif isinstance(v, (dict, list)):
                new_data[k] = mask_analytics_data(v, roles)
            else:
                new_data[k] = v
        return new_data
        
    return data
