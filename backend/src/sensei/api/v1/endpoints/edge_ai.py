from __future__ import annotations

from typing import Any, List, Optional
import anyio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from sensei.api.deps import CurrentUser
from sensei.api.utils import APIResponse, build_response
from sensei.core.config import settings
from sensei.services.core.edge_ai import (
    EdgeOrchestrator,
    AnomalyType,
    SyncPriority,
    MachineHealthStatus,
    SensorReading,
)

router = APIRouter()

# Singleton orchestrator
_orchestrator = EdgeOrchestrator(machine_id="system_core")

class SensorReadingRequest(BaseModel):
    sensor_id: str
    machine_id: str
    values: List[float]
    sample_rate: int
    reading_type: AnomalyType

@router.post("/inference", response_model=APIResponse)
async def run_inference(request: SensorReadingRequest, user: CurrentUser):
    """Run 1D-CNN inference on sensor data."""
    reading = SensorReading(
        sensor_id=request.sensor_id,
        machine_id=request.machine_id,
        timestamp=datetime.now(),
        values=request.values,
        sample_rate=request.sample_rate,
        reading_type=request.reading_type,
    )
    
    detection = await anyio.to_thread.run_sync(_orchestrator.run_inference, reading)
    return build_response(data=detection.__dict__ if detection else None)

@router.get("/machines/{machine_id}/health", response_model=APIResponse)
async def get_machine_health(machine_id: str, user: CurrentUser):
    """Get machine health status."""
    health = await anyio.to_thread.run_sync(_orchestrator.get_machine_health, machine_id)
    if not health:
        raise HTTPException(status_code=404, detail="Machine health data not found")
    return build_response(data=health.__dict__)

@router.post("/sync", response_model=APIResponse)
async def trigger_sync(user: CurrentUser):
    """Trigger a manual sync of edge messages to core."""
    result = await anyio.to_thread.run_sync(_orchestrator.sync_batch)
    return build_response(data=result.__dict__)

@router.get("/anomalies", response_model=APIResponse)
async def get_recent_anomalies(
    user: CurrentUser,  # noqa: ARG001
    machine_id: Optional[str] = None, 
    hours: int = 24, 
):
    """Get recent anomaly detections."""
    anomalies = await anyio.to_thread.run_sync(
        lambda: _orchestrator.get_recent_anomalies(machine_id=machine_id, hours=hours)
    )
    return build_response(data=[a.__dict__ for a in anomalies])
