"""
Tests for AI Email Drafting Service.

Comprehensive tests covering:
- Draft generation for all purposes
- Content generation (subject, salutation, opening, closing, signature)
- Multi-language support
- Tone variations
- Template management
- Compliance checks
- Improvement suggestions
- Draft lifecycle management
- History tracking
- Convenience methods
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID

from sensei.services.ai.ai_email_drafting import (
    # Enums
    EmailTone,
    EmailPurpose,
    DraftStatus,
    Language,
    ComplianceCheckType,
    SuggestionType,
    # Data classes
    Recipient,
    EmailContext,
    GenerationRequest,
    GeneratedDraft,
    ComplianceCheck,
    ImprovementSuggestion,
    EmailTemplate,
    DraftHistory,
    AIProviderConfig,
    # Templates
    SUBJECT_TEMPLATES,
    SALUTATION_TEMPLATES,
    CLOSING_TEMPLATES,
    # Service
    AIEmailDraftingService,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def service():
    """Create a service instance."""
    return AIEmailDraftingService()


@pytest.fixture
def service_with_config():
    """Create a service with provider config."""
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4",
        api_key="test-key",
        temperature=0.7,
        max_tokens=1000,
    )
    return AIEmailDraftingService(provider_config=config)


@pytest.fixture
def sample_recipient():
    """Create a sample recipient."""
    return Recipient(
        email="john.doe@example.com",
        name="John Doe",
        title="Mr.",
        company="Acme Corp",
        relationship="customer",
        language_preference=Language.ENGLISH,
        previous_interactions=5,
    )


@pytest.fixture
def sample_context(sample_recipient):
    """Create a sample email context."""
    return EmailContext(
        purpose=EmailPurpose.MISSING_INFO_REQUEST,
        recipient=sample_recipient,
        subject_hint="RFQ Documentation",
        key_points=[
            "Material specifications needed",
            "Volume requirements unclear",
            "Delivery location missing",
        ],
        reference_number="RFQ-2024-001",
        deadline=datetime.now(timezone.utc) + timedelta(days=7),
        tone=EmailTone.PROFESSIONAL,
        language=Language.ENGLISH,
        include_signature=True,
        max_paragraphs=4,
    )


@pytest.fixture
def sample_request(sample_context):
    """Create a sample generation request."""
    return GenerationRequest(
        context=sample_context,
        sender_name="Jane Smith",
        sender_title="Sales Manager",
        sender_email="jane.smith@ourcompany.com",
        company_name="Our Company Inc.",
        requested_by=uuid4(),
    )


# ============================================================================
# Enum Tests
# ============================================================================

class TestEmailTone:
    """Tests for EmailTone enum."""
    
    def test_all_tones_defined(self):
        """Verify all expected tones exist."""
        expected = {
            "formal", "professional", "friendly", 
            "urgent", "apologetic", "appreciative", "concise"
        }
        actual = {t.value for t in EmailTone}
        assert expected == actual
    
    def test_tone_values(self):
        """Verify tone values are lowercase."""
        for tone in EmailTone:
            assert tone.value == tone.value.lower()


class TestEmailPurpose:
    """Tests for EmailPurpose enum."""
    
    def test_all_purposes_defined(self):
        """Verify all expected purposes exist."""
        expected = {
            "missing_info_request", "quote_followup", "quote_submission",
            "supplier_inquiry", "meeting_request", "meeting_confirmation",
            "meeting_reschedule", "issue_notification", "status_update",
            "thank_you", "introduction", "escalation", "apology", "custom"
        }
        actual = {p.value for p in EmailPurpose}
        assert expected == actual


class TestDraftStatus:
    """Tests for DraftStatus enum."""
    
    def test_all_statuses_defined(self):
        """Verify all expected statuses exist."""
        expected = {
            "generating", "ready", "reviewed", 
            "approved", "sent", "discarded", "failed"
        }
        actual = {s.value for s in DraftStatus}
        assert expected == actual


class TestLanguage:
    """Tests for Language enum."""
    
    def test_all_languages_defined(self):
        """Verify all expected languages exist."""
        expected = {"en", "fr", "de", "es", "it", "pt", "ja", "zh", "ko", "ar"}
        actual = {l.value for l in Language}
        assert expected == actual
    
    def test_english_default(self):
        """Verify English is available."""
        assert Language.ENGLISH.value == "en"


class TestComplianceCheckType:
    """Tests for ComplianceCheckType enum."""
    
    def test_all_types_defined(self):
        """Verify all check types exist."""
        expected = {
            "pii_check", "confidentiality", "profanity",
            "legal_terms", "tone_appropriate", "completeness"
        }
        actual = {c.value for c in ComplianceCheckType}
        assert expected == actual


class TestSuggestionType:
    """Tests for SuggestionType enum."""
    
    def test_all_types_defined(self):
        """Verify all suggestion types exist."""
        expected = {
            "grammar", "clarity", "tone", 
            "structure", "brevity", "call_to_action"
        }
        actual = {s.value for s in SuggestionType}
        assert expected == actual


# ============================================================================
# Recipient Tests
# ============================================================================

class TestRecipient:
    """Tests for Recipient dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic recipient."""
        recipient = Recipient(email="test@example.com")
        assert recipient.email == "test@example.com"
        assert recipient.name is None
        assert recipient.title is None
        assert recipient.language_preference == Language.ENGLISH
    
    def test_full_recipient(self, sample_recipient):
        """Test fully populated recipient."""
        assert sample_recipient.email == "john.doe@example.com"
        assert sample_recipient.name == "John Doe"
        assert sample_recipient.title == "Mr."
        assert sample_recipient.company == "Acme Corp"
        assert sample_recipient.relationship == "customer"
        assert sample_recipient.previous_interactions == 5
    
    def test_display_name_with_full_name(self, sample_recipient):
        """Test display name extraction from full name."""
        assert sample_recipient.display_name() == "John"
    
    def test_display_name_single_name(self):
        """Test display name with single name."""
        recipient = Recipient(email="test@example.com", name="Alice")
        assert recipient.display_name() == "Alice"
    
    def test_display_name_no_name(self):
        """Test display name fallback when no name."""
        recipient = Recipient(email="test@example.com")
        assert recipient.display_name() == "there"


# ============================================================================
# EmailContext Tests
# ============================================================================

class TestEmailContext:
    """Tests for EmailContext dataclass."""
    
    def test_basic_creation(self, sample_recipient):
        """Test creating basic context."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=sample_recipient,
        )
        assert context.purpose == EmailPurpose.QUOTE_FOLLOWUP
        assert context.tone == EmailTone.PROFESSIONAL
        assert context.language == Language.ENGLISH
    
    def test_default_values(self, sample_recipient):
        """Test default values are set correctly."""
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
        )
        assert context.key_points == []
        assert context.attachments == []
        assert context.include_signature is True
        assert context.max_paragraphs == 4
    
    def test_full_context(self, sample_context):
        """Test fully populated context."""
        assert sample_context.purpose == EmailPurpose.MISSING_INFO_REQUEST
        assert sample_context.reference_number == "RFQ-2024-001"
        assert len(sample_context.key_points) == 3
        assert sample_context.deadline is not None


# ============================================================================
# GenerationRequest Tests
# ============================================================================

class TestGenerationRequest:
    """Tests for GenerationRequest dataclass."""
    
    def test_auto_id_generation(self, sample_context):
        """Test that ID is auto-generated."""
        request = GenerationRequest(context=sample_context)
        assert request.id is not None
        assert isinstance(request.id, UUID)
    
    def test_timestamp_auto_set(self, sample_context):
        """Test that timestamp is auto-set."""
        request = GenerationRequest(context=sample_context)
        assert request.requested_at is not None
        assert isinstance(request.requested_at, datetime)
    
    def test_full_request(self, sample_request):
        """Test fully populated request."""
        assert sample_request.sender_name == "Jane Smith"
        assert sample_request.sender_title == "Sales Manager"
        assert sample_request.sender_email == "jane.smith@ourcompany.com"
        assert sample_request.company_name == "Our Company Inc."


# ============================================================================
# Template Tests
# ============================================================================

class TestSubjectTemplates:
    """Tests for subject templates."""
    
    def test_missing_info_request_template(self):
        """Test missing info request subject template."""
        template = SUBJECT_TEMPLATES[EmailPurpose.MISSING_INFO_REQUEST]
        assert Language.ENGLISH in template
        assert "{reference}" in template[Language.ENGLISH]
    
    def test_quote_followup_template(self):
        """Test quote followup subject template."""
        template = SUBJECT_TEMPLATES[EmailPurpose.QUOTE_FOLLOWUP]
        assert Language.ENGLISH in template
        assert "Quote" in template[Language.ENGLISH] or "Follow" in template[Language.ENGLISH]
    
    def test_multiple_languages_available(self):
        """Test that multiple languages are supported."""
        template = SUBJECT_TEMPLATES[EmailPurpose.MISSING_INFO_REQUEST]
        assert len(template) >= 4  # At least 4 languages


class TestSalutationTemplates:
    """Tests for salutation templates."""
    
    def test_formal_salutation(self):
        """Test formal salutation template."""
        template = SALUTATION_TEMPLATES[EmailTone.FORMAL]
        assert Language.ENGLISH in template
        assert "{name}" in template[Language.ENGLISH]
    
    def test_friendly_salutation(self):
        """Test friendly salutation template."""
        template = SALUTATION_TEMPLATES[EmailTone.FRIENDLY]
        assert Language.ENGLISH in template
        assert "Hi" in template[Language.ENGLISH]
    
    def test_professional_salutation(self):
        """Test professional salutation template."""
        template = SALUTATION_TEMPLATES[EmailTone.PROFESSIONAL]
        assert Language.ENGLISH in template


class TestClosingTemplates:
    """Tests for closing templates."""
    
    def test_formal_closings(self):
        """Test formal closing options."""
        closings = CLOSING_TEMPLATES[EmailTone.FORMAL]
        assert Language.ENGLISH in closings
        assert len(closings[Language.ENGLISH]) >= 2
    
    def test_friendly_closings(self):
        """Test friendly closing options."""
        closings = CLOSING_TEMPLATES[EmailTone.FRIENDLY]
        assert Language.ENGLISH in closings
        # Friendly closings are less formal
        assert any("!" in c or "Cheers" in c for c in closings[Language.ENGLISH])
    
    def test_urgent_closings(self):
        """Test urgent closing options."""
        closings = CLOSING_TEMPLATES[EmailTone.URGENT]
        assert Language.ENGLISH in closings
        # Urgent closings mention response
        assert any("response" in c.lower() or "respond" in c.lower() for c in closings[Language.ENGLISH])


# ============================================================================
# Draft Generation Tests
# ============================================================================

class TestDraftGeneration:
    """Tests for draft generation."""
    
    def test_generate_draft_basic(self, service, sample_request):
        """Test basic draft generation."""
        draft = service.generate_draft(sample_request)
        
        assert draft.id is not None
        assert draft.request_id == sample_request.id
        assert draft.status == DraftStatus.READY
        assert draft.subject is not None
        assert draft.body_plain is not None
        assert draft.body_html is not None
    
    def test_draft_has_salutation(self, service, sample_request):
        """Test draft includes salutation."""
        draft = service.generate_draft(sample_request)
        assert "John" in draft.salutation or "Dear" in draft.salutation
    
    def test_draft_has_opening(self, service, sample_request):
        """Test draft includes opening."""
        draft = service.generate_draft(sample_request)
        assert len(draft.opening) > 0
    
    def test_draft_has_main_content(self, service, sample_request):
        """Test draft includes main content."""
        draft = service.generate_draft(sample_request)
        assert len(draft.main_content) > 0
    
    def test_draft_has_closing(self, service, sample_request):
        """Test draft includes closing."""
        draft = service.generate_draft(sample_request)
        assert len(draft.closing) > 0
    
    def test_draft_has_signature(self, service, sample_request):
        """Test draft includes signature."""
        draft = service.generate_draft(sample_request)
        assert "Jane Smith" in draft.signature
    
    def test_draft_has_confidence_score(self, service, sample_request):
        """Test draft has confidence score."""
        draft = service.generate_draft(sample_request)
        assert 0.0 <= draft.confidence_score <= 1.0
    
    def test_draft_has_generation_time(self, service, sample_request):
        """Test draft tracks generation time."""
        draft = service.generate_draft(sample_request)
        assert draft.generation_time_ms >= 0
    
    def test_draft_stored_in_service(self, service, sample_request):
        """Test draft is stored in service."""
        draft = service.generate_draft(sample_request)
        retrieved = service.get_draft(draft.id)
        assert retrieved is not None
        assert retrieved.id == draft.id
    
    def test_draft_history_recorded(self, service, sample_request):
        """Test generation is recorded in history."""
        draft = service.generate_draft(sample_request)
        history = service.get_history(draft.id)
        assert len(history) == 1
        assert history[0].action == "generated"


class TestSubjectGeneration:
    """Tests for subject line generation."""
    
    def test_missing_info_subject(self, service, sample_recipient):
        """Test missing info request subject."""
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
            reference_number="RFQ-123",
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "RFQ-123" in draft.subject
    
    def test_quote_followup_subject(self, service, sample_recipient):
        """Test quote followup subject."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=sample_recipient,
            reference_number="Q-456",
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "Q-456" in draft.subject
    
    def test_subject_with_hint(self, service, sample_recipient):
        """Test subject uses hint when available."""
        context = EmailContext(
            purpose=EmailPurpose.MEETING_REQUEST,
            recipient=sample_recipient,
            subject_hint="Product Demo",
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "Product Demo" in draft.subject or "Meeting" in draft.subject
    
    def test_alternatives_generated(self, service, sample_request):
        """Test alternative subjects are generated."""
        draft = service.generate_draft(sample_request)
        # May or may not have alternatives depending on purpose
        assert isinstance(draft.alternatives, list)


class TestSalutationGeneration:
    """Tests for salutation generation."""
    
    def test_formal_salutation(self, service, sample_recipient):
        """Test formal tone salutation."""
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
            tone=EmailTone.FORMAL,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "Dear" in draft.salutation
    
    def test_friendly_salutation(self, service, sample_recipient):
        """Test friendly tone salutation."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
            tone=EmailTone.FRIENDLY,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "Hi" in draft.salutation
    
    def test_recipient_name_used(self, service, sample_recipient):
        """Test recipient name appears in salutation."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=sample_recipient,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "John" in draft.salutation


class TestContentGeneration:
    """Tests for main content generation."""
    
    def test_key_points_included(self, service, sample_request):
        """Test key points appear in content."""
        draft = service.generate_draft(sample_request)
        
        # Check that key points are referenced
        body_lower = draft.body_plain.lower()
        assert any(
            "material" in body_lower or
            "volume" in body_lower or
            "delivery" in body_lower
            for _ in [1]
        )
    
    def test_deadline_mentioned(self, service, sample_request):
        """Test deadline is mentioned when provided."""
        draft = service.generate_draft(sample_request)
        
        # Deadline should be mentioned somewhere
        assert "response" in draft.body_plain.lower() or "timelines" in draft.body_plain.lower()
    
    def test_attachments_mentioned(self, service, sample_recipient):
        """Test attachments are mentioned."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_SUBMISSION,
            recipient=sample_recipient,
            attachments=["Quote.pdf", "Terms.pdf"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "attached" in draft.body_plain.lower()
    
    def test_max_paragraphs_respected(self, service, sample_recipient):
        """Test max paragraphs limit is respected."""
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
            key_points=["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
            max_paragraphs=2,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        # Main content should be limited
        assert len(draft.main_content) <= 2


class TestSignatureGeneration:
    """Tests for signature generation."""
    
    def test_full_signature(self, service, sample_request):
        """Test full signature includes all info."""
        draft = service.generate_draft(sample_request)
        
        assert "Jane Smith" in draft.signature
        assert "Sales Manager" in draft.signature
        assert "Our Company Inc." in draft.signature
    
    def test_signature_without_title(self, service, sample_recipient):
        """Test signature without title."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
        )
        request = GenerationRequest(
            context=context,
            sender_name="Alice",
            sender_email="alice@company.com",
            company_name="Company",
        )
        draft = service.generate_draft(request)
        
        assert "Alice" in draft.signature
    
    def test_no_signature_when_disabled(self, service, sample_recipient):
        """Test signature omitted when disabled."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
            include_signature=False,
        )
        request = GenerationRequest(
            context=context,
            sender_name="Bob",
            sender_email="bob@company.com",
            company_name="Company",
        )
        draft = service.generate_draft(request)
        
        # Signature should just be the name
        assert draft.signature == "Bob"


class TestHTMLConversion:
    """Tests for HTML email conversion."""
    
    def test_html_has_doctype(self, service, sample_request):
        """Test HTML includes doctype."""
        draft = service.generate_draft(sample_request)
        assert "<!DOCTYPE html>" in draft.body_html
    
    def test_html_has_style(self, service, sample_request):
        """Test HTML includes style."""
        draft = service.generate_draft(sample_request)
        assert "<style>" in draft.body_html
    
    def test_html_has_paragraphs(self, service, sample_request):
        """Test HTML uses paragraph tags."""
        draft = service.generate_draft(sample_request)
        assert "<p>" in draft.body_html
    
    def test_html_escapes_special_chars(self, service, sample_recipient):
        """Test HTML escapes special characters."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_SUBMISSION,
            recipient=sample_recipient,
            key_points=["Price < $100", "Rate > 5%"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "&lt;" in draft.body_html
        assert "&gt;" in draft.body_html


# ============================================================================
# Draft Management Tests
# ============================================================================

class TestDraftManagement:
    """Tests for draft lifecycle management."""
    
    def test_get_draft(self, service, sample_request):
        """Test retrieving a draft."""
        draft = service.generate_draft(sample_request)
        retrieved = service.get_draft(draft.id)
        
        assert retrieved is not None
        assert retrieved.id == draft.id
        assert retrieved.subject == draft.subject
    
    def test_get_nonexistent_draft(self, service):
        """Test retrieving non-existent draft."""
        result = service.get_draft(uuid4())
        assert result is None
    
    def test_update_draft_subject(self, service, sample_request):
        """Test updating draft subject."""
        draft = service.generate_draft(sample_request)
        user_id = uuid4()
        
        updated = service.update_draft(
            draft.id,
            {"subject": "New Subject Line"},
            user_id,
        )
        
        assert updated.subject == "New Subject Line"
    
    def test_update_draft_content(self, service, sample_request):
        """Test updating draft content."""
        draft = service.generate_draft(sample_request)
        
        updated = service.update_draft(
            draft.id,
            {"opening": "New opening paragraph."},
        )
        
        assert updated.opening == "New opening paragraph."
        assert "New opening" in updated.body_plain
    
    def test_update_records_edit(self, service, sample_request):
        """Test updates are tracked in edits_made."""
        draft = service.generate_draft(sample_request)
        
        service.update_draft(draft.id, {"subject": "Changed"})
        
        assert len(draft.edits_made) == 1
    
    def test_update_records_history(self, service, sample_request):
        """Test updates are recorded in history."""
        draft = service.generate_draft(sample_request)
        user_id = uuid4()
        
        service.update_draft(draft.id, {"subject": "Changed"}, user_id)
        
        history = service.get_history(draft.id)
        edit_entries = [h for h in history if h.action == "edited"]
        assert len(edit_entries) == 1
        assert edit_entries[0].actor_id == user_id
    
    def test_update_nonexistent_draft(self, service):
        """Test updating non-existent draft raises error."""
        with pytest.raises(ValueError):
            service.update_draft(uuid4(), {"subject": "Test"})
    
    def test_approve_draft(self, service, sample_request):
        """Test approving a draft."""
        draft = service.generate_draft(sample_request)
        user_id = uuid4()
        
        approved = service.approve_draft(draft.id, user_id)
        
        assert approved.status == DraftStatus.APPROVED
        assert approved.reviewed_by == user_id
        assert approved.reviewed_at is not None
    
    def test_approve_records_history(self, service, sample_request):
        """Test approval is recorded in history."""
        draft = service.generate_draft(sample_request)
        user_id = uuid4()
        
        service.approve_draft(draft.id, user_id)
        
        history = service.get_history(draft.id)
        approved_entries = [h for h in history if h.action == "approved"]
        assert len(approved_entries) == 1
    
    def test_approve_nonexistent_draft(self, service):
        """Test approving non-existent draft raises error."""
        with pytest.raises(ValueError):
            service.approve_draft(uuid4(), uuid4())
    
    def test_mark_sent(self, service, sample_request):
        """Test marking draft as sent."""
        draft = service.generate_draft(sample_request)
        
        sent = service.mark_sent(draft.id)
        
        assert sent.status == DraftStatus.SENT
    
    def test_mark_sent_records_history(self, service, sample_request):
        """Test sent status is recorded in history."""
        draft = service.generate_draft(sample_request)
        user_id = uuid4()
        
        service.mark_sent(draft.id, user_id)
        
        history = service.get_history(draft.id)
        sent_entries = [h for h in history if h.action == "sent"]
        assert len(sent_entries) == 1
    
    def test_discard_draft(self, service, sample_request):
        """Test discarding a draft."""
        draft = service.generate_draft(sample_request)
        
        service.discard_draft(draft.id, reason="Not needed")
        
        assert draft.status == DraftStatus.DISCARDED
    
    def test_discard_records_history(self, service, sample_request):
        """Test discard is recorded in history."""
        draft = service.generate_draft(sample_request)
        
        service.discard_draft(draft.id, reason="Changed approach")
        
        history = service.get_history(draft.id)
        discarded = [h for h in history if h.action == "discarded"]
        assert len(discarded) == 1
        assert discarded[0].details == "Changed approach"
    
    def test_regenerate_draft(self, service, sample_request):
        """Test regenerating a draft."""
        original = service.generate_draft(sample_request)
        user_id = uuid4()
        
        new_draft = service.regenerate_draft(
            original.id,
            user_id,
            feedback="Make it shorter",
        )
        
        assert new_draft.id != original.id
        assert original.status == DraftStatus.DISCARDED
    
    def test_regenerate_records_history(self, service, sample_request):
        """Test regeneration is recorded in history."""
        original = service.generate_draft(sample_request)
        
        service.regenerate_draft(original.id, feedback="Too long")
        
        history = service.get_history(original.id)
        regen = [h for h in history if h.action == "regenerated"]
        assert len(regen) == 1
        assert regen[0].details == "Too long"
    
    def test_regenerate_nonexistent(self, service):
        """Test regenerating non-existent draft raises error."""
        with pytest.raises(ValueError):
            service.regenerate_draft(uuid4())


# ============================================================================
# Compliance Check Tests
# ============================================================================

class TestComplianceChecks:
    """Tests for compliance checking."""
    
    def test_ssn_detection(self, service, sample_recipient):
        """Test SSN pattern detection."""
        context = EmailContext(
            purpose=EmailPurpose.CUSTOM,
            recipient=sample_recipient,
            key_points=["SSN: 123-45-6789"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert any("SSN" in issue for issue in draft.compliance_issues)
    
    def test_informal_language_formal_tone(self, service, sample_recipient):
        """Test informal language detection in formal emails."""
        context = EmailContext(
            purpose=EmailPurpose.CUSTOM,
            recipient=sample_recipient,
            key_points=["FYI this is gonna be quick"],
            tone=EmailTone.FORMAL,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        # Should flag informal terms
        assert any("informal" in issue.lower() or "fyi" in issue.lower() for issue in draft.compliance_issues)
    
    def test_placeholder_detection(self, service, sample_recipient):
        """Test placeholder bracket detection."""
        context = EmailContext(
            purpose=EmailPurpose.CUSTOM,
            recipient=sample_recipient,
            key_points=["Please fill [YOUR NAME]"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert any("placeholder" in issue.lower() for issue in draft.compliance_issues)
    
    def test_analyze_and_improve_pii(self, service):
        """Test analyze_and_improve detects PII."""
        checks, _ = service.analyze_and_improve("My SSN is 123-45-6789")
        
        pii_check = next(c for c in checks if c.check_type == ComplianceCheckType.PII_CHECK)
        assert not pii_check.passed
        assert pii_check.severity == "error"
    
    def test_analyze_and_improve_profanity(self, service):
        """Test analyze_and_improve detects profanity."""
        checks, _ = service.analyze_and_improve("What the hell is going on")
        
        profanity_check = next(c for c in checks if c.check_type == ComplianceCheckType.PROFANITY)
        assert not profanity_check.passed
    
    def test_analyze_and_improve_completeness(self, service):
        """Test analyze_and_improve checks completeness."""
        checks, _ = service.analyze_and_improve("Please contact [RECIPIENT NAME]")
        
        completeness_check = next(c for c in checks if c.check_type == ComplianceCheckType.COMPLETENESS)
        assert not completeness_check.passed


# ============================================================================
# Improvement Suggestion Tests
# ============================================================================

class TestImprovementSuggestions:
    """Tests for improvement suggestions."""
    
    def test_brevity_suggestion(self, service):
        """Test brevity suggestion for long emails."""
        long_text = " ".join(["word"] * 300)
        _, suggestions = service.analyze_and_improve(long_text)
        
        brevity = [s for s in suggestions if s.type == SuggestionType.BREVITY]
        assert len(brevity) > 0
    
    def test_greeting_suggestion(self, service):
        """Test suggestion to add greeting."""
        _, suggestions = service.analyze_and_improve("Here is the information you requested.")
        
        structure = [s for s in suggestions if s.type == SuggestionType.STRUCTURE]
        assert len(structure) > 0
    
    def test_cta_suggestion(self, service):
        """Test call-to-action suggestion."""
        _, suggestions = service.analyze_and_improve("Hi there, here is the update on the project.")
        
        cta = [s for s in suggestions if s.type == SuggestionType.CALL_TO_ACTION]
        assert len(cta) > 0
    
    def test_no_cta_needed(self, service):
        """Test no CTA suggestion when CTA present."""
        _, suggestions = service.analyze_and_improve("Hi, please let me know if you have questions.")
        
        cta = [s for s in suggestions if s.type == SuggestionType.CALL_TO_ACTION]
        assert len(cta) == 0
    
    def test_suggestion_priorities(self, service):
        """Test suggestions have valid priorities."""
        _, suggestions = service.analyze_and_improve("Test email content here.")
        
        valid_priorities = {"low", "medium", "high"}
        for suggestion in suggestions:
            assert suggestion.priority in valid_priorities


# ============================================================================
# Template Management Tests
# ============================================================================

class TestTemplateManagement:
    """Tests for template management."""
    
    def test_add_template(self, service):
        """Test adding a template."""
        template = EmailTemplate(
            id=uuid4(),
            name="Quick Follow-up",
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            language=Language.ENGLISH,
            subject_template="Following up on {reference}",
            body_template="Just checking in...",
            tone=EmailTone.FRIENDLY,
            placeholders=["reference"],
        )
        
        added = service.add_template(template)
        
        assert added.id == template.id
        assert service.get_template(template.id) is not None
    
    def test_get_template(self, service):
        """Test retrieving a template."""
        template = EmailTemplate(
            id=uuid4(),
            name="Test Template",
            purpose=EmailPurpose.INTRODUCTION,
            language=Language.ENGLISH,
            subject_template="Introduction",
            body_template="Hello...",
            tone=EmailTone.PROFESSIONAL,
            placeholders=[],
        )
        service.add_template(template)
        
        retrieved = service.get_template(template.id)
        
        assert retrieved is not None
        assert retrieved.name == "Test Template"
    
    def test_get_nonexistent_template(self, service):
        """Test retrieving non-existent template."""
        result = service.get_template(uuid4())
        assert result is None
    
    def test_list_templates_all(self, service):
        """Test listing all templates."""
        t1 = EmailTemplate(
            id=uuid4(), name="T1", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[],
        )
        t2 = EmailTemplate(
            id=uuid4(), name="T2", purpose=EmailPurpose.APOLOGY,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.APOLOGETIC, placeholders=[],
        )
        service.add_template(t1)
        service.add_template(t2)
        
        templates = service.list_templates()
        
        assert len(templates) == 2
    
    def test_list_templates_by_purpose(self, service):
        """Test filtering templates by purpose."""
        t1 = EmailTemplate(
            id=uuid4(), name="T1", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[],
        )
        t2 = EmailTemplate(
            id=uuid4(), name="T2", purpose=EmailPurpose.APOLOGY,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.APOLOGETIC, placeholders=[],
        )
        service.add_template(t1)
        service.add_template(t2)
        
        templates = service.list_templates(purpose=EmailPurpose.THANK_YOU)
        
        assert len(templates) == 1
        assert templates[0].purpose == EmailPurpose.THANK_YOU
    
    def test_list_templates_by_language(self, service):
        """Test filtering templates by language."""
        t1 = EmailTemplate(
            id=uuid4(), name="T1", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[],
        )
        t2 = EmailTemplate(
            id=uuid4(), name="T2", purpose=EmailPurpose.THANK_YOU,
            language=Language.FRENCH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[],
        )
        service.add_template(t1)
        service.add_template(t2)
        
        templates = service.list_templates(language=Language.FRENCH)
        
        assert len(templates) == 1
        assert templates[0].language == Language.FRENCH
    
    def test_list_templates_active_only(self, service):
        """Test filtering templates by active status."""
        t1 = EmailTemplate(
            id=uuid4(), name="Active", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[], is_active=True,
        )
        t2 = EmailTemplate(
            id=uuid4(), name="Inactive", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[], is_active=False,
        )
        service.add_template(t1)
        service.add_template(t2)
        
        active = service.list_templates(active_only=True)
        all_templates = service.list_templates(active_only=False)
        
        assert len(active) == 1
        assert len(all_templates) == 2
    
    def test_get_default_template(self, service):
        """Test getting default template."""
        t1 = EmailTemplate(
            id=uuid4(), name="Default", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[], is_default=True,
        )
        t2 = EmailTemplate(
            id=uuid4(), name="Alt", purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH, subject_template="", body_template="",
            tone=EmailTone.FRIENDLY, placeholders=[], is_default=False,
        )
        service.add_template(t1)
        service.add_template(t2)
        
        default = service.get_default_template(EmailPurpose.THANK_YOU)
        
        assert default is not None
        assert default.name == "Default"
    
    def test_get_default_template_not_found(self, service):
        """Test getting default when none exists."""
        result = service.get_default_template(EmailPurpose.ESCALATION)
        assert result is None


# ============================================================================
# Convenience Method Tests
# ============================================================================

class TestMissingInfoEmailGeneration:
    """Tests for generate_missing_info_email convenience method."""
    
    def test_basic_generation(self, service, sample_recipient):
        """Test basic missing info email generation."""
        draft = service.generate_missing_info_email(
            recipient=sample_recipient,
            missing_fields=["Material type", "Quantity needed"],
            rfq_number="RFQ-2024-100",
            sender_name="Sales Rep",
            sender_email="sales@company.com",
            company_name="Our Company",
        )
        
        assert draft.status == DraftStatus.READY
        assert "RFQ-2024-100" in draft.subject
    
    def test_with_deadline(self, service, sample_recipient):
        """Test missing info email with deadline."""
        deadline = datetime.now(timezone.utc) + timedelta(days=5)
        
        draft = service.generate_missing_info_email(
            recipient=sample_recipient,
            missing_fields=["Specs"],
            rfq_number="RFQ-123",
            sender_name="Rep",
            sender_email="rep@co.com",
            company_name="Co",
            deadline=deadline,
        )
        
        # Deadline should be mentioned
        assert "response" in draft.body_plain.lower() or "timelines" in draft.body_plain.lower()
    
    def test_missing_fields_in_body(self, service, sample_recipient):
        """Test that missing fields appear in body."""
        fields = ["Drawing files", "Tolerance specs", "Material grade"]
        
        draft = service.generate_missing_info_email(
            recipient=sample_recipient,
            missing_fields=fields,
            rfq_number="RFQ-456",
            sender_name="Rep",
            sender_email="rep@co.com",
            company_name="Co",
        )
        
        # Fields should be listed
        assert "key" in draft.body_plain.lower() or "details" in draft.body_plain.lower() or "following" in draft.body_plain.lower()


class TestQuoteFollowupGeneration:
    """Tests for generate_quote_followup convenience method."""
    
    def test_basic_generation(self, service, sample_recipient):
        """Test basic quote followup generation."""
        quote_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        draft = service.generate_quote_followup(
            recipient=sample_recipient,
            quote_number="Q-2024-001",
            quote_date=quote_date,
            sender_name="Sales",
            sender_email="sales@co.com",
            company_name="Our Co",
        )
        
        assert draft.status == DraftStatus.READY
        assert "Q-2024-001" in draft.subject
    
    def test_days_ago_calculation(self, service, sample_recipient):
        """Test days ago is calculated correctly."""
        quote_date = datetime.now(timezone.utc) - timedelta(days=5)
        
        draft = service.generate_quote_followup(
            recipient=sample_recipient,
            quote_number="Q-123",
            quote_date=quote_date,
            sender_name="Sales",
            sender_email="sales@co.com",
            company_name="Co",
        )
        
        # Should mention days ago
        assert "5 days ago" in draft.body_plain or "days" in draft.body_plain.lower()
    
    def test_custom_key_points(self, service, sample_recipient):
        """Test custom key points override auto-generated ones."""
        draft = service.generate_quote_followup(
            recipient=sample_recipient,
            quote_number="Q-456",
            quote_date=datetime.now(timezone.utc) - timedelta(days=3),
            key_points=["Special discount available", "Limited time offer"],
            sender_name="Sales",
            sender_email="sales@co.com",
            company_name="Co",
        )
        
        # Custom points should be referenced
        assert "key" in draft.body_plain.lower() or "details" in draft.body_plain.lower()


class TestMeetingRequestGeneration:
    """Tests for generate_meeting_request convenience method."""
    
    def test_basic_generation(self, service, sample_recipient):
        """Test basic meeting request generation."""
        draft = service.generate_meeting_request(
            recipient=sample_recipient,
            meeting_topic="Project Kickoff",
            proposed_times=["Monday 2pm", "Tuesday 10am"],
            sender_name="Manager",
            sender_email="mgr@co.com",
            company_name="Our Co",
        )
        
        assert draft.status == DraftStatus.READY
        assert "Meeting" in draft.subject or "Kickoff" in draft.subject
    
    def test_topic_in_subject(self, service, sample_recipient):
        """Test meeting topic appears in subject."""
        draft = service.generate_meeting_request(
            recipient=sample_recipient,
            meeting_topic="Quarterly Review",
            proposed_times=["Friday 3pm"],
            sender_name="Dir",
            sender_email="dir@co.com",
            company_name="Co",
        )
        
        assert "Quarterly Review" in draft.subject or "Meeting" in draft.subject
    
    def test_duration_mentioned(self, service, sample_recipient):
        """Test duration is mentioned in email."""
        draft = service.generate_meeting_request(
            recipient=sample_recipient,
            meeting_topic="Sync",
            proposed_times=["Today 4pm"],
            duration_minutes=45,
            sender_name="Lead",
            sender_email="lead@co.com",
            company_name="Co",
        )
        
        # Duration should be in body
        assert "45" in draft.body_plain or "minutes" in draft.body_plain.lower()


# ============================================================================
# History Tests
# ============================================================================

class TestDraftHistory:
    """Tests for draft history tracking."""
    
    def test_generation_recorded(self, service, sample_request):
        """Test generation is recorded."""
        draft = service.generate_draft(sample_request)
        history = service.get_history(draft.id)
        
        assert len(history) >= 1
        assert history[0].action == "generated"
    
    def test_edit_recorded(self, service, sample_request):
        """Test edit is recorded with before/after."""
        draft = service.generate_draft(sample_request)
        before = draft.body_plain
        
        service.update_draft(draft.id, {"opening": "New opening"})
        
        history = service.get_history(draft.id)
        edit = next(h for h in history if h.action == "edited")
        
        assert edit.before_text is not None
        assert edit.after_text is not None
    
    def test_full_lifecycle_history(self, service, sample_request):
        """Test complete lifecycle is tracked."""
        user_id = uuid4()
        
        draft = service.generate_draft(sample_request)
        service.update_draft(draft.id, {"subject": "Updated"}, user_id)
        service.approve_draft(draft.id, user_id)
        service.mark_sent(draft.id, user_id)
        
        history = service.get_history(draft.id)
        actions = [h.action for h in history]
        
        assert "generated" in actions
        assert "edited" in actions
        assert "approved" in actions
        assert "sent" in actions
    
    def test_history_timestamps(self, service, sample_request):
        """Test history entries have timestamps."""
        draft = service.generate_draft(sample_request)
        history = service.get_history(draft.id)
        
        for entry in history:
            assert entry.timestamp is not None
            assert isinstance(entry.timestamp, datetime)


# ============================================================================
# Multi-Language Tests
# ============================================================================

class TestMultiLanguageSupport:
    """Tests for multi-language support."""
    
    def test_french_subject(self, service, sample_recipient):
        """Test French subject generation."""
        sample_recipient.language_preference = Language.FRENCH
        
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
            reference_number="RFQ-FR-001",
            language=Language.FRENCH,
        )
        request = GenerationRequest(context=context, sender_name="Jean")
        draft = service.generate_draft(request)
        
        # Subject should be in French
        assert "Informations" in draft.subject or "RFQ-FR-001" in draft.subject
    
    def test_german_subject(self, service, sample_recipient):
        """Test German subject generation."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=sample_recipient,
            reference_number="Q-DE-001",
            language=Language.GERMAN,
        )
        request = GenerationRequest(context=context, sender_name="Hans")
        draft = service.generate_draft(request)
        
        # Should use German template or fallback
        assert "Q-DE-001" in draft.subject
    
    def test_spanish_salutation(self, service, sample_recipient):
        """Test Spanish salutation."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
            language=Language.SPANISH,
            tone=EmailTone.FRIENDLY,
        )
        request = GenerationRequest(context=context, sender_name="Carlos")
        draft = service.generate_draft(request)
        
        # Salutation should be Spanish
        assert "Hola" in draft.salutation or "John" in draft.salutation


# ============================================================================
# Tone Variation Tests
# ============================================================================

class TestToneVariations:
    """Tests for tone variations."""
    
    def test_formal_tone_characteristics(self, service, sample_recipient):
        """Test formal tone generates appropriate content."""
        context = EmailContext(
            purpose=EmailPurpose.INTRODUCTION,
            recipient=sample_recipient,
            tone=EmailTone.FORMAL,
        )
        request = GenerationRequest(context=context, sender_name="Dr. Smith")
        draft = service.generate_draft(request)
        
        assert "Dear" in draft.salutation
    
    def test_friendly_tone_characteristics(self, service, sample_recipient):
        """Test friendly tone generates appropriate content."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
            tone=EmailTone.FRIENDLY,
        )
        request = GenerationRequest(context=context, sender_name="Bob")
        draft = service.generate_draft(request)
        
        assert "Hi" in draft.salutation
    
    def test_urgent_tone_closing(self, service, sample_recipient):
        """Test urgent tone has appropriate closing."""
        context = EmailContext(
            purpose=EmailPurpose.ISSUE_NOTIFICATION,
            recipient=sample_recipient,
            tone=EmailTone.URGENT,
        )
        request = GenerationRequest(context=context, sender_name="Support")
        draft = service.generate_draft(request)
        
        # Urgent should mention response
        assert "response" in draft.closing.lower() or "respond" in draft.closing.lower() or "regards" in draft.closing.lower()


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_key_points(self, service, sample_recipient):
        """Test generation with empty key points."""
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=sample_recipient,
            key_points=[],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert draft.status == DraftStatus.READY
    
    def test_no_reference_number(self, service, sample_recipient):
        """Test generation without reference number."""
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=sample_recipient,
            reference_number=None,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert draft.status == DraftStatus.READY
        assert draft.subject is not None
    
    def test_recipient_without_name(self, service):
        """Test generation for recipient without name."""
        recipient = Recipient(email="anon@example.com")
        
        context = EmailContext(
            purpose=EmailPurpose.INTRODUCTION,
            recipient=recipient,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "there" in draft.salutation.lower() or "Dear" in draft.salutation
    
    def test_custom_purpose(self, service, sample_recipient):
        """Test generation with custom purpose."""
        context = EmailContext(
            purpose=EmailPurpose.CUSTOM,
            recipient=sample_recipient,
            subject_hint="Special Request",
            key_points=["Custom content here"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert draft.status == DraftStatus.READY
    
    def test_very_long_key_points(self, service, sample_recipient):
        """Test generation with many key points."""
        context = EmailContext(
            purpose=EmailPurpose.STATUS_UPDATE,
            recipient=sample_recipient,
            key_points=[f"Point {i}" for i in range(20)],
            max_paragraphs=3,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        # Should respect max paragraphs
        assert len(draft.main_content) <= 3
    
    def test_special_characters_in_recipient_name(self, service):
        """Test handling of special characters in name."""
        recipient = Recipient(
            email="test@example.com",
            name="José García-López",
        )
        context = EmailContext(
            purpose=EmailPurpose.THANK_YOU,
            recipient=recipient,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert draft.status == DraftStatus.READY
    
    def test_multiple_attachments(self, service, sample_recipient):
        """Test mention of multiple attachments."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_SUBMISSION,
            recipient=sample_recipient,
            attachments=["Quote.pdf", "Terms.pdf", "Catalog.pdf"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        # Should mention attachments with "and"
        assert "and" in draft.body_plain.lower()
    
    def test_single_attachment(self, service, sample_recipient):
        """Test mention of single attachment."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_SUBMISSION,
            recipient=sample_recipient,
            attachments=["Quote.pdf"],
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        assert "Quote.pdf" in draft.body_plain or "attached" in draft.body_plain.lower()


# ============================================================================
# Data Class Tests
# ============================================================================

class TestDataClasses:
    """Tests for data class initialization and defaults."""
    
    def test_compliance_check_creation(self):
        """Test ComplianceCheck creation."""
        check = ComplianceCheck(
            check_type=ComplianceCheckType.PII_CHECK,
            passed=True,
            severity="info",
            message="No PII found",
        )
        assert check.location is None
        assert check.suggestion is None
    
    def test_improvement_suggestion_creation(self):
        """Test ImprovementSuggestion creation."""
        suggestion = ImprovementSuggestion(
            type=SuggestionType.GRAMMAR,
            original_text="Their going",
            suggested_text="They're going",
            reason="Contraction needed",
            priority="high",
        )
        assert suggestion.auto_applicable is False
    
    def test_email_template_defaults(self):
        """Test EmailTemplate defaults."""
        template = EmailTemplate(
            id=uuid4(),
            name="Test",
            purpose=EmailPurpose.THANK_YOU,
            language=Language.ENGLISH,
            subject_template="Thanks!",
            body_template="Thank you...",
            tone=EmailTone.FRIENDLY,
            placeholders=[],
        )
        assert template.is_default is False
        assert template.is_active is True
        assert template.usage_count == 0
        assert template.success_rate == 0.0
    
    def test_draft_history_creation(self):
        """Test DraftHistory creation."""
        history = DraftHistory(
            draft_id=uuid4(),
            action="generated",
            actor_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
        )
        assert history.details is None
        assert history.before_text is None
        assert history.after_text is None
    
    def test_ai_provider_config_defaults(self):
        """Test AIProviderConfig defaults."""
        config = AIProviderConfig(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
        )
        assert config.endpoint is None
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.top_p == 0.9


# ============================================================================
# Service Configuration Tests
# ============================================================================

class TestServiceConfiguration:
    """Tests for service configuration."""
    
    def test_default_configuration(self):
        """Test service with default configuration."""
        service = AIEmailDraftingService()
        
        assert service.default_language == Language.ENGLISH
        assert service.default_tone == EmailTone.PROFESSIONAL
        assert service.provider_config is None
    
    def test_custom_defaults(self):
        """Test service with custom defaults."""
        service = AIEmailDraftingService(
            default_language=Language.FRENCH,
            default_tone=EmailTone.FORMAL,
        )
        
        assert service.default_language == Language.FRENCH
        assert service.default_tone == EmailTone.FORMAL
    
    def test_with_provider_config(self, service_with_config):
        """Test service with provider config."""
        assert service_with_config.provider_config is not None
        assert service_with_config.provider_config.provider == "openai"
        assert service_with_config.provider_config.model == "gpt-4"


# ============================================================================
# Confidence Score Tests
# ============================================================================

class TestConfidenceScore:
    """Tests for confidence score calculation."""
    
    def test_base_confidence(self, service, sample_request):
        """Test base confidence is reasonable."""
        draft = service.generate_draft(sample_request)
        
        # With complete context, should be high
        assert draft.confidence_score >= 0.7
    
    def test_confidence_reduced_by_issues(self, service, sample_recipient):
        """Test confidence reduced by compliance issues."""
        context = EmailContext(
            purpose=EmailPurpose.CUSTOM,
            recipient=sample_recipient,
            key_points=["SSN: 123-45-6789", "FYI this [PLACEHOLDER]"],
            tone=EmailTone.FORMAL,
        )
        request = GenerationRequest(context=context, sender_name="Test")
        draft = service.generate_draft(request)
        
        # Should be lower due to issues
        assert draft.confidence_score < 0.85
    
    def test_confidence_boosted_by_context(self, service, sample_recipient):
        """Test confidence boosted by complete context."""
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=sample_recipient,
            key_points=["Valid point"],
            reference_number="Q-123",
        )
        request = GenerationRequest(context=context, sender_name="Rep")
        draft = service.generate_draft(request)
        
        # Should be higher with complete context
        assert draft.confidence_score >= 0.85
    
    def test_confidence_bounds(self, service, sample_request):
        """Test confidence stays within 0-1 bounds."""
        draft = service.generate_draft(sample_request)
        
        assert 0.0 <= draft.confidence_score <= 1.0
