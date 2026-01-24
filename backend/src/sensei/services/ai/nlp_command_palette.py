"""
NLP Command Palette.

This module implements natural language processing for command execution:
- Multi-turn Conversational State: Session-based follow-up queries
- Action Parser: JSON-mode LLM to map NLP to system actions
- Fuzzy Symbol Matching: Flexible entity matching (RFQ 123, RFQ#123, etc.)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import difflib

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SESSION_TTL = 300  # 5 minutes
MAX_HISTORY_LENGTH = 10
FUZZY_MATCH_THRESHOLD = 0.6


# =============================================================================
# Enums
# =============================================================================

class ActionType(Enum):
    """Types of system actions."""
    # RFQ Actions
    CREATE_RFQ = "create_rfq"
    VIEW_RFQ = "view_rfq"
    UPDATE_RFQ = "update_rfq"
    LIST_RFQS = "list_rfqs"
    
    # Task Actions
    CREATE_TASK = "create_task"
    VIEW_TASK = "view_task"
    UPDATE_TASK = "update_task"
    LIST_TASKS = "list_tasks"
    ASSIGN_TASK = "assign_task"
    COMPLETE_TASK = "complete_task"
    
    # Approval Actions
    APPROVE = "approve"
    REJECT = "reject"
    LIST_APPROVALS = "list_approvals"
    
    # Quote Actions
    CREATE_QUOTE = "create_quote"
    VIEW_QUOTE = "view_quote"
    LIST_QUOTES = "list_quotes"
    
    # Order Actions
    VIEW_ORDER = "view_order"
    LIST_ORDERS = "list_orders"
    
    # Report Actions
    GENERATE_REPORT = "generate_report"
    
    # Search Actions
    SEARCH = "search"
    
    # Navigation Actions
    NAVIGATE = "navigate"
    
    # Unknown
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of entities that can be extracted."""
    RFQ = "rfq"
    TASK = "task"
    QUOTE = "quote"
    ORDER = "order"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    USER = "user"
    DATE = "date"
    STATUS = "status"
    PRIORITY = "priority"
    NUMBER = "number"


class ParseConfidence(Enum):
    """Confidence levels for parsing."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Entity:
    """An extracted entity from natural language."""
    entity_type: EntityType
    value: str
    normalized_value: Any
    start_pos: int
    end_pos: int
    confidence: float
    alternatives: List[str] = field(default_factory=list)


@dataclass
class ParsedAction:
    """A parsed action from natural language."""
    action_type: ActionType
    entities: List[Entity]
    parameters: Dict[str, Any]
    confidence: ParseConfidence
    original_query: str
    interpreted_as: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    query: str
    parsed_action: Optional[ParsedAction]
    response: Optional[str]
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSession:
    """A conversation session with history."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    history: List[ConversationTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, ttl_seconds: int = DEFAULT_SESSION_TTL) -> bool:
        """Check if session has expired."""
        return (_utcnow() - self.last_activity).total_seconds() > ttl_seconds
    
    def add_turn(
        self,
        query: str,
        parsed_action: Optional[ParsedAction] = None,
        response: Optional[str] = None,
    ) -> ConversationTurn:
        """Add a turn to the conversation."""
        turn = ConversationTurn(
            query=query,
            parsed_action=parsed_action,
            response=response,
            timestamp=_utcnow(),
            context=dict(self.context),
        )
        self.history.append(turn)
        self.last_activity = _utcnow()
        
        # Limit history length
        if len(self.history) > MAX_HISTORY_LENGTH:
            self.history = self.history[-MAX_HISTORY_LENGTH:]
        
        return turn
    
    def get_context_entities(self) -> Dict[EntityType, List[Entity]]:
        """Get entities from recent conversation context."""
        entities: Dict[EntityType, List[Entity]] = defaultdict(list)
        
        for turn in reversed(self.history[-5:]):
            if turn.parsed_action:
                for entity in turn.parsed_action.entities:
                    entities[entity.entity_type].append(entity)
        
        return entities


@dataclass
class SymbolMatch:
    """A fuzzy symbol match result."""
    input_text: str
    matched_symbol: str
    entity_type: EntityType
    entity_id: str
    confidence: float
    match_type: str  # exact, partial, fuzzy


# =============================================================================
# Fuzzy Symbol Matching
# =============================================================================

class FuzzyMatcher:
    """
    Fuzzy symbol matcher for flexible entity recognition.
    
    Handles variations like:
    - RFQ 123, RFQ#123, RFQ-123, #123
    - Task: Review, Task Review, task-review
    """
    
    # Entity prefixes and patterns
    ENTITY_PATTERNS = {
        EntityType.RFQ: [
            r"rfq\s*#?\s*(\d+)",
            r"rfq-(\d+)",
            r"request\s+for\s+quote\s*#?\s*(\d+)",
            r"#(\d+)",  # Bare number with # prefix
        ],
        EntityType.TASK: [
            r"task\s*#?\s*(\d+)",
            r"task-(\d+)",
            r"task:\s*(.+?)(?:\s|$)",
        ],
        EntityType.QUOTE: [
            r"quote\s*#?\s*(\d+)",
            r"quote-(\d+)",
            r"q-?(\d+)",
        ],
        EntityType.ORDER: [
            r"order\s*#?\s*(\d+)",
            r"order-(\d+)",
            r"po\s*#?\s*(\d+)",
            r"po-(\d+)",
        ],
        EntityType.CUSTOMER: [
            r"customer\s*[:\s]+(.+?)(?:\s+(?:rfq|task|order|for)|$)",
            r"for\s+(?:customer\s+)?(.+?)(?:\s+(?:rfq|task|order)|$)",
        ],
    }
    
    def __init__(self, known_symbols: Optional[Dict[EntityType, List[str]]] = None):
        self.known_symbols = known_symbols or {}
    
    def add_known_symbols(
        self,
        entity_type: EntityType,
        symbols: List[str],
    ) -> None:
        """Add known symbols for an entity type."""
        if entity_type not in self.known_symbols:
            self.known_symbols[entity_type] = []
        self.known_symbols[entity_type].extend(symbols)
    
    def match(
        self,
        text: str,
        entity_type: Optional[EntityType] = None,
    ) -> List[SymbolMatch]:
        """
        Match symbols in text.
        
        Args:
            text: Text to search for symbols
            entity_type: Optional specific entity type to match
            
        Returns:
            List of symbol matches
        """
        matches = []
        text_lower = text.lower()
        
        entity_types = [entity_type] if entity_type else list(self.ENTITY_PATTERNS.keys())
        
        for etype in entity_types:
            patterns = self.ENTITY_PATTERNS.get(etype, [])
            
            for pattern in patterns:
                for m in re.finditer(pattern, text_lower, re.IGNORECASE):
                    value = m.group(1) if m.groups() else m.group(0)
                    
                    # Determine match type and confidence
                    match_type = "exact"
                    confidence = 0.95
                    
                    if "#" not in text and value.isdigit():
                        # Bare number - less confident
                        match_type = "partial"
                        confidence = 0.7
                    
                    matches.append(SymbolMatch(
                        input_text=m.group(0),
                        matched_symbol=value.strip(),
                        entity_type=etype,
                        entity_id=value.strip(),
                        confidence=confidence,
                        match_type=match_type,
                    ))
        
        # Also try fuzzy matching against known symbols
        for etype in entity_types:
            known = self.known_symbols.get(etype, [])
            if known:
                fuzzy_matches = self._fuzzy_match_known(text_lower, etype, known)
                matches.extend(fuzzy_matches)
        
        # Deduplicate
        seen = set()
        unique_matches = []
        for match in matches:
            key = (match.entity_type, match.entity_id)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches
    
    def _fuzzy_match_known(
        self,
        text: str,
        entity_type: EntityType,
        known_symbols: List[str],
    ) -> List[SymbolMatch]:
        """Fuzzy match against known symbols."""
        matches = []
        
        words = text.split()
        
        for symbol in known_symbols:
            symbol_lower = symbol.lower()
            
            # Try direct substring match
            if symbol_lower in text:
                matches.append(SymbolMatch(
                    input_text=symbol,
                    matched_symbol=symbol,
                    entity_type=entity_type,
                    entity_id=symbol,
                    confidence=0.9,
                    match_type="exact",
                ))
                continue
            
            # Try fuzzy match on each word
            for word in words:
                ratio = difflib.SequenceMatcher(None, word, symbol_lower).ratio()
                if ratio >= FUZZY_MATCH_THRESHOLD:
                    matches.append(SymbolMatch(
                        input_text=word,
                        matched_symbol=symbol,
                        entity_type=entity_type,
                        entity_id=symbol,
                        confidence=ratio,
                        match_type="fuzzy",
                    ))
        
        return matches
    
    def normalize_id(self, text: str, entity_type: EntityType) -> str:
        """Normalize an ID to canonical form."""
        # Extract just the numeric/alphanumeric ID
        text = text.strip()
        
        # Remove common prefixes
        prefixes = {
            EntityType.RFQ: ["rfq", "#", "-"],
            EntityType.TASK: ["task", "#", "-", ":"],
            EntityType.QUOTE: ["quote", "q", "#", "-"],
            EntityType.ORDER: ["order", "po", "#", "-"],
        }
        
        for prefix in prefixes.get(entity_type, []):
            text = re.sub(rf"^{re.escape(prefix)}\s*", "", text, flags=re.IGNORECASE)
        
        return text.strip()


# =============================================================================
# Action Parser
# =============================================================================

class ActionParser:
    """
    Parser that maps natural language to system actions.
    
    Uses pattern matching and LLM-style intent detection.
    """
    
    # Intent patterns (regex-based)
    INTENT_PATTERNS = {
        # View/Show intents
        ActionType.VIEW_RFQ: [
            r"(?:show|view|open|display|get)\s+(?:me\s+)?rfq\s*#?\s*\d+",
            r"(?:what(?:'s| is) (?:the )?)?rfq\s*#?\s*\d+",
            r"rfq\s*#?\s*\d+\s+details",
        ],
        ActionType.VIEW_TASK: [
            r"(?:show|view|open|display|get)\s+(?:me\s+)?task\s*#?\s*\d+",
        ],
        ActionType.VIEW_ORDER: [
            r"(?:show|view|open|display|get)\s+(?:me\s+)?(?:order|po)\s*#?\s*\d+",
        ],
        
        # List intents
        ActionType.LIST_RFQS: [
            r"(?:show|list|display|get)\s+(?:me\s+)?(?:all\s+)?rfqs?",
            r"(?:what|which)\s+rfqs?",
            r"my\s+rfqs?",
        ],
        ActionType.LIST_TASKS: [
            r"(?:show|list|display|get)\s+(?:me\s+)?(?:all\s+)?(?:my\s+)?tasks?",
            r"(?:what|which)\s+tasks?",
            r"to.?do\s+list",
        ],
        ActionType.LIST_APPROVALS: [
            r"(?:show|list|display|get)\s+(?:me\s+)?(?:pending\s+)?approvals?",
            r"(?:what|which)\s+(?:needs?\s+)?approv(?:al|ing)",
        ],
        ActionType.LIST_ORDERS: [
            r"(?:show|list|display|get)\s+(?:me\s+)?(?:all\s+)?orders?",
        ],
        
        # Create intents
        ActionType.CREATE_RFQ: [
            r"(?:create|new|add|make)\s+(?:a\s+)?(?:new\s+)?rfq",
            r"(?:start|open)\s+(?:a\s+)?(?:new\s+)?rfq",
        ],
        ActionType.CREATE_TASK: [
            r"(?:create|new|add|make)\s+(?:a\s+)?(?:new\s+)?task",
            r"remind\s+me\s+to",
        ],
        
        # Update intents
        ActionType.UPDATE_RFQ: [
            r"(?:update|edit|modify|change)\s+rfq",
        ],
        ActionType.ASSIGN_TASK: [
            r"(?:assign|give)\s+(?:this\s+)?(?:task|it)\s+to",
        ],
        ActionType.COMPLETE_TASK: [
            r"(?:complete|finish|done|mark.+done)\s+(?:this\s+)?task",
        ],
        
        # Approval intents
        ActionType.APPROVE: [
            r"(?:approve|accept|ok)\s+(?:this|it|rfq|quote)",
        ],
        ActionType.REJECT: [
            r"(?:reject|decline|deny)\s+(?:this|it|rfq|quote)",
        ],
        
        # Search intents
        ActionType.SEARCH: [
            r"(?:search|find|look\s+for)\s+",
            r"(?:where|who|what|which)\s+(?:is|are)",
        ],
        
        # Report intents
        ActionType.GENERATE_REPORT: [
            r"(?:generate|create|run|show)\s+(?:a\s+)?report",
            r"(?:export|download)\s+",
        ],
        
        # Navigation intents
        ActionType.NAVIGATE: [
            r"(?:go|navigate|take\s+me)\s+to",
            r"open\s+(?:the\s+)?(?:dashboard|settings|home)",
        ],
    }
    
    def __init__(self, fuzzy_matcher: Optional[FuzzyMatcher] = None):
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher()
    
    def parse(
        self,
        query: str,
        session: Optional[ConversationSession] = None,
    ) -> ParsedAction:
        """
        Parse a natural language query into an action.
        
        Args:
            query: The natural language query
            session: Optional conversation session for context
            
        Returns:
            ParsedAction with detected intent and entities
        """
        query_lower = query.lower().strip()
        
        # Check for follow-up references
        is_follow_up = self._is_follow_up(query_lower)
        
        # Detect action type
        action_type, pattern_confidence = self._detect_action_type(query_lower)
        
        # Extract entities
        entities = self._extract_entities(query, session, is_follow_up)
        
        # Resolve context-dependent references
        if is_follow_up and session:
            entities = self._resolve_context_references(
                query_lower, entities, session
            )
        
        # Build parameters
        parameters = self._build_parameters(action_type, entities)
        
        # Determine confidence
        confidence = self._calculate_confidence(
            action_type, entities, pattern_confidence
        )
        
        # Generate interpretation
        interpreted_as = self._generate_interpretation(action_type, entities)
        
        # Generate suggestions for unclear queries
        suggestions = []
        if confidence in [ParseConfidence.LOW, ParseConfidence.UNCERTAIN]:
            suggestions = self._generate_suggestions(query, action_type, entities)
        
        return ParsedAction(
            action_type=action_type,
            entities=entities,
            parameters=parameters,
            confidence=confidence,
            original_query=query,
            interpreted_as=interpreted_as,
            suggestions=suggestions,
        )
    
    def _is_follow_up(self, query: str) -> bool:
        """Check if query is a follow-up to previous conversation."""
        follow_up_indicators = [
            r"^(?:now|then|and|also)\s+",
            r"^(?:those|these|that|this)\s+",
            r"^(?:filter|sort|show)\s+(?:them|those|it)",
            r"^for\s+(?:customer|that)",
            r"^(?:what|how)\s+about",
            r"^same\s+",
        ]
        
        return any(re.match(p, query) for p in follow_up_indicators)
    
    def _detect_action_type(
        self,
        query: str,
    ) -> Tuple[ActionType, float]:
        """Detect the action type from query."""
        for action_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return action_type, 0.9
        
        # Fallback heuristics
        if any(word in query for word in ["show", "list", "display", "get"]):
            return ActionType.LIST_TASKS, 0.5
        
        if any(word in query for word in ["search", "find", "where"]):
            return ActionType.SEARCH, 0.6
        
        return ActionType.UNKNOWN, 0.3
    
    def _extract_entities(
        self,
        query: str,
        session: Optional[ConversationSession],
        is_follow_up: bool,
    ) -> List[Entity]:
        """Extract entities from query."""
        entities = []
        query_lower = query.lower()
        
        # Use fuzzy matcher
        symbol_matches = self.fuzzy_matcher.match(query)
        
        for match in symbol_matches:
            entity = Entity(
                entity_type=match.entity_type,
                value=match.input_text,
                normalized_value=match.entity_id,
                start_pos=query_lower.find(match.input_text.lower()),
                end_pos=query_lower.find(match.input_text.lower()) + len(match.input_text),
                confidence=match.confidence,
            )
            entities.append(entity)
        
        # Extract status filters
        status_patterns = {
            "pending": ["pending", "awaiting", "waiting"],
            "approved": ["approved", "accepted"],
            "rejected": ["rejected", "declined"],
            "open": ["open", "active", "in progress"],
            "closed": ["closed", "completed", "done"],
            "overdue": ["overdue", "late", "past due"],
        }
        
        for status, keywords in status_patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    pos = query_lower.find(keyword)
                    entities.append(Entity(
                        entity_type=EntityType.STATUS,
                        value=keyword,
                        normalized_value=status,
                        start_pos=pos,
                        end_pos=pos + len(keyword),
                        confidence=0.85,
                    ))
                    break
        
        # Extract priority
        priority_patterns = {
            "high": ["high priority", "urgent", "critical", "asap"],
            "medium": ["medium priority", "normal"],
            "low": ["low priority", "minor"],
        }
        
        for priority, keywords in priority_patterns.items():
            for keyword in keywords:
                if keyword in query_lower:
                    pos = query_lower.find(keyword)
                    entities.append(Entity(
                        entity_type=EntityType.PRIORITY,
                        value=keyword,
                        normalized_value=priority,
                        start_pos=pos,
                        end_pos=pos + len(keyword),
                        confidence=0.9,
                    ))
                    break
        
        # Extract date references
        date_patterns = [
            (r"today", "today"),
            (r"tomorrow", "tomorrow"),
            (r"this week", "this_week"),
            (r"last week", "last_week"),
            (r"next week", "next_week"),
            (r"this month", "this_month"),
        ]
        
        for pattern, normalized in date_patterns:
            date_match: re.Match[str] | None = re.search(pattern, query_lower)
            if date_match:
                entities.append(Entity(
                    entity_type=EntityType.DATE,
                    value=date_match.group(0),
                    normalized_value=normalized,
                    start_pos=date_match.start(),
                    end_pos=date_match.end(),
                    confidence=0.95,
                ))
        
        return entities
    
    def _resolve_context_references(
        self,
        query: str,
        entities: List[Entity],
        session: ConversationSession,
    ) -> List[Entity]:
        """Resolve pronoun/demonstrative references from context."""
        context_entities = session.get_context_entities()
        
        # Check for pronoun references
        reference_patterns = [
            (r"\b(?:them|those|these)\b", None),  # Plural reference
            (r"\b(?:it|this|that)\b", None),  # Singular reference
        ]
        
        for pattern, _ in reference_patterns:
            if re.search(pattern, query):
                # Look for entities in context that match the action
                for entity_type, context_ents in context_entities.items():
                    if context_ents and entity_type not in [
                        e.entity_type for e in entities
                    ]:
                        # Add the most recent context entity
                        entities.append(context_ents[0])
                        break
        
        # Also inherit filters if query mentions filtering
        if "filter" in query and session.context.get("last_filters"):
            last_filters = session.context.get("last_filters")
            if isinstance(last_filters, dict):
                existing_types = {e.entity_type for e in entities}
                for key, value in last_filters.items():
                    try:
                        entity_type = EntityType(key)
                    except ValueError:
                        continue
                    if entity_type in existing_types:
                        continue
                    entities.append(
                        Entity(
                            entity_type=entity_type,
                            value=str(value),
                            normalized_value=value,
                            start_pos=-1,
                            end_pos=-1,
                            confidence=0.3,
                        )
                    )
        
        return entities
    
    def _build_parameters(
        self,
        action_type: ActionType,
        entities: List[Entity],
    ) -> Dict[str, Any]:
        """Build action parameters from entities."""
        params: Dict[str, Any] = {}
        
        for entity in entities:
            key = entity.entity_type.value
            
            if key in params:
                # Handle multiple entities of same type
                if not isinstance(params[key], list):
                    params[key] = [params[key]]
                params[key].append(entity.normalized_value)
            else:
                params[key] = entity.normalized_value
        
        return params
    
    def _calculate_confidence(
        self,
        action_type: ActionType,
        entities: List[Entity],
        pattern_confidence: float,
    ) -> ParseConfidence:
        """Calculate overall parsing confidence."""
        if action_type == ActionType.UNKNOWN:
            return ParseConfidence.UNCERTAIN
        
        entity_confidence = (
            sum(e.confidence for e in entities) / len(entities)
            if entities else 0.5
        )
        
        avg_confidence = (pattern_confidence + entity_confidence) / 2
        
        if avg_confidence >= 0.8:
            return ParseConfidence.HIGH
        elif avg_confidence >= 0.6:
            return ParseConfidence.MEDIUM
        elif avg_confidence >= 0.4:
            return ParseConfidence.LOW
        else:
            return ParseConfidence.UNCERTAIN
    
    def _generate_interpretation(
        self,
        action_type: ActionType,
        entities: List[Entity],
    ) -> str:
        """Generate human-readable interpretation."""
        action_names = {
            ActionType.VIEW_RFQ: "View RFQ",
            ActionType.LIST_RFQS: "List RFQs",
            ActionType.CREATE_RFQ: "Create new RFQ",
            ActionType.VIEW_TASK: "View Task",
            ActionType.LIST_TASKS: "List Tasks",
            ActionType.CREATE_TASK: "Create new Task",
            ActionType.LIST_APPROVALS: "List pending approvals",
            ActionType.APPROVE: "Approve item",
            ActionType.REJECT: "Reject item",
            ActionType.SEARCH: "Search",
            ActionType.NAVIGATE: "Navigate",
            ActionType.UNKNOWN: "Unknown action",
        }
        
        base = action_names.get(action_type, str(action_type.value))
        
        entity_parts = []
        for entity in entities:
            if entity.entity_type == EntityType.RFQ:
                entity_parts.append(f"RFQ #{entity.normalized_value}")
            elif entity.entity_type == EntityType.TASK:
                entity_parts.append(f"Task #{entity.normalized_value}")
            elif entity.entity_type == EntityType.STATUS:
                entity_parts.append(f"status={entity.normalized_value}")
            elif entity.entity_type == EntityType.CUSTOMER:
                entity_parts.append(f"customer={entity.normalized_value}")
        
        if entity_parts:
            return f"{base}: {', '.join(entity_parts)}"
        
        return base
    
    def _generate_suggestions(
        self,
        query: str,
        action_type: ActionType,
        entities: List[Entity],
    ) -> List[str]:
        """Generate suggestions for unclear queries."""
        suggestions = []
        
        if action_type == ActionType.UNKNOWN:
            suggestions.extend([
                "Try: 'Show my tasks'",
                "Try: 'List pending approvals'",
                "Try: 'View RFQ 123'",
            ])
        elif not entities:
            if action_type in [ActionType.VIEW_RFQ, ActionType.VIEW_TASK]:
                suggestions.append("Please specify an ID, e.g., 'RFQ 123'")
        
        return suggestions


# =============================================================================
# Conversation Manager
# =============================================================================

class ConversationManager:
    """
    Manages multi-turn conversation sessions.
    """
    
    def __init__(
        self,
        session_ttl: int = DEFAULT_SESSION_TTL,
        parser: Optional[ActionParser] = None,
    ):
        self.session_ttl = session_ttl
        self.parser = parser or ActionParser()
        self._sessions: Dict[str, ConversationSession] = {}
    
    def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
    ) -> ConversationSession:
        """Get existing session or create new one."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            
            if not session.is_expired(self.session_ttl):
                return session
            
            # Clean up expired session
            del self._sessions[session_id]
        
        # Create new session
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            created_at=_utcnow(),
            last_activity=_utcnow(),
        )
        self._sessions[session_id] = session
        
        return session
    
    def process_query(
        self,
        session_id: str,
        user_id: str,
        query: str,
    ) -> Tuple[ParsedAction, ConversationSession]:
        """
        Process a query in a conversation session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            query: Natural language query
            
        Returns:
            Tuple of (ParsedAction, ConversationSession)
        """
        session = self.get_or_create_session(session_id, user_id)
        
        # Parse the query with session context
        parsed_action = self.parser.parse(query, session)
        
        # Add to conversation history
        session.add_turn(query, parsed_action)
        
        # Update session context with extracted entities
        for entity in parsed_action.entities:
            session.context[entity.entity_type.value] = entity.normalized_value
        
        return parsed_action, session
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions. Returns count removed."""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(self.session_ttl)
        ]
        
        for sid in expired:
            del self._sessions[sid]
        
        return len(expired)
    
    def get_session_count(self) -> int:
        """Get active session count."""
        return len(self._sessions)


# =============================================================================
# NLP Command Palette
# =============================================================================

class NLPCommandPalette:
    """
    Main NLP command palette interface.
    
    Provides natural language interface to system commands.
    """
    
    def __init__(
        self,
        session_ttl: int = DEFAULT_SESSION_TTL,
        fuzzy_matcher: Optional[FuzzyMatcher] = None,
    ):
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher()
        self.parser = ActionParser(self.fuzzy_matcher)
        self.conversation_manager = ConversationManager(
            session_ttl=session_ttl,
            parser=self.parser,
        )
        
        # Action handlers
        self._handlers: Dict[ActionType, Callable[[ParsedAction], Any]] = {}
    
    def register_handler(
        self,
        action_type: ActionType,
        handler: Callable[[ParsedAction], Any],
    ) -> None:
        """Register a handler for an action type."""
        self._handlers[action_type] = handler
    
    def register_known_symbols(
        self,
        entity_type: EntityType,
        symbols: List[str],
    ) -> None:
        """Register known symbols for fuzzy matching."""
        self.fuzzy_matcher.add_known_symbols(entity_type, symbols)
    
    def execute(
        self,
        query: str,
        session_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Execute a natural language command.
        
        Args:
            query: Natural language query
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Execution result with action details
        """
        # Parse the query
        parsed_action, session = self.conversation_manager.process_query(
            session_id, user_id, query
        )
        
        result = {
            "query": query,
            "action_type": parsed_action.action_type.value,
            "interpreted_as": parsed_action.interpreted_as,
            "confidence": parsed_action.confidence.value,
            "parameters": parsed_action.parameters,
            "suggestions": parsed_action.suggestions,
            "executed": False,
            "result": None,
        }
        
        # Execute handler if registered
        handler = self._handlers.get(parsed_action.action_type)
        if handler:
            try:
                result["result"] = handler(parsed_action)
                result["executed"] = True
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def get_suggestions(
        self,
        partial_query: str,
        session_id: Optional[str] = None,
    ) -> List[str]:
        """
        Get autocomplete suggestions for partial query.
        
        Args:
            partial_query: Partial natural language query
            session_id: Optional session for context
            
        Returns:
            List of suggested completions
        """
        suggestions = []
        partial_lower = partial_query.lower().strip()
        
        # Common command patterns
        patterns = [
            ("show", ["show my tasks", "show pending approvals", "show RFQ"]),
            ("list", ["list RFQs", "list tasks", "list orders"]),
            ("create", ["create new RFQ", "create task"]),
            ("view", ["view RFQ", "view task", "view order"]),
            ("search", ["search for", "search RFQs", "search customers"]),
            ("approve", ["approve RFQ", "approve quote"]),
            ("filter", ["filter by customer", "filter by status"]),
        ]
        
        for prefix, completions in patterns:
            if partial_lower.startswith(prefix):
                suggestions.extend(completions)
            elif prefix.startswith(partial_lower):
                suggestions.extend(completions)
        
        # Add context-aware suggestions
        if session_id:
            session = self.conversation_manager._sessions.get(session_id)
            if session:
                context_entities = session.get_context_entities()
                
                if context_entities.get(EntityType.RFQ):
                    rfq_id = context_entities[EntityType.RFQ][0].normalized_value
                    suggestions.append(f"show details for RFQ {rfq_id}")
                    suggestions.append(f"approve RFQ {rfq_id}")
        
        # Deduplicate and limit
        unique = list(dict.fromkeys(suggestions))
        return unique[:10]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get palette statistics."""
        return {
            "active_sessions": self.conversation_manager.get_session_count(),
            "registered_handlers": len(self._handlers),
            "known_symbol_types": len(self.fuzzy_matcher.known_symbols),
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_nlp_command_palette(
    session_ttl: int = DEFAULT_SESSION_TTL,
) -> NLPCommandPalette:
    """
    Create an NLP command palette.
    
    Args:
        session_ttl: Session timeout in seconds
        
    Returns:
        Configured NLPCommandPalette
    """
    return NLPCommandPalette(session_ttl=session_ttl)
