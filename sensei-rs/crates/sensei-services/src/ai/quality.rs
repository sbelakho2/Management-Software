//! Quality Analysis — SPC, Control Charts, Process Capability, and Defect Analysis.
//!
//! Uses the [`sensei_zt::stats`](sensei_zt::stats) module (Zig-backed SIMD statistics)
//! for process capability calculations. Implements Western Electric zone rules
//! for control chart violation detection.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Type of control chart.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ControlChartType {
    XBarR,
    XBarS,
    IMrs,
    P,
    U,
    C,
}

/// Zone rule violation type (Western Electric rules).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ZoneRuleViolation {
    /// One point exceeds Zone A (3σ from center line).
    PointBeyond3Sigma,
    /// Two out of three consecutive points in Zone A or beyond (2σ–3σ).
    TwoOfThreeInZoneA,
    /// Four out of five consecutive points in Zone B or beyond (1σ–3σ).
    FourOfFiveInZoneB,
    /// Eight consecutive points on one side of the center line.
    EightOnOneSide,
    /// Six consecutive points increasing or decreasing (trend).
    SixPointTrend,
    /// Fourteen consecutive points alternating up and down.
    FourteenPointOscillation,
}

/// Process stability assessment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProcessStability {
    InControl,
    OutOfControl,
    Warning,
    InsufficientData,
}

/// Quality level classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum QualityLevel {
    Excellent,
    Good,
    Acceptable,
    Marginal,
    Poor,
    Critical,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A single measurement data point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Measurement {
    pub id: Uuid,
    pub value: f64,
    pub subgroup_id: Option<u32>,
    pub timestamp: DateTime<Utc>,
    pub batch_id: Option<String>,
}

/// A process capability analysis result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityAnalysis {
    pub cp: f64,
    pub cpk: f64,
    pub pp: f64,
    pub ppk: f64,
    pub mean: f64,
    pub std_dev: f64,
    pub within_std_dev: f64,
    pub lsl: f64,
    pub usl: f64,
    pub target: f64,
    pub below_lsl_pct: f64,
    pub above_usl_pct: f64,
    pub total_defect_pct: f64,
    pub ppm: u64,
    pub sigma_level: f64,
    pub quality_level: QualityLevel,
}

/// A control chart with limits and detected violations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlChart {
    pub chart_type: ControlChartType,
    pub center_line: f64,
    pub ucl: f64,
    pub lcl: f64,
    pub upper_warning: f64,
    pub lower_warning: f64,
    pub points: Vec<f64>,
    pub violations: Vec<ControlChartViolation>,
    pub stability: ProcessStability,
}

/// A control chart violation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ControlChartViolation {
    pub rule: ZoneRuleViolation,
    pub description: String,
    pub point_index: usize,
    pub severity: f64,
}

/// A quality prediction for a production run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityPrediction {
    pub predicted_defect_rate: f64,
    pub predicted_cpk: f64,
    pub confidence_interval_lower: f64,
    pub confidence_interval_upper: f64,
    pub recommended_params: HashMap<String, serde_json::Value>,
    pub risk_level: QualityLevel,
}

/// Defect analysis result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DefectAnalysis {
    pub total_units: u64,
    pub defect_count: u64,
    pub defect_rate: f64,
    pub defects_by_type: HashMap<String, u64>,
    pub pareto: Vec<(String, u64, f64)>,
    pub top_defects: Vec<(String, f64)>,
}

// ---------------------------------------------------------------------------
// QualityEngine
// ---------------------------------------------------------------------------

/// Engine for quality analysis using SPC, control charts, and process capability.
pub struct QualityEngine {
    /// Measurements keyed by (product_id, characteristic_name).
    measurements: HashMap<String, Vec<Measurement>>,
    /// Maximum measurements per product-characteristic pair.
    max_history: usize,
}

impl QualityEngine {
    /// Create a new [`QualityEngine`].
    pub fn new(max_history: usize) -> Self {
        Self {
            measurements: HashMap::new(),
            max_history,
        }
    }

    /// Record a measurement for quality tracking.
    pub fn record_measurement(&mut self, product_key: &str, measurement: Measurement) {
        let entries = self
            .measurements
            .entry(product_key.to_string())
            .or_insert_with(|| Vec::with_capacity(self.max_history));
        entries.push(measurement);

        if entries.len() > self.max_history {
            entries.drain(..entries.len() - self.max_history);
        }
    }

    /// Get measurements for a product-characteristic pair.
    pub fn get_measurements(&self, product_key: &str) -> Vec<&Measurement> {
        self.measurements
            .get(product_key)
            .map(|v| v.iter().collect())
            .unwrap_or_default()
    }

    /// Calculate process capability for a set of measurements.
    pub fn calculate_capability(
        &self,
        product_key: &str,
        lsl: f64,
        usl: f64,
        target: f64,
        subgroup_size: usize,
    ) -> CapabilityAnalysis {
        let entries = match self.measurements.get(product_key) {
            Some(e) => e,
            None => {
                return CapabilityAnalysis {
                    cp: 0.0,
                    cpk: 0.0,
                    pp: 0.0,
                    ppk: 0.0,
                    mean: 0.0,
                    std_dev: 0.0,
                    within_std_dev: 0.0,
                    lsl,
                    usl,
                    target,
                    below_lsl_pct: 0.0,
                    above_usl_pct: 0.0,
                    total_defect_pct: 0.0,
                    ppm: 0,
                    sigma_level: 0.0,
                    quality_level: QualityLevel::Poor,
                };
            }
        };

        let data: Vec<f64> = entries.iter().map(|m| m.value).collect();

        if data.len() < 2 {
            return CapabilityAnalysis {
                cp: 0.0,
                cpk: 0.0,
                pp: 0.0,
                ppk: 0.0,
                mean: sensei_zt::stats::mean(&data),
                std_dev: 0.0,
                within_std_dev: 0.0,
                lsl,
                usl,
                target,
                below_lsl_pct: 0.0,
                above_usl_pct: 0.0,
                total_defect_pct: 0.0,
                ppm: 0,
                sigma_level: 0.0,
                quality_level: QualityLevel::Critical,
            };
        }

        let result = sensei_zt::stats::calculate_capability(&data, lsl, usl, subgroup_size);

        // Calculate sigma level (Z-score for defects)
        // Sigma level = norm_s_inv(1 - total_defect_pct/2,000,000) + 1.5 (shift)
        let defect_rate = result.total_defect_pct / 100.0;
        let sigma_level = if defect_rate > 0.0 && defect_rate < 1.0 {
            let z = sensei_zt::stats::normal_quantile(1.0 - defect_rate / 2.0);
            (z + 1.5).max(0.0)
        } else if defect_rate <= 0.0 {
            6.0 // Perfect process
        } else {
            0.0
        };

        let quality_level = self.classify_quality(result.cpk);

        // PPM (parts per million defects)
        let ppm = (result.total_defect_pct * 10_000.0).round() as u64;

        CapabilityAnalysis {
            cp: result.cp,
            cpk: result.cpk,
            pp: result.pp,
            ppk: result.ppk,
            mean: result.mean,
            std_dev: result.std_dev,
            within_std_dev: result.within_std_dev,
            lsl,
            usl,
            target,
            below_lsl_pct: result.below_lsl,
            above_usl_pct: result.above_usl,
            total_defect_pct: result.total_defect_pct,
            ppm,
            sigma_level,
            quality_level,
        }
    }

    /// Create an X̄-R (X-bar R) control chart for a set of measurements.
    pub fn create_xbar_r_chart(&self, product_key: &str, subgroup_size: usize) -> ControlChart {
        let entries = match self.measurements.get(product_key) {
            Some(e) => e,
            None => {
                return ControlChart {
                    chart_type: ControlChartType::XBarR,
                    center_line: 0.0,
                    ucl: 0.0,
                    lcl: 0.0,
                    upper_warning: 0.0,
                    lower_warning: 0.0,
                    points: Vec::new(),
                    violations: Vec::new(),
                    stability: ProcessStability::InsufficientData,
                };
            }
        };

        let data: Vec<f64> = entries.iter().map(|m| m.value).collect();
        let n = data.len();

        if n < 2 {
            return ControlChart {
                chart_type: ControlChartType::XBarR,
                center_line: sensei_zt::stats::mean(&data),
                ucl: 0.0,
                lcl: 0.0,
                upper_warning: 0.0,
                lower_warning: 0.0,
                points: data,
                violations: Vec::new(),
                stability: ProcessStability::InsufficientData,
            };
        }

        let grand_mean = sensei_zt::stats::mean(&data);
        let overall_std = sensei_zt::stats::std_dev(&data);

        // For X-bar chart: UCL/LCL = grand_mean ± A2 * Rbar
        // Simplified: use overall std as estimate
        let sg = if subgroup_size < 2 { 2 } else { subgroup_size };
        let _a2 = sensei_zt::stats::d2(sg); // Actually we need A2, but d2 is related
        let a2_val = 3.0 / (sensei_zt::stats::d2(sg) * (sg as f64).sqrt());

        // Estimate Rbar from overall std
        let d2_val = sensei_zt::stats::d2(sg);
        let rbar = if d2_val > 0.0 {
            overall_std * d2_val
        } else {
            overall_std
        };

        let center_line = grand_mean;
        let ucl = grand_mean + a2_val * rbar;
        let lcl = grand_mean - a2_val * rbar;
        let upper_warning = grand_mean + (2.0 / 3.0) * (ucl - grand_mean);
        let lower_warning = grand_mean - (2.0 / 3.0) * (grand_mean - lcl);

        // Detect zone rule violations
        let violations = self.detect_zone_violations(&data, center_line, ucl, lcl);

        let stability = if violations.is_empty() {
            ProcessStability::InControl
        } else if violations.len() <= 2 {
            ProcessStability::Warning
        } else {
            ProcessStability::OutOfControl
        };

        ControlChart {
            chart_type: ControlChartType::XBarR,
            center_line,
            ucl,
            lcl,
            upper_warning,
            lower_warning,
            points: data,
            violations,
            stability,
        }
    }

    /// Detect Western Electric zone rule violations.
    fn detect_zone_violations(
        &self,
        data: &[f64],
        center: f64,
        ucl: f64,
        lcl: f64,
    ) -> Vec<ControlChartViolation> {
        let mut violations = Vec::new();

        if data.len() < 2 {
            return violations;
        }

        let sigma = ((ucl - center) / 3.0).max(0.001); // 1σ width

        // Zone boundaries
        let zone_a_upper = center + 2.0 * sigma;
        let zone_a_lower = center - 2.0 * sigma;
        let zone_b_upper = center + sigma;
        let zone_b_lower = center - sigma;

        // Rule 1: One point beyond 3σ (Zone A+)
        for (i, &point) in data.iter().enumerate() {
            if point > ucl || point < lcl {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::PointBeyond3Sigma,
                    description: format!(
                        "Point {} (value={:.3}) exceeds control limit (UCL={:.3}, LCL={:.3})",
                        i, point, ucl, lcl
                    ),
                    point_index: i,
                    severity: 1.0,
                });
            }
        }

        // Rule 2: Two of three consecutive points in Zone A (2σ–3σ) or beyond
        for i in 0..data.len().saturating_sub(2) {
            let window = &data[i..=i + 2];
            let in_zone_a = window
                .iter()
                .filter(|&&p| p >= zone_a_upper || p <= zone_a_lower)
                .count();
            if in_zone_a >= 2 {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::TwoOfThreeInZoneA,
                    description: format!("Points {}-{}: two of three in Zone A (2σ–3σ)", i, i + 2),
                    point_index: i + 1,
                    severity: 0.8,
                });
            }
        }

        // Rule 3: Four of five consecutive points in Zone B (1σ–3σ) or beyond
        for i in 0..data.len().saturating_sub(4) {
            let window = &data[i..=i + 4];
            let in_zone_b = window
                .iter()
                .filter(|&&p| p >= zone_b_upper || p <= zone_b_lower)
                .count();
            if in_zone_b >= 4 {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::FourOfFiveInZoneB,
                    description: format!("Points {}-{}: four of five in Zone B (1σ–3σ)", i, i + 4),
                    point_index: i + 2,
                    severity: 0.6,
                });
            }
        }

        // Rule 4: Eight consecutive points on one side of center line
        for i in 0..data.len().saturating_sub(7) {
            let window = &data[i..=i + 7];
            let above = window.iter().filter(|&&p| p >= center).count();
            let below = window.iter().filter(|&&p| p <= center).count();

            if above >= 8 || below >= 8 {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::EightOnOneSide,
                    description: format!(
                        "Points {}-{}: eight consecutive on one side of center line",
                        i,
                        i + 7
                    ),
                    point_index: i + 4,
                    severity: 0.7,
                });
            }
        }

        // Rule 5: Six consecutive points increasing or decreasing
        for i in 0..data.len().saturating_sub(5) {
            let window = &data[i..=i + 5];
            let increasing = window.windows(2).all(|w| w[1] >= w[0]);
            let decreasing = window.windows(2).all(|w| w[1] <= w[0]);

            if increasing || decreasing {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::SixPointTrend,
                    description: format!(
                        "Points {}-{}: six consecutive points {}",
                        i,
                        i + 5,
                        if increasing {
                            "increasing"
                        } else {
                            "decreasing"
                        }
                    ),
                    point_index: i + 3,
                    severity: 0.5,
                });
            }
        }

        // Rule 6: Fourteen consecutive points alternating up and down
        // (systematic oscillation — over-control or two alternating sources).
        for i in 0..data.len().saturating_sub(13) {
            let window = &data[i..=i + 13];
            let mut alternates = true;
            for j in 0..window.len() - 2 {
                let dir0 = window[j + 1] > window[j];
                let dir1 = window[j + 2] > window[j + 1];
                if dir0 == dir1 {
                    alternates = false;
                    break;
                }
            }
            if alternates {
                violations.push(ControlChartViolation {
                    rule: ZoneRuleViolation::FourteenPointOscillation,
                    description: format!(
                        "Points {}-{}: fourteen consecutive points alternating up and down",
                        i,
                        i + 13
                    ),
                    point_index: i + 7,
                    severity: 0.5,
                });
            }
        }

        violations
    }

    /// Predict quality for a production run based on historical capability.
    pub fn predict_quality(
        &self,
        product_key: &str,
        lsl: f64,
        usl: f64,
        target: f64,
        subgroup_size: usize,
    ) -> QualityPrediction {
        let capability = self.calculate_capability(product_key, lsl, usl, target, subgroup_size);

        // Predicted defect rate based on current capability
        let predicted_defect_rate = capability.total_defect_pct / 100.0;

        // Confidence interval around the predicted CpK
        let ci_half = if capability.std_dev > 0.0 && capability.cpk > 0.0 {
            capability.cpk * 0.1 // ±10% confidence interval
        } else {
            0.0
        };

        QualityPrediction {
            predicted_defect_rate,
            predicted_cpk: capability.cpk,
            confidence_interval_lower: (capability.cpk - ci_half).max(0.0),
            confidence_interval_upper: capability.cpk + ci_half,
            recommended_params: HashMap::new(),
            risk_level: capability.quality_level,
        }
    }

    /// Analyze defects from a set of defect data.
    pub fn analyze_defects(&self, total_units: u64, defects: &[(String, u64)]) -> DefectAnalysis {
        let mut defects_by_type: HashMap<String, u64> = HashMap::new();
        let mut total_defects = 0u64;

        for (defect_type, count) in defects {
            *defects_by_type.entry(defect_type.clone()).or_insert(0) += count;
            total_defects += count;
        }

        let defect_rate = if total_units > 0 {
            total_defects as f64 / total_units as f64
        } else {
            0.0
        };

        // Pareto analysis: sort by count descending, compute cumulative percentage
        let mut pareto: Vec<(String, u64, f64)> = defects_by_type
            .iter()
            .map(|(k, v)| (k.clone(), *v, 0.0))
            .collect();
        pareto.sort_by_key(|a| std::cmp::Reverse(a.1));

        let mut cumulative = 0u64;
        for (_, count, pct) in &mut pareto {
            cumulative += *count;
            *pct = if total_defects > 0 {
                cumulative as f64 / total_defects as f64 * 100.0
            } else {
                0.0
            };
        }

        // Top defects by percentage
        let top_defects: Vec<(String, f64)> = pareto
            .iter()
            .take(5)
            .map(|(k, v, _)| {
                let pct = if total_defects > 0 {
                    *v as f64 / total_defects as f64 * 100.0
                } else {
                    0.0
                };
                (k.clone(), pct)
            })
            .collect();

        DefectAnalysis {
            total_units,
            defect_count: total_defects,
            defect_rate,
            defects_by_type,
            pareto,
            top_defects,
        }
    }

    /// Classify quality level based on CpK value.
    pub fn classify_quality(&self, cpk: f64) -> QualityLevel {
        if cpk >= 2.0 {
            QualityLevel::Excellent
        } else if cpk >= 1.33 {
            QualityLevel::Good
        } else if cpk >= 1.0 {
            QualityLevel::Acceptable
        } else if cpk >= 0.67 {
            QualityLevel::Marginal
        } else if cpk > 0.0 {
            QualityLevel::Poor
        } else {
            QualityLevel::Critical
        }
    }

    /// Get summary statistics for all tracked metrics.
    pub fn get_summary(&self) -> HashMap<String, serde_json::Value> {
        let mut summary = HashMap::new();
        summary.insert(
            "metrics_tracked".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.measurements.len() as u64)),
        );
        let total: usize = self.measurements.values().map(|v| v.len()).sum();
        summary.insert(
            "total_measurements".to_string(),
            serde_json::Value::Number(serde_json::Number::from(total as u64)),
        );
        summary
    }

    /// Export state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "measurement_groups".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.measurements.len() as u64)),
        );
        state
    }
}

impl Default for QualityEngine {
    fn default() -> Self {
        Self::new(10_000)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn create_measurements(values: &[f64]) -> Vec<Measurement> {
        let now = Utc::now();
        values
            .iter()
            .enumerate()
            .map(|(i, &v)| Measurement {
                id: Uuid::new_v4(),
                value: v,
                subgroup_id: Some((i / 5) as u32),
                timestamp: now,
                batch_id: Some("batch-001".to_string()),
            })
            .collect()
    }

    // -- QualityEngine Tests -------------------------------------------------

    #[test]
    fn test_capability_analysis() {
        let mut engine = QualityEngine::new(100);

        // Centered, low-variance process
        let data = vec![
            10.05, 9.95, 10.02, 9.98, 10.01, 10.03, 9.97, 10.00, 10.04, 9.96,
        ];
        for m in create_measurements(&data) {
            engine.record_measurement("product-a:length", m);
        }

        let capability = engine.calculate_capability("product-a:length", 9.5, 10.5, 10.0, 5);
        assert!(
            capability.cp > 1.0,
            "Cp should be > 1.0, got {}",
            capability.cp
        );
        assert!(
            capability.cpk > 0.5,
            "Cpk should be > 0.5, got {}",
            capability.cpk
        );
        assert!((capability.mean - 10.0).abs() < 0.05);
    }

    #[test]
    fn test_capability_no_data() {
        let engine = QualityEngine::new(100);
        let capability = engine.calculate_capability("nonexistent", 0.0, 10.0, 5.0, 5);
        assert_eq!(capability.quality_level, QualityLevel::Poor);
        assert_eq!(capability.ppm, 0);
    }

    #[test]
    fn test_quality_classification() {
        let engine = QualityEngine::new(100);
        assert_eq!(engine.classify_quality(2.5), QualityLevel::Excellent);
        assert_eq!(engine.classify_quality(1.5), QualityLevel::Good);
        assert_eq!(engine.classify_quality(1.1), QualityLevel::Acceptable);
        assert_eq!(engine.classify_quality(0.8), QualityLevel::Marginal);
        assert_eq!(engine.classify_quality(0.3), QualityLevel::Poor);
        assert_eq!(engine.classify_quality(0.0), QualityLevel::Critical);
    }

    #[test]
    fn test_control_chart_xbar_r() {
        let mut engine = QualityEngine::new(100);

        // In-control process
        let data: Vec<f64> = (0..25)
            .map(|_| 10.0 + rand::random::<f64>() * 0.2 - 0.1)
            .collect();
        for m in create_measurements(&data) {
            engine.record_measurement("product-b:diameter", m);
        }

        let chart = engine.create_xbar_r_chart("product-b:diameter", 5);
        assert!(chart.ucl > chart.center_line);
        assert!(chart.lcl < chart.center_line);
        assert_eq!(chart.chart_type, ControlChartType::XBarR);
    }

    #[test]
    fn test_control_chart_detects_violations() {
        let engine = QualityEngine::new(100);

        // Out-of-control process: point far outside limits
        let data = vec![10.0, 10.1, 9.9, 10.0, 10.2, 9.8, 10.0, 15.0, 10.0, 9.9];
        let violations = engine.detect_zone_violations(&data, 10.0, 12.0, 8.0);
        assert!(!violations.is_empty());
        assert!(violations
            .iter()
            .any(|v| v.rule == ZoneRuleViolation::PointBeyond3Sigma));
    }

    #[test]
    fn test_detect_eight_on_one_side() {
        let engine = QualityEngine::new(100);

        // Eight consecutive points above center
        let data = vec![10.1, 10.2, 10.15, 10.3, 10.25, 10.1, 10.2, 10.15];
        let violations = engine.detect_zone_violations(&data, 10.0, 11.0, 9.0);
        assert!(violations
            .iter()
            .any(|v| v.rule == ZoneRuleViolation::EightOnOneSide));
    }

    #[test]
    fn test_detect_six_point_trend() {
        let engine = QualityEngine::new(100);

        // Six consecutive increasing points
        let data = vec![10.0, 10.1, 10.2, 10.3, 10.4, 10.5];
        let violations = engine.detect_zone_violations(&data, 10.0, 12.0, 8.0);
        assert!(violations
            .iter()
            .any(|v| v.rule == ZoneRuleViolation::SixPointTrend));
    }

    #[test]
    fn test_detect_fourteen_point_oscillation() {
        let engine = QualityEngine::new(100);

        // Fourteen consecutive alternating points (up, down, up, down, ...).
        let mut data = Vec::new();
        for i in 0..14 {
            data.push(10.0 + if i % 2 == 0 { 0.05 } else { -0.05 });
        }
        let violations = engine.detect_zone_violations(&data, 10.0, 11.0, 9.0);
        assert!(
            violations
                .iter()
                .any(|v| v.rule == ZoneRuleViolation::FourteenPointOscillation),
            "expected 14-point oscillation violation, got: {violations:?}"
        );

        // A monotonic run of the same length must NOT trigger the rule.
        let monotonic: Vec<f64> = (0..14).map(|i| 10.0 + i as f64 * 0.01).collect();
        let violations = engine.detect_zone_violations(&monotonic, 10.0, 11.0, 9.0);
        assert!(!violations
            .iter()
            .any(|v| v.rule == ZoneRuleViolation::FourteenPointOscillation));
    }

    #[test]
    fn test_defect_analysis() {
        let engine = QualityEngine::new(100);

        let defects = vec![
            ("scratch".to_string(), 45),
            ("dent".to_string(), 30),
            ("color_mismatch".to_string(), 15),
            ("dimension".to_string(), 10),
        ];

        let analysis = engine.analyze_defects(1000, &defects);
        assert_eq!(analysis.total_units, 1000);
        assert_eq!(analysis.defect_count, 100);
        assert!((analysis.defect_rate - 0.1).abs() < 0.001);
        assert_eq!(analysis.defects_by_type.len(), 4);

        // Pareto: top defect should be "scratch"
        assert_eq!(analysis.pareto[0].0, "scratch");
        assert_eq!(analysis.pareto[1].0, "dent");
    }

    #[test]
    fn test_predict_quality() {
        let mut engine = QualityEngine::new(100);

        let data = vec![
            10.05, 9.95, 10.02, 9.98, 10.01, 10.03, 9.97, 10.00, 10.04, 9.96,
        ];
        for m in create_measurements(&data) {
            engine.record_measurement("product-c:thickness", m);
        }

        let prediction = engine.predict_quality("product-c:thickness", 9.5, 10.5, 10.0, 5);
        assert!(prediction.predicted_cpk > 0.5);
        assert!(prediction.confidence_interval_lower < prediction.predicted_cpk);
        assert!(prediction.confidence_interval_upper > prediction.predicted_cpk);
    }

    #[test]
    fn test_get_summary() {
        let mut engine = QualityEngine::new(100);

        for m in create_measurements(&[1.0, 2.0, 3.0]) {
            engine.record_measurement("test", m);
        }

        let summary = engine.get_summary();
        assert_eq!(summary.get("metrics_tracked").unwrap().as_u64().unwrap(), 1);
        assert_eq!(
            summary.get("total_measurements").unwrap().as_u64().unwrap(),
            3
        );
    }

    #[test]
    fn test_control_chart_insufficient_data() {
        let engine = QualityEngine::new(100);
        let chart = engine.create_xbar_r_chart("empty", 5);
        assert_eq!(chart.stability, ProcessStability::InsufficientData);
    }

    #[test]
    fn test_capability_with_large_subgroup() {
        let mut engine = QualityEngine::new(1000);
        let data: Vec<f64> = (0..100)
            .map(|_| 50.0 + rand::random::<f64>() * 2.0 - 1.0)
            .collect();
        for m in create_measurements(&data) {
            engine.record_measurement("product-d:weight", m);
        }

        let capability = engine.calculate_capability("product-d:weight", 45.0, 55.0, 50.0, 5);
        assert!(capability.cp > 0.5);
        assert!(capability.mean > 49.0 && capability.mean < 51.0);
        assert!(capability.ppm < 1_000_000); // Should be well within spec
    }
}
