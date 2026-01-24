"""
Multi-Agent RFQ Analyzer - Specialized agents for comprehensive RFQ analysis.

Includes:
- Agent Orchestration: Coordinator managing specialized agents
- Technical Agent: DFM and spec-parsing
- Commercial Agent: Price-point analysis
- Risk Agent: Multi-vector risk scoring
- Agent Consensus Logic: Debate protocol for discrepancies
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional, Protocol
from collections import defaultdict
import hashlib
import re
import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.strategic_v2 import AgentAnalysisRecord, ConsensusDebateRecord


# =============================================================================
# Constants
# =============================================================================

DEFAULT_DEBATE_ROUNDS = 3
CONSENSUS_THRESHOLD = 0.75
HIGH_CONFIDENCE_THRESHOLD = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.6


# =============================================================================
# Enums
# =============================================================================

class AgentType(Enum):
    """Types of specialized agents."""
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    RISK = "risk"
    COORDINATOR = "coordinator"
    NEGOTIATOR = "negotiator"
    LOGISTICS = "logistics"


class AnalysisCategory(Enum):
    """Categories of RFQ analysis."""
    MANUFACTURABILITY = "manufacturability"
    PRICING = "pricing"
    RISK = "risk"
    CAPACITY = "capacity"
    COMPLIANCE = "compliance"
    SUPPLY_CHAIN = "supply_chain"
    TIMELINE = "timeline"


class RiskCategory(Enum):
    """Risk categories for scoring."""
    SUPPLY_CHAIN = "supply_chain"
    COMPLIANCE = "compliance"
    CAPACITY = "capacity"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    TIMELINE = "timeline"


class DebateOutcome(Enum):
    """Outcome of agent debate."""
    CONSENSUS = "consensus"
    MAJORITY = "majority"
    COORDINATOR_DECISION = "coordinator_decision"
    UNRESOLVED = "unresolved"


class Severity(Enum):
    """Severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DFMIssueType(Enum):
    """Design for Manufacturing issue types."""
    TOLERANCE = "tolerance"
    MATERIAL = "material"
    GEOMETRY = "geometry"
    PROCESS = "process"
    FINISH = "finish"
    ASSEMBLY = "assembly"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class RFQSpec:
    """RFQ specification data."""
    rfq_id: str
    customer_id: str
    description: str
    quantity: int
    target_price: Optional[float] = None
    deadline: Optional[datetime] = None
    material_specs: dict[str, Any] = field(default_factory=dict)
    dimension_specs: dict[str, Any] = field(default_factory=dict)
    finish_requirements: list[str] = field(default_factory=list)
    compliance_requirements: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DFMIssue:
    """Design for Manufacturing issue."""
    issue_type: DFMIssueType
    description: str
    severity: Severity
    location: Optional[str] = None
    suggested_fix: Optional[str] = None
    cost_impact: Optional[float] = None
    confidence: float = 0.8


@dataclass
class PriceAnalysis:
    """Price analysis result."""
    recommended_price: float
    min_price: float
    max_price: float
    margin_percentage: float
    historical_avg: Optional[float] = None
    market_position: str = "competitive"
    confidence: float = 0.8
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class RiskScore:
    """Risk score for a category."""
    category: RiskCategory
    score: float  # 0.0 to 1.0
    severity: Severity
    factors: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class AgentFinding:
    """Finding from an agent analysis."""
    agent_type: AgentType
    category: AnalysisCategory
    title: str
    description: str
    severity: Severity
    confidence: float
    data: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentPosition:
    """Agent's position on a debated topic."""
    agent_type: AgentType
    topic: str
    position: str
    justification: str
    confidence: float
    supporting_evidence: list[str] = field(default_factory=list)
    round_number: int = 1


@dataclass
class DebateResult:
    """Result of agent debate."""
    topic: str
    outcome: DebateOutcome
    final_position: str
    agreement_score: float
    rounds_needed: int
    positions: list[AgentPosition] = field(default_factory=list)
    coordinator_notes: str = ""
    debate_log: list[str] = field(default_factory=list)
    
    @property
    def rounds(self) -> int:
        """Alias for rounds_needed."""
        return self.rounds_needed
    
    @property
    def consensus_score(self) -> float:
        """Alias for agreement_score."""
        return self.agreement_score


@dataclass
class ComprehensiveAnalysis:
    """Comprehensive RFQ analysis from all agents."""
    rfq_id: str
    analysis_id: str
    timestamp: datetime
    
    # Agent findings
    technical_findings: list[AgentFinding] = field(default_factory=list)
    commercial_findings: list[AgentFinding] = field(default_factory=list)
    risk_findings: list[AgentFinding] = field(default_factory=list)
    negotiation_findings: list[AgentFinding] = field(default_factory=list)
    logistics_findings: list[AgentFinding] = field(default_factory=list)
    
    # Specific results
    dfm_issues: list[DFMIssue] = field(default_factory=list)
    price_analysis: Optional[PriceAnalysis] = None
    risk_scores: list[RiskScore] = field(default_factory=list)
    negotiation_strategy: dict[str, Any] = field(default_factory=dict)
    logistics_plan: dict[str, Any] = field(default_factory=dict)
    
    # Debate results
    debate_results: list[DebateResult] = field(default_factory=list)
    
    # Overall
    overall_score: float = 0.0
    recommendation: str = ""
    confidence: float = 0.8
    
    def get_all_findings(self) -> list[AgentFinding]:
        """Get all findings from all agents."""
        return (
            self.technical_findings + 
            self.commercial_findings + 
            self.risk_findings +
            self.negotiation_findings +
            self.logistics_findings
        )
    
    def get_critical_issues(self) -> list[AgentFinding]:
        """Get critical issues only."""
        return [f for f in self.get_all_findings() if f.severity in [Severity.HIGH, Severity.CRITICAL]]


# =============================================================================
# Agent Protocol
# =============================================================================

class AgentProtocol(Protocol):
    """Protocol for specialized agents."""
    
    @property
    def agent_type(self) -> AgentType:
        """Get agent type."""
        ...
    
    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze an RFQ and return findings."""
        ...
    
    def get_position(self, topic: str, context: dict[str, Any]) -> AgentPosition:
        """Get agent's position on a debated topic."""
        ...
    
    def update_position(self, topic: str, other_positions: list[AgentPosition]) -> AgentPosition:
        """Update position based on other agents' positions."""
        ...


# =============================================================================
# Base Agent
# =============================================================================

class BaseAgent:
    """Base class for specialized agents."""
    
    def __init__(self, agent_type: AgentType):
        """Initialize agent."""
        self._agent_type = agent_type
        self._positions: dict[str, AgentPosition] = {}
    
    @property
    def agent_type(self) -> AgentType:
        """Get agent type."""
        return self._agent_type
    
    async def analyze(self, rfq: "RFQSpec") -> list["AgentFinding"]:
        """Analyze RFQ - to be implemented by subclasses."""
        return []
    
    def _create_finding(
        self,
        category: AnalysisCategory,
        title: str,
        description: str,
        severity: Severity,
        confidence: float = 0.8,
        data: dict[str, Any] | None = None,
        recommendations: list[str] | None = None,
    ) -> AgentFinding:
        """Create an agent finding."""
        return AgentFinding(
            agent_type=self._agent_type,
            category=category,
            title=title,
            description=description,
            severity=severity,
            confidence=confidence,
            data=data or {},
            recommendations=recommendations or [],
        )
    
    def get_position(self, topic: str, context: dict[str, Any]) -> AgentPosition:
        """Get agent's position on a topic."""
        return AgentPosition(
            agent_type=self._agent_type,
            topic=topic,
            position="neutral",
            justification="No strong position",
            confidence=0.5,
        )
    
    def update_position(self, topic: str, other_positions: list[AgentPosition]) -> AgentPosition:
        """Update position based on other agents."""
        current = self._positions.get(topic)
        if not current:
            return self.get_position(topic, {})
        
        # Simple update: increase confidence if others agree
        agreeing = sum(1 for p in other_positions if p.position == current.position)
        total = len(other_positions)
        
        if total > 0:
            agreement_ratio = agreeing / total
            new_confidence = min(0.95, current.confidence + (agreement_ratio * 0.1))
        else:
            new_confidence = current.confidence
        
        return AgentPosition(
            agent_type=self._agent_type,
            topic=topic,
            position=current.position,
            justification=current.justification,
            confidence=new_confidence,
            supporting_evidence=current.supporting_evidence,
            round_number=current.round_number + 1,
        )


# =============================================================================
# Technical Agent
# =============================================================================

class TechnicalAgent(BaseAgent):
    """
    Technical Agent - Specialized in DFM and spec-parsing.
    
    Analyzes manufacturability, tolerances, materials, and processes.
    """
    
    # DFM rules
    MIN_WALL_THICKNESS = {
        "aluminum": 1.0,
        "steel": 0.8,
        "plastic": 0.5,
        "titanium": 1.5,
    }
    
    TIGHT_TOLERANCE_THRESHOLD = 0.01  # mm
    
    def __init__(self):
        """Initialize technical agent."""
        super().__init__(AgentType.TECHNICAL)
        self._material_database: dict[str, dict[str, Any]] = {}
        self._process_capabilities: dict[str, dict[str, Any]] = {}
    
    def register_material(self, name: str, properties: dict[str, Any]) -> None:
        """Register material properties."""
        self._material_database[name.lower()] = properties
    
    def register_process(self, name: str, capabilities: dict[str, Any]) -> None:
        """Register process capabilities."""
        self._process_capabilities[name.lower()] = capabilities
    
    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze RFQ for technical issues."""
        findings = []
        
        # Analyze dimensions and tolerances
        findings.extend(self._analyze_tolerances(rfq))
        
        # Analyze materials
        findings.extend(self._analyze_materials(rfq))
        
        # Analyze manufacturability
        findings.extend(self._analyze_manufacturability(rfq))
        
        # Analyze finish requirements
        findings.extend(self._analyze_finishes(rfq))
        
        return findings
    
    def _analyze_tolerances(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze tolerance specifications."""
        findings: list[AgentFinding] = []
        
        dims = rfq.dimension_specs
        if not dims:
            return findings
        
        tolerances = dims.get("tolerances", {})
        
        for feature, tolerance in tolerances.items():
            if isinstance(tolerance, (int, float)):
                if tolerance < self.TIGHT_TOLERANCE_THRESHOLD:
                    findings.append(self._create_finding(
                        category=AnalysisCategory.MANUFACTURABILITY,
                        title=f"Tight tolerance on {feature}",
                        description=f"Tolerance of ±{tolerance}mm may require precision machining",
                        severity=Severity.MEDIUM,
                        confidence=0.85,
                        data={"feature": feature, "tolerance": tolerance},
                        recommendations=[
                            "Consider relaxing tolerance if function permits",
                            "Budget for precision finishing operations",
                        ],
                    ))
        
        return findings
    
    def _analyze_materials(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze material specifications."""
        findings = []
        
        material = rfq.material_specs.get("primary_material", "").lower()
        if not material:
            findings.append(self._create_finding(
                category=AnalysisCategory.MANUFACTURABILITY,
                title="Material not specified",
                description="No primary material specified in RFQ",
                severity=Severity.HIGH,
                confidence=0.95,
                recommendations=["Request material specification from customer"],
            ))
            return findings
        
        # Check if material is known
        if material not in self._material_database and material not in self.MIN_WALL_THICKNESS:
            findings.append(self._create_finding(
                category=AnalysisCategory.MANUFACTURABILITY,
                title="Unknown material",
                description=f"Material '{material}' not in standard database",
                severity=Severity.MEDIUM,
                confidence=0.7,
                recommendations=["Verify material availability and properties"],
            ))
        
        return findings
    
    def _analyze_manufacturability(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze general manufacturability."""
        findings = []
        
        # Check quantity for process selection
        if rfq.quantity < 10:
            findings.append(self._create_finding(
                category=AnalysisCategory.MANUFACTURABILITY,
                title="Low quantity order",
                description=f"Quantity of {rfq.quantity} may not be cost-effective for some processes",
                severity=Severity.INFO,
                confidence=0.8,
                data={"quantity": rfq.quantity},
                recommendations=[
                    "Consider prototype-focused processes",
                    "Evaluate 3D printing or CNC machining",
                ],
            ))
        elif rfq.quantity > 10000:
            findings.append(self._create_finding(
                category=AnalysisCategory.MANUFACTURABILITY,
                title="High volume production",
                description=f"Quantity of {rfq.quantity} suitable for tooled processes",
                severity=Severity.INFO,
                confidence=0.85,
                data={"quantity": rfq.quantity},
                recommendations=[
                    "Consider injection molding or stamping",
                    "Evaluate dedicated tooling investment",
                ],
            ))
        
        return findings
    
    def _analyze_finishes(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze finish requirements."""
        findings = []
        
        for finish in rfq.finish_requirements:
            finish_lower = finish.lower()
            
            if "mirror" in finish_lower or "polish" in finish_lower:
                findings.append(self._create_finding(
                    category=AnalysisCategory.MANUFACTURABILITY,
                    title="High finish requirement",
                    description=f"Finish '{finish}' requires additional operations",
                    severity=Severity.LOW,
                    confidence=0.8,
                    data={"finish": finish},
                    recommendations=["Include polishing in cost estimate"],
                ))
            
            if "anodize" in finish_lower or "plate" in finish_lower:
                findings.append(self._create_finding(
                    category=AnalysisCategory.MANUFACTURABILITY,
                    title="Surface treatment required",
                    description=f"Surface treatment '{finish}' specified",
                    severity=Severity.INFO,
                    confidence=0.9,
                    data={"finish": finish},
                    recommendations=["Verify surface treatment vendor availability"],
                ))
        
        return findings
    
    def get_dfm_issues(self, rfq: RFQSpec) -> list[DFMIssue]:
        """Get specific DFM issues."""
        issues = []
        
        # Analyze dimensions for DFM
        dims = rfq.dimension_specs
        wall_thickness = dims.get("wall_thickness")
        material = rfq.material_specs.get("primary_material", "").lower()
        
        if wall_thickness and material:
            min_thickness = self.MIN_WALL_THICKNESS.get(material, 1.0)
            if wall_thickness < min_thickness:
                issues.append(DFMIssue(
                    issue_type=DFMIssueType.GEOMETRY,
                    description=f"Wall thickness {wall_thickness}mm below minimum {min_thickness}mm for {material}",
                    severity=Severity.HIGH,
                    location="wall features",
                    suggested_fix=f"Increase wall thickness to at least {min_thickness}mm",
                    cost_impact=0.0,
                    confidence=0.9,
                ))
        
        return issues
    
    def get_position(self, topic: str, context: dict[str, Any]) -> AgentPosition:
        """Get technical position on a topic."""
        if "price" in topic.lower():
            # Technical perspective on pricing
            return AgentPosition(
                agent_type=self._agent_type,
                topic=topic,
                position="cost-based",
                justification="Price should reflect actual manufacturing costs and complexity",
                confidence=0.75,
                supporting_evidence=["DFM analysis", "Process selection"],
            )
        
        if "risk" in topic.lower():
            return AgentPosition(
                agent_type=self._agent_type,
                topic=topic,
                position="technical-risk-focused",
                justification="Primary risk is manufacturability and tolerance achievement",
                confidence=0.8,
                supporting_evidence=["Tolerance analysis", "Material verification"],
            )
        
        return super().get_position(topic, context)


# =============================================================================
# Commercial Agent
# =============================================================================

class CommercialAgent(BaseAgent):
    """
    Commercial Agent - Specialized in pricing and market analysis.
    
    Analyzes historical pricing, market position, and commercial viability.
    """
    
    def __init__(self):
        """Initialize commercial agent."""
        super().__init__(AgentType.COMMERCIAL)
        self._price_history: dict[str, list[dict[str, Any]]] = {}
        self._customer_history: dict[str, dict[str, Any]] = {}
        self._margin_targets: dict[str, float] = {
            "standard": 0.25,
            "premium": 0.35,
            "competitive": 0.15,
        }
    
    def register_price_history(
        self,
        part_type: str,
        history: list[dict[str, Any]]
    ) -> None:
        """Register historical pricing data."""
        self._price_history[part_type.lower()] = history
    
    def register_customer_history(
        self,
        customer_id: str,
        history: dict[str, Any]
    ) -> None:
        """Register customer history."""
        self._customer_history[customer_id] = history
    
    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze RFQ for commercial factors."""
        findings = []
        
        # Analyze pricing
        findings.extend(self._analyze_pricing(rfq))
        
        # Analyze customer
        findings.extend(self._analyze_customer(rfq))
        
        # Analyze market position
        findings.extend(self._analyze_market(rfq))
        
        return findings
    
    def _analyze_pricing(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze pricing factors using BOM-cost rollups."""
        findings = []
        
        # Calculate real-world BOM cost rollup
        estimated_unit_cost = self._calculate_bom_cost(rfq)
        total_estimated_cost = estimated_unit_cost * rfq.quantity
        
        if rfq.target_price is not None:
            target_margin = (rfq.target_price - estimated_unit_cost) / rfq.target_price
            
            if target_margin < 0.1:
                findings.append(self._create_finding(
                    category=AnalysisCategory.PRICING,
                    title="Low margin opportunity",
                    description=f"Target price suggests margin of {target_margin:.1%} against estimated cost of ${estimated_unit_cost:.2f}/unit",
                    severity=Severity.HIGH,
                    confidence=0.85,
                    data={"target_margin": target_margin, "estimated_cost": estimated_unit_cost},
                    recommendations=[
                        "Negotiate on price or scope",
                        "Identify cost reduction opportunities in material or process",
                    ],
                ))
            elif target_margin > 0.4:
                findings.append(self._create_finding(
                    category=AnalysisCategory.PRICING,
                    title="High margin opportunity",
                    description=f"Target price allows for {target_margin:.1%} margin (Estimated cost: ${estimated_unit_cost:.2f}/unit)",
                    severity=Severity.INFO,
                    confidence=0.8,
                    data={"target_margin": target_margin, "estimated_cost": estimated_unit_cost},
                ))
        
        return findings

    def _calculate_bom_cost(self, rfq: RFQSpec) -> float:
        """
        Calculate estimated unit cost based on BOM rollup and manufacturing factors.
        """
        # Base material cost from specs or fallback
        material = rfq.material_specs.get("type", "aluminum").lower()
        base_rates = {
            "aluminum": 2.50,
            "steel": 1.20,
            "stainless": 4.50,
            "titanium": 25.0,
            "plastic": 0.80,
        }
        
        weight = rfq.material_specs.get("weight_kg", 1.5)
        material_cost = base_rates.get(material, 3.0) * weight
        
        # Process costs based on complexity
        complexity_score = 1.0
        if "dimension_specs" in rfq.metadata:
            dims = rfq.metadata["dimension_specs"]
            if len(dims.get("tolerances", [])) > 5:
                complexity_score += 0.5
        
        machine_hourly_rate = 65.0  # MAD/hr or USD/hr
        estimated_hours = 0.5 * complexity_score
        processing_cost = machine_hourly_rate * estimated_hours
        
        # Overhead and markup
        overhead_rate = 0.20
        total_unit_cost = (material_cost + processing_cost) * (1 + overhead_rate)
        
        return round(total_unit_cost, 2)
    
    def _analyze_customer(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze customer-related factors."""
        findings = []
        
        customer_data = self._customer_history.get(rfq.customer_id)
        
        if customer_data:
            win_rate = customer_data.get("win_rate", 0.5)
            if win_rate > 0.7:
                findings.append(self._create_finding(
                    category=AnalysisCategory.PRICING,
                    title="High win-rate customer",
                    description=f"Historical win rate of {win_rate:.0%} with this customer",
                    severity=Severity.INFO,
                    confidence=0.85,
                    data={"win_rate": win_rate},
                ))
            
            payment_history = customer_data.get("payment_rating", "good")
            if payment_history == "poor":
                findings.append(self._create_finding(
                    category=AnalysisCategory.RISK,
                    title="Payment risk",
                    description="Customer has history of late payments",
                    severity=Severity.MEDIUM,
                    confidence=0.8,
                    recommendations=["Consider stricter payment terms"],
                ))
        else:
            findings.append(self._create_finding(
                category=AnalysisCategory.PRICING,
                title="New customer",
                description="No historical data for this customer",
                severity=Severity.INFO,
                confidence=0.95,
                recommendations=["Conduct credit check"],
            ))
        
        return findings
    
    def _analyze_market(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze market factors."""
        findings = []
        
        # Check volume vs market
        if rfq.quantity > 5000:
            findings.append(self._create_finding(
                category=AnalysisCategory.PRICING,
                title="Volume pricing opportunity",
                description="High volume justifies volume discount strategy",
                severity=Severity.INFO,
                confidence=0.8,
                recommendations=["Apply volume discount structure"],
            ))
        
        return findings
    
    def calculate_price_recommendation(self, rfq: RFQSpec) -> PriceAnalysis:
        """Calculate recommended pricing."""
        # Simplified pricing model
        base_cost_per_unit = 10.0
        complexity_factor = 1.0 + (len(rfq.finish_requirements) * 0.1)
        quantity_factor = max(0.7, 1.0 - (rfq.quantity / 100000))
        
        unit_cost = base_cost_per_unit * complexity_factor * quantity_factor
        total_cost = unit_cost * rfq.quantity
        
        # Apply margin
        target_margin = self._margin_targets.get("standard", 0.25)
        recommended_price = total_cost / (1 - target_margin)
        
        return PriceAnalysis(
            recommended_price=recommended_price,
            min_price=total_cost * 1.1,
            max_price=recommended_price * 1.2,
            margin_percentage=target_margin * 100,
            market_position="competitive",
            confidence=0.75,
            breakdown={
                "material": total_cost * 0.4,
                "labor": total_cost * 0.3,
                "overhead": total_cost * 0.2,
                "finishing": total_cost * 0.1,
            },
        )
    
    def get_position(self, topic: str, context: dict[str, Any]) -> AgentPosition:
        """Get commercial position on a topic."""
        if "price" in topic.lower():
            return AgentPosition(
                agent_type=self._agent_type,
                topic=topic,
                position="market-competitive",
                justification="Price should balance competitiveness with profitability",
                confidence=0.8,
                supporting_evidence=["Historical win rates", "Market analysis"],
            )
        
        if "risk" in topic.lower():
            return AgentPosition(
                agent_type=self._agent_type,
                topic=topic,
                position="financial-risk-focused",
                justification="Primary risk is margin erosion and payment collection",
                confidence=0.75,
                supporting_evidence=["Customer history", "Market conditions"],
            )
        
        return super().get_position(topic, context)


# =============================================================================
# Risk Agent
# =============================================================================

class RiskAgent(BaseAgent):
    """
    Risk Agent - Multi-vector risk scoring.
    
    Analyzes supply chain, compliance, capacity, and other risks.
    """
    
    def __init__(self):
        """Initialize risk agent."""
        super().__init__(AgentType.RISK)
        self._supply_chain_data: dict[str, dict[str, Any]] = {}
        self._compliance_requirements: dict[str, list[str]] = {}
        self._capacity_data: dict[str, float] = {}
    
    def register_supply_chain_data(
        self,
        material: str,
        data: dict[str, Any]
    ) -> None:
        """Register supply chain data for a material."""
        self._supply_chain_data[material.lower()] = data
    
    def register_compliance_requirements(
        self,
        industry: str,
        requirements: list[str]
    ) -> None:
        """Register compliance requirements."""
        self._compliance_requirements[industry.lower()] = requirements
    
    def set_capacity_utilization(self, process: str, utilization: float) -> None:
        """Set capacity utilization for a process."""
        self._capacity_data[process.lower()] = utilization
    
    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze RFQ for risk factors."""
        findings = []
        
        # Supply chain risks
        findings.extend(self._analyze_supply_chain_risk(rfq))
        
        # Compliance risks
        findings.extend(self._analyze_compliance_risk(rfq))
        
        # Capacity risks
        findings.extend(self._analyze_capacity_risk(rfq))
        
        # Timeline risks
        findings.extend(self._analyze_timeline_risk(rfq))
        
        return findings
    
    def _analyze_supply_chain_risk(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze supply chain risks."""
        findings = []
        
        material = rfq.material_specs.get("primary_material", "").lower()
        
        if material in self._supply_chain_data:
            data = self._supply_chain_data[material]
            lead_time = data.get("lead_time_days", 14)
            availability = data.get("availability", 1.0)
            
            if lead_time > 30:
                findings.append(self._create_finding(
                    category=AnalysisCategory.SUPPLY_CHAIN,
                    title="Long material lead time",
                    description=f"Material {material} has {lead_time} day lead time",
                    severity=Severity.MEDIUM,
                    confidence=0.85,
                    data={"lead_time": lead_time},
                    recommendations=["Order material early", "Consider alternatives"],
                ))
            
            if availability < 0.8:
                findings.append(self._create_finding(
                    category=AnalysisCategory.SUPPLY_CHAIN,
                    title="Material availability risk",
                    description=f"Material {material} has limited availability ({availability:.0%})",
                    severity=Severity.HIGH,
                    confidence=0.8,
                    data={"availability": availability},
                    recommendations=["Secure material allocation", "Identify backup suppliers"],
                ))
        
        return findings
    
    def _analyze_compliance_risk(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze compliance risks."""
        findings = []
        
        for requirement in rfq.compliance_requirements:
            req_lower = requirement.lower()
            
            if "itar" in req_lower or "export" in req_lower:
                findings.append(self._create_finding(
                    category=AnalysisCategory.COMPLIANCE,
                    title="Export compliance requirement",
                    description=f"RFQ requires compliance with '{requirement}'",
                    severity=Severity.HIGH,
                    confidence=0.95,
                    data={"requirement": requirement},
                    recommendations=[
                        "Verify export license requirements",
                        "Review customer eligibility",
                    ],
                ))
            
            if "as9100" in req_lower or "iso" in req_lower:
                findings.append(self._create_finding(
                    category=AnalysisCategory.COMPLIANCE,
                    title="Quality certification required",
                    description=f"RFQ requires certification: {requirement}",
                    severity=Severity.MEDIUM,
                    confidence=0.9,
                    data={"requirement": requirement},
                    recommendations=["Verify certification is current"],
                ))
        
        return findings
    
    def _analyze_capacity_risk(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze capacity risks."""
        findings = []
        
        # Check overall capacity
        for process, utilization in self._capacity_data.items():
            if utilization > 0.9:
                findings.append(self._create_finding(
                    category=AnalysisCategory.CAPACITY,
                    title="Capacity constraint",
                    description=f"Process '{process}' at {utilization:.0%} utilization",
                    severity=Severity.HIGH,
                    confidence=0.85,
                    data={"process": process, "utilization": utilization},
                    recommendations=[
                        "Evaluate overtime/additional shifts",
                        "Consider subcontracting",
                    ],
                ))
            elif utilization > 0.75:
                findings.append(self._create_finding(
                    category=AnalysisCategory.CAPACITY,
                    title="Capacity warning",
                    description=f"Process '{process}' approaching capacity ({utilization:.0%})",
                    severity=Severity.MEDIUM,
                    confidence=0.8,
                    data={"process": process, "utilization": utilization},
                ))
        
        return findings
    
    def _analyze_timeline_risk(self, rfq: RFQSpec) -> list[AgentFinding]:
        """Analyze timeline risks."""
        findings = []
        
        if rfq.deadline:
            now = datetime.now(timezone.utc)
            deadline = rfq.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            
            days_until_deadline = (deadline - now).days
            
            if days_until_deadline < 14:
                findings.append(self._create_finding(
                    category=AnalysisCategory.TIMELINE,
                    title="Tight deadline",
                    description=f"Only {days_until_deadline} days until deadline",
                    severity=Severity.HIGH,
                    confidence=0.9,
                    data={"days_remaining": days_until_deadline},
                    recommendations=["Expedite processing", "Prioritize this order"],
                ))
            elif days_until_deadline < 30:
                findings.append(self._create_finding(
                    category=AnalysisCategory.TIMELINE,
                    title="Timeline awareness",
                    description=f"{days_until_deadline} days until deadline",
                    severity=Severity.INFO,
                    confidence=0.95,
                    data={"days_remaining": days_until_deadline},
                ))
        
        return findings
    
    def calculate_risk_scores(self, rfq: RFQSpec) -> list[RiskScore]:
        """Calculate comprehensive risk scores."""
        scores = []
        
        # Supply chain risk
        material = rfq.material_specs.get("primary_material", "").lower()
        sc_data = self._supply_chain_data.get(material, {})
        sc_score = 1.0 - sc_data.get("availability", 0.8)
        
        scores.append(RiskScore(
            category=RiskCategory.SUPPLY_CHAIN,
            score=sc_score,
            severity=self._score_to_severity(sc_score),
            factors=[f"Material: {material}"] if material else [],
            mitigations=["Dual source materials"] if sc_score > 0.5 else [],
            confidence=0.75,
        ))
        
        # Compliance risk
        compliance_score = min(0.3 * len(rfq.compliance_requirements), 1.0)
        scores.append(RiskScore(
            category=RiskCategory.COMPLIANCE,
            score=compliance_score,
            severity=self._score_to_severity(compliance_score),
            factors=rfq.compliance_requirements,
            confidence=0.85,
        ))
        
        # Capacity risk
        max_utilization = max(self._capacity_data.values()) if self._capacity_data else 0.5
        capacity_score = max(0, (max_utilization - 0.7) / 0.3)  # Scale 0.7-1.0 to 0-1
        
        scores.append(RiskScore(
            category=RiskCategory.CAPACITY,
            score=min(1.0, capacity_score),
            severity=self._score_to_severity(capacity_score),
            factors=[f"Max utilization: {max_utilization:.0%}"],
            confidence=0.8,
        ))
        
        return scores
    
    def _score_to_severity(self, score: float) -> Severity:
        """Convert risk score to severity."""
        if score >= 0.8:
            return Severity.CRITICAL
        elif score >= 0.6:
            return Severity.HIGH
        elif score >= 0.4:
            return Severity.MEDIUM
        elif score >= 0.2:
            return Severity.LOW
        else:
            return Severity.INFO
    
    def get_position(self, topic: str, context: dict[str, Any]) -> AgentPosition:
        """Get risk position on a topic."""
        return super().get_position(topic, context)


# =============================================================================
# Negotiator Agent
# =============================================================================

class NegotiatorAgent(BaseAgent):
    """
    Negotiation Strategy Agent.
    Provides tactical advice based on win/loss history and customer profile.
    """
    
    def __init__(self):
        super().__init__(AgentType.NEGOTIATOR)
        self._customer_behavior: dict[str, dict[str, Any]] = {}
        
    def register_customer_behavior(self, customer_id: str, behavior: dict[str, Any]) -> None:
        """Register observed customer negotiation behavior."""
        self._customer_behavior[customer_id] = behavior

    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        findings = []
        
        behavior = self._customer_behavior.get(rfq.customer_id, {})
        price_sensitivity = behavior.get("price_sensitivity", "medium")
        last_negotiation = behavior.get("last_negotiation_outcome", "fair")
        
        tactics = ["Focus on value-add components"]
        if price_sensitivity == "high":
            tactics.append("Lead with volume-based discount tiers")
            tactics.append("Highlight total cost of ownership vs sticker price")
        elif price_sensitivity == "low":
            tactics.append("Emphasize quality and speed of delivery")
            
        if last_negotiation == "aggressive":
            tactics.append("Prepare multiple fallback positions")
            
        findings.append(self._create_finding(
            category=AnalysisCategory.PRICING,
            title="Tactical Negotiation Strategy",
            description=f"Tailored strategy for {rfq.customer_id} based on {price_sensitivity} price sensitivity.",
            severity=Severity.INFO,
            confidence=0.85,
            data={
                "price_sensitivity": price_sensitivity,
                "customer_tier": behavior.get("tier", "standard")
            },
            recommendations=tactics
        ))
        return findings

    def get_strategy(self, rfq: RFQSpec) -> dict[str, Any]:
        behavior = self._customer_behavior.get(rfq.customer_id, {})
        target = rfq.target_price or 100.0
        
        # Calculate aggressive vs conservative opening
        multiplier = 1.15 if behavior.get("price_sensitivity") == "high" else 1.08
        
        return {
            "opening_offer": target * multiplier,
            "walk_away_price": target * 0.92,
            "concession_steps": ["Payment terms (Net 60)", "Partial tooling absorption", "5% volume discount"],
            "key_leverages": [
                "Proprietary alloy selection",
                "ISO 9001 certified process",
                "Existing capacity for immediate start"
            ],
        }


# =============================================================================
# Logistics Agent
# =============================================================================

class LogisticsAgent(BaseAgent):
    """
    Logistics & Lead Time Agent.
    Analyzes shipping constraints and supply chain timing.
    """
    
    def __init__(self):
        super().__init__(AgentType.LOGISTICS)
        self._region_transit_times: dict[str, int] = {
            "domestic": 2,
            "international": 7,
            "remote": 12
        }
        
    async def analyze(self, rfq: RFQSpec) -> list[AgentFinding]:
        findings = []
        
        dest_region = rfq.metadata.get("destination_region", "international")
        transit_days = self._region_transit_times.get(dest_region, 7)
        
        severity = Severity.LOW
        if transit_days > 10:
            severity = Severity.MEDIUM
            
        findings.append(self._create_finding(
            category=AnalysisCategory.TIMELINE,
            title="Logistics & Lead Time Assessment",
            description=f"Shipment to {dest_region} region. Transit estimate: {transit_days} days.",
            severity=severity,
            confidence=0.9,
            data={"estimated_transit_days": transit_days, "region": dest_region},
            recommendations=[
                "Confirm customs documentation availability",
                "Evaluate air freight if deadline is tight"
            ]
        ))
        return findings

    def get_logistics_plan(self, rfq: RFQSpec) -> dict[str, Any]:
        dest_region = rfq.metadata.get("destination_region", "international")
        transit_days = self._region_transit_times.get(dest_region, 7)
        
        # Production lead time (simulated)
        production_days = 14
        if rfq.quantity > 5000: production_days = 21
        
        return {
            "estimated_delivery_date": datetime.now(timezone.utc) + timedelta(days=production_days + transit_days),
            "production_lead_time": production_days,
            "transit_time": transit_days,
            "shipping_method": "Sea Freight" if rfq.quantity > 10000 else "Air Freight",
            "customs_risk": "Medium" if dest_region == "remote" else "Low",
        }


# =============================================================================
# Agent Orchestrator
# =============================================================================

class AgentOrchestrator:
    """
    Coordinator agent that manages specialized agents.
    
    Implements debate protocol for reaching consensus.
    """
    
    def __init__(
        self,
        max_debate_rounds: int = DEFAULT_DEBATE_ROUNDS,
        consensus_threshold: float = CONSENSUS_THRESHOLD,
    ):
        """Initialize orchestrator."""
        self.max_debate_rounds = max_debate_rounds
        self.consensus_threshold = consensus_threshold
        
        self._agents: dict[AgentType, BaseAgent] = {}
        self._debate_history: list[DebateResult] = []
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register a specialized agent."""
        self._agents[agent.agent_type] = agent
    
    def get_agent(self, agent_type: AgentType) -> BaseAgent | None:
        """Get registered agent by type."""
        return self._agents.get(agent_type)
    
    async def analyze_rfq(self, rfq: RFQSpec, db: AsyncSession | None = None) -> ComprehensiveAnalysis:
        """Perform comprehensive RFQ analysis with all agents and persist results."""
        analysis_id = hashlib.md5(
            f"{rfq.rfq_id}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:16]
        
        analysis = ComprehensiveAnalysis(
            rfq_id=rfq.rfq_id,
            analysis_id=analysis_id,
            timestamp=datetime.now(timezone.utc),
        )
        
        # Collect findings from each agent
        for agent_type, agent in self._agents.items():
            findings = await agent.analyze(rfq)
            
            # Persist individual agent findings
            if db is not None:
                for finding in findings:
                    record = AgentAnalysisRecord(
                        rfq_id=UUID(rfq.rfq_id),
                        agent_type=agent_type.value,
                        analysis_category=finding.category.value,
                        confidence=finding.confidence,
                        findings={"observation": finding.description},
                        recommendations=finding.recommendations,
                    )
                    db.add(record)

            if agent_type == AgentType.TECHNICAL:
                analysis.technical_findings = findings
                if isinstance(agent, TechnicalAgent):
                    analysis.dfm_issues = agent.get_dfm_issues(rfq)
            elif agent_type == AgentType.COMMERCIAL:
                analysis.commercial_findings = findings
                if isinstance(agent, CommercialAgent):
                    analysis.price_analysis = agent.calculate_price_recommendation(rfq)
            elif agent_type == AgentType.RISK:
                analysis.risk_findings = findings
                if isinstance(agent, RiskAgent):
                    analysis.risk_scores = agent.calculate_risk_scores(rfq)
            elif agent_type == AgentType.NEGOTIATOR:
                analysis.negotiation_findings = findings
                if isinstance(agent, NegotiatorAgent):
                    analysis.negotiation_strategy = agent.get_strategy(rfq)
            elif agent_type == AgentType.LOGISTICS:
                analysis.logistics_findings = findings
                if isinstance(agent, LogisticsAgent):
                    analysis.logistics_plan = agent.get_logistics_plan(rfq)
        
        # Check for discrepancies and run debate if needed
        discrepancies = self._identify_discrepancies(analysis)
        
        for topic, context in discrepancies:
            debate_result = await self._run_debate(topic, context)
            analysis.debate_results.append(debate_result)
            
            # Persist debate result
            if db is not None:
                debate_record = ConsensusDebateRecord(
                    rfq_id=UUID(rfq.rfq_id),
                    issue_description=topic,
                    rounds=debate_result.rounds,
                    outcome=debate_result.outcome.value,
                    final_consensus_score=debate_result.consensus_score,
                    debate_log=debate_result.debate_log,
                )
                db.add(debate_record)
        
        # Calculate overall score and recommendation
        analysis.overall_score = self._calculate_overall_score(analysis)
        analysis.recommendation = self._generate_recommendation(analysis)
        analysis.confidence = self._calculate_confidence(analysis)
        
        if db is not None:
            await db.commit()
        return analysis
    
    def _identify_discrepancies(
        self,
        analysis: ComprehensiveAnalysis
    ) -> list[tuple[str, dict[str, Any]]]:
        """Identify topics where agents may disagree."""
        discrepancies = []
        
        # Check if there are conflicting severity assessments
        all_findings = analysis.get_all_findings()
        
        by_category: dict[AnalysisCategory, list[AgentFinding]] = defaultdict(list)
        for finding in all_findings:
            by_category[finding.category].append(finding)
        
        for category, findings in by_category.items():
            if len(findings) >= 2:
                severities = set(f.severity for f in findings)
                if Severity.HIGH in severities and Severity.LOW in severities:
                    discrepancies.append((
                        f"severity_assessment_{category.value}",
                        {"category": category, "findings": findings},
                    ))
        
        # Price vs risk discrepancy
        if analysis.price_analysis and analysis.risk_scores:
            high_risks = [r for r in analysis.risk_scores if r.score > 0.6]
            if high_risks and analysis.price_analysis.confidence > 0.7:
                discrepancies.append((
                    "price_risk_alignment",
                    {
                        "price_analysis": analysis.price_analysis,
                        "risks": high_risks,
                    },
                ))
        
        return discrepancies
    
    async def _run_debate(
        self,
        topic: str,
        context: dict[str, Any]
    ) -> DebateResult:
        """Run debate protocol to resolve discrepancy."""
        if not self._agents:
            return DebateResult(
                topic=topic,
                outcome=DebateOutcome.COORDINATOR_DECISION,
                final_position="UNKNOWN",
                agreement_score=0.0,
                rounds_needed=0,
                positions=[],
                coordinator_notes="No agents available for debate",
            )
            
        positions: list[AgentPosition] = []
        
        # Collect initial positions
        for agent_type, agent in self._agents.items():
            position = agent.get_position(topic, context)
            positions.append(position)
            agent._positions[topic] = position
        
        # Run debate rounds
        for round_num in range(1, self.max_debate_rounds + 1):
            # Check for consensus
            position_counts: dict[str, int] = defaultdict(int)
            for pos in positions:
                position_counts[pos.position] += 1
            
            max_agreement = max(position_counts.values()) / len(positions)
            
            if max_agreement >= self.consensus_threshold:
                majority_position = max(position_counts.items(), key=lambda x: x[1])[0]
                return DebateResult(
                    topic=topic,
                    outcome=DebateOutcome.CONSENSUS,
                    final_position=majority_position,
                    agreement_score=max_agreement,
                    rounds_needed=round_num,
                    positions=positions,
                )
            
            # Update positions based on others' positions
            new_positions = []
            for agent_type, agent in self._agents.items():
                other_positions = [p for p in positions if p.agent_type != agent_type]
                new_position = agent.update_position(topic, other_positions)
                new_position.round_number = round_num
                new_positions.append(new_position)
                agent._positions[topic] = new_position
            
            positions = new_positions
        
        # No consensus reached - coordinator decides
        # Weighted by confidence
        weighted_positions: dict[str, float] = defaultdict(float)
        for pos in positions:
            weighted_positions[pos.position] += pos.confidence
        
        final_position = max(weighted_positions.items(), key=lambda x: x[1])[0]
        agreement = max(position_counts.values()) / len(positions)
        
        return DebateResult(
            topic=topic,
            outcome=DebateOutcome.COORDINATOR_DECISION,
            final_position=final_position,
            agreement_score=agreement,
            rounds_needed=self.max_debate_rounds,
            positions=positions,
            coordinator_notes="Decision made by coordinator based on confidence-weighted positions",
        )
    
    def _calculate_overall_score(self, analysis: ComprehensiveAnalysis) -> float:
        """Calculate overall analysis score (0-100)."""
        score = 100.0
        
        # Deduct for findings by severity
        for finding in analysis.get_all_findings():
            if finding.severity == Severity.CRITICAL:
                score -= 15
            elif finding.severity == Severity.HIGH:
                score -= 10
            elif finding.severity == Severity.MEDIUM:
                score -= 5
            elif finding.severity == Severity.LOW:
                score -= 2
        
        # Deduct for high risk scores
        for risk in analysis.risk_scores:
            if risk.score > 0.7:
                score -= 10
            elif risk.score > 0.5:
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendation(self, analysis: ComprehensiveAnalysis) -> str:
        """Generate overall recommendation."""
        score = analysis.overall_score
        critical_issues = analysis.get_critical_issues()
        
        if score >= 80 and not critical_issues:
            return "PROCEED: RFQ appears viable with low risk"
        elif score >= 60:
            return "PROCEED WITH CAUTION: Review identified issues before quoting"
        elif score >= 40:
            return "REVIEW REQUIRED: Significant concerns need management review"
        else:
            return "HIGH RISK: Consider declining or requiring scope changes"
    
    def _calculate_confidence(self, analysis: ComprehensiveAnalysis) -> float:
        """Calculate overall confidence in analysis."""
        confidences = []
        
        for finding in analysis.get_all_findings():
            confidences.append(finding.confidence)
        
        for risk in analysis.risk_scores:
            confidences.append(risk.confidence)
        
        if analysis.price_analysis:
            confidences.append(analysis.price_analysis.confidence)
        
        if not confidences:
            return 0.7
        
        return sum(confidences) / len(confidences)


# =============================================================================
# Multi-Agent RFQ Analyzer
# =============================================================================

class MultiAgentRFQAnalyzer:
    """
    Multi-Agent RFQ Analyzer - Main interface.
    
    Combines all specialized agents for comprehensive RFQ analysis.
    """
    
    def __init__(
        self,
        max_debate_rounds: int = DEFAULT_DEBATE_ROUNDS,
        consensus_threshold: float = CONSENSUS_THRESHOLD,
    ):
        """Initialize analyzer."""
        self.orchestrator = AgentOrchestrator(
            max_debate_rounds=max_debate_rounds,
            consensus_threshold=consensus_threshold,
        )
        
        # Create and register default agents
        self.technical_agent = TechnicalAgent()
        self.commercial_agent = CommercialAgent()
        self.risk_agent = RiskAgent()
        
        self.orchestrator.register_agent(self.technical_agent)
        self.orchestrator.register_agent(self.commercial_agent)
        self.orchestrator.register_agent(self.risk_agent)
        
        self._analysis_history: dict[str, ComprehensiveAnalysis] = {}
    
    async def analyze(self, rfq: RFQSpec) -> ComprehensiveAnalysis:
        """Perform full multi-agent analysis."""
        analysis = await self.orchestrator.analyze_rfq(rfq)
        self._analysis_history[analysis.analysis_id] = analysis
        return analysis
    
    def get_analysis(self, analysis_id: str) -> ComprehensiveAnalysis | None:
        """Get a previous analysis by ID."""
        return self._analysis_history.get(analysis_id)
    
    def configure_technical_agent(
        self,
        materials: dict[str, dict[str, Any]] | None = None,
        processes: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Configure technical agent with material/process data."""
        if materials:
            for name, props in materials.items():
                self.technical_agent.register_material(name, props)
        if processes:
            for name, caps in processes.items():
                self.technical_agent.register_process(name, caps)
    
    def configure_commercial_agent(
        self,
        price_history: dict[str, list[dict[str, Any]]] | None = None,
        customer_history: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Configure commercial agent with historical data."""
        if price_history:
            for part_type, price_data in price_history.items():
                self.commercial_agent.register_price_history(part_type, price_data)
        if customer_history:
            for customer_id, customer_data in customer_history.items():
                self.commercial_agent.register_customer_history(customer_id, customer_data)
    
    def configure_risk_agent(
        self,
        supply_chain: dict[str, dict[str, Any]] | None = None,
        capacity: dict[str, float] | None = None,
    ) -> None:
        """Configure risk agent with supply chain and capacity data."""
        if supply_chain:
            for material, data in supply_chain.items():
                self.risk_agent.register_supply_chain_data(material, data)
        if capacity:
            for process, utilization in capacity.items():
                self.risk_agent.set_capacity_utilization(process, utilization)
    
    def get_stats(self) -> dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_analyses": len(self._analysis_history),
            "registered_agents": len(self.orchestrator._agents),
            "debate_rounds_max": self.orchestrator.max_debate_rounds,
            "consensus_threshold": self.orchestrator.consensus_threshold,
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_rfq_analyzer(
    max_debate_rounds: int = DEFAULT_DEBATE_ROUNDS,
    consensus_threshold: float = CONSENSUS_THRESHOLD,
) -> MultiAgentRFQAnalyzer:
    """Create a configured multi-agent RFQ analyzer."""
    return MultiAgentRFQAnalyzer(
        max_debate_rounds=max_debate_rounds,
        consensus_threshold=consensus_threshold,
    )
