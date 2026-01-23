"""
SQLAlchemy models for starzERP (MySQL).
These match the schema of the erpStarz project.
"""

from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class StarzBase(DeclarativeBase):
    """Base class for starzERP models."""
    pass

class StarzWarehouse(StarzBase):
    __tablename__ = "wms_warehouse"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)

class StarzWmsDevice(StarzBase):
    __tablename__ = "wms_device"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_identifier: Mapped[str] = mapped_column("device_identifier", String(50))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column("device_type", String(50))
    status: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    capabilities: Mapped[Optional[dict]] = mapped_column(JSON)
    registered_at: Mapped[Optional[datetime]] = mapped_column("registered_at", DateTime)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column("last_seen_at", DateTime)
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)

class StarzWmsWorkstation(StarzBase):
    __tablename__ = "wms_workstation"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workstation_code: Mapped[str] = mapped_column("workstation_code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    station_type: Mapped[str] = mapped_column("station_type", String(50))
    scanner_model: Mapped[str] = mapped_column("scanner_model", String(50))
    scanner_serial: Mapped[Optional[str]] = mapped_column("scanner_serial", String(100))
    connection_type: Mapped[str] = mapped_column("connection_type", String(20))
    pc_hostname: Mapped[Optional[str]] = mapped_column("pc_hostname", String(100))
    current_user: Mapped[Optional[str]] = mapped_column("current_user", String(100))
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column("registered_at", DateTime)
    last_activity: Mapped[datetime] = mapped_column("last_activity", DateTime)
    api_token_hash: Mapped[Optional[str]] = mapped_column("api_token_hash", String(255))
    token_expires_at: Mapped[Optional[datetime]] = mapped_column("token_expires_at", DateTime)

class StarzArticle(StarzBase):
    __tablename__ = "article"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_reference: Mapped[str] = mapped_column("codeReference", String(100))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    prix: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(255))
    unit_id: Mapped[int] = mapped_column("unit_id", Integer)

class StarzLicensePlate(StarzBase):
    __tablename__ = "wms_license_plate"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column("code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    location_id: Mapped[Optional[int]] = mapped_column("location_id", Integer)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    item_sku: Mapped[Optional[str]] = mapped_column("item_sku", String(120))
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    uom: Mapped[Optional[str]] = mapped_column(String(10))
    created_at: Mapped[Optional[datetime]] = mapped_column("created_at", DateTime)
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)

class StarzStockLocation(StarzBase):
    __tablename__ = "wms_stock_location"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column("code", String(50))
    warehouse_id: Mapped[int] = mapped_column("warehouse_id", Integer)
    type: Mapped[str] = mapped_column("type", String(50))
    label: Mapped[Optional[str]] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)
