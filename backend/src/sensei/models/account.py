"""
Account and Contact models for CRM functionality.

Implements:
- Account: Company/organization records (customers, prospects, suppliers)
- Contact: Individual people associated with accounts
- AccountContact: Many-to-many relationship with role information
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.opportunity import Opportunity
    from sensei.models.quote import SupplierQuote
    from sensei.models.rfq import RFQ
    from sensei.models.work_center import WorkCenter


class AccountType(str, Enum):
    """Type of account."""
    
    CUSTOMER = "customer"
    PROSPECT = "prospect"
    SUPPLIER = "supplier"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    OTHER = "other"


class AccountStatus(str, Enum):
    """Account lifecycle status."""
    
    LEAD = "lead"
    PROSPECT = "prospect"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"
    BLOCKED = "blocked"


class AccountTier(str, Enum):
    """Account importance tier for prioritization."""
    
    STRATEGIC = "strategic"
    KEY = "key"
    STANDARD = "standard"
    SMALL = "small"


class Account(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Company/organization record.
    
    Central entity for customer, prospect, and supplier management.
    Supports the full sales pipeline from lead to active customer.
    """
    
    __tablename__ = "accounts"
    
    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    
    # Classification
    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AccountType.PROSPECT.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AccountStatus.LEAD.value,
        index=True,
    )
    tier: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sub_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Contact Information
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fax: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Primary Address
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    state_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Morocco",
        index=True,
    )
    
    # Business Information
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employees_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    revenue_currency: Mapped[str] = mapped_column(String(3), default="MAD", nullable=False)
    
    # Dates
    established_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    first_contact_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    customer_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Sales Information
    lead_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referred_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Capabilities (for suppliers)
    capabilities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Scoring and Analytics
    qualification_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    health_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Notes and Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Tags for categorization
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Parent account for hierarchies
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    
    # Relationships
    parent: Mapped["Account | None"] = relationship(
        "Account",
        remote_side="Account.id",
        back_populates="subsidiaries",
    )
    subsidiaries: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="parent",
    )
    
    contacts: Mapped[list["AccountContact"]] = relationship(
        "AccountContact",
        back_populates="account",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="select",
    )
    
    opportunities: Mapped[list["Opportunity"]] = relationship(
        "Opportunity",
        back_populates="account",
        foreign_keys="Opportunity.account_id",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="select",
    )
    
    rfqs: Mapped[list["RFQ"]] = relationship(
        "RFQ",
        back_populates="account",
        foreign_keys="RFQ.account_id",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="select",
    )
    
    supplier_quotes: Mapped[list["SupplierQuote"]] = relationship(
        "SupplierQuote",
        back_populates="supplier",
        foreign_keys="SupplierQuote.supplier_id",
        lazy="select",
    )
    
    # Phase 3: Work centers owned by this account
    work_centers: Mapped[list["WorkCenter"]] = relationship(
        "WorkCenter",
        back_populates="account",
        lazy="select",
    )
    
    __table_args__ = (
        Index("ix_accounts_type_status", account_type, status),
        Index("ix_accounts_name_search", name, postgresql_ops={"name": "gin_trgm_ops"}, postgresql_using="gin"),
        Index("ix_accounts_country_city", country, city),
    )
    
    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        
        city_parts = []
        if self.city:
            city_parts.append(self.city)
        if self.state_province:
            city_parts.append(self.state_province)
        if self.postal_code:
            city_parts.append(self.postal_code)
        if city_parts:
            parts.append(", ".join(city_parts))
        
        if self.country:
            parts.append(self.country)
        
        return "\n".join(parts)
    
    @property
    def is_customer(self) -> bool:
        """Check if this account is a customer."""
        return self.account_type == AccountType.CUSTOMER.value
    
    @property
    def is_supplier(self) -> bool:
        """Check if this account is a supplier."""
        return self.account_type == AccountType.SUPPLIER.value


class ContactRole(str, Enum):
    """Role of a contact at an account."""
    
    PRIMARY = "primary"
    BILLING = "billing"
    TECHNICAL = "technical"
    DECISION_MAKER = "decision_maker"
    INFLUENCER = "influencer"
    END_USER = "end_user"
    BUYER = "buyer"
    EXECUTIVE = "executive"
    OTHER = "other"


class Contact(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Individual person record.
    
    Contacts can be associated with multiple accounts through AccountContact.
    """
    
    __tablename__ = "contacts"
    
    # Name
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salutation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    # Contact Information
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email_secondary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_mobile: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_work: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_home: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Professional Information
    job_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Preferences
    preferred_language: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Africa/Casablanca",
        nullable=False,
    )
    
    # Address (personal address, different from account address)
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Social
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    twitter_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Marketing
    email_opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    do_not_call: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Dates
    birthdate: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Notes
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom Fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Tags
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    
    # Relationships
    accounts: Mapped[list["AccountContact"]] = relationship(
        "AccountContact",
        back_populates="contact",
        cascade="all, delete-orphan",
        lazy="select",
    )
    
    __table_args__ = (
        Index("ix_contacts_name", last_name, first_name),
        Index("ix_contacts_email_lower", email),
    )
    
    @property
    def full_name(self) -> str:
        """Get the contact's full name."""
        parts = []
        if self.salutation:
            parts.append(self.salutation)
        parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)
    
    @property
    def display_name(self) -> str:
        """Get display name (first last)."""
        return f"{self.first_name} {self.last_name}"


class AccountContact(Base, TimestampMixin):
    """
    Many-to-many relationship between accounts and contacts.
    
    Includes role and relationship metadata.
    """
    
    __tablename__ = "account_contacts"
    
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    
    # Role at this account
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ContactRole.OTHER.value,
    )
    
    # Is this the primary contact for the account?
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Is this relationship active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Start and end dates for the relationship
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Notes about this specific relationship
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="contacts")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="accounts")
    
    __table_args__ = (
        UniqueConstraint("account_id", "contact_id", name="uq_account_contact"),
        Index("ix_account_contacts_account_id", account_id),
        Index("ix_account_contacts_contact_id", contact_id),
        Index(
            "ix_account_contacts_primary",
            account_id,
            postgresql_where=(is_primary == True),  # noqa: E712
        ),
    )
