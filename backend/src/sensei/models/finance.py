"""
Finance and Accounting models.
"""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Integer as SAInteger,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects import postgresql

from sensei.models.base import Base, TimestampMixin, AuditMixin


class AccountingPeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class JournalEntryStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"

if TYPE_CHECKING:
    from sensei.models.user import User
    from sensei.models.site import Site
    from sensei.models.product import Product


class GLAccount(Base, TimestampMixin, AuditMixin):
    """
    General Ledger Account (Chart of Accounts).
    """
    __tablename__ = "gl_accounts"

    account_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    parent_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("gl_accounts.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(10), default="debit", nullable=False)  # debit or credit

    parent: Mapped[Optional["GLAccount"]] = relationship("GLAccount", remote_side="GLAccount.id", backref="children")


class OpeningBalance(Base, TimestampMixin, AuditMixin):
    """
    Opening balance for a GL account.
    """
    __tablename__ = "opening_balances"

    account_id: Mapped[UUID] = mapped_column(ForeignKey("gl_accounts.id", ondelete="CASCADE"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    account: Mapped["GLAccount"] = relationship("GLAccount")


class AccountingPeriod(Base, TimestampMixin, AuditMixin):
    """
    Accounting period (e.g. Month).
    Used to lock transactions for a period.
    """
    __tablename__ = "accounting_periods"

    period_key: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AccountingPeriodStatus.OPEN.value, nullable=False)  # open, closed
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    closed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[closed_by_id])


class JournalEntry(Base, TimestampMixin, AuditMixin):
    """
    General Ledger Journal Entry.
    """
    __tablename__ = "journal_entries"

    reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=JournalEntryStatus.DRAFT.value, nullable=False)  # draft, approved, posted, reversed
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    reversed_entry_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("journal_entries.id"), nullable=True)

    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    posted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[posted_by_id])
    lines: Mapped[list["JournalLine"]] = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base, TimestampMixin):
    """
    A single line in a Journal Entry.
    """
    __tablename__ = "journal_lines"

    entry_id: Mapped[UUID] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("gl_accounts.id"), nullable=False, index=True)
    
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_base: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")
    account: Mapped["GLAccount"] = relationship("GLAccount")


class FXRate(Base, TimestampMixin, AuditMixin):
    """
    Foreign Exchange Rate.
    """
    __tablename__ = "fx_rates"

    as_of: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    __table_args__ = (
        UniqueConstraint("as_of", "from_currency", "to_currency", name="uq_fx_rate"),
    )


class CurrencySetting(Base, TimestampMixin, AuditMixin):
    """
    Base currency and supported currencies configuration.
    """
    __tablename__ = "finance_currency_settings"

    base_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    reporting_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    allowed_currencies: Mapped[Optional[list]] = mapped_column(postgresql.JSONB(astext_type=Text()), nullable=True)
    fx_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auto_update_rates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class StandardCostRecord(Base, TimestampMixin, AuditMixin):
    """
    Standard cost record by SKU and effective date.
    """
    __tablename__ = "standard_costs"

    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    product_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    material_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    labor_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    overhead_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    product: Mapped[Optional["Product"]] = relationship("Product", foreign_keys=[product_id])

    __table_args__ = (
        UniqueConstraint("sku", "effective_date", name="uq_standard_cost_sku_date"),
    )


class WorkOrderCostRollup(Base, TimestampMixin, AuditMixin):
    """
    Stored cost rollup and variance for a work order.
    """
    __tablename__ = "work_order_cost_rollups"

    work_order_id: Mapped[int] = mapped_column(SAInteger, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    completed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    actual_material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    actual_labor_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    actual_overhead_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    relieved_actual_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    variance_material: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    variance_labor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    variance_overhead: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    variance_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaxJurisdiction(Base, TimestampMixin, AuditMixin):
    """
    Tax jurisdiction definition.
    """
    __tablename__ = "tax_jurisdictions"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class TaxRate(Base, TimestampMixin, AuditMixin):
    """
    Tax rate per jurisdiction and tax type.
    """
    __tablename__ = "tax_rates"

    jurisdiction_id: Mapped[UUID] = mapped_column(ForeignKey("tax_jurisdictions.id", ondelete="CASCADE"), nullable=False, index=True)
    tax_type: Mapped[str] = mapped_column(String(50), nullable=False)  # vat, sales, gst
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    jurisdiction: Mapped["TaxJurisdiction"] = relationship("TaxJurisdiction")


class TaxTransaction(Base, TimestampMixin, AuditMixin):
    """
    Tax transaction record for compliance tracking.
    """
    __tablename__ = "tax_transactions"

    jurisdiction_id: Mapped[UUID] = mapped_column(ForeignKey("tax_jurisdictions.id"), nullable=False, index=True)
    tax_rate_id: Mapped[UUID] = mapped_column(ForeignKey("tax_rates.id"), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    jurisdiction: Mapped["TaxJurisdiction"] = relationship("TaxJurisdiction")
    tax_rate: Mapped["TaxRate"] = relationship("TaxRate")


# =============================================================================
# BANKING AND PAYMENTS (for erpStarz import compatibility)
# =============================================================================


class Currency(Base, TimestampMixin, AuditMixin):
    """
    Currency definition.
    Maps from erpStarz `currency` table.
    """
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    decimal_places: Mapped[int] = mapped_column(default=2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)


class PaymentTerm(Base, TimestampMixin, AuditMixin):
    """
    Payment term definition.
    Maps from erpStarz `pay_term` table.
    """
    __tablename__ = "payment_terms"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    days_due: Mapped[int] = mapped_column(default=30, nullable=False)  # Net days
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    discount_days: Mapped[int] = mapped_column(default=0, nullable=False)  # Days for early payment discount
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)


class BankAccount(Base, TimestampMixin, AuditMixin):
    """
    Bank account for company financial operations.
    Maps from erpStarz `bank_account` and `company_bank` tables.
    """
    __tablename__ = "bank_accounts"

    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., SWIFT/BIC
    iban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="checking", nullable=False)  # checking, savings, cash
    
    site_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)
    gl_account_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("gl_accounts.id", ondelete="SET NULL"), nullable=True)
    
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    site: Mapped[Optional["Site"]] = relationship("Site")
    gl_account: Mapped[Optional["GLAccount"]] = relationship("GLAccount")
    transactions: Mapped[list["BankTransaction"]] = relationship("BankTransaction", back_populates="bank_account")


class BankTransaction(Base, TimestampMixin, AuditMixin):
    """
    Bank transaction record.
    Maps from erpStarz `bank_transaction` table.
    """
    __tablename__ = "bank_transactions"

    bank_account_id: Mapped[UUID] = mapped_column(ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # deposit, withdrawal, transfer, fee, interest
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    running_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False)  # pending, posted, reconciled, voided
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Link to source documents
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # payment, receipt, journal
    source_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    bank_account: Mapped["BankAccount"] = relationship("BankAccount", back_populates="transactions")
    reconciled_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reconciled_by_id])
