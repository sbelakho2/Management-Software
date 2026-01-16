from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    UniqueConstraint,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from sensei.models.base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from sensei.models.user import User
    from sensei.models.account import Account


class PurchaseRequisition(Base, TimestampMixin, AuditMixin):
    """
    Internal request to purchase goods or services.
    """
    __tablename__ = "purchase_requisitions"

    pr_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    requested_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    supplier_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, submitted, approved, rejected, canceled

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id])
    submitted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[submitted_by_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    rejected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[rejected_by_id])
    supplier: Mapped[Optional["Account"]] = relationship("Account")
    lines: Mapped[list["PRLine"]] = relationship("PRLine", back_populates="requisition", cascade="all, delete-orphan")


class PRLine(Base, TimestampMixin):
    """
    Individual item in a Purchase Requisition.
    """
    __tablename__ = "pr_lines"

    pr_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_requisitions.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    requisition: Mapped["PurchaseRequisition"] = relationship("PurchaseRequisition", back_populates="lines")


class PurchaseOrder(Base, TimestampMixin, AuditMixin):
    """
    Contractual agreement with a supplier.
    """
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, approved, sent, partially_received, received, closed, canceled

    source_pr_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("purchase_requisitions.id"), nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    supplier: Mapped["Account"] = relationship("Account")
    source_pr: Mapped[Optional["PurchaseRequisition"]] = relationship("PurchaseRequisition")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    sent_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[sent_by_id])
    lines: Mapped[list["POLine"]] = relationship("POLine", back_populates="order", cascade="all, delete-orphan")


class POLine(Base, TimestampMixin):
    """
    Individual item in a Purchase Order.
    """
    __tablename__ = "po_lines"

    po_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")


class GoodsReceipt(Base, TimestampMixin):
    """
    Record of goods received from a supplier.
    """
    __tablename__ = "goods_receipts"

    po_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    po: Mapped["PurchaseOrder"] = relationship("PurchaseOrder")
    received_by: Mapped["User"] = relationship("User")
    lines: Mapped[list["ReceiptLine"]] = relationship("ReceiptLine", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptLine(Base, TimestampMixin):
    """
    Individual item in a Goods Receipt.
    """
    __tablename__ = "receipt_lines"

    receipt_id: Mapped[UUID] = mapped_column(ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    receipt: Mapped["GoodsReceipt"] = relationship("GoodsReceipt", back_populates="lines")


class SupplierInvoice(Base, TimestampMixin, AuditMixin):
    """
    Invoice received from a supplier.
    """
    __tablename__ = "supplier_invoices"

    supplier_invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, submitted, approved, posted, paid, rejected, void

    po_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    supplier: Mapped["Account"] = relationship("Account")
    po: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    posted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[posted_by_id])
    paid_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[paid_by_id])
    lines: Mapped[list["SupplierInvoiceLine"]] = relationship("SupplierInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class SupplierInvoiceLine(Base, TimestampMixin):
    """
    Individual line in a Supplier Invoice.
    """
    __tablename__ = "supplier_invoice_lines"

    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    invoice: Mapped["SupplierInvoice"] = relationship("SupplierInvoice", back_populates="lines")


class PaymentRun(Base, TimestampMixin, AuditMixin):
    """
    Batch of payments to suppliers.
    """
    __tablename__ = "payment_runs"

    run_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, approved, executed, canceled

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    executed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[executed_by_id])
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="payment_run", cascade="all, delete-orphan")


class Payment(Base, TimestampMixin):
    """
    Single payment to a supplier.
    """
    __tablename__ = "payments"

    payment_run_id: Mapped[UUID] = mapped_column(ForeignKey("payment_runs.id"), nullable=False, index=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    payment_run: Mapped["PaymentRun"] = relationship("PaymentRun", back_populates="payments")
    supplier: Mapped["Account"] = relationship("Account")
    invoices: Mapped[list["SupplierInvoice"]] = relationship("SupplierInvoice", secondary="payment_invoice_links")


class PaymentInvoiceLink(Base):
    """
    Link between Payment and SupplierInvoice (Many-to-Many).
    """
    __tablename__ = "payment_invoice_links"

    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), primary_key=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("supplier_invoices.id", ondelete="CASCADE"), primary_key=True)
