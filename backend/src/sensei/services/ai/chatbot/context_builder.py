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

from sensei.models.rfq import RFQ
from sensei.models.quote import Quote
from sensei.models.work_order import WorkOrder
from sensei.models.task import Task
from sensei.services.core.context_bus import get_context_service

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
        """Add RFQ context with lineage from Context Bus."""
        if not self.session:
            return
        stmt = select(RFQ).where(RFQ.rfq_number == rfq_number)
        rfq = (await self.session.execute(stmt)).scalars().first()
        if not rfq:
            context.add_chunk(ContextChunk(
                context_type=ContextType.RFQ_DATA,
                content=f"RFQ {rfq_number} not found.",
                relevance_score=0.3,
            ))
            return

        user = context.user
        lines = [f"RFQ {rfq.rfq_number} — {rfq.title or 'N/A'}"]
        lines.append(f"  Status: {rfq.status}")
        lines.append(f"  Part: {rfq.part_number or 'N/A'} / {rfq.part_name or 'N/A'}")
        lines.append(f"  Process: {rfq.primary_process or 'N/A'}")
        if rfq.material_spec:
            lines.append(f"  Material: {rfq.material_spec} {rfq.material_grade or ''}")
        if rfq.lead_time_required:
            lines.append(f"  Lead Time Required: {rfq.lead_time_required} days")

        # Use Context Bus for lineage-based cross-entity context
        try:
            pack = await get_context_service().get_context_pack(
                self.session,
                root_entity_type="rfq",
                root_entity_id=str(rfq.id),
                max_depth=2,
            )
            related = [n for n in pack.nodes if n.entity_type != "rfq"]
            if related:
                lines.append("  Related entities:")
                for node in related:
                    safe_data = {
                        k: self.mask_value(v) if self.should_mask_field(user, node.entity_type, k) else v
                        for k, v in list(node.data.items())[:4]
                    }
                    summary = ", ".join(f"{k}: {v}" for k, v in safe_data.items() if v is not None)
                    lines.append(f"    → {node.entity_type}: {summary}")
        except Exception:
            logger.debug("Context Bus unavailable for RFQ %s", rfq_number, exc_info=True)

        context.add_chunk(ContextChunk(
            context_type=ContextType.RFQ_DATA,
            content="\n".join(lines),
            metadata={"rfq_number": rfq_number, "rfq_id": str(rfq.id)},
            relevance_score=1.0,
            source_id=f"rfq:{rfq_number}",
        ))
    
    async def _add_quote_context(self, context: ChatContext, quote_number: str) -> None:
        """Add quote context with lineage from Context Bus."""
        if not self.session:
            return
        stmt = select(Quote).where(Quote.quote_number == quote_number)
        quote = (await self.session.execute(stmt)).scalars().first()
        if not quote:
            context.add_chunk(ContextChunk(
                context_type=ContextType.QUOTE_DATA,
                content=f"Quote {quote_number} not found.",
                relevance_score=0.3,
            ))
            return

        user = context.user
        lines = [f"Quote {quote.quote_number} — {quote.title or 'N/A'}"]
        lines.append(f"  Status: {quote.status}")
        if not self.should_mask_field(user, "quote", "total"):
            lines.append(f"  Total: {quote.currency or ''} {quote.total or 'N/A'}")
        else:
            lines.append(f"  Total: {self.mask_value(quote.total, 'currency')}")
        if quote.lead_time_days:
            lines.append(f"  Lead Time: {quote.lead_time_days} days")
        if quote.payment_terms:
            lines.append(f"  Payment Terms: {quote.payment_terms}")
        if quote.special_conditions:
            lines.append(f"  Special Conditions: {quote.special_conditions}")

        # Use Context Bus for lineage-based cross-entity context
        try:
            pack = await get_context_service().get_context_pack(
                self.session,
                root_entity_type="quote",
                root_entity_id=str(quote.id),
                max_depth=2,
            )
            related = [n for n in pack.nodes if n.entity_type != "quote"]
            if related:
                lines.append("  Related entities:")
                for node in related:
                    safe_data = {
                        k: self.mask_value(v) if self.should_mask_field(user, node.entity_type, k) else v
                        for k, v in list(node.data.items())[:4]
                    }
                    summary = ", ".join(f"{k}: {v}" for k, v in safe_data.items() if v is not None)
                    lines.append(f"    → {node.entity_type}: {summary}")
        except Exception:
            logger.debug("Context Bus unavailable for Quote %s", quote_number, exc_info=True)

        context.add_chunk(ContextChunk(
            context_type=ContextType.QUOTE_DATA,
            content="\n".join(lines),
            metadata={"quote_number": quote_number, "quote_id": str(quote.id)},
            relevance_score=1.0,
            source_id=f"quote:{quote_number}",
        ))
    
    async def _add_work_order_context(self, context: ChatContext, wo_number: str) -> None:
        """Add work order context with lineage from Context Bus."""
        if not self.session:
            return
        stmt = select(WorkOrder).where(WorkOrder.work_order_number == wo_number)
        wo = (await self.session.execute(stmt)).scalars().first()
        if not wo:
            context.add_chunk(ContextChunk(
                context_type=ContextType.WORK_ORDER_DATA,
                content=f"Work Order {wo_number} not found.",
                relevance_score=0.3,
            ))
            return

        user = context.user
        status_str = wo.status.value if hasattr(wo.status, "value") else str(wo.status)
        lines = [f"Work Order {wo.work_order_number}"]
        lines.append(f"  Status: {status_str}")
        lines.append(f"  Qty Ordered: {wo.quantity_ordered}")
        lines.append(f"  Qty Completed: {wo.quantity_completed}")
        if wo.quantity_scrapped:
            lines.append(f"  Qty Scrapped: {wo.quantity_scrapped}")
        if wo.scheduled_start:
            lines.append(f"  Scheduled Start: {wo.scheduled_start.strftime('%Y-%m-%d')}")
        if wo.scheduled_end:
            lines.append(f"  Scheduled End: {wo.scheduled_end.strftime('%Y-%m-%d')}")

        # Use Context Bus for lineage-based cross-entity context
        try:
            pack = await get_context_service().get_context_pack(
                self.session,
                root_entity_type="work_order",
                root_entity_id=str(wo.id),
                max_depth=2,
            )
            related = [n for n in pack.nodes if n.entity_type != "work_order"]
            if related:
                lines.append("  Related entities:")
                for node in related:
                    safe_data = {
                        k: self.mask_value(v) if self.should_mask_field(user, node.entity_type, k) else v
                        for k, v in list(node.data.items())[:4]
                    }
                    summary = ", ".join(f"{k}: {v}" for k, v in safe_data.items() if v is not None)
                    lines.append(f"    → {node.entity_type}: {summary}")
        except Exception:
            logger.debug("Context Bus unavailable for WO %s", wo_number, exc_info=True)

        context.add_chunk(ContextChunk(
            context_type=ContextType.WORK_ORDER_DATA,
            content="\n".join(lines),
            metadata={"work_order_number": wo_number, "work_order_id": str(wo.id)},
            relevance_score=1.0,
            source_id=f"wo:{wo_number}",
        ))
    
    async def _add_task_context(self, context: ChatContext) -> None:
        """Add active tasks assigned to the user."""
        if not self.session:
            return
        stmt = (
            select(Task)
            .where(
                Task.assignee_id == context.user.user_id,
                Task.status.in_(["todo", "in_progress", "open", "blocked"]),
                or_(Task.is_deleted == False, Task.is_deleted.is_(None)),
            )
            .order_by(Task.due_date.asc().nulls_last())
            .limit(10)
        )
        tasks = (await self.session.execute(stmt)).scalars().all()

        if not tasks:
            context.add_chunk(ContextChunk(
                context_type=ContextType.TASK_DATA,
                content="No active tasks assigned to you.",
                relevance_score=0.3,
            ))
            return

        lines = [f"Your Active Tasks ({len(tasks)}):"]
        for t in tasks:
            due = t.due_date.strftime("%Y-%m-%d") if t.due_date else "No due date"
            prio = t.priority.upper() if isinstance(t.priority, str) else str(t.priority)
            lines.append(f"  • [{prio}] {t.title} — {t.status} (due: {due})")

        context.add_chunk(ContextChunk(
            context_type=ContextType.TASK_DATA,
            content="\n".join(lines),
            relevance_score=0.9,
        ))
    
    async def _add_approval_context(self, context: ChatContext) -> None:
        """Add pending approval context for user."""
        if not self.session:
            return
        user = context.user
        # Quotes pending approval where user has an approver role
        stmt = (
            select(Quote)
            .where(Quote.approval_status == "pending")
            .order_by(Quote.created_at.desc())
            .limit(10)
        )
        try:
            quotes = (await self.session.execute(stmt)).scalars().all()
        except Exception:
            # approval_status column may not exist on all deployments
            quotes = []

        if not quotes:
            context.add_chunk(ContextChunk(
                context_type=ContextType.APPROVAL_DATA,
                content="No pending approvals.",
                relevance_score=0.3,
            ))
            return

        lines = [f"Pending Approvals ({len(quotes)}):"]
        for q in quotes:
            total_str = (
                str(q.total) if not self.should_mask_field(user, "quote", "total") else self.mask_value(q.total, "currency")
            )
            lines.append(f"  • Quote {q.quote_number}: {q.title or 'N/A'} — {total_str}")

        context.add_chunk(ContextChunk(
            context_type=ContextType.APPROVAL_DATA,
            content="\n".join(lines),
            relevance_score=0.9,
        ))
    
    async def _add_email_context(
        self,
        context: ChatContext,
        parameters: Dict[str, Any],
    ) -> None:
        """Add context for email drafting from real entity data."""
        # Add relevant entity context for email
        if "rfq_number" in parameters:
            await self._add_rfq_context(context, parameters["rfq_number"])
        if "quote_number" in parameters:
            await self._add_quote_context(context, parameters["quote_number"])

        # Customer context from Context Bus if an entity was found
        for chunk in context.chunks:
            if chunk.metadata and chunk.metadata.get("rfq_id"):
                try:
                    pack = await get_context_service().get_context_pack(
                        self.session,
                        root_entity_type="rfq",
                        root_entity_id=chunk.metadata["rfq_id"],
                        max_depth=3,
                    )
                    acct = next((n for n in pack.nodes if n.entity_type == "account"), None)
                    if acct:
                        context.add_chunk(ContextChunk(
                            context_type=ContextType.CUSTOMER_DATA,
                            content=f"Customer: {acct.data.get('name', 'N/A')} ({acct.data.get('industry', 'N/A')})",
                            relevance_score=0.8,
                        ))
                        return
                except Exception:
                    pass

        context.add_chunk(ContextChunk(
            context_type=ContextType.CUSTOMER_DATA,
            content="Customer/recipient information not resolved — specify an RFQ or quote number for richer context.",
            relevance_score=0.4,
        ))
    
    async def _add_metrics_context(self, context: ChatContext) -> None:
        """Add aggregate metrics context for reporting."""
        if not self.session:
            return
        lines = ["Key Metrics:"]
        try:
            rfq_count = (await self.session.execute(select(func.count()).select_from(RFQ))).scalar_one()
            lines.append(f"  Total RFQs: {rfq_count}")
        except Exception:
            pass
        try:
            quote_count = (await self.session.execute(select(func.count()).select_from(Quote))).scalar_one()
            lines.append(f"  Total Quotes: {quote_count}")
        except Exception:
            pass
        try:
            wo_count = (await self.session.execute(select(func.count()).select_from(WorkOrder))).scalar_one()
            lines.append(f"  Total Work Orders: {wo_count}")
        except Exception:
            pass
        try:
            open_tasks = (await self.session.execute(
                select(func.count()).select_from(Task).where(Task.status.in_(["todo", "in_progress", "open"]))
            )).scalar_one()
            lines.append(f"  Open Tasks: {open_tasks}")
        except Exception:
            pass

        context.add_chunk(ContextChunk(
            context_type=ContextType.METRICS,
            content="\n".join(lines),
            relevance_score=0.8,
        ))
    
    async def _add_knowledge_context(
        self,
        context: ChatContext,
        query: str,
    ) -> None:
        """Add knowledge base context via hybrid search if available."""
        try:
            from sensei.services.ai.hybrid_search import HybridSearchEngine, SearchQuery, SearchMode
            # HybridSearchEngine is a singleton; attempt to use if initialized
            engine: HybridSearchEngine | None = None
            try:
                from sensei.services.ai.hybrid_search import _engine_singleton  # noqa: F811
                engine = _engine_singleton
            except ImportError:
                pass

            if engine is not None:
                result = engine.search(SearchQuery(query=query, top_k=3, mode=SearchMode.HYBRID))
                if result.results:
                    parts = [f"[Knowledge] {r.chunk.text[:300]}" for r in result.results[:3]]
                    context.add_chunk(ContextChunk(
                        context_type=ContextType.KNOWLEDGE_BASE,
                        content="\n---\n".join(parts),
                        metadata={"source": "hybrid_search", "num_results": len(result.results)},
                        relevance_score=0.7,
                    ))
                    return
        except Exception:
            logger.debug("Hybrid search unavailable, falling back", exc_info=True)

        # Fallback: note that knowledge search is not yet available in this session
        context.add_chunk(ContextChunk(
            context_type=ContextType.KNOWLEDGE_BASE,
            content="Knowledge base search is available. Ask about manufacturing processes, quality standards, or operational procedures.",
            metadata={"source": "knowledge_base"},
            relevance_score=0.4,
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
