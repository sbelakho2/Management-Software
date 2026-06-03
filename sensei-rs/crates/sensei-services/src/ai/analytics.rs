//! Analytics — KPI Computation, Trend Analysis, and Performance Metrics.
//!
//! Derived from analytics/KPI patterns across the Python backend codebase.
//! Provides calculation engines for manufacturing KPIs, trend classification,
//! and performance dashboards.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Trend direction for a metric.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TrendDirection {
    Improving,
    Declining,
    Stable,
    Volatile,
    InsufficientData,
}

/// KPI category for grouping.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum KpiCategory {
    Quality,
    Productivity,
    Maintenance,
    Cost,
    Safety,
    Delivery,
    Inventory,
    Overall,
}

/// Aggregation method for metric calculation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AggregationMethod {
    Sum,
    Average,
    Min,
    Max,
    Count,
    Rate,
    Percentage,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A single KPI measurement data point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiMeasurement {
    pub id: Uuid,
    pub name: String,
    pub category: KpiCategory,
    pub value: f64,
    pub target: Option<f64>,
    pub unit: String,
    pub timestamp: DateTime<Utc>,
    pub tags: HashMap<String, String>,
}

/// Computed KPI with trend and status.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiResult {
    pub name: String,
    pub category: KpiCategory,
    pub current_value: f64,
    pub previous_value: Option<f64>,
    pub target: Option<f64>,
    pub unit: String,
    pub trend: TrendDirection,
    pub change_pct: Option<f64>,
    pub is_on_target: Option<bool>,
    pub sample_size: usize,
}

/// A computed OEE (Overall Equipment Effectiveness) breakdown.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OeeResult {
    pub availability: f64,
    pub performance: f64,
    pub quality: f64,
    pub oee: f64,
    pub availability_loss_hours: f64,
    pub performance_loss_hours: f64,
    pub quality_loss_hours: f64,
}

/// Summary statistics for a data series.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeriesStatistics {
    pub mean: f64,
    pub median: f64,
    pub std_dev: f64,
    pub min: f64,
    pub max: f64,
    pub count: usize,
    pub sum: f64,
    pub q1: f64,
    pub q3: f64,
    pub iqr: f64,
    pub outliers: Vec<f64>,
}

// ---------------------------------------------------------------------------
// Trend Detection Constants
// ---------------------------------------------------------------------------

/// Minimum data points needed for trend analysis.
const MIN_TREND_POINTS: usize = 4;

/// Coefficient of variation threshold for stability classification.
const STABILITY_CV_THRESHOLD: f64 = 0.15;

/// Minimum R² value for a trend to be considered non-volatile.
const TREND_RSQ_THRESHOLD: f64 = 0.6;

// ---------------------------------------------------------------------------
// AnalyticsEngine
// ---------------------------------------------------------------------------

/// Engine for KPI computation, trend analysis, and performance analytics.
pub struct AnalyticsEngine {
    /// Historical KPI measurements keyed by (name, category).
    measurements: HashMap<String, Vec<KpiMeasurement>>,
    /// Maximum measurements to retain per KPI.
    max_history: usize,
}

impl AnalyticsEngine {
    /// Create a new [`AnalyticsEngine`].
    pub fn new(max_history: usize) -> Self {
        Self {
            measurements: HashMap::new(),
            max_history,
        }
    }

    /// Record a KPI measurement.
    pub fn record_measurement(&mut self, measurement: KpiMeasurement) {
        let key = format!("{}:{:?}", measurement.name, measurement.category);
        let entries = self
            .measurements
            .entry(key)
            .or_insert_with(|| Vec::with_capacity(self.max_history));

        entries.push(measurement);

        // Trim oldest entries
        if entries.len() > self.max_history {
            entries.drain(..entries.len() - self.max_history);
        }
    }

    /// Compute a KPI result for a given name and category.
    pub fn compute_kpi(
        &self,
        name: &str,
        category: KpiCategory,
        target: Option<f64>,
    ) -> KpiResult {
        let key = format!("{}:{:?}", name, category);
        let entries = self.measurements.get(&key);

        let (current_value, previous_value, sample_size, trend, change_pct) =
            match entries {
                Some(data) if !data.is_empty() => {
                    let sorted = self.sort_by_time(data);
                    let current = sorted.last().unwrap().value;
                    let prev = if sorted.len() >= 2 {
                        Some(sorted[sorted.len() - 2].value)
                    } else {
                        None
                    };
                    let change = prev.map(|p| {
                        if p != 0.0 {
                            ((current - p) / p) * 100.0
                        } else {
                            0.0
                        }
                    });
                    let trend = self.detect_trend(&sorted);
                    (current, prev, sorted.len(), trend, change)
                }
                _ => (0.0, None, 0, TrendDirection::InsufficientData, None),
            };

        let is_on_target = target.map(|t| {
            if t == 0.0 {
                current_value == 0.0
            } else {
                let deviation = ((current_value - t) / t).abs();
                deviation <= 0.1 // Within 10 % of target
            }
        });

        KpiResult {
            name: name.to_string(),
            category,
            current_value,
            previous_value,
            target,
            unit: entries
                .and_then(|e| e.last())
                .map(|e| e.unit.clone())
                .unwrap_or_default(),
            trend,
            change_pct,
            is_on_target,
            sample_size,
        }
    }

    /// Compute OEE from availability, performance, and quality data.
    pub fn compute_oee(
        &self,
        available_seconds: f64,
        planned_production_seconds: f64,
        ideal_cycle_time_seconds: f64,
        total_parts: u64,
        good_parts: u64,
    ) -> OeeResult {
        // Availability = Operating Time / Planned Production Time
        let availability = if planned_production_seconds > 0.0 {
            available_seconds / planned_production_seconds
        } else {
            0.0
        };

        // Performance = (Ideal Cycle Time × Total Parts) / Operating Time
        let performance = if available_seconds > 0.0 {
            let ideal_time = ideal_cycle_time_seconds * total_parts as f64;
            (ideal_time / available_seconds).min(1.0)
        } else {
            0.0
        };

        // Quality = Good Parts / Total Parts
        let quality = if total_parts > 0 {
            good_parts as f64 / total_parts as f64
        } else {
            1.0
        };

        let oee = availability * performance * quality;

        // Calculate loss hours
        let total_hours = planned_production_seconds / 3600.0;
        let operating_hours = available_seconds / 3600.0;

        OeeResult {
            availability,
            performance,
            quality,
            oee,
            availability_loss_hours: total_hours - operating_hours,
            performance_loss_hours: operating_hours * (1.0 - performance),
            quality_loss_hours: operating_hours * performance * (1.0 - quality),
        }
    }

    /// Calculate statistical summary for a KPI's data series.
    pub fn calculate_statistics(&self, name: &str, category: KpiCategory) -> SeriesStatistics {
        let key = format!("{}:{:?}", name, category);
        let entries = match self.measurements.get(&key) {
            Some(e) => e,
            None => {
                return SeriesStatistics {
                    mean: 0.0,
                    median: 0.0,
                    std_dev: 0.0,
                    min: 0.0,
                    max: 0.0,
                    count: 0,
                    sum: 0.0,
                    q1: 0.0,
                    q3: 0.0,
                    iqr: 0.0,
                    outliers: Vec::new(),
                };
            }
        };

        let values: Vec<f64> = entries.iter().map(|e| e.value).collect();
        let count = values.len();
        if count == 0 {
            return SeriesStatistics {
                mean: 0.0,
                median: 0.0,
                std_dev: 0.0,
                min: 0.0,
                max: 0.0,
                count: 0,
                sum: 0.0,
                q1: 0.0,
                q3: 0.0,
                iqr: 0.0,
                outliers: Vec::new(),
            };
        }

        let sum: f64 = values.iter().sum();
        let mean = sum / count as f64;

        let mut sorted = values.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let min = sorted[0];
        let max = sorted[count - 1];
        let median = if count % 2 == 0 {
            (sorted[count / 2 - 1] + sorted[count / 2]) / 2.0
        } else {
            sorted[count / 2]
        };

        // Variance and std dev
        let variance = if count > 1 {
            values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (count - 1) as f64
        } else {
            0.0
        };
        let std_dev = variance.sqrt();

        // Quartiles
        let q1 = self.percentile(&sorted, 0.25);
        let q3 = self.percentile(&sorted, 0.75);
        let iqr = q3 - q1;

        // Outliers (IQR method: below Q1 - 1.5*IQR or above Q3 + 1.5*IQR)
        let lower_bound = q1 - 1.5 * iqr;
        let upper_bound = q3 + 1.5 * iqr;
        let outliers: Vec<f64> = values
            .iter()
            .filter(|&&v| v < lower_bound || v > upper_bound)
            .copied()
            .collect();

        SeriesStatistics {
            mean,
            median,
            std_dev,
            min,
            max,
            count,
            sum,
            q1,
            q3,
            iqr,
            outliers,
        }
    }

    /// Detect the trend direction from a time-ordered series of measurements.
    pub fn detect_trend(&self, data: &[&KpiMeasurement]) -> TrendDirection {
        if data.len() < MIN_TREND_POINTS {
            return TrendDirection::InsufficientData;
        }

        let values: Vec<f64> = data.iter().map(|m| m.value).collect();
        let n = values.len() as f64;

        // Calculate simple linear regression
        let indices: Vec<f64> = (0..data.len()).map(|i| i as f64).collect();
        let mean_x = indices.iter().sum::<f64>() / n;
        let mean_y = values.iter().sum::<f64>() / n;

        let mut numerator = 0.0f64;
        let mut denom_x = 0.0f64;
        let mut denom_y = 0.0f64;

        for (i, &y) in values.iter().enumerate() {
            let x = i as f64;
            let x_diff = x - mean_x;
            let y_diff = y - mean_y;
            numerator += x_diff * y_diff;
            denom_x += x_diff * x_diff;
            denom_y += y_diff * y_diff;
        }

        // Slope and R²
        let slope = if denom_x > 0.0 {
            numerator / denom_x
        } else {
            0.0
        };

        let r_squared = if denom_x > 0.0 && denom_y > 0.0 {
            (numerator / (denom_x.sqrt() * denom_y.sqrt())).powi(2)
        } else {
            0.0
        };

        // Check volatility
        let mean_abs = mean_y.abs().max(1e-10);
        let cv = (values.iter().map(|v| (v - mean_y).powi(2)).sum::<f64>() / n).sqrt() / mean_abs;

        if cv > STABILITY_CV_THRESHOLD && r_squared < TREND_RSQ_THRESHOLD {
            return TrendDirection::Volatile;
        }

        if r_squared < 0.3 {
            return TrendDirection::Stable;
        }

        if slope > 0.0 {
            TrendDirection::Improving
        } else {
            TrendDirection::Declining
        }
    }

    /// Calculate the percentile of a sorted data series.
    fn percentile(&self, sorted: &[f64], p: f64) -> f64 {
        if sorted.is_empty() {
            return 0.0;
        }
        let n = sorted.len();
        let rank = p * (n - 1) as f64;
        let lower = rank.floor() as usize;
        let upper = rank.ceil() as usize;

        if lower == upper {
            sorted[lower]
        } else {
            let frac = rank - lower as f64;
            sorted[lower] * (1.0 - frac) + sorted[upper] * frac
        }
    }

    /// Sort measurements by timestamp.
    fn sort_by_time<'a>(&self, data: &'a [KpiMeasurement]) -> Vec<&'a KpiMeasurement> {
        let mut sorted: Vec<&KpiMeasurement> = data.iter().collect();
        sorted.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
        sorted
    }

    /// Generate a dashboard summary with multiple KPIs.
    pub fn get_dashboard(
        &self,
        kpi_names: &[(&str, KpiCategory)],
    ) -> Vec<KpiResult> {
        kpi_names
            .iter()
            .map(|(name, category)| {
                self.compute_kpi(name, *category, None)
            })
            .collect()
    }

    /// Export state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "kpis_tracked".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.measurements.len() as u64)),
        );
        state
    }
}

impl Default for AnalyticsEngine {
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

    fn create_measurement(
        name: &str,
        category: KpiCategory,
        value: f64,
        timestamp: DateTime<Utc>,
    ) -> KpiMeasurement {
        KpiMeasurement {
            id: Uuid::new_v4(),
            name: name.to_string(),
            category,
            value,
            target: None,
            unit: "%".to_string(),
            timestamp,
            tags: HashMap::new(),
        }
    }

    // -- AnalyticsEngine Tests -----------------------------------------------

    #[test]
    fn test_record_and_compute_kpi() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        engine.record_measurement(create_measurement(
            "OEE",
            KpiCategory::Overall,
            0.75,
            now,
        ));
        engine.record_measurement(create_measurement(
            "OEE",
            KpiCategory::Overall,
            0.78,
            now + Duration::hours(1),
        ));

        let result = engine.compute_kpi("OEE", KpiCategory::Overall, Some(0.85));
        assert!((result.current_value - 0.78).abs() < 0.01);
        assert!(result.previous_value.is_some());
        assert!((result.previous_value.unwrap() - 0.75).abs() < 0.01);
        assert_eq!(result.sample_size, 2);
    }

    #[test]
    fn test_kpi_no_data() {
        let engine = AnalyticsEngine::new(100);
        let result = engine.compute_kpi("Nonexistent", KpiCategory::Quality, None);
        assert_eq!(result.sample_size, 0);
        assert_eq!(result.trend, TrendDirection::InsufficientData);
    }

    #[test]
    fn test_trend_improving() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        for i in 0..6 {
            engine.record_measurement(create_measurement(
                "OEE",
                KpiCategory::Overall,
                0.60 + (i as f64) * 0.05,
                now + Duration::hours(i),
            ));
        }

        let result = engine.compute_kpi("OEE", KpiCategory::Overall, None);
        assert_eq!(result.trend, TrendDirection::Improving);
    }

    #[test]
    fn test_trend_declining() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        for i in 0..6 {
            engine.record_measurement(create_measurement(
                "Defect Rate",
                KpiCategory::Quality,
                0.05 + (i as f64) * 0.02,
                now + Duration::hours(i),
            ));
        }

        let result = engine.compute_kpi("Defect Rate", KpiCategory::Quality, None);
        // For defect rate, increasing is declining (negative trend)
        assert_eq!(result.trend, TrendDirection::Declining);
    }

    #[test]
    fn test_trend_insufficient_data() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        engine.record_measurement(create_measurement(
            "Test",
            KpiCategory::Productivity,
            0.5,
            now,
        ));

        let result = engine.compute_kpi("Test", KpiCategory::Productivity, None);
        assert_eq!(result.trend, TrendDirection::InsufficientData);
    }

    #[test]
    fn test_oee_calculation() {
        let engine = AnalyticsEngine::new(100);

        // Perfect scenario
        let result = engine.compute_oee(36000.0, 36000.0, 10.0, 3600, 3600);
        assert!((result.oee - 1.0).abs() < 0.001);
        assert!((result.availability - 1.0).abs() < 0.001);
        assert!((result.performance - 1.0).abs() < 0.001);
        assert!((result.quality - 1.0).abs() < 0.001);

        // Realistic scenario: 85% OEE
        let realistic = engine.compute_oee(34200.0, 36000.0, 10.0, 3240, 3078);
        // Availability = 34200/36000 = 0.95
        // Performance = (10*3240)/34200 = 0.947
        // Quality = 3078/3240 = 0.95
        // OEE = 0.95*0.947*0.95 = 0.855
        assert!((realistic.oee - 0.85).abs() < 0.02);
    }

    #[test]
    fn test_statistics() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        let values = [10.0, 12.0, 11.0, 14.0, 13.0, 15.0, 9.0, 11.0, 12.0, 10.0];
        for (i, &v) in values.iter().enumerate() {
            engine.record_measurement(create_measurement(
                "Temperature",
                KpiCategory::Quality,
                v,
                now + Duration::hours(i as i64),
            ));
        }

        let stats = engine.calculate_statistics("Temperature", KpiCategory::Quality);
        assert_eq!(stats.count, 10);
        assert!((stats.mean - 11.7).abs() < 0.1);
        assert!((stats.min - 9.0).abs() < 0.01);
        assert!((stats.max - 15.0).abs() < 0.01);
        assert!(stats.sum > 0.0);
    }

    #[test]
    fn test_empty_statistics() {
        let engine = AnalyticsEngine::new(100);
        let stats = engine.calculate_statistics("Empty", KpiCategory::Quality);
        assert_eq!(stats.count, 0);
        assert!((stats.mean - 0.0).abs() < 0.01);
    }

    #[test]
    fn test_dashboard() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        engine.record_measurement(create_measurement(
            "OEE",
            KpiCategory::Overall,
            0.82,
            now,
        ));
        engine.record_measurement(create_measurement(
            "Defect Rate",
            KpiCategory::Quality,
            0.03,
            now,
        ));

        let dashboard = engine.get_dashboard(&[
            ("OEE", KpiCategory::Overall),
            ("Defect Rate", KpiCategory::Quality),
        ]);
        assert_eq!(dashboard.len(), 2);
    }

    #[test]
    fn test_percentile() {
        let engine = AnalyticsEngine::new(100);
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];

        let median = engine.percentile(&data, 0.5);
        assert!((median - 3.0).abs() < 0.01);

        let q1 = engine.percentile(&data, 0.25);
        assert!((q1 - 2.0).abs() < 0.01);
    }

    #[test]
    fn test_on_target() {
        let mut engine = AnalyticsEngine::new(100);
        let now = Utc::now();

        engine.record_measurement(create_measurement(
            "Defect Rate",
            KpiCategory::Quality,
            0.031,
            now,
        ));

        // Target is 3%, current is 3.1% — within 10% tolerance → on target
        let result = engine.compute_kpi("Defect Rate", KpiCategory::Quality, Some(0.03));
        assert_eq!(result.is_on_target, Some(true));

        // Far from target
        engine.record_measurement(create_measurement(
            "Defect Rate",
            KpiCategory::Quality,
            0.1,
            now + Duration::hours(1),
        ));
        let result = engine.compute_kpi("Defect Rate", KpiCategory::Quality, Some(0.03));
        assert_eq!(result.is_on_target, Some(false));
    }

    #[test]
    fn test_record_does_not_exceed_max() {
        let mut engine = AnalyticsEngine::new(5);
        let now = Utc::now();

        for i in 0..10 {
            engine.record_measurement(create_measurement(
                "A",
                KpiCategory::Quality,
                i as f64,
                now + Duration::hours(i),
            ));
        }

        let stats = engine.calculate_statistics("A", KpiCategory::Quality);
        assert_eq!(stats.count, 5);
    }
}
