//! Canonical TPS contracts shared by the learning and flow surfaces.

/// Measurement state (thirteenth audit): Unknown is an ACTUAL TYPE.
/// A value that is not measured is never silently zero.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum MeasurementState {
    Measured { value: f64 },
    Estimated { value: f64, confidence: f64 },
    Unavailable { reason: String },
    NotApplicable,
}

impl MeasurementState {
    /// The numeric value when one exists; None when unknown — the reader
    /// can never confuse "not measured" with a zero.
    pub fn value(&self) -> Option<f64> {
        match self {
            MeasurementState::Measured { value } => Some(*value),
            MeasurementState::Estimated { value, .. } => Some(*value),
            MeasurementState::Unavailable { .. } | MeasurementState::NotApplicable => None,
        }
    }

    pub fn measured(value: f64) -> Self {
        MeasurementState::Measured { value }
    }

    pub fn unavailable(reason: &str) -> Self {
        MeasurementState::Unavailable {
            reason: reason.to_string(),
        }
    }
}

/// One learning metric — a directional fact, never a composite grade.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct LearningMetric {
    pub key: String,
    pub label: String,
    pub value: MeasurementState,
    pub unit: String,
    pub better: String,
    #[serde(default)]
    pub target: Option<f64>,
    #[serde(default)]
    pub gap: Option<f64>,
    pub guidance: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Unknown is an actual type: an unmeasured value is never zero.
    #[test]
    fn measurement_state_never_fakes_precision() {
        let m = MeasurementState::unavailable("rework is not tracked");
        assert_eq!(m.value(), None, "unavailable has no numeric value");
        let n = MeasurementState::measured(42.0);
        assert_eq!(n.value(), Some(42.0));
        assert!(!matches!(m, MeasurementState::Measured { .. }));
    }
}
