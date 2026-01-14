"""
Admin API Endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response, now_utc
from sensei.models.admin import AdminGate, ApprovalWorkflow, Template, LearningCadence, FeatureFlag
from sensei.models.user import Role, User

router = APIRouter()

# =============================================================================
# Schemas
# =============================================================================

class AdminStatsResponse(BaseModel):
    total_gates: int
    active_gates: int
    total_approvals: int
    active_approvals: int
    total_templates: int
    default_templates: int
    total_roles: int
    total_users: int
    total_learning_cadences: int
    active_learning_cadences: int
    total_feature_flags: int
    enabled_features: int

class AdminGateBase(BaseModel):
    name: str
    phase: str
    description: Optional[str] = None
    required_approvers: int = 1
    status: str = "active"
    order: int = 0
    bypass_roles: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)

class AdminGateResponse(AdminGateBase):
    id: str
    created_at: datetime
    updated_at: datetime

class AdminGateCreate(AdminGateBase):
    pass

class AdminGateUpdate(BaseModel):
    name: Optional[str] = None
    phase: Optional[str] = None
    description: Optional[str] = None
    required_approvers: Optional[int] = None
    status: Optional[str] = None
    order: Optional[int] = None
    bypass_roles: Optional[List[str]] = None
    conditions: Optional[List[str]] = None

class ReorderGatesRequest(BaseModel):
    gate_ids: List[str]

# Other schemas can be added similarly...

# =============================================================================
# Endpoints - Stats
# =============================================================================

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(db: DBSession) -> Any:
    """Get system-wide admin statistics."""
    # This is a simplified implementation. In a real app, you'd use count() queries.
    total_gates = db.query(AdminGate).count()
    active_gates = db.query(AdminGate).filter(AdminGate.status == "active").count()
    total_approvals = db.query(ApprovalWorkflow).count()
    active_approvals = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.is_active == True).count()
    total_templates = db.query(Template).count()
    default_templates = db.query(Template).filter(Template.is_default == True).count()
    total_roles = db.query(Role).count()
    total_users = db.query(User).count()
    total_learning_cadences = db.query(LearningCadence).count()
    active_learning_cadences = db.query(LearningCadence).filter(LearningCadence.is_active == True).count()
    total_feature_flags = db.query(FeatureFlag).count()
    enabled_features = db.query(FeatureFlag).filter(FeatureFlag.enabled == True).count()
    
    return AdminStatsResponse(
        total_gates=total_gates,
        active_gates=active_gates,
        total_approvals=total_approvals,
        active_approvals=active_approvals,
        total_templates=total_templates,
        default_templates=default_templates,
        total_roles=total_roles,
        total_users=total_users,
        total_learning_cadences=total_learning_cadences,
        active_learning_cadences=active_learning_cadences,
        total_feature_flags=total_feature_flags,
        enabled_features=enabled_features
    )

# =============================================================================
# Endpoints - Gates
# =============================================================================

@router.get("/gates", response_model=APIResponse[dict])
async def get_gates(db: DBSession) -> Any:
    """Get all admin gates."""
    gates = db.query(AdminGate).order_by(AdminGate.order).all()
    return build_response(data={"items": gates})

@router.post("/gates", response_model=AdminGateResponse)
async def create_gate(gate_in: AdminGateCreate, db: DBSession) -> Any:
    """Create a new admin gate."""
    gate = AdminGate(
        id=str(uuid.uuid4()),
        **gate_in.model_dump()
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate

@router.get("/gates/{gate_id}", response_model=AdminGateResponse)
async def get_gate(gate_id: str, db: DBSession) -> Any:
    """Get a specific admin gate."""
    gate = db.query(AdminGate).filter(AdminGate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    return gate

@router.patch("/gates/{gate_id}", response_model=AdminGateResponse)
async def update_gate(gate_id: str, gate_in: AdminGateUpdate, db: DBSession) -> Any:
    """Update an admin gate."""
    gate = db.query(AdminGate).filter(AdminGate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    update_data = gate_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gate, field, value)
    
    db.commit()
    db.refresh(gate)
    return gate

@router.delete("/gates/{gate_id}")
async def delete_gate(gate_id: str, db: DBSession) -> Any:
    """Delete an admin gate."""
    gate = db.query(AdminGate).filter(AdminGate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    db.delete(gate)
    db.commit()
    return {"success": True}

@router.post("/gates/reorder")
async def reorder_gates(request: ReorderGatesRequest, db: DBSession) -> Any:
    """Reorder gates."""
    for index, gate_id in enumerate(request.gate_ids):
        db.execute(
            update(AdminGate)
            .where(AdminGate.id == gate_id)
            .values(order=index + 1)
        )
    db.commit()
    return {"success": True}

# =============================================================================
# Endpoints - Approvals
# =============================================================================

@router.get("/approvals", response_model=APIResponse[dict])
async def get_approvals(db: DBSession) -> Any:
    """Get all approval workflows."""
    approvals = db.query(ApprovalWorkflow).all()
    return build_response(data={"items": approvals})

@router.post("/approvals", response_model=Any)
async def create_approval(approval_in: Any, db: DBSession) -> Any:
    """Create a new approval workflow."""
    approval = ApprovalWorkflow(
        id=str(uuid.uuid4()),
        **approval_in.model_dump() if hasattr(approval_in, "model_dump") else approval_in
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval

@router.patch("/approvals/{approval_id}", response_model=Any)
async def update_approval(approval_id: str, approval_in: Any, db: DBSession) -> Any:
    """Update an approval workflow."""
    approval = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    update_data = approval_in.model_dump(exclude_unset=True) if hasattr(approval_in, "model_dump") else approval_in
    for field, value in update_data.items():
        setattr(approval, field, value)
    
    db.commit()
    db.refresh(approval)
    return approval

@router.delete("/approvals/{approval_id}")
async def delete_approval(approval_id: str, db: DBSession) -> Any:
    """Delete an approval workflow."""
    approval = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    db.delete(approval)
    db.commit()
    return {"success": True}

# =============================================================================
# Endpoints - Templates
# =============================================================================

@router.get("/templates", response_model=APIResponse[dict])
async def get_templates(db: DBSession) -> Any:
    """Get all templates."""
    templates = db.query(Template).all()
    return build_response(data={"items": templates})

@router.post("/templates", response_model=Any)
async def create_template(template_in: Any, db: DBSession) -> Any:
    """Create a new template."""
    template = Template(
        id=str(uuid.uuid4()),
        **template_in.model_dump() if hasattr(template_in, "model_dump") else template_in
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

@router.patch("/templates/{template_id}", response_model=Any)
async def update_template(template_id: str, template_in: Any, db: DBSession) -> Any:
    """Update a template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_in.model_dump(exclude_unset=True) if hasattr(template_in, "model_dump") else template_in
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    return template

@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, db: DBSession) -> Any:
    """Delete a template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    return {"success": True}

# =============================================================================
# Endpoints - Learning Cadences
# =============================================================================

@router.get("/learning-cadences", response_model=APIResponse[dict])
async def get_learning_cadences(db: DBSession) -> Any:
    """Get all learning cadences."""
    cadences = db.query(LearningCadence).all()
    return build_response(data={"items": cadences})

@router.post("/learning-cadences", response_model=Any)
async def create_learning_cadence(cadence_in: Any, db: DBSession) -> Any:
    """Create a new learning cadence."""
    cadence = LearningCadence(
        id=str(uuid.uuid4()),
        **cadence_in.model_dump() if hasattr(cadence_in, "model_dump") else cadence_in
    )
    db.add(cadence)
    db.commit()
    db.refresh(cadence)
    return cadence

@router.patch("/learning-cadences/{cadence_id}", response_model=Any)
async def update_learning_cadence(cadence_id: str, cadence_in: Any, db: DBSession) -> Any:
    """Update a learning cadence."""
    cadence = db.query(LearningCadence).filter(LearningCadence.id == cadence_id).first()
    if not cadence:
        raise HTTPException(status_code=404, detail="Learning cadence not found")
    
    update_data = cadence_in.model_dump(exclude_unset=True) if hasattr(cadence_in, "model_dump") else cadence_in
    for field, value in update_data.items():
        setattr(cadence, field, value)
    
    db.commit()
    db.refresh(cadence)
    return cadence

@router.delete("/learning-cadences/{cadence_id}")
async def delete_learning_cadence(cadence_id: str, db: DBSession) -> Any:
    """Delete a learning cadence."""
    cadence = db.query(LearningCadence).filter(LearningCadence.id == cadence_id).first()
    if not cadence:
        raise HTTPException(status_code=404, detail="Learning cadence not found")
    
    db.delete(cadence)
    db.commit()
    return {"success": True}

# =============================================================================
# Endpoints - Feature Flags
# =============================================================================

@router.get("/feature-flags", response_model=APIResponse[dict])
async def get_feature_flags(db: DBSession) -> Any:
    """Get all feature flags."""
    flags = db.query(FeatureFlag).all()
    return build_response(data={"items": flags})

@router.patch("/feature-flags/{flag_id}", response_model=Any)
async def update_feature_flag(flag_id: str, flag_in: Any, db: DBSession) -> Any:
    """Update a feature flag."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    
    update_data = flag_in.model_dump(exclude_unset=True) if hasattr(flag_in, "model_dump") else flag_in
    for field, value in update_data.items():
        setattr(flag, field, value)
    
    db.commit()
    db.refresh(flag)
    return flag

# =============================================================================
# Endpoints - Roles
# =============================================================================

@router.get("/roles", response_model=APIResponse[dict])
async def get_roles(db: DBSession) -> Any:
    """Get all roles with member counts."""
    roles = db.query(Role).all()
    role_list = []
    for r in roles:
        # Actually calculate member count
        member_count = db.query(User).filter(User.roles.any(id=r.id)).count()
        role_dict = {
            "id": str(r.id),
            "name": r.name,
            "display_name": r.display_name,
            "description": r.description,
            "permissions": [p.permission.name for p in r.permissions],
            "member_count": member_count,
            "can_approve": True,
            "hierarchy_level": r.hierarchy_level
        }
        role_list.append(role_dict)
    return build_response(data={"items": role_list})
