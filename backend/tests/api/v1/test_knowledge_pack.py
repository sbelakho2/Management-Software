import pytest


@pytest.mark.asyncio
async def test_knowledge_pack_read_requires_reader_role(async_session):
    from unittest.mock import MagicMock

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from sensei.api import deps
    from sensei.api.deps import get_db
    from sensei.api.v1.endpoints import knowledge_pack

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_get_current_active_user():
        user = MagicMock()
        user.get_role_names.return_value = ["ceo"]
        user.id = "user-1"
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user

    app.include_router(knowledge_pack.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/knowledge-pack/sources")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["success"] is True
        assert isinstance(payload["data"], list)


@pytest.mark.asyncio
async def test_knowledge_pack_ingest_requires_curator(async_session):
    from unittest.mock import MagicMock

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from sensei.api import deps
    from sensei.api.deps import get_db
    from sensei.api.v1.endpoints import knowledge_pack

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_get_current_active_user():
        user = MagicMock()
        user.get_role_names.return_value = ["gm"]
        user.id = "user-1"
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user

    app.include_router(knowledge_pack.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge-pack/ingest",
            json={
                "source_id": "00000000-0000-0000-0000-000000000000",
                "content": "Hello",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_knowledge_pack_ingest_curator_success(async_session):
    from unittest.mock import MagicMock

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from sensei.api import deps
    from sensei.api.deps import get_db
    from sensei.api.v1.endpoints import knowledge_pack
    from sensei.models.strategic_v2 import KnowledgeSourceRecord

    app = FastAPI()

    source = KnowledgeSourceRecord(
        name="Test Source",
        source_type="internal_document",
        uri="test://source",
        is_active=True,
        metadata_fields={},
    )
    async_session.add(source)
    await async_session.commit()
    await async_session.refresh(source)

    async def override_get_db():
        yield async_session

    async def override_get_current_active_user():
        user = MagicMock()
        user.get_role_names.return_value = ["ml_engineer"]
        user.id = "user-1"
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user

    app.include_router(knowledge_pack.router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge-pack/ingest",
            json={
                "source_id": str(source.id),
                "content": "Paragraph one.\n\nParagraph two.",
                "chunk_size": 50,
                "overlap": 0,
            },
        )
        assert resp.status_code == 201
        payload = resp.json()
        assert payload["success"] is True
        assert payload["data"]["chunks"] >= 1
