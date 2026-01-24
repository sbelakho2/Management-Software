"""
Smart Supplier Matchmaker Service.

AI-powered supplier matching using capability graphs and semantic matching
to recommend ideal suppliers for RFQ requirements.

Features:
- Capability graph representation
- Semantic matching with embeddings
- Multi-criteria scoring
- Rank aggregation
- Constraint satisfaction
"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, cast
import math
import re
import uuid


# =============================================================================
# Enums
# =============================================================================

class MatchingCriteria(Enum):
    """Criteria for supplier matching."""
    
    CAPABILITY = "capability"
    PRICE = "price"
    QUALITY = "quality"
    DELIVERY = "delivery"
    RELIABILITY = "reliability"
    LOCATION = "location"
    CAPACITY = "capacity"
    CERTIFICATION = "certification"


class SupplierTier(Enum):
    """Supplier tier classification."""
    
    STRATEGIC = "strategic"
    PREFERRED = "preferred"
    APPROVED = "approved"
    PROBATIONARY = "probationary"
    INACTIVE = "inactive"


class MatchConfidence(Enum):
    """Confidence level of match."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class CapabilityType(Enum):
    """Types of capabilities."""
    
    MATERIAL = "material"
    PROCESS = "process"
    EQUIPMENT = "equipment"
    CERTIFICATION = "certification"
    INDUSTRY = "industry"


# =============================================================================
# Constants
# =============================================================================

DEFAULT_WEIGHTS = {
    MatchingCriteria.CAPABILITY: 0.30,
    MatchingCriteria.QUALITY: 0.20,
    MatchingCriteria.DELIVERY: 0.15,
    MatchingCriteria.PRICE: 0.15,
    MatchingCriteria.RELIABILITY: 0.10,
    MatchingCriteria.CAPACITY: 0.05,
    MatchingCriteria.CERTIFICATION: 0.03,
    MatchingCriteria.LOCATION: 0.02,
}

# Semantic similarity mappings for capability matching
CAPABILITY_SYNONYMS = {
    "aluminum": ["aluminium", "al", "6061", "7075"],
    "steel": ["stainless", "carbon steel", "steel alloy"],
    "cnc": ["cnc machining", "milling", "turning", "cnc milling"],
    "milling": ["mill", "cnc milling", "vertical milling"],
    "turning": ["lathe", "cnc turning", "turning center"],
    "welding": ["weld", "mig", "tig", "arc welding"],
    "coating": ["plating", "anodizing", "powder coat", "finish"],
    "inspection": ["qc", "quality control", "testing", "metrology"],
    "assembly": ["assemble", "sub-assembly", "final assembly"],
    "3d printing": ["additive", "am", "additive manufacturing", "printing"],
}


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Capability:
    """Supplier capability."""
    
    capability_id: str
    name: str
    capability_type: CapabilityType
    proficiency_level: float = 0.8  # 0-1
    keywords: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    capacity_info: dict[str, Any] = field(default_factory=dict)
    
    def matches_keyword(self, keyword: str) -> float:
        """Check if capability matches keyword, returning similarity score."""
        keyword_lower = keyword.lower().strip()
        name_lower = self.name.lower()
        
        # Exact match
        if keyword_lower == name_lower:
            return 1.0
        
        # Check if keyword in name
        if keyword_lower in name_lower or name_lower in keyword_lower:
            return 0.9
        
        # Check keywords list
        for kw in self.keywords:
            if keyword_lower == kw.lower():
                return 0.85
            if keyword_lower in kw.lower() or kw.lower() in keyword_lower:
                return 0.7
        
        # Check synonyms
        for base, synonyms in CAPABILITY_SYNONYMS.items():
            if keyword_lower in [base] + synonyms:
                if name_lower in [base] + synonyms:
                    return 0.75
                for kw in self.keywords:
                    if kw.lower() in [base] + synonyms:
                        return 0.6
        
        return 0.0


@dataclass
class PerformanceMetrics:
    """Supplier performance metrics."""
    
    on_time_delivery_rate: float = 0.95  # 0-1
    quality_score: float = 0.95  # 0-1
    defect_rate: float = 0.02  # 0-1
    response_time_hours: float = 24.0
    average_lead_time_days: float = 14.0
    price_competitiveness: float = 0.85  # 0-1, higher is more competitive
    orders_completed: int = 100
    issues_reported: int = 5
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability score."""
        if self.orders_completed == 0:
            return 0.5
        
        issue_rate = self.issues_reported / self.orders_completed
        # Lower issue rate = higher reliability
        return max(0.0, 1.0 - (issue_rate * 10))
    
    @property
    def overall_score(self) -> float:
        """Calculate overall performance score."""
        return (
            self.on_time_delivery_rate * 0.3 +
            self.quality_score * 0.3 +
            (1 - self.defect_rate) * 0.2 +
            self.reliability_score * 0.2
        )


@dataclass
class Supplier:
    """Supplier entity."""
    
    supplier_id: str
    name: str
    tier: SupplierTier = SupplierTier.APPROVED
    capabilities: list[Capability] = field(default_factory=list)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    certifications: list[str] = field(default_factory=list)
    location: str = ""
    region: str = ""
    minimum_order_value: float = 0.0
    maximum_capacity_units: int = 10000
    lead_time_days: int = 14
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def has_certification(self, cert: str) -> bool:
        """Check if supplier has certification."""
        cert_lower = cert.lower()
        for c in self.certifications:
            if cert_lower in c.lower() or c.lower() in cert_lower:
                return True
        return False
    
    def get_capability_match(self, keyword: str) -> float:
        """Get best capability match for keyword."""
        if not self.capabilities:
            return 0.0
        
        return max(cap.matches_keyword(keyword) for cap in self.capabilities)


@dataclass
class RFQRequirement:
    """RFQ requirement for matching."""
    
    rfq_id: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    required_certifications: list[str] = field(default_factory=list)
    quantity: int = 1
    target_price: float | None = None
    target_lead_time_days: int | None = None
    preferred_regions: list[str] = field(default_factory=list)
    minimum_quality_score: float = 0.8
    priority_weights: dict[MatchingCriteria, float] = field(default_factory=dict)
    
    def get_weights(self) -> dict[MatchingCriteria, float]:
        """Get matching weights, using defaults if not specified."""
        weights = DEFAULT_WEIGHTS.copy()
        weights.update(self.priority_weights)
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            return {k: v / total for k, v in weights.items()}
        return weights


@dataclass
class MatchScore:
    """Individual match score for a criteria."""
    
    criteria: MatchingCriteria
    score: float  # 0-1
    weight: float
    weighted_score: float
    explanation: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupplierMatch:
    """Result of supplier matching."""
    
    match_id: str
    supplier: Supplier
    rfq_id: str
    overall_score: float
    confidence: MatchConfidence
    rank: int
    criteria_scores: list[MatchScore] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    missing_certifications: list[str] = field(default_factory=list)
    matched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_recommended(self) -> bool:
        """Check if supplier is recommended."""
        return self.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]
    
    def get_score_breakdown(self) -> dict[str, float]:
        """Get score breakdown by criteria."""
        return {
            score.criteria.value: score.weighted_score
            for score in self.criteria_scores
        }


@dataclass
class MatchingResult:
    """Complete matching result."""
    
    result_id: str
    rfq_id: str
    matches: list[SupplierMatch]
    total_suppliers_evaluated: int
    matching_duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def recommended_suppliers(self) -> list[SupplierMatch]:
        """Get recommended suppliers."""
        return [m for m in self.matches if m.is_recommended]
    
    @property
    def top_match(self) -> SupplierMatch | None:
        """Get top match."""
        if self.matches:
            return self.matches[0]
        return None


# =============================================================================
# Capability Graph
# =============================================================================

class CapabilityGraph:
    """
    Graph representation of capabilities and their relationships.
    
    Nodes are capabilities, edges represent relationships like:
    - "requires" (capability A requires capability B)
    - "similar" (capabilities are semantically similar)
    - "complementary" (capabilities often used together)
    """
    
    def __init__(self):
        """Initialize capability graph."""
        self._nodes: dict[str, Capability] = {}
        self._edges: dict[str, list[tuple[str, str, float]]] = {}  # source -> [(target, type, weight)]
        self._reverse_edges: dict[str, list[tuple[str, str, float]]] = {}
        
        # Initialize with standard capability relationships
        self._init_standard_relationships()
    
    def _init_standard_relationships(self):
        """Initialize standard capability relationships."""
        # Standard relationships (capability pairs and their relationship type)
        standard_relationships = [
            ("cnc machining", "milling", "includes", 0.9),
            ("cnc machining", "turning", "includes", 0.9),
            ("milling", "cnc machining", "part_of", 0.9),
            ("turning", "cnc machining", "part_of", 0.9),
            ("welding", "assembly", "complementary", 0.7),
            ("inspection", "quality control", "similar", 0.95),
            ("coating", "surface treatment", "similar", 0.9),
            ("anodizing", "coating", "type_of", 0.85),
            ("powder coating", "coating", "type_of", 0.85),
            ("3d printing", "additive manufacturing", "similar", 0.95),
        ]
        
        for source, target, rel_type, weight in standard_relationships:
            self.add_relationship(source, target, rel_type, weight)
    
    def add_capability(self, capability: Capability):
        """Add capability to graph."""
        self._nodes[capability.name.lower()] = capability
    
    def add_relationship(
        self,
        source: str,
        target: str,
        relationship_type: str,
        weight: float = 1.0,
    ):
        """Add relationship between capabilities."""
        source_lower = source.lower()
        target_lower = target.lower()
        
        if source_lower not in self._edges:
            self._edges[source_lower] = []
        self._edges[source_lower].append((target_lower, relationship_type, weight))
        
        if target_lower not in self._reverse_edges:
            self._reverse_edges[target_lower] = []
        self._reverse_edges[target_lower].append((source_lower, relationship_type, weight))
    
    def get_related_capabilities(
        self,
        capability: str,
        max_depth: int = 2,
    ) -> list[tuple[str, float]]:
        """Get related capabilities with similarity scores."""
        capability_lower = capability.lower()
        visited: set[str] = set()
        related: list[tuple[str, float]] = []
        
        def traverse(node: str, depth: int, cumulative_weight: float):
            if depth > max_depth or node in visited:
                return
            
            visited.add(node)
            
            # Get outgoing edges
            for target, rel_type, weight in self._edges.get(node, []):
                if target not in visited:
                    new_weight = cumulative_weight * weight * (0.9 ** depth)
                    related.append((target, new_weight))
                    traverse(target, depth + 1, new_weight)
            
            # Get incoming edges for "similar" and "type_of" relationships
            for source, rel_type, weight in self._reverse_edges.get(node, []):
                if source not in visited and rel_type in ["similar", "type_of"]:
                    new_weight = cumulative_weight * weight * (0.9 ** depth)
                    related.append((source, new_weight))
                    traverse(source, depth + 1, new_weight)
        
        traverse(capability_lower, 0, 1.0)
        
        # Combine duplicate entries
        combined: dict[str, float] = {}
        for cap, score in related:
            if cap not in combined or combined[cap] < score:
                combined[cap] = score
        
        return sorted(combined.items(), key=lambda x: x[1], reverse=True)
    
    def calculate_similarity(self, cap1: str, cap2: str) -> float:
        """Calculate similarity between two capabilities."""
        cap1_lower = cap1.lower()
        cap2_lower = cap2.lower()
        
        # Exact match
        if cap1_lower == cap2_lower:
            return 1.0
        
        # Check synonyms
        for base, synonyms in CAPABILITY_SYNONYMS.items():
            all_terms = [base] + synonyms
            if cap1_lower in all_terms and cap2_lower in all_terms:
                return 0.95
        
        # Check graph relationships
        related = self.get_related_capabilities(cap1_lower)
        for cap, score in related:
            if cap == cap2_lower:
                return score
        
        # Substring matching
        if cap1_lower in cap2_lower or cap2_lower in cap1_lower:
            return 0.7
        
        # Word overlap
        words1 = set(cap1_lower.split())
        words2 = set(cap2_lower.split())
        if words1 & words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            return 0.5 * (intersection / union)
        
        return 0.0


# =============================================================================
# Semantic Matcher
# =============================================================================

class SemanticMatcher:
    """
    Semantic matching using text similarity and embeddings.
    
    Uses TF-IDF-like approach for lightweight semantic matching.
    """
    
    def __init__(self):
        """Initialize semantic matcher."""
        self._document_frequencies: dict[str, int] = {}
        self._total_documents = 0
        self._capability_graph = CapabilityGraph()
    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Convert to lowercase and split on non-alphanumeric
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        return words
    
    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        """Compute term frequency."""
        tf: dict[str, float] = {}
        total = len(tokens)
        
        if total == 0:
            return tf
        
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        
        # Normalize
        for token in tf:
            tf[token] = tf[token] / total
        
        return tf
    
    def _compute_idf(self, token: str) -> float:
        """Compute inverse document frequency."""
        if self._total_documents == 0:
            return 1.0
        
        df = self._document_frequencies.get(token, 0)
        if df == 0:
            return 1.0
        
        return math.log(self._total_documents / df) + 1
    
    def index_capabilities(self, suppliers: list[Supplier]):
        """Index supplier capabilities for better matching."""
        self._document_frequencies = {}
        self._total_documents = len(suppliers)
        
        for supplier in suppliers:
            # Get all text from supplier
            tokens = set()
            for cap in supplier.capabilities:
                tokens.update(self._tokenize(cap.name))
                for kw in cap.keywords:
                    tokens.update(self._tokenize(kw))
            
            # Update document frequencies
            for token in tokens:
                self._document_frequencies[token] = \
                    self._document_frequencies.get(token, 0) + 1
    
    def compute_similarity(
        self,
        requirement_text: str,
        capability_text: str,
    ) -> float:
        """Compute semantic similarity between requirement and capability."""
        req_tokens = self._tokenize(requirement_text)
        cap_tokens = self._tokenize(capability_text)
        
        if not req_tokens or not cap_tokens:
            return 0.0
        
        req_tf = self._compute_tf(req_tokens)
        cap_tf = self._compute_tf(cap_tokens)
        
        # Compute TF-IDF weighted cosine similarity
        common_tokens = set(req_tf.keys()) & set(cap_tf.keys())
        
        if not common_tokens:
            # Try capability graph for semantic similarity
            for req_token in req_tokens:
                for cap_token in cap_tokens:
                    sim = self._capability_graph.calculate_similarity(
                        req_token, cap_token
                    )
                    if sim > 0.5:
                        return sim * 0.8  # Discount for indirect match
            return 0.0
        
        numerator = 0.0
        req_norm = 0.0
        cap_norm = 0.0
        
        for token in set(req_tf.keys()) | set(cap_tf.keys()):
            idf = self._compute_idf(token)
            
            req_weight = req_tf.get(token, 0) * idf
            cap_weight = cap_tf.get(token, 0) * idf
            
            numerator += req_weight * cap_weight
            req_norm += req_weight ** 2
            cap_norm += cap_weight ** 2
        
        if req_norm == 0 or cap_norm == 0:
            return 0.0
        
        return numerator / (math.sqrt(req_norm) * math.sqrt(cap_norm))
    
    def match_capability(
        self,
        requirement: str,
        capabilities: list[Capability],
    ) -> tuple[float, Capability | None]:
        """Find best matching capability for a requirement."""
        best_score = 0.0
        best_match: Capability | None = None
        
        for cap in capabilities:
            # Combine name and keywords for matching
            cap_text = cap.name + " " + " ".join(cap.keywords)
            score = self.compute_similarity(requirement, cap_text)
            
            # Factor in proficiency
            score *= cap.proficiency_level
            
            if score > best_score:
                best_score = score
                best_match = cap
        
        return best_score, best_match


# =============================================================================
# Criteria Scorers
# =============================================================================

class CriteriaScorer(ABC):
    """Base class for criteria scoring."""
    
    @abstractmethod
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on this criteria."""
        ...


class CapabilityScorer(CriteriaScorer):
    """Score supplier on capability match."""
    
    def __init__(self, semantic_matcher: SemanticMatcher):
        """Initialize with semantic matcher."""
        self._matcher = semantic_matcher
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on capability match."""
        if not requirement.required_capabilities:
            return MatchScore(
                criteria=MatchingCriteria.CAPABILITY,
                score=0.5,
                weight=requirement.get_weights().get(MatchingCriteria.CAPABILITY, 0.3),
                weighted_score=0.15,
                explanation="No specific capabilities required",
            )
        
        # Score each required capability
        capability_scores = []
        matched_caps = []
        missing_caps = []
        
        for req_cap in requirement.required_capabilities:
            score, matched = self._matcher.match_capability(
                req_cap, supplier.capabilities
            )
            capability_scores.append(score)
            
            if score >= 0.5:
                matched_caps.append(req_cap)
            else:
                missing_caps.append(req_cap)
        
        # Average score
        avg_score = sum(capability_scores) / len(capability_scores)
        
        # Penalize for missing critical capabilities
        missing_penalty = len(missing_caps) / len(requirement.required_capabilities) * 0.3
        final_score = max(0, avg_score - missing_penalty)
        
        weight = requirement.get_weights().get(MatchingCriteria.CAPABILITY, 0.3)
        
        return MatchScore(
            criteria=MatchingCriteria.CAPABILITY,
            score=final_score,
            weight=weight,
            weighted_score=final_score * weight,
            explanation=f"Matched {len(matched_caps)}/{len(requirement.required_capabilities)} capabilities",
            details={
                "matched": matched_caps,
                "missing": missing_caps,
                "individual_scores": capability_scores,
            },
        )


class QualityScorer(CriteriaScorer):
    """Score supplier on quality."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on quality."""
        quality = supplier.performance.quality_score
        defect_penalty = supplier.performance.defect_rate * 2
        
        score = max(0, quality - defect_penalty)
        
        # Check if meets minimum
        meets_minimum = score >= requirement.minimum_quality_score
        
        weight = requirement.get_weights().get(MatchingCriteria.QUALITY, 0.2)
        
        explanation = f"Quality score: {quality:.0%}, Defect rate: {supplier.performance.defect_rate:.1%}"
        if not meets_minimum:
            explanation += f" (Below minimum {requirement.minimum_quality_score:.0%})"
        
        return MatchScore(
            criteria=MatchingCriteria.QUALITY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=explanation,
            details={
                "quality_score": quality,
                "defect_rate": supplier.performance.defect_rate,
                "meets_minimum": meets_minimum,
            },
        )


class DeliveryScorer(CriteriaScorer):
    """Score supplier on delivery performance."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on delivery."""
        on_time = supplier.performance.on_time_delivery_rate
        lead_time = supplier.lead_time_days
        
        score = on_time
        
        # Check against target lead time
        lead_time_ok = True
        if requirement.target_lead_time_days:
            if lead_time <= requirement.target_lead_time_days:
                # Meets target
                score *= 1.1  # Bonus
            else:
                # Exceeds target
                excess_ratio = lead_time / requirement.target_lead_time_days
                score *= (1 / excess_ratio)
                lead_time_ok = False
        
        score = min(1.0, score)
        weight = requirement.get_weights().get(MatchingCriteria.DELIVERY, 0.15)
        
        return MatchScore(
            criteria=MatchingCriteria.DELIVERY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"On-time: {on_time:.0%}, Lead time: {lead_time} days",
            details={
                "on_time_rate": on_time,
                "lead_time_days": lead_time,
                "meets_target_lead_time": lead_time_ok,
            },
        )


class PriceScorer(CriteriaScorer):
    """Score supplier on price competitiveness."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on price."""
        competitiveness = supplier.performance.price_competitiveness
        
        # Factor in minimum order value
        mov_penalty = 0.0
        if supplier.minimum_order_value > 0 and requirement.target_price:
            estimated_total = requirement.target_price * requirement.quantity
            if estimated_total < supplier.minimum_order_value:
                mov_penalty = 0.2
        
        score = max(0, competitiveness - mov_penalty)
        weight = requirement.get_weights().get(MatchingCriteria.PRICE, 0.15)
        
        return MatchScore(
            criteria=MatchingCriteria.PRICE,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"Price competitiveness: {competitiveness:.0%}",
            details={
                "competitiveness": competitiveness,
                "minimum_order_value": supplier.minimum_order_value,
                "mov_penalty": mov_penalty,
            },
        )


class ReliabilityScorer(CriteriaScorer):
    """Score supplier on reliability."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on reliability."""
        reliability = supplier.performance.reliability_score
        
        # Factor in tier
        tier_bonus = {
            SupplierTier.STRATEGIC: 0.1,
            SupplierTier.PREFERRED: 0.05,
            SupplierTier.APPROVED: 0.0,
            SupplierTier.PROBATIONARY: -0.1,
            SupplierTier.INACTIVE: -0.3,
        }
        
        score = min(1.0, reliability + tier_bonus.get(supplier.tier, 0))
        weight = requirement.get_weights().get(MatchingCriteria.RELIABILITY, 0.1)
        
        return MatchScore(
            criteria=MatchingCriteria.RELIABILITY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"Reliability: {reliability:.0%}, Tier: {supplier.tier.value}",
            details={
                "reliability_score": reliability,
                "tier": supplier.tier.value,
                "orders_completed": supplier.performance.orders_completed,
                "issues_reported": supplier.performance.issues_reported,
            },
        )


class CertificationScorer(CriteriaScorer):
    """Score supplier on certifications."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on certifications."""
        if not requirement.required_certifications:
            return MatchScore(
                criteria=MatchingCriteria.CERTIFICATION,
                score=0.5,
                weight=requirement.get_weights().get(MatchingCriteria.CERTIFICATION, 0.03),
                weighted_score=0.015,
                explanation="No specific certifications required",
            )
        
        matched = []
        missing = []
        
        for cert in requirement.required_certifications:
            if supplier.has_certification(cert):
                matched.append(cert)
            else:
                missing.append(cert)
        
        score = len(matched) / len(requirement.required_certifications)
        weight = requirement.get_weights().get(MatchingCriteria.CERTIFICATION, 0.03)
        
        return MatchScore(
            criteria=MatchingCriteria.CERTIFICATION,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"Certifications: {len(matched)}/{len(requirement.required_certifications)}",
            details={
                "matched": matched,
                "missing": missing,
            },
        )


class CapacityScorer(CriteriaScorer):
    """Score supplier on capacity."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on capacity."""
        capacity = supplier.maximum_capacity_units
        required = requirement.quantity
        
        if required <= 0:
            score = 1.0
        elif capacity >= required * 1.5:
            score = 1.0  # Has plenty of capacity
        elif capacity >= required:
            score = 0.8  # Can handle it
        elif capacity >= required * 0.5:
            score = 0.4  # Might struggle
        else:
            score = 0.1  # Cannot handle
        
        weight = requirement.get_weights().get(MatchingCriteria.CAPACITY, 0.05)
        
        return MatchScore(
            criteria=MatchingCriteria.CAPACITY,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"Capacity: {capacity:,} units (required: {required:,})",
            details={
                "max_capacity": capacity,
                "required": required,
                "utilization": required / capacity if capacity > 0 else float('inf'),
            },
        )


class LocationScorer(CriteriaScorer):
    """Score supplier on location."""
    
    def score(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> MatchScore:
        """Score supplier on location."""
        if not requirement.preferred_regions:
            return MatchScore(
                criteria=MatchingCriteria.LOCATION,
                score=0.5,
                weight=requirement.get_weights().get(MatchingCriteria.LOCATION, 0.02),
                weighted_score=0.01,
                explanation="No location preference",
            )
        
        # Check if supplier is in preferred region
        supplier_region = supplier.region.lower()
        in_preferred = any(
            region.lower() in supplier_region or supplier_region in region.lower()
            for region in requirement.preferred_regions
        )
        
        score = 1.0 if in_preferred else 0.3
        weight = requirement.get_weights().get(MatchingCriteria.LOCATION, 0.02)
        
        return MatchScore(
            criteria=MatchingCriteria.LOCATION,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            explanation=f"Region: {supplier.region}" + (" (preferred)" if in_preferred else ""),
            details={
                "supplier_region": supplier.region,
                "preferred_regions": requirement.preferred_regions,
                "in_preferred": in_preferred,
            },
        )


# =============================================================================
# Rank Aggregator
# =============================================================================

class RankAggregator:
    """Aggregate multiple rankings into a single ranking."""
    
    @staticmethod
    def borda_count(rankings: list[list[str]]) -> list[tuple[str, float]]:
        """
        Aggregate rankings using Borda count.
        
        Each ranking gives points: n-1 for first, n-2 for second, etc.
        """
        if not rankings:
            return []
        
        n = max(len(r) for r in rankings)
        scores: dict[str, float] = {}
        
        for ranking in rankings:
            for i, item in enumerate(ranking):
                points = n - i - 1
                scores[item] = scores.get(item, 0) + points
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    @staticmethod
    def kemeny_young_approx(
        rankings: list[list[str]],
        items: list[str],
    ) -> list[str]:
        """
        Approximate Kemeny-Young consensus ranking.
        
        Greedy algorithm based on pairwise preferences.
        """
        if not items:
            return []
        
        # Compute pairwise preferences
        preferences: dict[tuple[str, str], int] = {}
        
        for ranking in rankings:
            for i, item_i in enumerate(ranking):
                for j, item_j in enumerate(ranking):
                    if i < j:
                        key = (item_i, item_j)
                        preferences[key] = preferences.get(key, 0) + 1
        
        # Build consensus using greedy insertion
        result: list[str] = []
        remaining = set(items)
        
        while remaining:
            # Find item with highest pairwise wins against remaining
            best_item = None
            best_score = -1
            
            for item in remaining:
                score = 0
                for other in remaining:
                    if other != item:
                        score += preferences.get((item, other), 0)
                        score -= preferences.get((other, item), 0)
                
                if score > best_score:
                    best_score = score
                    best_item = item
            
            if best_item:
                result.append(best_item)
                remaining.remove(best_item)
            else:
                # Add any remaining
                result.extend(remaining)
                break
        
        return result


# =============================================================================
# Smart Supplier Matchmaker
# =============================================================================

class SmartSupplierMatchmaker:
    """
    AI-powered supplier matching engine.
    
    Combines capability graphs, semantic matching, and multi-criteria
    scoring to find optimal suppliers for RFQ requirements.
    """
    
    def __init__(self):
        """Initialize matchmaker."""
        self._suppliers: dict[str, Supplier] = {}
        self._capability_graph = CapabilityGraph()
        self._semantic_matcher = SemanticMatcher()
        
        # Initialize scorers
        self._scorers: dict[MatchingCriteria, CriteriaScorer] = {
            MatchingCriteria.CAPABILITY: CapabilityScorer(self._semantic_matcher),
            MatchingCriteria.QUALITY: QualityScorer(),
            MatchingCriteria.DELIVERY: DeliveryScorer(),
            MatchingCriteria.PRICE: PriceScorer(),
            MatchingCriteria.RELIABILITY: ReliabilityScorer(),
            MatchingCriteria.CERTIFICATION: CertificationScorer(),
            MatchingCriteria.CAPACITY: CapacityScorer(),
            MatchingCriteria.LOCATION: LocationScorer(),
        }
    
    def add_supplier(self, supplier: Supplier):
        """Add supplier to matchmaker."""
        self._suppliers[supplier.supplier_id] = supplier
        
        # Add capabilities to graph
        for cap in supplier.capabilities:
            self._capability_graph.add_capability(cap)
    
    def add_suppliers(self, suppliers: list[Supplier]):
        """Add multiple suppliers."""
        for supplier in suppliers:
            self.add_supplier(supplier)
        
        # Re-index semantic matcher
        self._semantic_matcher.index_capabilities(list(self._suppliers.values()))
    
    def remove_supplier(self, supplier_id: str):
        """Remove supplier."""
        if supplier_id in self._suppliers:
            del self._suppliers[supplier_id]
    
    def get_supplier(self, supplier_id: str) -> Supplier | None:
        """Get supplier by ID."""
        return self._suppliers.get(supplier_id)
    
    def _score_supplier(
        self,
        supplier: Supplier,
        requirement: RFQRequirement,
    ) -> list[MatchScore]:
        """Score supplier on all criteria."""
        scores = []
        
        for criteria, scorer in self._scorers.items():
            score = scorer.score(supplier, requirement)
            scores.append(score)
        
        return scores
    
    def _determine_confidence(
        self,
        overall_score: float,
        criteria_scores: list[MatchScore],
    ) -> MatchConfidence:
        """Determine match confidence."""
        if overall_score >= 0.8:
            return MatchConfidence.HIGH
        elif overall_score >= 0.6:
            return MatchConfidence.MEDIUM
        elif overall_score >= 0.4:
            return MatchConfidence.LOW
        else:
            return MatchConfidence.UNCERTAIN
    
    def _identify_strengths_weaknesses(
        self,
        criteria_scores: list[MatchScore],
    ) -> tuple[list[str], list[str]]:
        """Identify supplier strengths and weaknesses."""
        strengths = []
        weaknesses = []
        
        for score in criteria_scores:
            if score.score >= 0.8:
                strengths.append(f"{score.criteria.value.title()}: {score.explanation}")
            elif score.score < 0.5:
                weaknesses.append(f"{score.criteria.value.title()}: {score.explanation}")
        
        return strengths, weaknesses
    
    def _filter_suppliers(
        self,
        requirement: RFQRequirement,
    ) -> list[Supplier]:
        """Pre-filter suppliers based on hard constraints."""
        eligible = []
        
        for supplier in self._suppliers.values():
            # Must be active
            if not supplier.active:
                continue
            
            # Cannot be inactive tier
            if supplier.tier == SupplierTier.INACTIVE:
                continue
            
            # Check capacity
            if requirement.quantity > supplier.maximum_capacity_units * 2:
                continue
            
            eligible.append(supplier)
        
        return eligible
    
    def match(
        self,
        requirement: RFQRequirement,
        max_results: int = 10,
        use_rank_aggregation: bool = True,
    ) -> MatchingResult:
        """
        Find matching suppliers for requirement.
        
        Args:
            requirement: RFQ requirement
            max_results: Maximum number of results
            use_rank_aggregation: Use Borda count for final ranking
        
        Returns:
            MatchingResult with ranked suppliers
        """
        import time
        start_time = time.time()
        
        # Filter eligible suppliers
        eligible = self._filter_suppliers(requirement)
        
        if not eligible:
            return MatchingResult(
                result_id=str(uuid.uuid4()),
                rfq_id=requirement.rfq_id,
                matches=[],
                total_suppliers_evaluated=0,
                matching_duration_ms=(time.time() - start_time) * 1000,
            )
        
        # Score all suppliers
        supplier_scores: list[tuple[Supplier, list[MatchScore], float]] = []
        
        for supplier in eligible:
            criteria_scores = self._score_supplier(supplier, requirement)
            overall = sum(s.weighted_score for s in criteria_scores)
            supplier_scores.append((supplier, criteria_scores, overall))
        
        # Rank by each criteria for rank aggregation
        if use_rank_aggregation and len(supplier_scores) > 2:
            criteria_rankings: list[list[str]] = []
            
            for criteria in self._scorers:
                # Get scores for this criteria
                criteria_list = []
                for supplier, scores, _ in supplier_scores:
                    for s in scores:
                        if s.criteria == criteria:
                            criteria_list.append((supplier.supplier_id, s.score))
                            break
                
                # Sort by score
                criteria_list.sort(key=lambda x: x[1], reverse=True)
                criteria_rankings.append([x[0] for x in criteria_list])
            
            # Aggregate rankings
            aggregated = RankAggregator.borda_count(criteria_rankings)
            id_to_rank = {item[0]: i for i, item in enumerate(aggregated)}
            
            # Re-sort using aggregated ranking
            supplier_scores.sort(key=lambda x: id_to_rank.get(x[0].supplier_id, 999))
        else:
            # Sort by overall score
            supplier_scores.sort(key=lambda x: x[2], reverse=True)
        
        # Build matches
        matches = []
        
        for rank, (supplier, criteria_scores, overall) in enumerate(supplier_scores[:max_results]):
            confidence = self._determine_confidence(overall, criteria_scores)
            strengths, weaknesses = self._identify_strengths_weaknesses(criteria_scores)
            
            # Find missing capabilities/certifications
            capability_score = next(
                (s for s in criteria_scores if s.criteria == MatchingCriteria.CAPABILITY),
                None,
            )
            cert_score = next(
                (s for s in criteria_scores if s.criteria == MatchingCriteria.CERTIFICATION),
                None,
            )
            
            missing_caps = capability_score.details.get("missing", []) if capability_score else []
            missing_certs = cert_score.details.get("missing", []) if cert_score else []
            
            match = SupplierMatch(
                match_id=str(uuid.uuid4()),
                supplier=supplier,
                rfq_id=requirement.rfq_id,
                overall_score=overall,
                confidence=confidence,
                rank=rank + 1,
                criteria_scores=criteria_scores,
                strengths=strengths,
                weaknesses=weaknesses,
                missing_capabilities=missing_caps,
                missing_certifications=missing_certs,
            )
            matches.append(match)
        
        duration_ms = (time.time() - start_time) * 1000
        
        return MatchingResult(
            result_id=str(uuid.uuid4()),
            rfq_id=requirement.rfq_id,
            matches=matches,
            total_suppliers_evaluated=len(eligible),
            matching_duration_ms=duration_ms,
        )
    
    def find_alternative_suppliers(
        self,
        supplier_id: str,
        requirement: RFQRequirement,
        max_results: int = 5,
    ) -> list[SupplierMatch]:
        """Find alternative suppliers similar to specified supplier."""
        target = self.get_supplier(supplier_id)
        if not target:
            return []
        
        # Use target's capabilities as additional requirements
        enhanced_requirement = RFQRequirement(
            rfq_id=requirement.rfq_id,
            description=requirement.description,
            required_capabilities=requirement.required_capabilities + [
                cap.name for cap in target.capabilities
            ],
            required_certifications=requirement.required_certifications,
            quantity=requirement.quantity,
            target_price=requirement.target_price,
            target_lead_time_days=requirement.target_lead_time_days,
            preferred_regions=requirement.preferred_regions or [target.region],
            minimum_quality_score=requirement.minimum_quality_score,
            priority_weights=requirement.priority_weights,
        )
        
        # Find matches excluding target
        result = self.match(enhanced_requirement, max_results=max_results + 1)
        
        # Filter out target supplier
        alternatives = [
            m for m in result.matches
            if m.supplier.supplier_id != supplier_id
        ][:max_results]
        
        return alternatives
    
    def compare_suppliers(
        self,
        supplier_ids: list[str],
        requirement: RFQRequirement,
    ) -> dict[str, Any]:
        """Compare specific suppliers."""
        suppliers = [
            s for s in (self.get_supplier(sid) for sid in supplier_ids)
            if s is not None
        ]
        
        if not suppliers:
            return {"error": "No valid suppliers found"}
        
        comparisons = []
        
        for supplier in suppliers:
            criteria_scores = self._score_supplier(supplier, requirement)
            overall = sum(s.weighted_score for s in criteria_scores)
            
            comparisons.append({
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "overall_score": overall,
                "tier": supplier.tier.value,
                "scores": {
                    s.criteria.value: {
                        "score": s.score,
                        "weighted": s.weighted_score,
                    }
                    for s in criteria_scores
                },
            })
        
        # Sort by overall score
        comparisons.sort(key=lambda x: cast(float, x["overall_score"]), reverse=True)
        
        return {
            "rfq_id": requirement.rfq_id,
            "suppliers_compared": len(comparisons),
            "comparisons": comparisons,
            "recommended": comparisons[0]["supplier_id"] if comparisons else None,
        }
    
    def get_capability_gaps(
        self,
        requirement: RFQRequirement,
    ) -> dict[str, Any]:
        """Identify capability gaps in supplier base."""
        required = set(cap.lower() for cap in requirement.required_capabilities)
        
        # Check each capability coverage
        coverage: dict[str, list[str]] = {cap: [] for cap in required}
        
        for supplier in self._suppliers.values():
            for cap in required:
                if supplier.get_capability_match(cap) >= 0.5:
                    coverage[cap].append(supplier.name)
        
        gaps = []
        limited = []
        well_covered = []
        
        for cap, suppliers in coverage.items():
            if not suppliers:
                gaps.append(cap)
            elif len(suppliers) <= 2:
                limited.append({"capability": cap, "suppliers": suppliers})
            else:
                well_covered.append({"capability": cap, "supplier_count": len(suppliers)})
        
        return {
            "gaps": gaps,
            "limited_coverage": limited,
            "well_covered": well_covered,
            "total_capabilities_checked": len(required),
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_supplier_matchmaker(
    suppliers: list[Supplier] | None = None,
) -> SmartSupplierMatchmaker:
    """Create and initialize supplier matchmaker."""
    matchmaker = SmartSupplierMatchmaker()
    
    if suppliers:
        matchmaker.add_suppliers(suppliers)
    
    return matchmaker
