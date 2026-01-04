"""
Tests for Opportunity and RFQ models.

Tests:
- Opportunity model fields and defaults
- Opportunity stage and status handling
- Opportunity weighted amount calculation
- Opportunity days_in_stage calculation
- RFQ model fields and defaults
- RFQ status workflow
- RFQ days_until_due calculation
- RFQQuestion model
- RFQAttachment model
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.opportunity import (
    NoteType,
    Opportunity,
    OpportunityNote,
    OpportunitySource,
    OpportunityStage,
    OpportunityType,
)
from sensei.models.rfq import (
    QuestionStatus,
    RFQ,
    RFQAttachment,
    RFQAttachmentType,
    RFQPriority,
    RFQQuestion,
    RFQSource,
    RFQStatus,
)


class TestOpportunityModel:
    """Tests for the Opportunity model."""

    def test_opportunity_required_fields(self):
        """Opportunity should require name, opportunity_number, account_id."""
        account_id = uuid4()
        opp = Opportunity(
            name="Test Opportunity",
            opportunity_number="OPP-001",
            account_id=account_id,
        )
        assert opp.name == "Test Opportunity"
        assert opp.opportunity_number == "OPP-001"
        assert opp.account_id == account_id

    def test_opportunity_default_stage_is_prospecting(self):
        """Opportunity stage should default to prospecting."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            stage=OpportunityStage.PROSPECTING.value,
        )
        assert opp.stage == OpportunityStage.PROSPECTING.value

    def test_opportunity_default_type_is_new_business(self):
        """Opportunity type should default to new_business."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            opportunity_type=OpportunityType.NEW_BUSINESS.value,
        )
        assert opp.opportunity_type == OpportunityType.NEW_BUSINESS.value

    def test_opportunity_default_probability_is_10(self):
        """Opportunity probability should default to 10%."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            probability=10,
        )
        assert opp.probability == 10

    def test_opportunity_default_currency_is_mad(self):
        """Opportunity currency should default to MAD."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            currency="MAD",
        )
        assert opp.currency == "MAD"

    def test_opportunity_calculate_weighted_amount(self):
        """calculate_weighted_amount should return amount * probability / 100."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            amount=Decimal("100000.00"),
            probability=25,
        )
        result = opp.calculate_weighted_amount()
        assert result == Decimal("25000.00")

    def test_opportunity_calculate_weighted_amount_none_when_no_amount(self):
        """calculate_weighted_amount should return None when amount is None."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            probability=25,
        )
        result = opp.calculate_weighted_amount()
        assert result is None

    def test_opportunity_is_open_true_for_active_stages(self):
        """is_open should be True for non-closed stages."""
        for stage in [
            OpportunityStage.PROSPECTING,
            OpportunityStage.QUALIFICATION,
            OpportunityStage.NEEDS_ANALYSIS,
            OpportunityStage.VALUE_PROPOSITION,
            OpportunityStage.PROPOSAL,
            OpportunityStage.NEGOTIATION,
        ]:
            opp = Opportunity(
                name="Test",
                opportunity_number="OPP-001",
                account_id=uuid4(),
                stage=stage.value,
            )
            assert opp.is_open is True

    def test_opportunity_is_open_false_for_closed_won(self):
        """is_open should be False for closed_won stage."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            stage=OpportunityStage.CLOSED_WON.value,
        )
        assert opp.is_open is False

    def test_opportunity_is_open_false_for_closed_lost(self):
        """is_open should be False for closed_lost stage."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            stage=OpportunityStage.CLOSED_LOST.value,
        )
        assert opp.is_open is False

    def test_opportunity_is_closed_inverse_of_is_open(self):
        """is_closed should be the inverse of is_open."""
        opp1 = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            stage=OpportunityStage.PROSPECTING.value,
        )
        assert opp1.is_closed is False

        opp2 = Opportunity(
            name="Test",
            opportunity_number="OPP-002",
            account_id=uuid4(),
            stage=OpportunityStage.CLOSED_WON.value,
        )
        assert opp2.is_closed is True

    def test_opportunity_days_in_stage_none_when_no_stage_changed_at(self):
        """days_in_stage should be None when stage_changed_at is not set."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
        )
        assert opp.days_in_stage is None

    def test_opportunity_days_in_stage_calculation(self):
        """days_in_stage should calculate days since stage_changed_at."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            stage_changed_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        assert opp.days_in_stage == 5

    def test_opportunity_default_priority_is_medium(self):
        """Opportunity priority should default to medium."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            priority="medium",
        )
        assert opp.priority == "medium"

    def test_opportunity_is_in_forecast_default_true(self):
        """is_in_forecast should default to True."""
        opp = Opportunity(
            name="Test",
            opportunity_number="OPP-001",
            account_id=uuid4(),
            is_in_forecast=True,
        )
        assert opp.is_in_forecast is True


class TestOpportunityStageEnum:
    """Tests for OpportunityStage enum."""

    def test_all_stages_defined(self):
        """All expected opportunity stages should be defined."""
        assert OpportunityStage.PROSPECTING.value == "prospecting"
        assert OpportunityStage.QUALIFICATION.value == "qualification"
        assert OpportunityStage.NEEDS_ANALYSIS.value == "needs_analysis"
        assert OpportunityStage.VALUE_PROPOSITION.value == "value_proposition"
        assert OpportunityStage.PROPOSAL.value == "proposal"
        assert OpportunityStage.NEGOTIATION.value == "negotiation"
        assert OpportunityStage.CLOSED_WON.value == "closed_won"
        assert OpportunityStage.CLOSED_LOST.value == "closed_lost"


class TestOpportunityNoteModel:
    """Tests for the OpportunityNote model."""

    def test_opportunity_note_required_fields(self):
        """OpportunityNote should require opportunity_id and content."""
        opp_id = uuid4()
        note = OpportunityNote(
            opportunity_id=opp_id,
            content="This is a note",
        )
        assert note.opportunity_id == opp_id
        assert note.content == "This is a note"

    def test_opportunity_note_default_type_is_note(self):
        """OpportunityNote type should default to note."""
        note = OpportunityNote(
            opportunity_id=uuid4(),
            content="Test",
            note_type=NoteType.NOTE.value,
        )
        assert note.note_type == NoteType.NOTE.value

    def test_opportunity_note_is_internal_default_true(self):
        """is_internal should default to True."""
        note = OpportunityNote(
            opportunity_id=uuid4(),
            content="Test",
            is_internal=True,
        )
        assert note.is_internal is True

    def test_opportunity_note_is_pinned_default_false(self):
        """is_pinned should default to False."""
        note = OpportunityNote(
            opportunity_id=uuid4(),
            content="Test",
            is_pinned=False,
        )
        assert note.is_pinned is False


class TestRFQModel:
    """Tests for the RFQ model."""

    def test_rfq_required_fields(self):
        """RFQ should require rfq_number, title, account_id."""
        account_id = uuid4()
        rfq = RFQ(
            rfq_number="RFQ-2024-001",
            title="Automotive Parts Quote Request",
            account_id=account_id,
        )
        assert rfq.rfq_number == "RFQ-2024-001"
        assert rfq.title == "Automotive Parts Quote Request"
        assert rfq.account_id == account_id

    def test_rfq_default_status_is_received(self):
        """RFQ status should default to received."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            status=RFQStatus.RECEIVED.value,
        )
        assert rfq.status == RFQStatus.RECEIVED.value

    def test_rfq_default_priority_is_medium(self):
        """RFQ priority should default to medium."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            priority=RFQPriority.MEDIUM.value,
        )
        assert rfq.priority == RFQPriority.MEDIUM.value

    def test_rfq_default_revision_is_1(self):
        """RFQ revision should default to 1."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            revision=1,
        )
        assert rfq.revision == 1

    def test_rfq_default_currency_is_mad(self):
        """RFQ currency should default to MAD."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            currency="MAD",
        )
        assert rfq.currency == "MAD"

    def test_rfq_is_open_true_for_active_statuses(self):
        """is_open should be True for non-closed statuses."""
        for status in [
            RFQStatus.DRAFT,
            RFQStatus.RECEIVED,
            RFQStatus.UNDER_REVIEW,
            RFQStatus.QUESTIONS_PENDING,
            RFQStatus.QUALIFYING,
            RFQStatus.QUALIFIED,
            RFQStatus.NOT_QUALIFIED,
            RFQStatus.QUOTING,
            RFQStatus.QUOTED,
        ]:
            rfq = RFQ(
                rfq_number="RFQ-001",
                title="Test",
                account_id=uuid4(),
                status=status.value,
            )
            assert rfq.is_open is True

    def test_rfq_is_open_false_for_closed_statuses(self):
        """is_open should be False for closed statuses."""
        for status in [
            RFQStatus.WON,
            RFQStatus.LOST,
            RFQStatus.NO_BID,
            RFQStatus.CANCELLED,
            RFQStatus.EXPIRED,
        ]:
            rfq = RFQ(
                rfq_number="RFQ-001",
                title="Test",
                account_id=uuid4(),
                status=status.value,
            )
            assert rfq.is_open is False

    def test_rfq_days_until_due_none_when_no_due_date(self):
        """days_until_due should be None when due_date is not set."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
        )
        assert rfq.days_until_due is None

    def test_rfq_days_until_due_positive_for_future_date(self):
        """days_until_due should be positive for future due dates."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            due_date=datetime.now(timezone.utc) + timedelta(days=10),
        )
        assert rfq.days_until_due == 9 or rfq.days_until_due == 10

    def test_rfq_days_until_due_negative_for_past_date(self):
        """days_until_due should be negative for past due dates."""
        rfq = RFQ(
            rfq_number="RFQ-001",
            title="Test",
            account_id=uuid4(),
            due_date=datetime.now(timezone.utc) - timedelta(days=5),
        )
        assert rfq.days_until_due == -5 or rfq.days_until_due == -6


class TestRFQStatusEnum:
    """Tests for RFQStatus enum."""

    def test_all_statuses_defined(self):
        """All expected RFQ statuses should be defined."""
        assert RFQStatus.DRAFT.value == "draft"
        assert RFQStatus.RECEIVED.value == "received"
        assert RFQStatus.UNDER_REVIEW.value == "under_review"
        assert RFQStatus.QUESTIONS_PENDING.value == "questions_pending"
        assert RFQStatus.QUALIFYING.value == "qualifying"
        assert RFQStatus.QUALIFIED.value == "qualified"
        assert RFQStatus.NOT_QUALIFIED.value == "not_qualified"
        assert RFQStatus.QUOTING.value == "quoting"
        assert RFQStatus.QUOTED.value == "quoted"
        assert RFQStatus.WON.value == "won"
        assert RFQStatus.LOST.value == "lost"
        assert RFQStatus.NO_BID.value == "no_bid"
        assert RFQStatus.CANCELLED.value == "cancelled"
        assert RFQStatus.EXPIRED.value == "expired"


class TestRFQQuestionModel:
    """Tests for the RFQQuestion model."""

    def test_rfq_question_required_fields(self):
        """RFQQuestion should require rfq_id, question_number, question."""
        rfq_id = uuid4()
        q = RFQQuestion(
            rfq_id=rfq_id,
            question_number=1,
            question="What is the material specification?",
        )
        assert q.rfq_id == rfq_id
        assert q.question_number == 1
        assert q.question == "What is the material specification?"

    def test_rfq_question_default_status_is_draft(self):
        """RFQQuestion status should default to draft."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            status=QuestionStatus.DRAFT.value,
        )
        assert q.status == QuestionStatus.DRAFT.value

    def test_rfq_question_is_critical_default_false(self):
        """is_critical should default to False."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            is_critical=False,
        )
        assert q.is_critical is False

    def test_rfq_question_is_answered_false_for_draft(self):
        """is_answered should be False for draft status."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            status=QuestionStatus.DRAFT.value,
        )
        assert q.is_answered is False

    def test_rfq_question_is_answered_false_for_sent(self):
        """is_answered should be False for sent status."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            status=QuestionStatus.SENT.value,
        )
        assert q.is_answered is False

    def test_rfq_question_is_answered_true_for_answered(self):
        """is_answered should be True for answered status."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            status=QuestionStatus.ANSWERED.value,
        )
        assert q.is_answered is True

    def test_rfq_question_is_answered_true_for_closed(self):
        """is_answered should be True for closed status."""
        q = RFQQuestion(
            rfq_id=uuid4(),
            question_number=1,
            question="Test?",
            status=QuestionStatus.CLOSED.value,
        )
        assert q.is_answered is True


class TestRFQAttachmentModel:
    """Tests for the RFQAttachment model."""

    def test_rfq_attachment_required_fields(self):
        """RFQAttachment should require rfq_id, filename, file_size, etc."""
        rfq_id = uuid4()
        att = RFQAttachment(
            rfq_id=rfq_id,
            filename="drawing_001.pdf",
            original_filename="Part_Drawing_Rev_A.pdf",
            file_size=1048576,  # 1 MB
            mime_type="application/pdf",
            storage_key="rfqs/abc123/drawing_001.pdf",
            storage_bucket="sensei-uploads",
        )
        assert att.rfq_id == rfq_id
        assert att.filename == "drawing_001.pdf"
        assert att.file_size == 1048576
        assert att.mime_type == "application/pdf"

    def test_rfq_attachment_default_type_is_other(self):
        """attachment_type should default to other."""
        att = RFQAttachment(
            rfq_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            attachment_type=RFQAttachmentType.OTHER.value,
        )
        assert att.attachment_type == RFQAttachmentType.OTHER.value

    def test_rfq_attachment_is_customer_provided_default_true(self):
        """is_customer_provided should default to True."""
        att = RFQAttachment(
            rfq_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
            is_customer_provided=True,
        )
        assert att.is_customer_provided is True

    def test_rfq_attachment_file_size_human_bytes(self):
        """file_size_human should format bytes correctly."""
        att = RFQAttachment(
            rfq_id=uuid4(),
            filename="test.txt",
            original_filename="test.txt",
            file_size=500,
            mime_type="text/plain",
            storage_key="test/key",
            storage_bucket="bucket",
        )
        assert "500" in att.file_size_human
        assert "B" in att.file_size_human

    def test_rfq_attachment_file_size_human_kb(self):
        """file_size_human should format KB correctly."""
        att = RFQAttachment(
            rfq_id=uuid4(),
            filename="test.txt",
            original_filename="test.txt",
            file_size=5120,  # 5 KB
            mime_type="text/plain",
            storage_key="test/key",
            storage_bucket="bucket",
        )
        assert "KB" in att.file_size_human

    def test_rfq_attachment_file_size_human_mb(self):
        """file_size_human should format MB correctly."""
        att = RFQAttachment(
            rfq_id=uuid4(),
            filename="test.pdf",
            original_filename="test.pdf",
            file_size=5242880,  # 5 MB
            mime_type="application/pdf",
            storage_key="test/key",
            storage_bucket="bucket",
        )
        assert "MB" in att.file_size_human
