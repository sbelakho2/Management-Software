from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from sensei.api.deps import get_current_user, get_db, get_token_data
from sensei.api.exceptions import register_exception_handlers
from sensei.api.v1.endpoints.project_management import router as pm_router
from sensei.core.security import TokenData
from sensei.models.user import User, UserStatus


@pytest_asyncio.fixture
async def app(async_session):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(pm_router, prefix="/project-management")

    # Create a real user in the DB (no mocks)
    admin_user = User(
        email="pmtest@example.com",
        username="pmtest",
        password_hash="not-a-real-hash",
        first_name="PM",
        last_name="Tester",
        display_name="PM Tester",
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
        email_verified=True,
    )

    regular_user = User(
        email="pmtest2@example.com",
        username="pmtest2",
        password_hash="not-a-real-hash",
        first_name="PM2",
        last_name="Tester2",
        display_name="PM Tester 2",
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
        email_verified=True,
    )

    async_session.add_all([admin_user, regular_user])
    await async_session.commit()
    await async_session.refresh(admin_user)
    await async_session.refresh(regular_user)

    app.state.users = {
        "admin": admin_user,
        "regular": regular_user,
    }
    app.state.current_user = admin_user

    async def _override_get_db():
        yield async_session

    async def _override_get_current_user():
        return app.state.current_user

    async def _override_get_token_data() -> TokenData:
        now = datetime.now(timezone.utc)
        current = app.state.current_user
        roles = ["admin"] if current == app.state.users["admin"] else ["ops"]
        return TokenData(
            sub=str(current.id),
            type="access",
            exp=now + timedelta(hours=1),
            iat=now,
            jti=str(uuid4()),
            roles=roles,
            permissions=[],
        )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_token_data] = _override_get_token_data
    return app


@pytest.mark.asyncio
async def test_project_crud_and_membership(app):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        resp = await client.post(
            "/project-management/projects",
            json={"name": "Alpha Project", "description": "Test", "is_private": True},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        project = body["data"]
        assert project["name"] == "Alpha Project"
        assert project["slug"] == "alpha-project"

        project_id = project["id"]

        # List projects
        resp = await client.get("/project-management/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["pagination"]["total_items"] >= 1
        assert any(p["id"] == project_id for p in body["data"])

        # Get project
        resp = await client.get(f"/project-management/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == project_id

        # Update project
        resp = await client.patch(
            f"/project-management/projects/{project_id}",
            json={"status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

        # Add member (upsert)
        # use same user as member
        user_id = resp.json()["data"]["owner_id"]
        resp = await client.post(
            f"/project-management/projects/{project_id}/members",
            json={"user_id": user_id, "role": "admin", "can_delete": True},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "admin"

        resp = await client.get(f"/project-management/projects/{project_id}/members")
        assert resp.status_code == 200
        members = resp.json()["data"]
        assert any(m["user_id"] == user_id for m in members)

        # Remove member
        resp = await client.delete(f"/project-management/projects/{project_id}/members/{user_id}")
        assert resp.status_code == 200

        resp = await client.get(f"/project-management/projects/{project_id}/members")
        assert resp.status_code == 200
        assert all(m["user_id"] != user_id for m in resp.json()["data"])


@pytest.mark.asyncio
async def test_epic_story_subtask_comment_flow(app):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create project
        resp = await client.post("/project-management/projects", json={"name": "Beta"})
        project_id = resp.json()["data"]["id"]

        # Create epic
        resp = await client.post(
            "/project-management/epics",
            json={"project_id": project_id, "subject": "Epic 1"},
        )
        assert resp.status_code == 200
        epic = resp.json()["data"]
        assert epic["ref"] == 1

        # Epics are project-scoped: cross-project linking should not be allowed.
        resp = await client.post("/project-management/projects", json={"name": "Gamma"})
        assert resp.status_code == 200
        other_project_id = resp.json()["data"]["id"]

        resp = await client.post(
            "/project-management/epics",
            json={"project_id": other_project_id, "subject": "Epic 2"},
        )
        assert resp.status_code == 200
        other_epic_id = resp.json()["data"]["id"]

        # Create sprint
        resp = await client.post(
            "/project-management/sprints",
            json={
                "project_id": project_id,
                "name": "Sprint 1",
                "start_date": "2026-01-01",
                "end_date": "2026-01-14",
            },
        )
        assert resp.status_code == 200
        sprint_id = resp.json()["data"]["id"]

        # Create user story (linked)
        resp = await client.post(
            "/project-management/user-stories",
            json={
                "project_id": project_id,
                "subject": "Story 1",
                "epic_id": epic["id"],
                "sprint_id": sprint_id,
                "priority": 80,
            },
        )
        assert resp.status_code == 200
        story = resp.json()["data"]
        assert story["ref"] == 1
        assert story["priority"] == 80

        resp = await client.post(
            "/project-management/user-stories",
            json={
                "project_id": project_id,
                "subject": "Story invalid epic",
                "epic_id": other_epic_id,
                "sprint_id": sprint_id,
            },
        )
        assert resp.status_code == 404

        # Create two subtasks (ref increments)
        resp = await client.post(
            "/project-management/subtasks",
            json={"user_story_id": story["id"], "subject": "Sub 1"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["ref"] == 1

        resp = await client.post(
            "/project-management/subtasks",
            json={"user_story_id": story["id"], "subject": "Sub 2"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["ref"] == 2

        resp = await client.get(f"/project-management/user-stories/{story['id']}/subtasks")
        assert resp.status_code == 200
        assert [s["ref"] for s in resp.json()["data"]] == [1, 2]

        # Close subtask
        subtask_id = resp.json()["data"][0]["id"]
        resp = await client.patch(f"/project-management/subtasks/{subtask_id}", json={"is_closed": True})
        assert resp.status_code == 200
        assert resp.json()["data"]["is_closed"] is True

        # Comment on story
        resp = await client.post(
            "/project-management/story-comments",
            json={"user_story_id": story["id"], "content": "Looks good"},
        )
        assert resp.status_code == 200

        resp = await client.get(f"/project-management/user-stories/{story['id']}/story-comments")
        assert resp.status_code == 200
        comments = resp.json()["data"]
        assert len(comments) == 1
        assert comments[0]["content"] == "Looks good"


@pytest.mark.asyncio
async def test_private_project_permissions(app):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a private project as admin
        app.state.current_user = app.state.users["admin"]
        resp = await client.post(
            "/project-management/projects",
            json={"name": "Private Project", "description": "Test", "is_private": True},
        )
        assert resp.status_code == 200
        project_id = resp.json()["data"]["id"]

        # Regular user should not see or access it
        app.state.current_user = app.state.users["regular"]
        resp = await client.get("/project-management/projects")
        assert resp.status_code == 200
        assert all(p["id"] != project_id for p in resp.json()["data"])

        resp = await client.get(f"/project-management/projects/{project_id}")
        assert resp.status_code == 403

        # Admin invites regular user, but only with comment permission
        app.state.current_user = app.state.users["admin"]
        regular_id = app.state.users["regular"].id
        resp = await client.post(
            f"/project-management/projects/{project_id}/members",
            json={
                "user_id": str(regular_id),
                "role": "member",
                "can_comment": True,
                "can_edit": False,
                "can_invite": False,
                "can_delete": False,
            },
        )
        assert resp.status_code == 200

        # Regular user can now read the project
        app.state.current_user = app.state.users["regular"]
        resp = await client.get(f"/project-management/projects/{project_id}")
        assert resp.status_code == 200

        # But cannot edit the project
        resp = await client.patch(f"/project-management/projects/{project_id}", json={"description": "Nope"})
        assert resp.status_code == 403

        # Create an epic/sprint/story as admin, then regular can comment on the story
        app.state.current_user = app.state.users["admin"]
        resp = await client.post("/project-management/epics", json={"project_id": project_id, "subject": "Epic"})
        assert resp.status_code == 200

        resp = await client.post("/project-management/sprints", json={"project_id": project_id, "name": "Sprint"})
        assert resp.status_code == 422
        resp = await client.post(
            "/project-management/sprints",
            json={
                "project_id": project_id,
                "name": "Sprint",
                "start_date": "2026-01-01",
                "end_date": "2026-01-14",
            },
        )
        assert resp.status_code == 200
        sprint_id = resp.json()["data"]["id"]

        resp = await client.post(
            "/project-management/user-stories",
            json={"project_id": project_id, "subject": "Story", "sprint_id": sprint_id},
        )
        assert resp.status_code == 200
        story_id = resp.json()["data"]["id"]

        app.state.current_user = app.state.users["regular"]

        # Comment allowed
        resp = await client.post(
            "/project-management/story-comments",
            json={"user_story_id": story_id, "content": "ok"},
        )
        assert resp.status_code == 200

        # Creating a user story requires edit permission
        resp = await client.post(
            "/project-management/user-stories",
            json={"project_id": project_id, "subject": "Should fail"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_issue_milestone_wiki_permissions_and_flow(app):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a private project as admin
        app.state.current_user = app.state.users["admin"]
        resp = await client.post(
            "/project-management/projects",
            json={"name": "PM With Issues", "is_private": True},
        )
        assert resp.status_code == 200
        project_id = resp.json()["data"]["id"]

        # Create milestone as admin
        resp = await client.post(
            "/project-management/milestones",
            json={
                "project_id": project_id,
                "name": "Release 1",
                "milestone_type": "deadline",
                "due_date": "2026-02-01",
            },
        )
        assert resp.status_code == 200
        milestone_id = resp.json()["data"]["id"]

        # Create issue as admin (linked to milestone)
        resp = await client.post(
            "/project-management/issues",
            json={
                "project_id": project_id,
                "subject": "Bug 1",
                "milestone_id": milestone_id,
                "issue_type": "bug",
                "severity": "normal",
                "priority": "normal",
                "status": "new",
            },
        )
        assert resp.status_code == 200
        issue = resp.json()["data"]
        assert issue["ref"] == 1
        issue_id = issue["id"]

        # Invite regular user as comment-only member
        regular_id = app.state.users["regular"].id
        resp = await client.post(
            f"/project-management/projects/{project_id}/members",
            json={
                "user_id": str(regular_id),
                "role": "member",
                "can_comment": True,
                "can_edit": False,
                "can_invite": False,
                "can_delete": False,
            },
        )
        assert resp.status_code == 200

        # Regular user can read project-scoped lists
        app.state.current_user = app.state.users["regular"]
        resp = await client.get(f"/project-management/projects/{project_id}/issues")
        assert resp.status_code == 200
        assert any(i["id"] == issue_id for i in resp.json()["data"])

        resp = await client.get(f"/project-management/projects/{project_id}/milestones")
        assert resp.status_code == 200
        assert any(m["id"] == milestone_id for m in resp.json()["data"])

        # But cannot create issues/milestones/wiki pages without edit permission
        resp = await client.post(
            "/project-management/issues",
            json={"project_id": project_id, "subject": "Should fail"},
        )
        assert resp.status_code == 403

        resp = await client.post(
            "/project-management/milestones",
            json={
                "project_id": project_id,
                "name": "Should fail",
                "due_date": "2026-03-01",
            },
        )
        assert resp.status_code == 403

        resp = await client.post(
            "/project-management/wiki-pages",
            json={"project_id": project_id, "title": "Should fail", "content": "x"},
        )
        assert resp.status_code == 403

        # Commenting on issue is allowed
        resp = await client.post(
            f"/project-management/issues/{issue_id}/comments",
            json={"content": "ack"},
        )
        assert resp.status_code == 200

        resp = await client.get(f"/project-management/issues/{issue_id}/comments")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["content"] == "ack"

        # Admin creates wiki page; regular user can read it
        app.state.current_user = app.state.users["admin"]
        resp = await client.post(
            "/project-management/wiki-pages",
            json={
                "project_id": project_id,
                "title": "Runbook",
                "content": "Hello",
                "page_type": "documentation",
            },
        )
        assert resp.status_code == 200
        wiki_id = resp.json()["data"]["id"]

        app.state.current_user = app.state.users["regular"]
        resp = await client.get(f"/project-management/projects/{project_id}/wiki-pages")
        assert resp.status_code == 200
        assert any(p["id"] == wiki_id for p in resp.json()["data"])
