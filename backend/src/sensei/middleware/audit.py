"""
Audit Middleware

Writes audit log entries for mutating HTTP requests.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Callable
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response

from sensei.core.database import async_session_factory
from sensei.core.security import decode_token
from sensei.models.audit_log import AuditLog
from sensei.models.user import User

_logger = logging.getLogger(__name__)


_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/audit-logs",
    "/api/v1/security-audit",
)
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _extract_entity(path: str) -> tuple[str, str | None]:
    path = path.split("?")[0]
    parts = [p for p in path.split("/") if p]
    entity_type = "unknown"
    if len(parts) >= 2 and parts[0] == "api" and parts[1] == "v1":
        entity_type = parts[2] if len(parts) > 2 else "root"
    elif parts:
        entity_type = parts[0]

    entity_id = None
    for part in parts:
        if _UUID_RE.fullmatch(part):
            entity_id = part
            break
    return entity_type, entity_id


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to write audit logs for mutating requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if request.method not in _MUTATING_METHODS:
            return response

        # Only audit successful mutations (2xx/3xx) — failed requests
        # (4xx/5xx) didn't change state and just waste a DB session (#127).
        if response.status_code >= 400:
            return response

        path = request.url.path
        if path.startswith(_SKIP_PREFIXES):
            return response

        entity_type, entity_id = _extract_entity(path)
        correlation_id = getattr(request.state, "correlation_id", None)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        token = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]

        user_id = None
        user_email = None
        if token:
            try:
                token_data = decode_token(token, "access")
                try:
                    user_id = UUID(token_data.sub)
                except Exception:
                    user_id = None
            except Exception:
                pass

        # Prefer request.state.user if available
        state_user = getattr(request.state, "user", None)
        if state_user is not None:
            user_email = getattr(state_user, "email", None)

        async def _write_audit() -> None:
            try:
                async with async_session_factory() as session:
                    resolved_email = user_email
                    if resolved_email is None and user_id is not None:
                        result = await session.execute(
                            select(User.email).where(User.id == user_id)
                        )
                        resolved_email = result.scalar_one_or_none()
                    log = AuditLog.create_log(
                        entity_type=entity_type,
                        entity_id=entity_id or path,
                        action=request.method.lower(),
                        user_id=user_id,
                        user_email=resolved_email,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_id=correlation_id,
                        description=f"{request.method} {path} -> {response.status_code}",
                        metadata={
                            "status_code": response.status_code,
                            "path": path,
                        },
                    )
                    session.add(log)
                    await session.commit()
            except Exception:
                _logger.exception("Failed to write audit log for %s %s", request.method, path)

        asyncio.create_task(_write_audit())
        return response
