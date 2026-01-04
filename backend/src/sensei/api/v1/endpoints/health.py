"""Health Check Endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness probe for Kubernetes/container orchestration."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> dict:
    """Liveness probe for Kubernetes/container orchestration."""
    return {"status": "alive"}
