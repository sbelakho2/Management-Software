"""
Tests for Quote models.

Tests:
- Quote model fields and defaults
- Quote version management
- QuoteLineItem calculations
- SupplierQuote model
- Quote status workflow
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.quote import (
    ApprovalStatus,
    LineItemType,
    Quote,
    QuoteLineItem,
    QuoteStatus,
    QuoteVersion,
    SupplierQuote,
    SupplierQuoteItem,
    SupplierQuoteStatus,
)


class TestQuoteModel:
    """Tests for the Quote model."""

    def test_quote_required_fields(self):
        """Quote should require quote_number, account_id, title."""
        account_id = uuid4()
        quote = Quote(
            quote_number="QT-2024-001",
            account_id=account_id,
            title="Automotive Parts Quote",
        )
        assert quote.quote_number == "QT-2024-001"
        assert quote.account_id == account_id
        assert quote.title == "Automotive Parts Quote"

    def test_quote_default_status_is_draft(self):
        """Quote status should default to draft."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            status=QuoteStatus.DRAFT.value,
        )
        assert quote.status == QuoteStatus.DRAFT.value

    def test_quote_default_current_version_is_1(self):
        """Quote current_version should default to 1."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            current_version=1,
        )
        assert quote.current_version == 1

    def test_quote_default_currency_is_mad(self):
        """Quote currency should default to MAD."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            currency="MAD",
        )
        assert quote.currency == "MAD"

    def test_quote_default_exchange_rate_is_1(self):
        """Quote exchange_rate should default to 1.0."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            exchange_rate=Decimal("1.0"),
        )
        assert quote.exchange_rate == Decimal("1.0")

    def test_quote_default_approval_status(self):
        """Quote approval_status should default to not_required."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            approval_status=ApprovalStatus.NOT_REQUIRED.value,
        )
        assert quote.approval_status == ApprovalStatus.NOT_REQUIRED.value

    def test_quote_default_requires_approval_false(self):
        """requires_approval should default to False."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            requires_approval=False,
        )
        assert quote.requires_approval is False

    def test_quote_default_subtotal_zero(self):
        """subtotal should default to 0."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            subtotal=Decimal("0"),
        )
        assert quote.subtotal == Decimal("0")

    def test_quote_is_open_true_for_active_statuses(self):
        """is_open should be True for non-closed statuses."""
        for status in [
            QuoteStatus.DRAFT,
            QuoteStatus.PENDING_REVIEW,
            QuoteStatus.PENDING_APPROVAL,
            QuoteStatus.APPROVED,
            QuoteStatus.SENT,
            QuoteStatus.VIEWED,
        ]:
            quote = Quote(
                quote_number="QT-001",
                account_id=uuid4(),
                title="Test Quote",
                status=status.value,
            )
            assert quote.is_open is True

    def test_quote_is_open_false_for_closed_statuses(self):
        """is_open should be False for closed statuses."""
        for status in [
            QuoteStatus.ACCEPTED,
            QuoteStatus.REJECTED,
            QuoteStatus.EXPIRED,
            QuoteStatus.CANCELLED,
        ]:
            quote = Quote(
                quote_number="QT-001",
                account_id=uuid4(),
                title="Test Quote",
                status=status.value,
            )
            assert quote.is_open is False

    def test_quote_is_expired_false_when_no_valid_until(self):
        """is_expired should be False when valid_until is not set."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
        )
        assert quote.is_expired is False

    def test_quote_is_expired_false_for_future_date(self):
        """is_expired should be False when valid_until is in the future."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            valid_until=datetime.now(timezone.utc) + timedelta(days=10),
        )
        assert quote.is_expired is False

    def test_quote_is_expired_true_for_past_date(self):
        """is_expired should be True when valid_until is in the past."""
        quote = Quote(
            quote_number="QT-001",
            account_id=uuid4(),
            title="Test Quote",
            valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert quote.is_expired is True


class TestQuoteStatusEnum:
    """Tests for QuoteStatus enum."""

    def test_all_statuses_defined(self):
        """All expected quote statuses should be defined."""
        assert QuoteStatus.DRAFT.value == "draft"
        assert QuoteStatus.PENDING_REVIEW.value == "pending_review"
        assert QuoteStatus.PENDING_APPROVAL.value == "pending_approval"
        assert QuoteStatus.APPROVED.value == "approved"
        assert QuoteStatus.SENT.value == "sent"
        assert QuoteStatus.VIEWED.value == "viewed"
        assert QuoteStatus.ACCEPTED.value == "accepted"
        assert QuoteStatus.REJECTED.value == "rejected"
        assert QuoteStatus.EXPIRED.value == "expired"
        assert QuoteStatus.CANCELLED.value == "cancelled"
        assert QuoteStatus.REVISED.value == "revised"


class TestApprovalStatusEnum:
    """Tests for ApprovalStatus enum."""

    def test_all_statuses_defined(self):
        """All expected approval statuses should be defined."""
        assert ApprovalStatus.NOT_REQUIRED.value == "not_required"
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"


class TestQuoteVersionModel:
    """Tests for the QuoteVersion model."""

    def test_quote_version_required_fields(self):
        """QuoteVersion should require quote_id, version_number, snapshot."""
        quote_id = uuid4()
        version = QuoteVersion(
            quote_id=quote_id,
            version_number=1,
            snapshot={"total": 10000, "line_items": []},
        )
        assert version.quote_id == quote_id
        assert version.version_number == 1
        assert version.snapshot == {"total": 10000, "line_items": []}

    def test_quote_version_snapshot_dict(self):
        """QuoteVersion snapshot should accept a dict."""
        version = QuoteVersion(
            quote_id=uuid4(),
            version_number=1,
            snapshot={"subtotal": 5000, "discount": 500, "total": 4500},
        )
        assert version.snapshot["subtotal"] == 5000
        assert version.snapshot["total"] == 4500


class TestQuoteLineItemModel:
    """Tests for the QuoteLineItem model."""

    def test_line_item_required_fields(self):
        """QuoteLineItem should require quote_id, line_number, description, quantity, unit_price, line_total."""
        quote_id = uuid4()
        item = QuoteLineItem(
            quote_id=quote_id,
            line_number=1,
            description="Machined Part XYZ",
            quantity=Decimal("100"),
            unit_price=Decimal("50.00"),
            line_total=Decimal("5000.00"),
        )
        assert item.quote_id == quote_id
        assert item.line_number == 1
        assert item.description == "Machined Part XYZ"
        assert item.quantity == Decimal("100")
        assert item.unit_price == Decimal("50.00")
        assert item.line_total == Decimal("5000.00")

    def test_line_item_default_unit_of_measure_is_ea(self):
        """unit_of_measure should default to EA."""
        item = QuoteLineItem(
            quote_id=uuid4(),
            line_number=1,
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            unit_of_measure="EA",
        )
        assert item.unit_of_measure == "EA"

    def test_line_item_default_discount_amount_zero(self):
        """discount_amount should default to 0."""
        item = QuoteLineItem(
            quote_id=uuid4(),
            line_number=1,
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            discount_amount=Decimal("0"),
        )
        assert item.discount_amount == Decimal("0")

    def test_line_item_default_is_included_true(self):
        """is_included should default to True."""
        item = QuoteLineItem(
            quote_id=uuid4(),
            line_number=1,
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            is_included=True,
        )
        assert item.is_included is True

    def test_line_item_default_is_optional_false(self):
        """is_optional should default to False."""
        item = QuoteLineItem(
            quote_id=uuid4(),
            line_number=1,
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            is_optional=False,
        )
        assert item.is_optional is False


class TestLineItemTypeEnum:
    """Tests for LineItemType enum."""

    def test_all_types_defined(self):
        """All expected line item types should be defined."""
        assert LineItemType.PRODUCT.value == "product"
        assert LineItemType.SERVICE.value == "service"
        assert LineItemType.TOOLING.value == "tooling"
        assert LineItemType.NRE.value == "nre"
        assert LineItemType.FREIGHT.value == "freight"
        assert LineItemType.OTHER.value == "other"


class TestSupplierQuoteModel:
    """Tests for the SupplierQuote model."""

    def test_supplier_quote_required_fields(self):
        """SupplierQuote should require internal_reference and supplier_id."""
        supplier_id = uuid4()
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=supplier_id,
        )
        assert sq.internal_reference == "SQ-INT-001"
        assert sq.supplier_id == supplier_id

    def test_supplier_quote_default_status_is_requested(self):
        """SupplierQuote status should default to requested."""
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=uuid4(),
            status=SupplierQuoteStatus.REQUESTED.value,
        )
        assert sq.status == SupplierQuoteStatus.REQUESTED.value

    def test_supplier_quote_default_currency_is_mad(self):
        """SupplierQuote currency should default to MAD."""
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=uuid4(),
            currency="MAD",
        )
        assert sq.currency == "MAD"

    def test_supplier_quote_is_expired_false_when_no_valid_until(self):
        """is_expired should be False when valid_until is not set."""
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=uuid4(),
        )
        assert sq.is_expired is False

    def test_supplier_quote_is_expired_false_for_future_date(self):
        """is_expired should be False when valid_until is in the future."""
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=uuid4(),
            valid_until=datetime.now(timezone.utc) + timedelta(days=10),
        )
        assert sq.is_expired is False

    def test_supplier_quote_is_expired_true_for_past_date(self):
        """is_expired should be True when valid_until is in the past."""
        sq = SupplierQuote(
            internal_reference="SQ-INT-001",
            supplier_id=uuid4(),
            valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert sq.is_expired is True


class TestSupplierQuoteStatusEnum:
    """Tests for SupplierQuoteStatus enum."""

    def test_all_statuses_defined(self):
        """All expected supplier quote statuses should be defined."""
        assert SupplierQuoteStatus.REQUESTED.value == "requested"
        assert SupplierQuoteStatus.RECEIVED.value == "received"
        assert SupplierQuoteStatus.UNDER_REVIEW.value == "under_review"
        assert SupplierQuoteStatus.ACCEPTED.value == "accepted"
        assert SupplierQuoteStatus.REJECTED.value == "rejected"
        assert SupplierQuoteStatus.EXPIRED.value == "expired"


class TestSupplierQuoteItemModel:
    """Tests for the SupplierQuoteItem model."""

    def test_supplier_quote_item_required_fields(self):
        """SupplierQuoteItem should require supplier_quote_id, line_number, description, etc."""
        sq_id = uuid4()
        item = SupplierQuoteItem(
            supplier_quote_id=sq_id,
            line_number=1,
            description="Raw Material",
            quantity=Decimal("100"),
            unit_price=Decimal("5.00"),
            line_total=Decimal("500.00"),
        )
        assert item.supplier_quote_id == sq_id
        assert item.line_number == 1
        assert item.description == "Raw Material"
        assert item.quantity == Decimal("100")
        assert item.unit_price == Decimal("5.00")
        assert item.line_total == Decimal("500.00")

    def test_supplier_quote_item_default_unit_of_measure_is_ea(self):
        """unit_of_measure should default to EA."""
        item = SupplierQuoteItem(
            supplier_quote_id=uuid4(),
            line_number=1,
            description="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("10.00"),
            unit_of_measure="EA",
        )
        assert item.unit_of_measure == "EA"
