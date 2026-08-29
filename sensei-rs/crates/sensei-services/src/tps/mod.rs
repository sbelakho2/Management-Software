//! Deterministic TPS kernel: takt, pitch and available-time calculations.
//!
//! These are pure functions with NO LLM involvement — the agent receives
//! the result; it never invents it.

use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
pub mod rules;
pub mod signals;

use std::time::Duration;

/// A window of customer demand for a product family.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DemandWindow {
    pub product_family_id: uuid::Uuid,
    pub site_id: uuid::Uuid,
    pub start: chrono::DateTime<chrono::Utc>,
    pub end: chrono::DateTime<chrono::Utc>,
    /// Total units required in the window.
    pub required_units: Decimal,
    /// References to the demand sources (orders, forecasts).
    pub source_refs: Vec<String>,
}

/// Available production time within a window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AvailableProductionTime {
    pub scheduled_seconds: u64,
    pub breaks_seconds: u64,
    pub planned_downtime_seconds: u64,
}

impl AvailableProductionTime {
    pub fn net_seconds(&self) -> u64 {
        self.scheduled_seconds
            .saturating_sub(self.breaks_seconds)
            .saturating_sub(self.planned_downtime_seconds)
    }
}

/// The computed takt for a demand window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaktSnapshot {
    pub demand_window_id: uuid::Uuid,
    pub net_available_seconds: u64,
    pub demand_units: Decimal,
    /// Seconds of available time per demanded unit.
    pub takt_seconds: Decimal,
    pub calculated_at: chrono::DateTime<chrono::Utc>,
    /// Evidence: the inputs the calculation used.
    pub evidence_refs: Vec<String>,
}

/// Deterministic takt calculation.
///
/// `takt = net available production time / customer demand`.
///
/// Returns `None` when demand is zero (no takt can be defined) — never a
/// fabricated number.
pub fn calculate_takt(
    demand_window_id: uuid::Uuid,
    available: &AvailableProductionTime,
    demand_units: Decimal,
) -> Option<TaktSnapshot> {
    if demand_units <= Decimal::ZERO {
        return None;
    }
    let net = available.net_seconds();
    let takt = Decimal::from(net) / demand_units;
    Some(TaktSnapshot {
        demand_window_id,
        net_available_seconds: net,
        demand_units,
        takt_seconds: takt,
        calculated_at: chrono::Utc::now(),
        evidence_refs: vec![
            format!("calendar:net_seconds={net}"),
            format!("demand_units={demand_units}"),
        ],
    })
}

/// Pitch: one container's worth of production at takt (the standard
/// replenishment/leveling interval). `container_quantity` is the kanban/
/// pitch container size in units.
pub fn calculate_pitch(takt_seconds: Decimal, container_quantity: Decimal) -> Option<Decimal> {
    if container_quantity <= Decimal::ZERO {
        return None;
    }
    Some(takt_seconds * container_quantity)
}

/// Cycle-time-to-takt comparison helper: a cycle above takt cannot meet
/// demand within the window.
pub fn cycle_exceeds_takt(cycle_seconds: Decimal, takt_seconds: Decimal) -> bool {
    takt_seconds > Decimal::ZERO && cycle_seconds > takt_seconds
}

/// Convert a `Duration` to a Decimal number of seconds (exact).
pub fn duration_to_seconds(d: Duration) -> Decimal {
    Decimal::from(d.as_secs())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn takt_is_net_time_over_demand() {
        let available = AvailableProductionTime {
            scheduled_seconds: 28_800, // 8h
            breaks_seconds: 1_800,     // 30min
            planned_downtime_seconds: 600,
        };
        let takt = calculate_takt(uuid::Uuid::new_v4(), &available, Decimal::from(1000u32))
            .expect("positive demand");
        // net = 28800 - 1800 - 600 = 26400; 26400 / 1000 = 26.4s
        assert_eq!(takt.takt_seconds, Decimal::from_str_exact("26.4").unwrap());
        assert_eq!(takt.net_available_seconds, 26_400);
    }

    #[test]
    fn zero_demand_has_no_takt() {
        let available = AvailableProductionTime {
            scheduled_seconds: 28_800,
            breaks_seconds: 0,
            planned_downtime_seconds: 0,
        };
        assert!(calculate_takt(uuid::Uuid::new_v4(), &available, Decimal::ZERO).is_none());
    }

    #[test]
    fn pitch_is_takt_times_container() {
        let pitch = calculate_pitch(
            Decimal::from_str_exact("26.4").unwrap(),
            Decimal::from(10u32),
        );
        assert_eq!(pitch, Some(Decimal::from(264u32)));
    }

    #[test]
    fn cycle_above_takt_is_detected() {
        assert!(cycle_exceeds_takt(
            Decimal::from(30u32),
            Decimal::from_str_exact("26.4").unwrap()
        ));
        assert!(!cycle_exceeds_takt(
            Decimal::from(20u32),
            Decimal::from_str_exact("26.4").unwrap()
        ));
    }
}
