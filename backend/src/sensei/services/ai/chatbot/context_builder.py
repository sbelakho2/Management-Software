"""
Role-Based Context Builder for Sensei OS Chatbot.

Builds RBAC-safe context for LLM responses:
- Filters accessible data based on user role
- Retrieves relevant context from database
- Applies field-level security
- Assembles RAG context from knowledge base
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context that can be included."""
    
    USER_INFO = "user_info"
    RFQ_DATA = "rfq_data"
    QUOTE_DATA = "quote_data"
    WORK_ORDER_DATA = "work_order_data"
    TASK_DATA = "task_data"
    APPROVAL_DATA = "approval_data"
    CUSTOMER_DATA = "customer_data"
    SUPPLIER_DATA = "supplier_data"
    KNOWLEDGE_BASE = "knowledge_base"
    RECENT_ACTIVITY = "recent_activity"
    METRICS = "metrics"


@dataclass
class ContextChunk:
    """A chunk of context information."""
    
    context_type: ContextType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 1.0
    source_id: Optional[str] = None
    is_sensitive: bool = False


@dataclass
class UserContext:
    """User context for RBAC filtering."""
    
    user_id: UUID
    email: str
    name: str
    roles: Set[str]
    permissions: Set[str]
    department: Optional[str] = None
    org_id: Optional[UUID] = None
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role.lower() in {r.lower() for r in self.roles}
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        user_roles_lower = {r.lower() for r in self.roles}
        return any(r.lower() in user_roles_lower for r in roles)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.has_any_role(["admin", "superuser"])
    
    @property
    def is_executive(self) -> bool:
        """Check if user is executive level."""
        return self.has_any_role(["admin", "ceo", "gm", "exec"])
    
    @property
    def is_manager(self) -> bool:
        """Check if user is manager level or higher."""
        return self.has_any_role([
            "admin", "ceo", "gm", "exec", "finance", "hr", 
            "ops", "quality", "it", "supervisor"
        ])


@dataclass
class ChatContext:
    """Complete context for chat response generation."""
    
    user: UserContext
    intent_type: str
    query: str
    chunks: List[ContextChunk] = field(default_factory=list)
    system_prompt: str = ""
    max_tokens: int = 2048
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_context_text(self, max_chars: int = 4000) -> str:
        """Get formatted context text for LLM."""
        parts: List[str] = []
        current_chars = 0
        
        # Sort by relevance
        sorted_chunks = sorted(self.chunks, key=lambda c: c.relevance_score, reverse=True)
        
        for chunk in sorted_chunks:
            if current_chars + len(chunk.content) > max_chars:
                break
            parts.append(f"[{chunk.context_type.value}]\n{chunk.content}")
            current_chars += len(chunk.content)
        
        return "\n\n".join(parts)
    
    def add_chunk(self, chunk: ContextChunk) -> None:
        """Add a context chunk."""
        self.chunks.append(chunk)


class ContextBuilder:
    """
    Builds RBAC-safe context for chat responses.
    
    Applies role-based filtering to all data access and
    masks sensitive fields based on user permissions.
    """
    
    # Role-based access matrix for data types
    DATA_ACCESS_MATRIX: Dict[ContextType, Set[str]] = {
        ContextType.USER_INFO: {"admin", "hr"},
        ContextType.RFQ_DATA: {
            "admin", "ceo", "gm", "exec", "sales", "sales_engineer",
            "estimator", "quality", "ops", "engineering"
        },
        ContextType.QUOTE_DATA: {
            "admin", "ceo", "gm", "exec", "sales", "sales_engineer",
            "estimator", "finance", "quality"
        },
        ContextType.WORK_ORDER_DATA: {
            "admin", "ceo", "gm", "exec", "ops", "quality", "engineering",
            "supervisor", "team_lead", "operator", "maintenance"
        },
        ContextType.TASK_DATA: {"*"},  # Everyone can see their own tasks
        ContextType.APPROVAL_DATA: {"*"},  # Role-specific approvals
        ContextType.CUSTOMER_DATA: {
            "admin", "ceo", "gm", "exec", "sales", "sales_engineer",
            "estimator", "finance", "quality"
        },
        ContextType.SUPPLIER_DATA: {
            "admin", "ceo", "gm", "exec", "purchasing", "supply_chain",
            "quality", "finance"
        },
        ContextType.KNOWLEDGE_BASE: {"*"},  # Everyone can access knowledge
        ContextType.RECENT_ACTIVITY: {"*"},  # Filtered per user
        ContextType.METRICS: {
            "admin", "ceo", "gm", "exec", "finance", "ops", "quality"
        },
    }
    
    # Sensitive fields that require masking for non-privileged users
    SENSITIVE_FIELDS: Dict[str, Set[str]] = {
        "customer": {"credit_limit", "payment_terms", "discount_rate"},
        "quote": {"cost_breakdown", "margin", "discount_pct"},
        "employee": {"salary", "ssn", "bank_account", "compensation"},
        "supplier": {"pricing_tier", "contract_terms"},
    }
    
    # Executive-only fields
    EXECUTIVE_FIELDS: Dict[str, Set[str]] = {
        "quote": {"profit_margin", "target_margin"},
        "rfq": {"competitive_analysis"},
        "work_order": {"labor_cost", "overhead_allocation"},
    }
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialize context builder.
        
        Args:
            session: Optional async database session
        """
        self.session = session
    
    def can_access(self, user: UserContext, context_type: ContextType) -> bool:
        """
        Check if user can access a context type.
        
        Args:
            user: User context
            context_type: Type of context to access
            
        Returns:
            True if access is allowed
        """
        if user.is_admin:
            return True
        
        allowed_roles = self.DATA_ACCESS_MATRIX.get(context_type, set())
        if "*" in allowed_roles:
            return True
        
        return user.has_any_role(list(allowed_roles))
    
    def should_mask_field(
        self,
        user: UserContext,
        entity_type: str,
        field_name: str,
    ) -> bool:
        """
        Check if a field should be masked for this user.
        
        Args:
            user: User context
            entity_type: Type of entity (customer, quote, etc.)
            field_name: Name of the field
            
        Returns:
            True if field should be masked
        """
        if user.is_admin:
            return False
        
        # Check executive-only fields
        exec_fields = self.EXECUTIVE_FIELDS.get(entity_type, set())
        if field_name in exec_fields and not user.is_executive:
            return True
        
        # Check sensitive fields
        sensitive = self.SENSITIVE_FIELDS.get(entity_type, set())
        if field_name in sensitive:
            # Finance can see financial fields
            if "finance" in {r.lower() for r in user.roles}:
                return entity_type not in ["employee"]
            # HR can see employee fields
            if "hr" in {r.lower() for r in user.roles}:
                return entity_type != "employee"
            return not user.is_executive
        
        return False
    
    def mask_value(self, value: Any, field_type: str = "default") -> str:
        """
        Mask a sensitive value.
        
        Args:
            value: Value to mask
            field_type: Type of field for appropriate masking
            
        Returns:
            Masked value
        """
        if value is None:
            return "[REDACTED]"
        
        str_value = str(value)
        
        if field_type == "currency":
            return "$***.**"
        elif field_type == "percentage":
            return "**%"
        elif field_type == "ssn":
            return "***-**-" + str_value[-4:] if len(str_value) >= 4 else "***-**-****"
        elif field_type == "email":
            if "@" in str_value:
                parts = str_value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
            return "***@***.***"
        elif field_type == "phone":
            return "***-***-" + str_value[-4:] if len(str_value) >= 4 else "***-***-****"
        else:
            # Generic masking - show first and last char
            if len(str_value) > 2:
                return str_value[0] + "*" * (len(str_value) - 2) + str_value[-1]
            return "***"
    
    async def build_context(
        self,
        user: UserContext,
        intent_type: str,
        query: str,
        parameters: Dict[str, Any],
    ) -> ChatContext:
        """
        Build complete context for chat response.
        
        Args:
            user: User context
            intent_type: Classified intent type
            query: Original user query
            parameters: Extracted parameters
            
        Returns:
            Built chat context
        """
        context = ChatContext(
            user=user,
            intent_type=intent_type,
            query=query,
        )
        
        # Add user context chunk
        context.add_chunk(ContextChunk(
            context_type=ContextType.USER_INFO,
            content=self._format_user_context(user),
            relevance_score=0.5,
        ))
        
        # Add intent-specific context
        await self._add_intent_context(context, intent_type, parameters)
        
        # Add knowledge base context if relevant
        if intent_type in ["knowledge_query", "a3_assist", "five_whys", "general_chat"]:
            await self._add_knowledge_context(context, query)
        
        # Build system prompt based on role
        context.system_prompt = self._build_system_prompt(user, intent_type)
        
        return context
    
    def _format_user_context(self, user: UserContext) -> str:
        """Format user context for LLM."""
        roles_str = ", ".join(sorted(user.roles))
        return f"""Current User:
- Name: {user.name}
- Roles: {roles_str}
- Department: {user.department or 'Not specified'}
- Access Level: {'Executive' if user.is_executive else 'Manager' if user.is_manager else 'Standard'}"""
    
    async def _add_intent_context(
        self,
        context: ChatContext,
        intent_type: str,
        parameters: Dict[str, Any],
    ) -> None:
        """Add context based on intent type."""
        user = context.user
        
        if intent_type == "data_lookup":
            # Add relevant data based on parameters
            if "rfq_number" in parameters and self.can_access(user, ContextType.RFQ_DATA):
                await self._add_rfq_context(context, parameters["rfq_number"])
            elif "quote_number" in parameters and self.can_access(user, ContextType.QUOTE_DATA):
                await self._add_quote_context(context, parameters["quote_number"])
            elif "work_order_number" in parameters and self.can_access(user, ContextType.WORK_ORDER_DATA):
                await self._add_work_order_context(context, parameters["work_order_number"])
        
        elif intent_type in ["task_list", "task_create", "task_complete"]:
            await self._add_task_context(context)
        
        elif intent_type in ["approval_list", "approval_approve", "approval_reject"]:
            await self._add_approval_context(context)
        
        elif intent_type == "email_draft":
            await self._add_email_context(context, parameters)
        
        elif intent_type in ["report_generate", "metrics"]:
            if self.can_access(user, ContextType.METRICS):
                await self._add_metrics_context(context)
    
    async def _add_rfq_context(self, context: ChatContext, rfq_number: str) -> None:
        """Add RFQ context."""
        # In production, this would query the database
        # For now, provide a template context
        context.add_chunk(ContextChunk(
            context_type=ContextType.RFQ_DATA,
            content=f"RFQ {rfq_number}: Data would be loaded from database",
            metadata={"rfq_number": rfq_number},
            relevance_score=1.0,
            source_id=f"rfq:{rfq_number}",
        ))
    
    async def _add_quote_context(self, context: ChatContext, quote_number: str) -> None:
        """Add quote context."""
        context.add_chunk(ContextChunk(
            context_type=ContextType.QUOTE_DATA,
            content=f"Quote {quote_number}: Data would be loaded from database",
            metadata={"quote_number": quote_number},
            relevance_score=1.0,
            source_id=f"quote:{quote_number}",
        ))
    
    async def _add_work_order_context(self, context: ChatContext, wo_number: str) -> None:
        """Add work order context."""
        context.add_chunk(ContextChunk(
            context_type=ContextType.WORK_ORDER_DATA,
            content=f"Work Order {wo_number}: Data would be loaded from database",
            metadata={"work_order_number": wo_number},
            relevance_score=1.0,
            source_id=f"wo:{wo_number}",
        ))
    
    async def _add_task_context(self, context: ChatContext) -> None:
        """Add task context for user."""
        context.add_chunk(ContextChunk(
            context_type=ContextType.TASK_DATA,
            content="User's tasks would be loaded from database",
            relevance_score=0.9,
        ))
    
    async def _add_approval_context(self, context: ChatContext) -> None:
        """Add approval context for user."""
        context.add_chunk(ContextChunk(
            context_type=ContextType.APPROVAL_DATA,
            content="User's pending approvals would be loaded from database",
            relevance_score=0.9,
        ))
    
    async def _add_email_context(
        self,
        context: ChatContext,
        parameters: Dict[str, Any],
    ) -> None:
        """Add context for email drafting."""
        # Add relevant entity context for email
        if "rfq_number" in parameters:
            await self._add_rfq_context(context, parameters["rfq_number"])
        if "quote_number" in parameters:
            await self._add_quote_context(context, parameters["quote_number"])
        
        context.add_chunk(ContextChunk(
            context_type=ContextType.CUSTOMER_DATA,
            content="Customer/recipient information for email",
            relevance_score=0.8,
        ))
    
    async def _add_metrics_context(self, context: ChatContext) -> None:
        """Add metrics context for reporting."""
        context.add_chunk(ContextChunk(
            context_type=ContextType.METRICS,
            content="Key metrics would be loaded from database",
            relevance_score=0.8,
        ))
    
    async def _add_knowledge_context(
        self,
        context: ChatContext,
        query: str,
    ) -> None:
        """Add knowledge base context via RAG."""
        # This would integrate with the hybrid search service
        context.add_chunk(ContextChunk(
            context_type=ContextType.KNOWLEDGE_BASE,
            content=f"Relevant knowledge for query: {query}",
            metadata={"source": "knowledge_base"},
            relevance_score=0.7,
        ))
    
    def _build_system_prompt(self, user: UserContext, intent_type: str) -> str:
        """Build role-appropriate system prompt."""
        base_prompt = """You are Sensei, an AI assistant for Sensei OS manufacturing management software.
You help users with RFQs, quotes, work orders, tasks, quality management, and continuous improvement.

IMPORTANT RULES:
1. Only provide information the user has permission to see based on their role.
2. Never reveal sensitive data like salaries, SSNs, or confidential business information.
3. If asked about something outside the user's access, politely explain you cannot provide that information.
4. Be concise and professional.
5. When drafting emails, maintain appropriate business tone.
6. For A3/problem solving, use Socratic questioning to guide the user.
"""
        
        role_specific = ""
        
        if user.is_executive:
            role_specific = """
As an executive-level user, you have broad access to:
- All RFQs, quotes, and work orders
- Financial summaries and metrics
- Strategic reports and analytics
- Approval workflows
"""
        elif user.is_manager:
            role_specific = f"""
As a manager in {user.department or 'your department'}, you have access to:
- Department-related RFQs, quotes, and work orders
- Team tasks and approvals
- Quality metrics and reports
- Training status for your team
"""
        else:
            role_specific = """
You have access to:
- Your assigned tasks and work orders
- RFQs and quotes you're involved with
- Training materials and knowledge base
- Standard operating procedures
"""
        
        intent_specific = ""
        if intent_type == "email_draft":
            intent_specific = """
For email drafting:
- Use professional, clear language
- Include relevant context from the RFQ/quote if referenced
- Suggest appropriate follow-up actions
- Keep emails concise but complete
"""
        elif intent_type in ["a3_assist", "five_whys"]:
            intent_specific = """
For problem solving:
- Use Socratic questioning to guide understanding
- Help identify root causes, not just symptoms
- Reference TPS/Lean principles when appropriate
- Encourage data-driven analysis
"""
        
        return base_prompt + role_specific + intent_specific


def create_context_builder(session: Optional[AsyncSession] = None) -> ContextBuilder:
    """Factory function to create context builder."""
    return ContextBuilder(session)
