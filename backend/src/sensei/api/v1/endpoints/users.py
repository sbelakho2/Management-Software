"""User Management Endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
async def get_current_user() -> dict:
    """Get current authenticated user."""
    return {"message": "Current user endpoint - implementation in 1.3"}


@router.get("/")
async def list_users() -> dict:
    """List all users (admin only)."""
    return {"message": "List users endpoint - implementation in 1.3"}
