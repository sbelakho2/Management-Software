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
from sqlalchemy.dialects.postgresql import JSONB
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
    
    # LPN support
    lpn_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wms_license_plates.id"), nullable=True, index=True)
    
    @property
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved

    last_counted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product")
    location: Mapped["Location"] = relationship("Location")
    lpn: Mapped[Optional["LicensePlate"]] = relationship("LicensePlate")


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
    
    # LPN support
    lpn_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wms_license_plates.id"), nullable=True, index=True)
    
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. PO number, SO number
    
    product: Mapped["Product"] = relationship("Product")
    source_location: Mapped["Location"] = relationship("Location", foreign_keys=[source_location_id])
    destination_location: Mapped["Location"] = relationship("Location", foreign_keys=[destination_location_id])
    lpn: Mapped[Optional["LicensePlate"]] = relationship("LicensePlate")


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


class LicensePlate(Base, TimestampMixin, AuditMixin):
    """
    WMS License Plate (LPN) for tracking containers, pallets, or totes.
    """
    __tablename__ = "wms_license_plates"

    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, consumed, lost, damaged
    
    # Current location
    location_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("inventory_locations.id"), nullable=True)
    parent_lpn_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("wms_license_plates.id"), nullable=True)
    
    # Contents (can be multiple products in one container)
    # For simplicity, we can link items to LPNs in inventory_levels or a separate table.
    # erpStarz seems to have product/quantity directly on LPN or via relationships.
    
    location: Mapped[Optional["Location"]] = relationship("Location")
    parent_lpn: Mapped[Optional["LicensePlate"]] = relationship("LicensePlate", remote_side="LicensePlate.id", backref="child_lpns")


class WmsWorkstation(Base, TimestampMixin, AuditMixin):
    """
    WMS Workstation - PC + Scanner combo for warehouse operations.
    """
    __tablename__ = "wms_workstations"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_warehouses.id"), nullable=False)
    station_type: Mapped[str] = mapped_column(String(50), nullable=False) # receiving, shipping, picking, counting
    
    # Hardware details
    scanner_model: Mapped[str] = mapped_column(String(50), default="Tera HW0002-O")
    scanner_serial: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    connection_type: Mapped[str] = mapped_column(String(20), default="usb") # usb, wireless
    pc_hostname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class WmsDevice(Base, TimestampMixin, AuditMixin):
    """
    WMS Handheld or mobile device.
    """
    __tablename__ = "wms_devices"

    device_identifier: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    device_type: Mapped[str] = mapped_column(String(40), nullable=False) # handheld, tablet, fork-mount
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    
    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_warehouses.id"), nullable=False)
    
    # JSON capabilities (matching erpStarz)
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
