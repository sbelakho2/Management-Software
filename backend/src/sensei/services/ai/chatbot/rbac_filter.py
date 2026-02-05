"""
RBAC Response Filter for Sensei OS Chatbot.

Filters LLM responses to ensure RBAC compliance:
- Removes data the user shouldn't see
- Masks sensitive fields
- Validates response against permissions
- Logs access attempts for audit
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from sensei.services.ai.chatbot.context_builder import UserContext

logger = logging.getLogger(__name__)


class FilterAction(str, Enum):
    """Actions taken by the filter."""
    
    ALLOWED = "allowed"
    MASKED = "masked"
    REDACTED = "redacted"
    BLOCKED = "blocked"


class ViolationType(str, Enum):
    """Types of RBAC violations detected."""
    
    UNAUTHORIZED_DATA = "unauthorized_data"
    SENSITIVE_FIELD = "sensitive_field"
    PII_EXPOSURE = "pii_exposure"
    FINANCIAL_DATA = "financial_data"
    EXECUTIVE_ONLY = "executive_only"
    CROSS_TENANT = "cross_tenant"


@dataclass
class FilterViolation:
    """A detected RBAC violation."""
    
    violation_type: ViolationType
    description: str
    original_content: str
    action_taken: FilterAction
    field_name: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class FilterResult:
    """Result of filtering an LLM response."""
    
    original_response: str
    filtered_response: str
    was_modified: bool
    violations: List[FilterViolation] = field(default_factory=list)
    filter_time_ms: float = 0.0
    audit_id: UUID = field(default_factory=uuid4)
    
    @property
    def violation_count(self) -> int:
        """Get number of violations detected."""
        return len(self.violations)
    
    @property
    def was_blocked(self) -> bool:
        """Check if response was fully blocked."""
        return any(v.action_taken == FilterAction.BLOCKED for v in self.violations)


class RBACResponseFilter:
    """
    Filters LLM responses for RBAC compliance.
    
    Scans response text for sensitive patterns and applies
    appropriate masking or redaction based on user permissions.
    """
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "ssn": [
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
            (r"\b\d{9}\b(?=.*(?:ssn|social))", "SSN"),
        ],
        "credit_card": [
            (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "credit_card"),
            (r"\b\d{16}\b", "credit_card"),
        ],
        "bank_account": [
            (r"\baccount[:\s#]*\d{8,17}\b", "bank_account"),
            (r"\brouting[:\s#]*\d{9}\b", "routing_number"),
        ],
        "salary": [
            (r"\b(?:salary|wage|pay|compensation)[:\s]*\$[\d,]+(?:\.\d{2})?\b", "salary"),
            (r"\$[\d,]+(?:\.\d{2})?\s*(?:per\s+(?:hour|year|month|week)|annually|monthly)\b", "salary"),
        ],
        "email": [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
        ],
        "phone": [
            (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone"),
        ],
        "cost_margin": [
            (r"\b(?:margin|markup|profit)[:\s]*[\d.]+%\b", "margin"),
            (r"\b(?:cost|price)\s+breakdown\b", "cost_breakdown"),
            (r"\b(?:unit\s+cost|cogs)[:\s]*\$[\d,]+\b", "cost"),
        ],
    }
    
    # Role-based access for sensitive data types
    SENSITIVE_DATA_ACCESS: Dict[str, Set[str]] = {
        "ssn": {"admin", "hr"},
        "credit_card": {"admin", "finance"},
        "bank_account": {"admin", "finance"},
        "salary": {"admin", "hr", "ceo", "gm"},
        "email": {"*"},  # Generally accessible but may need masking
        "phone": {"*"},  # Generally accessible
        "cost_margin": {"admin", "ceo", "gm", "exec", "finance", "estimator"},
    }
    
    # Keywords that suggest executive-only information
    EXECUTIVE_KEYWORDS = [
        "profit margin", "net profit", "gross margin", "ebitda",
        "competitive analysis", "strategic", "acquisition",
        "employee compensation", "executive salary", "bonus structure",
        "confidential", "restricted", "proprietary",
    ]
    
    # Keywords that suggest cross-tenant data
    CROSS_TENANT_KEYWORDS = [
        "other customer", "competitor", "their account",
        "all customers", "all users", "everyone's",
    ]
    
    def __init__(self):
        """Initialize RBAC filter."""
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns."""
        self._compiled_patterns: Dict[str, List[Tuple[re.Pattern, str]]] = {}
        for category, patterns in self.SENSITIVE_PATTERNS.items():
            self._compiled_patterns[category] = [
                (re.compile(pattern, re.IGNORECASE), label)
                for pattern, label in patterns
            ]
    
    def filter_response(
        self,
        response: str,
        user: UserContext,
    ) -> FilterResult:
        """
        Filter an LLM response for RBAC compliance.
        
        Args:
            response: Raw LLM response text
            user: User context for permission checking
            
        Returns:
            FilterResult with filtered response and violations
        """
        import time
        start_time = time.perf_counter()
        
        violations: List[FilterViolation] = []
        filtered = response
        
        # Check for sensitive patterns
        filtered, pattern_violations = self._filter_sensitive_patterns(filtered, user)
        violations.extend(pattern_violations)
        
        # Check for executive-only content
        filtered, exec_violations = self._filter_executive_content(filtered, user)
        violations.extend(exec_violations)
        
        # Check for cross-tenant data leakage
        filtered, tenant_violations = self._filter_cross_tenant(filtered, user)
        violations.extend(tenant_violations)
        
        # Log violations if any
        if violations:
            logger.warning(
                f"RBAC filter detected {len(violations)} violations for user {user.email}: "
                f"types={[v.violation_type.value for v in violations]}"
            )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return FilterResult(
            original_response=response,
            filtered_response=filtered,
            was_modified=filtered != response,
            violations=violations,
            filter_time_ms=elapsed_ms,
        )
    
    def _filter_sensitive_patterns(
        self,
        text: str,
        user: UserContext,
    ) -> Tuple[str, List[FilterViolation]]:
        """Filter sensitive data patterns."""
        violations: List[FilterViolation] = []
        filtered = text
        
        for category, patterns in self._compiled_patterns.items():
            # Check if user can see this category
            allowed_roles = self.SENSITIVE_DATA_ACCESS.get(category, set())
            can_see = (
                "*" in allowed_roles or
                user.is_admin or
                user.has_any_role(list(allowed_roles))
            )
            
            if not can_see:
                for pattern, label in patterns:
                    matches = list(pattern.finditer(filtered))
                    for match in reversed(matches):  # Reverse to preserve positions
                        original = match.group(0)
                        masked = self._mask_value(original, category)
                        filtered = filtered[:match.start()] + masked + filtered[match.end():]
                        
                        violations.append(FilterViolation(
                            violation_type=ViolationType.SENSITIVE_FIELD,
                            description=f"Masked {label} - user lacks {category} access",
                            original_content=original,
                            action_taken=FilterAction.MASKED,
                            field_name=label,
                        ))
        
        return filtered, violations
    
    def _filter_executive_content(
        self,
        text: str,
        user: UserContext,
    ) -> Tuple[str, List[FilterViolation]]:
        """Filter executive-only content."""
        violations: List[FilterViolation] = []
        
        if user.is_executive:
            return text, violations
        
        text_lower = text.lower()
        for keyword in self.EXECUTIVE_KEYWORDS:
            if keyword in text_lower:
                # Find sentences containing the keyword and redact them
                sentences = text.split(". ")
                filtered_sentences = []
                
                for sentence in sentences:
                    if keyword in sentence.lower():
                        violations.append(FilterViolation(
                            violation_type=ViolationType.EXECUTIVE_ONLY,
                            description=f"Redacted executive-only content: {keyword}",
                            original_content=sentence[:50] + "...",
                            action_taken=FilterAction.REDACTED,
                        ))
                        filtered_sentences.append("[This information requires executive access]")
                    else:
                        filtered_sentences.append(sentence)
                
                text = ". ".join(filtered_sentences)
        
        return text, violations
    
    def _filter_cross_tenant(
        self,
        text: str,
        user: UserContext,
    ) -> Tuple[str, List[FilterViolation]]:
        """Filter cross-tenant data leakage."""
        violations: List[FilterViolation] = []
        
        if user.is_admin:
            return text, violations
        
        text_lower = text.lower()
        for keyword in self.CROSS_TENANT_KEYWORDS:
            if keyword in text_lower:
                violations.append(FilterViolation(
                    violation_type=ViolationType.CROSS_TENANT,
                    description=f"Warning: potential cross-tenant reference: {keyword}",
                    original_content=keyword,
                    action_taken=FilterAction.ALLOWED,  # Just warn, don't block
                ))
        
        return text, violations
    
    def _mask_value(self, value: str, category: str) -> str:
        """Mask a sensitive value appropriately."""
        if category == "ssn":
            # Show last 4 digits
            return "***-**-" + value[-4:] if len(value) >= 4 else "***-**-****"
        elif category == "credit_card":
            # Show last 4 digits
            clean = re.sub(r"[- ]", "", value)
            return "**** **** **** " + clean[-4:] if len(clean) >= 4 else "**** **** **** ****"
        elif category == "bank_account":
            return "[ACCOUNT ***]"
        elif category == "salary":
            return "[COMPENSATION REDACTED]"
        elif category == "email":
            if "@" in value:
                parts = value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
            return "***@***.***"
        elif category == "phone":
            return "***-***-" + value[-4:] if len(value) >= 4 else "***-***-****"
        elif category == "cost_margin":
            return "[FINANCIAL DATA REDACTED]"
        else:
            return "[REDACTED]"
    
    def validate_response(
        self,
        response: str,
        user: UserContext,
        intent_type: str,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a response is appropriate for the user.
        
        Args:
            response: Response to validate
            user: User context
            intent_type: Type of intent being served
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues: List[str] = []
        
        # Check response length
        if len(response) > 10000:
            issues.append("Response exceeds maximum length")
        
        # Check for obvious hallucination patterns
        hallucination_patterns = [
            r"I don't have access to .* but here is",
            r"I'm making up",
            r"I'm guessing",
            r"I cannot verify but",
        ]
        
        for pattern in hallucination_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(f"Potential hallucination detected: {pattern}")
        
        # Validate intent-specific requirements
        if intent_type == "email_draft":
            if "subject:" not in response.lower() and "subject line:" not in response.lower():
                issues.append("Email draft missing subject line")
        
        return len(issues) == 0, issues


def create_rbac_filter() -> RBACResponseFilter:
    """Factory function to create RBAC filter."""
    return RBACResponseFilter()
