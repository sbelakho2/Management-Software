//! System learning metrics (item 43): measure whether the SYSTEM learns —
//! NEVER rank people by fewest Andons/NCRs. The metrics are about latency,
//! recurrence, verification and standardization:
//!
//! - detection latency: how quickly an abnormality becomes visible
//! - help-response latency: whether the support chain responds
//! - containment time: how quickly customer/process risk is controlled
//! - recurrence: whether learning actually worked
//! - escalation latency: whether barriers move upward promptly
//! - verification rate: whether PDCA closes with evidence
//! - standardization rate: whether learning becomes institutional
//!
//! A healthy system may show MORE Andons initially (people becoming
//! comfortable exposing problems) — these metrics never punish that.

use chrono::{DateTime, Utc};
use serde::Serialize;

/// One learning metric with target/condition context (item 66: metrics are
/// actual/target/gap/trend, not bare counts).
#[derive(Debug, Clone, Serialize)]
pub struct LearningMetric {
    pub key: &'static str,
    pub label: &'static str,
    pub value: f64,
    pub unit: &'static str,
    /// The direction that means improvement.
    pub better: &'static str,
    /// Target where one exists.
    pub target: Option<f64>,
    /// The gap to target (positive = below target when better is "lower").
    pub gap: Option<f64>,
    /// Interpretation guidance (plain language, item 43).
    pub guidance: String,
}

/// Aggregated learning view over a window — a PATTERN, not a grade
/// (thirteenth audit): a composite index would be optimized and would
/// punish problem exposure. The metrics carry their own direction and
/// the interpretation belongs to the reader.
#[derive(Debug, Clone, Serialize)]
pub struct LearningSnapshot {
    pub window_days: i64,
    pub metrics: Vec<LearningMetric>,
    pub generated_at: DateTime<Utc>,
}

/// Pure computation over observable inputs — deterministic and testable.
/// Inputs are computed by the caller from the DB-backed stores.
pub struct LearningInputs {
    /// Mean seconds between abnormality OCCURRENCE and its Andon record.
    pub detection_latency_seconds: f64,
    /// Mean seconds between Andon raise and first acknowledgement.
    pub help_response_seconds: f64,
    /// Mean seconds between Andon raise and containment/resolve.
    pub containment_seconds: f64,
    /// Fraction of closed Andons that recurred within the window.
    pub recurrence_rate: f64,
    /// Mean seconds between abnormality detection and tier escalation.
    pub escalation_latency_seconds: f64,
    /// Fraction of countermeasures/A3s closed WITH explicit verification.
    pub verification_rate: f64,
    /// Fraction of verified learnings that produced a standard revision.
    pub standardization_rate: f64,
    /// Fraction of deviations tied to a defined standard (vs "unknown").
    /// NONE when unmeasured — an unmeasured KPI must never appear as a
    /// fabricated number (item 46: unknown ≠ zero).
    pub deviations_tied_to_standard: Option<f64>,
    /// Mean seconds between Andon resolution and the next raise (stability).
    pub mean_interval_between_failures_seconds: f64,
    /// Count of open A3s (hypothesis quality proxy: more open, tested ones
    /// is healthier than silently closed ones).
    pub open_a3s: usize,
    /// Count of A3s with a documented hypothesis.
    pub a3s_with_hypothesis: usize,
}

pub fn compute_learning(inputs: &LearningInputs) -> LearningSnapshot {
    let detection = LearningMetric {
        key: "detection_latency",
        label: "Detection latency",
        value: inputs.detection_latency_seconds,
        unit: "s",
        better: "lower",
        target: Some(60.0),
        gap: Some((inputs.detection_latency_seconds - 60.0).max(0.0)),
        guidance: "How quickly an abnormality becomes visible. Falling latency means \
                   people are comfortable exposing problems EARLY — that is health, \
                   not failure."
            .to_string(),
    };
    let response = LearningMetric {
        key: "help_response_latency",
        label: "Help-response latency",
        value: inputs.help_response_seconds,
        unit: "s",
        better: "lower",
        target: Some(300.0),
        gap: Some((inputs.help_response_seconds - 300.0).max(0.0)),
        guidance: "Whether the support chain responds when help is asked. This is the \
                   system's promise to the person who stops the line."
            .to_string(),
    };
    let containment = LearningMetric {
        key: "containment_time",
        label: "Containment time",
        value: inputs.containment_seconds,
        unit: "s",
        better: "lower",
        target: Some(1800.0),
        gap: Some((inputs.containment_seconds - 1800.0).max(0.0)),
        guidance: "How quickly customer/process risk is controlled after the abnormality \
                   becomes visible."
            .to_string(),
    };
    let recurrence = LearningMetric {
        key: "recurrence_rate",
        label: "Recurrence",
        value: inputs.recurrence_rate,
        unit: "%",
        better: "lower",
        target: Some(0.15),
        gap: Some((inputs.recurrence_rate - 0.15).max(0.0)),
        guidance: "Whether learning actually worked. Rising recurrence means the \
                   countermeasure was not verified — reopen the learning path."
            .to_string(),
    };
    let escalation = LearningMetric {
        key: "escalation_latency",
        label: "Tier escalation latency",
        value: inputs.escalation_latency_seconds,
        unit: "s",
        better: "lower",
        target: Some(3600.0),
        gap: Some((inputs.escalation_latency_seconds - 3600.0).max(0.0)),
        guidance: "Whether barriers move upward promptly instead of being absorbed \
                   silently."
            .to_string(),
    };
    let verification = LearningMetric {
        key: "verification_rate",
        label: "Countermeasures with explicit verification",
        value: inputs.verification_rate,
        unit: "%",
        better: "higher",
        target: Some(0.8),
        gap: Some((0.8 - inputs.verification_rate).max(0.0)),
        guidance: "Whether PDCA closes with demonstrated evidence — 'we did something' \
                   is not 'we demonstrated it changed the condition'."
            .to_string(),
    };
    let standardization = LearningMetric {
        key: "standardization_rate",
        label: "Verified learning standardized",
        value: inputs.standardization_rate,
        unit: "%",
        better: "higher",
        target: Some(0.7),
        gap: Some((0.7 - inputs.standardization_rate).max(0.0)),
        guidance: "Whether learning becomes institutional (a revised standard), not a \
                   one-off fix."
            .to_string(),
    };
    let tied = match inputs.deviations_tied_to_standard {
        Some(value) => LearningMetric {
            key: "deviations_tied_to_standard",
            label: "Deviations tied to a defined standard",
            value,
            unit: "%",
            better: "higher",
            target: Some(0.9),
            gap: Some((0.9 - value).max(0.0)),
            guidance: "Whether 'normal' is actually defined — an abnormality without a \
                       standard is a gap in the standard, not a person's failure."
                .to_string(),
        },
        // NOT MEASURED — an explicit state, never a fabricated zero (item 46).
        None => LearningMetric {
            key: "deviations_tied_to_standard",
            label: "Deviations tied to a defined standard",
            value: 0.0,
            unit: "%",
            better: "higher",
            target: None,
            gap: None,
            guidance: "NOT YET MEASURED — this KPI requires deviation records that \
                       reference a standard; it is not a measured zero."
                .to_string(),
        },
    };
    let stability = LearningMetric {
        // Item 49: name the prototype metric honestly — this is the mean
        // time between RESOLVED ANDONS on a work center, not equipment
        // MTBF (andons can be material/quality/method/safety, not just
        // equipment failures).
        key: "mean_time_between_resolved_andons",
        label: "Mean time between resolved Andons",
        value: inputs.mean_interval_between_failures_seconds,
        unit: "s",
        better: "higher",
        target: None,
        gap: None,
        guidance: "Stability trend (resolved-Andon intervals). NOT equipment MTBF — \
                   Andons cover material, quality, method and safety conditions too; \
                   true MTBF requires failure-specific event semantics."
            .to_string(),
    };
    let hypothesis_quality = LearningMetric {
        key: "a3_hypothesis_quality",
        label: "A3s with explicit hypothesis",
        value: if inputs.open_a3s > 0 {
            inputs.a3s_with_hypothesis as f64 / inputs.open_a3s as f64
        } else {
            0.0
        },
        unit: "%",
        better: "higher",
        target: Some(0.9),
        gap: None,
        guidance: "Whether people TEST rather than guess — a hypothesis states what \
                   result would confirm/refute a cause."
            .to_string(),
    };

    let metrics = vec![
        detection,
        response,
        containment,
        recurrence,
        escalation,
        verification,
        standardization,
        tied,
        stability,
        hypothesis_quality,
    ];

    LearningSnapshot {
        window_days: 30,
        metrics,
        generated_at: Utc::now(),
    }
}

/// Latency helper: seconds between two timestamps (0 when absent).
pub fn seconds_between(from: Option<DateTime<Utc>>, to: DateTime<Utc>) -> f64 {
    match from {
        Some(f) => (to - f).num_milliseconds().max(0) as f64 / 1000.0,
        None => 0.0,
    }
}

/// Compute a mean over a slice (0 when empty).
pub fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

/// Recurrence: fraction of closed Andons that were re-raised on the same
/// work center/issue within `window`.
pub fn recurrence_rate(closed: usize, re_raised: usize) -> f64 {
    if closed == 0 {
        0.0
    } else {
        re_raised as f64 / closed as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    #[test]
    fn learning_index_is_bounded() {
        let inputs = LearningInputs {
            detection_latency_seconds: 45.0,
            help_response_seconds: 120.0,
            containment_seconds: 900.0,
            recurrence_rate: 0.2,
            escalation_latency_seconds: 1800.0,
            verification_rate: 0.9,
            standardization_rate: 0.8,
            deviations_tied_to_standard: Some(0.95),
            mean_interval_between_failures_seconds: 3600.0,
            open_a3s: 4,
            a3s_with_hypothesis: 4,
        };
        let s = compute_learning(&inputs);
        assert_eq!(s.metrics.len(), 10);
        // All metric labels present and gap direction correct.
        let recurrence = s
            .metrics
            .iter()
            .find(|m| m.key == "recurrence_rate")
            .unwrap();
        assert_eq!(recurrence.better, "lower");
        let verification = s
            .metrics
            .iter()
            .find(|m| m.key == "verification_rate")
            .unwrap();
        assert_eq!(verification.better, "higher");
    }

    #[test]
    fn better_system_scores_higher() {
        let poor = LearningInputs {
            detection_latency_seconds: 600.0,
            help_response_seconds: 3600.0,
            containment_seconds: 7200.0,
            recurrence_rate: 0.7,
            escalation_latency_seconds: 86400.0,
            verification_rate: 0.1,
            standardization_rate: 0.1,
            deviations_tied_to_standard: Some(0.3),
            mean_interval_between_failures_seconds: 300.0,
            open_a3s: 2,
            a3s_with_hypothesis: 0,
        };
        let good = LearningInputs {
            detection_latency_seconds: 30.0,
            help_response_seconds: 60.0,
            containment_seconds: 300.0,
            recurrence_rate: 0.05,
            escalation_latency_seconds: 900.0,
            verification_rate: 0.95,
            standardization_rate: 0.9,
            deviations_tied_to_standard: Some(1.0),
            mean_interval_between_failures_seconds: 14400.0,
            open_a3s: 5,
            a3s_with_hypothesis: 5,
        };
        // Thirteenth audit: NO composite index — the pattern carries the
        // interpretation. Assert the DIRECTIONAL invariants instead.
        let good_s = compute_learning(&good);
        let poor_s = compute_learning(&poor);
        let gap_of = |s: &LearningSnapshot, key: &str| -> f64 {
            s.metrics
                .iter()
                .find(|m| m.key == key)
                .and_then(|m| m.gap)
                .unwrap_or(0.0)
        };
        // lower-better: a slower response has a LARGER gap.
        assert!(
            gap_of(&poor_s, "help_response_latency") > gap_of(&good_s, "help_response_latency"),
            "a slower help response must show a larger gap, not zero"
        );
        // higher-better: a lower verification rate has a LARGER gap.
        assert!(
            gap_of(&poor_s, "verification_rate") > gap_of(&good_s, "verification_rate"),
            "a lower verification rate must show a larger gap"
        );
    }

    #[test]
    fn recurrence_and_latency_helpers() {
        assert_eq!(recurrence_rate(0, 3), 0.0);
        assert_eq!(recurrence_rate(4, 1), 0.25);
        let now = Utc::now();
        let d = seconds_between(Some(now - Duration::minutes(5)), now);
        assert!((d - 300.0).abs() < 1.0);
        assert_eq!(mean(&[]), 0.0);
        assert_eq!(mean(&[1.0, 3.0]), 2.0);
    }
}

#[cfg(test)]
mod behavioral_anti_tests {
    use super::*;

    /// Thirteenth audit: "Never treat fewer Andons as intrinsically
    /// better" — a system with FEW Andons but MANY escapes must not look
    /// healthier than one exposing MORE problems while containing them
    /// faster. There is NO composite index to game; the pattern must be
    /// read from the metrics themselves.
    #[test]
    fn hidden_problems_are_not_excellence() {
        // Sick system: zero visible problems, everything escapes downstream.
        let sick = LearningInputs {
            detection_latency_seconds: 0.0,
            help_response_seconds: 0.0,
            containment_seconds: 0.0,
            recurrence_rate: 1.0, // every escape recurs
            escalation_latency_seconds: 0.0,
            verification_rate: 0.0, // nothing ever verified
            standardization_rate: 0.0,
            deviations_tied_to_standard: Some(0.0),
            mean_interval_between_failures_seconds: 1e15, // NO andons at all
            open_a3s: 0,
            a3s_with_hypothesis: 0,
        };
        // Healthy: problems EXPOSED, contained fast, verified, standardized.
        let healthy = LearningInputs {
            detection_latency_seconds: 60.0,
            help_response_seconds: 120.0,
            containment_seconds: 600.0,
            recurrence_rate: 0.1,
            escalation_latency_seconds: 1800.0,
            verification_rate: 0.9,
            standardization_rate: 0.8,
            deviations_tied_to_standard: Some(0.9),
            mean_interval_between_failures_seconds: 1800.0,
            open_a3s: 3,
            a3s_with_hypothesis: 3,
        };
        let sick_s = compute_learning(&sick);
        let healthy_s = compute_learning(&healthy);
        let gap_of = |s: &LearningSnapshot, key: &str| -> f64 {
            s.metrics
                .iter()
                .find(|m| m.key == key)
                .and_then(|m| m.gap)
                .unwrap_or(f64::INFINITY)
        };
        // Recurrence: the sick system's escapes recur — its gap is LARGER
        // than the healthy system that actually reports problems.
        assert!(
            gap_of(&sick_s, "recurrence_rate") > gap_of(&healthy_s, "recurrence_rate"),
            "hidden problems must NOT look healthy"
        );
        // Verification: the sick system verified nothing — larger gap.
        assert!(
            gap_of(&sick_s, "verification_rate") > gap_of(&healthy_s, "verification_rate"),
            "a system that verifies nothing must show the larger gap"
        );
    }
}
