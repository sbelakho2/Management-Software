import pytest


@pytest.mark.asyncio
async def test_dev_e2e_seed_lineage_roundtrip(async_session):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    from sensei.api.deps import get_current_user, get_db, get_token_data
    from sensei.api.v1.endpoints import context_bus, data_lineage, dev_e2e, quotes, rfqs
    from sensei.core.security import TokenData
    from sensei.models.user import User, UserStatus

    app = FastAPI()

    async def override_get_db():
        yield async_session

    # Create a real user row so audit foreign keys remain valid.
    user = User(
        email="e2e@test.local",
        username="e2e_test",
        password_hash="not-used",
        first_name="E2E",
        last_name="Test",
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
        email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    async def override_get_current_user():
        return user

    async def override_get_token_data() -> TokenData:
        now = datetime.now(timezone.utc)
        return TokenData(
            sub=str(user.id),
            type="access",
            exp=now + timedelta(hours=1),
            iat=now,
            jti=str(uuid4()),
            roles=["admin"],
            permissions=[],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_token_data] = override_get_token_data

    # Register the minimal set of routers needed for the E2E integrity flow.
    app.include_router(dev_e2e.router, prefix="/api/v1/dev", tags=["Dev"])
    app.include_router(rfqs.router, prefix="/api/v1/rfqs", tags=["RFQs"])
    app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["Quotes"])
    app.include_router(data_lineage.router, prefix="/api/v1/data-lineage", tags=["Data Lineage"])
    app.include_router(context_bus.router, prefix="/api/v1/context", tags=["Context"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        seed = await client.post("/api/v1/dev/e2e/seed-lineage")
        assert seed.status_code == 201
        seed_json = seed.json()
        assert seed_json["success"] is True
        seeded = seed_json["data"]

        rfq_id = seeded["rfq_id"]
        quote_id = seeded["quote_id"]
        rel = seeded["lineage_relationship_type"]

        rfq_get = await client.get(f"/api/v1/rfqs/{rfq_id}")
        assert rfq_get.status_code == 200

        quote_get = await client.get(f"/api/v1/quotes/{quote_id}")
        assert quote_get.status_code == 200

        lineage = await client.get(
            "/api/v1/data-lineage/graph",
            params={"entity_type": "rfq", "entity_id": rfq_id, "max_depth": 2},
        )
        assert lineage.status_code == 200
        lineage_json = lineage.json()
        assert lineage_json["success"] is True

        edges = lineage_json["data"]["edges"]
        assert any(
            e["source_entity_type"] == "rfq"
            and e["source_entity_id"] == rfq_id
            and e["target_entity_type"] == "quote"
            and e["target_entity_id"] == quote_id
            and e["relationship_type"] == rel
            for e in edges
        )

        ctx = await client.get(
            "/api/v1/context/pack",
            params={"entity_type": "rfq", "entity_id": rfq_id, "max_depth": 2},
        )
        assert ctx.status_code == 200
        ctx_json = ctx.json()
        assert ctx_json["success"] is True
        assert any(n["entity_type"] == "rfq" and n["entity_id"] == rfq_id for n in ctx_json["data"]["nodes"])
