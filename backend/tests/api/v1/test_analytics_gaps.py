import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, Depends
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from sensei.api.v1.endpoints.analytics import router as analytics_router
from sensei.api.v1.endpoints.executive_intel import router as executive_router
from sensei.api.v1.endpoints.andon import router as andon_router
from sensei.api import deps
from sensei.core.security import TokenData

from datetime import datetime, timezone, timedelta

@pytest.fixture
def app():
    application = FastAPI()
    application.include_router(analytics_router, prefix="/api/v1/analytics")
    application.include_router(executive_router, prefix="/api/v1/executive")
    application.include_router(andon_router, prefix="/api/v1/andon")
    return application

async def mock_get_token_data_admin():
    return TokenData(
        sub=str(uuid4()),
        type="access",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        jti=str(uuid4()),
        roles=["admin"],
        permissions=[]
    )

async def mock_get_token_data_operator():
    return TokenData(
        sub=str(uuid4()),
        type="access",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        jti=str(uuid4()),
        roles=["operator"],
        permissions=[]
    )

async def mock_get_current_user():
    user = MagicMock()
    user.id = uuid4()
    user.role = "admin"
    user.status = "active"
    return user

@pytest.mark.asyncio
async def test_analytics_rbac_admin(app):
    app.dependency_overrides[deps.get_token_data] = mock_get_token_data_admin
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/analytics/trends")
    assert response.status_code == 200
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_analytics_rbac_operator(app):
    app.dependency_overrides[deps.get_token_data] = mock_get_token_data_operator
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/analytics/trends")
    # Operator is not in ["admin", "ceo", "gm", "exec", "ops", "finance", "quality"]
    assert response.status_code == 403
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_andon_analytics_endpoint(app):
    app.dependency_overrides[deps.get_token_data] = mock_get_token_data_admin
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    # Need to mock DB for this one
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
    
    app.dependency_overrides[deps.get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/andon/analytics")
    
    if response.status_code != 200:
        print(f"DEBUG_LOG: Response body: {response.json()}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "avg_response_time_minutes" in data
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_executive_intel_rbac(app):
    payload = {"question": "How many open non conformances?"}
    
    # Admin access
    app.dependency_overrides[deps.get_token_data] = mock_get_token_data_admin
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    # Mock DB
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())
    app.dependency_overrides[deps.get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/executive/nl2sql", json=payload)
    assert response.status_code == 200
    
    # Operator denied
    app.dependency_overrides[deps.get_token_data] = mock_get_token_data_operator
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/executive/nl2sql", json=payload)
    assert response.status_code == 403
    app.dependency_overrides.clear()
