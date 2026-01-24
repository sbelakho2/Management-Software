"""
Product, BOM, and Routing models for production management.

Products represent manufactured items with their bill of materials
and routing (sequence of operations).
"""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from sensei.models.work_center import Station
    from sensei.models.work_order import WorkOrder
    from sensei.models.standard_work import StandardWork
    from sensei.models.andon import AndonEvent
    from sensei.models.kanban import KanbanCard
    from sensei.models.quality import NonConformance, InspectionPlan
    from sensei.models.training import SkillRequirement


class ProductStatus(enum.Enum):
    """Status of a product."""

    ACTIVE = "active"
    OBSOLETE = "obsolete"
    PROTOTYPE = "prototype"
    DISCONTINUED = "discontinued"
    PENDING_APPROVAL = "pending_approval"


class UnitOfMeasure(enum.Enum):
    """Standard units of measure."""

    EACH = "each"
    KILOGRAM = "kg"
    GRAM = "g"
    LITER = "l"
    MILLILITER = "ml"
    METER = "m"
    CENTIMETER = "cm"
    MILLIMETER = "mm"
    SQUARE_METER = "m2"
    CUBIC_METER = "m3"
    PIECE = "pc"
    SET = "set"
    BOX = "box"
    PALLET = "pallet"


class Product(Base, TimestampMixin, AuditMixin, SoftDeleteMixin):
    """
    Product master data for manufactured items.

    Products have versions (revisions), bill of materials,
    and routing definitions for production.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # SKU/Stock Keeping Unit
    revision: Mapped[str] = mapped_column(String(20), nullable=False, default="A")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Product category

    # Classification
    product_family: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    product_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Units and specifications
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure), nullable=False, default=UnitOfMeasure.EACH
    )
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    dimensions: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # L x W x H

    # Cost and pricing
    standard_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4), nullable=True
    )  # Alternative unit cost field
    standard_labor_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )

    # Lead times
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    setup_time_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True
    )

    # Status
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus),
        nullable=False,
        default=ProductStatus.ACTIVE,
        index=True,
    )

    # Relationships
    bom_items: Mapped[list["BOMItem"]] = relationship(
        "BOMItem",
        back_populates="product",
        cascade="all, delete-orphan",
        foreign_keys="BOMItem.product_id",
    )
    routings: Mapped[list["Routing"]] = relationship(
        "Routing", back_populates="product", cascade="all, delete-orphan"
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="product"
    )
    standard_works: Mapped[list["StandardWork"]] = relationship(
        "StandardWork", back_populates="product"
    )
    andon_events: Mapped[list["AndonEvent"]] = relationship(
        "AndonEvent", back_populates="product"
    )
    kanban_cards: Mapped[list["KanbanCard"]] = relationship(
        "KanbanCard", back_populates="product"
    )
    skill_requirements: Mapped[list["SkillRequirement"]] = relationship(
        "SkillRequirement", back_populates="product"
    )
    non_conformances: Mapped[list["NonConformance"]] = relationship(
        "NonConformance", back_populates="product"
    )
    inspection_plans: Mapped[list["InspectionPlan"]] = relationship(
        "InspectionPlan", back_populates="product"
    )

    __table_args__ = (
        UniqueConstraint(
            "part_number", "revision", name="uq_product_part_revision"
        ),
        CheckConstraint("lead_time_days >= 0", name="ck_product_lead_time_nonnegative"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, part_number='{self.part_number}', rev='{self.revision}')>"

    @property
    def full_part_number(self) -> str:
        """Return full part number with revision."""
        return f"{self.part_number}-{self.revision}"

    @property
    def is_active(self) -> bool:
        """Check if product is active for production."""
        return self.status == ProductStatus.ACTIVE

    @property
    def total_routing_time_seconds(self) -> int:
        """Calculate total standard time for all routing steps."""
        return sum(r.standard_time_seconds for r in self.routings)


class BOMItem(Base, TimestampMixin, AuditMixin):
    """
    Bill of Materials line item.

    Defines components and their quantities required
    to manufacture a product.
    """

    __tablename__ = "bom_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Parent product
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )

    # Component details
    component_part_number: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    component_product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=True, index=True
    )
    component_description: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Quantity and unit
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("1.0")
    )
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure), nullable=False, default=UnitOfMeasure.EACH
    )

    # Position and classification
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    find_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # Reference designator

    # Flags
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_phantom: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # Phantom/subassembly
    is_alternate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Scrap allowance
    scrap_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.0")
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="bom_items",
        foreign_keys=[product_id],
    )
    component_product: Mapped[Optional["Product"]] = relationship(
        "Product",
        foreign_keys=[component_product_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id", "component_part_number", "position",
            name="uq_bom_product_component_position"
        ),
        CheckConstraint("quantity > 0", name="ck_bom_quantity_positive"),
        CheckConstraint(
            "scrap_factor >= 0 AND scrap_factor < 1",
            name="ck_bom_scrap_factor_range"
        ),
    )

    def __repr__(self) -> str:
        return f"<BOMItem(product_id={self.product_id}, component='{self.component_part_number}', qty={self.quantity})>"

    @property
    def extended_quantity(self) -> Decimal:
        """Calculate quantity including scrap allowance."""
        return self.quantity * (1 + self.scrap_factor)


class Routing(Base, TimestampMixin, AuditMixin):
    """
    Production routing step for a product.

    Defines the sequence of operations and the stations
    where operations are performed.
    """

    __tablename__ = "routings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]

    # Product and sequence
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # Operation details
    operation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Station assignment
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id"), nullable=False, index=True
    )

    # Time standards (in seconds)
    standard_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    setup_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    move_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    queue_time_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # Labor requirements
    labor_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    crew_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Flags
    is_subcontracted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_inspection: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", back_populates="routings"
    )
    station: Mapped["Station"] = relationship(
        "Station", back_populates="routings"
    )
    work_order_operations: Mapped[list["WorkOrderOperation"]] = relationship(
        "WorkOrderOperation", back_populates="routing"
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id", "sequence", name="uq_routing_product_sequence"
        ),
        CheckConstraint("sequence > 0", name="ck_routing_sequence_positive"),
        CheckConstraint(
            "standard_time_seconds > 0", name="ck_routing_standard_time_positive"
        ),
        CheckConstraint(
            "setup_time_seconds >= 0", name="ck_routing_setup_time_nonnegative"
        ),
        CheckConstraint("crew_size > 0", name="ck_routing_crew_size_positive"),
    )

    def __repr__(self) -> str:
        return f"<Routing(product_id={self.product_id}, seq={self.sequence}, op='{self.operation_name}')>"

    @property
    def total_time_seconds(self) -> int:
        """Calculate total time including setup, operation, and move."""
        return (
            self.setup_time_seconds +
            self.standard_time_seconds +
            self.move_time_seconds +
            self.queue_time_seconds
        )

    @property
    def time_per_unit_seconds(self) -> int:
        """Time per unit excluding setup."""
        return self.standard_time_seconds


# Forward references for type checking
from sensei.models.work_order import WorkOrderOperation
