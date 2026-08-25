//! Supplier Quality services.
//!
//! Provides supplier scorecard computation (PPM, OTD, CoPQ), SCAR (Supplier
//! Corrective Action Request) workflow, and complaint / 8D management.

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, TenantId, Timestamp, new_id, now};
use std::collections::HashMap;
use uuid::Uuid;

use super::models::{
    ComplaintStatus, EightDReport, FindingSeverity, NpsStats, Scar, ScarStatus,
    SupplierPeriodStats, SupplierProfile, SupplierScorecard,
};

// ---------------------------------------------------------------------------
// Traits
// ---------------------------------------------------------------------------

/// Supplier profile and scorecard management.
#[async_trait]
pub trait SupplierService: Send + Sync {
    /// Upsert a supplier profile.
    async fn upsert_supplier(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        name: String,
        tier: String,
    ) -> Result<SupplierProfile>;

    /// Record a receipt of units from a supplier.
    async fn record_receipt(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        units_received: u64,
    ) -> Result<SupplierPeriodStats>;

    /// Record defects found from a supplier lot.
    async fn record_defects(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        defects_found: u64,
    ) -> Result<SupplierPeriodStats>;

    /// Record a delivery event (on-time or late).
    async fn record_delivery(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        on_time: bool,
    ) -> Result<SupplierPeriodStats>;

    /// Record cost of poor quality for a supplier.
    async fn record_copq(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        copq_amount: f64,
    ) -> Result<SupplierPeriodStats>;

    /// Compute a supplier scorecard for a period.
    async fn compute_scorecard(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
    ) -> Result<SupplierScorecard>;

    /// List supplier profiles.
    async fn list_suppliers(&self, _tenant_id: TenantId) -> Result<Vec<SupplierProfile>>;
}

/// SCAR (Supplier Corrective Action Request) management.
#[async_trait]
pub trait ScarService: Send + Sync {
    /// Create a new SCAR.
    async fn create_scar(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        title: String,
        description: String,
        severity: FindingSeverity,
        due_date: Option<Timestamp>,
    ) -> Result<Scar>;

    /// Get a SCAR by ID.
    async fn get_scar(&self, id: EntityId) -> Result<Scar>;

    /// List SCARs for a tenant.
    async fn list_scars(&self, _tenant_id: TenantId) -> Result<Vec<Scar>>;

    /// Send SCAR to supplier (transition to SentToSupplier).
    async fn send_scar(&self, id: EntityId) -> Result<Scar>;

    /// Add containment action.
    async fn add_containment(&self, id: EntityId, action: String) -> Result<Scar>;

    /// Set root cause.
    async fn set_root_cause(&self, id: EntityId, root_cause: String) -> Result<Scar>;

    /// Add corrective action.
    async fn add_corrective_action(&self, id: EntityId, action: String) -> Result<Scar>;

    /// Verify and close a SCAR.
    async fn verify_and_close(
        &self,
        id: EntityId,
        verification_notes: String,
    ) -> Result<Scar>;
}

/// Customer satisfaction service (complaints, surveys, NPS).
#[async_trait]
pub trait CustomerSatisfactionService: Send + Sync {
    /// Create a complaint.
    async fn create_complaint(
        &self,
        _tenant_id: TenantId,
        customer_id: Uuid,
        description: String,
        severity: FindingSeverity,
        product_id: Option<Uuid>,
    ) -> Result<super::models::CustomerComplaint>;

    /// Add containment action to complaint.
    async fn add_complaint_containment(
        &self,
        id: EntityId,
        action: String,
    ) -> Result<super::models::CustomerComplaint>;

    /// Set complaint root cause.
    async fn set_complaint_root_cause(
        &self,
        id: EntityId,
        root_cause: String,
    ) -> Result<super::models::CustomerComplaint>;

    /// Add corrective action to complaint.
    async fn add_complaint_corrective_action(
        &self,
        id: EntityId,
        action: String,
    ) -> Result<super::models::CustomerComplaint>;

    /// Close a complaint.
    async fn close_complaint(&self, id: EntityId) -> Result<super::models::CustomerComplaint>;

    /// Generate 8D report from complaint.
    async fn generate_8d_report(
        &self,
        complaint_id: EntityId,
        team: Vec<String>,
    ) -> Result<EightDReport>;

    /// List complaints.
    async fn list_complaints(&self, _tenant_id: TenantId) -> Result<Vec<super::models::CustomerComplaint>>;

    /// Create customer survey.
    async fn create_survey(
        &self,
        _tenant_id: TenantId,
        title: String,
        survey_type: String,
    ) -> Result<super::models::CustomerSurvey>;

    /// Add response to survey.
    async fn add_survey_response(
        &self,
        survey_id: EntityId,
        customer_id: Uuid,
        nps_score: u32,
        feedback: Option<String>,
    ) -> Result<super::models::CustomerSurveyResponse>;

    /// Compute NPS statistics.
    async fn compute_nps(&self, survey_id: Option<EntityId>) -> Result<NpsStats>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// Combined in-memory supplier quality service.
pub struct InMemorySupplierQualityService {
    suppliers: tokio::sync::RwLock<Vec<SupplierProfile>>,
    stats: tokio::sync::RwLock<Vec<(String, String, SupplierPeriodStats)>>, // (supplier_id, period_key)
    scorecards: tokio::sync::RwLock<Vec<SupplierScorecard>>,
    scars: tokio::sync::RwLock<Vec<Scar>>,
    complaints: tokio::sync::RwLock<Vec<super::models::CustomerComplaint>>,
    surveys: tokio::sync::RwLock<Vec<super::models::CustomerSurvey>>,
    _8d_reports: tokio::sync::RwLock<Vec<EightDReport>>,
    /// Per-(tenant, day) sequence counters for SCAR and complaint numbers.
    scar_counters: tokio::sync::RwLock<HashMap<(Uuid, String), u64>>,
    complaint_counters: tokio::sync::RwLock<HashMap<(Uuid, String), u64>>,
}

impl InMemorySupplierQualityService {
    pub fn new() -> Self {
        Self {
            suppliers: tokio::sync::RwLock::new(Vec::new()),
            stats: tokio::sync::RwLock::new(Vec::new()),
            scorecards: tokio::sync::RwLock::new(Vec::new()),
            scars: tokio::sync::RwLock::new(Vec::new()),
            complaints: tokio::sync::RwLock::new(Vec::new()),
            surveys: tokio::sync::RwLock::new(Vec::new()),
            _8d_reports: tokio::sync::RwLock::new(Vec::new()),
            scar_counters: tokio::sync::RwLock::new(HashMap::new()),
            complaint_counters: tokio::sync::RwLock::new(HashMap::new()),
        }
    }

    /// Next per-tenant daily SCAR sequence number (e.g. `SCAR-20260824-0001`).
    async fn _next_scar_number(&self, tenant_id: Uuid) -> String {
        let day = chrono::Utc::now().format("%Y%m%d").to_string();
        let mut counters = self.scar_counters.write().await;
        let seq = counters.entry((tenant_id, day.clone())).or_insert(0);
        *seq += 1;
        format!("SCAR-{day}-{seq:04}")
    }

    /// Next per-tenant daily complaint sequence number.
    async fn _next_complaint_number(&self, tenant_id: Uuid) -> String {
        let day = chrono::Utc::now().format("%Y%m%d").to_string();
        let mut counters = self.complaint_counters.write().await;
        let seq = counters.entry((tenant_id, day.clone())).or_insert(0);
        *seq += 1;
        format!("CMP-{day}-{seq:04}")
    }

    fn _get_or_create_stats<'a>(
        stats: &'a mut Vec<(String, String, SupplierPeriodStats)>,
        supplier_id: &'a str,
        period_key: &'a str,
    ) -> &'a mut SupplierPeriodStats {
        let idx = stats
            .iter()
            .position(|(s, p, _)| s == supplier_id && p == period_key);
        let idx = idx.unwrap_or_else(|| {
            let new_stats = SupplierPeriodStats {
                period_key: period_key.to_string(),
                units_received: 0,
                defects_found: 0,
                lots_received: 0,
                lots_rejected: 0,
                on_time_deliveries: 0,
                late_deliveries: 0,
                total_copq: 0.0,
            };
            stats.push((supplier_id.to_string(), period_key.to_string(), new_stats));
            stats.len() - 1
        });
        &mut stats[idx].2
    }
}

impl Default for InMemorySupplierQualityService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl SupplierService for InMemorySupplierQualityService {
    async fn upsert_supplier(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        name: String,
        tier: String,
    ) -> Result<SupplierProfile> {
        let mut suppliers = self.suppliers.write().await;
        if let Some(existing) = suppliers
            .iter_mut()
            .find(|s| s.supplier_id == supplier_id)
        {
            existing.name = name;
            existing.tier = tier;
            return Ok(existing.clone());
        }
        let profile = SupplierProfile {
            id: new_id(),
            supplier_id,
            name,
            tier,
            status: "active".to_string(),
            created_at: now(),
        };
        suppliers.push(profile.clone());
        Ok(profile)
    }

    async fn record_receipt(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        units_received: u64,
    ) -> Result<SupplierPeriodStats> {
        let mut stats = self.stats.write().await;
        let s = Self::_get_or_create_stats(&mut stats, &supplier_id, &period_key);
        s.units_received += units_received;
        s.lots_received += 1;
        Ok(s.clone())
    }

    async fn record_defects(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        defects_found: u64,
    ) -> Result<SupplierPeriodStats> {
        let mut stats = self.stats.write().await;
        let s = Self::_get_or_create_stats(&mut stats, &supplier_id, &period_key);
        s.defects_found += defects_found;
        s.lots_rejected += 1;
        Ok(s.clone())
    }

    async fn record_delivery(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        on_time: bool,
    ) -> Result<SupplierPeriodStats> {
        let mut stats = self.stats.write().await;
        let s = Self::_get_or_create_stats(&mut stats, &supplier_id, &period_key);
        if on_time {
            s.on_time_deliveries += 1;
        } else {
            s.late_deliveries += 1;
        }
        Ok(s.clone())
    }

    async fn record_copq(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
        copq_amount: f64,
    ) -> Result<SupplierPeriodStats> {
        let mut stats = self.stats.write().await;
        let s = Self::_get_or_create_stats(&mut stats, &supplier_id, &period_key);
        s.total_copq += copq_amount;
        Ok(s.clone())
    }

    async fn compute_scorecard(
        &self,
        _tenant_id: TenantId,
        supplier_id: String,
        period_key: String,
    ) -> Result<SupplierScorecard> {
        let stats = self.stats.read().await;
        let entry = stats
            .iter()
            .find(|(s, p, _)| s == &supplier_id && p == &period_key)
            .map(|(_, _, st)| st.clone());

        let stats = entry.unwrap_or(SupplierPeriodStats {
            period_key: period_key.clone(),
            units_received: 0,
            defects_found: 0,
            lots_received: 0,
            lots_rejected: 0,
            on_time_deliveries: 0,
            late_deliveries: 0,
            total_copq: 0.0,
        });

        let ppm = stats.ppm();
        let otd = stats.otd_percent();

        // Quality score: inverse of PPM (normalized to 0-100)
        let quality_score = if ppm <= 0.0 {
            100.0
        } else {
            (100.0_f64 - (ppm / 10_000.0).min(100.0)).max(0.0)
        };

        // Delivery score = OTD %
        let delivery_score = otd;

        // CoPQ score: inverse of CoPQ relative to units received
        let copq_score = if stats.total_copq <= 0.0 || stats.units_received == 0 {
            100.0
        } else {
            let copq_per_unit = stats.total_copq / stats.units_received as f64;
            (100.0_f64 - (copq_per_unit * 10.0).min(100.0)).max(0.0)
        };

        // Overall: weighted average
        let overall = quality_score * 0.30 + delivery_score * 0.30 + copq_score * 0.40;

        let suppliers = self.suppliers.read().await;
        let tier = suppliers
            .iter()
            .find(|s| s.supplier_id == supplier_id)
            .map(|s| s.tier.clone())
            .unwrap_or_default();

        let scorecard = SupplierScorecard {
            supplier_id,
            period_key,
            ppm_score: ppm,
            otd_score: otd,
            quality_score,
            delivery_score,
            copq_score,
            overall_score: overall,
            tier,
            computed_at: now(),
        };

        let mut scorecards = self.scorecards.write().await;
        scorecards.push(scorecard.clone());
        Ok(scorecard)
    }

    async fn list_suppliers(&self, _tenant_id: TenantId) -> Result<Vec<SupplierProfile>> {
        let suppliers = self.suppliers.read().await;
        Ok(suppliers.clone())
    }
}

#[async_trait]
impl ScarService for InMemorySupplierQualityService {
    async fn create_scar(
        &self,
        tenant_id: TenantId,
        supplier_id: String,
        title: String,
        description: String,
        severity: FindingSeverity,
        due_date: Option<Timestamp>,
    ) -> Result<Scar> {
        let scar = Scar {
            id: new_id(),
            scar_number: self._next_scar_number(tenant_id).await,
            supplier_id,
            title,
            description,
            status: ScarStatus::Open,
            severity,
            containment_action: None,
            root_cause: None,
            corrective_action: None,
            verification_notes: None,
            due_date,
            created_at: now(),
            updated_at: now(),
        };
        self.scars.write().await.push(scar.clone());
        Ok(scar)
    }

    async fn get_scar(&self, id: EntityId) -> Result<Scar> {
        self.scars
            .read()
            .await
            .iter()
            .find(|s| s.id == id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))
    }

    async fn list_scars(&self, _tenant_id: TenantId) -> Result<Vec<Scar>> {
        let scars = self.scars.read().await;
        Ok(scars.clone())
    }

    async fn send_scar(&self, id: EntityId) -> Result<Scar> {
        let mut scars = self.scars.write().await;
        let scar = scars
            .iter_mut()
            .find(|s| s.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))?;
        scar.status = ScarStatus::SentToSupplier;
        scar.updated_at = now();
        Ok(scar.clone())
    }

    async fn add_containment(&self, id: EntityId, action: String) -> Result<Scar> {
        let mut scars = self.scars.write().await;
        let scar = scars
            .iter_mut()
            .find(|s| s.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))?;
        scar.containment_action = Some(action);
        scar.status = ScarStatus::ContainmentInProgress;
        scar.updated_at = now();
        Ok(scar.clone())
    }

    async fn set_root_cause(&self, id: EntityId, root_cause: String) -> Result<Scar> {
        let mut scars = self.scars.write().await;
        let scar = scars
            .iter_mut()
            .find(|s| s.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))?;
        scar.root_cause = Some(root_cause);
        scar.status = ScarStatus::RootCauseAnalysis;
        scar.updated_at = now();
        Ok(scar.clone())
    }

    async fn add_corrective_action(&self, id: EntityId, action: String) -> Result<Scar> {
        let mut scars = self.scars.write().await;
        let scar = scars
            .iter_mut()
            .find(|s| s.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))?;
        scar.corrective_action = Some(action);
        scar.status = ScarStatus::CorrectiveActionDefined;
        scar.updated_at = now();
        Ok(scar.clone())
    }

    async fn verify_and_close(
        &self,
        id: EntityId,
        verification_notes: String,
    ) -> Result<Scar> {
        let mut scars = self.scars.write().await;
        let scar = scars
            .iter_mut()
            .find(|s| s.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("SCAR {id} not found")))?;
        scar.verification_notes = Some(verification_notes);
        scar.status = ScarStatus::Closed;
        scar.updated_at = now();
        Ok(scar.clone())
    }
}

#[async_trait]
impl CustomerSatisfactionService for InMemorySupplierQualityService {
    async fn create_complaint(
        &self,
        tenant_id: TenantId,
        customer_id: Uuid,
        description: String,
        severity: FindingSeverity,
        product_id: Option<Uuid>,
    ) -> Result<super::models::CustomerComplaint> {
        let complaint = super::models::CustomerComplaint {
            id: new_id(),
            complaint_number: self._next_complaint_number(tenant_id).await,
            customer_id,
            product_id,
            description,
            status: ComplaintStatus::Open,
            severity,
            containment_action: None,
            root_cause: None,
            corrective_action: None,
            closed_at: None,
            created_at: now(),
            updated_at: now(),
        };
        self.complaints.write().await.push(complaint.clone());
        Ok(complaint)
    }

    async fn add_complaint_containment(
        &self,
        id: EntityId,
        action: String,
    ) -> Result<super::models::CustomerComplaint> {
        let mut complaints = self.complaints.write().await;
        let c = complaints
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint {id} not found")))?;
        c.containment_action = Some(action);
        c.status = ComplaintStatus::ContainmentInProgress;
        c.updated_at = now();
        Ok(c.clone())
    }

    async fn set_complaint_root_cause(
        &self,
        id: EntityId,
        root_cause: String,
    ) -> Result<super::models::CustomerComplaint> {
        let mut complaints = self.complaints.write().await;
        let c = complaints
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint {id} not found")))?;
        c.root_cause = Some(root_cause);
        c.status = ComplaintStatus::RootCauseAnalysis;
        c.updated_at = now();
        Ok(c.clone())
    }

    async fn add_complaint_corrective_action(
        &self,
        id: EntityId,
        action: String,
    ) -> Result<super::models::CustomerComplaint> {
        let mut complaints = self.complaints.write().await;
        let c = complaints
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint {id} not found")))?;
        c.corrective_action = Some(action);
        c.status = ComplaintStatus::CorrectiveAction;
        c.updated_at = now();
        Ok(c.clone())
    }

    async fn close_complaint(&self, id: EntityId) -> Result<super::models::CustomerComplaint> {
        let mut complaints = self.complaints.write().await;
        let c = complaints
            .iter_mut()
            .find(|c| c.id == id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint {id} not found")))?;
        c.status = ComplaintStatus::Closed;
        c.closed_at = Some(now());
        c.updated_at = now();
        Ok(c.clone())
    }

    async fn generate_8d_report(
        &self,
        complaint_id: EntityId,
        team: Vec<String>,
    ) -> Result<EightDReport> {
        let complaints = self.complaints.read().await;
        let c = complaints
            .iter()
            .find(|c| c.id == complaint_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Complaint {complaint_id} not found")))?;

        let report = EightDReport {
            id: new_id(),
            complaint_id,
            d1_team: team,
            d2_problem_description: c.description.clone(),
            d3_containment: c.containment_action.clone().unwrap_or_default(),
            d4_root_cause: c.root_cause.clone().unwrap_or_default(),
            d5_corrective_action: c.corrective_action.clone().unwrap_or_default(),
            d6_implementation: String::new(),
            d7_preventive_action: String::new(),
            d8_celebration: String::new(),
            created_at: now(),
        };
        self._8d_reports.write().await.push(report.clone());
        Ok(report)
    }

    async fn list_complaints(
        &self,
        _tenant_id: TenantId,
    ) -> Result<Vec<super::models::CustomerComplaint>> {
        let complaints = self.complaints.read().await;
        Ok(complaints.clone())
    }

    async fn create_survey(
        &self,
        _tenant_id: TenantId,
        title: String,
        survey_type: String,
    ) -> Result<super::models::CustomerSurvey> {
        let survey = super::models::CustomerSurvey {
            id: new_id(),
            title,
            survey_type,
            responses: Vec::new(),
            created_at: now(),
        };
        self.surveys.write().await.push(survey.clone());
        Ok(survey)
    }

    async fn add_survey_response(
        &self,
        survey_id: EntityId,
        customer_id: Uuid,
        nps_score: u32,
        feedback: Option<String>,
    ) -> Result<super::models::CustomerSurveyResponse> {
        let mut surveys = self.surveys.write().await;
        let survey = surveys
            .iter_mut()
            .find(|s| s.id == survey_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Survey {survey_id} not found")))?;

        let response = super::models::CustomerSurveyResponse {
            id: new_id(),
            survey_id,
            customer_id,
            nps_score,
            feedback,
            response_date: now(),
        };
        survey.responses.push(response.clone());
        Ok(response)
    }

    async fn compute_nps(&self, survey_id: Option<EntityId>) -> Result<NpsStats> {
        let surveys = self.surveys.read().await;
        let responses: Vec<&super::models::CustomerSurveyResponse> = match survey_id {
            Some(sid) => surveys
                .iter()
                .find(|s| s.id == sid)
                .map(|s| s.responses.iter().collect())
                .unwrap_or_default(),
            None => surveys.iter().flat_map(|s| s.responses.iter()).collect(),
        };

        let total = responses.len() as u32;
        if total == 0 {
            return Ok(NpsStats {
                total_responses: 0,
                promoters: 0,
                passives: 0,
                detractors: 0,
                nps_score: 0.0,
                promoter_percent: 0.0,
                passive_percent: 0.0,
                detractor_percent: 0.0,
            });
        }

        let promoters = responses.iter().filter(|r| r.nps_score >= 9).count() as u32;
        let passives = responses
            .iter()
            .filter(|r| (7..=8).contains(&r.nps_score))
            .count() as u32;
        let detractors = responses.iter().filter(|r| r.nps_score <= 6).count() as u32;

        let promoter_pct = (promoters as f64 / total as f64) * 100.0;
        let passive_pct = (passives as f64 / total as f64) * 100.0;
        let detractor_pct = (detractors as f64 / total as f64) * 100.0;
        let nps = promoter_pct - detractor_pct;

        Ok(NpsStats {
            total_responses: total,
            promoters,
            passives,
            detractors,
            nps_score: nps,
            promoter_percent: promoter_pct,
            passive_percent: passive_pct,
            detractor_percent: detractor_pct,
        })
    }
}
