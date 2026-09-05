//! The deterministic verifier (items 109, 114-115, 132): every factual
//! claim grounded, evidence current, conflicts surfaced, permissions
//! valid, calculations tool-backed.
//!
//! Thirtieth audit item 23: measured claims are checked against TYPED
//! evidence — exact object, exact attribute, exact site/work-center
//! scope, source-time validity/freshness, unit compatibility and the
//! claimed operator/value — so the verdict never depends on the language
//! the claim was written in. Derived claims are checked against the
//! server's recomputation of the derivation program.

use crate::claims::{validate_claims, Claim};
use crate::context::{ClaimAssertion, ClaimOperator, DerivedAssertion};
use crate::evidence::{EvidenceConflict, FreshnessClass};
use crate::facts::RecomputedDerivation;
use crate::tools::{PolicyEngine, ToolSpec};
use chrono::{DateTime, Utc};
use uuid::Uuid;

/// Tolerance policy for derived results: relative to the recomputed
/// value's magnitude — the deterministic program's decimal math can
/// legitimately round-trip through f64 at the ~1e-15 level, but a
/// claimed 0.99 for a recomputed 0.972222… is nowhere near.
pub const DERIVED_RESULT_RELATIVE_TOLERANCE: f64 = 1e-6;

/// Time-skew policy for claim validity: a claim's asserted valid time
/// must coincide with the cited evidence's own observation time within
/// this window; claims about a time the evidence did NOT observe cannot
/// be measured by that evidence.
pub const CLAIM_TIME_SKEW_SECS: i64 = 60;

/// The maximum age a claim's asserted time may have behind "now" before
/// the claim is out-of-freshness. Claim times in the future (beyond the
/// skew window) are rejected as unverifiable.
pub const CLAIM_TIME_FUTURE_SKEW_SECS: i64 = 60;

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

// ═══════════════════════════════════════════════════════════════════════
// Thirtieth audit item 23 — typed assertion verification
// ═══════════════════════════════════════════════════════════════════════

/// Normalize a unit string for compatibility comparison: case-folded,
/// trimmed; plural and singular forms are equivalent ("units" == "unit").
fn normalize_unit(u: &str) -> String {
    let t = u.trim().to_lowercase();
    if t.ends_with('s') && t.len() > 1 {
        t[..t.len() - 1].to_string()
    } else {
        t
    }
}

/// Unit policy for measured claims: the claim MUST state the unit of its
/// claimed value whenever the evidence carries one, and the two must be
/// compatible (singular/plural-insensitive, case-insensitive). Unknown
/// (missing) units on either side are a rejection, not a pass — an
/// unverifiable unit dimension can never verify a claim.
pub fn units_compatible(claimed: Option<&str>, evidence: Option<&str>) -> Result<(), String> {
    match (claimed.map(normalize_unit), evidence.map(normalize_unit)) {
        (None, None) => Ok(()),
        (Some(c), Some(e)) if c == e => Ok(()),
        (Some(c), Some(e)) => Err(format!(
            "unit mismatch: the claim is in '{c}' but the evidence value is in '{e}'"
        )),
        (None, Some(e)) => Err(format!(
            "the claim does not state a unit but the evidence value is in '{e}'"
        )),
        (Some(c), None) => Err(format!(
            "the claim is in '{c}' but the evidence value carries no unit to compare"
        )),
    }
}

/// Best-effort numeric view of a JSON value. Strings are NOT coerced to
/// numbers — a "12" string claim never compares equal to the number 12.
fn numeric(v: &serde_json::Value) -> Option<f64> {
    v.as_f64()
}

fn finite(v: f64) -> bool {
    v.is_finite()
}

/// Deterministic operator semantics: the operator is satisfied when the
/// EVIDENCE value (the "actual" side) satisfies the operator against the
/// claimed value — a claim "completed ≤ 10 units" holds iff
/// actual ≤ 10. Returns Ok(true) when the claimed operator/value is
/// satisfied, Ok(false) when it is not, Err for inapplicable comparisons
/// (non-numeric operands where the operator requires numbers) — an
/// inapplicable comparison is a rejection, never a pass.
///
/// `Range { min, max }` asserts the evidence value lies within the
/// inclusive bounds. `Approximate { tolerance }` asserts an ABSOLUTE
/// numeric tolerance around the claimed value.
pub fn operator_satisfied(
    op: &ClaimOperator,
    claimed: &serde_json::Value,
    actual: &serde_json::Value,
) -> Result<bool, String> {
    let err_inapplicable = |kind: &str| {
        format!(
            "claim value {claimed} and evidence value {actual} are not both {kind} — \
             the '{:?}' comparison cannot be evaluated",
            op
        )
    };
    match op {
        ClaimOperator::Equal => {
            if let (Some(c), Some(a)) = (numeric(claimed), numeric(actual)) {
                if !finite(c) || !finite(a) {
                    return Err(err_inapplicable("finite numbers"));
                }
                Ok(c == a)
            } else if let (Some(c), Some(a)) = (claimed.as_str(), actual.as_str()) {
                Ok(c == a)
            } else if claimed.is_number() != actual.is_number() {
                // A number never equals a string (or vice versa) — the
                // comparison is inapplicable, never silently false-equal.
                Err(err_inapplicable("the same kind of value"))
            } else {
                Ok(claimed == actual)
            }
        }
        ClaimOperator::LessThan
        | ClaimOperator::LessThanOrEqual
        | ClaimOperator::GreaterThan
        | ClaimOperator::GreaterThanOrEqual => {
            let (Some(c), Some(a)) = (numeric(claimed), numeric(actual)) else {
                return Err(err_inapplicable("numbers"));
            };
            if !finite(c) || !finite(a) {
                return Err(err_inapplicable("finite numbers"));
            }
            Ok(match op {
                ClaimOperator::LessThan => a < c,
                ClaimOperator::LessThanOrEqual => a <= c,
                ClaimOperator::GreaterThan => a > c,
                ClaimOperator::GreaterThanOrEqual => a >= c,
                _ => unreachable!(),
            })
        }
        ClaimOperator::Range { min, max } => {
            let (Some(a), Some(lo), Some(hi)) = (numeric(actual), numeric(min), numeric(max))
            else {
                return Err(err_inapplicable("numbers"));
            };
            if !finite(a) || !finite(lo) || !finite(hi) {
                return Err(err_inapplicable("finite numbers"));
            }
            if lo > hi {
                return Err(format!(
                    "invalid range bound: min {lo} is greater than max {hi}"
                ));
            }
            Ok(a >= lo && a <= hi)
        }
        ClaimOperator::Approximate { tolerance } => {
            let (Some(c), Some(a)) = (numeric(claimed), numeric(actual)) else {
                return Err(err_inapplicable("numbers"));
            };
            if !finite(c) || !finite(a) {
                return Err(err_inapplicable("finite numbers"));
            }
            if !tolerance.is_finite() || *tolerance < 0.0 {
                return Err(format!("invalid tolerance '{tolerance}' — must be >= 0"));
            }
            // ABSOLUTE tolerance on the evidence value's scale.
            Ok((c - a).abs() <= *tolerance)
        }
    }
}

/// The freshness window policy per measured fact domain (thirtieth audit
/// item 23): work-order transactional state ages in minutes,
/// condition/metric aggregates in hours. Unknown domains default to
/// hours. The policy is data, not prose.
pub fn freshness_window(object_type: &str, _attribute: &str) -> chrono::Duration {
    match object_type {
        "work_order" | "andon" => chrono::Duration::minutes(10),
        _ => chrono::Duration::hours(4),
    }
}

/// Parse a claim's asserted validity instant: the claim-level `valid_at`
/// wins when present; otherwise the assertion address' `valid_time`.
pub fn parse_claim_time(
    valid_at: Option<&str>,
    address_valid_time: Option<&str>,
) -> Option<DateTime<Utc>> {
    valid_at
        .or(address_valid_time)
        .and_then(|t| DateTime::parse_from_rfc3339(t).ok())
        .map(|t| t.with_timezone(&Utc))
}

/// The FULL deterministic chain for ONE typed measured claim against ONE
/// cited evidence item (thirtieth audit item 23):
///
/// 1. the evidence must carry a TYPED fact;
/// 2. exact object match (object_type + object_id);
/// 3. exact attribute match;
/// 4. exact site scope match;
/// 5. exact work-center scope match;
/// 6. time validity: the claim's asserted valid time must coincide with
///    the evidence's observation time (within [`CLAIM_TIME_SKEW_SECS`]),
///    must not lie in the future (beyond the skew), and must not be
///    out-of-freshness (older than the domain window); evidence older
///    than the domain window is stale;
/// 7. unit compatibility;
/// 8. the claimed operator/value must be satisfied by the evidence's
///    typed value.
///
/// Returns the list of issues (empty = the claim is measured by this
/// evidence). Every failure is an explicit rejection — a claim is never
/// dropped because its sentence did not classify.
pub fn verify_measured_claim(
    claim_time: Option<DateTime<Utc>>,
    assertion: &ClaimAssertion,
    request_site: Option<Uuid>,
    request_work_center: Option<Uuid>,
    item: &crate::context::ContextItem,
    now: DateTime<Utc>,
) -> Vec<String> {
    let mut issues: Vec<String> = Vec::new();
    let Some(fact) = item.typed_fact() else {
        issues.push(
            "the cited evidence carries no typed fact (address/value/unit/observed_at) — \
             it can never measure a typed claim"
                .to_string(),
        );
        return issues;
    };
    // The claim's asserted valid time: the claim-level time wins when
    // given; otherwise the assertion address' own `valid_time`; when
    // neither is stated the claim is treated as referring to the
    // evidence's observation instant (see the time checks below).
    let claim_time = claim_time.or_else(|| {
        assertion
            .address
            .valid_time
            .as_deref()
            .and_then(|t| DateTime::parse_from_rfc3339(t).ok())
            .map(|t| t.with_timezone(&Utc))
    });
    let evidence_id = if item.evidence_id.is_empty() {
        "<uncited>"
    } else {
        item.evidence_id.as_str()
    };
    let tag = |msg: String| format!("Evidence '{evidence_id}' rejects the claim: {msg}");

    // 2. exact object match.
    let addr = &assertion.address;
    if addr.object_type != fact.address.object_type {
        issues.push(tag(format!(
            "wrong object type — the claim is about '{}' but the evidence measures '{}'",
            addr.object_type, fact.address.object_type
        )));
    }
    if addr.object_id != fact.address.object_id {
        issues.push(tag(format!(
            "wrong object — the claim is about '{}' but the evidence measures '{}'",
            addr.object_id, fact.address.object_id
        )));
    }
    // 3. exact attribute match.
    if addr.attribute != fact.address.attribute {
        issues.push(tag(format!(
            "wrong attribute — the claim is about attribute '{}' but the evidence \
             measures '{}'",
            addr.attribute, fact.address.attribute
        )));
    }

    // 4. exact site scope.
    match (request_site, fact.site_id) {
        (Some(req), Some(ev)) if req == ev => {}
        (Some(req), Some(ev)) => issues.push(tag(format!(
            "wrong site scope — the claim runs under site {req} but the evidence was \
             produced under site {ev}"
        ))),
        (Some(req), None) => issues.push(tag(format!(
            "wrong site scope — the claim runs under site {req} but the evidence \
             carries no source site"
        ))),
        (None, Some(ev)) => issues.push(tag(format!(
            "wrong site scope — the evidence was produced under site {ev} but the \
             claim carries no site scope"
        ))),
        (None, None) => {}
    }
    // 5. exact work-center scope.
    match (request_work_center, fact.work_center_id) {
        (Some(req), Some(ev)) if req == ev => {}
        (Some(req), Some(ev)) => issues.push(tag(format!(
            "wrong work-center scope — the claim runs under work center {req} but the \
             evidence belongs to work center {ev}"
        ))),
        (Some(req), None) => issues.push(tag(format!(
            "wrong work-center scope — the claim runs under work center {req} but \
             the evidence carries no work center"
        ))),
        (None, Some(ev)) => issues.push(tag(format!(
            "wrong work-center scope — the evidence belongs to work center {ev} but \
             the claim carries no work-center scope"
        ))),
        (None, None) => {}
    }

    // 6. time validity + freshness.
    let window = freshness_window(&fact.address.object_type, &fact.address.attribute);
    match fact.observed_at {
        None => issues.push(tag(
            "no source observation time — an untimed measurement cannot verify a \
             timed claim"
                .to_string(),
        )),
        Some(observed) => {
            if now - observed > window {
                issues.push(tag(format!(
                    "stale evidence — observed {} ({} ago) exceeds the {:?} freshness \
                     window",
                    observed.to_rfc3339(),
                    (now - observed).num_seconds(),
                    window
                )));
            }
            let effective_claim_time = claim_time.unwrap_or(observed);
            let skew = chrono::Duration::seconds(CLAIM_TIME_SKEW_SECS);
            if effective_claim_time > now + skew {
                issues.push(tag(format!(
                    "out-of-freshness claim time — the claim asserts a valid time {} \
                     in the future",
                    effective_claim_time.to_rfc3339()
                )));
            } else if now - effective_claim_time > window {
                issues.push(tag(format!(
                    "out-of-freshness claim time — the claim asserts a valid time {} \
                     that is older than the {:?} freshness window",
                    effective_claim_time.to_rfc3339(),
                    window
                )));
            }
            if claim_time.is_some() && (effective_claim_time - observed).abs() > skew {
                issues.push(tag(format!(
                    "wrong valid time — the claim asserts the fact held at {} but the \
                     evidence observed it at {}",
                    effective_claim_time.to_rfc3339(),
                    observed.to_rfc3339()
                )));
            }
        }
    }

    // 7. units.
    if let Err(e) = units_compatible(assertion.unit.as_deref(), fact.unit.as_deref()) {
        issues.push(tag(e));
    }

    // 8. claimed operator/value.
    match operator_satisfied(&assertion.operator, &assertion.value, &fact.value) {
        Ok(true) => {}
        Ok(false) => issues.push(tag(format!(
            "claimed value does not hold — the evidence value is {} while the claim \
             asserts {:?} {}",
            fact.value, assertion.operator, assertion.value
        ))),
        Err(e) => issues.push(tag(e)),
    }
    issues
}

/// Verify a DERIVED claim against the server's recomputation of the
/// deterministic program (thirtieth audit item 23, derived facts): the
/// program must exist at the claimed version, the claimed result must
/// agree with the recomputed value within
/// [`DERIVED_RESULT_RELATIVE_TOLERANCE`], units must be compatible, and
/// every operand evidence id must be real (the caller supplies
/// `operand_exists`).
pub fn verify_derived_claim(
    derived: &DerivedAssertion,
    recomputed: Option<&RecomputedDerivation>,
    operand_exists: impl Fn(&str) -> bool,
    now: DateTime<Utc>,
) -> Vec<String> {
    let mut issues: Vec<String> = Vec::new();
    let missing_operands: Vec<&String> = derived
        .operand_evidence_ids
        .iter()
        .filter(|id| !operand_exists(id))
        .collect();
    if !missing_operands.is_empty() {
        issues.push(format!(
            "derived claim cites operand evidence ids that were not issued by the \
             Context Kernel: {:?}",
            missing_operands
        ));
    }
    let Some(value) = recomputed else {
        issues.push(format!(
            "derived claim '{}'@v{} could not be recomputed — no deterministic \
             derivation program produced it, so the claimed result {} is not accepted",
            derived.derivation_id, derived.derivation_version, derived.result
        ));
        return issues;
    };
    if value.derivation_id != derived.derivation_id || value.version != derived.derivation_version {
        issues.push(format!(
            "derivation version mismatch — the deterministic program '{}' is at version \
             {} but the claim asserts version {}",
            derived.derivation_id, value.version, derived.derivation_version
        ));
    }
    if let Err(e) = units_compatible(derived.unit.as_deref(), value.unit.as_deref()) {
        issues.push(format!("derived claim rejects the recomputed result: {e}"));
    }
    let tolerance_ok = match (derived.result.as_f64(), value.value.as_f64()) {
        (Some(c), Some(r)) => {
            if !c.is_finite() || !r.is_finite() {
                false
            } else {
                (c - r).abs() <= DERIVED_RESULT_RELATIVE_TOLERANCE * r.abs().max(1.0)
            }
        }
        _ => derived.result == value.value,
    };
    if !tolerance_ok {
        issues.push(format!(
            "derived claim does not hold — the deterministic program recomputed {} \
             while the claim asserts {} (relative tolerance {})",
            value.value, derived.result, DERIVED_RESULT_RELATIVE_TOLERANCE
        ));
    }
    if value.recomputed_at + freshness_window("metric", "value") < now {
        issues.push("the recomputed derivation is already out of the freshness window".to_string());
    }
    issues
}

/// Structural check for an untyped measured claim (legacy envelope
/// compatibility): the cited evidence must exist (already guaranteed by
/// the caller) and — for items with scope — the site scopes must match
/// the request scope exactly. Returns the issue list (empty = ok).
pub fn site_scope_matches(
    request_site: Option<Uuid>,
    item: &crate::context::ContextItem,
) -> Vec<String> {
    match (request_site, item.site_scope) {
        (Some(req), Some(ev)) if req == ev => Vec::new(),
        (Some(req), Some(ev)) => vec![format!(
            "the evidence's site scope ({ev}) differs from the request's active site \
             ({req}) — wrong-site evidence cannot measure the claim"
        )],
        (Some(_), None) => vec![
            "the evidence carries no site scope but the claim runs under a site — \
             wrong-site evidence cannot measure the claim"
                .to_string(),
        ],
        (None, None) => Vec::new(),
        (None, Some(ev)) => vec![format!(
            "the evidence carries a site scope ({ev}) but the claim runs without one \
             — wrong-site evidence cannot measure the claim"
        )],
    }
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

    // ═══ thirtieth audit item 23 — typed assertion verification ═══

    use crate::context::{ClaimAssertion, ClaimOperator, ContextItem, FactAddress};
    use crate::facts::{ContextFact, FactDerivation, RecomputedDerivation};
    use serde_json::json;
    use uuid::Uuid;

    const SITE_A: u128 = 1;
    const WC_A: u128 = 11;

    fn wo_item(completed: i64, observed_at: Option<chrono::DateTime<Utc>>) -> ContextItem {
        let site = Some(Uuid::from_u128(SITE_A));
        let wc = Some(Uuid::from_u128(WC_A));
        let fact = ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            completed,
            Some("units"),
            site,
            wc,
            observed_at,
            format!("wo=WO-123 product=P completed={completed}/100"),
        );
        item_with_evidence_id(fact)
    }

    fn item_with_evidence_id(fact: ContextFact) -> ContextItem {
        let mut item = fact.to_context_item();
        item.evidence_id = item.derive_evidence_id();
        item
    }

    fn assertion(
        object_id: &str,
        attribute: &str,
        operator: ClaimOperator,
        value: serde_json::Value,
        unit: Option<&str>,
        valid_time: Option<String>,
    ) -> ClaimAssertion {
        ClaimAssertion {
            address: FactAddress {
                object_type: "work_order".to_string(),
                object_id: object_id.to_string(),
                attribute: attribute.to_string(),
                valid_time,
            },
            operator,
            value,
            unit: unit.map(str::to_string),
        }
    }

    fn base_assertion() -> ClaimAssertion {
        assertion(
            "WO-123",
            "quantity_completed",
            ClaimOperator::Equal,
            json!(12),
            Some("units"),
            None,
        )
    }

    #[test]
    fn operator_semantics_are_exact_for_equal() {
        // Equal is EXACT: the audit's canonical hole (12 vs 999).
        assert!(operator_satisfied(&ClaimOperator::Equal, &json!(12), &json!(12)).unwrap());
        assert!(!operator_satisfied(&ClaimOperator::Equal, &json!(999), &json!(12)).unwrap());
        assert!(!operator_satisfied(&ClaimOperator::Equal, &json!(12.5), &json!(12)).unwrap());
        // Strings compare for qualitative facts; numbers never equal strings.
        assert!(
            operator_satisfied(&ClaimOperator::Equal, &json!("active"), &json!("active")).unwrap()
        );
        assert!(
            operator_satisfied(&ClaimOperator::Equal, &json!("12"), &json!(12)).is_err(),
            "a '12' string never equals the number 12"
        );
    }

    #[test]
    fn operator_semantics_cover_partial_and_approx_and_range() {
        // The EVIDENCE value must satisfy the operator against the
        // claimed value: "completed <= 10" holds iff actual <= 10.
        assert!(operator_satisfied(&ClaimOperator::LessThan, &json!(12), &json!(11)).unwrap());
        assert!(!operator_satisfied(&ClaimOperator::LessThan, &json!(10), &json!(11)).unwrap());
        assert!(
            operator_satisfied(&ClaimOperator::LessThanOrEqual, &json!(12), &json!(12)).unwrap()
        );
        assert!(operator_satisfied(&ClaimOperator::GreaterThan, &json!(10), &json!(12)).unwrap());
        assert!(
            operator_satisfied(&ClaimOperator::GreaterThanOrEqual, &json!(12), &json!(12)).unwrap()
        );
        // Approximate: ABSOLUTE tolerance around the claimed value.
        assert!(operator_satisfied(
            &ClaimOperator::Approximate { tolerance: 1.0 },
            &json!(97.2),
            &json!(97.4)
        )
        .unwrap());
        assert!(!operator_satisfied(
            &ClaimOperator::Approximate { tolerance: 0.05 },
            &json!(97.2),
            &json!(99.0)
        )
        .unwrap());
        // Range: the evidence value must lie within the inclusive bounds.
        assert!(operator_satisfied(
            &ClaimOperator::Range {
                min: json!(10),
                max: json!(20)
            },
            &json!(99),
            &json!(15)
        )
        .unwrap());
        assert!(!operator_satisfied(
            &ClaimOperator::Range {
                min: json!(10),
                max: json!(20)
            },
            &json!(99),
            &json!(25)
        )
        .unwrap());
    }

    #[test]
    fn unit_compatibility_policy() {
        assert!(units_compatible(Some("units"), Some("units")).is_ok());
        assert!(units_compatible(Some("Units"), Some("unit")).is_ok());
        assert!(units_compatible(None, None).is_ok());
        assert!(units_compatible(Some("kg"), Some("units")).is_err());
        assert!(
            units_compatible(None, Some("units")).is_err(),
            "claim must state its unit"
        );
        assert!(
            units_compatible(Some("units"), None).is_err(),
            "no unit to compare"
        );
    }

    #[test]
    fn real_evidence_wrong_value_fails() {
        // Evidence E: WO-123 quantity_completed = 12. Model: '999'.
        let item = item_with_evidence_id(ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            12,
            Some("units"),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            Some(Utc::now() - chrono::Duration::minutes(2)),
            "wo=WO-123 completed=12/100",
        ));
        let mut bad = base_assertion();
        bad.value = json!(999);
        let issues = verify_measured_claim(
            None,
            &bad,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues
                .iter()
                .any(|i| i.contains("claimed value does not hold")
                    && i.contains("12")
                    && i.contains("999")),
            "wrong claimed value must be rejected: {issues:?}"
        );
    }

    #[test]
    fn real_evidence_correct_value_passes_full_chain() {
        let observed = Utc::now() - chrono::Duration::minutes(1);
        let item = item_with_evidence_id(ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            12,
            Some("units"),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            Some(observed),
            "wo=WO-123 completed=12/100",
        ));
        let issues = verify_measured_claim(
            Some(observed),
            &base_assertion(),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(issues.is_empty(), "correct typed claim passes: {issues:?}");
    }

    #[test]
    fn real_evidence_wrong_object_fails() {
        let item = wo_item(12, Some(Utc::now()));
        let mut a = base_assertion();
        a.address.object_id = "WO-456".to_string();
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(issues
            .iter()
            .any(|i| i.contains("wrong object") && i.contains("WO-456")));
    }

    #[test]
    fn real_evidence_wrong_attribute_fails() {
        let item = wo_item(12, Some(Utc::now()));
        let mut a = base_assertion();
        a.address.attribute = "quantity".to_string();
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(issues
            .iter()
            .any(|i| i.contains("wrong attribute") && i.contains("quantity")));
    }

    #[test]
    fn wrong_unit_fails() {
        let item = wo_item(12, Some(Utc::now()));
        let mut a = base_assertion();
        a.unit = Some("kg".to_string());
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(issues
            .iter()
            .any(|i| i.contains("unit mismatch") && i.contains("kg")));
    }

    #[test]
    fn wrong_valid_time_fails() {
        let observed = Utc::now() - chrono::Duration::minutes(1);
        let item = wo_item(12, Some(observed));
        // The claim asserts the fact held yesterday: the evidence never
        // observed that time and the claim is out of freshness.
        let a = assertion(
            "WO-123",
            "quantity_completed",
            ClaimOperator::Equal,
            json!(12),
            Some("units"),
            Some((Utc::now() - chrono::Duration::days(2)).to_rfc3339()),
        );
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues
                .iter()
                .any(|i| i.contains("wrong valid time") || i.contains("out-of-freshness")),
            "claim time that the evidence never observed must fail: {issues:?}"
        );
    }

    #[test]
    fn wrong_site_and_wrong_work_center_fail() {
        let item = wo_item(12, Some(Utc::now()));
        let a = base_assertion();
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(2)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues.iter().any(|i| i.contains("wrong site scope")),
            "{issues:?}"
        );
        let issues = verify_measured_claim(
            None,
            &a,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(22)),
            &item,
            Utc::now(),
        );
        assert!(
            issues.iter().any(|i| i.contains("wrong work-center scope")),
            "{issues:?}"
        );
    }

    #[test]
    fn stale_evidence_fails_freshness() {
        let old = Utc::now() - chrono::Duration::minutes(30);
        let item = wo_item(12, Some(old));
        let issues = verify_measured_claim(
            None,
            &base_assertion(),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues.iter().any(|i| i.contains("stale evidence")),
            "{issues:?}"
        );
    }

    #[test]
    fn untimed_evidence_cannot_measure_a_claim() {
        let item = wo_item(12, None);
        let issues = verify_measured_claim(
            None,
            &base_assertion(),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues
                .iter()
                .any(|i| i.contains("no source observation time")),
            "{issues:?}"
        );
    }

    #[test]
    fn untyped_string_evidence_cannot_measure_a_typed_claim() {
        let item = ContextItem {
            payload: json!({"section": "current_work", "text": "wo=WO-123 completed=12/100"}),
            provenance: crate::context::Provenance {
                source: "section:current_work".to_string(),
                source_revision: None,
                observed_at: Some(Utc::now()),
                recorded_at: Utc::now(),
                authority: crate::context::AuthorityRank::TransactionalState,
            },
            sensitivity: crate::context::DataClass::Internal,
            token_cost: 5,
            epistemic_status: crate::context::EpistemicStatus::RecordedFact,
            evidence_id: "ev:untyped".to_string(),
            fact_address: Some("section:current_work".to_string()),
            site_scope: None,
        };
        let issues = verify_measured_claim(
            None,
            &base_assertion(),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues.iter().any(|i| i.contains("carries no typed fact")),
            "{issues:?}"
        );
    }

    fn metric_item(value: f64) -> ContextItem {
        let mut fact = ContextFact::measured(
            "metric_tree",
            "metric",
            "process_yield_proxy",
            "value",
            value,
            Some("ratio"),
            Some(Uuid::from_u128(SITE_A)),
            None,
            Some(Utc::now() - chrono::Duration::minutes(1)),
            format!("metric_id=process_yield_proxy value={value} unit=ratio"),
        );
        fact.derivation = Some(FactDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            derivation_version: 1,
        });
        let mut item = fact.to_context_item();
        item.evidence_id = item.derive_evidence_id();
        item
    }

    fn derived_assertion(result: f64, unit: Option<&str>) -> crate::context::DerivedAssertion {
        crate::context::DerivedAssertion {
            derivation_id: "process_yield_proxy".to_string(),
            derivation_version: 1,
            operand_evidence_ids: vec![],
            result: json!(result),
            unit: unit.map(str::to_string),
        }
    }

    #[test]
    fn derived_claim_wrong_math_fails_against_recomputation() {
        let item = metric_item(0.9722222222222222);
        // The deterministic program recomputes 0.972222…; the claim
        // asserts 0.99.
        let recomputed = RecomputedDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            version: 1,
            value: json!(0.9722222222222222),
            unit: Some("ratio".to_string()),
            recomputed_at: Utc::now(),
        };
        let operands_exist = |id: &str| id == item.evidence_id || id.is_empty();
        let bad = derived_assertion(0.99, Some("ratio"));
        let issues = verify_derived_claim(&bad, Some(&recomputed), operands_exist, Utc::now());
        assert!(
            issues
                .iter()
                .any(|i| i.contains("does not hold") && i.contains("0.972") && i.contains("0.99")),
            "wrong derived math must fail against the recomputation: {issues:?}"
        );
        // The correct result passes.
        let good = derived_assertion(0.9722222222222222, Some("ratio"));
        let issues = verify_derived_claim(&good, Some(&recomputed), operands_exist, Utc::now());
        assert!(
            issues.is_empty(),
            "correct derived result passes: {issues:?}"
        );
    }

    #[test]
    fn derived_claim_without_recomputation_fails_closed() {
        let claim = derived_assertion(0.99, Some("ratio"));
        let issues = verify_derived_claim(&claim, None, |_| true, Utc::now());
        assert!(
            issues.iter().any(|i| i.contains("could not be recomputed")),
            "{issues:?}"
        );
    }

    #[test]
    fn derived_claim_with_unknown_operand_evidence_fails() {
        let recomputed = RecomputedDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            version: 1,
            value: json!(0.9722222222222222),
            unit: Some("ratio".to_string()),
            recomputed_at: Utc::now(),
        };
        let mut claim = derived_assertion(0.9722222222222222, Some("ratio"));
        claim.operand_evidence_ids = vec!["ev:made-up".to_string()];
        let issues = verify_derived_claim(&claim, Some(&recomputed), |_| false, Utc::now());
        assert!(
            issues
                .iter()
                .any(|i| i.contains("operand evidence ids") && i.contains("ev:made-up")),
            "{issues:?}"
        );
    }

    #[test]
    fn derived_claim_wrong_version_fails() {
        let recomputed = RecomputedDerivation {
            derivation_id: "process_yield_proxy".to_string(),
            version: 2,
            value: json!(0.9722222222222222),
            unit: Some("ratio".to_string()),
            recomputed_at: Utc::now(),
        };
        let claim = derived_assertion(0.9722222222222222, Some("ratio"));
        let issues = verify_derived_claim(&claim, Some(&recomputed), |_| true, Utc::now());
        assert!(
            issues
                .iter()
                .any(|i| i.contains("version mismatch") && i.contains("version 2")),
            "{issues:?}"
        );
    }

    #[test]
    fn multilingual_claims_are_checked_by_assertion_not_language() {
        // The SAME typed assertion passes whatever language the statement
        // is rendered in — the verifier never parses French/Arabic prose.
        let observed = Utc::now() - chrono::Duration::minutes(1);
        let item = item_with_evidence_id(ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            12,
            Some("units"),
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            Some(observed),
            "wo=WO-123 completed=12/100",
        ));
        for statement in [
            "WO-123 a terminé 12 unités",
            "أكمل WO-123 12 وحدة",
            "WO-123 hat 12 Einheiten abgeschlossen",
            "WO-123 completed 12 units",
        ] {
            let issues = verify_measured_claim(
                Some(observed),
                &base_assertion(),
                Some(Uuid::from_u128(SITE_A)),
                Some(Uuid::from_u128(WC_A)),
                &item,
                Utc::now(),
            );
            assert!(issues.is_empty(), "'{statement}' fails: {issues:?}");
        }
        let mut wrong = base_assertion();
        wrong.value = json!(999);
        let issues = verify_measured_claim(
            Some(observed),
            &wrong,
            Some(Uuid::from_u128(SITE_A)),
            Some(Uuid::from_u128(WC_A)),
            &item,
            Utc::now(),
        );
        assert!(
            issues
                .iter()
                .any(|i| i.contains("claimed value does not hold")),
            "the Arabic/French rendering of a wrong value must fail too"
        );
    }
}
