from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sensei.models.quoting_helper import DisciplineType, WorkPacketStatus


class WorkPacketBase(BaseModel):
    """Base Work Packet fields."""
    
    discipline: DisciplineType
    status: WorkPacketStatus = WorkPacketStatus.PENDING
    due_at: Optional[datetime] = None
    owner_id: Optional[UUID] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    blocker_reason: Optional[str] = None


class WorkPacketCreate(WorkPacketBase):
    """Schema for creating a work packet."""
    
    rfq_id: UUID


class WorkPacketUpdate(BaseModel):
    """Schema for updating a work packet."""
    
    status: Optional[WorkPacketStatus] = None
    owner_id: Optional[UUID] = None
    outputs: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    blocker_reason: Optional[str] = None


class WorkPacketRead(WorkPacketBase):
    """Schema for reading a work packet."""
    
    id: UUID
    rfq_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PCBSpecBase(BaseModel):
    """Base PCB Spec fields."""
    
    layers: Optional[int] = None
    finish: Optional[str] = None
    thickness_mm: Optional[Decimal] = None
    size_x_mm: Optional[Decimal] = None
    size_y_mm: Optional[Decimal] = None
    impedance_req: bool = False
    copper_weight_oz: Optional[Decimal] = None
    min_trace_width_mm: Optional[Decimal] = None
    min_hole_size_mm: Optional[Decimal] = None


class PCBSpecRead(PCBSpecBase):
    """Schema for reading a PCB spec."""
    
    id: UUID
    rfq_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


class RateCardBase(BaseModel):
    """Base Rate Card fields."""
    
    name: str
    is_active: bool = True
    labor_rate_hourly: Decimal
    smt_placement_rate: Decimal
    setup_charge: Decimal
    default_yield_multiplier: Decimal = Decimal("1.02")
    scrap_rate_multiplier: Decimal = Decimal("1.01")
    rules: Dict[str, Any] = Field(default_factory=dict)


class RateCardRead(RateCardBase):
    """Schema for reading a rate card."""
    
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)


class QuoteActualBase(BaseModel):
    """Base Quote Actual fields."""
    
    quoted_material_cost: Decimal
    actual_material_cost: Decimal
    quoted_labor_minutes: int
    actual_labor_minutes: int
    quoted_yield: Decimal
    actual_yield: Decimal
    variance_notes: Optional[str] = None
    root_cause_categories: List[str] = Field(default_factory=list)


class QuoteActualRead(QuoteActualBase):
    """Schema for reading a quote actual."""
    
    id: UUID
    quote_id: UUID
    
    model_config = ConfigDict(from_attributes=True)
