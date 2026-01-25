"""
AI Email Drafting Service.

Provides AI-powered email generation for various business contexts:
- Missing Information Requests
- Quote Follow-ups
- Supplier Inquiries
- Meeting Confirmations
- Issue Notifications
- Status Updates

Key Features:
- Context-aware email generation
- Tone/style customization
- Multi-language support
- Template suggestions
- Grammar/clarity improvements
- Compliance checking
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4
import re
import json


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================================
# Enums
# ============================================================================

class EmailTone(str, Enum):
    """Tone options for email generation."""
    
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    APOLOGETIC = "apologetic"
    APPRECIATIVE = "appreciative"
    CONCISE = "concise"


class EmailPurpose(str, Enum):
    """Purpose categories for email generation."""

    MISSING_INFO_REQUEST = "missing_info_request"
    QUOTE_FOLLOWUP = "quote_followup"
    QUOTE_SUBMISSION = "quote_submission"
    SUPPLIER_INQUIRY = "supplier_inquiry"
    MEETING_REQUEST = "meeting_request"
    MEETING_CONFIRMATION = "meeting_confirmation"
    MEETING_RESCHEDULE = "meeting_reschedule"
    ISSUE_NOTIFICATION = "issue_notification"
    STATUS_UPDATE = "status_update"
    THANK_YOU = "thank_you"
    INTRODUCTION = "introduction"
    ESCALATION = "escalation"
    APOLOGY = "apology"
    CUSTOM = "custom"  # Default purpose for custom emails

class DraftStatus(str, Enum):
    """Status of an email draft."""
    
    GENERATING = "generating"
    READY = "ready"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SENT = "sent"
    DISCARDED = "discarded"
    FAILED = "failed"


class Language(str, Enum):
    """Supported languages."""
    
    ENGLISH = "en"
    FRENCH = "fr"
    GERMAN = "de"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    CHINESE = "zh"
    KOREAN = "ko"
    ARABIC = "ar"


class ComplianceCheckType(str, Enum):
    """Types of compliance checks."""
    
    PII_CHECK = "pii_check"
    CONFIDENTIALITY = "confidentiality"
    PROFANITY = "profanity"
    LEGAL_TERMS = "legal_terms"
    TONE_APPROPRIATE = "tone_appropriate"
    COMPLETENESS = "completeness"


class SuggestionType(str, Enum):
    """Types of improvement suggestions."""
    
    GRAMMAR = "grammar"
    CLARITY = "clarity"
    TONE = "tone"
    STRUCTURE = "structure"
    BREVITY = "brevity"
    CALL_TO_ACTION = "call_to_action"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Recipient:
    """Email recipient information."""
    
    email: str
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    relationship: Optional[str] = None  # e.g., "customer", "supplier", "colleague"
    language_preference: Language = Language.ENGLISH
    previous_interactions: int = 0
    
    def display_name(self) -> str:
        """Get display name for salutation."""
        if self.name:
            return self.name.split()[0] if " " in self.name else self.name
        return "there"


@dataclass
class EmailContext:
    """Context for email generation."""
    
    purpose: EmailPurpose = EmailPurpose.CUSTOM
    recipient: Recipient = field(default_factory=lambda: Recipient(email="", name=""))
    subject_hint: Optional[str] = None
    key_points: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    reference_number: Optional[str] = None  # RFQ number, Quote number, etc.
    deadline: Optional[datetime] = None
    tone: EmailTone = EmailTone.PROFESSIONAL
    language: Language = Language.ENGLISH
    include_signature: bool = True
    max_paragraphs: int = 4
    additional_context: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationRequest:
    """Request to generate an email draft."""
    
    id: UUID = field(default_factory=uuid4)
    context: EmailContext = field(default_factory=lambda: EmailContext())
    sender_name: str = ""
    sender_title: Optional[str] = None
    sender_email: str = ""
    company_name: str = ""
    requested_by: Optional[UUID] = None
    requested_at: datetime = field(default_factory=_utcnow)


@dataclass
class GeneratedDraft:
    """A generated email draft."""
    
    id: UUID
    request_id: UUID
    subject: str
    body_plain: str
    body_html: str
    salutation: str
    opening: str
    main_content: list[str]
    closing: str
    signature: str
    status: DraftStatus
    confidence_score: float
    alternatives: list[str] = field(default_factory=list)
    compliance_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    tokens_used: int = 0
    generation_time_ms: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    edits_made: list[str] = field(default_factory=list)


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""
    
    check_type: ComplianceCheckType
    passed: bool
    severity: str  # "info", "warning", "error"
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ImprovementSuggestion:
    """Suggestion for improving the email."""
    
    type: SuggestionType
    original_text: str
    suggested_text: str
    reason: str
    priority: str  # "low", "medium", "high"
    auto_applicable: bool = False


@dataclass
class EmailTemplate:
    """Predefined email template."""
    
    id: UUID
    name: str
    purpose: EmailPurpose
    language: Language
    subject_template: str
    body_template: str
    tone: EmailTone
    placeholders: list[str]
    is_default: bool = False
    is_active: bool = True
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class DraftHistory:
    """History of draft generation and edits."""
    
    draft_id: UUID
    action: str  # "generated", "edited", "regenerated", "approved", "sent"
    actor_id: Optional[UUID]
    timestamp: datetime
    details: Optional[str] = None
    before_text: Optional[str] = None
    after_text: Optional[str] = None


@dataclass
class AIProviderConfig:
    """Configuration for AI provider (Local only)."""
    
    provider: str = "local"
    model: str = "local-llm"
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9


# ============================================================================
# Template Library
# ============================================================================

SUBJECT_TEMPLATES: dict[EmailPurpose, dict[Language, str]] = {
    EmailPurpose.MISSING_INFO_REQUEST: {
        Language.ENGLISH: "Additional Information Needed - {reference}",
        Language.FRENCH: "Informations Supplémentaires Requises - {reference}",
        Language.GERMAN: "Zusätzliche Informationen Benötigt - {reference}",
        Language.SPANISH: "Se Necesita Información Adicional - {reference}",
    },
    EmailPurpose.QUOTE_FOLLOWUP: {
        Language.ENGLISH: "Follow-up: Quote {reference}",
        Language.FRENCH: "Suivi : Devis {reference}",
        Language.GERMAN: "Nachverfolgung: Angebot {reference}",
        Language.SPANISH: "Seguimiento: Cotización {reference}",
    },
    EmailPurpose.QUOTE_SUBMISSION: {
        Language.ENGLISH: "Quote Submission - {reference}",
        Language.FRENCH: "Soumission de Devis - {reference}",
        Language.GERMAN: "Angebotsabgabe - {reference}",
        Language.SPANISH: "Presentación de Cotización - {reference}",
    },
    EmailPurpose.MEETING_REQUEST: {
        Language.ENGLISH: "Meeting Request: {subject}",
        Language.FRENCH: "Demande de Réunion : {subject}",
        Language.GERMAN: "Terminanfrage: {subject}",
        Language.SPANISH: "Solicitud de Reunión: {subject}",
    },
    EmailPurpose.ISSUE_NOTIFICATION: {
        Language.ENGLISH: "Important Notice: {subject}",
        Language.FRENCH: "Avis Important : {subject}",
        Language.GERMAN: "Wichtiger Hinweis: {subject}",
        Language.SPANISH: "Aviso Importante: {subject}",
    },
    EmailPurpose.STATUS_UPDATE: {
        Language.ENGLISH: "Status Update - {reference}",
        Language.FRENCH: "Mise à Jour du Statut - {reference}",
        Language.GERMAN: "Statusaktualisierung - {reference}",
        Language.SPANISH: "Actualización de Estado - {reference}",
    },
}

SALUTATION_TEMPLATES: dict[EmailTone, dict[Language, str]] = {
    EmailTone.FORMAL: {
        Language.ENGLISH: "Dear {title} {name},",
        Language.FRENCH: "Cher/Chère {title} {name},",
        Language.GERMAN: "Sehr geehrte/r {title} {name},",
        Language.SPANISH: "Estimado/a {title} {name},",
    },
    EmailTone.PROFESSIONAL: {
        Language.ENGLISH: "Dear {name},",
        Language.FRENCH: "Bonjour {name},",
        Language.GERMAN: "Hallo {name},",
        Language.SPANISH: "Hola {name},",
    },
    EmailTone.FRIENDLY: {
        Language.ENGLISH: "Hi {name},",
        Language.FRENCH: "Salut {name},",
        Language.GERMAN: "Hallo {name},",
        Language.SPANISH: "¡Hola {name}!",
    },
}

CLOSING_TEMPLATES: dict[EmailTone, dict[Language, list[str]]] = {
    EmailTone.FORMAL: {
        Language.ENGLISH: [
            "Yours sincerely,",
            "Kind regards,",
            "Best regards,",
            "Respectfully,",
        ],
        Language.FRENCH: [
            "Cordialement,",
            "Veuillez agréer mes salutations distinguées,",
            "Bien à vous,",
        ],
    },
    EmailTone.PROFESSIONAL: {
        Language.ENGLISH: [
            "Best regards,",
            "Kind regards,",
            "Thanks,",
            "Regards,",
        ],
        Language.FRENCH: [
            "Cordialement,",
            "Bien à vous,",
            "Merci,",
        ],
    },
    EmailTone.FRIENDLY: {
        Language.ENGLISH: [
            "Thanks!",
            "Cheers,",
            "Talk soon,",
            "Best,",
        ],
        Language.FRENCH: [
            "À bientôt,",
            "Merci !",
            "Bises,",
        ],
    },
    EmailTone.URGENT: {
        Language.ENGLISH: [
            "Looking forward to your prompt response,",
            "Please respond at your earliest convenience,",
            "Time-sensitive - please respond soon,",
        ],
    },
}


# ============================================================================
# AI Email Drafting Service
# ============================================================================

class AIEmailDraftingService:
    """Service for AI-powered email draft generation."""
    
    def __init__(
        self,
        provider_config: Optional[AIProviderConfig] = None,
        default_language: Language = Language.ENGLISH,
        default_tone: EmailTone = EmailTone.PROFESSIONAL,
    ):
        self.provider_config = provider_config
        self.default_language = default_language
        self.default_tone = default_tone
        self._templates: dict[UUID, EmailTemplate] = {}
        self._drafts: dict[UUID, GeneratedDraft] = {}
        self._history: list[DraftHistory] = []
    
    # ========================================================================
    # Draft Generation
    # ========================================================================
    
    def generate_draft(
        self,
        request: GenerationRequest,
    ) -> GeneratedDraft:
        """
        Generate an email draft based on the request context.
        
        Args:
            request: The generation request with context
            
        Returns:
            Generated email draft
        """
        import time
        start_time = time.time()
        
        context = request.context
        
        # Generate subject
        subject = self._generate_subject(context)
        
        # Generate salutation
        salutation = self._generate_salutation(context)
        
        # Generate opening
        opening = self._generate_opening(context)
        
        # Generate main content paragraphs
        main_content = self._generate_main_content(context)
        
        # Generate closing
        closing = self._generate_closing(context)
        
        # Generate signature
        signature = self._generate_signature(
            request.sender_name,
            request.sender_title,
            request.sender_email,
            request.company_name,
            context.include_signature,
        )
        
        # Assemble plain text body
        body_parts: list[str | list[str]] = [
            salutation,
            "",
            opening,
        ]
        body_parts.extend(["", para] for para in main_content)
        body_parts.extend([
            "",
            closing,
            "",
            signature,
        ])
        
        # Flatten the list
        flat_parts = []
        for part in body_parts:
            if isinstance(part, list):
                flat_parts.extend(part)
            else:
                flat_parts.append(part)
        
        body_plain = "\n".join(flat_parts)
        
        # Generate HTML version
        body_html = self._convert_to_html(body_plain)
        
        # Run compliance checks
        compliance_issues = self._run_compliance_checks(body_plain, context)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(body_plain, context)
        
        # Generate alternatives
        alternatives = self._generate_alternatives(subject, context)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            context,
            len(compliance_issues),
            len(suggestions),
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        draft = GeneratedDraft(
            id=uuid4(),
            request_id=request.id,
            subject=subject,
            body_plain=body_plain,
            body_html=body_html,
            salutation=salutation,
            opening=opening,
            main_content=main_content,
            closing=closing,
            signature=signature,
            status=DraftStatus.READY,
            confidence_score=confidence_score,
            alternatives=alternatives,
            compliance_issues=compliance_issues,
            suggestions=suggestions,
            generation_time_ms=generation_time_ms,
        )
        
        self._drafts[draft.id] = draft
        self._record_history(draft.id, "generated", request.requested_by)
        
        return draft
    
    def regenerate_draft(
        self,
        draft_id: UUID,
        user_id: Optional[UUID] = None,
        feedback: Optional[str] = None,
    ) -> GeneratedDraft:
        """
        Regenerate a draft with optional feedback.
        
        Args:
            draft_id: ID of the draft to regenerate
            user_id: User requesting regeneration
            feedback: Optional feedback to improve generation
            
        Returns:
            New draft
        """
        original = self._drafts.get(draft_id)
        if not original:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Mark original as discarded
        original.status = DraftStatus.DISCARDED
        
        # Record history
        self._record_history(
            draft_id,
            "regenerated",
            user_id,
            details=feedback,
        )
        
        # For now, we just generate a new draft with the same request
        # In production, feedback would be incorporated
        new_draft = GeneratedDraft(
            id=uuid4(),
            request_id=original.request_id,
            subject=original.subject,
            body_plain=original.body_plain,
            body_html=original.body_html,
            salutation=original.salutation,
            opening=original.opening,
            main_content=original.main_content,
            closing=original.closing,
            signature=original.signature,
            status=DraftStatus.READY,
            confidence_score=original.confidence_score,
            alternatives=original.alternatives,
            compliance_issues=original.compliance_issues,
            suggestions=original.suggestions,
            generation_time_ms=original.generation_time_ms,
        )
        
        self._drafts[new_draft.id] = new_draft
        return new_draft
    
    # ========================================================================
    # Draft Management
    # ========================================================================
    
    def get_draft(self, draft_id: UUID) -> Optional[GeneratedDraft]:
        """Get a draft by ID."""
        return self._drafts.get(draft_id)
    
    def update_draft(
        self,
        draft_id: UUID,
        updates: dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> GeneratedDraft:
        """
        Update a draft with user edits.
        
        Args:
            draft_id: Draft to update
            updates: Fields to update
            user_id: User making the update
            
        Returns:
            Updated draft
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        before_text = draft.body_plain
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        
        # Regenerate plain/html if content changed
        if "main_content" in updates or "opening" in updates or "closing" in updates:
            body_parts = [draft.salutation, "", draft.opening]
            for para in draft.main_content:
                body_parts.extend(["", para])
            body_parts.extend(["", draft.closing, "", draft.signature])
            draft.body_plain = "\n".join(body_parts)
            draft.body_html = self._convert_to_html(draft.body_plain)
        
        draft.edits_made.append(json.dumps(updates))
        
        self._record_history(
            draft_id,
            "edited",
            user_id,
            before_text=before_text,
            after_text=draft.body_plain,
        )
        
        return draft
    
    def approve_draft(
        self,
        draft_id: UUID,
        user_id: UUID,
    ) -> GeneratedDraft:
        """
        Approve a draft for sending.
        
        Args:
            draft_id: Draft to approve
            user_id: User approving
            
        Returns:
            Approved draft
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        draft.status = DraftStatus.APPROVED
        draft.reviewed_at = datetime.now(timezone.utc)
        draft.reviewed_by = user_id
        
        self._record_history(draft_id, "approved", user_id)
        
        return draft
    
    def mark_sent(
        self,
        draft_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> GeneratedDraft:
        """
        Mark a draft as sent.
        
        Args:
            draft_id: Draft that was sent
            user_id: User who sent it
            
        Returns:
            Updated draft
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        draft.status = DraftStatus.SENT
        
        self._record_history(draft_id, "sent", user_id)
        
        return draft
    
    def discard_draft(
        self,
        draft_id: UUID,
        user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> None:
        """
        Discard a draft.
        
        Args:
            draft_id: Draft to discard
            user_id: User discarding
            reason: Optional reason
        """
        draft = self._drafts.get(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        draft.status = DraftStatus.DISCARDED
        
        self._record_history(draft_id, "discarded", user_id, details=reason)
    
    # ========================================================================
    # Content Generation (Private Methods)
    # ========================================================================
    
    def _generate_subject(self, context: EmailContext) -> str:
        """Generate email subject line."""
        purpose = context.purpose
        language = context.language
        
        # Use template if available
        if purpose in SUBJECT_TEMPLATES:
            templates = SUBJECT_TEMPLATES[purpose]
            template = templates.get(language, templates.get(Language.ENGLISH, ""))
            
            # Fill in placeholders
            subject = template.format(
                reference=context.reference_number or "N/A",
                subject=context.subject_hint or "",
            )
            return subject
        
        # Fallback to hint or generic
        if context.subject_hint:
            return context.subject_hint
        
        return f"Regarding {context.purpose.value.replace('_', ' ').title()}"
    
    def _generate_salutation(self, context: EmailContext) -> str:
        """Generate email salutation."""
        tone = context.tone
        language = context.language
        recipient = context.recipient
        
        if tone in SALUTATION_TEMPLATES:
            templates = SALUTATION_TEMPLATES[tone]
            template = templates.get(language, templates.get(Language.ENGLISH, "Hi {name},"))
            
            return template.format(
                name=recipient.display_name(),
                title=recipient.title or "",
            ).strip()
        
        return f"Dear {recipient.display_name()},"
    
    def _generate_opening(self, context: EmailContext) -> str:
        """Generate email opening paragraph."""
        purpose = context.purpose
        recipient = context.recipient
        
        openings = {
            EmailPurpose.MISSING_INFO_REQUEST: [
                f"I hope this email finds you well. I'm reaching out regarding {context.reference_number or 'your recent inquiry'} to request some additional information.",
                f"Thank you for your interest in working with us. To proceed with {context.reference_number or 'your request'}, we need a few more details.",
            ],
            EmailPurpose.QUOTE_FOLLOWUP: [
                f"I wanted to follow up on the quote we sent ({context.reference_number}) and see if you had any questions.",
                f"I'm reaching out to check in on the status of quote {context.reference_number} and offer any assistance you might need.",
            ],
            EmailPurpose.QUOTE_SUBMISSION: [
                f"Thank you for the opportunity to quote on {context.reference_number}. Please find our proposal attached.",
                f"We're pleased to submit our quote for {context.reference_number or 'your project'}. Below you'll find a summary of our offering.",
            ],
            EmailPurpose.MEETING_REQUEST: [
                f"I'd like to schedule a meeting to discuss {context.subject_hint or 'an important matter'}.",
                f"I'm reaching out to request some time on your calendar to discuss {context.subject_hint or 'our collaboration'}.",
            ],
            EmailPurpose.ISSUE_NOTIFICATION: [
                f"I'm writing to inform you about an important matter that requires your attention.",
                f"This email is to notify you of a situation that has arisen regarding {context.reference_number or 'our engagement'}.",
            ],
            EmailPurpose.STATUS_UPDATE: [
                f"I wanted to provide you with an update on the status of {context.reference_number or 'your project'}.",
                f"Here's the latest update regarding {context.reference_number or 'your request'}:",
            ],
            EmailPurpose.THANK_YOU: [
                f"I wanted to take a moment to thank you for {context.subject_hint or 'your support'}.",
                f"Thank you so much for {context.subject_hint or 'everything'}. We truly appreciate it.",
            ],
        }
        
        purpose_openings = openings.get(purpose, [
            "I hope this email finds you well.",
            "Thank you for reaching out.",
        ])
        
        return purpose_openings[0]
    
    def _generate_main_content(self, context: EmailContext) -> list[str]:
        """Generate main content paragraphs."""
        paragraphs = []
        
        # If key points provided, build paragraphs from them
        if context.key_points:
            if len(context.key_points) <= 3:
                # Short list - combine into paragraph
                intro = "Here are the key details:"
                points = "\n• " + "\n• ".join(context.key_points)
                paragraphs.append(intro + points)
            else:
                # Longer list - break into sections
                paragraphs.append("Please see the following details:")
                for i, point in enumerate(context.key_points, 1):
                    paragraphs.append(f"{i}. {point}")
        else:
            # Generate based on purpose
            paragraphs.extend(self._generate_purpose_content(context))
        
        # Add deadline mention if applicable
        if context.deadline:
            deadline_str = context.deadline.strftime("%B %d, %Y")
            paragraphs.append(
                f"We would appreciate a response by {deadline_str} to ensure we can meet our timelines."
            )
        
        # Mention attachments
        if context.attachments:
            if len(context.attachments) == 1:
                paragraphs.append(f"I've attached {context.attachments[0]} for your reference.")
            else:
                attachment_list = ", ".join(context.attachments[:-1]) + f" and {context.attachments[-1]}"
                paragraphs.append(f"I've attached {attachment_list} for your reference.")
        
        # Limit to max paragraphs
        return paragraphs[:context.max_paragraphs]
    
    def _generate_purpose_content(self, context: EmailContext) -> list[str]:
        """Generate content specific to email purpose."""
        purpose = context.purpose
        
        content_map = {
            EmailPurpose.MISSING_INFO_REQUEST: [
                "To complete our assessment and provide you with an accurate quote, we need the following information:",
                "• [Specific information needed]",
                "Having these details will help us ensure we meet your requirements precisely.",
            ],
            EmailPurpose.QUOTE_FOLLOWUP: [
                "We're committed to providing you with the best possible solution and would be happy to:",
                "• Answer any questions about our proposal",
                "• Discuss pricing options or customizations",
                "• Arrange a call to walk through the details",
            ],
            EmailPurpose.SUPPLIER_INQUIRY: [
                "We're exploring potential partnerships and would like to learn more about your capabilities.",
                "Specifically, we're interested in understanding your lead times, minimum order quantities, and quality certifications.",
            ],
            EmailPurpose.MEETING_REQUEST: [
                "I believe a brief meeting would be valuable to:",
                "• Align on key objectives",
                "• Address any questions or concerns",
                "• Discuss next steps",
                "Would any of the following times work for you? [Please suggest 2-3 time slots]",
            ],
        }
        
        return content_map.get(purpose, [
            "Please let me know if you have any questions or need additional information.",
        ])
    
    def _generate_closing(self, context: EmailContext) -> str:
        """Generate email closing."""
        tone = context.tone
        language = context.language
        
        if tone in CLOSING_TEMPLATES:
            templates = CLOSING_TEMPLATES[tone]
            closings = templates.get(language, templates.get(Language.ENGLISH, ["Best regards,"]))
            return closings[0]
        
        return "Best regards,"
    
    def _generate_signature(
        self,
        sender_name: str,
        sender_title: Optional[str],
        sender_email: str,
        company_name: str,
        include_signature: bool,
    ) -> str:
        """Generate email signature block."""
        if not include_signature:
            return sender_name
        
        lines = [sender_name]
        if sender_title:
            lines.append(sender_title)
        if company_name:
            lines.append(company_name)
        if sender_email:
            lines.append(sender_email)
        
        return "\n".join(lines)
    
    def _convert_to_html(self, plain_text: str) -> str:
        """Convert plain text to HTML email format."""
        # Escape HTML entities
        html = plain_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Convert line breaks to paragraphs
        paragraphs = html.split("\n\n")
        html_parts = []
        
        for para in paragraphs:
            if para.strip():
                # Handle bullet points
                if para.startswith("• ") or para.startswith("- "):
                    items = para.split("\n")
                    list_items = "".join(f"<li>{item.lstrip('•- ')}</li>" for item in items if item.strip())
                    html_parts.append(f"<ul>{list_items}</ul>")
                else:
                    # Regular paragraph
                    formatted = para.replace("\n", "<br>")
                    html_parts.append(f"<p>{formatted}</p>")
        
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333; }}
p {{ margin: 0 0 16px 0; }}
ul {{ margin: 0 0 16px 0; padding-left: 24px; }}
li {{ margin-bottom: 8px; }}
</style>
</head>
<body>
{"".join(html_parts)}
</body>
</html>"""
    
    # ========================================================================
    # Compliance and Suggestions
    # ========================================================================
    
    def _run_compliance_checks(
        self,
        text: str,
        context: EmailContext,
    ) -> list[str]:
        """Run compliance checks on the draft."""
        issues = []
        
        # Check for PII patterns
        pii_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', "Possible SSN detected"),
            (r'\b\d{16}\b', "Possible credit card number detected"),
            (r'\b(?:password|pwd|secret)\s*[:=]\s*\S+', "Password in plain text detected"),
        ]
        
        for pattern, message in pii_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(message)
        
        # Check for profanity (simplified)
        profane_words = {"damn", "hell", "crap"}
        words = set(text.lower().split())
        if words & profane_words:
            issues.append("Informal language detected - consider more professional alternatives")
        
        # Check tone appropriateness
        if context.tone == EmailTone.FORMAL:
            informal_indicators = ["hey", "gonna", "wanna", "asap", "fyi"]
            for indicator in informal_indicators:
                if indicator in text.lower():
                    issues.append(f"Informal term '{indicator}' may not be appropriate for formal tone")
        
        # Check for completeness
        if "[" in text and "]" in text:
            issues.append("Placeholder brackets found - ensure all fields are filled")
        
        return issues
    
    def _generate_suggestions(
        self,
        text: str,
        context: EmailContext,
    ) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # Check length
        word_count = len(text.split())
        if word_count > 300:
            suggestions.append("Consider shortening the email for better readability")
        
        # Check for call to action
        cta_indicators = ["please", "would you", "could you", "let me know", "respond", "reply"]
        has_cta = any(indicator in text.lower() for indicator in cta_indicators)
        if not has_cta:
            suggestions.append("Consider adding a clear call-to-action")
        
        # Check for passive voice (simplified)
        passive_patterns = ["was sent", "has been", "will be sent", "is being"]
        for pattern in passive_patterns:
            if pattern in text.lower():
                suggestions.append("Consider using active voice for more impact")
                break
        
        # Check for deadline if urgent
        if context.tone == EmailTone.URGENT and not context.deadline:
            suggestions.append("For urgent emails, consider specifying a deadline")
        
        return suggestions
    
    def _generate_alternatives(
        self,
        subject: str,
        context: EmailContext,
    ) -> list[str]:
        """Generate alternative subject lines."""
        alternatives = []
        
        # Generate variations based on purpose
        purpose = context.purpose
        ref = context.reference_number or ""
        
        if purpose == EmailPurpose.MISSING_INFO_REQUEST:
            alternatives = [
                f"Action Required: Additional Info for {ref}",
                f"Quick Question About {ref}",
                f"Following Up: {ref} Documentation Needed",
            ]
        elif purpose == EmailPurpose.QUOTE_FOLLOWUP:
            alternatives = [
                f"Checking In: {ref}",
                f"Any Questions About Quote {ref}?",
                f"Your {ref} Quote - How Can We Help?",
            ]
        elif purpose == EmailPurpose.MEETING_REQUEST:
            alternatives = [
                f"Can We Schedule 15 Minutes?",
                f"Quick Chat Request: {context.subject_hint or 'Discussion'}",
                f"Time to Connect?",
            ]
        
        return alternatives
    
    def _calculate_confidence(
        self,
        context: EmailContext,
        issue_count: int,
        suggestion_count: int,
    ) -> float:
        """Calculate confidence score for the draft."""
        base_score = 0.85
        
        # Reduce for issues
        base_score -= issue_count * 0.1
        
        # Slight reduction for many suggestions
        base_score -= min(suggestion_count * 0.03, 0.15)
        
        # Boost for complete context
        if context.key_points:
            base_score += 0.05
        if context.reference_number:
            base_score += 0.03
        if context.recipient.name:
            base_score += 0.02
        
        return max(0.0, min(1.0, base_score))
    
    # ========================================================================
    # Template Management
    # ========================================================================
    
    def add_template(self, template: EmailTemplate) -> EmailTemplate:
        """Add a new email template."""
        self._templates[template.id] = template
        return template
    
    def get_template(self, template_id: UUID) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        purpose: Optional[EmailPurpose] = None,
        language: Optional[Language] = None,
        active_only: bool = True,
    ) -> list[EmailTemplate]:
        """List templates with optional filtering."""
        templates = list(self._templates.values())
        
        if purpose:
            templates = [t for t in templates if t.purpose == purpose]
        if language:
            templates = [t for t in templates if t.language == language]
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return sorted(templates, key=lambda t: (-t.usage_count, t.name))
    
    def get_default_template(
        self,
        purpose: EmailPurpose,
        language: Language = Language.ENGLISH,
    ) -> Optional[EmailTemplate]:
        """Get the default template for a purpose and language."""
        for template in self._templates.values():
            if template.purpose == purpose and template.language == language and template.is_default:
                return template
        return None
    
    # ========================================================================
    # History
    # ========================================================================
    
    def _record_history(
        self,
        draft_id: UUID,
        action: str,
        actor_id: Optional[UUID],
        details: Optional[str] = None,
        before_text: Optional[str] = None,
        after_text: Optional[str] = None,
    ) -> None:
        """Record an action in draft history."""
        self._history.append(DraftHistory(
            draft_id=draft_id,
            action=action,
            actor_id=actor_id,
            timestamp=datetime.now(timezone.utc),
            details=details,
            before_text=before_text,
            after_text=after_text,
        ))
    
    def get_history(self, draft_id: UUID) -> list[DraftHistory]:
        """Get history for a draft."""
        return [h for h in self._history if h.draft_id == draft_id]
    
    # ========================================================================
    # Convenience Methods
    # ========================================================================
    
    def generate_missing_info_email(
        self,
        recipient: Recipient,
        missing_fields: list[str],
        rfq_number: str,
        sender_name: str,
        sender_email: str,
        company_name: str,
        deadline: Optional[datetime] = None,
    ) -> GeneratedDraft:
        """
        Convenience method for generating missing info request emails.
        
        Args:
            recipient: Email recipient
            missing_fields: List of missing field descriptions
            rfq_number: RFQ reference number
            sender_name: Sender's name
            sender_email: Sender's email
            company_name: Company name
            deadline: Optional response deadline
            
        Returns:
            Generated email draft
        """
        context = EmailContext(
            purpose=EmailPurpose.MISSING_INFO_REQUEST,
            recipient=recipient,
            key_points=missing_fields,
            reference_number=rfq_number,
            deadline=deadline,
            tone=EmailTone.PROFESSIONAL,
        )
        
        request = GenerationRequest(
            context=context,
            sender_name=sender_name,
            sender_email=sender_email,
            company_name=company_name,
        )
        
        return self.generate_draft(request)
    
    def generate_quote_followup(
        self,
        recipient: Recipient,
        quote_number: str,
        quote_date: datetime,
        key_points: Optional[list[str]] = None,
        sender_name: str = "",
        sender_email: str = "",
        company_name: str = "",
    ) -> GeneratedDraft:
        """
        Convenience method for generating quote follow-up emails.
        
        Args:
            recipient: Email recipient
            quote_number: Quote reference number
            quote_date: Date the quote was sent
            key_points: Optional key points to mention
            sender_name: Sender's name
            sender_email: Sender's email
            company_name: Company name
            
        Returns:
            Generated email draft
        """
        days_ago = (datetime.now(timezone.utc) - quote_date).days
        
        auto_points = [
            f"We sent quote {quote_number} {days_ago} days ago",
            "We're happy to answer any questions",
            "Let us know if you'd like to discuss pricing or terms",
        ]
        
        context = EmailContext(
            purpose=EmailPurpose.QUOTE_FOLLOWUP,
            recipient=recipient,
            key_points=key_points or auto_points,
            reference_number=quote_number,
            tone=EmailTone.PROFESSIONAL,
        )
        
        request = GenerationRequest(
            context=context,
            sender_name=sender_name,
            sender_email=sender_email,
            company_name=company_name,
        )
        
        return self.generate_draft(request)
    
    def generate_meeting_request(
        self,
        recipient: Recipient,
        meeting_topic: str,
        proposed_times: list[str],
        duration_minutes: int = 30,
        sender_name: str = "",
        sender_email: str = "",
        company_name: str = "",
    ) -> GeneratedDraft:
        """
        Convenience method for generating meeting request emails.
        
        Args:
            recipient: Email recipient
            meeting_topic: Topic/purpose of the meeting
            proposed_times: List of proposed meeting times
            duration_minutes: Expected meeting duration
            sender_name: Sender's name
            sender_email: Sender's email
            company_name: Company name
            
        Returns:
            Generated email draft
        """
        key_points = [
            f"Topic: {meeting_topic}",
            f"Duration: {duration_minutes} minutes",
            "Proposed times:",
        ] + [f"  • {time}" for time in proposed_times]
        
        context = EmailContext(
            purpose=EmailPurpose.MEETING_REQUEST,
            recipient=recipient,
            subject_hint=meeting_topic,
            key_points=key_points,
            tone=EmailTone.PROFESSIONAL,
        )
        
        request = GenerationRequest(
            context=context,
            sender_name=sender_name,
            sender_email=sender_email,
            company_name=company_name,
        )
        
        return self.generate_draft(request)
    
    def analyze_and_improve(
        self,
        draft_text: str,
        context: Optional[EmailContext] = None,
    ) -> tuple[list[ComplianceCheck], list[ImprovementSuggestion]]:
        """
        Analyze an existing email draft and provide improvements.
        
        Args:
            draft_text: The email text to analyze
            context: Optional context for better analysis
            
        Returns:
            Tuple of compliance checks and improvement suggestions
        """
        # Run compliance checks
        compliance_checks = []
        
        # PII check
        has_ssn = bool(re.search(r'\b\d{3}-\d{2}-\d{4}\b', draft_text))
        compliance_checks.append(ComplianceCheck(
            check_type=ComplianceCheckType.PII_CHECK,
            passed=not has_ssn,
            severity="error" if has_ssn else "info",
            message="SSN detected in text" if has_ssn else "No PII detected",
        ))
        
        # Profanity check
        profane_words = {"damn", "hell", "crap"}
        words = set(draft_text.lower().split())
        found_profanity = words & profane_words
        compliance_checks.append(ComplianceCheck(
            check_type=ComplianceCheckType.PROFANITY,
            passed=not found_profanity,
            severity="warning" if found_profanity else "info",
            message=f"Inappropriate language found: {found_profanity}" if found_profanity else "Language is appropriate",
        ))
        
        # Completeness check
        has_placeholders = "[" in draft_text and "]" in draft_text
        compliance_checks.append(ComplianceCheck(
            check_type=ComplianceCheckType.COMPLETENESS,
            passed=not has_placeholders,
            severity="error" if has_placeholders else "info",
            message="Unfilled placeholders detected" if has_placeholders else "Email appears complete",
        ))
        
        # Generate improvement suggestions
        suggestions = []
        
        # Brevity suggestion
        word_count = len(draft_text.split())
        if word_count > 250:
            suggestions.append(ImprovementSuggestion(
                type=SuggestionType.BREVITY,
                original_text="",
                suggested_text="",
                reason=f"Email has {word_count} words. Consider trimming to under 200 for better engagement.",
                priority="medium",
            ))
        
        # Check for greeting
        greetings = ["hi", "hello", "dear", "good morning", "good afternoon"]
        has_greeting = any(draft_text.lower().startswith(g) for g in greetings)
        if not has_greeting:
            suggestions.append(ImprovementSuggestion(
                type=SuggestionType.STRUCTURE,
                original_text=draft_text[:50] if len(draft_text) > 50 else draft_text,
                suggested_text="Dear [Name],",
                reason="Consider adding a greeting to make the email more personable",
                priority="low",
            ))
        
        # Call to action check
        cta_words = ["please", "let me know", "respond", "reply", "advise", "confirm"]
        has_cta = any(cta in draft_text.lower() for cta in cta_words)
        if not has_cta:
            suggestions.append(ImprovementSuggestion(
                type=SuggestionType.CALL_TO_ACTION,
                original_text="",
                suggested_text="Please let me know if you have any questions.",
                reason="Adding a clear call-to-action improves response rates",
                priority="high",
            ))
        
        return compliance_checks, suggestions
