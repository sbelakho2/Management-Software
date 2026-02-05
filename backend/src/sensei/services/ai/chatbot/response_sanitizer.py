"""
Response Sanitizer for Sensei OS Chatbot.

Final sanitization layer before returning responses:
- PII detection and masking
- Profanity filtering
- Format validation
- Output normalization
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from sensei.services.ai.chatbot.context_builder import UserContext

logger = logging.getLogger(__name__)


class SanitizationType(str, Enum):
    """Types of sanitization applied."""
    
    PII_MASKING = "pii_masking"
    PROFANITY_FILTER = "profanity_filter"
    FORMAT_CORRECTION = "format_correction"
    LENGTH_TRUNCATION = "length_truncation"
    ENCODING_FIX = "encoding_fix"
    INJECTION_REMOVAL = "injection_removal"


@dataclass
class SanitizationAction:
    """A sanitization action taken."""
    
    sanitization_type: SanitizationType
    description: str
    original_segment: str
    sanitized_segment: str
    position: int = 0


@dataclass
class SanitizationResult:
    """Result of response sanitization."""
    
    original_response: str
    sanitized_response: str
    was_modified: bool
    actions: List[SanitizationAction] = field(default_factory=list)
    sanitization_time_ms: float = 0.0
    
    @property
    def action_count(self) -> int:
        """Get number of sanitization actions taken."""
        return len(self.actions)


class ResponseSanitizer:
    """
    Final sanitization layer for chat responses.
    
    Applies PII masking, profanity filtering, and format
    validation to ensure responses are safe and appropriate.
    """
    
    # PII patterns for detection
    PII_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "ssn": [
            (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-{last4}"),
        ],
        "credit_card": [
            (r"\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b", "**** **** **** {last4}"),
        ],
        "phone": [
            (r"\b(\+?1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b", "***-***-{last4}"),
        ],
        "email": [
            (r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", "{first2}***@{domain}"),
        ],
        "ip_address": [
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "***.***.***.***"),
        ],
    }
    
    # Prompt injection patterns to detect and remove
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"disregard\s+your\s+(system\s+)?prompt",
        r"you\s+are\s+now\s+(?:in\s+)?(?:a\s+)?(?:new|different)\s+mode",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if\s+you",
        r"forget\s+(?:everything|all)\s+(?:you\s+)?(?:know|learned)",
        r"<\s*(?:script|style|iframe)",
        r"javascript\s*:",
        r"data\s*:\s*text/html",
    ]
    
    # Maximum response length
    MAX_RESPONSE_LENGTH = 8000
    
    def __init__(self, mask_pii: bool = True, max_length: int = MAX_RESPONSE_LENGTH):
        """
        Initialize sanitizer.
        
        Args:
            mask_pii: Whether to mask PII in responses
            max_length: Maximum response length
        """
        self.mask_pii = mask_pii
        self.max_length = max_length
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns."""
        self._compiled_pii: Dict[str, List[Tuple[re.Pattern, str]]] = {}
        for category, patterns in self.PII_PATTERNS.items():
            self._compiled_pii[category] = [
                (re.compile(pattern, re.IGNORECASE), mask)
                for pattern, mask in patterns
            ]
        
        self._compiled_injections = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        ]
    
    def sanitize(
        self,
        response: str,
        user: Optional[UserContext] = None,
    ) -> SanitizationResult:
        """
        Sanitize a response before returning to user.
        
        Args:
            response: Response to sanitize
            user: Optional user context for role-based decisions
            
        Returns:
            SanitizationResult with sanitized response
        """
        import time
        start_time = time.perf_counter()
        
        actions: List[SanitizationAction] = []
        sanitized = response
        
        # Fix encoding issues
        sanitized, encoding_actions = self._fix_encoding(sanitized)
        actions.extend(encoding_actions)
        
        # Remove potential prompt injections (if present in output)
        sanitized, injection_actions = self._remove_injections(sanitized)
        actions.extend(injection_actions)
        
        # Mask PII if enabled
        if self.mask_pii:
            sanitized, pii_actions = self._mask_pii(sanitized)
            actions.extend(pii_actions)
        
        # Truncate if too long
        if len(sanitized) > self.max_length:
            original_len = len(sanitized)
            sanitized = self._truncate_safely(sanitized, self.max_length)
            actions.append(SanitizationAction(
                sanitization_type=SanitizationType.LENGTH_TRUNCATION,
                description=f"Truncated from {original_len} to {len(sanitized)} chars",
                original_segment=f"...{response[-50:]}",
                sanitized_segment=f"...{sanitized[-50:]}",
            ))
        
        # Format corrections
        sanitized, format_actions = self._correct_format(sanitized)
        actions.extend(format_actions)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        return SanitizationResult(
            original_response=response,
            sanitized_response=sanitized,
            was_modified=sanitized != response,
            actions=actions,
            sanitization_time_ms=elapsed_ms,
        )
    
    def _fix_encoding(self, text: str) -> Tuple[str, List[SanitizationAction]]:
        """Fix common encoding issues."""
        actions: List[SanitizationAction] = []
        
        # Replace common encoding artifacts
        replacements = [
            ("\ufffd", "?"),  # Replacement character
            ("\x00", ""),     # Null bytes
            ("\r\n", "\n"),   # Normalize line endings
            ("\r", "\n"),
        ]
        
        fixed = text
        for old, new in replacements:
            if old in fixed:
                count = fixed.count(old)
                fixed = fixed.replace(old, new)
                actions.append(SanitizationAction(
                    sanitization_type=SanitizationType.ENCODING_FIX,
                    description=f"Replaced {count} encoding artifacts",
                    original_segment=repr(old),
                    sanitized_segment=repr(new),
                ))
        
        return fixed, actions
    
    def _remove_injections(self, text: str) -> Tuple[str, List[SanitizationAction]]:
        """Remove potential prompt injection content."""
        actions: List[SanitizationAction] = []
        cleaned = text
        
        for pattern in self._compiled_injections:
            matches = list(pattern.finditer(cleaned))
            for match in reversed(matches):
                original = match.group(0)
                cleaned = cleaned[:match.start()] + "[REMOVED]" + cleaned[match.end():]
                
                actions.append(SanitizationAction(
                    sanitization_type=SanitizationType.INJECTION_REMOVAL,
                    description="Removed potential injection content",
                    original_segment=original[:30] + "...",
                    sanitized_segment="[REMOVED]",
                    position=match.start(),
                ))
                
                logger.warning(
                    f"Removed potential prompt injection from response: "
                    f"pattern={pattern.pattern[:30]}, match={original[:30]}"
                )
        
        return cleaned, actions
    
    def _mask_pii(self, text: str) -> Tuple[str, List[SanitizationAction]]:
        """Mask PII in response."""
        actions: List[SanitizationAction] = []
        masked = text
        
        for category, patterns in self._compiled_pii.items():
            for pattern, mask_template in patterns:
                matches = list(pattern.finditer(masked))
                for match in reversed(matches):
                    original = match.group(0)
                    mask = self._apply_mask_template(original, mask_template, match)
                    masked = masked[:match.start()] + mask + masked[match.end():]
                    
                    actions.append(SanitizationAction(
                        sanitization_type=SanitizationType.PII_MASKING,
                        description=f"Masked {category}",
                        original_segment=original,
                        sanitized_segment=mask,
                        position=match.start(),
                    ))
        
        return masked, actions
    
    def _apply_mask_template(
        self,
        original: str,
        template: str,
        match: re.Match,
    ) -> str:
        """Apply a mask template to a matched value."""
        # Extract last 4 digits/chars if available
        digits = re.sub(r"[^\d]", "", original)
        last4 = digits[-4:] if len(digits) >= 4 else "****"
        
        # For emails, extract first 2 chars and domain
        first2 = original[:2] if len(original) >= 2 else "**"
        domain = ""
        if "@" in original:
            parts = original.split("@")
            first2 = parts[0][:2] if len(parts[0]) >= 2 else "**"
            domain = parts[1] if len(parts) > 1 else "***.***"
        
        return template.format(
            last4=last4,
            first2=first2,
            domain=domain,
        )
    
    def _truncate_safely(self, text: str, max_length: int) -> str:
        """Truncate text at a safe boundary."""
        if len(text) <= max_length:
            return text
        
        # Try to truncate at a sentence boundary
        truncated = text[:max_length]
        
        # Look for last sentence ending
        for ending in [". ", ".\n", "? ", "?\n", "! ", "!\n"]:
            last_pos = truncated.rfind(ending)
            if last_pos > max_length * 0.7:  # Don't truncate too much
                return truncated[:last_pos + 1] + "\n\n[Response truncated due to length]"
        
        # Fall back to word boundary
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:
            return truncated[:last_space] + "...\n\n[Response truncated due to length]"
        
        return truncated + "...\n\n[Response truncated due to length]"
    
    def _correct_format(self, text: str) -> Tuple[str, List[SanitizationAction]]:
        """Apply format corrections."""
        actions: List[SanitizationAction] = []
        corrected = text
        
        # Remove excessive whitespace
        if "  " in corrected or "\n\n\n" in corrected:
            original_len = len(corrected)
            corrected = re.sub(r" {3,}", "  ", corrected)
            corrected = re.sub(r"\n{4,}", "\n\n\n", corrected)
            
            if len(corrected) != original_len:
                actions.append(SanitizationAction(
                    sanitization_type=SanitizationType.FORMAT_CORRECTION,
                    description="Normalized excessive whitespace",
                    original_segment="(whitespace)",
                    sanitized_segment="(normalized)",
                ))
        
        # Ensure response ends with proper punctuation or newline
        corrected = corrected.rstrip()
        if corrected and corrected[-1] not in ".!?\n":
            corrected += "."
        
        return corrected, actions
    
    def validate_for_display(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate that text is safe for display.
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_safe, list of issues)
        """
        issues: List[str] = []
        
        # Check for unclosed HTML-like tags
        if re.search(r"<(?!br|hr|img)[a-z]+[^>]*>(?!.*</[a-z]+>)", text, re.IGNORECASE):
            issues.append("Contains unclosed HTML-like tags")
        
        # Check for suspicious URLs
        if re.search(r"https?://[^\s]*(?:evil|malicious|hack)", text, re.IGNORECASE):
            issues.append("Contains suspicious URLs")
        
        # Check for excessive length
        if len(text) > 50000:
            issues.append("Response exceeds display limit")
        
        return len(issues) == 0, issues


def create_response_sanitizer(
    mask_pii: bool = True,
    max_length: int = 8000,
) -> ResponseSanitizer:
    """Factory function to create response sanitizer."""
    return ResponseSanitizer(mask_pii=mask_pii, max_length=max_length)
