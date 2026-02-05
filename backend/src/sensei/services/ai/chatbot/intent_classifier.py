"""
Intent Classifier for Sensei OS Chatbot.

Classifies user queries into actionable intents:
- DATA_LOOKUP: Query for information (RFQs, quotes, work orders, etc.)
- EMAIL_DRAFT: Request to draft an email
- REPORT_GENERATE: Generate a report or summary
- TASK_ACTION: Create, update, or complete tasks
- APPROVAL_ACTION: Approve or reject items
- PROBLEM_SOLVING: A3, 5 Whys, root cause analysis
- KNOWLEDGE_QUERY: TPS/Lean knowledge questions
- NAVIGATION: Navigate to a page or resource
- GENERAL_CHAT: General conversation or help
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Types of user intents."""
    
    # Data operations
    DATA_LOOKUP = "data_lookup"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    
    # Communication
    EMAIL_DRAFT = "email_draft"
    EMAIL_SEND = "email_send"
    
    # Reporting
    REPORT_GENERATE = "report_generate"
    REPORT_EXPORT = "report_export"
    
    # Task management
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_COMPLETE = "task_complete"
    TASK_LIST = "task_list"
    
    # Approvals
    APPROVAL_LIST = "approval_list"
    APPROVAL_APPROVE = "approval_approve"
    APPROVAL_REJECT = "approval_reject"
    
    # Problem solving
    A3_ASSIST = "a3_assist"
    FIVE_WHYS = "five_whys"
    ROOT_CAUSE = "root_cause"
    
    # Knowledge
    KNOWLEDGE_QUERY = "knowledge_query"
    TRAINING_LOOKUP = "training_lookup"
    
    # Navigation
    NAVIGATION = "navigation"
    
    # General
    GENERAL_CHAT = "general_chat"
    HELP = "help"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Types of entities extracted from queries."""
    
    RFQ = "rfq"
    QUOTE = "quote"
    WORK_ORDER = "work_order"
    TASK = "task"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PRODUCT = "product"
    USER = "user"
    DATE = "date"
    STATUS = "status"
    PRIORITY = "priority"
    NUMBER = "number"
    EMAIL = "email"
    PAGE = "page"


@dataclass
class ExtractedEntity:
    """An entity extracted from user query."""
    
    entity_type: EntityType
    value: str
    normalized_value: Any
    confidence: float
    start_pos: int = 0
    end_pos: int = 0


# Intents that require executing an action
ACTION_INTENTS = {
    IntentType.DATA_LOOKUP,
    IntentType.DATA_CREATE,
    IntentType.DATA_UPDATE,
    IntentType.EMAIL_DRAFT,
    IntentType.EMAIL_SEND,
    IntentType.TASK_CREATE,
    IntentType.TASK_COMPLETE,
    IntentType.TASK_LIST,
    IntentType.APPROVAL_APPROVE,
    IntentType.APPROVAL_REJECT,
    IntentType.APPROVAL_LIST,
    IntentType.REPORT_GENERATE,
    IntentType.NAVIGATION,
}


@dataclass
class Intent:
    """Classified intent from user query."""
    
    intent_type: IntentType
    confidence: float
    entities: List[ExtractedEntity] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    requires_rbac_check: bool = True
    suggested_actions: List[str] = field(default_factory=list)
    
    @property
    def requires_action(self) -> bool:
        """Check if this intent requires executing an action."""
        return self.intent_type in ACTION_INTENTS


class IntentClassifier:
    """
    Classifies user queries into actionable intents.
    
    Uses pattern matching and keyword analysis for fast,
    deterministic classification without LLM dependency.
    """
    
    # Intent patterns - ordered by priority
    INTENT_PATTERNS: Dict[IntentType, List[Tuple[str, float]]] = {
        IntentType.EMAIL_DRAFT: [
            (r"\b(draft|write|compose|create)\s+(an?\s+)?email\b", 0.95),
            (r"\bemail\s+(to|for|about)\b", 0.90),
            (r"\bsend\s+(a\s+)?(follow.?up|reminder|message)\b", 0.85),
            (r"\b(follow.?up|remind)\s+.*(email|message)\b", 0.85),
        ],
        IntentType.EMAIL_SEND: [
            (r"\bsend\s+(the\s+)?email\b", 0.95),
            (r"\bemail\s+this\s+to\b", 0.90),
        ],
        IntentType.REPORT_GENERATE: [
            (r"\b(generate|create|build|make)\s+(a\s+)?report\b", 0.95),
            (r"\breport\s+(on|for|about)\b", 0.90),
            (r"\bsummar(y|ize)\b", 0.85),
            (r"\b(weekly|monthly|daily)\s+(report|summary)\b", 0.90),
            (r"\bexport\s+.*(data|report|csv|excel)\b", 0.85),
        ],
        IntentType.DATA_LOOKUP: [
            (r"\b(show|get|find|list|display|what|where|which)\s+(me\s+)?(the\s+)?", 0.80),
            (r"\bstatus\s+(of|for)\b", 0.85),
            (r"\bhow\s+many\b", 0.85),
            (r"\bwhat('s|is)\s+(the\s+)?(status|state|progress)\b", 0.90),
            (r"\b(pending|overdue|open|closed)\s+(rfq|quote|task|order)s?\b", 0.90),
            (r"\bmy\s+(rfq|quote|task|approval|work.?order)s?\b", 0.90),
        ],
        IntentType.TASK_CREATE: [
            (r"\b(create|add|new)\s+(a\s+)?task\b", 0.95),
            (r"\bremind\s+me\s+to\b", 0.85),
            (r"\badd\s+to\s+(my\s+)?to.?do\b", 0.85),
        ],
        IntentType.TASK_COMPLETE: [
            (r"\b(complete|finish|done|close)\s+(the\s+)?task\b", 0.95),
            (r"\bmark\s+.*(complete|done|finished)\b", 0.90),
        ],
        IntentType.TASK_LIST: [
            (r"\b(my|show|list)\s+(my\s+)?(tasks?|to.?do)\b", 0.90),
            (r"\blist\s+my\s+tasks?\b", 0.95),
            (r"\bwhat('s|do\s+i\s+have)\s+(on\s+my\s+)?(plate|list|to.?do)\b", 0.85),
            (r"\bmy\s+tasks?\b", 0.85),
        ],
        IntentType.APPROVAL_LIST: [
            (r"\b(pending|my)\s+approvals?\b", 0.95),
            (r"\bwhat\s+(needs|requires)\s+(my\s+)?approval\b", 0.90),
            (r"\bapproval\s+(queue|list|pending)\b", 0.90),
        ],
        IntentType.APPROVAL_APPROVE: [
            (r"\bapprove\s+(the\s+)?(rfq|quote|request|order)\b", 0.95),
            (r"\bapprove\s+#?\d+\b", 0.90),
        ],
        IntentType.APPROVAL_REJECT: [
            (r"\breject\s+(the\s+)?(rfq|quote|request|order)\b", 0.95),
            (r"\breject\s+#?\d+\b", 0.90),
            (r"\bdecline\s+(the\s+)?(rfq|quote|request)\b", 0.90),
        ],
        IntentType.A3_ASSIST: [
            (r"\ba3\s+(report|analysis|help)\b", 0.95),
            (r"\bhelp\s+(me\s+)?with\s+(an?\s+)?a3\b", 0.90),
            (r"\bstart\s+(an?\s+)?a3\b", 0.90),
            (r"\bproblem\s+solving\b", 0.80),
        ],
        IntentType.FIVE_WHYS: [
            (r"\b5\s*whys?\b", 0.95),
            (r"\bfive\s*whys?\b", 0.95),
            (r"\broot\s+cause\s+analysis\b", 0.85),
        ],
        IntentType.KNOWLEDGE_QUERY: [
            (r"\b(what\s+is|explain|define|tell\s+me\s+about)\s+(tps|lean|kaizen|kanban|andon|jidoka|heijunka|muda|mura|muri)\b", 0.95),
            (r"\b(how\s+to|best\s+practice|standard)\s+", 0.75),
            (r"\b(tps|lean|toyota)\s+(principle|method|approach)\b", 0.90),
        ],
        IntentType.TRAINING_LOOKUP: [
            (r"\btraining\s+(for|on|about|status|matrix)\b", 0.90),
            (r"\b(my|employee)\s+training\b", 0.85),
            (r"\bcertification\s+(status|expir|due)\b", 0.85),
        ],
        IntentType.NAVIGATION: [
            (r"\b(go\s+to|open|navigate\s+to|take\s+me\s+to)\s+", 0.90),
            (r"\bshow\s+me\s+the\s+.+\s+page\b", 0.85),
        ],
        IntentType.HELP: [
            (r"\b(help|how\s+do\s+i|how\s+can\s+i|what\s+can\s+you)\b", 0.80),
            (r"\bwhat\s+can\s+you\s+do\b", 0.90),
        ],
    }
    
    # Entity extraction patterns
    ENTITY_PATTERNS: Dict[EntityType, List[Tuple[str, str]]] = {
        EntityType.RFQ: [
            (r"rfq[#\-\s]*(\d+)", "rfq_number"),
            (r"request\s+for\s+quote[#\-\s]*(\d+)", "rfq_number"),
            (r"rfq[#\-\s]*([A-Z0-9\-]+)", "rfq_id"),
        ],
        EntityType.QUOTE: [
            (r"quote[#\-\s]*(\d+)", "quote_number"),
            (r"quotation[#\-\s]*(\d+)", "quote_number"),
            (r"q[#\-](\d+)", "quote_number"),
        ],
        EntityType.WORK_ORDER: [
            (r"(?:work\s*order|wo)[#\-\s]*(\d+)", "wo_number"),
            (r"wo[#\-]([A-Z0-9\-]+)", "wo_id"),
        ],
        EntityType.CUSTOMER: [
            (r"(?:customer|client)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:about|for|regarding)|$)", "customer_name"),
            (r"(?:for|to)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:about|regarding)|$)", "customer_name"),
        ],
        EntityType.SUPPLIER: [
            (r"supplier\s+([A-Z][a-zA-Z\s]+?)(?:\s+|$)", "supplier_name"),
            (r"vendor\s+([A-Z][a-zA-Z\s]+?)(?:\s+|$)", "vendor_name"),
        ],
        EntityType.DATE: [
            (r"(today|tomorrow|yesterday)", "relative_date"),
            (r"(this|next|last)\s+(week|month|quarter)", "relative_period"),
            (r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", "date_string"),
        ],
        EntityType.STATUS: [
            (r"\b(pending|approved|rejected|open|closed|draft|in\s*progress|completed|overdue)\b", "status"),
        ],
        EntityType.PRIORITY: [
            (r"\b(urgent|high|medium|low|critical)\s*(?:priority)?\b", "priority"),
        ],
        EntityType.NUMBER: [
            (r"#?(\d+)", "number"),
        ],
        EntityType.EMAIL: [
            (r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", "email"),
        ],
    }
    
    # Navigation targets
    NAVIGATION_TARGETS = {
        "dashboard": "/dashboard",
        "home": "/dashboard",
        "rfqs": "/rfqs",
        "rfq list": "/rfqs",
        "quotes": "/quotes",
        "quotations": "/quotes",
        "work orders": "/work-orders",
        "production": "/production",
        "quality": "/quality",
        "tasks": "/tasks",
        "approvals": "/approvals",
        "customers": "/customers",
        "accounts": "/accounts",
        "suppliers": "/suppliers",
        "inventory": "/inventory",
        "finance": "/finance",
        "hr": "/hr",
        "training": "/training",
        "a3": "/a3",
        "kanban": "/kanban",
        "obeya": "/obeya",
        "settings": "/settings",
        "reports": "/reports",
        "analytics": "/analytics",
    }
    
    def __init__(self):
        """Initialize intent classifier."""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._compiled_intents: Dict[IntentType, List[Tuple[re.Pattern, float]]] = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            self._compiled_intents[intent_type] = [
                (re.compile(pattern, re.IGNORECASE), confidence)
                for pattern, confidence in patterns
            ]
        
        self._compiled_entities: Dict[EntityType, List[Tuple[re.Pattern, str]]] = {}
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            self._compiled_entities[entity_type] = [
                (re.compile(pattern, re.IGNORECASE), group_name)
                for pattern, group_name in patterns
            ]
    
    def classify(self, query: str) -> Intent:
        """
        Classify a user query into an intent.
        
        Args:
            query: User's natural language query
            
        Returns:
            Classified intent with extracted entities
        """
        query = query.strip()
        if not query:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
            )
        
        # Find best matching intent
        best_intent_type = IntentType.GENERAL_CHAT
        best_confidence = 0.5  # Default confidence for general chat
        
        for intent_type, patterns in self._compiled_intents.items():
            for pattern, base_confidence in patterns:
                if pattern.search(query):
                    if base_confidence > best_confidence:
                        best_confidence = base_confidence
                        best_intent_type = intent_type
        
        # Extract entities
        entities = self._extract_entities(query)
        
        # Build parameters based on intent type
        parameters = self._build_parameters(best_intent_type, entities, query)
        
        # Determine if confirmation needed (for destructive actions)
        requires_confirmation = best_intent_type in [
            IntentType.APPROVAL_APPROVE,
            IntentType.APPROVAL_REJECT,
            IntentType.EMAIL_SEND,
            IntentType.DATA_UPDATE,
            IntentType.TASK_COMPLETE,
        ]
        
        # Determine if RBAC check needed
        requires_rbac_check = best_intent_type not in [
            IntentType.HELP,
            IntentType.GENERAL_CHAT,
            IntentType.NAVIGATION,
        ]
        
        # Generate suggested actions
        suggested_actions = self._generate_suggestions(best_intent_type, entities)
        
        return Intent(
            intent_type=best_intent_type,
            confidence=best_confidence,
            entities=entities,
            parameters=parameters,
            requires_confirmation=requires_confirmation,
            requires_rbac_check=requires_rbac_check,
            suggested_actions=suggested_actions,
        )
    
    def _extract_entities(self, query: str) -> List[ExtractedEntity]:
        """Extract entities from query."""
        entities: List[ExtractedEntity] = []
        
        for entity_type, patterns in self._compiled_entities.items():
            for pattern, group_name in patterns:
                for match in pattern.finditer(query):
                    value = match.group(1) if match.lastindex else match.group(0)
                    entities.append(ExtractedEntity(
                        entity_type=entity_type,
                        value=value,
                        normalized_value=self._normalize_entity(entity_type, value),
                        confidence=0.9,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    ))
        
        return entities
    
    def _normalize_entity(self, entity_type: EntityType, value: str) -> Any:
        """Normalize an extracted entity value."""
        if entity_type == EntityType.STATUS:
            return value.lower().replace(" ", "_")
        elif entity_type == EntityType.PRIORITY:
            return value.lower().replace(" priority", "")
        elif entity_type == EntityType.DATE:
            # Simple relative date handling
            lower = value.lower()
            if lower == "today":
                return datetime.now(timezone.utc).date().isoformat()
            elif lower == "tomorrow":
                from datetime import timedelta
                return (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
            elif lower == "yesterday":
                from datetime import timedelta
                return (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
            return value
        elif entity_type in [EntityType.RFQ, EntityType.QUOTE, EntityType.WORK_ORDER]:
            # Remove common prefixes
            return re.sub(r"^[#\-\s]+", "", value)
        return value
    
    def _build_parameters(
        self,
        intent_type: IntentType,
        entities: List[ExtractedEntity],
        query: str,
    ) -> Dict[str, Any]:
        """Build action parameters from entities."""
        params: Dict[str, Any] = {"raw_query": query}
        
        # Map entities to parameters
        for entity in entities:
            if entity.entity_type == EntityType.RFQ:
                params["rfq_number"] = entity.normalized_value
            elif entity.entity_type == EntityType.QUOTE:
                params["quote_number"] = entity.normalized_value
            elif entity.entity_type == EntityType.WORK_ORDER:
                params["work_order_number"] = entity.normalized_value
            elif entity.entity_type == EntityType.CUSTOMER:
                params["customer_name"] = entity.normalized_value
            elif entity.entity_type == EntityType.SUPPLIER:
                params["supplier_name"] = entity.normalized_value
            elif entity.entity_type == EntityType.STATUS:
                params["status_filter"] = entity.normalized_value
            elif entity.entity_type == EntityType.PRIORITY:
                params["priority_filter"] = entity.normalized_value
            elif entity.entity_type == EntityType.DATE:
                params["date_filter"] = entity.normalized_value
            elif entity.entity_type == EntityType.EMAIL:
                params["email_address"] = entity.normalized_value
        
        # Handle navigation
        if intent_type == IntentType.NAVIGATION:
            for target, path in self.NAVIGATION_TARGETS.items():
                if target in query.lower():
                    params["navigation_target"] = path
                    params["navigation_label"] = target
                    break
        
        return params
    
    def _generate_suggestions(
        self,
        intent_type: IntentType,
        entities: List[ExtractedEntity],
    ) -> List[str]:
        """Generate helpful suggestions based on intent."""
        suggestions: List[str] = []
        
        if intent_type == IntentType.DATA_LOOKUP and not entities:
            suggestions.extend([
                "Try specifying an RFQ number, e.g., 'Show RFQ 1234'",
                "You can filter by status: 'Show pending quotes'",
                "Use 'my' to see your items: 'Show my tasks'",
            ])
        elif intent_type == IntentType.EMAIL_DRAFT and not any(
            e.entity_type in [EntityType.CUSTOMER, EntityType.EMAIL] for e in entities
        ):
            suggestions.extend([
                "Specify a recipient: 'Draft email to customer Acme Corp'",
                "Include context: 'Draft follow-up email for RFQ 1234'",
            ])
        elif intent_type == IntentType.GENERAL_CHAT:
            suggestions.extend([
                "I can help with RFQs, quotes, and work orders",
                "Try 'Show my pending approvals'",
                "Ask 'Draft an email for RFQ 1234'",
                "Say 'Help' to see all capabilities",
            ])
        
        return suggestions


def create_intent_classifier() -> IntentClassifier:
    """Factory function to create intent classifier."""
    return IntentClassifier()
