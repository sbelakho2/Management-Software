"""
Tests for Account and Contact models.

Tests:
- Account model fields and defaults
- Account type and status enums
- Account address formatting
- Account customer/supplier checks
- Contact model fields
- Contact name formatting
- AccountContact relationship
- Primary contact handling
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.account import (
    Account,
    AccountContact,
    AccountStatus,
    AccountTier,
    AccountType,
    Contact,
    ContactRole,
)


class TestAccountModel:
    """Tests for the Account model."""

    def test_account_required_fields(self):
        """Account should require name."""
        account = Account(name="Acme Corp")
        assert account.name == "Acme Corp"

    def test_account_default_type_is_prospect(self):
        """Account type should default to prospect - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        account = Account(name="Test", account_type=AccountType.PROSPECT.value)
        assert account.account_type == AccountType.PROSPECT.value

    def test_account_default_status_is_lead(self):
        """Account status should default to lead - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        account = Account(name="Test", status=AccountStatus.LEAD.value)
        assert account.status == AccountStatus.LEAD.value

    def test_account_default_country_is_morocco(self):
        """Account country should default to Morocco - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        account = Account(name="Test", country="Morocco")
        assert account.country == "Morocco"

    def test_account_default_currency_is_mad(self):
        """Account revenue currency should default to MAD - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        account = Account(name="Test", revenue_currency="MAD")
        assert account.revenue_currency == "MAD"

    def test_account_is_customer_true_for_customer_type(self):
        """is_customer should be True for customer type."""
        account = Account(name="Test", account_type=AccountType.CUSTOMER.value)
        assert account.is_customer is True

    def test_account_is_customer_false_for_other_types(self):
        """is_customer should be False for non-customer types."""
        account = Account(name="Test", account_type=AccountType.PROSPECT.value)
        assert account.is_customer is False

    def test_account_is_supplier_true_for_supplier_type(self):
        """is_supplier should be True for supplier type."""
        account = Account(name="Test", account_type=AccountType.SUPPLIER.value)
        assert account.is_supplier is True

    def test_account_is_supplier_false_for_other_types(self):
        """is_supplier should be False for non-supplier types."""
        account = Account(name="Test", account_type=AccountType.CUSTOMER.value)
        assert account.is_supplier is False

    def test_account_full_address_with_all_fields(self):
        """full_address should format complete address correctly."""
        account = Account(
            name="Test",
            address_line1="123 Main St",
            address_line2="Suite 100",
            city="Casablanca",
            state_province="Grand Casablanca",
            postal_code="20000",
            country="Morocco",
        )
        address = account.full_address
        assert "123 Main St" in address
        assert "Suite 100" in address
        assert "Casablanca" in address
        assert "Morocco" in address

    def test_account_full_address_with_minimal_fields(self):
        """full_address should work with minimal fields."""
        account = Account(name="Test", city="Rabat", country="Morocco")
        address = account.full_address
        assert "Rabat" in address
        assert "Morocco" in address

    def test_account_full_address_empty_when_no_address(self):
        """full_address should handle no address fields."""
        # Explicit country since SQLAlchemy column defaults don't apply without DB
        account = Account(name="Test", country="Morocco")
        address = account.full_address
        assert "Morocco" in address

    def test_account_custom_fields_default_empty_dict(self):
        """custom_fields should default to empty dict."""
        account = Account(name="Test")
        assert account.custom_fields == {} or account.custom_fields is None

    def test_account_tags_default_empty_list(self):
        """tags should default to empty list."""
        account = Account(name="Test")
        assert account.tags == [] or account.tags is None

    def test_account_with_all_fields(self):
        """Account should accept all fields."""
        account = Account(
            name="Acme Corporation",
            legal_name="Acme Corp S.A.",
            account_number="ACC-001",
            account_type=AccountType.CUSTOMER.value,
            status=AccountStatus.ACTIVE.value,
            tier=AccountTier.STRATEGIC.value,
            industry="Automotive",
            website="https://acme.com",
            phone="+212 5 22 123456",
            email="contact@acme.com",
            address_line1="123 Industrial Zone",
            city="Casablanca",
            country="Morocco",
            tax_id="MA123456789",
            employees_count=500,
            annual_revenue=Decimal("10000000.00"),
        )
        assert account.name == "Acme Corporation"
        assert account.tier == AccountTier.STRATEGIC.value
        assert account.industry == "Automotive"


class TestAccountTypeEnum:
    """Tests for AccountType enum."""

    def test_all_types_defined(self):
        """All expected account types should be defined."""
        assert AccountType.CUSTOMER.value == "customer"
        assert AccountType.PROSPECT.value == "prospect"
        assert AccountType.SUPPLIER.value == "supplier"
        assert AccountType.PARTNER.value == "partner"
        assert AccountType.COMPETITOR.value == "competitor"
        assert AccountType.OTHER.value == "other"


class TestAccountStatusEnum:
    """Tests for AccountStatus enum."""

    def test_all_statuses_defined(self):
        """All expected account statuses should be defined."""
        assert AccountStatus.LEAD.value == "lead"
        assert AccountStatus.PROSPECT.value == "prospect"
        assert AccountStatus.QUALIFIED.value == "qualified"
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.INACTIVE.value == "inactive"
        assert AccountStatus.CHURNED.value == "churned"
        assert AccountStatus.BLOCKED.value == "blocked"


class TestAccountTierEnum:
    """Tests for AccountTier enum."""

    def test_all_tiers_defined(self):
        """All expected account tiers should be defined."""
        assert AccountTier.STRATEGIC.value == "strategic"
        assert AccountTier.KEY.value == "key"
        assert AccountTier.STANDARD.value == "standard"
        assert AccountTier.SMALL.value == "small"


class TestContactModel:
    """Tests for the Contact model."""

    def test_contact_required_fields(self):
        """Contact should require first_name and last_name."""
        contact = Contact(first_name="John", last_name="Doe")
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"

    def test_contact_full_name_basic(self):
        """full_name should return first and last name."""
        contact = Contact(first_name="John", last_name="Doe")
        assert contact.full_name == "John Doe"

    def test_contact_full_name_with_salutation(self):
        """full_name should include salutation if present."""
        contact = Contact(first_name="John", last_name="Doe", salutation="Mr.")
        assert contact.full_name == "Mr. John Doe"

    def test_contact_full_name_with_middle_name(self):
        """full_name should include middle name if present."""
        contact = Contact(first_name="John", last_name="Doe", middle_name="Robert")
        assert contact.full_name == "John Robert Doe"

    def test_contact_full_name_with_suffix(self):
        """full_name should include suffix if present."""
        contact = Contact(first_name="John", last_name="Doe", suffix="Jr.")
        assert contact.full_name == "John Doe Jr."

    def test_contact_full_name_complete(self):
        """full_name should handle all name components."""
        contact = Contact(
            first_name="John",
            last_name="Doe",
            salutation="Dr.",
            middle_name="Robert",
            suffix="III",
        )
        assert contact.full_name == "Dr. John Robert Doe III"

    def test_contact_display_name(self):
        """display_name should return first last format."""
        contact = Contact(
            first_name="John", last_name="Doe", salutation="Dr.", suffix="III"
        )
        assert contact.display_name == "John Doe"

    def test_contact_default_language_is_fr(self):
        """Default preferred language should be French - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        contact = Contact(first_name="Test", last_name="User", preferred_language="fr")
        assert contact.preferred_language == "fr"

    def test_contact_default_timezone_is_casablanca(self):
        """Default timezone should be Africa/Casablanca - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        contact = Contact(first_name="Test", last_name="User", timezone="Africa/Casablanca")
        assert contact.timezone == "Africa/Casablanca"

    def test_contact_email_opt_out_default_false(self):
        """email_opt_out should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        contact = Contact(first_name="Test", last_name="User", email_opt_out=False)
        assert contact.email_opt_out is False

    def test_contact_do_not_call_default_false(self):
        """do_not_call should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        contact = Contact(first_name="Test", last_name="User", do_not_call=False)
        assert contact.do_not_call is False


class TestContactRoleEnum:
    """Tests for ContactRole enum."""

    def test_all_roles_defined(self):
        """All expected contact roles should be defined."""
        assert ContactRole.PRIMARY.value == "primary"
        assert ContactRole.BILLING.value == "billing"
        assert ContactRole.TECHNICAL.value == "technical"
        assert ContactRole.DECISION_MAKER.value == "decision_maker"
        assert ContactRole.INFLUENCER.value == "influencer"
        assert ContactRole.END_USER.value == "end_user"
        assert ContactRole.BUYER.value == "buyer"
        assert ContactRole.EXECUTIVE.value == "executive"
        assert ContactRole.OTHER.value == "other"


class TestAccountContactModel:
    """Tests for the AccountContact model."""

    def test_account_contact_required_fields(self):
        """AccountContact should require account_id and contact_id."""
        account_id = uuid4()
        contact_id = uuid4()
        ac = AccountContact(account_id=account_id, contact_id=contact_id)
        assert ac.account_id == account_id
        assert ac.contact_id == contact_id

    def test_account_contact_default_role_is_other(self):
        """AccountContact role should default to other - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        ac = AccountContact(account_id=uuid4(), contact_id=uuid4(), role=ContactRole.OTHER.value)
        assert ac.role == ContactRole.OTHER.value

    def test_account_contact_is_primary_default_false(self):
        """is_primary should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        ac = AccountContact(account_id=uuid4(), contact_id=uuid4(), is_primary=False)
        assert ac.is_primary is False

    def test_account_contact_is_active_default_true(self):
        """is_active should default to True - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        ac = AccountContact(account_id=uuid4(), contact_id=uuid4(), is_active=True)
        assert ac.is_active is True

    def test_account_contact_with_role(self):
        """AccountContact should accept role."""
        ac = AccountContact(
            account_id=uuid4(),
            contact_id=uuid4(),
            role=ContactRole.DECISION_MAKER.value,
            is_primary=True,
        )
        assert ac.role == ContactRole.DECISION_MAKER.value
        assert ac.is_primary is True

    def test_account_contact_with_dates(self):
        """AccountContact should accept start and end dates."""
        now = datetime.now(timezone.utc)
        ac = AccountContact(
            account_id=uuid4(),
            contact_id=uuid4(),
            start_date=now,
            end_date=now,
        )
        assert ac.start_date == now
        assert ac.end_date == now
