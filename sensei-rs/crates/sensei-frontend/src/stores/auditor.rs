//! Auditor (compliance audits) reactive store.
//!
//! Mirrors the Zustand [`auditor.ts`](frontend/src/stores/auditor.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// Audit statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditStatsDto {
    pub total_audits: i32,
    pub completed: i32,
    pub in_progress: i32,
    pub planned: i32,
    pub overdue: i32,
    pub compliance_rate: f64,
    pub open_findings: i32,
    pub critical_findings: i32,
}

/// An audit entity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditDto {
    pub id: String,
    pub title: String,
    pub audit_type: String,
    pub scope: String,
    pub status: String,
    pub scheduled_date: Option<String>,
    pub completed_date: Option<String>,
    pub score: Option<f64>,
    pub findings_count: i32,
    pub created_at: String,
}

/// An audit finding.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditFindingDto {
    pub id: String,
    pub audit_id: String,
    pub title: String,
    pub description: String,
    pub severity: String,
    pub status: String,
    pub owner: Option<String>,
    pub due_date: Option<String>,
    pub created_at: String,
}

/// A compliance area with metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceAreaDto {
    pub id: String,
    pub name: String,
    pub score: f64,
    pub status: String,
    pub findings_count: i32,
}

/// Reactive store for auditor/compliance data.
#[derive(Debug, Clone)]
pub struct AuditorStore {
    /// Audit statistics.
    pub stats: RwSignal<Option<AuditStatsDto>>,
    /// List of audits.
    pub audits: RwSignal<Vec<AuditDto>>,
    /// Upcoming audits.
    pub upcoming_audits: RwSignal<Vec<AuditDto>>,
    /// Audit findings.
    pub findings: RwSignal<Vec<AuditFindingDto>>,
    /// Open findings.
    pub open_findings: RwSignal<Vec<AuditFindingDto>>,
    /// Compliance areas.
    pub compliance_areas: RwSignal<Vec<ComplianceAreaDto>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
    /// Timestamp of last full fetch (for cache).
    pub last_fetched_at: RwSignal<Option<String>>,
}

const CACHE_DURATION_MS: u64 = 60_000; // 60 seconds

impl AuditorStore {
    pub fn new() -> Self {
        Self {
            stats: RwSignal::new(None),
            audits: RwSignal::new(Vec::new()),
            upcoming_audits: RwSignal::new(Vec::new()),
            findings: RwSignal::new(Vec::new()),
            open_findings: RwSignal::new(Vec::new()),
            compliance_areas: RwSignal::new(Vec::new()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
            last_fetched_at: RwSignal::new(None),
        }
    }

    /// Fetch all auditor data at once (with caching).
    pub async fn fetch_all(&self, client: &ApiClient) {
        if let Some(ts) = self.last_fetched_at.get() {
            if let Ok(parsed) = chrono::DateTime::parse_from_rfc3339(&ts) {
                let elapsed = chrono::Utc::now()
                    .signed_duration_since(parsed.with_timezone(&chrono::Utc))
                    .num_milliseconds() as u64;
                if elapsed < CACHE_DURATION_MS {
                    return;
                }
            }
        }
        self.loading.set(true);
        self.error.set(None);

        let s = client.get::<AuditStatsDto>("/api/v1/auditor/stats").await;
        let a = client.get::<Vec<AuditDto>>("/api/v1/auditor/audits").await;
        let u = client.get::<Vec<AuditDto>>("/api/v1/auditor/upcoming").await;
        let f = client.get::<Vec<AuditFindingDto>>("/api/v1/auditor/findings").await;
        let o = client.get::<Vec<AuditFindingDto>>("/api/v1/auditor/findings/open").await;
        let c = client.get::<Vec<ComplianceAreaDto>>("/api/v1/auditor/compliance-areas").await;

        let mut errors: Vec<String> = Vec::new();
        if let Err(e) = &s { errors.push(e.to_string()); }
        if let Err(e) = &a { errors.push(e.to_string()); }
        if let Err(e) = &u { errors.push(e.to_string()); }
        if let Err(e) = &f { errors.push(e.to_string()); }
        if let Err(e) = &o { errors.push(e.to_string()); }
        if let Err(e) = &c { errors.push(e.to_string()); }

        if let Ok(data) = s { self.stats.set(Some(data)); }
        if let Ok(data) = a { self.audits.set(data); }
        if let Ok(data) = u { self.upcoming_audits.set(data); }
        if let Ok(data) = f { self.findings.set(data); }
        if let Ok(data) = o { self.open_findings.set(data); }
        if let Ok(data) = c { self.compliance_areas.set(data); }
        if !errors.is_empty() {
            self.error.set(Some(errors.join("; ")));
        }

        self.last_fetched_at.set(Some(chrono::Utc::now().to_rfc3339()));
        self.loading.set(false);
    }

    pub async fn fetch_stats(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<AuditStatsDto>("/api/v1/auditor/stats").await {
            Ok(data) => self.stats.set(Some(data)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_audits(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<AuditDto>>("/api/v1/auditor/audits").await {
            Ok(data) => self.audits.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_upcoming_audits(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<AuditDto>>("/api/v1/auditor/upcoming").await {
            Ok(data) => self.upcoming_audits.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_findings(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<AuditFindingDto>>("/api/v1/auditor/findings").await {
            Ok(data) => self.findings.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_open_findings(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<AuditFindingDto>>("/api/v1/auditor/findings/open").await {
            Ok(data) => self.open_findings.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn fetch_compliance_areas(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match client.get::<Vec<ComplianceAreaDto>>("/api/v1/auditor/compliance-areas").await {
            Ok(data) => self.compliance_areas.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.loading.set(false);
    }

    pub async fn create_audit(&self, client: &ApiClient, data: &serde_json::Value) -> Result<AuditDto, ApiError> {
        let audit: AuditDto = client.post("/api/v1/auditor/audits", data).await?;
        self.audits.update(|a| a.push(audit.clone()));
        Ok(audit)
    }

    pub async fn update_audit_status(&self, client: &ApiClient, audit_id: &str, status: &str) -> Result<AuditDto, ApiError> {
        let payload = serde_json::json!({ "status": status });
        let audit: AuditDto = client.put(&format!("/api/v1/auditor/audits/{}/status", audit_id), &payload).await?;
        self.audits.update(|a| {
            if let Some(pos) = a.iter().position(|x| x.id == audit_id) {
                a[pos] = audit.clone();
            }
        });
        Ok(audit)
    }

    pub async fn create_finding(&self, client: &ApiClient, data: &serde_json::Value) -> Result<AuditFindingDto, ApiError> {
        let finding: AuditFindingDto = client.post("/api/v1/auditor/findings", data).await?;
        self.findings.update(|f| f.push(finding.clone()));
        Ok(finding)
    }

    pub async fn update_finding_status(&self, client: &ApiClient, finding_id: &str, status: &str) -> Result<AuditFindingDto, ApiError> {
        let payload = serde_json::json!({ "status": status });
        let finding: AuditFindingDto = client.put(&format!("/api/v1/auditor/findings/{}/status", finding_id), &payload).await?;
        self.findings.update(|f| {
            if let Some(pos) = f.iter().position(|x| x.id == finding_id) {
                f[pos] = finding.clone();
            }
        });
        Ok(finding)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }
}

impl Default for AuditorStore {
    fn default() -> Self {
        Self::new()
    }
}
