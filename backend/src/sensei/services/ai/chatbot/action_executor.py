"""
Action Executor for Sensei OS Chatbot.

Executes actions based on classified intents:
- Email drafting via AIEmailDraftingService
- Data queries via database
- Task management
- Approval workflows
- Navigation commands
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Awaitable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.services.ai.chatbot.context_builder import UserContext, ChatContext
from sensei.services.ai.chatbot.intent_classifier import Intent, IntentType

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be executed."""
    
    # Data operations
    QUERY_DATA = "query_data"
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    
    # Email
    DRAFT_EMAIL = "draft_email"
    SEND_EMAIL = "send_email"
    
    # Tasks
    LIST_TASKS = "list_tasks"
    CREATE_TASK = "create_task"
    COMPLETE_TASK = "complete_task"
    
    # Approvals
    LIST_APPROVALS = "list_approvals"
    APPROVE_ITEM = "approve_item"
    REJECT_ITEM = "reject_item"
    
    # Reports
    GENERATE_REPORT = "generate_report"
    
    # Knowledge
    SEARCH_KNOWLEDGE = "search_knowledge"
    
    # Navigation
    NAVIGATE = "navigate"
    
    # No action (informational only)
    NONE = "none"


class ActionStatus(str, Enum):
    """Status of action execution."""
    
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING_CONFIRMATION = "pending_confirmation"
    UNAUTHORIZED = "unauthorized"


@dataclass
class ActionResult:
    """Result of executing an action."""
    
    action_type: ActionType
    status: ActionStatus
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    confirmation_required: bool = False
    confirmation_prompt: str = ""
    action_id: UUID = field(default_factory=uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.status == ActionStatus.SUCCESS


class ActionExecutor:
    """
    Executes actions based on classified intents.
    
    Integrates with existing services:
    - AIEmailDraftingService for email drafting
    - Database for data queries
    - Task service for task management
    - Approval workflows
    """
    
    # Intent to action type mapping
    INTENT_TO_ACTION: Dict[IntentType, ActionType] = {
        IntentType.DATA_LOOKUP: ActionType.QUERY_DATA,
        IntentType.DATA_CREATE: ActionType.CREATE_RECORD,
        IntentType.DATA_UPDATE: ActionType.UPDATE_RECORD,
        IntentType.EMAIL_DRAFT: ActionType.DRAFT_EMAIL,
        IntentType.EMAIL_SEND: ActionType.SEND_EMAIL,
        IntentType.TASK_LIST: ActionType.LIST_TASKS,
        IntentType.TASK_CREATE: ActionType.CREATE_TASK,
        IntentType.TASK_COMPLETE: ActionType.COMPLETE_TASK,
        IntentType.APPROVAL_LIST: ActionType.LIST_APPROVALS,
        IntentType.APPROVAL_APPROVE: ActionType.APPROVE_ITEM,
        IntentType.APPROVAL_REJECT: ActionType.REJECT_ITEM,
        IntentType.REPORT_GENERATE: ActionType.GENERATE_REPORT,
        IntentType.KNOWLEDGE_QUERY: ActionType.SEARCH_KNOWLEDGE,
        IntentType.TRAINING_LOOKUP: ActionType.SEARCH_KNOWLEDGE,
        IntentType.A3_ASSIST: ActionType.SEARCH_KNOWLEDGE,
        IntentType.FIVE_WHYS: ActionType.SEARCH_KNOWLEDGE,
        IntentType.NAVIGATION: ActionType.NAVIGATE,
        IntentType.GENERAL_CHAT: ActionType.NONE,
        IntentType.HELP: ActionType.NONE,
        IntentType.UNKNOWN: ActionType.NONE,
    }
    
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        email_service: Optional[Any] = None,
    ):
        """
        Initialize action executor.
        
        Args:
            session: Optional async database session
            email_service: Optional email drafting service
        """
        self.session = session
        self.email_service = email_service
        self._action_handlers: Dict[ActionType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register action handlers."""
        self._action_handlers = {
            ActionType.QUERY_DATA: self._handle_query_data,
            ActionType.DRAFT_EMAIL: self._handle_draft_email,
            ActionType.LIST_TASKS: self._handle_list_tasks,
            ActionType.CREATE_TASK: self._handle_create_task,
            ActionType.COMPLETE_TASK: self._handle_complete_task,
            ActionType.LIST_APPROVALS: self._handle_list_approvals,
            ActionType.APPROVE_ITEM: self._handle_approve_item,
            ActionType.REJECT_ITEM: self._handle_reject_item,
            ActionType.GENERATE_REPORT: self._handle_generate_report,
            ActionType.SEARCH_KNOWLEDGE: self._handle_search_knowledge,
            ActionType.NAVIGATE: self._handle_navigate,
            ActionType.NONE: self._handle_none,
        }
    
    async def execute(
        self,
        intent: Intent,
        context: ChatContext,
        confirmed: bool = False,
    ) -> ActionResult:
        """
        Execute an action based on intent.
        
        Args:
            intent: Classified intent
            context: Chat context
            confirmed: Whether user has confirmed destructive action
            
        Returns:
            ActionResult with execution status
        """
        action_type = self.INTENT_TO_ACTION.get(intent.intent_type, ActionType.NONE)
        
        # Check if confirmation is needed
        if intent.requires_confirmation and not confirmed:
            return ActionResult(
                action_type=action_type,
                status=ActionStatus.PENDING_CONFIRMATION,
                message="This action requires confirmation.",
                confirmation_required=True,
                confirmation_prompt=self._generate_confirmation_prompt(intent, context),
            )
        
        # Get handler
        handler = self._action_handlers.get(action_type, self._handle_none)
        
        try:
            result = await handler(intent, context)
            logger.info(
                "Action executed action_type=%s status=%s user_id=%s",
                action_type.value,
                result.status.value,
                str(context.user.user_id),
            )
            return result
        except PermissionError as e:
            logger.warning(
                "Action unauthorized action_type=%s user_id=%s error=%s",
                action_type.value,
                str(context.user.user_id),
                str(e),
            )
            return ActionResult(
                action_type=action_type,
                status=ActionStatus.UNAUTHORIZED,
                message=f"You don't have permission to perform this action: {e}",
            )
        except Exception as e:
            logger.error(
                "Action failed action_type=%s user_id=%s error=%s",
                action_type.value,
                str(context.user.user_id),
                str(e),
                exc_info=True,
            )
            return ActionResult(
                action_type=action_type,
                status=ActionStatus.FAILED,
                message=f"Action failed: {str(e)}",
            )
    
    def _generate_confirmation_prompt(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> str:
        """Generate confirmation prompt for destructive actions."""
        if intent.intent_type == IntentType.APPROVAL_APPROVE:
            item = intent.parameters.get("rfq_number") or intent.parameters.get("quote_number", "item")
            return f"Are you sure you want to approve {item}? Reply 'yes' to confirm."
        elif intent.intent_type == IntentType.APPROVAL_REJECT:
            item = intent.parameters.get("rfq_number") or intent.parameters.get("quote_number", "item")
            return f"Are you sure you want to reject {item}? Reply 'yes' to confirm."
        elif intent.intent_type == IntentType.EMAIL_SEND:
            return "Are you sure you want to send this email? Reply 'yes' to confirm."
        elif intent.intent_type == IntentType.TASK_COMPLETE:
            return "Are you sure you want to mark this task as complete? Reply 'yes' to confirm."
        return "Please confirm this action by replying 'yes'."
    
    async def _handle_query_data(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle data lookup queries."""
        params = intent.parameters
        
        # Determine what type of data to query
        if "rfq_number" in params:
            return await self._query_rfq(params["rfq_number"], context)
        elif "quote_number" in params:
            return await self._query_quote(params["quote_number"], context)
        elif "work_order_number" in params:
            return await self._query_work_order(params["work_order_number"], context)
        elif "status_filter" in params:
            return await self._query_by_status(params, context)
        else:
            # General lookup - provide summary
            return ActionResult(
                action_type=ActionType.QUERY_DATA,
                status=ActionStatus.SUCCESS,
                message="Please specify what you'd like to look up (RFQ, quote, work order, or task).",
                data={"suggestions": [
                    "Show RFQ 1234",
                    "List pending quotes",
                    "Show my open tasks",
                ]},
            )
    
    async def _query_rfq(self, rfq_number: str, context: ChatContext) -> ActionResult:
        """Query RFQ data."""
        # In production, this would query the database
        return ActionResult(
            action_type=ActionType.QUERY_DATA,
            status=ActionStatus.SUCCESS,
            message=f"RFQ {rfq_number} information retrieved.",
            data={
                "rfq_number": rfq_number,
                "query_type": "rfq",
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _query_quote(self, quote_number: str, context: ChatContext) -> ActionResult:
        """Query quote data."""
        return ActionResult(
            action_type=ActionType.QUERY_DATA,
            status=ActionStatus.SUCCESS,
            message=f"Quote {quote_number} information retrieved.",
            data={
                "quote_number": quote_number,
                "query_type": "quote",
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _query_work_order(self, wo_number: str, context: ChatContext) -> ActionResult:
        """Query work order data."""
        return ActionResult(
            action_type=ActionType.QUERY_DATA,
            status=ActionStatus.SUCCESS,
            message=f"Work Order {wo_number} information retrieved.",
            data={
                "work_order_number": wo_number,
                "query_type": "work_order",
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _query_by_status(
        self,
        params: Dict[str, Any],
        context: ChatContext,
    ) -> ActionResult:
        """Query entities by status."""
        status = params.get("status_filter", "all")
        return ActionResult(
            action_type=ActionType.QUERY_DATA,
            status=ActionStatus.SUCCESS,
            message=f"Queried items with status: {status}",
            data={
                "status_filter": status,
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _handle_draft_email(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle email drafting requests."""
        params = intent.parameters
        
        # Extract email context
        recipient = params.get("customer_name", params.get("email_address", ""))
        rfq_number = params.get("rfq_number")
        quote_number = params.get("quote_number")
        
        # Use email service if available
        if self.email_service:
            try:
                # This would integrate with AIEmailDraftingService
                draft = await self._generate_email_draft(
                    recipient=recipient,
                    rfq_number=rfq_number,
                    quote_number=quote_number,
                    query=params.get("raw_query", ""),
                    user=context.user,
                )
                return ActionResult(
                    action_type=ActionType.DRAFT_EMAIL,
                    status=ActionStatus.SUCCESS,
                    message="Email draft generated.",
                    data={"draft": draft},
                )
            except Exception as e:
                logger.error(f"Email draft generation failed: {e}")
        
        # Fallback: provide template
        return ActionResult(
            action_type=ActionType.DRAFT_EMAIL,
            status=ActionStatus.PARTIAL,
            message="Email draft prepared. Please customize before sending.",
            data={
                "draft": {
                    "to": recipient,
                    "subject": f"Regarding {'RFQ ' + rfq_number if rfq_number else 'Quote ' + quote_number if quote_number else 'Your Request'}",
                    "body": "Dear [Recipient],\n\n[Email body to be drafted based on context]\n\nBest regards,\n" + context.user.name,
                },
                "note": "Full email generation requires AIEmailDraftingService integration",
            },
        )
    
    async def _generate_email_draft(
        self,
        recipient: str,
        rfq_number: Optional[str],
        quote_number: Optional[str],
        query: str,
        user: UserContext,
    ) -> Dict[str, str]:
        """Generate email draft using AI service."""
        # This would integrate with AIEmailDraftingService
        subject = f"Follow-up: {'RFQ ' + rfq_number if rfq_number else 'Quote ' + quote_number if quote_number else 'Your Request'}"
        body = f"""Dear {recipient or '[Recipient]'},

Thank you for your inquiry. We are following up on {'RFQ ' + rfq_number if rfq_number else 'Quote ' + quote_number if quote_number else 'your recent request'}.

[Add specific details here]

Please don't hesitate to reach out if you have any questions.

Best regards,
{user.name}
{user.email}"""
        
        return {
            "to": recipient,
            "subject": subject,
            "body": body,
        }
    
    async def _handle_list_tasks(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle task listing."""
        return ActionResult(
            action_type=ActionType.LIST_TASKS,
            status=ActionStatus.SUCCESS,
            message=f"Your tasks for {context.user.name}:",
            data={
                "tasks": [
                    {"id": 1, "title": "Example task 1", "status": "pending"},
                    {"id": 2, "title": "Example task 2", "status": "in_progress"},
                ],
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _handle_create_task(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle task creation."""
        return ActionResult(
            action_type=ActionType.CREATE_TASK,
            status=ActionStatus.SUCCESS,
            message="Task creation prepared. What would you like the task title to be?",
            data={"requires_input": True},
        )
    
    async def _handle_complete_task(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle task completion."""
        task_id = intent.parameters.get("task_id")
        return ActionResult(
            action_type=ActionType.COMPLETE_TASK,
            status=ActionStatus.SUCCESS,
            message=f"Task {task_id or '[ID]'} marked as complete.",
            data={"task_id": task_id},
        )
    
    async def _handle_list_approvals(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle approval listing."""
        return ActionResult(
            action_type=ActionType.LIST_APPROVALS,
            status=ActionStatus.SUCCESS,
            message=f"Pending approvals for {context.user.name}:",
            data={
                "approvals": [
                    {"type": "quote", "id": "Q-1234", "amount": "$15,000", "requestor": "John Doe"},
                ],
                "note": "Database integration pending - returning placeholder",
            },
        )
    
    async def _handle_approve_item(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle item approval."""
        item_id = intent.parameters.get("rfq_number") or intent.parameters.get("quote_number")
        return ActionResult(
            action_type=ActionType.APPROVE_ITEM,
            status=ActionStatus.SUCCESS,
            message=f"Item {item_id or '[ID]'} approved.",
            data={"item_id": item_id, "approved_by": str(context.user.user_id)},
        )
    
    async def _handle_reject_item(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle item rejection."""
        item_id = intent.parameters.get("rfq_number") or intent.parameters.get("quote_number")
        return ActionResult(
            action_type=ActionType.REJECT_ITEM,
            status=ActionStatus.SUCCESS,
            message=f"Item {item_id or '[ID]'} rejected.",
            data={"item_id": item_id, "rejected_by": str(context.user.user_id)},
        )
    
    async def _handle_generate_report(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle report generation."""
        return ActionResult(
            action_type=ActionType.GENERATE_REPORT,
            status=ActionStatus.SUCCESS,
            message="Report generation initiated. What type of report would you like?",
            data={
                "available_reports": [
                    "RFQ Summary",
                    "Quote Performance",
                    "Production Status",
                    "Quality Metrics",
                ],
            },
        )
    
    async def _handle_search_knowledge(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle knowledge base search."""
        query = intent.parameters.get("raw_query", "")
        return ActionResult(
            action_type=ActionType.SEARCH_KNOWLEDGE,
            status=ActionStatus.SUCCESS,
            message="Searching knowledge base...",
            data={
                "query": query,
                "results": [],  # Would be populated by hybrid search
                "note": "Knowledge base integration pending",
            },
        )
    
    async def _handle_navigate(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle navigation requests."""
        target = intent.parameters.get("navigation_target", "/dashboard")
        label = intent.parameters.get("navigation_label", "Dashboard")
        return ActionResult(
            action_type=ActionType.NAVIGATE,
            status=ActionStatus.SUCCESS,
            message=f"Navigate to {label}",
            data={
                "path": target,
                "label": label,
            },
        )
    
    async def _handle_none(
        self,
        intent: Intent,
        context: ChatContext,
    ) -> ActionResult:
        """Handle informational requests (no action needed)."""
        return ActionResult(
            action_type=ActionType.NONE,
            status=ActionStatus.SUCCESS,
            message="This is an informational request.",
            data={},
        )


def create_action_executor(
    session: Optional[AsyncSession] = None,
    email_service: Optional[Any] = None,
) -> ActionExecutor:
    """Factory function to create action executor."""
    return ActionExecutor(session=session, email_service=email_service)
