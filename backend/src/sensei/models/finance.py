"""
Finance and Accounting models.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin


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
