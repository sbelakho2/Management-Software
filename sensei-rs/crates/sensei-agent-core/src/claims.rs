//! The Claim Ledger (item 97): every important claim is classified, and a
//! factual claim about live tenant data MUST carry evidence refs (item 98).

use crate::evidence::EvidenceRef;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Classification of a claim (item 97).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ClaimKind {
    /// Directly measured/observed ("Cell 3 median cycle = 71.2 s").
    ObservedFact,
    /// Computed from observed facts ("cycle exceeds takt by 7.2 s").
    DerivedFact,
    /// Untested explanation — never asserted as fact.
    Hypothesis,
    /// A proposed action.
    Recommendation,
    /// A concrete proposed write (goes through the approval policy).
    ProposedAction,
}

/// One claim in the ledger.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claim {
    pub id: uuid::Uuid,
    pub kind: ClaimKind,
    pub statement: String,
    /// Evidence for facts; empty for hypotheses/recommendations (which
    /// must not be presented as facts).
    pub evidence_refs: Vec<EvidenceRef>,
    /// For DerivedFact: the deterministic calculation that produced it.
    pub deterministic_calculation: Option<String>,
    /// Hypotheses may carry a confidence; facts never do.
    pub confidence: Option<f64>,
    pub created_at: DateTime<Utc>,
}

/// Rules (item 98): a factual claim about live data requires evidence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaimViolation {
    pub claim_id: uuid::Uuid,
    pub reason: String,
}

/// Validate a claim ledger: facts without evidence are violations;
/// hypotheses must not be marked as facts.
pub fn validate_claims(claims: &[Claim]) -> Vec<ClaimViolation> {
    let mut violations = Vec::new();
    for claim in claims {
        match claim.kind {
            ClaimKind::ObservedFact | ClaimKind::DerivedFact => {
                if claim.evidence_refs.is_empty() {
                    violations.push(ClaimViolation {
                        claim_id: claim.id,
                        reason: format!(
                            "Factual claim without evidence: '{}' — no EvidenceRef, so it must be \\
                             queried through a tool, stated as unavailable, or labeled a hypothesis",
                            claim.statement
                        ),
                    });
                }
                if claim.confidence.is_some() {
                    violations.push(ClaimViolation {
                        claim_id: claim.id,
                        reason: "Facts do not carry confidence; only hypotheses do".to_string(),
                    });
                }
                if claim.kind == ClaimKind::DerivedFact && claim.deterministic_calculation.is_none()
                {
                    violations.push(ClaimViolation {
                        claim_id: claim.id,
                        reason: "Derived fact without a deterministic calculation".to_string(),
                    });
                }
            }
            ClaimKind::Hypothesis | ClaimKind::Recommendation | ClaimKind::ProposedAction => {
                if !claim.evidence_refs.is_empty() {
                    // Hypotheses may cite supporting observations — that is
                    // fine; nothing to flag here.
                }
            }
        }
    }
    violations
}

/// Test helper: build a claim (also used by the verifier tests).
#[cfg(test)]
pub(crate) fn claim_fixture(kind: ClaimKind, evidence: Vec<EvidenceRef>) -> Claim {
    Claim {
        id: uuid::Uuid::new_v4(),
        kind,
        statement: "test".to_string(),
        evidence_refs: evidence,
        deterministic_calculation: None,
        confidence: None,
        created_at: Utc::now(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::EvidenceRef;
    use chrono::Utc;

    fn claim(kind: ClaimKind, evidence: Vec<EvidenceRef>) -> Claim {
        claim_fixture(kind, evidence)
    }

    #[test]
    fn facts_require_evidence() {
        let claims = vec![claim(ClaimKind::ObservedFact, vec![])];
        assert!(!validate_claims(&claims).is_empty());
    }

    #[test]
    fn evidenced_facts_pass() {
        let ev = vec![EvidenceRef::new("cycle_snapshot:CS-1", 1, Utc::now())];
        let claims = vec![claim(ClaimKind::ObservedFact, ev)];
        assert!(validate_claims(&claims).is_empty());
    }

    #[test]
    fn hypotheses_do_not_require_evidence() {
        let claims = vec![claim(ClaimKind::Hypothesis, vec![])];
        assert!(validate_claims(&claims).is_empty());
    }
}
