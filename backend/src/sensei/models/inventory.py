"""
Inventory models.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Boolean,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from sensei.models.product import Product
    from sensei.models.user import User


class Warehouse(Base, TimestampMixin, AuditMixin):
    """
    Physical warehouse.
    """
    __tablename__ = "inventory_warehouses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    locations: Mapped[list["Location"]] = relationship("Location", back_populates="warehouse")


class Location(Base, TimestampMixin, AuditMixin):
    """
    Storage location within a warehouse (hierarchical).
    """
    __tablename__ = "inventory_locations"

    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_warehouses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("inventory_locations.id"), nullable=True)
    location_type: Mapped[str] = mapped_column(String(50), default="internal", nullable=False) # internal, view, supplier, customer, inventory

    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="locations")
    parent: Mapped[Optional["Location"]] = relationship("Location", remote_side="Location.id", backref="children")


class InventoryLevel(Base, TimestampMixin, AuditMixin):
    """
    Inventory level for an item at a specific location.
    """
    __tablename__ = "inventory_levels"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_locations.id"), nullable=False, index=True)
    
    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    quantity_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    
    @property
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved

    last_counted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product")
    location: Mapped["Location"] = relationship("Location")


class StockMove(Base, TimestampMixin, AuditMixin):
    """
    Record of stock movement between locations.
    """
    __tablename__ = "inventory_stock_moves"

    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    source_location_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_locations.id"), nullable=False)
    destination_location_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_locations.id"), nullable=False)
    
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="done", nullable=False) # draft, waiting, confirmed, done, cancelled
    
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. PO number, SO number
    
    product: Mapped["Product"] = relationship("Product")
    source_location: Mapped["Location"] = relationship("Location", foreign_keys=[source_location_id])
    destination_location: Mapped["Location"] = relationship("Location", foreign_keys=[destination_location_id])


class ValuationLayer(Base, TimestampMixin):
    """
    Financial valuation record for a stock move.
    """
    __tablename__ = "inventory_valuation_layers"

    stock_move_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_stock_moves.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    product: Mapped["Product"] = relationship("Product")
    stock_move: Mapped["StockMove"] = relationship("StockMove")
