import pytest


@pytest.mark.asyncio
async def test_ai_email_drafting_allows_ceo(async_session, monkeypatch):
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from uuid import uuid4

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from sensei.api import deps
    from sensei.api.deps import get_db
    from sensei.api.v1.endpoints import ai_email_drafting
    from sensei.core.security import TokenData
    from sensei.services.ai.ai_email_drafting import DraftStatus, GeneratedDraft

    app = FastAPI()

    async def override_get_db():
        yield async_session

    async def override_get_current_active_user():
        user = MagicMock()
        user.get_role_names.return_value = ["ceo"]
        user.id = "00000000-0000-0000-0000-000000000001"
        user.is_superuser = False
        return user

    async def override_get_token_data() -> TokenData:
        now = datetime.now(timezone.utc)
        return TokenData(
            sub="00000000-0000-0000-0000-000000000001",
            type="access",
            exp=now,
            iat=now,
            jti=str(uuid4()),
            roles=["ceo"],
            permissions=[],
        )

    def fake_generate_draft(_req):
        return GeneratedDraft(
            id="00000000-0000-0000-0000-000000000010",
            request_id="00000000-0000-0000-0000-000000000011",
            subject="Subject",
            body_plain="Body",
            body_html="<p>Body</p>",
            salutation="Hi",
            opening="Opening",
            main_content=["Line 1"],
            closing="Closing",
            signature="Sig",
            status=DraftStatus.READY,
            confidence_score=0.9,
            alternatives=[],
            compliance_issues=[],
            suggestions=[],
            tokens_used=1,
            generation_time_ms=5,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(ai_email_drafting._service, "generate_draft", fake_generate_draft)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user
    app.dependency_overrides[deps.get_token_data] = override_get_token_data

    app.include_router(ai_email_drafting.router, prefix="/api/v1/ai")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ai/email/generate",
            json={
                "recipient": {"email": "x@test.local"},
                "sender_name": "CEO",
                "sender_email": "ceo@test.local",
                "key_points": ["Point"],
            },
        )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["success"] is True
    assert payload["data"]["subject"] == "Subject"
