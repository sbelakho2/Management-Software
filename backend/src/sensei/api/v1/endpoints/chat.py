"""
Chat API Endpoints for Sensei OS Chatbot.

Provides REST API endpoints for:
- Sending chat messages
- Managing chat sessions
- Streaming responses (SSE)
- Session cleanup
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import User
from sensei.services.ai.chatbot import (
    ChatService,
    ChatResponse,
    create_chat_service,
)
from sensei.services.ai.chatbot.context_builder import UserContext
from sensei.services.ai.chatbot.intent_classifier import IntentType

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["chat"],
)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""
    
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")
    session_id: Optional[UUID] = Field(None, description="Optional session ID for conversation continuity")
    confirmed: bool = Field(False, description="Whether user confirmed a pending action")


class ActionResultData(BaseModel):
    """Data from an executed action."""
    
    action_type: str
    status: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    confirmation_required: bool = False
    confirmation_prompt: str = ""


class ChatMessageResponse(BaseModel):
    """Response from a chat message."""
    
    message: str = Field(..., description="Assistant's response")
    intent: str = Field(..., description="Classified intent type")
    action_result: Optional[ActionResultData] = Field(None, description="Result of any executed action")
    suggestions: List[str] = Field(default_factory=list, description="Suggested follow-up queries")
    navigation: Optional[Dict[str, str]] = Field(None, description="Navigation target if applicable")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    processing_time_ms: float = Field(0.0, description="Processing time in milliseconds")


class SessionInfo(BaseModel):
    """Information about a chat session."""
    
    session_id: str
    user_id: str
    message_count: int
    created_at: datetime
    last_active: datetime


class SessionListResponse(BaseModel):
    """Response containing list of sessions."""
    
    sessions: List[SessionInfo]
    total: int


# ============================================================================
# Service Instance
# ============================================================================

# Global service instance (will be properly initialized with dependencies)
def get_chat_service(
    db: AsyncSession = Depends(deps.get_db),
) -> ChatService:
    """Get or create chat service instance - always uses current request's db session."""
    return create_chat_service(
        session=db,
        enable_vps_optimization=True,
    )


def build_user_context(user: User) -> UserContext:
    """Build UserContext from authenticated User model."""
    # Extract role names from the User→UserRole→Role relationship
    role_names: set[str] = set()
    permission_names: set[str] = set()
    if hasattr(user, 'roles') and user.roles:
        for user_role in user.roles:
            if hasattr(user_role, 'role') and user_role.role:
                role_names.add(user_role.role.name)
                # Gather permissions from each role
                if hasattr(user_role.role, 'permissions') and user_role.role.permissions:
                    for rp in user_role.role.permissions:
                        if hasattr(rp, 'permission') and rp.permission:
                            permission_names.add(f"{rp.permission.resource}:{rp.permission.action}")
    return UserContext(
        user_id=user.id,
        email=user.email,
        name=user.full_name or user.email,
        roles=role_names,
        permissions=permission_names,
        department=getattr(user, 'department', None),
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/message",
    response_model=APIResponse[ChatMessageResponse],
    summary="Send a chat message",
    description="Send a message to the chatbot and receive a response.",
)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(deps.get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[ChatMessageResponse]:
    """
    Send a message to the chatbot.
    
    The chatbot will:
    1. Classify the intent of your message
    2. Execute any relevant actions (data lookup, email drafting, etc.)
    3. Generate a response based on your permissions
    4. Return suggestions for follow-up queries
    """
    try:
        # Build user context
        user_context = build_user_context(current_user)
        
        # Process message
        response = await chat_service.chat(
            message=request.message,
            user=user_context,
            session_id=request.session_id,
            confirmed=request.confirmed,
        )
        
        # Build action result if present
        action_result_data = None
        if response.action_result:
            action_result_data = ActionResultData(
                action_type=response.action_result.action_type.value,
                status=response.action_result.status.value,
                message=response.action_result.message,
                data=response.action_result.data,
                confirmation_required=response.action_result.confirmation_required,
                confirmation_prompt=response.action_result.confirmation_prompt,
            )
        
        # Build response
        chat_response = ChatMessageResponse(
            message=response.message,
            intent=response.intent.value,
            action_result=action_result_data,
            suggestions=response.suggestions,
            navigation=response.navigation,
            session_id=response.metadata.get("session_id"),
            processing_time_ms=response.processing_time_ms,
        )
        
        return build_response(
            data=chat_response,
            message="Message processed successfully",
        )
        
    except Exception as e:
        logger.error(f"Chat message failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get(
    "/stream",
    summary="Stream chat response",
    description="Stream chat response using Server-Sent Events (SSE).",
)
async def stream_message(
    message: str = Query(..., min_length=1, max_length=4000),
    session_id: Optional[UUID] = Query(None),
    current_user: User = Depends(deps.get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """
    Stream chat response token by token.
    
    Uses Server-Sent Events (SSE) for real-time streaming.
    """
    user_context = build_user_context(current_user)
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in chat_service.stream_chat(
                message=message,
                user=user_context,
                session_id=session_id,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/sessions",
    response_model=APIResponse[SessionListResponse],
    summary="List chat sessions",
    description="List all active chat sessions for the current user.",
)
async def list_sessions(
    current_user: User = Depends(deps.get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[SessionListResponse]:
    """List all active chat sessions for the current user."""
    sessions = []
    
    for session_id, session in chat_service._sessions.items():
        if session.user_id == current_user.id:
            sessions.append(SessionInfo(
                session_id=str(session_id),
                user_id=str(session.user_id),
                message_count=len(session.messages),
                created_at=session.created_at,
                last_active=session.last_active,
            ))
    
    return build_response(
        data=SessionListResponse(
            sessions=sessions,
            total=len(sessions),
        ),
        message=f"Found {len(sessions)} active sessions",
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=APIResponse[Dict[str, bool]],
    summary="Delete a chat session",
    description="Delete a specific chat session.",
)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[Dict[str, bool]]:
    """Delete a specific chat session."""
    session = chat_service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's session",
        )
    
    del chat_service._sessions[session_id]
    
    return build_response(
        data={"deleted": True},
        message="Session deleted successfully",
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=APIResponse[List[Dict[str, str]]],
    summary="Get session history",
    description="Get the message history for a specific session.",
)
async def get_session_history(
    session_id: UUID,
    max_messages: int = Query(50, ge=1, le=100),
    current_user: User = Depends(deps.get_current_active_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[List[Dict[str, str]]]:
    """Get message history for a session."""
    session = chat_service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's session",
        )
    
    history = session.get_history(max_messages)
    
    return build_response(
        data=history,
        message=f"Retrieved {len(history)} messages",
    )


@router.post(
    "/sessions/cleanup",
    response_model=APIResponse[Dict[str, int]],
    summary="Cleanup inactive sessions",
    description="Remove inactive sessions older than specified hours (admin only).",
    dependencies=[Depends(deps.RoleChecker(["admin"]))],
)
async def cleanup_sessions(
    max_age_hours: int = Query(24, ge=1, le=720),
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[Dict[str, int]]:
    """Clean up inactive sessions (admin only)."""
    removed = chat_service.cleanup_inactive_sessions(max_age_hours)
    
    return build_response(
        data={"removed_sessions": removed},
        message=f"Removed {removed} inactive sessions",
    )


@router.get(
    "/intents",
    response_model=APIResponse[List[str]],
    summary="List available intents",
    description="List all supported intent types.",
)
async def list_intents() -> APIResponse[List[str]]:
    """List all supported intent types."""
    intents = [intent.value for intent in IntentType]
    
    return build_response(
        data=intents,
        message=f"Found {len(intents)} intent types",
    )


@router.get(
    "/health",
    response_model=APIResponse[Dict[str, Any]],
    summary="Chat service health",
    description="Check the health of the chat service.",
)
async def chat_health(
    chat_service: ChatService = Depends(get_chat_service),
) -> APIResponse[Dict[str, Any]]:
    """Check chat service health."""
    health_data = {
        "status": "healthy",
        "active_sessions": len(chat_service._sessions),
        "llm_available": chat_service.llm_client is not None,
        "vps_optimization": chat_service.enable_vps_optimization,
    }
    
    return build_response(
        data=health_data,
        message="Chat service is healthy",
    )
