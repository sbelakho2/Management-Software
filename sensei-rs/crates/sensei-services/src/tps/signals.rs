//! TPS signal classifier (item 41): silently classifies operational
//! signals across dimensions — flow, batch effect, muri, recurrence,
//! supplier variability, systemic flow, genchi-genbutsu gap, learning
//! gaps, standard violations. The AI may internally think in TPS terms;
//! the USER-FACING guidance is plain language about the observed
//! condition and what to look at next — never a lecture about waste.
//!
//! Every classifier is a pure function over observable inputs (counts,
//! timestamps, statuses) so the layer is deterministic and testable.

use chrono::{DateTime, Utc};

/// One classified signal with the plain-language guidance shown to users.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub struct TpsSignal {
    /// Internal dimension (muda/mura/muri/flow/recurrence/...).
    pub dimension: &'static str,
    /// User-facing message — describes the CONDITION and the next
    /// observation, never prescribes a countermeasure.
    pub guidance: String,
    /// Severity 0..3 (0 = note, 3 = systemic/escalate).
    pub severity: u8,
}

/// Queue continuously growing -> flow/bottleneck issue.
pub fn classify_queue_growth(
    queue_delta: i64,
    window_minutes: i64,
    threshold_per_hour: i64,
) -> Option<TpsSignal> {
    if window_minutes <= 0 {
        return None;
    }
    let per_hour = queue_delta * 60 / window_minutes;
    if per_hour >= threshold_per_hour {
        Some(TpsSignal {
            dimension: "flow",
            severity: 2,
            guidance: format!(
                "Work is accumulating here ({per_hour:+}/hour). Inspect capacity and \
                 interruption causes at the process before it grows further."
            ),
        })
    } else {
        None
    }
}

/// Large batches despite variable demand -> overproduction / batch effect.
pub fn classify_batch_effect(
    batch_days_of_demand: f64,
    demand_volatility: f64,
    batch_threshold_days: f64,
    volatility_threshold: f64,
) -> Option<TpsSignal> {
    if batch_days_of_demand >= batch_threshold_days && demand_volatility >= volatility_threshold {
        Some(TpsSignal {
            dimension: "overproduction",
            severity: 2,
            guidance: format!(
                "Current production exceeds near-term pull by {batch_days_of_demand:.1} days of \
                 demand, while demand varies ±{:.0}%. Review the run size against actual pull.",
                demand_volatility * 100.0
            ),
        })
    } else {
        None
    }
}

/// Employee repeatedly bypasses an awkward step -> muri / poor standard.
pub fn classify_workaround(workaround_count: i64, workaround_threshold: i64) -> Option<TpsSignal> {
    if workaround_count >= workaround_threshold {
        Some(TpsSignal {
            dimension: "muri",
            severity: 2,
            guidance: format!(
                "This step has generated {workaround_count} workarounds. Observe the actual \
                 work condition before enforcing compliance — the standard may be the problem."
            ),
        })
    } else {
        None
    }
}

/// Same Andon recurs -> countermeasure ineffective.
pub fn classify_andon_recurrence(
    same_issue_count: i64,
    since_days: i64,
    recurrence_threshold: i64,
) -> Option<TpsSignal> {
    if same_issue_count >= recurrence_threshold {
        Some(TpsSignal {
            dimension: "recurrence",
            severity: 2,
            guidance: format!(
                "This condition has returned {same_issue_count} times in the last {since_days} \
                 days since the last corrective action. Compare the occurrences before \
                 treating it as the same problem."
            ),
        })
    } else {
        None
    }
}

/// Supplier delivery swings -> mura (variability, not mean, drives risk).
pub fn classify_supplier_variability(
    delivery_stddev_days: f64,
    mean_lead_days: f64,
    variability_threshold: f64,
) -> Option<TpsSignal> {
    if mean_lead_days > 0.0 {
        let cv = delivery_stddev_days / mean_lead_days;
        if cv >= variability_threshold {
            return Some(TpsSignal {
                dimension: "mura",
                severity: 2,
                guidance: format!(
                    "Delivery variability (CV {cv:.2}), not mean lead time, is driving shortage \
                     risk. Stabilize the supplier's delivery window before increasing stock."
                ),
            });
        }
    }
    None
}

/// Finished goods grow while delivery misses rise -> systemic flow problem.
pub fn classify_systemic_flow(
    fg_growth_days: f64,
    delivery_miss_delta: i64,
    growth_threshold_days: f64,
) -> Option<TpsSignal> {
    if fg_growth_days >= growth_threshold_days && delivery_miss_delta > 0 {
        Some(TpsSignal {
            dimension: "systemic_flow",
            severity: 3,
            guidance: format!(
                "Finished goods are growing (+{fg_growth_days:.1} days) while delivery misses \
                 are rising (+{delivery_miss_delta}). This is a systemic flow problem — \
                 escalate to cross-domain analysis."
            ),
        })
    } else {
        None
    }
}

/// Manager completes LSW remotely (no observation) -> genchi-genbutsu gap.
pub fn classify_remote_lsw(
    completed_at: DateTime<Utc>,
    observation_time: DateTime<Utc>,
    max_skew_seconds: i64,
) -> Option<TpsSignal> {
    let skew = (completed_at - observation_time).num_seconds();
    if skew > max_skew_seconds {
        Some(TpsSignal {
            dimension: "genchi_genbutsu",
            severity: 1,
            guidance:
                "This check was completed without a direct process observation. LSW requires \
                 going to see the actual condition — complete it at the gemba."
                    .to_string(),
        })
    } else {
        None
    }
}

/// NCR closed but the same defect returns -> learning not standardized.
pub fn classify_reopened_defect(reopened_count: i64, reopen_threshold: i64) -> Option<TpsSignal> {
    if reopened_count >= reopen_threshold {
        Some(TpsSignal {
            dimension: "learning_gap",
            severity: 2,
            guidance: format!(
                "This defect has returned {reopened_count} times after closure. The learning \
                 was not standardized — reopen the learning path before closing again."
            ),
        })
    } else {
        None
    }
}

/// Operator cannot hit standard cycle -> do NOT blame the operator: show
/// the actual work/material/equipment conditions.
pub fn classify_cycle_miss(
    cycle_seconds: f64,
    standard_seconds: f64,
    miss_ratio: f64,
) -> Option<TpsSignal> {
    if standard_seconds > 0.0 && cycle_seconds > standard_seconds * (1.0 + miss_ratio) {
        Some(TpsSignal {
            dimension: "standard_gap",
            severity: 1,
            guidance: format!(
                "Actual cycle ({cycle_seconds:.0}s) exceeds the standard ({standard_seconds:.0}s). \
                 Look at the actual work, material, equipment and method conditions before \
                 drawing any conclusion about the operator."
            ),
        })
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn queue_growth_detected_with_rate() {
        let s = classify_queue_growth(30, 30, 40).expect("signal");
        assert_eq!(s.dimension, "flow");
        assert!(s.guidance.contains("accumulating"));
        assert_eq!(classify_queue_growth(10, 60, 40), None);
    }

    #[test]
    fn batch_effect_needs_volatility() {
        let s = classify_batch_effect(4.2, 0.5, 4.0, 0.4).expect("signal");
        assert_eq!(s.dimension, "overproduction");
        assert!(s.guidance.contains("4.2 days"));
        assert_eq!(classify_batch_effect(4.2, 0.1, 4.0, 0.4), None);
    }

    #[test]
    fn workaround_and_recurrence() {
        let s = classify_workaround(4, 3).expect("signal");
        assert_eq!(s.dimension, "muri");
        assert!(s.guidance.contains("standard may be the problem"));
        let r = classify_andon_recurrence(4, 17, 3).expect("signal");
        assert_eq!(r.dimension, "recurrence");
        assert!(r.guidance.contains("4 times"));
    }

    #[test]
    fn supplier_variability_cv() {
        let s = classify_supplier_variability(9.0, 6.0, 1.0).expect("signal");
        assert_eq!(s.dimension, "mura");
        assert_eq!(classify_supplier_variability(1.0, 6.0, 1.0), None);
    }

    #[test]
    fn systemic_flow_escalates() {
        let s = classify_systemic_flow(5.0, 2, 4.0).expect("signal");
        assert_eq!(s.severity, 3);
        assert_eq!(classify_systemic_flow(5.0, 0, 4.0), None);
    }

    #[test]
    fn remote_lsw_and_cycle_miss() {
        let now = Utc::now();
        let s = classify_remote_lsw(now, now - chrono::Duration::minutes(30), 300).expect("signal");
        assert_eq!(s.dimension, "genchi_genbutsu");
        assert_eq!(
            classify_remote_lsw(now, now - chrono::Duration::minutes(1), 300),
            None
        );
        let c = classify_cycle_miss(90.0, 60.0, 0.2).expect("signal");
        assert_eq!(c.dimension, "standard_gap");
        assert!(c
            .guidance
            .contains("before drawing any conclusion about the operator"));
    }
}
