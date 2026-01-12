"""A3 reasoning gates.

Implements lightweight, deterministic validation checks for A3 section updates.

Goal:
- Challenge inputs that contradict core Lean/TPS principles
- Be fully testable without external model dependencies

The gates are intentionally conservative: they only BLOCK when the input is
strongly suggestive of a known anti-pattern (e.g., "add buffer inventory" as a
countermeasure). Other issues are WARNINGs and can be surfaced by the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class GateSeverity(str, Enum):
    WARNING = "warning"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class GateIssue:
    code: str
    severity: GateSeverity
    message: str
    questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "questions": list(self.questions),
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(n in text for n in needles)


def _extract_whys(structured_content: Any) -> list[str]:
    """Extract likely 5-Why chain strings from various JSON shapes."""

    if not structured_content or not isinstance(structured_content, dict):
        return []

    for key in ("whys", "five_whys", "5whys", "fiveWhys"):
        raw = structured_content.get(key)
        if not raw:
            continue

        if isinstance(raw, list):
            whys: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    whys.append(item)
                elif isinstance(item, dict):
                    for subkey in ("why", "text", "cause", "answer"):
                        value = item.get(subkey)
                        if isinstance(value, str) and value.strip():
                            whys.append(value)
                            break
            return [w for w in whys if w.strip()]

    return []


def evaluate_a3_section_update(
    *,
    section_type: str,
    content: str | None,
    structured_content: Any,
) -> list[GateIssue]:
    """Evaluate an A3 section update against deterministic TPS/Lean gates."""

    section_type_norm = _normalize(section_type)
    content_norm = _normalize(content)

    combined = content_norm
    whys = _extract_whys(structured_content)
    if whys:
        combined = combined + " " + " ".join(_normalize(w) for w in whys)

    issues: list[GateIssue] = []

    # ---------------------------------------------------------------------
    # Root cause (5-Whys) principles: avoid "blame the person" root causes.
    # ---------------------------------------------------------------------
    if section_type_norm in {"root_cause", "root cause", "rootcause"}:
        blame_terms = (
            "operator error",
            "careless",
            "didn't follow",
            "did not follow",
            "negligent",
            "lazy",
            "human error",
        )
        if _contains_any(combined, blame_terms):
            issues.append(
                GateIssue(
                    code="TPS_ROOT_CAUSE_BLAME_PERSON",
                    severity=GateSeverity.WARNING,
                    message=(
                        "The root cause reads like person-blame. In TPS, treat this as a "
                        "signal to investigate the process/system that allowed the error."
                    ),
                    questions=(
                        "What in the process made the mistake possible?",
                        "What control or poka-yoke could prevent recurrence?",
                        "What standard work or visual cue was missing or unclear?",
                    ),
                )
            )

        # If user wrote countermeasures in the root-cause section, nudge.
        countermeasure_terms = (
            "train",
            "retrain",
            "hire",
            "overtime",
            "add inspection",
            "100% inspection",
            "double check",
        )
        if _contains_any(combined, countermeasure_terms):
            issues.append(
                GateIssue(
                    code="TPS_ROOT_CAUSE_CONTAINS_COUNTERMEASURE",
                    severity=GateSeverity.WARNING,
                    message=(
                        "This section contains countermeasures. Root cause should describe "
                        "the underlying system condition, not the fix."
                    ),
                    questions=(
                        "Can you restate the underlying condition without proposing a solution?",
                        "What evidence at gemba supports this as the true cause?",
                    ),
                )
            )

        # 5-Whys depth check if structured chain exists.
        if whys and len(whys) < 3:
            issues.append(
                GateIssue(
                    code="TPS_5WHYS_TOO_SHALLOW",
                    severity=GateSeverity.WARNING,
                    message="5-Whys chain is short; consider going deeper before locking the cause.",
                    questions=(
                        "Why does that condition exist?",
                        "What upstream process created that condition?",
                    ),
                )
            )

    # ---------------------------------------------------------------------
    # Countermeasures principles: avoid adding waste as a "fix".
    # ---------------------------------------------------------------------
    if section_type_norm in {"countermeasures", "countermeasure"}:
        # Strong anti-pattern: "add buffer/inventory" as countermeasure.
        # Allow "reduce inventory" explicitly.
        if (
            _contains_any(combined, ("increase inventory", "add inventory", "buffer stock", "add buffer", "safety stock"))
            and not _contains_any(combined, ("reduce inventory", "lower inventory", "decrease inventory"))
        ):
            issues.append(
                GateIssue(
                    code="TPS_COUNTERMEASURE_ADDS_INVENTORY",
                    severity=GateSeverity.BLOCK,
                    message=(
                        "The countermeasure proposes adding buffer inventory. In TPS this often "
                        "hides problems instead of removing root causes."
                    ),
                    questions=(
                        "What root cause are we trying to hide with inventory?",
                        "What flow/stability change would remove the need for a buffer?",
                        "Can we implement SMED, heijunka, or poka-yoke instead?",
                    ),
                )
            )

        # Softer anti-patterns: inspection-only or speed-up directives.
        inspection_terms = (
            "100% inspection",
            "double check",
            "add inspection",
            "inspect",
        )
        if _contains_any(combined, inspection_terms) and not _contains_any(
            combined, ("poka-yoke", "mistake proof", "error-proof")
        ):
            issues.append(
                GateIssue(
                    code="TPS_COUNTERMEASURE_INSPECTION_ONLY",
                    severity=GateSeverity.WARNING,
                    message=(
                        "Inspection detects defects but doesn’t prevent them. Prefer prevention "
                        "(jidoka/poka-yoke) where possible."
                    ),
                    questions=(
                        "How can we prevent the defect at the source?",
                        "What can we stop automatically when an abnormality occurs?",
                    ),
                )
            )

        speed_terms = ("work faster", "move faster", "go faster")
        if _contains_any(combined, speed_terms):
            issues.append(
                GateIssue(
                    code="TPS_COUNTERMEASURE_SPEED_UP",
                    severity=GateSeverity.WARNING,
                    message=(
                        "“Work faster” is not a reliable countermeasure. Improve the process "
                        "(standard work, layout, tooling) instead."
                    ),
                    questions=(
                        "What motion/waiting waste can we remove?",
                        "What standard work change would reduce cycle time safely?",
                    ),
                )
            )

    return issues


def build_gate_payload(issues: list[GateIssue]) -> dict[str, Any]:
    status = "pass" if not issues else (
        "block" if any(i.severity == GateSeverity.BLOCK for i in issues) else "warning"
    )

    return {
        "status": status,
        "checked_at": _now_iso(),
        "issues": [i.to_dict() for i in issues],
    }
