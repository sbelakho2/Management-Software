//! Evidence: every tool result carries it; every factual claim requires it
//! (items 96-98, 110, 114-115).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// A reference to the authoritative source of a fact (item 96).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct EvidenceRef {
    /// Canonical source id, e.g. "capability_result:CAP-778".
    pub source: String,
    /// Version of the source at read time.
    pub version: u32,
    /// When the source observed the fact (event time, not ingestion).
    pub observed_at: DateTime<Utc>,
}

impl EvidenceRef {
    pub fn new(source: impl Into<String>, version: u32, observed_at: DateTime<Utc>) -> Self {
        Self {
            source: source.into(),
            version,
            observed_at,
        }
    }
}

/// Every tool result carries its evidence, observation time and the
/// version of the tool that produced it (items 96, 117).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult<T> {
    pub data: T,
    pub evidence: Vec<EvidenceRef>,
    pub observed_at: DateTime<Utc>,
    pub source_version: String,
}

impl<T> ToolResult<T> {
    pub fn new(data: T, evidence: Vec<EvidenceRef>, source_version: &str) -> Self {
        Self {
            data,
            evidence,
            observed_at: Utc::now(),
            source_version: source_version.to_string(),
        }
    }
}

/// Freshness classes per fact type (item 114) — inventory ages in minutes,
/// standards age until superseded.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FreshnessClass {
    Seconds,
    Minutes,
    Hours,
    Days,
    UntilSuperseded,
}

impl FreshnessClass {
    pub fn max_age(&self) -> Option<chrono::Duration> {
        match self {
            FreshnessClass::Seconds => Some(chrono::Duration::seconds(60)),
            FreshnessClass::Minutes => Some(chrono::Duration::minutes(10)),
            FreshnessClass::Hours => Some(chrono::Duration::hours(4)),
            FreshnessClass::Days => Some(chrono::Duration::days(2)),
            FreshnessClass::UntilSuperseded => None,
        }
    }
}

/// Explicit evidence conflict (item 115): two sources disagree; the agent
/// must surface the conflict, never pick a side arbitrarily.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceConflict {
    pub fact: String,
    pub source_a: EvidenceRef,
    pub source_b: EvidenceRef,
    pub value_a: serde_json::Value,
    pub value_b: serde_json::Value,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn freshness_policy() {
        assert!(FreshnessClass::Minutes.max_age().is_some());
        assert!(FreshnessClass::UntilSuperseded.max_age().is_none());
    }
}
