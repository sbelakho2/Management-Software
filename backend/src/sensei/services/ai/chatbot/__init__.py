"""
Sensei OS Chatbot Service.

RBAC-aware conversational AI assistant for manufacturing operations.
Provides natural language interface for:
- Data queries with role-based filtering
- Email drafting with context
- Task management
- Reporting assistance
- Problem-solving guidance (A3, 5 Whys)

All responses are filtered through RBAC and PII controls.
"""

from sensei.services.ai.chatbot.chat_service import (
    ChatService,
    ChatMessage,
    ChatSession,
    ChatResponse,
    MessageRole,
    create_chat_service,
)
from sensei.services.ai.chatbot.intent_classifier import (
    IntentClassifier,
    Intent,
    IntentType,
)
from sensei.services.ai.chatbot.context_builder import (
    ContextBuilder,
    ChatContext,
)
from sensei.services.ai.chatbot.rbac_filter import (
    RBACResponseFilter,
    FilterResult,
)
from sensei.services.ai.chatbot.response_sanitizer import (
    ResponseSanitizer,
    SanitizationResult,
)
from sensei.services.ai.chatbot.action_executor import (
    ActionExecutor,
    ActionResult,
    ActionType,
)

__all__ = [
    # Main service
    "ChatService",
    "ChatMessage",
    "ChatSession",
    "ChatResponse",
    "MessageRole",
    "create_chat_service",
    # Intent classification
    "IntentClassifier",
    "Intent",
    "IntentType",
    # Context building
    "ContextBuilder",
    "ChatContext",
    # RBAC filtering
    "RBACResponseFilter",
    "FilterResult",
    # Sanitization
    "ResponseSanitizer",
    "SanitizationResult",
    # Action execution
    "ActionExecutor",
    "ActionResult",
    "ActionType",
]
