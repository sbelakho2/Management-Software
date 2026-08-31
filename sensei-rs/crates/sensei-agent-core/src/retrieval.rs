//! DUAL-ROUTE RETRIEVAL (fifteenth audit, items 10-11).
//!
//! The retrieval route is chosen by a tiny, deterministic classifier — the
//! large model never invents the retrieval strategy. Two domain routes exist:
//!
//! - LOCAL  (entity-centric): machine / lot / order / defect / person / material
//! - GLOBAL (conceptual):     site / supplier / product family / process / customer / strategic
//!
//! Temporal, Comparative and Causal modifiers, and exact identifiers, refine
//! the route into a concrete retrieval strategy (see [`route_plan`]).
//!
//! # Classification precedence (deterministic, documented)
//!
//! 1. Exact identifier present AND a causal keyword → [`RetrievalMode::Causal`]
//!    (a "why" question ABOUT an entity walks the causal chain, anchored by
//!    the identifier).
//! 2. Exact identifier alone → [`RetrievalMode::Exact`] (identifiers are the
//!    strongest signal: WO-123, PO-45, NC-9000, A3-12, COND-7, lot X).
//! 3. Comparative keywords ("vs", "versus", "compared", "better than",
//!    "worse than") → [`RetrievalMode::Comparative`].
//! 4. Causal keywords ("why", "cause", "because", "resulted") →
//!    [`RetrievalMode::Causal`].
//! 5. Remaining category hits (Temporal, Global, Local) are counted: one
//!    category hit → that mode; two or more categories hit →
//!    [`RetrievalMode::Mixed`]; no hits at all → [`RetrievalMode::Local`]
//!    (entity-centric fallback).

use serde_json::Value;
use uuid::Uuid;

/// Retrieval mode (fifteenth audit 11): the classifier decides the route
/// deterministically — the model never invents the retrieval strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RetrievalMode {
    /// A precise identifier (WO-123, PCB-900, lot X).
    Exact,
    /// machine/lot/order/defect/person/material — entity-centric.
    Local,
    /// site/supplier/product family/process/customer — conceptual.
    Global,
    /// "last week", "this quarter".
    Temporal,
    /// "vs", "compared to", "better/worse than".
    Comparative,
    /// "why", "because", "caused".
    Causal,
    /// Two or more non-Exact categories hit in one query.
    Mixed,
}

const PREFIXES: &[&str] = &["WO", "PO", "SO", "NC", "A3", "COND"];

const KEYWORDS_COMPARATIVE: &[&str] = &["vs", "versus", "compared", "better than", "worse than"];

const KEYWORDS_CAUSAL: &[&str] = &["why", "cause", "because", "resulted"];

const KEYWORDS_TEMPORAL: &[&str] = &[
    "yesterday",
    "last week",
    "this month",
    "quarter",
    "hour",
    "shift",
];

const KEYWORDS_GLOBAL: &[&str] = &[
    "site", "supplier", "family", "process", "customer", "plant", "tunisia", "morocco",
];

const KEYWORDS_LOCAL: &[&str] = &[
    "machine",
    "work center",
    "line",
    "cell",
    "material",
    "defect",
    "lot",
    "order",
    "operator",
];

/// Short keywords that would false-positive as plain substrings
/// ("deadline" contains "line", "requisite" contains "site",
/// "lottery" contains "lot") — these match on word boundaries only.
const KEYWORDS_WORD_BOUNDED: &[&str] = &["lot", "line", "cell", "site", "order", "vs"];

fn contains_word(text: &str, word: &str) -> bool {
    text.split(|c: char| !c.is_alphanumeric())
        .any(|token| token == word)
}

fn keyword_hit(text: &str, keyword: &str) -> bool {
    if KEYWORDS_WORD_BOUNDED.contains(&keyword) {
        contains_word(text, keyword)
    } else {
        text.contains(keyword)
    }
}

/// Matches `\b(WO|PO|SO|NC|A3|COND)-?[0-9]+\b`, an 8+ character
/// uppercase/alphanumeric token, or "lot" followed by an id token.
fn contains_identifier(query: &str) -> bool {
    let tokens: Vec<String> = query
        .split(|c: char| !c.is_alphanumeric())
        .filter(|t| !t.is_empty())
        .map(|t| t.to_uppercase())
        .collect();

    for (i, token) in tokens.iter().enumerate() {
        if is_prefix(token) {
            if let Some(next) = tokens.get(i + 1) {
                if !next.is_empty() && next.chars().all(|c| c.is_ascii_digit()) {
                    return true;
                }
            }
        }
        if is_prefixed_id(token) {
            return true;
        }
        if token == "LOT" {
            if let Some(next) = tokens.get(i + 1) {
                if is_lot_id(next) {
                    return true;
                }
            }
        }
        if is_long_token(token) {
            return true;
        }
    }
    false
}

fn is_prefix(token: &str) -> bool {
    PREFIXES.contains(&token)
}

fn is_prefixed_id(token: &str) -> bool {
    PREFIXES.iter().any(|p| {
        token
            .strip_prefix(p)
            .is_some_and(|rest| !rest.is_empty() && rest.chars().all(|c| c.is_ascii_digit()))
    })
}

fn is_lot_id(token: &str) -> bool {
    !token.is_empty()
        && (token.chars().count() == 1
            || token.chars().any(|c| c.is_ascii_digit())
            || token.chars().all(|c| c.is_ascii_hexdigit()))
}

fn is_long_token(token: &str) -> bool {
    token.chars().count() >= 8
        && token.chars().any(|c| c.is_ascii_uppercase())
        && token.chars().any(|c| c.is_ascii_digit())
        && token
            .chars()
            .all(|c| c.is_ascii_uppercase() || c.is_ascii_digit())
}

/// Deterministically classify a user query into a retrieval mode.
///
/// Precedence (see module docs): Exact+Causal → Causal, Exact alone →
/// Exact, Comparative, Causal, then a category hit-count over Temporal /
/// Global / Local (one hit → that mode, two or more → Mixed, none →
/// Local).
pub fn classify_retrieval_mode(query: &str) -> RetrievalMode {
    let text = query.to_lowercase();
    let has_identifier = contains_identifier(query);
    let causal_hit = KEYWORDS_CAUSAL.iter().any(|k| keyword_hit(&text, k));

    if has_identifier && causal_hit {
        return RetrievalMode::Causal;
    }
    if has_identifier {
        return RetrievalMode::Exact;
    }
    if KEYWORDS_COMPARATIVE.iter().any(|k| keyword_hit(&text, k)) {
        return RetrievalMode::Comparative;
    }
    if causal_hit {
        return RetrievalMode::Causal;
    }

    let temporal_hits = KEYWORDS_TEMPORAL
        .iter()
        .filter(|k| keyword_hit(&text, k))
        .count();
    let global_hits = KEYWORDS_GLOBAL
        .iter()
        .filter(|k| keyword_hit(&text, k))
        .count();
    let local_hits = KEYWORDS_LOCAL
        .iter()
        .filter(|k| keyword_hit(&text, k))
        .count();

    let categories =
        usize::from(temporal_hits > 0) + usize::from(global_hits > 0) + usize::from(local_hits > 0);

    match categories {
        0 => RetrievalMode::Local,
        1 if global_hits > 0 => RetrievalMode::Global,
        1 if local_hits > 0 => RetrievalMode::Local,
        1 => RetrievalMode::Temporal,
        _ => RetrievalMode::Mixed,
    }
}

fn strategy(mode: RetrievalMode) -> &'static str {
    match mode {
        RetrievalMode::Exact => "entity_lookup",
        RetrievalMode::Local => "graph_traversal",
        RetrievalMode::Global => "aggregation",
        RetrievalMode::Temporal => "temporal_series",
        RetrievalMode::Comparative => "comparison",
        RetrievalMode::Causal => "causal_chain",
        RetrievalMode::Mixed => "mixed",
    }
}

/// Produce the routing plan for a classified mode: the strategy to execute
/// and the entity scope the retrieval should be anchored to.
pub fn route_plan(
    mode: RetrievalMode,
    scope_site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
) -> Value {
    serde_json::json!({
        "mode": mode,
        "strategy": strategy(mode),
        "scope": {
            "site_id": scope_site_id,
            "work_center_id": work_center_id,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_identifier_alone_is_exact() {
        assert_eq!(classify_retrieval_mode("WO-123"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("PO-45"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("NC 9000"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("COND-7"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("A3-12"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("WO123"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("lot X"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("lot 45"), RetrievalMode::Exact);
        assert_eq!(classify_retrieval_mode("BATCH12AB"), RetrievalMode::Exact);
    }

    #[test]
    fn exact_identifier_with_causal_keyword_is_causal() {
        assert_eq!(
            classify_retrieval_mode("why is WO-123 late?"),
            RetrievalMode::Causal
        );
        assert_eq!(
            classify_retrieval_mode("what caused NC-9000 to fail"),
            RetrievalMode::Causal
        );
    }

    #[test]
    fn causal_without_identifier_is_causal() {
        assert_eq!(
            classify_retrieval_mode("why is the supplier late"),
            RetrievalMode::Causal
        );
    }

    #[test]
    fn comparative_is_comparative() {
        assert_eq!(
            classify_retrieval_mode("line A vs line B"),
            RetrievalMode::Comparative
        );
        assert_eq!(
            classify_retrieval_mode("output compared to last quarter"),
            RetrievalMode::Comparative
        );
    }

    #[test]
    fn temporal_alone_is_temporal() {
        assert_eq!(
            classify_retrieval_mode("last week"),
            RetrievalMode::Temporal
        );
        assert_eq!(
            classify_retrieval_mode("this quarter"),
            RetrievalMode::Temporal
        );
    }

    #[test]
    fn local_entity_query_is_local() {
        assert_eq!(
            classify_retrieval_mode("machine 14 cycle"),
            RetrievalMode::Local
        );
        assert_eq!(
            classify_retrieval_mode("material defect on line 3"),
            RetrievalMode::Local
        );
    }

    #[test]
    fn global_conceptual_query_is_global() {
        assert_eq!(
            classify_retrieval_mode("site bizerte output"),
            RetrievalMode::Global
        );
        assert_eq!(
            classify_retrieval_mode("supplier quality in tunisia"),
            RetrievalMode::Global
        );
    }

    #[test]
    fn global_plus_temporal_is_mixed() {
        assert_eq!(
            classify_retrieval_mode("supplier delivery this quarter"),
            RetrievalMode::Mixed
        );
    }

    #[test]
    fn local_plus_global_is_mixed() {
        assert_eq!(
            classify_retrieval_mode("machine defect at supplier plant"),
            RetrievalMode::Mixed
        );
    }

    #[test]
    fn fallback_is_local() {
        assert_eq!(
            classify_retrieval_mode("anything at all"),
            RetrievalMode::Local
        );
        assert_eq!(classify_retrieval_mode(""), RetrievalMode::Local);
    }

    #[test]
    fn word_boundaries_avoid_false_positives() {
        assert_eq!(
            classify_retrieval_mode("a lot of material"),
            RetrievalMode::Local
        );
        assert_eq!(
            classify_retrieval_mode("deadline moved"),
            RetrievalMode::Local
        );
        assert_eq!(
            classify_retrieval_mode("requisite parts"),
            RetrievalMode::Local
        );
    }

    #[test]
    fn strategy_per_mode() {
        let cases = [
            (RetrievalMode::Exact, "entity_lookup"),
            (RetrievalMode::Local, "graph_traversal"),
            (RetrievalMode::Global, "aggregation"),
            (RetrievalMode::Temporal, "temporal_series"),
            (RetrievalMode::Comparative, "comparison"),
            (RetrievalMode::Causal, "causal_chain"),
            (RetrievalMode::Mixed, "mixed"),
        ];
        for (mode, expected) in cases {
            let plan = route_plan(mode, None, None);
            assert_eq!(plan["mode"], serde_json::json!(mode), "mode mismatch");
            assert_eq!(plan["strategy"], expected, "strategy for {mode:?}");
            assert_eq!(plan["scope"]["site_id"], Value::Null);
            assert_eq!(plan["scope"]["work_center_id"], Value::Null);
        }
    }

    #[test]
    fn route_plan_carries_scope_ids() {
        let site_id = Uuid::new_v4();
        let work_center_id = Uuid::new_v4();
        let plan = route_plan(RetrievalMode::Exact, Some(site_id), Some(work_center_id));
        assert_eq!(plan["mode"], "exact");
        assert_eq!(plan["strategy"], "entity_lookup");
        assert_eq!(plan["scope"]["site_id"], serde_json::json!(site_id));
        assert_eq!(
            plan["scope"]["work_center_id"],
            serde_json::json!(work_center_id)
        );
    }
}
