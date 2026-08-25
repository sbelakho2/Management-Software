//! Predictive Maintenance — Equipment Health Scoring, RUL Estimation, and Scheduling.
//!
//! Derived from maintenance domain patterns found in the backend Python codebase
//! (e.g., [`field_returns.py`](backend/src/sensei/services/maintenance/field_returns.py),
//! [`maintenance_tpm.py`](backend/src/sensei/services/maintenance/maintenance_tpm.py)).
//!
//! # Features
//!
//! - **Health Scoring**: Weighted assessment from uptime, vibration, temperature, cycles.
//! - **Failure Probability**: Weibull-based estimation using equipment age and usage.
//! - **RUL Estimation**: Remaining useful life in operating hours.
//! - **Risk Classification**: Low / Medium / High / Critical.
//! - **Maintenance Scheduling**: Optimal maintenance date based on predicted failure.
//! - **Failure Mode Classification**: Pattern-based matching against known failure modes.

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Risk level for equipment failure.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Equipment type category.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EquipmentCategory {
    Pump,
    Compressor,
    Conveyor,
    Press,
    CNC,
    Robot,
    Furnace,
    Mixer,
    CoolingTower,
    Generator,
    Other,
}

/// Known failure mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FailureMode {
    BearingWear,
    BeltFailure,
    SealLeak,
    ElectricalFault,
    Overheating,
    VibrationExcess,
    LubricationFailure,
    Corrosion,
    FatigueCrack,
    CalibrationDrift,
    Unknown,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// Telemetry snapshot for equipment health assessment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquipmentTelemetry {
    pub equipment_id: Uuid,
    pub uptime_hours: f64,
    pub operating_cycles: u64,
    pub vibration_level: f64,
    pub temperature_celsius: f64,
    pub last_maintenance_at: DateTime<Utc>,
    pub recorded_at: DateTime<Utc>,
}

/// A single maintenance action recommendation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenanceAction {
    pub action: String,
    pub priority: u8,
    pub estimated_hours: f64,
    pub required_skills: Vec<String>,
    pub parts_needed: Vec<String>,
}

/// Predictive maintenance recommendation for a piece of equipment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenancePrediction {
    pub equipment_id: Uuid,
    pub equipment_name: String,
    pub category: EquipmentCategory,
    pub health_score: f64,
    pub failure_probability: f64,
    pub estimated_remaining_life_hours: f64,
    pub risk_level: RiskLevel,
    pub predicted_failure_mode: FailureMode,
    pub recommended_maintenance_date: DateTime<Utc>,
    pub suggested_actions: Vec<MaintenanceAction>,
    pub confidence: f64,
}

// ---------------------------------------------------------------------------
// Failure Mode Signatures
// ---------------------------------------------------------------------------

/// Failure mode signature: maps operating conditions to likely failure modes.
#[allow(dead_code)]
struct FailureSignature {
    mode: FailureMode,
    vibration_threshold: f64,    // Above this → possible
    temperature_threshold: f64,  // Above this → possible
    cycle_sensitivity: f64,      // Per 1000 cycles, probability increase
    description: &'static str,
    actions: &'static [&'static str],
    skills: &'static [&'static str],
    parts: &'static [&'static str],
}

const FAILURE_SIGNATURES: &[FailureSignature] = &[
    FailureSignature {
        mode: FailureMode::BearingWear,
        vibration_threshold: 6.0,
        temperature_threshold: 75.0,
        cycle_sensitivity: 0.15,
        description: "Bearing wear detected — increasing vibration and temperature",
        actions: &[
            "Replace bearings",
            "Check lubrication system",
            "Inspect bearing housing for wear",
            "Verify alignment",
        ],
        skills: &["Mechanic", "Lubrication Technician"],
        parts: &["Bearing set", "Grease", "Seal kit"],
    },
    FailureSignature {
        mode: FailureMode::BeltFailure,
        vibration_threshold: 4.0,
        temperature_threshold: 60.0,
        cycle_sensitivity: 0.10,
        description: "Belt wear/fraying detected — tension loss and vibration",
        actions: &[
            "Replace drive belt(s)",
            "Check and adjust tension",
            "Inspect pulleys for wear",
            "Align drive system",
        ],
        skills: &["Mechanic"],
        parts: &["Drive belt", "Tensioner"],
    },
    FailureSignature {
        mode: FailureMode::Overheating,
        vibration_threshold: 3.0,
        temperature_threshold: 85.0,
        cycle_sensitivity: 0.05,
        description: "Overheating trend detected — check cooling system",
        actions: &[
            "Check coolant levels and flow",
            "Clean heat exchanger fins",
            "Verify fan operation",
            "Check ambient temperature conditions",
            "Inspect thermal sensors",
        ],
        skills: &["HVAC Technician", "Mechanic"],
        parts: &["Coolant", "Fan belt", "Thermal sensor"],
    },
    FailureSignature {
        mode: FailureMode::VibrationExcess,
        vibration_threshold: 8.0,
        temperature_threshold: 50.0,
        cycle_sensitivity: 0.08,
        description: "Excessive vibration — potential imbalance or misalignment",
        actions: &[
            "Perform vibration analysis",
            "Check and re-balance rotating parts",
            "Verify foundation bolts",
            "Check coupling alignment",
            "Inspect for resonant frequencies",
        ],
        skills: &["Vibration Analyst", "Mechanic"],
        parts: &["Shim kit", "Coupling", "Mounting bolts"],
    },
    FailureSignature {
        mode: FailureMode::LubricationFailure,
        vibration_threshold: 5.0,
        temperature_threshold: 70.0,
        cycle_sensitivity: 0.12,
        description: "Lubrication degradation — increased friction and wear",
        actions: &[
            "Drain and replace lubricant",
            "Clean lubricant system",
            "Check for contamination",
            "Verify lubricant type matches specification",
            "Inspect seals and wipers",
        ],
        skills: &["Lubrication Technician", "Mechanic"],
        parts: &["Lubricant oil", "Filter", "Seal kit"],
    },
    FailureSignature {
        mode: FailureMode::SealLeak,
        vibration_threshold: 4.5,
        temperature_threshold: 65.0,
        cycle_sensitivity: 0.09,
        description: "Seal degradation — potential leakage path detected",
        actions: &[
            "Replace seals and gaskets",
            "Check shaft surface for wear",
            "Verify installation clearance",
            "Test for leaks after replacement",
        ],
        skills: &["Mechanic", "Seal Specialist"],
        parts: &["Seal kit", "Gasket set", "O-rings"],
    },
];

// ---------------------------------------------------------------------------
// PredictiveMaintenanceEngine
// ---------------------------------------------------------------------------

/// Engine for predictive maintenance analysis.
///
/// Assesses equipment health, predicts failure probabilities, estimates
/// remaining useful life, and recommends maintenance actions.
pub struct PredictiveMaintenanceEngine {
    /// Historical telemetry data per equipment.
    telemetry_history: HashMap<Uuid, Vec<EquipmentTelemetry>>,
    /// Maximum telemetry entries per equipment.
    max_history: usize,
}

impl PredictiveMaintenanceEngine {
    /// Create a new [`PredictiveMaintenanceEngine`].
    pub fn new(max_history: usize) -> Self {
        Self {
            telemetry_history: HashMap::new(),
            max_history,
        }
    }

    /// Record telemetry data for an equipment.
    pub fn record_telemetry(&mut self, telemetry: EquipmentTelemetry) {
        let entry = self
            .telemetry_history
            .entry(telemetry.equipment_id)
            .or_insert_with(|| Vec::with_capacity(self.max_history));
        entry.push(telemetry);

        // Trim old entries
        if entry.len() > self.max_history {
            entry.drain(..entry.len() - self.max_history);
        }
    }

    /// Get telemetry history for an equipment.
    pub fn get_telemetry(&self, equipment_id: Uuid) -> Vec<&EquipmentTelemetry> {
        self.telemetry_history
            .get(&equipment_id)
            .map(|v| v.iter().collect())
            .unwrap_or_default()
    }

    /// Predict maintenance needs for an equipment based on telemetry.
    pub fn predict_maintenance(
        &self,
        equipment_id: Uuid,
        name: &str,
        category: EquipmentCategory,
    ) -> Option<MaintenancePrediction> {
        let history = self.telemetry_history.get(&equipment_id)?;
        let latest = history.last()?;

        // Calculate health score from all dimensions
        let health_score = self.calculate_health_score(history);

        // Predict failure mode
        let (failure_mode, match_confidence) = self.predict_failure_mode(history);

        // Calculate failure probability based on health, age, and usage
        let failure_probability = self.calculate_failure_probability(history);

        // Estimate remaining useful life
        let estimated_rul = self.estimate_remaining_life(health_score, history);

        // Determine risk level
        let risk_level = self.classify_risk(failure_probability);

        // Schedule maintenance
        let maintenance_date = self.schedule_maintenance(risk_level, latest.recorded_at);

        // Generate suggested actions
        let suggested_actions = self.generate_actions(failure_mode, category, risk_level);

        Some(MaintenancePrediction {
            equipment_id,
            equipment_name: name.to_string(),
            category,
            health_score,
            failure_probability,
            estimated_remaining_life_hours: estimated_rul,
            risk_level,
            predicted_failure_mode: failure_mode,
            recommended_maintenance_date: maintenance_date,
            suggested_actions,
            confidence: match_confidence,
        })
    }

    /// Calculate a composite health score (0.0 = critical, 1.0 = perfect) from telemetry.
    fn calculate_health_score(&self, history: &[EquipmentTelemetry]) -> f64 {
        if history.is_empty() {
            return 1.0;
        }

        let latest = history.last().unwrap();

        // Dimension scores (each 0.0–1.0, 1.0 = healthy)
        let uptime_score = (latest.uptime_hours / 8760.0).min(1.0); // Hours in a year

        let vibration_score = if latest.vibration_level <= 2.0 {
            1.0
        } else if latest.vibration_level >= 10.0 {
            0.0
        } else {
            1.0 - (latest.vibration_level - 2.0) / 8.0
        };

        let temperature_score = if latest.temperature_celsius <= 40.0 {
            1.0
        } else if latest.temperature_celsius >= 100.0 {
            0.0
        } else {
            1.0 - (latest.temperature_celsius - 40.0) / 60.0
        };

        let maintenance_recency = if history.len() >= 2 {
            let last_maint = latest.last_maintenance_at;
            let now = latest.recorded_at;
            let hours_since_maint = (now - last_maint).num_hours() as f64;
            if hours_since_maint <= 0.0 {
                1.0
            } else {
                (1.0 - (hours_since_maint / 8760.0).min(1.0)).max(0.3)
            }
        } else {
            0.5 // Default for unknown maintenance history
        };

        // Trend: if vibration or temperature is increasing, penalize
        let mut trend_penalty = 0.0f64;
        if history.len() >= 3 {
            let recent: Vec<&EquipmentTelemetry> = history.iter().rev().take(3).collect();
            let vib_trend = recent[0].vibration_level - recent[2].vibration_level;
            let temp_trend = recent[0].temperature_celsius - recent[2].temperature_celsius;

            if vib_trend > 1.0 {
                trend_penalty += 0.1;
            }
            if temp_trend > 5.0 {
                trend_penalty += 0.1;
            }
        }

        // Weighted composite
        let score = uptime_score * 0.15
            + vibration_score * 0.30
            + temperature_score * 0.25
            + maintenance_recency * 0.20
            - trend_penalty;

        score.clamp(0.0, 1.0)
    }

    /// Predict the most likely failure mode based on telemetry patterns.
    fn predict_failure_mode(&self, history: &[EquipmentTelemetry]) -> (FailureMode, f64) {
        if history.is_empty() {
            return (FailureMode::Unknown, 0.0);
        }

        let latest = history.last().unwrap();

        let mut best_match = FailureMode::Unknown;
        let mut best_score = 0.0f64;

        for signature in FAILURE_SIGNATURES {
            let mut score = 0.0f64;

            // Vibration match
            if latest.vibration_level >= signature.vibration_threshold {
                let excess = (latest.vibration_level - signature.vibration_threshold) / 5.0;
                score += 0.3 + excess.min(0.3);
            }

            // Temperature match
            if latest.temperature_celsius >= signature.temperature_threshold {
                let excess =
                    (latest.temperature_celsius - signature.temperature_threshold) / 30.0;
                score += 0.3 + excess.min(0.3);
            }

            // Cycle sensitivity
            if let Some(earliest) = history.first() {
                let total_cycles = latest.operating_cycles.saturating_sub(earliest.operating_cycles);
                let cycle_score = (total_cycles as f64 / 1000.0) * signature.cycle_sensitivity;
                score += cycle_score.min(0.4);
            }

            if score > best_score {
                best_score = score;
                best_match = signature.mode;
            }
        }

        // If no signature matches well, check for generic degradation
        if best_score < 0.2 {
            if latest.vibration_level > 3.0 {
                best_match = FailureMode::VibrationExcess;
                best_score = 0.3;
            } else if latest.temperature_celsius > 50.0 {
                best_match = FailureMode::Overheating;
                best_score = 0.3;
            }
        }

        (best_match, best_score.min(1.0))
    }

    /// Calculate failure probability (0.0–1.0) using a simplified Weibull model.
    fn calculate_failure_probability(&self, history: &[EquipmentTelemetry]) -> f64 {
        let health = self.calculate_health_score(history);
        let latest = history.last().unwrap();

        // Base failure rate from health score
        let base_rate = 1.0 - health;

        // Age factor: equipment degrades over time
        let age_years = latest.uptime_hours / 8760.0;
        let age_factor = (age_years / 10.0).min(1.0) * 0.3;

        // Usage factor: more cycles = more wear
        let cycle_factor = if let Some(first) = history.first() {
            let total_cycles = latest.operating_cycles.saturating_sub(first.operating_cycles);
            ((total_cycles as f64) / 100_000.0).min(1.0) * 0.2
        } else {
            0.0
        };

        // Time since last maintenance factor
        let maint_hours = (latest.recorded_at - latest.last_maintenance_at).num_hours() as f64;
        let maint_factor = (maint_hours / 4380.0).min(1.0) * 0.1; // 6 months = full factor

        let probability = (base_rate * 0.4 + age_factor + cycle_factor + maint_factor).min(1.0);

        // Deterministic uncertainty band seeded from the equipment id so
        // repeated calls for the same equipment return identical probabilities.
        let entity_seed = history
            .last()
            .map(|h| {
                let mut hasher = std::collections::hash_map::DefaultHasher::new();
                use std::hash::{Hash, Hasher};
                h.equipment_id.hash(&mut hasher);
                hasher.finish()
            })
            .unwrap_or(0);
        let noise = ((entity_seed % 1000) as f64 / 1000.0 - 0.5) * 0.1;
        (probability + noise).clamp(0.0, 1.0)
    }

    /// Estimate remaining useful life in operating hours.
    fn estimate_remaining_life(
        &self,
        health_score: f64,
        history: &[EquipmentTelemetry],
    ) -> f64 {
        if health_score <= 0.0 {
            return 0.0;
        }

        // Base RUL: full health → ~2 years (17520 hours)
        let base_rul = health_score * 17520.0;

        // Degradation factor based on recent trends
        let mut degradation = 0.0f64;
        if history.len() >= 3 {
            let recent: Vec<&EquipmentTelemetry> = history.iter().rev().take(3).collect();
            let vib_change = recent[0].vibration_level - recent[2].vibration_level;
            let temp_change = recent[0].temperature_celsius - recent[2].temperature_celsius;

            if vib_change > 0.0 {
                degradation += vib_change * 100.0;
            }
            if temp_change > 0.0 {
                degradation += temp_change * 50.0;
            }
        }

        (base_rul - degradation).max(0.0)
    }

    /// Classify risk level based on failure probability.
    fn classify_risk(&self, failure_probability: f64) -> RiskLevel {
        if failure_probability >= 0.8 {
            RiskLevel::Critical
        } else if failure_probability >= 0.5 {
            RiskLevel::High
        } else if failure_probability >= 0.2 {
            RiskLevel::Medium
        } else {
            RiskLevel::Low
        }
    }

    /// Schedule the optimal maintenance date.
    fn schedule_maintenance(
        &self,
        risk_level: RiskLevel,
        current_time: DateTime<Utc>,
    ) -> DateTime<Utc> {
        match risk_level {
            RiskLevel::Critical => current_time + Duration::days(1),
            RiskLevel::High => current_time + Duration::days(7),
            RiskLevel::Medium => current_time + Duration::days(30),
            RiskLevel::Low => current_time + Duration::days(90),
        }
    }

    /// Generate maintenance actions based on predicted failure mode.
    fn generate_actions(
        &self,
        failure_mode: FailureMode,
        _category: EquipmentCategory,
        risk_level: RiskLevel,
    ) -> Vec<MaintenanceAction> {
        let mut actions = Vec::new();

        // Find matching signature
        if let Some(sig) = FAILURE_SIGNATURES.iter().find(|s| s.mode == failure_mode) {
            let priority = match risk_level {
                RiskLevel::Critical => 1,
                RiskLevel::High => 2,
                RiskLevel::Medium => 3,
                RiskLevel::Low => 4,
            };

            for (i, action) in sig.actions.iter().enumerate() {
                actions.push(MaintenanceAction {
                    action: action.to_string(),
                    priority: priority + (i as u8),
                    estimated_hours: match i {
                        0 => 4.0,
                        1 => 2.0,
                        _ => 1.0,
                    },
                    required_skills: sig.skills.iter().map(|s| s.to_string()).collect(),
                    parts_needed: sig.parts.iter().map(|p| p.to_string()).collect(),
                });
            }
        }

        // If no specific actions found, add generic inspection
        if actions.is_empty() {
            actions.push(MaintenanceAction {
                action: "Perform comprehensive equipment inspection".to_string(),
                priority: 2,
                estimated_hours: 2.0,
                required_skills: vec!["Maintenance Technician".to_string()],
                parts_needed: vec![],
            });
        }

        actions
    }

    /// Export state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "equipment_tracked".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.telemetry_history.len() as u64)),
        );
        state
    }
}

impl Default for PredictiveMaintenanceEngine {
    fn default() -> Self {
        Self::new(1000)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn create_telemetry(
        equip_id: Uuid,
        uptime: f64,
        vib: f64,
        temp: f64,
        cycles: u64,
        maint_ago_hours: i64,
    ) -> EquipmentTelemetry {
        let now = Utc::now();
        EquipmentTelemetry {
            equipment_id: equip_id,
            uptime_hours: uptime,
            operating_cycles: cycles,
            vibration_level: vib,
            temperature_celsius: temp,
            last_maintenance_at: now - Duration::hours(maint_ago_hours),
            recorded_at: now,
        }
    }

    #[test]
    fn test_health_score_perfect() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        let telemetry = create_telemetry(equip_id, 1000.0, 1.0, 30.0, 1000, 24);
        let score = engine.calculate_health_score(&[telemetry]);
        assert!(score > 0.8);
    }

    #[test]
    fn test_health_score_deteriorated() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        let telemetry = create_telemetry(equip_id, 50000.0, 9.0, 95.0, 50000, 8000);
        let score = engine.calculate_health_score(&[telemetry]);
        assert!(score < 0.5);
    }

    #[test]
    fn test_predict_maintenance() {
        let mut engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        // Add some history with degrading conditions
        for i in 0..5 {
            let vib = 2.0 + (i as f64) * 1.2;
            let temp = 35.0 + (i as f64) * 8.0;
            let uptime = 1000.0 + (i as f64) * 500.0;
            let cycles = 1000 + (i as u64) * 2000;
            let now = Utc::now();

            let telemetry = EquipmentTelemetry {
                equipment_id: equip_id,
                uptime_hours: uptime,
                operating_cycles: cycles,
                vibration_level: vib,
                temperature_celsius: temp,
                last_maintenance_at: now - Duration::hours(1000),
                recorded_at: now + Duration::hours(i * 24),
            };
            engine.record_telemetry(telemetry);
        }

        let prediction = engine.predict_maintenance(equip_id, "CNC-001", EquipmentCategory::CNC);
        assert!(prediction.is_some());

        let pred = prediction.unwrap();
        assert_eq!(pred.equipment_id, equip_id);
        assert!(pred.failure_probability >= 0.0);
        assert!(pred.health_score >= 0.0);
        assert!(pred.estimated_remaining_life_hours >= 0.0);
    }

    #[test]
    fn test_predict_without_data() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        let prediction = engine.predict_maintenance(
            equip_id,
            "Unknown",
            EquipmentCategory::Other,
        );
        assert!(prediction.is_none());
    }

    #[test]
    fn test_risk_classification() {
        let engine = PredictiveMaintenanceEngine::new(10);
        assert_eq!(engine.classify_risk(0.9), RiskLevel::Critical);
        assert_eq!(engine.classify_risk(0.6), RiskLevel::High);
        assert_eq!(engine.classify_risk(0.3), RiskLevel::Medium);
        assert_eq!(engine.classify_risk(0.1), RiskLevel::Low);
    }

    #[test]
    fn test_failure_mode_prediction() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        // High vibration and temperature → likely bearing wear
        let telemetry = create_telemetry(equip_id, 5000.0, 7.0, 80.0, 10000, 1000);
        let (mode, confidence) = engine.predict_failure_mode(&[telemetry]);
        assert!(confidence > 0.3);
        // Should match bearing wear or overheating
        assert!(
            mode == FailureMode::BearingWear
                || mode == FailureMode::Overheating
                || mode == FailureMode::LubricationFailure
        );
    }

    #[test]
    fn test_rul_estimation() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let equip_id = Uuid::new_v4();

        // Healthy equipment should have high RUL
        let healthy = create_telemetry(equip_id, 1000.0, 1.0, 30.0, 1000, 24);
        let rul_healthy = engine.estimate_remaining_life(0.95, &[healthy]);
        assert!(rul_healthy > 10000.0);

        // Deteriorated equipment should have low RUL
        let degraded = create_telemetry(equip_id, 50000.0, 9.0, 95.0, 50000, 8000);
        let rul_degraded = engine.estimate_remaining_life(0.2, &[degraded]);
        assert!(rul_degraded < 5000.0);
    }

    #[test]
    fn test_schedule_maintenance() {
        let engine = PredictiveMaintenanceEngine::new(10);
        let now = Utc::now();

        let critical_date = engine.schedule_maintenance(RiskLevel::Critical, now);
        let low_date = engine.schedule_maintenance(RiskLevel::Low, now);

        assert!(critical_date < low_date);
        assert!(critical_date <= now + Duration::days(2));
        assert!(low_date >= now + Duration::days(30));
    }

    #[test]
    fn test_record_and_query_telemetry() {
        let mut engine = PredictiveMaintenanceEngine::new(100);
        let equip_id = Uuid::new_v4();

        let t = create_telemetry(equip_id, 1000.0, 3.0, 45.0, 5000, 100);
        engine.record_telemetry(t);

        let history = engine.get_telemetry(equip_id);
        assert_eq!(history.len(), 1);

        let no_history = engine.get_telemetry(Uuid::new_v4());
        assert!(no_history.is_empty());
    }

    #[test]
    fn test_actions_generated() {
        let engine = PredictiveMaintenanceEngine::new(10);

        let actions = engine.generate_actions(
            FailureMode::BearingWear,
            EquipmentCategory::Pump,
            RiskLevel::High,
        );
        assert!(!actions.is_empty());
        assert_eq!(actions[0].priority, 2); // High risk → priority 2
    }
}
