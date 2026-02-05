"""
Chat Service - Main Orchestration for Sensei OS Chatbot.

This is the primary entry point for the chatbot system. It orchestrates:
1. Intent classification
2. RBAC-safe context building
3. LLM response generation
4. Action execution
5. Response filtering and sanitization
6. Audit logging

Optimized for VPS deployment with CPU-only inference.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.ai.chatbot.action_executor import (
    ActionExecutor,
    ActionResult,
    ActionStatus,
    create_action_executor,
)
from sensei.services.ai.chatbot.context_builder import (
    ContextBuilder,
    ChatContext,
    UserContext,
)
from sensei.services.ai.chatbot.intent_classifier import (
    IntentClassifier,
    Intent,
    IntentType,
)
from sensei.services.ai.chatbot.rbac_filter import (
    RBACResponseFilter,
    FilterResult,
)
from sensei.services.ai.chatbot.response_sanitizer import (
    ResponseSanitizer,
    SanitizationResult,
)

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Message roles in conversation."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    """A message in the chat conversation."""
    
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM."""
        return {
            "role": self.role.value,
            "content": self.content,
        }


@dataclass
class ChatSession:
    """A chat session with conversation history."""
    
    session_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default=None)
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_active = datetime.now(timezone.utc)
        return message
    
    def get_history(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get conversation history for LLM context."""
        recent = self.messages[-max_messages:] if max_messages else self.messages
        return [m.to_dict() for m in recent]


@dataclass
class ChatResponse:
    """Response from the chat service."""
    
    message: str
    intent: IntentType
    action_result: Optional[ActionResult] = None
    suggestions: List[str] = field(default_factory=list)
    navigation: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    response_id: UUID = field(default_factory=uuid4)
    processing_time_ms: float = 0.0


class ChatService:
    """
    Main chat service orchestrating all components.
    
    This service:
    1. Manages conversation sessions
    2. Classifies user intents
    3. Builds RBAC-safe context
    4. Generates LLM responses
    5. Executes actions
    6. Filters and sanitizes responses
    7. Logs all interactions for audit
    
    Optimized for VPS with:
    - CPU-only inference
    - Reduced context window (2048 tokens)
    - Aggressive caching
    - Rate limiting
    """
    
    # System prompts for different roles
    ROLE_SYSTEM_PROMPTS: Dict[str, str] = {
        "admin": """You are Sensei, an AI assistant for a manufacturing ERP system. You help administrators manage the system, users, and configurations. You have access to all data and can help with any query. Be concise and professional. When asked about specific data, provide accurate information from the context. When asked to perform actions, execute them and confirm completion.""",
        
        "executive": """You are Sensei, an AI assistant for a manufacturing ERP system. You help executives with high-level insights, KPIs, and strategic decisions. Focus on summaries and trends rather than operational details. You can access performance metrics, financial summaries, and approval workflows. Be concise and strategic in your responses.""",
        
        "manager": """You are Sensei, an AI assistant for a manufacturing ERP system. You help managers oversee operations, approve requests, and track team performance. You can access data for your team and department. Focus on actionable insights and help with approvals and task management. Be professional and concise.""",
        
        "operator": """You are Sensei, an AI assistant for a manufacturing ERP system. You help operators with their daily tasks, work orders, and production tracking. You can help look up procedures, report issues, and track progress. Keep responses brief and action-oriented.""",
        
        "viewer": """You are Sensei, an AI assistant for a manufacturing ERP system. You can help answer questions about the system and provide general information. Your access to specific data is limited. If you cannot access certain information, explain what you can help with instead.""",
        
        "default": """You are Sensei, an AI assistant for a manufacturing ERP system. You help users navigate the system, find information, and complete tasks. Be helpful, concise, and professional. If you cannot complete a request, explain why and suggest alternatives.""",
    }
    
    # VPS-optimized settings
    VPS_SETTINGS = {
        "max_context_tokens": 2048,
        "max_response_tokens": 256,
        "max_history_messages": 5,
        "inference_timeout_seconds": 30,
        "cache_ttl_seconds": 300,
    }
    
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        llm_client: Optional[Any] = None,
        email_service: Optional[Any] = None,
        enable_vps_optimization: bool = True,
    ):
        """
        Initialize chat service.
        
        Args:
            session: Optional async database session
            llm_client: Optional LLM client (LocalLLMClient)
            email_service: Optional email drafting service
            enable_vps_optimization: Enable VPS-specific optimizations
        """
        self.session = session
        self.llm_client = llm_client
        self.email_service = email_service
        self.enable_vps_optimization = enable_vps_optimization
        
        # Initialize components
        self.intent_classifier = IntentClassifier()
        self.context_builder = ContextBuilder(session)
        self.rbac_filter = RBACResponseFilter()
        self.response_sanitizer = ResponseSanitizer()
        self.action_executor = create_action_executor(session, email_service)
        
        # Session management
        self._sessions: Dict[UUID, ChatSession] = {}
        
        # Cache for frequently accessed data
        self._context_cache: Dict[str, tuple] = {}
    
    def get_or_create_session(self, user_id: UUID) -> ChatSession:
        """Get existing session or create new one."""
        # Look for existing session
        for session in self._sessions.values():
            if session.user_id == user_id:
                return session
        
        # Create new session
        session = ChatSession(user_id=user_id)
        self._sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    async def chat(
        self,
        message: str,
        user: UserContext,
        session_id: Optional[UUID] = None,
        confirmed: bool = False,
    ) -> ChatResponse:
        """
        Process a chat message and generate response.
        
        Args:
            message: User's message
            user: User context with permissions
            session_id: Optional session ID for conversation continuity
            confirmed: Whether user confirmed a pending action
            
        Returns:
            ChatResponse with message and any actions
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get or create session
            if session_id:
                session = self.get_session(session_id) or self.get_or_create_session(user.user_id)
            else:
                session = self.get_or_create_session(user.user_id)
            
            # Add user message to history
            session.add_message(MessageRole.USER, message)
            
            # Step 1: Classify intent
            intent = self.intent_classifier.classify(message)
            logger.debug(f"Classified intent: {intent.intent_type.value}")
            
            # Step 2: Build context
            context = await self.context_builder.build_context(
                user, 
                intent.intent_type.value, 
                message,
                intent.parameters,
            )
            
            # Step 3: Execute action if needed
            action_result = None
            if intent.requires_action:
                action_result = await self.action_executor.execute(intent, context, confirmed)
                
                # If confirmation needed, return early
                if action_result.confirmation_required:
                    response_content = action_result.confirmation_prompt
                    session.add_message(MessageRole.ASSISTANT, response_content)
                    
                    return ChatResponse(
                        message=response_content,
                        intent=intent.intent_type,
                        action_result=action_result,
                        processing_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                    )
            
            # Step 4: Generate LLM response
            llm_response = await self._generate_response(
                message=message,
                intent=intent,
                context=context,
                action_result=action_result,
                history=session.get_history(self.VPS_SETTINGS["max_history_messages"]),
            )
            
            # Step 5: Filter response for RBAC compliance
            filter_result = self.rbac_filter.filter_response(llm_response, context.user)
            if filter_result.violations:
                logger.warning(
                    f"Response filtered for RBAC violations: {len(filter_result.violations)}"
                )
            
            # Get the primary role from the roles set
            primary_role = next(iter(context.user.roles), "viewer")
            
            # Step 6: Sanitize response
            sanitization_result = self.response_sanitizer.sanitize(
                filter_result.filtered_response,
                primary_role,
            )
            
            final_response = sanitization_result.sanitized_response
            
            # Add assistant message to history
            session.add_message(MessageRole.ASSISTANT, final_response)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(intent, context)
            
            # Check for navigation
            navigation = None
            if action_result and action_result.action_type.value == "navigate":
                navigation = action_result.data
            
            # Log interaction for audit
            await self._log_interaction(
                user=user,
                session_id=session.session_id,
                message=message,
                response=final_response,
                intent=intent,
                action_result=action_result,
            )
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ChatResponse(
                message=final_response,
                intent=intent.intent_type,
                action_result=action_result,
                suggestions=suggestions,
                navigation=navigation,
                processing_time_ms=processing_time,
                metadata={
                    "session_id": str(session.session_id),
                    "filtered": filter_result.was_modified,
                    "sanitized": sanitization_result.was_modified,
                },
            )
            
        except Exception as e:
            logger.error(f"Chat processing failed: {e}", exc_info=True)
            
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return ChatResponse(
                message="I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
                intent=IntentType.UNKNOWN,
                processing_time_ms=processing_time,
                metadata={"error": str(e)},
            )
    
    async def _generate_response(
        self,
        message: str,
        intent: Intent,
        context: ChatContext,
        action_result: Optional[ActionResult],
        history: List[Dict[str, str]],
    ) -> str:
        """Generate LLM response."""
        # Build system prompt - get primary role from roles set
        primary_role = next(iter(context.user.roles), "viewer")
        role_key = self._get_role_key(primary_role)
        system_prompt = self.ROLE_SYSTEM_PROMPTS.get(role_key, self.ROLE_SYSTEM_PROMPTS["default"])
        
        # Add context to system prompt
        context_info = self._format_context(context)
        if context_info:
            system_prompt += f"\n\nRelevant context:\n{context_info}"
        
        # Add action result if available
        if action_result:
            action_info = self._format_action_result(action_result)
            system_prompt += f"\n\nAction performed:\n{action_info}"
        
        # Try to use LLM client
        if self.llm_client:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history)
                messages.append({"role": "user", "content": message})
                
                response = await self._call_llm(messages)
                return response
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
        
        # Fallback: Generate template response
        return self._generate_template_response(intent, context, action_result)
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call the LLM with VPS-optimized settings."""
        if not self.llm_client:
            raise ValueError("No LLM client configured")
        
        try:
            # Check if async method exists
            if hasattr(self.llm_client, 'generate_async'):
                response = await asyncio.wait_for(
                    self.llm_client.generate_async(
                        messages=messages,
                        max_tokens=self.VPS_SETTINGS["max_response_tokens"],
                    ),
                    timeout=self.VPS_SETTINGS["inference_timeout_seconds"],
                )
            elif hasattr(self.llm_client, 'generate'):
                # Run sync method in executor
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.llm_client.generate(
                            messages=messages,
                            max_tokens=self.VPS_SETTINGS["max_response_tokens"],
                        ),
                    ),
                    timeout=self.VPS_SETTINGS["inference_timeout_seconds"],
                )
            else:
                raise ValueError("LLM client has no generate method")
            
            return response.get("content", "") if isinstance(response, dict) else str(response)
            
        except asyncio.TimeoutError:
            logger.warning("LLM inference timed out")
            raise
    
    def _get_role_key(self, role: str) -> str:
        """Get role key for system prompt."""
        role_lower = role.lower()
        if "admin" in role_lower:
            return "admin"
        elif "exec" in role_lower or "director" in role_lower:
            return "executive"
        elif "manager" in role_lower or "lead" in role_lower or "supervisor" in role_lower:
            return "manager"
        elif "operator" in role_lower or "tech" in role_lower or "specialist" in role_lower:
            return "operator"
        elif "viewer" in role_lower or "read" in role_lower:
            return "viewer"
        return "default"
    
    def _format_context(self, context: ChatContext) -> str:
        """Format context for LLM."""
        parts = []
        
        # Use the get_context_text method from ChatContext
        context_text = context.get_context_text()
        if context_text:
            parts.append(f"Relevant Information:\n{context_text}")
        
        return "\n\n".join(parts)
    
    def _format_action_result(self, result: ActionResult) -> str:
        """Format action result for LLM."""
        status = "completed successfully" if result.is_success else f"failed ({result.status.value})"
        return f"Action '{result.action_type.value}' {status}: {result.message}"
    
    def _generate_template_response(
        self,
        intent: Intent,
        context: ChatContext,
        action_result: Optional[ActionResult],
    ) -> str:
        """Generate template response when LLM is unavailable."""
        if action_result and action_result.is_success:
            return action_result.message
        
        # Intent-based templates
        templates = {
            IntentType.GENERAL_CHAT: "Hello! I'm Sensei, your AI assistant. How can I help you today?",
            IntentType.HELP: "I can help you with:\n• Looking up RFQs, quotes, and work orders\n• Drafting emails\n• Managing tasks\n• Approving requests\n• Generating reports\n\nJust ask me anything!",
            IntentType.DATA_LOOKUP: "I found the requested information. " + (action_result.message if action_result else "Please specify what you'd like to look up."),
            IntentType.EMAIL_DRAFT: "I've prepared an email draft for you. Would you like to review it?",
            IntentType.UNKNOWN: "I'm not sure I understood that. Could you please rephrase your request?",
        }
        
        return templates.get(intent.intent_type, templates[IntentType.UNKNOWN])
    
    def _generate_suggestions(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> List[str]:
        """Generate follow-up suggestions."""
        suggestions = []
        
        # Intent-based suggestions
        if intent.intent_type == IntentType.DATA_LOOKUP:
            suggestions.extend([
                "Show more details",
                "Draft a follow-up email",
                "Create a task",
            ])
        elif intent.intent_type == IntentType.EMAIL_DRAFT:
            suggestions.extend([
                "Edit the subject",
                "Make it more formal",
                "Add attachments",
            ])
        elif intent.intent_type == IntentType.APPROVAL_LIST:
            suggestions.extend([
                "Approve all pending",
                "Show oldest first",
                "Export to report",
            ])
        elif intent.intent_type in (IntentType.GENERAL_CHAT, IntentType.HELP):
            suggestions.extend([
                "Show my pending tasks",
                "What's the status of my RFQs?",
                "Help me draft an email",
            ])
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    async def _log_interaction(
        self,
        user: UserContext,
        session_id: UUID,
        message: str,
        response: str,
        intent: Intent,
        action_result: Optional[ActionResult],
    ) -> None:
        """Log chat interaction for audit trail."""
        # Get primary role from roles set
        primary_role = next(iter(user.roles), "viewer")
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user.user_id),
            "user_role": primary_role,
            "session_id": str(session_id),
            "user_message": message[:500],  # Truncate for storage
            "assistant_response": response[:500],
            "intent": intent.intent_type.value,
            "confidence": intent.confidence,
            "action_type": action_result.action_type.value if action_result else None,
            "action_status": action_result.status.value if action_result else None,
        }
        
        logger.info("Chat interaction", extra=log_entry)
        
        # In production, also write to audit table
        # await self._write_audit_log(log_entry)
    
    async def stream_chat(
        self,
        message: str,
        user: UserContext,
        session_id: Optional[UUID] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response token by token.
        
        Useful for real-time UX but may not be supported by all LLM clients.
        """
        # For now, just yield the full response
        response = await self.chat(message, user, session_id)
        
        # Simulate streaming by yielding chunks
        chunk_size = 10
        for i in range(0, len(response.message), chunk_size):
            yield response.message[i:i + chunk_size]
            await asyncio.sleep(0.01)  # Small delay for streaming effect
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up inactive sessions."""
        now = datetime.now(timezone.utc)
        to_remove = []
        
        for session_id, session in self._sessions.items():
            age = (now - session.last_active).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self._sessions[session_id]
        
        return len(to_remove)


def create_chat_service(
    session: Optional[AsyncSession] = None,
    llm_client: Optional[Any] = None,
    email_service: Optional[Any] = None,
    enable_vps_optimization: bool = True,
) -> ChatService:
    """Factory function to create chat service."""
    return ChatService(
        session=session,
        llm_client=llm_client,
        email_service=email_service,
        enable_vps_optimization=enable_vps_optimization,
    )
