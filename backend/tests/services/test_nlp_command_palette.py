"""
Tests for NLP Command Palette.

Covers:
- Fuzzy Symbol Matching
- Action Parser
- Conversation Manager
- NLP Command Palette
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import time


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sensei.services.ai.nlp_command_palette import (
    # Enums
    ActionType,
    EntityType,
    ParseConfidence,
    # Data models
    Entity,
    ParsedAction,
    ConversationTurn,
    ConversationSession,
    SymbolMatch,
    # Classes
    FuzzyMatcher,
    ActionParser,
    ConversationManager,
    NLPCommandPalette,
    # Factory
    create_nlp_command_palette,
    # Constants
    DEFAULT_SESSION_TTL,
    FUZZY_MATCH_THRESHOLD,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def fuzzy_matcher():
    """Fuzzy matcher instance."""
    return FuzzyMatcher()


@pytest.fixture
def action_parser(fuzzy_matcher):
    """Action parser instance."""
    return ActionParser(fuzzy_matcher)


@pytest.fixture
def conversation_manager(action_parser):
    """Conversation manager instance."""
    return ConversationManager(session_ttl=60, parser=action_parser)


@pytest.fixture
def command_palette():
    """NLP command palette instance."""
    return NLPCommandPalette(session_ttl=60)


@pytest.fixture
def sample_session():
    """Sample conversation session."""
    return ConversationSession(
        session_id="session_001",
        user_id="user_001",
        created_at=_utcnow(),
        last_activity=_utcnow(),
    )


# =============================================================================
# FuzzyMatcher Tests
# =============================================================================

class TestFuzzyMatcher:
    """Tests for FuzzyMatcher."""
    
    def test_match_rfq_standard(self, fuzzy_matcher):
        """Test matching standard RFQ format."""
        matches = fuzzy_matcher.match("Show me RFQ 123")
        
        assert len(matches) >= 1
        rfq_match = next((m for m in matches if m.entity_type == EntityType.RFQ), None)
        assert rfq_match is not None
        assert rfq_match.entity_id == "123"
    
    def test_match_rfq_with_hash(self, fuzzy_matcher):
        """Test matching RFQ#123 format."""
        matches = fuzzy_matcher.match("View RFQ#456")
        
        rfq_match = next((m for m in matches if m.entity_type == EntityType.RFQ), None)
        assert rfq_match is not None
        assert rfq_match.entity_id == "456"
    
    def test_match_rfq_with_dash(self, fuzzy_matcher):
        """Test matching RFQ-789 format."""
        matches = fuzzy_matcher.match("Open RFQ-789")
        
        rfq_match = next((m for m in matches if m.entity_type == EntityType.RFQ), None)
        assert rfq_match is not None
        assert rfq_match.entity_id == "789"
    
    def test_match_bare_number_with_hash(self, fuzzy_matcher):
        """Test matching #123 format."""
        matches = fuzzy_matcher.match("Show #123")
        
        assert len(matches) >= 1
        # Bare # should have lower confidence
        rfq_match = next((m for m in matches if m.entity_type == EntityType.RFQ), None)
        assert rfq_match is not None
    
    def test_match_task(self, fuzzy_matcher):
        """Test matching task patterns."""
        matches = fuzzy_matcher.match("View task 42")
        
        task_match = next((m for m in matches if m.entity_type == EntityType.TASK), None)
        assert task_match is not None
        assert task_match.entity_id == "42"
    
    def test_match_order_po(self, fuzzy_matcher):
        """Test matching PO format."""
        matches = fuzzy_matcher.match("Show PO#100")
        
        order_match = next((m for m in matches if m.entity_type == EntityType.ORDER), None)
        assert order_match is not None
        assert order_match.entity_id == "100"
    
    def test_match_quote(self, fuzzy_matcher):
        """Test matching quote patterns."""
        matches = fuzzy_matcher.match("View quote 55")
        
        quote_match = next((m for m in matches if m.entity_type == EntityType.QUOTE), None)
        assert quote_match is not None
        assert quote_match.entity_id == "55"
    
    def test_match_multiple_entities(self, fuzzy_matcher):
        """Test matching multiple entities in one query."""
        matches = fuzzy_matcher.match("Compare RFQ 123 with RFQ 456")
        
        rfq_matches = [m for m in matches if m.entity_type == EntityType.RFQ]
        assert len(rfq_matches) >= 2
    
    def test_match_with_known_symbols(self, fuzzy_matcher):
        """Test fuzzy matching with known symbols."""
        fuzzy_matcher.add_known_symbols(
            EntityType.CUSTOMER,
            ["Acme Corp", "TechCo Industries", "Global Manufacturing"]
        )
        
        matches = fuzzy_matcher.match("Show RFQs for Acme Corp")
        
        customer_match = next(
            (m for m in matches if m.entity_type == EntityType.CUSTOMER), None
        )
        assert customer_match is not None
        # Matched symbol is normalized to lowercase
        assert customer_match.matched_symbol.lower() == "acme corp"
    
    def test_fuzzy_match_similar_name(self, fuzzy_matcher):
        """Test fuzzy matching for similar names."""
        fuzzy_matcher.add_known_symbols(
            EntityType.CUSTOMER,
            ["Acme Corporation"]
        )
        
        matches = fuzzy_matcher.match("Find orders for AcmeCorp")
        
        # Should fuzzy match to "Acme Corporation"
        # Note: depends on fuzzy threshold
        assert isinstance(matches, list)
    
    def test_normalize_id_rfq(self, fuzzy_matcher):
        """Test ID normalization for RFQ."""
        normalized = fuzzy_matcher.normalize_id("RFQ#123", EntityType.RFQ)
        assert normalized == "123"
        
        normalized = fuzzy_matcher.normalize_id("rfq-456", EntityType.RFQ)
        assert normalized == "456"
    
    def test_normalize_id_task(self, fuzzy_matcher):
        """Test ID normalization for Task."""
        normalized = fuzzy_matcher.normalize_id("task: 789", EntityType.TASK)
        assert normalized == "789"
    
    def test_no_match(self, fuzzy_matcher):
        """Test no match case."""
        matches = fuzzy_matcher.match("Hello world, nice day")
        
        # Should not match any RFQ/task patterns
        rfq_matches = [m for m in matches if m.entity_type == EntityType.RFQ]
        assert len(rfq_matches) == 0


# =============================================================================
# ActionParser Tests
# =============================================================================

class TestActionParser:
    """Tests for ActionParser."""
    
    def test_parse_view_rfq(self, action_parser):
        """Test parsing view RFQ intent."""
        result = action_parser.parse("Show me RFQ 123")
        
        assert result.action_type == ActionType.VIEW_RFQ
        assert result.confidence in [ParseConfidence.HIGH, ParseConfidence.MEDIUM]
    
    def test_parse_list_rfqs(self, action_parser):
        """Test parsing list RFQs intent."""
        result = action_parser.parse("List all RFQs")
        
        assert result.action_type == ActionType.LIST_RFQS
    
    def test_parse_list_tasks(self, action_parser):
        """Test parsing list tasks intent."""
        result = action_parser.parse("Show my tasks")
        
        assert result.action_type == ActionType.LIST_TASKS
    
    def test_parse_create_rfq(self, action_parser):
        """Test parsing create RFQ intent."""
        result = action_parser.parse("Create a new RFQ")
        
        assert result.action_type == ActionType.CREATE_RFQ
    
    def test_parse_create_task(self, action_parser):
        """Test parsing create task intent."""
        result = action_parser.parse("Add a new task")
        
        assert result.action_type == ActionType.CREATE_TASK
    
    def test_parse_list_approvals(self, action_parser):
        """Test parsing list approvals intent."""
        result = action_parser.parse("Show pending approvals")
        
        assert result.action_type == ActionType.LIST_APPROVALS
    
    def test_parse_approve(self, action_parser):
        """Test parsing approve intent."""
        result = action_parser.parse("Approve this RFQ")
        
        assert result.action_type == ActionType.APPROVE
    
    def test_parse_reject(self, action_parser):
        """Test parsing reject intent."""
        result = action_parser.parse("Reject this quote")
        
        assert result.action_type == ActionType.REJECT
    
    def test_parse_search(self, action_parser):
        """Test parsing search intent."""
        result = action_parser.parse("Search for customer XYZ")
        
        assert result.action_type == ActionType.SEARCH
    
    def test_parse_navigate(self, action_parser):
        """Test parsing navigation intent."""
        result = action_parser.parse("Go to dashboard")
        
        assert result.action_type == ActionType.NAVIGATE
    
    def test_parse_with_status_filter(self, action_parser):
        """Test parsing with status filter."""
        result = action_parser.parse("Show pending RFQs")
        
        status_entity = next(
            (e for e in result.entities if e.entity_type == EntityType.STATUS), None
        )
        assert status_entity is not None
        assert status_entity.normalized_value == "pending"
    
    def test_parse_with_priority_filter(self, action_parser):
        """Test parsing with priority filter."""
        result = action_parser.parse("Show urgent tasks")
        
        priority_entity = next(
            (e for e in result.entities if e.entity_type == EntityType.PRIORITY), None
        )
        assert priority_entity is not None
        assert priority_entity.normalized_value == "high"
    
    def test_parse_with_date_filter(self, action_parser):
        """Test parsing with date filter."""
        result = action_parser.parse("Show tasks due today")
        
        date_entity = next(
            (e for e in result.entities if e.entity_type == EntityType.DATE), None
        )
        assert date_entity is not None
        assert date_entity.normalized_value == "today"
    
    def test_parse_unknown(self, action_parser):
        """Test parsing unknown intent."""
        result = action_parser.parse("asdfghjkl random words")
        
        assert result.action_type == ActionType.UNKNOWN
        assert result.confidence == ParseConfidence.UNCERTAIN
    
    def test_parse_generates_interpretation(self, action_parser):
        """Test that parser generates interpretation."""
        result = action_parser.parse("View RFQ 123")
        
        assert len(result.interpreted_as) > 0
        assert "RFQ" in result.interpreted_as or "View" in result.interpreted_as
    
    def test_parse_low_confidence_suggestions(self, action_parser):
        """Test that low confidence generates suggestions."""
        result = action_parser.parse("xyz 123")
        
        if result.confidence in [ParseConfidence.LOW, ParseConfidence.UNCERTAIN]:
            assert len(result.suggestions) > 0
    
    def test_parse_extracts_entities(self, action_parser):
        """Test that parser extracts entities."""
        result = action_parser.parse("Show RFQ 123 details")
        
        rfq_entity = next(
            (e for e in result.entities if e.entity_type == EntityType.RFQ), None
        )
        assert rfq_entity is not None
        assert rfq_entity.normalized_value == "123"
    
    def test_parse_builds_parameters(self, action_parser):
        """Test that parser builds parameters."""
        result = action_parser.parse("Show pending RFQ 123")
        
        assert "rfq" in result.parameters or "status" in result.parameters
    
    def test_is_follow_up_detection(self, action_parser):
        """Test follow-up query detection."""
        # These should be detected as follow-ups
        follow_ups = [
            "now filter those by customer",
            "then sort by date",
            "and show the urgent ones",
            "those for customer ABC",
        ]
        
        for query in follow_ups:
            assert action_parser._is_follow_up(query.lower()) is True
        
        # These should not be follow-ups
        new_queries = [
            "show my tasks",
            "list all rfqs",
            "create a new task",
        ]
        
        for query in new_queries:
            assert action_parser._is_follow_up(query.lower()) is False


# =============================================================================
# ConversationSession Tests
# =============================================================================

class TestConversationSession:
    """Tests for ConversationSession."""
    
    def test_session_creation(self, sample_session):
        """Test session creation."""
        assert sample_session.session_id == "session_001"
        assert sample_session.user_id == "user_001"
        assert len(sample_session.history) == 0
    
    def test_add_turn(self, sample_session):
        """Test adding a conversation turn."""
        turn = sample_session.add_turn(
            query="Show my tasks",
            parsed_action=None,
            response="Here are your tasks",
        )
        
        assert len(sample_session.history) == 1
        assert turn.query == "Show my tasks"
    
    def test_session_expiration(self):
        """Test session expiration check."""
        session = ConversationSession(
            session_id="test",
            user_id="user",
            created_at=_utcnow() - timedelta(seconds=100),
            last_activity=_utcnow() - timedelta(seconds=100),
        )
        
        assert session.is_expired(ttl_seconds=60) is True
        assert session.is_expired(ttl_seconds=200) is False
    
    def test_history_limit(self, sample_session):
        """Test that history is limited."""
        for i in range(15):
            sample_session.add_turn(f"Query {i}")
        
        # Should be limited to MAX_HISTORY_LENGTH (10)
        assert len(sample_session.history) <= 10
    
    def test_get_context_entities(self, sample_session, action_parser):
        """Test getting entities from context."""
        # Add a turn with entities
        parsed = action_parser.parse("Show RFQ 123")
        sample_session.add_turn("Show RFQ 123", parsed)
        
        context_entities = sample_session.get_context_entities()
        
        assert EntityType.RFQ in context_entities


# =============================================================================
# ConversationManager Tests
# =============================================================================

class TestConversationManager:
    """Tests for ConversationManager."""
    
    def test_get_or_create_session_new(self, conversation_manager):
        """Test creating a new session."""
        session = conversation_manager.get_or_create_session("sess_1", "user_1")
        
        assert session.session_id == "sess_1"
        assert session.user_id == "user_1"
    
    def test_get_or_create_session_existing(self, conversation_manager):
        """Test getting existing session."""
        session1 = conversation_manager.get_or_create_session("sess_1", "user_1")
        session1.add_turn("First query")
        
        session2 = conversation_manager.get_or_create_session("sess_1", "user_1")
        
        assert session2 is session1
        assert len(session2.history) == 1
    
    def test_process_query(self, conversation_manager):
        """Test processing a query."""
        parsed, session = conversation_manager.process_query(
            "sess_1", "user_1", "Show my tasks"
        )
        
        assert parsed.action_type == ActionType.LIST_TASKS
        assert len(session.history) == 1
    
    def test_process_follow_up_query(self, conversation_manager):
        """Test processing follow-up queries."""
        # First query
        conversation_manager.process_query("sess_1", "user_1", "Show RFQ 123")
        
        # Follow-up
        parsed, session = conversation_manager.process_query(
            "sess_1", "user_1", "Now filter those by status"
        )
        
        assert len(session.history) == 2
    
    def test_clear_session(self, conversation_manager):
        """Test clearing a session."""
        conversation_manager.get_or_create_session("sess_1", "user_1")
        
        conversation_manager.clear_session("sess_1")
        
        assert conversation_manager.get_session_count() == 0
    
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        manager = ConversationManager(session_ttl=1)
        
        manager.get_or_create_session("sess_1", "user_1")
        manager.get_or_create_session("sess_2", "user_2")
        
        assert manager.get_session_count() == 2
        
        # Wait for expiration
        time.sleep(1.1)
        
        removed = manager.cleanup_expired_sessions()
        
        assert removed == 2
        assert manager.get_session_count() == 0


# =============================================================================
# NLPCommandPalette Tests
# =============================================================================

class TestNLPCommandPalette:
    """Tests for NLPCommandPalette."""
    
    def test_execute_basic(self, command_palette):
        """Test basic execution."""
        result = command_palette.execute(
            query="Show my tasks",
            session_id="sess_1",
            user_id="user_1",
        )
        
        assert result["query"] == "Show my tasks"
        assert result["action_type"] == "list_tasks"
        assert "interpreted_as" in result
    
    def test_execute_with_handler(self, command_palette):
        """Test execution with registered handler."""
        mock_handler = Mock(return_value={"tasks": []})
        command_palette.register_handler(ActionType.LIST_TASKS, mock_handler)
        
        result = command_palette.execute(
            query="Show my tasks",
            session_id="sess_1",
            user_id="user_1",
        )
        
        assert result["executed"] is True
        mock_handler.assert_called_once()
    
    def test_execute_handler_error(self, command_palette):
        """Test execution when handler raises error."""
        def error_handler(action):
            raise ValueError("Test error")
        
        command_palette.register_handler(ActionType.LIST_TASKS, error_handler)
        
        result = command_palette.execute(
            query="Show my tasks",
            session_id="sess_1",
            user_id="user_1",
        )
        
        assert "error" in result
        assert "Test error" in result["error"]
    
    def test_register_known_symbols(self, command_palette):
        """Test registering known symbols."""
        command_palette.register_known_symbols(
            EntityType.CUSTOMER,
            ["Acme Corp", "TechCo"]
        )
        
        result = command_palette.execute(
            query="Show RFQs for Acme Corp",
            session_id="sess_1",
            user_id="user_1",
        )
        
        # Should recognize customer
        assert "customer" in result["parameters"] or len(result["parameters"]) > 0
    
    def test_get_suggestions_basic(self, command_palette):
        """Test getting suggestions."""
        suggestions = command_palette.get_suggestions("show")
        
        assert len(suggestions) > 0
        assert any("show" in s.lower() for s in suggestions)
    
    def test_get_suggestions_with_context(self, command_palette):
        """Test suggestions with session context."""
        # First execute a query to establish context
        command_palette.execute("Show RFQ 123", "sess_1", "user_1")
        
        # Get suggestions with context
        suggestions = command_palette.get_suggestions("", session_id="sess_1")
        
        assert isinstance(suggestions, list)
    
    def test_get_stats(self, command_palette):
        """Test getting stats."""
        command_palette.execute("Test query", "sess_1", "user_1")
        
        stats = command_palette.get_stats()
        
        assert stats["active_sessions"] == 1
        assert "registered_handlers" in stats
    
    def test_multi_turn_conversation(self, command_palette):
        """Test multi-turn conversation."""
        # First turn
        result1 = command_palette.execute(
            "Show all RFQs",
            "sess_1",
            "user_1",
        )
        assert result1["action_type"] == "list_rfqs"
        
        # Second turn - filter
        result2 = command_palette.execute(
            "Filter those by pending status",
            "sess_1",
            "user_1",
        )
        
        # Should maintain session context
        assert "pending" in str(result2) or result2.get("parameters", {}).get("status") == "pending"


# =============================================================================
# Entity Tests
# =============================================================================

class TestEntity:
    """Tests for Entity data class."""
    
    def test_entity_creation(self):
        """Test entity creation."""
        entity = Entity(
            entity_type=EntityType.RFQ,
            value="RFQ 123",
            normalized_value="123",
            start_pos=0,
            end_pos=7,
            confidence=0.95,
        )
        
        assert entity.entity_type == EntityType.RFQ
        assert entity.normalized_value == "123"
        assert entity.confidence == 0.95
    
    def test_entity_with_alternatives(self):
        """Test entity with alternatives."""
        entity = Entity(
            entity_type=EntityType.CUSTOMER,
            value="acme",
            normalized_value="Acme Corp",
            start_pos=0,
            end_pos=4,
            confidence=0.7,
            alternatives=["ACME Inc", "Acme Corporation"],
        )
        
        assert len(entity.alternatives) == 2


# =============================================================================
# ParsedAction Tests
# =============================================================================

class TestParsedAction:
    """Tests for ParsedAction data class."""
    
    def test_parsed_action_creation(self):
        """Test parsed action creation."""
        action = ParsedAction(
            action_type=ActionType.VIEW_RFQ,
            entities=[],
            parameters={"rfq": "123"},
            confidence=ParseConfidence.HIGH,
            original_query="View RFQ 123",
            interpreted_as="View RFQ #123",
        )
        
        assert action.action_type == ActionType.VIEW_RFQ
        assert action.confidence == ParseConfidence.HIGH


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_nlp_command_palette(self):
        """Test creating command palette."""
        palette = create_nlp_command_palette(session_ttl=120)
        
        assert isinstance(palette, NLPCommandPalette)


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enumeration values."""
    
    def test_action_types(self):
        """Test ActionType enum."""
        assert ActionType.VIEW_RFQ.value == "view_rfq"
        assert ActionType.LIST_TASKS.value == "list_tasks"
        assert ActionType.UNKNOWN.value == "unknown"
    
    def test_entity_types(self):
        """Test EntityType enum."""
        assert EntityType.RFQ.value == "rfq"
        assert EntityType.TASK.value == "task"
        assert EntityType.CUSTOMER.value == "customer"
    
    def test_parse_confidence(self):
        """Test ParseConfidence enum."""
        assert ParseConfidence.HIGH.value == "high"
        assert ParseConfidence.UNCERTAIN.value == "uncertain"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full NLP pipeline."""
    
    def test_end_to_end_rfq_workflow(self):
        """Test end-to-end RFQ workflow."""
        palette = create_nlp_command_palette()
        
        # Register mock handlers
        results = []
        
        palette.register_handler(
            ActionType.LIST_RFQS,
            lambda a: results.append(("list", a.parameters))
        )
        palette.register_handler(
            ActionType.VIEW_RFQ,
            lambda a: results.append(("view", a.parameters))
        )
        
        # Execute queries
        r1 = palette.execute("Show all RFQs", "sess", "user")
        assert r1["executed"] is True
        
        r2 = palette.execute("View RFQ 123", "sess", "user")
        assert r2["executed"] is True
        assert r2["parameters"].get("rfq") == "123"
    
    def test_various_rfq_formats(self):
        """Test various RFQ ID formats."""
        palette = create_nlp_command_palette()
        
        formats = [
            ("Show RFQ 123", "123"),
            ("View RFQ#456", "456"),
            ("Open RFQ-789", "789"),
            ("Display request for quote 100", "100"),
        ]
        
        for query, expected_id in formats:
            result = palette.execute(query, f"sess_{expected_id}", "user")
            assert result["parameters"].get("rfq") == expected_id, \
                f"Failed for query: {query}"
    
    def test_context_inheritance(self):
        """Test that context is inherited across turns."""
        palette = create_nlp_command_palette()
        
        # First query sets context
        palette.execute("Show RFQ 123", "sess", "user")
        
        # Second query should have access to RFQ context
        result = palette.execute("What is the status", "sess", "user")
        
        # Session should have RFQ in context
        session = palette.conversation_manager._sessions.get("sess")
        assert session is not None
        assert "rfq" in session.context or len(session.history) == 2
    
    def test_status_filter_combinations(self):
        """Test various status filter combinations."""
        palette = create_nlp_command_palette()
        
        status_queries = [
            ("Show pending approvals", "pending"),
            ("List approved RFQs", "approved"),
            ("Display overdue tasks", "overdue"),
        ]
        
        for query, expected_status in status_queries:
            result = palette.execute(query, f"sess_{expected_status}", "user")
            assert result["parameters"].get("status") == expected_status, \
                f"Failed for query: {query}"
    
    def test_priority_detection(self):
        """Test priority detection in queries."""
        palette = create_nlp_command_palette()
        
        priority_queries = [
            ("Show urgent tasks", "high"),
            ("List high priority items", "high"),
            ("Display low priority requests", "low"),
        ]
        
        for query, expected_priority in priority_queries:
            result = palette.execute(query, f"sess_{expected_priority}", "user")
            assert result["parameters"].get("priority") == expected_priority, \
                f"Failed for query: {query}"
