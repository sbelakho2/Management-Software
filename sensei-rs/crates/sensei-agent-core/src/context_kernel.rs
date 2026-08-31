//! Context kernel (fifteenth audit 74-79): deterministic planning, then
//! budgeted assembly. The model never invents the retrieval strategy —
//! `plan_context` decides what must be present, and `build_context_bundle`
//! assembles it under the token budget while preserving contradictions.

use crate::context::{plan_context, ContextItem, ContextPlan, ContextRequest};
use std::collections::{HashMap, HashSet};

/// The assembled context handed to the model: sections keyed by plan
/// requirement, the spent token budget, and any surviving contradictions.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ContextBundle {
    pub plan: ContextPlan,
    pub sections: Vec<(String, Vec<ContextItem>)>,
    pub total_tokens: u32,
    pub contradictions: Vec<String>,
}

/// Assemble the context bundle: filter by sensitivity ceiling, select
/// greedily by authority × recency under the token budget, then force-include
/// every side of any contradiction (fifteenth audit 77: contradictions
/// survive retrieval — they are never collapsed, even past the budget).
pub fn build_context_bundle(req: &ContextRequest, items: Vec<ContextItem>) -> ContextBundle {
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
        a.authority
            .cmp(&b.authority)
            .then_with(|| b.observed_at.cmp(&a.observed_at))
            .then_with(|| a.source.cmp(&b.source))
    });

    let mut selected: Vec<ContextItem> = Vec::new();
    let mut dropped: Vec<ContextItem> = Vec::new();
    let mut total: u32 = 0;
    for item in candidates {
        if total + item.token_cost <= req.max_tokens {
            let cost = item.token_cost;
            selected.push(item);
            total += cost;
        } else {
            dropped.push(item);
        }
    }

    // Contradiction preservation: for every fact key on which the supplied
    // items disagree, ensure at least one item per distinct value survives.
    let mut key_values: HashMap<String, HashSet<String>> = HashMap::new();
    let mut value_cost: HashMap<(String, String), u32> = HashMap::new();
    for item in selected.iter().chain(dropped.iter()) {
        if let Some(obj) = item.payload.as_object() {
            for (key, value) in obj {
                let v = value.to_string();
                key_values.entry(key.clone()).or_default().insert(v.clone());
                value_cost
                    .entry((key.clone(), v))
                    .and_modify(|c| *c = (*c).min(item.token_cost))
                    .or_insert(item.token_cost);
            }
        }
    }

    let mut contradictions: Vec<String> = Vec::new();
    for (key, values) in &key_values {
        if values.len() <= 1 {
            continue;
        }
        contradictions.push(key.clone());
        for value in values {
            let present = selected
                .iter()
                .any(|i| i.payload.get(key).map(|v| v.to_string()) == Some(value.clone()));
            if present {
                continue;
            }
            if let Some(item) = dropped
                .iter()
                .filter(|i| i.payload.get(key).map(|v| v.to_string()) == Some(value.clone()))
                .min_by_key(|i| i.token_cost)
            {
                let cost = item.token_cost;
                selected.push(item.clone());
                total += cost;
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::{
        budget_allocation, has_contradiction, AuthorityRank, EpistemicStatus, TaskKind,
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
            source: source.to_string(),
            source_revision: None,
            observed_at,
            authority,
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
            json!({"valve_position": "open"}),
            AuthorityRank::VerifiedObservation,
            5,
            Some(Utc::now()),
        );
        let b = item(
            "sensor-b",
            json!({"valve_position": "closed"}),
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
        let bundle = build_context_bundle(&request(TaskKind::Troubleshoot, 25), items);
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
            json!({"valve_position": "open", "live_state": "running"}),
            AuthorityRank::VerifiedObservation,
            10,
            Some(now),
        );
        let b = item(
            "sensor-b",
            json!({"valve_position": "closed", "live_state": "running"}),
            AuthorityRank::VerifiedObservation,
            100,
            Some(now - Duration::minutes(1)),
        );
        let bundle = build_context_bundle(&request(TaskKind::Troubleshoot, 10), vec![a, b]);
        assert!(bundle
            .contradictions
            .contains(&"valve_position".to_string()));
        let kept: usize = bundle.sections.iter().map(|(_, v)| v.len()).sum();
        assert_eq!(kept, 2);
        assert_eq!(bundle.total_tokens, 110);
    }
}
