//! Context kernel (fifteenth audit 74-79): deterministic planning, then
//! budgeted assembly. The model never invents the retrieval strategy —
//! `plan_context` decides what must be present, and `build_context_bundle`
//! assembles it under the token budget while preserving contradictions.

use crate::context::{
    contradiction_candidates, fact_address_of, plan_context, ContextItem, ContextPlan,
    ContextRequest, FactAddress, TokenBudget,
};
use std::collections::{HashMap, HashSet};

/// The assembled context handed to the model: sections keyed by plan
/// requirement, the spent token budget, and any surviving contradictions
/// as COMPACT one-line representations (sixteenth audit 11).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ContextBundle {
    pub plan: ContextPlan,
    pub sections: Vec<(String, Vec<ContextItem>)>,
    pub total_tokens: u32,
    pub contradictions: Vec<String>,
}

/// Assemble the context bundle: filter by sensitivity ceiling, select
/// greedily by authority × recency under the normal token budget, then
/// represent every surviving contradiction as compact one-line claims
/// (sixteenth audit 10-11) charged against `conflicts_reserved` first,
/// then `emergency_overrun` — beyond that cap the contradiction is
/// dropped, never unbounded. Contradictions are detected at the
/// fact-address level, so WO-1 vs WO-2 is never a contradiction.
pub fn build_context_bundle(
    req: &ContextRequest,
    items: Vec<ContextItem>,
    budget: TokenBudget,
) -> ContextBundle {
    let plan = plan_context(req);
    let ceiling = parse_sensitivity(&req.sensitivity_ceiling);

    let mut candidates: Vec<ContextItem> = items
        .into_iter()
        .filter(|i| {
            ceiling.is_none_or(|c| parse_sensitivity(&i.sensitivity).is_none_or(|s| s <= c))
        })
        .collect();

    // Deterministic greedy order: highest authority first, then most recent,
    // then by source name for full determinism (ties keep input order).
    candidates.sort_by(|a, b| {
        a.provenance
            .authority
            .cmp(&b.provenance.authority)
            .then_with(|| b.provenance.observed_at.cmp(&a.provenance.observed_at))
            .then_with(|| a.provenance.source.cmp(&b.provenance.source))
    });

    let mut selected: Vec<ContextItem> = Vec::new();
    let mut dropped: Vec<ContextItem> = Vec::new();
    let mut total: u32 = 0;
    for item in candidates {
        if total + item.token_cost <= budget.normal {
            let cost = item.token_cost;
            selected.push(item);
            total += cost;
        } else {
            dropped.push(item);
        }
    }

    // Contradiction preservation: detect disagreements at the fact-address
    // level over every attribute present in the supplied items, then emit
    // one compact line per distinct value ("source X says value Y for
    // {attribute}"). Each line's token cost counts against
    // conflicts_reserved; once that is exhausted, emergency_overrun is
    // used up to its cap; beyond that the contradiction is dropped.
    let mut attributes: Vec<String> = Vec::new();
    for item in selected.iter().chain(dropped.iter()) {
        if let Some(obj) = item.payload.as_object() {
            for key in obj.keys() {
                if !attributes.iter().any(|k| k == key) {
                    attributes.push(key.clone());
                }
            }
        }
    }
    attributes.sort();

    let all: Vec<ContextItem> = selected.iter().chain(dropped.iter()).cloned().collect();
    let conflict_cap = budget
        .conflicts_reserved
        .saturating_add(budget.emergency_overrun);
    let mut conflict_spent: u32 = 0;
    let mut contradictions: Vec<String> = Vec::new();
    for attribute in &attributes {
        for (address, values) in contradiction_candidates(&all, attribute) {
            for value in values {
                let source = source_for(&selected, &dropped, &address, attribute, &value);
                let line = format!(
                    "source {} says value {} for {attribute}",
                    source.as_deref().unwrap_or("unknown"),
                    value
                );
                let cost = estimate_tokens(&line);
                if conflict_spent + cost > conflict_cap {
                    continue; // budget exhausted: drop, never unbounded
                }
                conflict_spent += cost;
                total += cost;
                contradictions.push(line);
            }
        }
    }
    contradictions.sort();

    let mut order: Vec<String> = Vec::new();
    let mut groups: HashMap<String, Vec<ContextItem>> = HashMap::new();
    for item in selected {
        let name = section_of(&item, &plan.required);
        if !groups.contains_key(&name) {
            order.push(name.clone());
        }
        groups.entry(name).or_default().push(item);
    }

    let mut sections = Vec::new();
    let mut emitted: HashSet<String> = HashSet::new();
    for name in &plan.required {
        if let Some(group) = groups.remove(name) {
            sections.push((name.clone(), group));
            emitted.insert(name.clone());
        }
    }
    for name in order {
        if !emitted.contains(&name) {
            if let Some(group) = groups.remove(&name) {
                sections.push((name, group));
            }
        }
    }

    ContextBundle {
        plan,
        sections,
        total_tokens: total,
        contradictions,
    }
}

fn parse_sensitivity(s: &str) -> Option<u32> {
    s.trim().parse::<u32>().ok()
}

fn section_of(item: &ContextItem, required: &[String]) -> String {
    if let Some(obj) = item.payload.as_object() {
        for name in required {
            if obj.contains_key(name) {
                return name.clone();
            }
        }
    }
    "general".to_string()
}

/// The source of an item that contributed `value` for `attribute` at the
/// given fact address (prefers selected items, then dropped).
fn source_for(
    selected: &[ContextItem],
    dropped: &[ContextItem],
    address: &FactAddress,
    attribute: &str,
    value: &serde_json::Value,
) -> Option<String> {
    selected
        .iter()
        .chain(dropped.iter())
        .find(|i| {
            fact_address_of(i, attribute).as_ref() == Some(address)
                && i.payload.get(attribute) == Some(value)
        })
        .map(|i| i.provenance.source.clone())
}

/// Crude token estimate for a compact contradiction line: ~4 chars per
/// token, at least 1.
fn estimate_tokens(s: &str) -> u32 {
    (s.chars().count() as u32).div_ceil(4)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::{
        budget_allocation, contradiction_candidates, has_contradiction, AuthorityRank,
        EpistemicStatus, TaskKind, TokenBudget,
    };
    use chrono::{Duration, Utc};
    use serde_json::json;
    use uuid::Uuid;

    fn request(task: TaskKind, max_tokens: u32) -> ContextRequest {
        ContextRequest {
            principal_id: Uuid::new_v4(),
            roles: vec!["maintenance".to_string()],
            site_id: None,
            value_stream_id: None,
            work_center_id: None,
            task,
            focal_objects: vec![],
            max_tokens,
            sensitivity_ceiling: "3".to_string(),
            trace_id: "test-trace".to_string(),
        }
    }

    fn item(
        source: &str,
        payload: serde_json::Value,
        authority: AuthorityRank,
        token_cost: u32,
        observed_at: Option<chrono::DateTime<Utc>>,
    ) -> ContextItem {
        ContextItem {
            payload,
            provenance: crate::context::Provenance {
                source: source.to_string(),
                source_revision: None,
                observed_at,
                recorded_at: Utc::now(),
                authority,
            },
            sensitivity: "1".to_string(),
            token_cost,
            epistemic_status: EpistemicStatus::RecordedFact,
        }
    }

    #[test]
    fn troubleshoot_plan_requires_failure_context() {
        let plan = plan_context(&request(TaskKind::Troubleshoot, 1000));
        for required in ["process_standard", "recent_failures", "similar_lessons"] {
            assert!(
                plan.required.iter().any(|r| r == required),
                "missing {required}"
            );
        }
        assert_eq!(plan.budget, 1000);
    }

    #[test]
    fn executive_plan_differs_from_troubleshoot() {
        let exec = plan_context(&request(TaskKind::ExecutiveAnalysis, 1000));
        assert!(exec.required.iter().any(|r| r == "metric_tree"));
        assert!(exec.required.iter().any(|r| r == "exception_summary"));
        assert!(exec.required.iter().any(|r| r == "causal_candidates"));
        assert!(!exec.required.iter().any(|r| r == "process_standard"));
    }

    #[test]
    fn budget_allocation_sums_to_about_one() {
        for task in [
            TaskKind::Troubleshoot,
            TaskKind::ExecutiveAnalysis,
            TaskKind::OperatorAssist,
            TaskKind::PlannerDecision,
            TaskKind::QualityInvestigation,
            TaskKind::General,
        ] {
            let sum: f64 = budget_allocation(&task).iter().map(|(_, s)| s).sum();
            assert!((sum - 1.0).abs() < 0.11, "{task:?} sums to {sum}");
        }
    }

    #[test]
    fn contradiction_is_detected() {
        let a = item(
            "sensor-a",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "open"
            }),
            AuthorityRank::VerifiedObservation,
            5,
            Some(Utc::now()),
        );
        let b = item(
            "sensor-b",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "closed"
            }),
            AuthorityRank::VerifiedObservation,
            5,
            Some(Utc::now()),
        );
        assert!(has_contradiction(&[a.clone(), b.clone()], "valve_position"));
        assert!(!has_contradiction(&[a], "valve_position"));
    }

    #[test]
    fn bundle_respects_token_budget() {
        let items: Vec<ContextItem> = (0..5)
            .map(|i| {
                item(
                    &format!("src-{i}"),
                    json!({"live_state": "running"}),
                    AuthorityRank::VerifiedObservation,
                    10,
                    Some(Utc::now() - Duration::minutes(i)),
                )
            })
            .collect();
        let bundle = build_context_bundle(
            &request(TaskKind::Troubleshoot, 25),
            items,
            TokenBudget::default_for(25),
        );
        assert!(bundle.total_tokens <= 25);
        assert_eq!(bundle.total_tokens, 20);
        assert!(bundle.contradictions.is_empty());
        let kept: usize = bundle.sections.iter().map(|(_, v)| v.len()).sum();
        assert_eq!(kept, 2);
    }

    #[test]
    fn bundle_keeps_both_sides_of_a_contradiction() {
        let now = Utc::now();
        let a = item(
            "sensor-a",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "open",
                "live_state": "running"
            }),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let b = item(
            "sensor-b",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "closed",
                "live_state": "running"
            }),
            AuthorityRank::VerifiedObservation,
            100,
            Some(now - Duration::minutes(1)),
        );
        let budget = TokenBudget::default_for(300);
        let bundle =
            build_context_bundle(&request(TaskKind::Troubleshoot, 300), vec![a, b], budget);
        assert!(bundle
            .contradictions
            .iter()
            .any(|c| c.contains("valve_position") && c.contains("open")));
        assert!(bundle
            .contradictions
            .iter()
            .any(|c| c.contains("valve_position") && c.contains("closed")));
        let kept: usize = bundle.sections.iter().map(|(_, v)| v.len()).sum();
        assert_eq!(kept, 2);
        assert!(bundle.total_tokens <= 110 + budget.conflicts_reserved + budget.emergency_overrun);
    }

    #[test]
    fn different_objects_do_not_contradict() {
        let now = Utc::now();
        let a = item(
            "wo-src",
            json!({"id": "WO-1", "status": "open"}),
            AuthorityRank::TransactionalState,
            10,
            Some(now),
        );
        let b = item(
            "wo-src",
            json!({"id": "WO-2", "status": "closed"}),
            AuthorityRank::TransactionalState,
            10,
            Some(now),
        );
        assert!(!has_contradiction(&[a.clone(), b.clone()], "status"));
        assert!(contradiction_candidates(&[a, b], "status").is_empty());
    }

    #[test]
    fn same_address_different_values_contradict() {
        let now = Utc::now();
        let a = item(
            "wo-src",
            json!({
                "_fact_address": {"object_type": "work_order", "object_id": "WO-1"},
                "status": "open"
            }),
            AuthorityRank::TransactionalState,
            10,
            Some(now),
        );
        let b = item(
            "wo-src",
            json!({
                "_fact_address": {"object_type": "work_order", "object_id": "WO-1"},
                "status": "closed"
            }),
            AuthorityRank::TransactionalState,
            10,
            Some(now),
        );
        assert!(has_contradiction(&[a.clone(), b.clone()], "status"));
        let candidates = contradiction_candidates(&[a, b], "status");
        assert_eq!(candidates.len(), 1);
        assert_eq!(candidates[0].0.object_id, "WO-1");
        assert_eq!(candidates[0].1.len(), 2);
    }

    #[test]
    fn compact_contradiction_stays_within_conflicts_reserved() {
        let now = Utc::now();
        let a = item(
            "sensor-a",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "open"
            }),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let b = item(
            "sensor-b",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "closed"
            }),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let budget = TokenBudget::default_for(1000);
        let bundle =
            build_context_bundle(&request(TaskKind::Troubleshoot, 1000), vec![a, b], budget);
        assert_eq!(bundle.contradictions.len(), 2);
        let kept: usize = bundle.sections.iter().map(|(_, v)| v.len()).sum();
        assert_eq!(kept, 2);
        assert!(bundle.total_tokens <= budget.normal + budget.conflicts_reserved);
    }

    #[test]
    fn budget_exhaustion_stops_force_includes() {
        let now = Utc::now();
        let mut a_fields = serde_json::Map::new();
        let mut b_fields = serde_json::Map::new();
        a_fields.insert("id".into(), json!("WO-1"));
        b_fields.insert("id".into(), json!("WO-1"));
        for i in 0..10 {
            a_fields.insert(format!("attr-{i:02}"), json!("open"));
            b_fields.insert(format!("attr-{i:02}"), json!("closed"));
        }
        let a = item(
            "sensor-a",
            serde_json::Value::Object(a_fields),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let b = item(
            "sensor-b",
            serde_json::Value::Object(b_fields),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now - Duration::minutes(1)),
        );
        let budget = TokenBudget {
            normal: 1000,
            conflicts_reserved: 30,
            emergency_overrun: 10,
        };
        let bundle =
            build_context_bundle(&request(TaskKind::Troubleshoot, 1000), vec![a, b], budget);
        assert!(!bundle.contradictions.is_empty());
        assert!(bundle.contradictions.len() < 20);
        assert!(
            bundle.total_tokens
                <= budget.normal + budget.conflicts_reserved + budget.emergency_overrun
        );
    }

    #[test]
    fn zero_conflict_budget_drops_all_contradictions() {
        let now = Utc::now();
        let a = item(
            "sensor-a",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "open"
            }),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let b = item(
            "sensor-b",
            json!({
                "_fact_address": {"object_type": "valve", "object_id": "v-1"},
                "valve_position": "closed"
            }),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let budget = TokenBudget {
            normal: 1000,
            conflicts_reserved: 0,
            emergency_overrun: 0,
        };
        let bundle =
            build_context_bundle(&request(TaskKind::Troubleshoot, 1000), vec![a, b], budget);
        assert!(bundle.contradictions.is_empty());
        assert!(bundle.total_tokens <= budget.normal);
    }
}
