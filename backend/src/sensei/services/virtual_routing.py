"""
Virtual Routing Service.

Provides virtual routing assumptions for quoting and costing purposes.
A "Virtual Routing" is a routing definition used for cost estimation
when actual production routings don't exist yet.

Virtual routings allow:
- Estimation of labor costs for new products
- What-if analysis for routing changes
- Template-based routing creation
- Quick costing without full routing setup
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class OperationType(str, Enum):
    """Standard operation types for virtual routing."""
    
    # Manufacturing operations
    SETUP = "setup"
    MACHINING = "machining"
    ASSEMBLY = "assembly"
    WELDING = "welding"
    PAINTING = "painting"
    FINISHING = "finishing"
    
    # Quality operations
    INSPECTION = "inspection"
    TESTING = "testing"
    QC_CHECK = "qc_check"
    
    # Material handling
    MATERIAL_PREP = "material_prep"
    PACKAGING = "packaging"
    SHIPPING = "shipping"
    
    # Subcontracting
    SUBCONTRACT = "subcontract"
    TREATMENT = "treatment"  # Heat treatment, plating, etc.
    
    # Generic
    CUSTOM = "custom"


class CostBasis(str, Enum):
    """How the cost for an operation is calculated."""
    
    PER_UNIT = "per_unit"              # Cost per part/unit
    PER_HOUR = "per_hour"              # Hourly rate
    PER_BATCH = "per_batch"            # Cost per batch/lot
    FIXED = "fixed"                     # Fixed cost regardless of quantity
    PERCENTAGE = "percentage"           # Percentage of material cost


class RoutingSource(str, Enum):
    """Source of the virtual routing."""
    
    MANUAL = "manual"                   # Created manually for quote
    TEMPLATE = "template"               # Created from a template
    CLONED = "cloned"                   # Cloned from actual routing
    SIMILAR_PART = "similar_part"       # Based on similar part routing
    AI_ESTIMATED = "ai_estimated"       # AI/ML estimated routing


@dataclass
class VirtualOperation:
    """A single operation in a virtual routing."""
    
    id: UUID
    sequence: int
    operation_type: OperationType
    operation_name: str
    description: str | None = None
    
    # Station/Work center
    work_center_id: UUID | None = None
    work_center_name: str | None = None
    
    # Time estimates
    setup_time_minutes: Decimal = Decimal("0")
    run_time_minutes: Decimal = Decimal("0")  # Per unit
    move_time_minutes: Decimal = Decimal("0")
    queue_time_minutes: Decimal = Decimal("0")
    
    # Labor
    crew_size: int = 1
    labor_rate_per_hour: Decimal = Decimal("0")
    
    # Overhead
    overhead_rate_per_hour: Decimal = Decimal("0")
    machine_rate_per_hour: Decimal = Decimal("0")
    
    # Cost calculation
    cost_basis: CostBasis = CostBasis.PER_UNIT
    fixed_cost: Decimal = Decimal("0")
    cost_percentage: Decimal = Decimal("0")  # For PERCENTAGE cost basis
    
    # Flags
    is_subcontracted: bool = False
    is_optional: bool = False
    is_parallel: bool = False  # Can run in parallel with previous op
    
    # Subcontract details
    subcontract_vendor_id: UUID | None = None
    subcontract_cost: Decimal = Decimal("0")
    subcontract_lead_days: int = 0
    
    # Scrap/yield
    scrap_rate: Decimal = Decimal("0")  # 0.05 = 5% scrap
    
    # Notes
    notes: str | None = None
    
    def calculate_time_per_unit(self, batch_size: int = 1) -> Decimal:
        """Calculate total time per unit including setup amortization."""
        if batch_size <= 0:
            batch_size = 1
        
        setup_per_unit = self.setup_time_minutes / Decimal(batch_size)
        return (
            setup_per_unit 
            + self.run_time_minutes 
            + self.move_time_minutes 
            + self.queue_time_minutes
        )
    
    def calculate_labor_cost(
        self,
        quantity: int,
        batch_size: int = 1,
    ) -> Decimal:
        """Calculate labor cost for given quantity."""
        if self.cost_basis == CostBasis.FIXED:
            return self.fixed_cost
        
        if self.cost_basis == CostBasis.PER_BATCH:
            num_batches = (quantity + batch_size - 1) // batch_size
            return self.fixed_cost * num_batches
        
        if self.cost_basis == CostBasis.PERCENTAGE:
            # This requires material cost input, return 0 here
            return Decimal("0")
        
        # Per unit or per hour
        total_time = self.calculate_time_per_unit(batch_size) * quantity
        hours = total_time / Decimal("60")
        return (hours * self.labor_rate_per_hour * self.crew_size).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
    
    def calculate_overhead_cost(
        self,
        quantity: int,
        batch_size: int = 1,
    ) -> Decimal:
        """Calculate overhead/machine cost for given quantity."""
        total_time = self.calculate_time_per_unit(batch_size) * quantity
        hours = total_time / Decimal("60")
        overhead = (hours * self.overhead_rate_per_hour).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        machine = (hours * self.machine_rate_per_hour).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        return overhead + machine
    
    def calculate_total_cost(
        self,
        quantity: int,
        batch_size: int = 1,
        material_cost: Decimal = Decimal("0"),
    ) -> Decimal:
        """Calculate total operation cost including all elements."""
        if self.is_subcontracted:
            return self.subcontract_cost * quantity
        
        if self.cost_basis == CostBasis.PERCENTAGE:
            return (material_cost * self.cost_percentage / 100).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
        
        labor = self.calculate_labor_cost(quantity, batch_size)
        overhead = self.calculate_overhead_cost(quantity, batch_size)
        
        # Apply scrap factor
        scrap_multiplier = 1 + self.scrap_rate
        return ((labor + overhead) * scrap_multiplier).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )


@dataclass
class VirtualRouting:
    """A virtual routing for cost estimation."""
    
    id: UUID
    name: str
    description: str | None = None
    source: RoutingSource = RoutingSource.MANUAL
    
    # Reference to what this routing is for
    quote_id: UUID | None = None
    quote_line_item_id: UUID | None = None
    product_id: UUID | None = None
    opportunity_id: UUID | None = None
    
    # If based on template or actual routing
    template_id: UUID | None = None
    source_routing_id: int | None = None  # Actual routing.id if cloned
    
    # Operations
    operations: list[VirtualOperation] = field(default_factory=list)
    
    # Default values for new operations
    default_labor_rate: Decimal = Decimal("25.00")
    default_overhead_rate: Decimal = Decimal("35.00")
    default_machine_rate: Decimal = Decimal("15.00")
    
    # Assumptions
    batch_size: int = 1
    learning_curve_factor: Decimal = Decimal("1.0")  # 1.0 = no learning curve
    
    # Metadata
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    
    # Notes
    notes: str | None = None
    assumptions: dict[str, Any] = field(default_factory=dict)
    
    def add_operation(
        self,
        operation_type: OperationType,
        operation_name: str,
        sequence: int | None = None,
        **kwargs: Any,
    ) -> VirtualOperation:
        """Add a new operation to the routing."""
        if sequence is None:
            sequence = len(self.operations) + 1
        
        # Apply default rates if not provided
        if "labor_rate_per_hour" not in kwargs:
            kwargs["labor_rate_per_hour"] = self.default_labor_rate
        if "overhead_rate_per_hour" not in kwargs:
            kwargs["overhead_rate_per_hour"] = self.default_overhead_rate
        if "machine_rate_per_hour" not in kwargs:
            kwargs["machine_rate_per_hour"] = self.default_machine_rate
        
        operation = VirtualOperation(
            id=uuid4(),
            sequence=sequence,
            operation_type=operation_type,
            operation_name=operation_name,
            **kwargs,
        )
        
        self.operations.append(operation)
        self._renumber_sequences()
        self.updated_at = datetime.now(timezone.utc)
        
        return operation
    
    def remove_operation(self, operation_id: UUID) -> bool:
        """Remove an operation from the routing."""
        for i, op in enumerate(self.operations):
            if op.id == operation_id:
                self.operations.pop(i)
                self._renumber_sequences()
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False
    
    def _renumber_sequences(self) -> None:
        """Renumber operation sequences to be consecutive."""
        self.operations.sort(key=lambda o: o.sequence)
        for i, op in enumerate(self.operations):
            op.sequence = (i + 1) * 10  # Leave gaps for insertion
    
    def get_operation(self, operation_id: UUID) -> VirtualOperation | None:
        """Get an operation by ID."""
        for op in self.operations:
            if op.id == operation_id:
                return op
        return None
    
    def calculate_total_time_minutes(self, quantity: int = 1) -> Decimal:
        """Calculate total routing time for given quantity."""
        total = Decimal("0")
        for op in self.operations:
            if not op.is_optional:
                total += op.calculate_time_per_unit(self.batch_size) * quantity
        return total
    
    def calculate_lead_time_days(
        self,
        quantity: int,
        hours_per_day: Decimal = Decimal("8"),
    ) -> int:
        """Calculate estimated lead time in days."""
        total_minutes = self.calculate_total_time_minutes(quantity)
        hours = total_minutes / Decimal("60")
        days = hours / hours_per_day
        
        # Add subcontract lead times (assume sequential)
        subcontract_days = sum(
            op.subcontract_lead_days 
            for op in self.operations 
            if op.is_subcontracted
        )
        
        return int(days.quantize(Decimal("1"), ROUND_HALF_UP)) + subcontract_days
    
    def calculate_costs(
        self,
        quantity: int,
        material_cost: Decimal = Decimal("0"),
    ) -> dict[str, Decimal]:
        """Calculate detailed costs for given quantity."""
        labor_cost = Decimal("0")
        overhead_cost = Decimal("0")
        subcontract_cost = Decimal("0")
        
        for op in self.operations:
            if op.is_optional:
                continue
            
            if op.is_subcontracted:
                subcontract_cost += op.subcontract_cost * quantity
            else:
                labor_cost += op.calculate_labor_cost(quantity, self.batch_size)
                overhead_cost += op.calculate_overhead_cost(quantity, self.batch_size)
        
        # Apply learning curve
        if self.learning_curve_factor != Decimal("1.0"):
            labor_cost = (labor_cost * self.learning_curve_factor).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
        
        total_cost = labor_cost + overhead_cost + subcontract_cost
        
        return {
            "labor_cost": labor_cost,
            "overhead_cost": overhead_cost,
            "subcontract_cost": subcontract_cost,
            "total_manufacturing_cost": total_cost,
            "cost_per_unit": (
                total_cost / quantity 
                if quantity > 0 
                else Decimal("0")
            ).quantize(Decimal("0.0001"), ROUND_HALF_UP),
        }


@dataclass
class RoutingTemplate:
    """A template for creating virtual routings."""
    
    id: UUID
    name: str
    description: str | None = None
    
    # Template category
    category: str | None = None  # e.g., "machining", "assembly", "welding"
    
    # Template operations (without IDs - they get assigned on use)
    operations: list[dict[str, Any]] = field(default_factory=list)
    
    # Default rates
    default_labor_rate: Decimal = Decimal("25.00")
    default_overhead_rate: Decimal = Decimal("35.00")
    default_machine_rate: Decimal = Decimal("15.00")
    
    # Usage tracking
    usage_count: int = 0
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    
    is_active: bool = True


class VirtualRoutingService(PersistentServiceMixin):
    """Service for managing virtual routings."""

    SERVICE_NAME = "virtual_routing"
    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._routings: dict[UUID, VirtualRouting] = {}
        self._templates: dict[UUID, RoutingTemplate] = {}
        self._work_center_rates: dict[UUID, dict[str, Decimal]] = {}
        self._state_loaded = False
        
        # Initialize with common templates
        self._init_default_templates()

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        routings_data = await self.load_state(self._DEFAULT_TENANT_ID, "routings")
        templates_data = await self.load_state(self._DEFAULT_TENANT_ID, "templates")
        work_center_rates_data = await self.load_state(self._DEFAULT_TENANT_ID, "work_center_rates")

        if routings_data is None and templates_data is None and work_center_rates_data is None:
            self._state_loaded = True
            return

        if routings_data is not None:
            self._routings = {
                UUID(routing_id): decode_dataclass(routing, VirtualRouting)
                for routing_id, routing in routings_data.items()
            }
        if templates_data is not None:
            self._templates = {
                UUID(template_id): decode_dataclass(template, RoutingTemplate)
                for template_id, template in templates_data.items()
            }
        if work_center_rates_data is not None:
            self._work_center_rates = {
                UUID(center_id): {k: Decimal(v) for k, v in rates.items()}
                for center_id, rates in work_center_rates_data.items()
            }

        self._state_loaded = True

    async def persist_all(self) -> None:
        routings_data = {
            str(routing_id): encode_dataclass(routing) for routing_id, routing in self._routings.items()
        }
        templates_data = {
            str(template_id): encode_dataclass(template) for template_id, template in self._templates.items()
        }
        work_center_rates_data = {
            str(center_id): {k: str(v) for k, v in rates.items()}
            for center_id, rates in self._work_center_rates.items()
        }

        await self.save_state(self._DEFAULT_TENANT_ID, "routings", routings_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "templates", templates_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "work_center_rates", work_center_rates_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()
    
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._routings.clear()
        self._templates.clear()
        self._work_center_rates.clear()
        self._init_default_templates()

    async def clear_async(self) -> None:
        await self._ensure_loaded()
        self.clear()
        await self.persist_all()
    
    def _init_default_templates(self) -> None:
        """Initialize with some default routing templates."""
        # Simple machining template
        machining_id = uuid4()
        self._templates[machining_id] = RoutingTemplate(
            id=machining_id,
            name="Simple Machining",
            description="Basic machining routing with setup, operation, and inspection",
            category="machining",
            operations=[
                {
                    "operation_type": OperationType.SETUP,
                    "operation_name": "Setup",
                    "setup_time_minutes": Decimal("15"),
                    "run_time_minutes": Decimal("0"),
                },
                {
                    "operation_type": OperationType.MACHINING,
                    "operation_name": "CNC Machining",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("5"),
                },
                {
                    "operation_type": OperationType.INSPECTION,
                    "operation_name": "First Article Inspection",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("2"),
                },
            ],
        )
        
        # Assembly template
        assembly_id = uuid4()
        self._templates[assembly_id] = RoutingTemplate(
            id=assembly_id,
            name="Assembly Process",
            description="Standard assembly routing with prep, assembly, and test",
            category="assembly",
            operations=[
                {
                    "operation_type": OperationType.MATERIAL_PREP,
                    "operation_name": "Material Preparation",
                    "setup_time_minutes": Decimal("10"),
                    "run_time_minutes": Decimal("1"),
                },
                {
                    "operation_type": OperationType.ASSEMBLY,
                    "operation_name": "Assembly",
                    "setup_time_minutes": Decimal("5"),
                    "run_time_minutes": Decimal("10"),
                },
                {
                    "operation_type": OperationType.TESTING,
                    "operation_name": "Functional Test",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("3"),
                },
                {
                    "operation_type": OperationType.PACKAGING,
                    "operation_name": "Packaging",
                    "setup_time_minutes": Decimal("0"),
                    "run_time_minutes": Decimal("2"),
                },
            ],
        )
    
    # =========================================================================
    # Work Center Rate Management
    # =========================================================================
    
    def set_work_center_rates(
        self,
        work_center_id: UUID,
        labor_rate: Decimal,
        overhead_rate: Decimal,
        machine_rate: Decimal,
    ) -> None:
        """Set standard rates for a work center."""
        self._work_center_rates[work_center_id] = {
            "labor_rate": labor_rate,
            "overhead_rate": overhead_rate,
            "machine_rate": machine_rate,
        }

    async def set_work_center_rates_async(self, **kwargs: Any) -> None:
        await self._ensure_loaded()
        self.set_work_center_rates(**kwargs)
        await self.persist_all()
    
    def get_work_center_rates(self, work_center_id: UUID) -> dict[str, Decimal] | None:
        """Get rates for a work center."""
        return self._work_center_rates.get(work_center_id)

    async def get_work_center_rates_async(self, work_center_id: UUID) -> dict[str, Decimal] | None:
        await self._ensure_loaded()
        return self.get_work_center_rates(work_center_id)
    
    # =========================================================================
    # Virtual Routing CRUD
    # =========================================================================
    
    def create_routing(
        self,
        name: str,
        description: str | None = None,
        quote_id: UUID | None = None,
        quote_line_item_id: UUID | None = None,
        product_id: UUID | None = None,
        created_by: UUID | None = None,
        **kwargs: Any,
    ) -> VirtualRouting:
        """Create a new virtual routing."""
        routing_id = uuid4()
        routing = VirtualRouting(
            id=routing_id,
            name=name,
            description=description,
            source=RoutingSource.MANUAL,
            quote_id=quote_id,
            quote_line_item_id=quote_line_item_id,
            product_id=product_id,
            created_by=created_by,
            **kwargs,
        )
        self._routings[routing_id] = routing
        return routing

    async def create_routing_async(self, **kwargs: Any) -> VirtualRouting:
        await self._ensure_loaded()
        routing = self.create_routing(**kwargs)
        await self.persist_all()
        return routing
    
    def create_from_template(
        self,
        template_id: UUID,
        name: str,
        quote_id: UUID | None = None,
        quote_line_item_id: UUID | None = None,
        created_by: UUID | None = None,
        time_multiplier: Decimal = Decimal("1.0"),
    ) -> VirtualRouting | None:
        """Create a virtual routing from a template."""
        template = self._templates.get(template_id)
        if template is None:
            return None
        
        routing = VirtualRouting(
            id=uuid4(),
            name=name,
            description=f"Created from template: {template.name}",
            source=RoutingSource.TEMPLATE,
            quote_id=quote_id,
            quote_line_item_id=quote_line_item_id,
            template_id=template_id,
            created_by=created_by,
            default_labor_rate=template.default_labor_rate,
            default_overhead_rate=template.default_overhead_rate,
            default_machine_rate=template.default_machine_rate,
        )

        # Add operations from template
        for op_data in template.operations:
            op_type = op_data.get("operation_type", OperationType.CUSTOM)
            op_name = op_data.get("operation_name", "Operation")
            
            # Apply time multiplier
            setup_time = op_data.get("setup_time_minutes", Decimal("0"))
            run_time = op_data.get("run_time_minutes", Decimal("0"))
            
            if time_multiplier != Decimal("1.0"):
                setup_time = (setup_time * time_multiplier).quantize(
                    Decimal("0.01"), ROUND_HALF_UP
                )
                run_time = (run_time * time_multiplier).quantize(
                    Decimal("0.01"), ROUND_HALF_UP
                )
            
            routing.add_operation(
                operation_type=op_type,
                operation_name=op_name,
                description=op_data.get("description"),
                setup_time_minutes=setup_time,
                run_time_minutes=run_time,
                move_time_minutes=op_data.get("move_time_minutes", Decimal("0")),
                queue_time_minutes=op_data.get("queue_time_minutes", Decimal("0")),
                crew_size=op_data.get("crew_size", 1),
                is_subcontracted=op_data.get("is_subcontracted", False),
            )
        
        # Increment template usage count
        template.usage_count += 1
        
        self._routings[routing.id] = routing
        return routing

    async def create_from_template_async(self, **kwargs: Any) -> VirtualRouting | None:
        await self._ensure_loaded()
        routing = self.create_from_template(**kwargs)
        await self.persist_all()
        return routing
    
    def clone_routing(
        self,
        source_routing_id: UUID,
        new_name: str,
        quote_id: UUID | None = None,
        quote_line_item_id: UUID | None = None,
    ) -> VirtualRouting | None:
        """Clone an existing virtual routing."""
        source = self._routings.get(source_routing_id)
        if source is None:
            return None
        
        new_routing = VirtualRouting(
            id=uuid4(),
            name=new_name,
            description=f"Cloned from: {source.name}",
            source=RoutingSource.CLONED,
            quote_id=quote_id,
            quote_line_item_id=quote_line_item_id,
            product_id=source.product_id,
            default_labor_rate=source.default_labor_rate,
            default_overhead_rate=source.default_overhead_rate,
            default_machine_rate=source.default_machine_rate,
            batch_size=source.batch_size,
            learning_curve_factor=source.learning_curve_factor,
            assumptions=source.assumptions.copy(),
        )

        # Clone operations
        for op in source.operations:
            new_routing.add_operation(
                operation_type=op.operation_type,
                operation_name=op.operation_name,
                description=op.description,
                work_center_id=op.work_center_id,
                work_center_name=op.work_center_name,
                setup_time_minutes=op.setup_time_minutes,
                run_time_minutes=op.run_time_minutes,
                move_time_minutes=op.move_time_minutes,
                queue_time_minutes=op.queue_time_minutes,
                crew_size=op.crew_size,
                labor_rate_per_hour=op.labor_rate_per_hour,
                overhead_rate_per_hour=op.overhead_rate_per_hour,
                machine_rate_per_hour=op.machine_rate_per_hour,
                cost_basis=op.cost_basis,
                fixed_cost=op.fixed_cost,
                cost_percentage=op.cost_percentage,
                is_subcontracted=op.is_subcontracted,
                is_optional=op.is_optional,
                is_parallel=op.is_parallel,
                subcontract_vendor_id=op.subcontract_vendor_id,
                subcontract_cost=op.subcontract_cost,
                subcontract_lead_days=op.subcontract_lead_days,
                scrap_rate=op.scrap_rate,
                notes=op.notes,
            )
        
        self._routings[new_routing.id] = new_routing
        return new_routing

    async def clone_routing_async(self, **kwargs: Any) -> VirtualRouting | None:
        await self._ensure_loaded()
        routing = self.clone_routing(**kwargs)
        await self.persist_all()
        return routing
    
    def get_routing(self, routing_id: UUID) -> VirtualRouting | None:
        """Get a virtual routing by ID."""
        return self._routings.get(routing_id)

    async def get_routing_async(self, routing_id: UUID) -> VirtualRouting | None:
        await self._ensure_loaded()
        return self.get_routing(routing_id)
    
    def list_routings(
        self,
        quote_id: UUID | None = None,
        product_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> list[VirtualRouting]:
        """List virtual routings with optional filtering."""
        routings = list(self._routings.values())
        
        if quote_id is not None:
            routings = [r for r in routings if r.quote_id == quote_id]
        
        if product_id is not None:
            routings = [r for r in routings if r.product_id == product_id]
        
        if created_by is not None:
            routings = [r for r in routings if r.created_by == created_by]
        
        return sorted(routings, key=lambda r: r.created_at, reverse=True)

    async def list_routings_async(self, **kwargs: Any) -> list[VirtualRouting]:
        await self._ensure_loaded()
        return self.list_routings(**kwargs)
    
    def delete_routing(self, routing_id: UUID) -> bool:
        """Delete a virtual routing."""
        if routing_id in self._routings:
            del self._routings[routing_id]
            return True
        return False

    async def delete_routing_async(self, routing_id: UUID) -> bool:
        await self._ensure_loaded()
        result = self.delete_routing(routing_id)
        await self.persist_all()
        return result
    
    # =========================================================================
    # Template Management
    # =========================================================================
    
    def create_template(
        self,
        name: str,
        description: str | None = None,
        category: str | None = None,
        operations: list[dict[str, Any]] | None = None,
        created_by: UUID | None = None,
    ) -> RoutingTemplate:
        """Create a new routing template."""
        template_id = uuid4()
        template = RoutingTemplate(
            id=template_id,
            name=name,
            description=description,
            category=category,
            operations=operations or [],
            created_by=created_by,
        )
        self._templates[template_id] = template
        return template

    async def create_template_async(self, **kwargs: Any) -> RoutingTemplate:
        await self._ensure_loaded()
        template = self.create_template(**kwargs)
        await self.persist_all()
        return template
    
    def create_template_from_routing(
        self,
        routing_id: UUID,
        template_name: str,
        category: str | None = None,
    ) -> RoutingTemplate | None:
        """Create a template from an existing virtual routing."""
        routing = self._routings.get(routing_id)
        if routing is None:
            return None
        
        # Convert operations to template format (no IDs)
        operations = []
        for op in routing.operations:
            operations.append({
                "operation_type": op.operation_type,
                "operation_name": op.operation_name,
                "description": op.description,
                "setup_time_minutes": op.setup_time_minutes,
                "run_time_minutes": op.run_time_minutes,
                "move_time_minutes": op.move_time_minutes,
                "queue_time_minutes": op.queue_time_minutes,
                "crew_size": op.crew_size,
                "is_subcontracted": op.is_subcontracted,
                "is_optional": op.is_optional,
            })
        
        template = RoutingTemplate(
            id=uuid4(),
            name=template_name,
            description=f"Created from routing: {routing.name}",
            category=category,
            operations=operations,
            default_labor_rate=routing.default_labor_rate,
            default_overhead_rate=routing.default_overhead_rate,
            default_machine_rate=routing.default_machine_rate,
            created_by=routing.created_by,
        )
        
        self._templates[template.id] = template
        return template

    async def create_template_from_routing_async(self, **kwargs: Any) -> RoutingTemplate | None:
        await self._ensure_loaded()
        template = self.create_template_from_routing(**kwargs)
        await self.persist_all()
        return template
    
    def get_template(self, template_id: UUID) -> RoutingTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    async def get_template_async(self, template_id: UUID) -> RoutingTemplate | None:
        await self._ensure_loaded()
        return self.get_template(template_id)
    
    def list_templates(
        self,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[RoutingTemplate]:
        """List available templates."""
        templates = list(self._templates.values())
        
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        if category is not None:
            templates = [t for t in templates if t.category == category]
        
        return sorted(templates, key=lambda t: t.name)

    async def list_templates_async(self, **kwargs: Any) -> list[RoutingTemplate]:
        await self._ensure_loaded()
        return self.list_templates(**kwargs)
    
    def delete_template(self, template_id: UUID) -> bool:
        """Delete a template (soft delete - marks as inactive)."""
        template = self._templates.get(template_id)
        if template is None:
            return False
        
        template.is_active = False
        template.updated_at = datetime.now(timezone.utc)
        return True

    async def delete_template_async(self, template_id: UUID) -> bool:
        await self._ensure_loaded()
        result = self.delete_template(template_id)
        await self.persist_all()
        return result
    
    # =========================================================================
    # Cost Estimation
    # =========================================================================
    
    def estimate_costs(
        self,
        routing_id: UUID,
        quantity: int,
        material_cost: Decimal = Decimal("0"),
    ) -> dict[str, Any] | None:
        """Estimate costs for a virtual routing."""
        routing = self._routings.get(routing_id)
        if routing is None:
            return None
        
        costs = routing.calculate_costs(quantity, material_cost)
        
        return {
            "routing_id": routing_id,
            "routing_name": routing.name,
            "quantity": quantity,
            "material_cost": material_cost,
            **costs,
            "total_cost": costs["total_manufacturing_cost"] + material_cost,
            "unit_total_cost": (
                (costs["total_manufacturing_cost"] + material_cost) / quantity
                if quantity > 0
                else Decimal("0")
            ).quantize(Decimal("0.0001"), ROUND_HALF_UP),
        }

    async def estimate_costs_async(self, **kwargs: Any) -> dict[str, Any] | None:
        await self._ensure_loaded()
        return self.estimate_costs(**kwargs)
    
    def compare_routings(
        self,
        routing_ids: list[UUID],
        quantity: int,
        material_cost: Decimal = Decimal("0"),
    ) -> dict[str, Any]:
        """Compare costs between multiple virtual routings."""
        results = []
        
        for routing_id in routing_ids:
            estimate = self.estimate_costs(routing_id, quantity, material_cost)
            if estimate:
                results.append(estimate)
        
        if not results:
            return {
                "quantity": quantity,
                "material_cost": material_cost,
                "routings": [],
                "best_cost_routing": None,
                "best_time_routing": None,
            }
        
        # Find best by cost
        best_cost = min(results, key=lambda r: r["total_cost"])
        
        # Find best by time
        best_time_id = None
        best_time = None
        for routing_id in routing_ids:
            routing = self._routings.get(routing_id)
            if routing:
                time = routing.calculate_total_time_minutes(quantity)
                if best_time is None or time < best_time:
                    best_time = time
                    best_time_id = routing_id
        
        return {
            "quantity": quantity,
            "material_cost": material_cost,
            "routings": results,
            "best_cost_routing": best_cost["routing_id"],
            "best_cost": best_cost["total_cost"],
            "best_time_routing": best_time_id,
            "best_time_minutes": best_time,
        }

    async def compare_routings_async(self, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.compare_routings(**kwargs)
    
    def calculate_break_even_quantity(
        self,
        routing_id: UUID,
        target_unit_cost: Decimal,
        material_cost_per_unit: Decimal = Decimal("0"),
        max_quantity: int = 100000,
    ) -> int | None:
        """Calculate quantity needed to achieve target unit cost."""
        routing = self._routings.get(routing_id)
        if routing is None:
            return None
        
        # Binary search for break-even quantity
        low, high = 1, max_quantity
        
        while low < high:
            mid = (low + high) // 2
            costs = routing.calculate_costs(mid, material_cost_per_unit * mid)
            unit_cost = (
                costs["total_manufacturing_cost"] / mid + material_cost_per_unit
            )
            
            if unit_cost <= target_unit_cost:
                high = mid
            else:
                low = mid + 1
        
        # Verify the found quantity works
        costs = routing.calculate_costs(low, material_cost_per_unit * low)
        unit_cost = costs["total_manufacturing_cost"] / low + material_cost_per_unit
        
        if unit_cost <= target_unit_cost:
            return low
        
        return None  # Can't achieve target

    async def calculate_break_even_quantity_async(self, **kwargs: Any) -> int | None:
        await self._ensure_loaded()
        return self.calculate_break_even_quantity(**kwargs)
    
    # =========================================================================
    # Quick Builders
    # =========================================================================
    
    def create_simple_machining_routing(
        self,
        name: str,
        setup_minutes: Decimal,
        cycle_time_minutes: Decimal,
        quote_id: UUID | None = None,
        labor_rate: Decimal = Decimal("25.00"),
        machine_rate: Decimal = Decimal("50.00"),
    ) -> VirtualRouting:
        """Quick builder for simple machining routing."""
        routing = self.create_routing(
            name=name,
            description="Simple machining process",
            quote_id=quote_id,
            default_labor_rate=labor_rate,
            default_machine_rate=machine_rate,
        )
        
        routing.add_operation(
            operation_type=OperationType.SETUP,
            operation_name="Setup",
            setup_time_minutes=setup_minutes,
            run_time_minutes=Decimal("0"),
        )
        
        routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=cycle_time_minutes,
        )
        
        routing.add_operation(
            operation_type=OperationType.INSPECTION,
            operation_name="Inspection",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("1"),
        )
        
        return routing

    async def create_simple_machining_routing_async(self, **kwargs: Any) -> VirtualRouting:
        await self._ensure_loaded()
        routing = self.create_simple_machining_routing(**kwargs)
        await self.persist_all()
        return routing
    
    def create_assembly_routing(
        self,
        name: str,
        assembly_time_minutes: Decimal,
        test_time_minutes: Decimal = Decimal("0"),
        quote_id: UUID | None = None,
        labor_rate: Decimal = Decimal("20.00"),
    ) -> VirtualRouting:
        """Quick builder for assembly routing."""
        routing = self.create_routing(
            name=name,
            description="Assembly process",
            quote_id=quote_id,
            default_labor_rate=labor_rate,
        )
        
        routing.add_operation(
            operation_type=OperationType.MATERIAL_PREP,
            operation_name="Material Prep",
            setup_time_minutes=Decimal("5"),
            run_time_minutes=Decimal("1"),
        )
        
        routing.add_operation(
            operation_type=OperationType.ASSEMBLY,
            operation_name="Assembly",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=assembly_time_minutes,
        )
        
        if test_time_minutes > 0:
            routing.add_operation(
                operation_type=OperationType.TESTING,
                operation_name="Functional Test",
                setup_time_minutes=Decimal("0"),
                run_time_minutes=test_time_minutes,
            )
        
        routing.add_operation(
            operation_type=OperationType.PACKAGING,
            operation_name="Packaging",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("2"),
        )
        
        return routing

    async def create_assembly_routing_async(self, **kwargs: Any) -> VirtualRouting:
        await self._ensure_loaded()
        routing = self.create_assembly_routing(**kwargs)
        await self.persist_all()
        return routing
    
    def create_subcontract_routing(
        self,
        name: str,
        subcontract_cost_per_unit: Decimal,
        lead_time_days: int,
        vendor_id: UUID | None = None,
        quote_id: UUID | None = None,
    ) -> VirtualRouting:
        """Quick builder for subcontracted work."""
        routing = self.create_routing(
            name=name,
            description="Subcontracted process",
            quote_id=quote_id,
        )
        
        routing.add_operation(
            operation_type=OperationType.SUBCONTRACT,
            operation_name="Subcontract",
            is_subcontracted=True,
            subcontract_cost=subcontract_cost_per_unit,
            subcontract_lead_days=lead_time_days,
            subcontract_vendor_id=vendor_id,
        )
        
        return routing

    async def create_subcontract_routing_async(self, **kwargs: Any) -> VirtualRouting:
        await self._ensure_loaded()
        routing = self.create_subcontract_routing(**kwargs)
        await self.persist_all()
        return routing
