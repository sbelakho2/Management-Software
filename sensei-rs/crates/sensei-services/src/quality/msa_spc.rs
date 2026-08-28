//! Measurement Systems Analysis (MSA), Process Capability, and SPC services.
//!
//! - **MSA**: Gage R&R (repeatability & reproducibility), linearity, bias per AIAG MSA 4th Ed.
//! - **Process Capability**: Cp, Cpk, Pp, Ppk calculations.
//! - **SPC / Change Point**: CUSUM / EWMA change point detection.
//!
//! ## SIMD-accelerated statistics
//!
//! The [`calculate_capability`], [`calculate_histogram`], [`mean`], [`std_dev`],
//! [`normal_cdf`], and [`normal_quantile`] functions delegate to
//! `sensei_zt::stats` (Zig SIMD when available, pure-Rust fallback otherwise).

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{new_id, now, EntityId, TenantId};
use uuid::Uuid;

use super::models::{
    ChangePointEvent, ChangePointObservation, ChangePointStudy, MsaMeasurement, MsaResult,
    MsaStudy, MsaStudyType, ProcessCapabilityMeasurement, ProcessCapabilityResult,
    ProcessCapabilityStudy,
};

// ---------------------------------------------------------------------------
// MSA Service
// ---------------------------------------------------------------------------

/// MSA (Measurement Systems Analysis) service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait MsaService: Send + Sync {
    /// Create a new MSA study.
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        study_type: MsaStudyType,
        title: String,
        gauge_id: Option<Uuid>,
        operators_count: u32,
        parts_count: u32,
        trials_count: u32,
    ) -> Result<MsaStudy>;

    /// Get an MSA study by ID.
    async fn get_study(&self, id: EntityId) -> Result<MsaStudy>;

    /// List MSA studies.
    async fn list_studies(&self, _tenant_id: TenantId) -> Result<Vec<MsaStudy>>;

    /// Add a measurement to an MSA study.
    async fn add_measurement(
        &self,
        study_id: EntityId,
        operator_id: Uuid,
        part_id: String,
        trial_number: u32,
        measured_value: f64,
    ) -> Result<MsaMeasurement>;

    /// Compute GRR (Gage Repeatability & Reproducibility) for a study.
    async fn compute_grr(&self, study_id: EntityId) -> Result<MsaResult>;
}

// ---------------------------------------------------------------------------
// Process Capability Service
// ---------------------------------------------------------------------------

/// Process capability service trait.
#[async_trait]
pub trait ProcessCapabilityService: Send + Sync {
    /// Create a new capability study.
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        title: String,
        characteristic: String,
        lsl: f64,
        usl: f64,
        target: Option<f64>,
    ) -> Result<ProcessCapabilityStudy>;

    /// Get a study by ID.
    async fn get_study(&self, id: EntityId) -> Result<ProcessCapabilityStudy>;

    /// List studies.
    async fn list_studies(&self, _tenant_id: TenantId) -> Result<Vec<ProcessCapabilityStudy>>;

    /// Add a measurement to a study.
    async fn add_measurement(
        &self,
        study_id: EntityId,
        measured_value: f64,
        sample_label: Option<String>,
    ) -> Result<ProcessCapabilityMeasurement>;

    /// Compute capability indices (Cp, Cpk, etc.) for a study.
    async fn compute_capability(&self, study_id: EntityId) -> Result<ProcessCapabilityResult>;
}

// ---------------------------------------------------------------------------
// SPC / Change Point Detection Service
// ---------------------------------------------------------------------------

/// Change point detection service trait (CUSUM/EWMA).
#[async_trait]
pub trait ChangePointService: Send + Sync {
    /// Create a change point study.
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        title: String,
        parameter: String,
        sensitivity: f64,
        algorithm: String,
    ) -> Result<ChangePointStudy>;

    /// Add an observation to a study.
    async fn add_observation(
        &self,
        study_id: EntityId,
        value: f64,
        label: Option<String>,
    ) -> Result<ChangePointObservation>;

    /// List observations for a study.
    async fn list_observations(&self, study_id: EntityId) -> Result<Vec<ChangePointObservation>>;

    /// Detect change points in a study.
    async fn detect_change_points(&self, study_id: EntityId) -> Result<Vec<ChangePointEvent>>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// Combined in-memory MSA, Process Capability, and SPC service.
pub struct InMemoryMsaSpcService {
    msa_studies: tokio::sync::RwLock<Vec<MsaStudy>>,
    capa_studies: tokio::sync::RwLock<Vec<ProcessCapabilityStudy>>,
    cp_studies: tokio::sync::RwLock<Vec<ChangePointStudy>>,
}

impl InMemoryMsaSpcService {
    pub fn new() -> Self {
        Self {
            msa_studies: tokio::sync::RwLock::new(Vec::new()),
            capa_studies: tokio::sync::RwLock::new(Vec::new()),
            cp_studies: tokio::sync::RwLock::new(Vec::new()),
        }
    }
}

impl Default for InMemoryMsaSpcService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl MsaService for InMemoryMsaSpcService {
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        study_type: MsaStudyType,
        title: String,
        gauge_id: Option<Uuid>,
        operators_count: u32,
        parts_count: u32,
        trials_count: u32,
    ) -> Result<MsaStudy> {
        let study = MsaStudy {
            id: new_id(),
            study_type,
            title,
            gauge_id,
            operators_count,
            parts_count,
            trials_count,
            status: "In Progress".into(),
            measurements: Vec::new(),
            result: None,
            created_at: now(),
            completed_at: None,
        };
        self.msa_studies.write().await.push(study.clone());
        Ok(study)
    }

    async fn get_study(&self, id: EntityId) -> Result<MsaStudy> {
        self.msa_studies
            .read()
            .await
            .iter()
            .find(|s| s.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("MSA study {id} not found")))
    }

    async fn list_studies(&self, _tenant_id: TenantId) -> Result<Vec<MsaStudy>> {
        let studies = self.msa_studies.read().await;
        Ok(studies.clone())
    }

    async fn add_measurement(
        &self,
        study_id: EntityId,
        operator_id: Uuid,
        part_id: String,
        trial_number: u32,
        measured_value: f64,
    ) -> Result<MsaMeasurement> {
        let mut studies = self.msa_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| SenseiError::NotFound(format!("MSA study {study_id} not found")))?;

        let measurement = MsaMeasurement {
            id: new_id(),
            study_id,
            operator_id,
            part_id,
            trial_number,
            measured_value,
            measured_at: now(),
        };
        study.measurements.push(measurement.clone());
        Ok(measurement)
    }

    async fn compute_grr(&self, study_id: EntityId) -> Result<MsaResult> {
        let mut studies = self.msa_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| SenseiError::NotFound(format!("MSA study {study_id} not found")))?;

        if study.measurements.is_empty() {
            return Err(SenseiError::Validation(
                "No measurements recorded for GRR calculation".into(),
            ));
        }

        // Group measurements by operator and part
        let measurements = &study.measurements;

        // Calculate overall mean
        let n = measurements.len() as f64;
        let _overall_mean: f64 = measurements.iter().map(|m| m.measured_value).sum::<f64>() / n;

        // Group by operator
        let mut operator_means: std::collections::HashMap<Uuid, Vec<f64>> =
            std::collections::HashMap::new();
        // Group by part
        let mut part_means: std::collections::HashMap<String, Vec<f64>> =
            std::collections::HashMap::new();

        for m in measurements {
            operator_means
                .entry(m.operator_id)
                .or_default()
                .push(m.measured_value);
            part_means
                .entry(m.part_id.clone())
                .or_default()
                .push(m.measured_value);
        }

        // Calculate repeatability (EV) - average range method
        // For simplicity: use within-operator standard deviation
        let mut within_operator_var = 0.0;
        let mut operator_count = 0usize;
        for vals in operator_means.values() {
            if vals.len() > 1 {
                let mean = vals.iter().sum::<f64>() / vals.len() as f64;
                let var: f64 = vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
                    / (vals.len() as f64 - 1.0);
                within_operator_var += var;
                operator_count += 1;
            }
        }
        let ev = if operator_count > 0 {
            (within_operator_var / operator_count as f64).sqrt()
        } else {
            0.0
        };

        // Calculate reproducibility (AV) - between-operator variation
        let mut between_operator_var = 0.0;
        let op_count = operator_means.len() as f64;
        if op_count > 1.0 {
            let op_avg: Vec<f64> = operator_means
                .values()
                .map(|v| v.iter().sum::<f64>() / v.len() as f64)
                .collect();
            let grand_op_mean = op_avg.iter().sum::<f64>() / op_count;
            between_operator_var = op_avg
                .iter()
                .map(|m| (m - grand_op_mean).powi(2))
                .sum::<f64>()
                / (op_count - 1.0);
        }
        let av = between_operator_var.sqrt();

        // Calculate part variation (PV)
        let mut between_part_var = 0.0;
        let part_count = part_means.len() as f64;
        if part_count > 1.0 {
            let part_avg: Vec<f64> = part_means
                .values()
                .map(|v| v.iter().sum::<f64>() / v.len() as f64)
                .collect();
            let grand_part_mean = part_avg.iter().sum::<f64>() / part_count;
            between_part_var = part_avg
                .iter()
                .map(|m| (m - grand_part_mean).powi(2))
                .sum::<f64>()
                / (part_count - 1.0);
        }
        let pv = between_part_var.sqrt();

        // GRR = sqrt(EV^2 + AV^2)
        let grr = (ev.powi(2) + av.powi(2)).sqrt();

        // Total variation = sqrt(GRR^2 + PV^2)
        let tv = (grr.powi(2) + pv.powi(2)).sqrt();

        // %GRR = (GRR / TV) * 100
        let grr_percent = if tv > 0.0 { (grr / tv) * 100.0 } else { 0.0 };

        // ndc = number of distinct categories = 1.41 * (PV / GRR)
        let ndc = if grr > 0.0 {
            (1.41 * (pv / grr)).round() as u32
        } else {
            1
        };

        let result = MsaResult {
            id: new_id(),
            study_id,
            repeatability_ev: ev,
            reproducibility_av: av,
            grr,
            part_variation_pv: pv,
            total_variation_tv: tv,
            grr_percent,
            ndc,
            created_at: now(),
        };

        study.result = Some(result.clone());
        study.status = "Completed".into();
        study.completed_at = Some(now());

        Ok(result)
    }
}

#[async_trait]
impl ProcessCapabilityService for InMemoryMsaSpcService {
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        title: String,
        characteristic: String,
        lsl: f64,
        usl: f64,
        target: Option<f64>,
    ) -> Result<ProcessCapabilityStudy> {
        let study = ProcessCapabilityStudy {
            id: new_id(),
            title,
            characteristic,
            lsl,
            usl,
            target,
            status: "In Progress".into(),
            measurements: Vec::new(),
            result: None,
            created_at: now(),
            completed_at: None,
            msa_reference: None,
            decision_grade: false,
        };
        self.capa_studies.write().await.push(study.clone());
        Ok(study)
    }

    async fn get_study(&self, id: EntityId) -> Result<ProcessCapabilityStudy> {
        self.capa_studies
            .read()
            .await
            .iter()
            .find(|s| s.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Capability study {id} not found")))
    }

    async fn list_studies(&self, _tenant_id: TenantId) -> Result<Vec<ProcessCapabilityStudy>> {
        let studies = self.capa_studies.read().await;
        Ok(studies.clone())
    }

    async fn add_measurement(
        &self,
        study_id: EntityId,
        measured_value: f64,
        sample_label: Option<String>,
    ) -> Result<ProcessCapabilityMeasurement> {
        let mut studies = self.capa_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Capability study {study_id} not found"))
            })?;

        let measurement = ProcessCapabilityMeasurement {
            id: new_id(),
            study_id,
            measured_value,
            sample_label,
            measured_at: now(),
        };
        study.measurements.push(measurement.clone());
        Ok(measurement)
    }

    async fn compute_capability(&self, study_id: EntityId) -> Result<ProcessCapabilityResult> {
        let mut studies = self.capa_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Capability study {study_id} not found"))
            })?;

        if study.measurements.len() < 2 {
            return Err(SenseiError::Validation(
                "Need at least 2 measurements for capability analysis".into(),
            ));
        }

        let values: Vec<f64> = study
            .measurements
            .iter()
            .map(|m| m.measured_value)
            .collect();
        let n = values.len() as f64;
        let mean: f64 = values.iter().sum::<f64>() / n;

        // Within-sample (subgroup) standard deviation — Cp/Cpk basis.
        let variance: f64 = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n - 1.0);
        let std_dev = variance.sqrt();

        // Overall (population) standard deviation — Pp/Ppk basis. With
        // individual measurements this is the exact overall dispersion.
        let overall_variance: f64 = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
        let overall_std_dev = overall_variance.sqrt();

        let tolerance = study.usl - study.lsl;

        // Cp = (USL - LSL) / (6 * sigma_within)
        let cp = if std_dev > 0.0 {
            tolerance / (6.0 * std_dev)
        } else {
            0.0
        };

        // Cpu = (USL - mean) / (3 * sigma_within)
        let cpu = if std_dev > 0.0 {
            (study.usl - mean) / (3.0 * std_dev)
        } else {
            0.0
        };

        // Cpl = (mean - LSL) / (3 * sigma_within)
        let cpl = if std_dev > 0.0 {
            (mean - study.lsl) / (3.0 * std_dev)
        } else {
            0.0
        };

        // Cpk = min(Cpu, Cpl)
        let cpk = cpu.min(cpl);

        // Pp / Ppk use the overall standard deviation.
        let pp = if overall_std_dev > 0.0 {
            tolerance / (6.0 * overall_std_dev)
        } else {
            0.0
        };
        let ppu = if overall_std_dev > 0.0 {
            (study.usl - mean) / (3.0 * overall_std_dev)
        } else {
            0.0
        };
        let ppl = if overall_std_dev > 0.0 {
            (mean - study.lsl) / (3.0 * overall_std_dev)
        } else {
            0.0
        };
        let ppk = ppu.min(ppl);

        let is_capable = ProcessCapabilityResult::determine_capability(cpk);

        let result = ProcessCapabilityResult {
            id: new_id(),
            study_id,
            mean,
            std_dev,
            cp,
            cpk,
            cpu,
            cpl,
            pp: Some(pp),
            ppk: Some(ppk),
            sample_size: n as u32,
            is_capable,
            created_at: now(),
        };

        study.result = Some(result.clone());
        study.status = "Completed".into();
        study.completed_at = Some(now());

        Ok(result)
    }
}

#[async_trait]
impl ChangePointService for InMemoryMsaSpcService {
    async fn create_study(
        &self,
        _tenant_id: TenantId,
        title: String,
        parameter: String,
        sensitivity: f64,
        algorithm: String,
    ) -> Result<ChangePointStudy> {
        let study = ChangePointStudy {
            id: new_id(),
            title,
            parameter,
            sensitivity,
            algorithm,
            observations: Vec::new(),
            events: Vec::new(),
            created_at: now(),
        };
        self.cp_studies.write().await.push(study.clone());
        Ok(study)
    }

    async fn add_observation(
        &self,
        study_id: EntityId,
        value: f64,
        label: Option<String>,
    ) -> Result<ChangePointObservation> {
        let mut studies = self.cp_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Change point study {study_id} not found"))
            })?;

        let observation = ChangePointObservation {
            id: new_id(),
            study_id,
            value,
            label,
            observed_at: now(),
        };
        study.observations.push(observation.clone());
        Ok(observation)
    }

    async fn list_observations(&self, study_id: EntityId) -> Result<Vec<ChangePointObservation>> {
        let studies = self.cp_studies.read().await;
        let study = studies.iter().find(|s| s.id == study_id).ok_or_else(|| {
            SenseiError::NotFound(format!("Change point study {study_id} not found"))
        })?;
        Ok(study.observations.clone())
    }

    async fn detect_change_points(&self, study_id: EntityId) -> Result<Vec<ChangePointEvent>> {
        let mut studies = self.cp_studies.write().await;
        let study = studies
            .iter_mut()
            .find(|s| s.id == study_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Change point study {study_id} not found"))
            })?;

        if study.observations.len() < 3 {
            return Ok(Vec::new());
        }

        let values: Vec<f64> = study.observations.iter().map(|o| o.value).collect();
        let n = values.len();
        let mean: f64 = values.iter().sum::<f64>() / n as f64;

        // Simple CUSUM-based change point detection
        let sensitivity = study.sensitivity.max(0.1);
        let threshold = sensitivity * mean.abs().max(1.0);

        let mut events = Vec::new();
        let mut cumulative_sum = 0.0_f64;
        let mut last_change_idx = 0usize;

        for (i, &value) in values.iter().enumerate() {
            cumulative_sum += value - mean;

            if cumulative_sum.abs() > threshold && i > last_change_idx + 1 {
                let magnitude = cumulative_sum;
                let confidence = (magnitude.abs() / threshold).min(1.0);

                let event = ChangePointEvent {
                    id: new_id(),
                    study_id,
                    index_position: i,
                    change_magnitude: magnitude,
                    confidence,
                    notes: Some(format!(
                        "Change detected at observation {} (CUSUM={:.2}, threshold={:.2})",
                        i, cumulative_sum, threshold
                    )),
                    detected_at: now(),
                };
                events.push(event);
                cumulative_sum = 0.0;
                last_change_idx = i;
            }
        }

        study.events.extend(events.clone());
        Ok(events)
    }
}

// ──────────────────────────────────────────────
// SIMD-accelerated SPC helpers
// ──────────────────────────────────────────────

/// Re-export [`sensei_zt::stats::CapabilityResult`] for convenience.
pub use sensei_zt::stats::CapabilityResult;

/// Re-export [`sensei_zt::stats::HistogramResult`] for convenience.
pub use sensei_zt::stats::HistogramResult;

/// Re-export [`sensei_zt::stats::mean`] for convenience.
pub use sensei_zt::stats::mean;

/// Re-export [`sensei_zt::stats::std_dev`] for convenience.
pub use sensei_zt::stats::std_dev;

/// Re-export [`sensei_zt::stats::normal_cdf`] for convenience.
pub use sensei_zt::stats::normal_cdf;

/// Re-export [`sensei_zt::stats::normal_quantile`] for convenience.
pub use sensei_zt::stats::normal_quantile;

/// Compute process capability indices (Cp, Cpk, Pp, Ppk) with SIMD
/// acceleration via the Zig native library when available.
///
/// Delegates to [`sensei_zt::stats::calculate_capability`].
pub fn calculate_capability_spc(
    data: &[f64],
    lsl: f64,
    usl: f64,
    subgroup_size: usize,
) -> CapabilityResult {
    sensei_zt::stats::calculate_capability(data, lsl, usl, subgroup_size)
}

/// Compute a histogram with SIMD-accelerated min/max and bin assignment.
///
/// Delegates to [`sensei_zt::stats::calculate_histogram`].
pub fn calculate_histogram_spc(data: &[f64], bin_count: usize) -> HistogramResult {
    sensei_zt::stats::calculate_histogram(data, bin_count)
}
