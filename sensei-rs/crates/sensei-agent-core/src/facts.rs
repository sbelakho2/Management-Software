//! TYPED kernel facts (thirtieth audit item 23): the authoritative fact
//! the Context Kernel hands to the model is NO LONGER a flat string. A
//! [`ContextFact`] carries its [`FactAddress`] (object_type, object_id,
//! attribute), its TYPED value, its unit and its source observation time
//! as DATA — `display_text` exists only to render the fact for the model;
//! it is never the verification truth.
//!
//! The model-facing verifier checks claims against the typed fields, so
//! language becomes irrelevant: French "12 unités terminées", Arabic,
//! German and English renderings of the same fact all carry the SAME
//! address/value/unit and produce the same deterministic verdict. A claim
//! that the value is 999 while the evidence says 12 fails on the
//! operator/value comparison, whatever the sentence said.
//!
//! Evidence materialization: the typed fact rides INSIDE a
//! [`ContextItem`] payload under [`TYPED_FACT_PAYLOAD_KEY`], so the
//! kernel's existing provenance/evidence-id machinery applies unchanged
//! (the `ContextItem` STRUCT is not extended — legacy JSON round-trips
//! untouched) and [`ContextItem::typed_fact`] recovers the typed view at
//! verification time.

use crate::context::{
    AuthorityRank, ContextItem, DataClass, EpistemicStatus, FactAddress, Provenance,
};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// The payload key under which a typed [`ContextFact`] rides inside a
/// [`ContextItem`]'s JSON payload. The payload's `section`/`text` keys
/// stay the render keys; this key carries the verification truth.
pub const TYPED_FACT_PAYLOAD_KEY: &str = "_typed_fact";

/// The payload key holding the model-facing section of the item.
pub const FACT_SECTION_PAYLOAD_KEY: &str = "section";

/// The payload key holding the model-facing rendered text of the item.
pub const FACT_TEXT_PAYLOAD_KEY: &str = "text";

/// One typed authoritative kernel fact (thirtieth audit item 23).
///
/// `section` is the context section the fact was fetched under;
/// `address` identifies the OBJECT + ATTRIBUTE the value describes;
/// `value` is the typed value; `unit` its unit when the value is
/// dimensional; `site_id`/`work_center_id` are the SOURCE scope the fact
/// was retrieved under (never substituted after retrieval);
/// `observed_at` is the source observation time (row/event time, never
/// retrieval time); `derivation` is present when the value was computed
/// by a deterministic derivation program (metrics); `display_text` is
/// the model rendering ONLY.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContextFact {
    pub section: String,
    pub address: FactAddress,
    pub value: serde_json::Value,
    pub unit: Option<String>,
    pub site_id: Option<Uuid>,
    pub work_center_id: Option<Uuid>,
    pub observed_at: Option<DateTime<Utc>>,
    /// Present when the value is the OUTPUT of a deterministic derivation
    /// program (e.g. a metric computation), NOT a raw reading.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub derivation: Option<FactDerivation>,
    /// The model rendering — never the source of verification truth.
    pub display_text: String,
}

/// The deterministic derivation program that produced a derived fact:
/// the server re-runs `derivation_id` at `derivation_version` when a
/// claim asserts a derived result — the model never gets to say "x% was
/// deterministically derived" unless the program agrees.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FactDerivation {
    pub derivation_id: String,
    pub derivation_version: u32,
}

/// The result of the server RE-RUNNING a derivation program at
/// verification/release time. Claims that carry a
/// [`DerivedAssertion`](crate::context::DerivedAssertion) are only
/// measured against these recomputed values.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RecomputedDerivation {
    pub derivation_id: String,
    pub version: u32,
    pub value: serde_json::Value,
    pub unit: Option<String>,
    /// When the deterministic program produced the value.
    pub recomputed_at: DateTime<Utc>,
}

impl ContextFact {
    /// Build a typed fact. `display_text` is the model rendering; the
    /// typed fields are the verification truth.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        section: impl Into<String>,
        address: FactAddress,
        value: serde_json::Value,
        unit: Option<impl Into<String>>,
        site_id: Option<Uuid>,
        work_center_id: Option<Uuid>,
        observed_at: Option<DateTime<Utc>>,
        display_text: impl Into<String>,
    ) -> Self {
        Self {
            section: section.into(),
            address,
            value,
            unit: unit.map(Into::into),
            site_id,
            work_center_id,
            observed_at,
            derivation: None,
            display_text: display_text.into(),
        }
    }

    /// Convenience builder for a measured (non-derived) numeric fact.
    #[allow(clippy::too_many_arguments)]
    pub fn measured(
        section: impl Into<String>,
        object_type: impl Into<String>,
        object_id: impl Into<String>,
        attribute: impl Into<String>,
        value: impl Serialize,
        unit: Option<impl Into<String>>,
        site_id: Option<Uuid>,
        work_center_id: Option<Uuid>,
        observed_at: Option<DateTime<Utc>>,
        display_text: impl Into<String>,
    ) -> Self {
        Self {
            section: section.into(),
            address: FactAddress {
                object_type: object_type.into(),
                object_id: object_id.into(),
                attribute: attribute.into(),
                valid_time: observed_at.map(|t| t.to_rfc3339()),
            },
            value: serde_json::to_value(value).unwrap_or(serde_json::Value::Null),
            unit: unit.map(Into::into),
            site_id,
            work_center_id,
            observed_at,
            derivation: None,
            display_text: display_text.into(),
        }
    }

    /// Mark this fact as the output of a deterministic derivation
    /// program (metric values).
    pub fn with_derivation(mut self, derivation_id: impl Into<String>, version: u32) -> Self {
        self.derivation = Some(FactDerivation {
            derivation_id: derivation_id.into(),
            derivation_version: version,
        });
        self
    }

    /// Materialize this typed fact as a kernel [`ContextItem`]: the
    /// model rendering lives under `text` and the TYPED fact rides under
    /// [`TYPED_FACT_PAYLOAD_KEY`]. The evidence id is derived from the
    /// item's own provenance + payload by the kernel (stable across
    /// identical constructions).
    pub fn to_context_item(self) -> ContextItem {
        let display_text = self.display_text.clone();
        let section = self.section.clone();
        let mut payload = serde_json::Map::new();
        payload.insert(
            FACT_SECTION_PAYLOAD_KEY.to_string(),
            serde_json::Value::String(section),
        );
        payload.insert(
            FACT_TEXT_PAYLOAD_KEY.to_string(),
            serde_json::Value::String(display_text),
        );
        payload.insert(
            TYPED_FACT_PAYLOAD_KEY.to_string(),
            serde_json::to_value(&self).unwrap_or(serde_json::Value::Null),
        );
        let source = format!(
            "section:{}/{}:{}:{}",
            self.section, self.address.object_type, self.address.object_id, self.address.attribute
        );
        ContextItem {
            payload: serde_json::Value::Object(payload),
            provenance: Provenance {
                source,
                source_revision: None,
                observed_at: self.observed_at,
                recorded_at: Utc::now(),
                authority: AuthorityRank::TransactionalState,
            },
            sensitivity: DataClass::Internal,
            token_cost: (self.display_text.len() as u32 / 4).max(1),
            epistemic_status: if self.derivation.is_some() {
                EpistemicStatus::DerivedFact
            } else {
                EpistemicStatus::RecordedFact
            },
            evidence_id: String::new(),
            fact_address: Some(format!("section:{}", self.section)),
            site_scope: self.site_id,
        }
    }
}

impl ContextItem {
    /// Recover the TYPED fact of this evidence item, when the item was
    /// materialized from a [`ContextFact`]. Items built from plain
    /// strings (legacy/crafted) carry no typed fact and return `None` —
    /// they can never deterministically measure a typed claim.
    pub fn typed_fact(&self) -> Option<ContextFact> {
        let raw = self.payload.get(TYPED_FACT_PAYLOAD_KEY)?;
        serde_json::from_value(raw.clone()).ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::context::Claim;
    use chrono::Duration;

    fn fact(completed: i64) -> ContextFact {
        let observed_at = Utc::now() - Duration::minutes(2);
        ContextFact::measured(
            "current_work",
            "work_order",
            "WO-123",
            "quantity_completed",
            completed,
            Some("units"),
            None,
            Some(Uuid::from_u128(7)),
            Some(observed_at),
            format!("wo=WO-123 product=P completed={completed}/100"),
        )
    }

    #[test]
    fn typed_fact_round_trips_through_context_item_payload() {
        let f = fact(12);
        let item = f.clone().to_context_item();
        assert_eq!(item.evidence_id, String::new(), "kernel issues the id");
        assert_eq!(
            item.payload
                .get(FACT_TEXT_PAYLOAD_KEY)
                .and_then(|v| v.as_str()),
            Some("wo=WO-123 product=P completed=12/100"),
            "the model rendering is preserved under the text key"
        );
        let back = item.typed_fact().expect("typed fact must survive");
        assert_eq!(back.address, f.address);
        assert_eq!(back.value, serde_json::json!(12));
        assert_eq!(back.unit.as_deref(), Some("units"));
        assert_eq!(back.observed_at, f.observed_at);
        assert_eq!(back.display_text, f.display_text);
        assert_eq!(back.work_center_id, Some(Uuid::from_u128(7)));
    }

    #[test]
    fn derived_fact_marks_epistemic_status_and_derivation() {
        let f = fact(12)
            .with_derivation("process_yield_proxy", 1)
            .to_context_item();
        assert_eq!(f.epistemic_status, EpistemicStatus::DerivedFact);
        let back = f.typed_fact().unwrap();
        let d = back.derivation.expect("derivation recorded");
        assert_eq!(d.derivation_id, "process_yield_proxy");
        assert_eq!(d.derivation_version, 1);
    }

    #[test]
    fn plain_string_items_have_no_typed_fact() {
        let item = ContextItem {
            payload: serde_json::json!({ "section": "metric_tree", "text": "42" }),
            provenance: Provenance {
                source: "x".to_string(),
                source_revision: None,
                observed_at: None,
                recorded_at: Utc::now(),
                authority: AuthorityRank::TransactionalState,
            },
            sensitivity: DataClass::Internal,
            token_cost: 1,
            epistemic_status: EpistemicStatus::RecordedFact,
            evidence_id: String::new(),
            fact_address: None,
            site_scope: None,
        };
        assert!(item.typed_fact().is_none());
    }

    #[test]
    fn claim_with_assertion_round_trips_through_json() {
        let claim = Claim {
            statement: "WO-123 completed 12 units".to_string(),
            epistemic_status: "measured".to_string(),
            fact_addresses: vec!["site:unknown/address:section:current_work".to_string()],
            evidence_refs: vec!["ev:abc".to_string()],
            confidence: None,
            valid_at: None,
            assertion: Some(crate::context::ClaimAssertion {
                address: FactAddress {
                    object_type: "work_order".to_string(),
                    object_id: "WO-123".to_string(),
                    attribute: "quantity_completed".to_string(),
                    valid_time: None,
                },
                operator: crate::context::ClaimOperator::Equal,
                value: serde_json::json!(12),
                unit: Some("units".to_string()),
            }),
            derived: None,
        };
        let json = serde_json::to_string(&claim).unwrap();
        let back: Claim = serde_json::from_str(&json).unwrap();
        assert_eq!(back.assertion, claim.assertion);
        let legacy: Claim = serde_json::from_str(
            r#"{"statement":"s","epistemic_status":"measured","fact_addresses":[],"evidence_refs":[],"confidence":null,"valid_at":null}"#,
        )
        .unwrap();
        assert!(legacy.assertion.is_none(), "new field is optional in JSON");
        assert!(legacy.derived.is_none());
    }
}
