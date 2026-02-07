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
    from sensei.models.quote import Quote


class CustomerCreditProfile(Base, TimestampMixin, AuditMixin):
    """
    Credit controls for a customer account.
    """
    __tablename__ = "customer_credit_profiles"

    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_on_credit_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hold_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    account: Mapped["Account"] = relationship("Account")


class SalesOrder(Base, TimestampMixin, AuditMixin):
    """
    Customer order for goods or services.
    """
    __tablename__ = "sales_orders"

    so_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False) # draft, approved, on_hold, released, closed, canceled

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)

    source_quote_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    source_quote_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    account: Mapped["Account"] = relationship("Account")
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    released_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[released_by_id])
    source_quote: Mapped[Optional["Quote"]] = relationship("Quote")
    lines: Mapped[list["SalesOrderLine"]] = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan")


class SalesOrderLine(Base, TimestampMixin):
    """
    Individual item in a Sales Order.
    """
    __tablename__ = "sales_order_lines"

    so_id: Mapped[UUID] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped["SalesOrder"] = relationship("SalesOrder", back_populates="lines")


class CustomerInvoice(Base, TimestampMixin, AuditMixin):
    """
    Invoice issued to a customer.
    """
    __tablename__ = "customer_invoices"

    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="issued", nullable=False) # issued, paid, void

    sales_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("sales_orders.id"), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_credit_memo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["Account"] = relationship("Account")
    sales_order: Mapped[Optional["SalesOrder"]] = relationship("SalesOrder")
    lines: Mapped[list["CustomerInvoiceLine"]] = relationship("CustomerInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class CustomerInvoiceLine(Base, TimestampMixin):
    """
    Individual line in a Customer Invoice.
    """
    __tablename__ = "customer_invoice_lines"

    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("customer_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    invoice: Mapped["CustomerInvoice"] = relationship("CustomerInvoice", back_populates="lines")


class PaymentReceipt(Base, TimestampMixin):
    """
    Record of payment received from a customer.
    """
    __tablename__ = "payment_receipts"

    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="posted", nullable=False) # posted, reversed
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    account: Mapped["Account"] = relationship("Account")
    received_by: Mapped["User"] = relationship("User")
    allocations: Mapped[list["PaymentAllocation"]] = relationship("PaymentAllocation", back_populates="receipt", cascade="all, delete-orphan")


class PaymentAllocation(Base, TimestampMixin):
    """
    Allocation of a payment receipt to an invoice.
    """
    __tablename__ = "payment_allocations"

    receipt_id: Mapped[UUID] = mapped_column(ForeignKey("payment_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("customer_invoices.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    receipt: Mapped["PaymentReceipt"] = relationship("PaymentReceipt", back_populates="allocations")
    invoice: Mapped["CustomerInvoice"] = relationship("CustomerInvoice")


class InvoiceDispute(Base, TimestampMixin):
    """
    Record of a disputed customer invoice.
    """
    __tablename__ = "invoice_disputes"

    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("customer_invoices.id"), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False) # open, resolved
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    invoice: Mapped["CustomerInvoice"] = relationship("CustomerInvoice")
    opened_by: Mapped["User"] = relationship("User", foreign_keys=[opened_by_id])
    resolved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_id])


# =============================================================================
# SHIPPING AND FULFILLMENT (for erpStarz import compatibility)
# =============================================================================


class Shipment(Base, TimestampMixin, AuditMixin):
    """
    Outbound shipment to customer.
    Maps from erpStarz `shipment` table.
    """
    __tablename__ = "shipments"

    shipment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    sales_order_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("sales_orders.id"), nullable=True, index=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    
    ship_from_warehouse_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    ship_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    carrier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    service_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ground, express, overnight
    
    ship_to_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ship_to_address: Mapped[str] = mapped_column(Text, nullable=False)
    ship_to_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ship_to_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ship_to_postal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ship_to_country: Mapped[str] = mapped_column(String(100), default="Tunisia", nullable=False)
    
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    weight_uom: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # kg, lb
    
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, picked, packed, shipped, delivered, canceled
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    sales_order: Mapped[Optional["SalesOrder"]] = relationship("SalesOrder")
    account: Mapped["Account"] = relationship("Account")
    lines: Mapped[list["ShipmentLine"]] = relationship("ShipmentLine", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentLine(Base, TimestampMixin):
    """
    Line item in a shipment.
    Maps from erpStarz `shipment_item` table.
    """
    __tablename__ = "shipment_lines"

    shipment_id: Mapped[UUID] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    sales_order_line_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("sales_order_lines.id"), nullable=True)
    
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_shipped: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), default="EA", nullable=False)
    
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # For legacy import tracking
    legacy_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="lines")
    sales_order_line: Mapped[Optional["SalesOrderLine"]] = relationship("SalesOrderLine")
