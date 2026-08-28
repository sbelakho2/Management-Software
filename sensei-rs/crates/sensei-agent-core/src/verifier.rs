//! The deterministic verifier (items 109, 114-115, 132): every factual
//! claim grounded, evidence current, conflicts surfaced, permissions
//! valid, calculations tool-backed.

use crate::claims::{validate_claims, Claim};
use crate::evidence::{EvidenceConflict, FreshnessClass};
use crate::tools::{PolicyEngine, ToolSpec};
use chrono::Utc;

/// Verifier verdicts (item 109).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    Pass,
    NeedsEvidence,
    StaleEvidence,
    Contradiction,
    PolicyViolation,
}

/// Verification outcome with details.
#[derive(Debug, Clone)]
pub struct Verification {
    pub verdict: Verdict,
    pub issues: Vec<String>,
}

/// Verify a drafted answer/action before it reaches the user (the verifier
/// cannot create new facts either — it only checks).
pub fn verify(
    claims: &[Claim],
    policy: &PolicyEngine,
    caller_permissions: &[String],
    tools: &[ToolSpec],
    conflicts: &[EvidenceConflict],
    freshness: &[(usize, FreshnessClass)], // claim index -> freshness class
) -> Verification {
    let mut issues = Vec::new();

    // 1. Claim structure: facts need evidence (item 98).
    for violation in validate_claims(claims) {
        issues.push(violation.reason);
    }

    // 2. Evidence freshness (item 114).
    for (idx, class) in freshness {
        if let Some(claim) = claims.get(*idx) {
            if let Some(max_age) = class.max_age() {
                let oldest = claim
                    .evidence_refs
                    .iter()
                    .map(|e| e.observed_at)
                    .min()
                    .unwrap_or(Utc::now());
                if Utc::now() - oldest > max_age {
                    issues.push(format!(
                        "Claim '{}' rests on evidence older than the {:?} freshness window",
                        claim.statement, class
                    ));
                }
            }
        }
    }

    // 3. Conflicts are surfaced, never resolved arbitrarily (item 115).
    for conflict in conflicts {
        issues.push(format!(
            "Evidence conflict on '{}': {} (v{}) says {} while {} (v{}) says {}",
            conflict.fact,
            conflict.source_a.source,
            conflict.source_a.version,
            conflict.value_a,
            conflict.source_b.source,
            conflict.source_b.version,
            conflict.value_b
        ));
    }

    // 4. Permissions: every proposed action's tool must be executable by
    //    the caller (the policy engine independently re-checks rights and
    //    approval policies).
    let ctx_perms: std::collections::HashSet<String> = caller_permissions.iter().cloned().collect();
    for claim in claims {
        if claim.kind == crate::claims::ClaimKind::ProposedAction {
            let tool = tools
                .iter()
                .find(|t| t.name == claim.deterministic_calculation.as_deref().unwrap_or(""));
            let ok = tool
                .map(|t| ctx_perms.contains(&t.required_permission) && !policy.approval_required(t))
                .unwrap_or(false);
            if !ok {
                issues.push(format!(
                    "Proposed action '{}' references a tool the caller may not execute \
                     (permission or approval policy)",
                    claim.statement
                ));
            }
        }
    }

    // 5. Tool arguments validity is enforced by the tool layer itself
    //    (schemas); the verifier only checks the above.

    let verdict = if issues.is_empty() {
        Verdict::Pass
    } else if issues.iter().any(|i| i.contains("Evidence conflict")) {
        Verdict::Contradiction
    } else if issues
        .iter()
        .any(|i| i.contains("may not execute") || i.contains("cannot"))
    {
        Verdict::PolicyViolation
    } else if issues.iter().any(|i| i.contains("freshness")) {
        Verdict::StaleEvidence
    } else {
        Verdict::NeedsEvidence
    };

    Verification { verdict, issues }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::claims::{claim_fixture, ClaimKind};
    use crate::evidence::EvidenceRef;
    use crate::tools::ToolRisk;
    use chrono::Utc;

    #[test]
    fn unsupported_fact_fails_verification() {
        let claims = vec![claim_fixture(ClaimKind::ObservedFact, vec![])];
        let policy = PolicyEngine::new(vec![], ToolRisk::ReadOnly);
        let v = verify(&claims, &policy, &[], &[], &[], &[]);
        assert_eq!(v.verdict, Verdict::NeedsEvidence);
    }

    #[test]
    fn conflict_is_surfaced() {
        let ev = vec![EvidenceRef::new("mes", 1, Utc::now())];
        let claims = vec![claim_fixture(ClaimKind::ObservedFact, ev)];
        let policy = PolicyEngine::new(vec![], ToolRisk::ReadOnly);
        let conflict = EvidenceConflict {
            fact: "produced_qty".to_string(),
            source_a: EvidenceRef::new("mes", 1, Utc::now()),
            source_b: EvidenceRef::new("erp", 1, Utc::now()),
            value_a: serde_json::json!(928),
            value_b: serde_json::json!(950),
        };
        let v = verify(&claims, &policy, &[], &[], &[conflict], &[]);
        assert_eq!(v.verdict, Verdict::Contradiction);
    }

    #[test]
    fn stale_evidence_is_flagged() {
        let old = Utc::now() - chrono::Duration::hours(3);
        let ev = vec![EvidenceRef::new("inventory", 1, old)];
        let claims = vec![claim_fixture(ClaimKind::ObservedFact, ev)];
        let policy = PolicyEngine::new(vec![], ToolRisk::ReadOnly);
        let v = verify(
            &claims,
            &policy,
            &[],
            &[],
            &[],
            &[(0, FreshnessClass::Minutes)],
        );
        assert_eq!(v.verdict, Verdict::StaleEvidence);
    }
}
