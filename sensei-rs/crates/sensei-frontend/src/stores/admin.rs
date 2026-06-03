//! Admin configuration store — gates, approval workflows, templates, roles,
//! learning cadences, feature flags, and audit logs.
//!
//! Port of [`frontend/src/stores/admin.ts`](frontend/src/stores/admin.ts).

use leptos::prelude::*;
use std::collections::HashSet;
use crate::api::client::{ApiClient, ApiError};

// ---------------------------------------------------------------------------
// Re-exported domain types
// ---------------------------------------------------------------------------

pub type GateStatus = String; // "active" | "inactive"
pub type ApprovalType = String; // "quote" | "change_order" | "invoice" | "purchase" | "expense"
pub type TemplateType = String; // "a3" | "obeya" | "email" | "report"
pub type RoleType = String; // "operator" | "team_lead" | "supervisor" | "gm" | "admin"
pub type LearningFrequency = String; // "daily" | "weekly" | "monthly" | "quarterly"
pub type FeatureFlagCategory = String; // "feature" | "experiment" | "killswitch"

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Gate {
    pub id: String,
    pub name: String,
    pub phase: String,
    pub description: String,
    pub required_approvers: i32,
    pub bypass_roles: Vec<RoleType>,
    pub conditions: Vec<String>,
    pub status: GateStatus,
    pub order: i32,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ApprovalWorkflow {
    pub id: String,
    #[serde(rename = "type")]
    pub approval_type: ApprovalType,
    pub name: String,
    pub threshold_amount: Option<f64>,
    pub required_roles: Vec<RoleType>,
    pub sequence_required: bool,
    pub timeout_hours: i32,
    pub auto_escalate: bool,
    pub escalation_roles: Vec<RoleType>,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Template {
    pub id: String,
    #[serde(rename = "type")]
    pub template_type: TemplateType,
    pub name: String,
    pub description: String,
    pub content: String,
    pub sections: Option<Vec<String>>,
    pub variables: Vec<String>,
    pub is_default: bool,
    pub created_by: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Role {
    pub id: String,
    pub name: RoleType,
    pub display_name: String,
    pub description: String,
    pub permissions: Vec<String>,
    pub member_count: i32,
    pub can_approve: bool,
    pub hierarchy_level: i32,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct LearningCadence {
    pub id: String,
    pub name: String,
    pub frequency: LearningFrequency,
    pub duration_minutes: i32,
    pub mandatory: bool,
    pub target_roles: Vec<RoleType>,
    pub topics: Vec<String>,
    pub reminder_days_before: i32,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FeatureFlag {
    pub id: String,
    pub key: String,
    pub name: String,
    pub description: String,
    pub enabled: bool,
    pub rollout_percentage: f64,
    pub target_roles: Option<Vec<RoleType>>,
    pub requires_restart: bool,
    pub category: FeatureFlagCategory,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AuditLogEntry {
    pub id: String,
    pub created_at: String,
    pub user_email: String,
    pub action: String,
    pub entity_type: String,
    pub entity_id: String,
    pub request_id: String,
    pub ip_address: Option<String>,
    pub extra_data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AdminStats {
    pub total_gates: i32,
    pub active_gates: i32,
    pub total_approvals: i32,
    pub active_approvals: i32,
    pub total_templates: i32,
    pub default_templates: i32,
    pub total_roles: i32,
    pub total_users: i32,
    pub total_learning_cadences: i32,
    pub active_learning_cadences: i32,
    pub total_feature_flags: i32,
    pub enabled_features: i32,
}

impl Default for AdminStats {
    fn default() -> Self {
        Self {
            total_gates: 0,
            active_gates: 0,
            total_approvals: 0,
            active_approvals: 0,
            total_templates: 0,
            default_templates: 0,
            total_roles: 0,
            total_users: 0,
            total_learning_cadences: 0,
            active_learning_cadences: 0,
            total_feature_flags: 0,
            enabled_features: 0,
        }
    }
}

// ---------------------------------------------------------------------------
// AdminStore
// ---------------------------------------------------------------------------

const CACHE_DURATION_MS: f64 = 30_000.0; // 30 seconds

#[derive(Debug, Clone)]
pub struct AdminStore {
    // Data signals
    pub gates: RwSignal<Vec<Gate>>,
    pub approvals: RwSignal<Vec<ApprovalWorkflow>>,
    pub templates: RwSignal<Vec<Template>>,
    pub roles: RwSignal<Vec<Role>>,
    pub learning_cadences: RwSignal<Vec<LearningCadence>>,
    pub feature_flags: RwSignal<Vec<FeatureFlag>>,
    pub audit_logs: RwSignal<Vec<AuditLogEntry>>,
    pub stats: RwSignal<Option<AdminStats>>,

    // Loading & error state
    pub loading_ops: RwSignal<HashSet<String>>,
    pub error: RwSignal<Option<String>>,
    pub last_fetched_at: RwSignal<Option<f64>>,
}

impl AdminStore {
    pub fn new() -> Self {
        Self {
            gates: RwSignal::new(Vec::new()),
            approvals: RwSignal::new(Vec::new()),
            templates: RwSignal::new(Vec::new()),
            roles: RwSignal::new(Vec::new()),
            learning_cadences: RwSignal::new(Vec::new()),
            feature_flags: RwSignal::new(Vec::new()),
            audit_logs: RwSignal::new(Vec::new()),
            stats: RwSignal::new(None),
            loading_ops: RwSignal::new(HashSet::new()),
            error: RwSignal::new(None),
            last_fetched_at: RwSignal::new(None),
        }
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    fn start_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.insert(op.to_string());
        });
        self.error.set(None);
    }

    fn end_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.remove(op);
        });
    }

    fn is_cache_valid(&self) -> bool {
        if let Some(last) = self.last_fetched_at.get() {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as f64;
            (now - last) < CACHE_DURATION_MS
        } else {
            false
        }
    }

    pub fn is_op_loading(&self, op: &str) -> bool {
        self.loading_ops.get().contains(op)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Gates
    // -----------------------------------------------------------------------

    pub async fn fetch_gates(&self, client: &ApiClient) {
        if self.is_cache_valid() && !self.loading_ops.get().is_empty() {
            return;
        }
        self.start_op("fetchGates");
        match client.get::<serde_json::Value>("/admin/gates").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.gates.set(items);
                }
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_millis() as f64;
                self.last_fetched_at.set(Some(now));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchGates");
    }

    pub async fn fetch_gate_by_id(&self, client: &ApiClient, id: &str) -> Result<Gate, ()> {
        self.start_op("fetchGateById");
        let result = client.get::<Gate>(&format!("/admin/gates/{id}")).await;
        match result {
            Ok(gate) => {
                self.end_op("fetchGateById");
                Ok(gate)
            }
            Err(e) => {
                // Fallback to cached
                let cached = self.gates.get().into_iter().find(|g| g.id == id);
                if let Some(g) = cached {
                    self.end_op("fetchGateById");
                    return Ok(g);
                }
                self.error.set(Some(e.to_string()));
                self.end_op("fetchGateById");
                Err(())
            }
        }
    }

    pub async fn create_gate(&self, client: &ApiClient, gate_data: serde_json::Value) -> Result<Gate, ()> {
        self.start_op("createGate");
        match client.post::<Gate, serde_json::Value>("/admin/gates", &gate_data).await {
            Ok(new_gate) => {
                self.gates.update(|gates| gates.push(new_gate.clone()));
                self.end_op("createGate");
                Ok(new_gate)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createGate");
                Err(())
            }
        }
    }

    pub async fn update_gate(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<Gate, ()> {
        self.start_op("updateGate");
        match client.put::<Gate, serde_json::Value>(&format!("/admin/gates/{id}"), &updates).await {
            Ok(updated) => {
                self.gates.update(|gates| {
                    if let Some(pos) = gates.iter().position(|g| g.id == id) {
                        gates[pos] = updated.clone();
                    }
                });
                self.end_op("updateGate");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateGate");
                Err(())
            }
        }
    }

    pub async fn delete_gate(&self, client: &ApiClient, id: &str) -> Result<(), ()> {
        self.start_op("deleteGate");
        match client.delete::<serde_json::Value>(&format!("/admin/gates/{id}")).await {
            Ok(_) => {
                self.gates.update(|gates| gates.retain(|g| g.id != id));
                self.end_op("deleteGate");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("deleteGate");
                Err(())
            }
        }
    }

    pub async fn toggle_gate_status(&self, client: &ApiClient, id: &str) {
        let gate_opt = self.gates.get().into_iter().find(|g| g.id == id);
        if let Some(gate) = gate_opt {
            let new_status = if gate.status == "active" { "inactive" } else { "active" };
            let updates = serde_json::json!({ "status": new_status });
            let _ = self.update_gate(client, id, updates).await;
        }
    }

    pub async fn reorder_gates(&self, client: &ApiClient, gate_ids: Vec<String>) -> Result<(), ()> {
        self.start_op("reorderGates");
        let body = serde_json::json!({ "gate_ids": gate_ids });
        match client.post::<serde_json::Value, serde_json::Value>("/admin/gates/reorder", &body).await {
            Ok(_) => {
                self.gates.update(|gates| {
                    for (index, gid) in gate_ids.iter().enumerate() {
                        if let Some(gate) = gates.iter_mut().find(|g| g.id == *gid) {
                            gate.order = (index + 1) as i32;
                        }
                    }
                });
                self.end_op("reorderGates");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("reorderGates");
                Err(())
            }
        }
    }

    // -----------------------------------------------------------------------
    // Approvals
    // -----------------------------------------------------------------------

    pub async fn fetch_approvals(&self, client: &ApiClient) {
        self.start_op("fetchApprovals");
        match client.get::<serde_json::Value>("/admin/approvals").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.approvals.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchApprovals");
    }

    pub async fn create_approval(&self, client: &ApiClient, approval_data: serde_json::Value) -> Result<ApprovalWorkflow, ()> {
        self.start_op("createApproval");
        match client.post::<ApprovalWorkflow, serde_json::Value>("/admin/approvals", &approval_data).await {
            Ok(new) => {
                self.approvals.update(|a| a.push(new.clone()));
                self.end_op("createApproval");
                Ok(new)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createApproval");
                Err(())
            }
        }
    }

    pub async fn update_approval(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<ApprovalWorkflow, ()> {
        self.start_op("updateApproval");
        match client.put::<ApprovalWorkflow, serde_json::Value>(&format!("/admin/approvals/{id}"), &updates).await {
            Ok(updated) => {
                self.approvals.update(|a| {
                    if let Some(pos) = a.iter().position(|x| x.id == id) {
                        a[pos] = updated.clone();
                    }
                });
                self.end_op("updateApproval");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateApproval");
                Err(())
            }
        }
    }

    pub async fn delete_approval(&self, client: &ApiClient, id: &str) -> Result<(), ()> {
        self.start_op("deleteApproval");
        match client.delete::<serde_json::Value>(&format!("/admin/approvals/{id}")).await {
            Ok(_) => {
                self.approvals.update(|a| a.retain(|x| x.id != id));
                self.end_op("deleteApproval");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("deleteApproval");
                Err(())
            }
        }
    }

    pub async fn toggle_approval_status(&self, client: &ApiClient, id: &str) {
        let approval_opt = self.approvals.get().into_iter().find(|a| a.id == id);
        if let Some(approval) = approval_opt {
            let updates = serde_json::json!({ "is_active": !approval.is_active });
            let _ = self.update_approval(client, id, updates).await;
        }
    }

    // -----------------------------------------------------------------------
    // Templates
    // -----------------------------------------------------------------------

    pub async fn fetch_templates(&self, client: &ApiClient) {
        self.start_op("fetchTemplates");
        match client.get::<serde_json::Value>("/admin/templates").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.templates.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchTemplates");
    }

    pub async fn create_template(&self, client: &ApiClient, template_data: serde_json::Value) -> Result<Template, ()> {
        self.start_op("createTemplate");
        match client.post::<Template, serde_json::Value>("/admin/templates", &template_data).await {
            Ok(new) => {
                self.templates.update(|t| t.push(new.clone()));
                self.end_op("createTemplate");
                Ok(new)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createTemplate");
                Err(())
            }
        }
    }

    pub async fn update_template(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<Template, ()> {
        self.start_op("updateTemplate");
        match client.put::<Template, serde_json::Value>(&format!("/admin/templates/{id}"), &updates).await {
            Ok(updated) => {
                self.templates.update(|t| {
                    if let Some(pos) = t.iter().position(|x| x.id == id) {
                        t[pos] = updated.clone();
                    }
                });
                self.end_op("updateTemplate");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateTemplate");
                Err(())
            }
        }
    }

    pub async fn delete_template(&self, client: &ApiClient, id: &str) -> Result<(), ()> {
        self.start_op("deleteTemplate");
        match client.delete::<serde_json::Value>(&format!("/admin/templates/{id}")).await {
            Ok(_) => {
                self.templates.update(|t| t.retain(|x| x.id != id));
                self.end_op("deleteTemplate");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("deleteTemplate");
                Err(())
            }
        }
    }

    pub async fn set_default_template(&self, client: &ApiClient, id: &str) {
        let template_type = {
            let templates = self.templates.get();
            templates.into_iter().find(|t| t.id == id).map(|t| t.template_type.clone())
        };
        if let Some(typ) = template_type {
            match client.put::<serde_json::Value, serde_json::Value>(
                &format!("/admin/templates/{id}"),
                &serde_json::json!({ "is_default": true }),
            ).await {
                Ok(_) => {
                    self.templates.update(|t| {
                        for template in t.iter_mut() {
                            if template.template_type == typ {
                                template.is_default = template.id == id;
                            }
                        }
                    });
                }
                Err(e) => {
                    self.error.set(Some(e.to_string()));
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Roles
    // -----------------------------------------------------------------------

    pub async fn fetch_roles(&self, client: &ApiClient) {
        self.start_op("fetchRoles");
        match client.get::<serde_json::Value>("/admin/roles").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.roles.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchRoles");
    }

    pub async fn update_role_permissions(&self, client: &ApiClient, id: &str, permissions: Vec<String>) -> Result<Role, ()> {
        self.start_op("updateRolePermissions");
        let body = serde_json::json!({ "permissions": permissions });
        match client.put::<Role, serde_json::Value>(&format!("/admin/roles/{id}"), &body).await {
            Ok(updated) => {
                self.roles.update(|r| {
                    if let Some(pos) = r.iter().position(|x| x.id == id) {
                        r[pos] = updated.clone();
                    }
                });
                self.end_op("updateRolePermissions");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateRolePermissions");
                Err(())
            }
        }
    }

    // -----------------------------------------------------------------------
    // Learning Cadences
    // -----------------------------------------------------------------------

    pub async fn fetch_learning_cadences(&self, client: &ApiClient) {
        self.start_op("fetchLearningCadences");
        match client.get::<serde_json::Value>("/admin/learning-cadences").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.learning_cadences.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchLearningCadences");
    }

    pub async fn create_learning_cadence(&self, client: &ApiClient, cadence_data: serde_json::Value) -> Result<LearningCadence, ()> {
        self.start_op("createLearningCadence");
        match client.post::<LearningCadence, serde_json::Value>("/admin/learning-cadences", &cadence_data).await {
            Ok(new) => {
                self.learning_cadences.update(|c| c.push(new.clone()));
                self.end_op("createLearningCadence");
                Ok(new)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createLearningCadence");
                Err(())
            }
        }
    }

    pub async fn update_learning_cadence(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<LearningCadence, ()> {
        self.start_op("updateLearningCadence");
        match client.put::<LearningCadence, serde_json::Value>(&format!("/admin/learning-cadences/{id}"), &updates).await {
            Ok(updated) => {
                self.learning_cadences.update(|c| {
                    if let Some(pos) = c.iter().position(|x| x.id == id) {
                        c[pos] = updated.clone();
                    }
                });
                self.end_op("updateLearningCadence");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateLearningCadence");
                Err(())
            }
        }
    }

    pub async fn delete_learning_cadence(&self, client: &ApiClient, id: &str) -> Result<(), ()> {
        self.start_op("deleteLearningCadence");
        match client.delete::<serde_json::Value>(&format!("/admin/learning-cadences/{id}")).await {
            Ok(_) => {
                self.learning_cadences.update(|c| c.retain(|x| x.id != id));
                self.end_op("deleteLearningCadence");
                Ok(())
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("deleteLearningCadence");
                Err(())
            }
        }
    }

    pub async fn toggle_learning_cadence_status(&self, client: &ApiClient, id: &str) {
        let cadence_opt = self.learning_cadences.get().into_iter().find(|c| c.id == id);
        if let Some(cadence) = cadence_opt {
            let updates = serde_json::json!({ "is_active": !cadence.is_active });
            let _ = self.update_learning_cadence(client, id, updates).await;
        }
    }

    // -----------------------------------------------------------------------
    // Feature Flags
    // -----------------------------------------------------------------------

    pub async fn fetch_feature_flags(&self, client: &ApiClient) {
        self.start_op("fetchFeatureFlags");
        match client.get::<serde_json::Value>("/admin/feature-flags").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.feature_flags.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchFeatureFlags");
    }

    pub async fn update_feature_flag(&self, client: &ApiClient, id: &str, updates: serde_json::Value) -> Result<FeatureFlag, ()> {
        self.start_op("updateFeatureFlag");
        match client.put::<FeatureFlag, serde_json::Value>(&format!("/admin/feature-flags/{id}"), &updates).await {
            Ok(updated) => {
                self.feature_flags.update(|f| {
                    if let Some(pos) = f.iter().position(|x| x.id == id) {
                        f[pos] = updated.clone();
                    }
                });
                self.end_op("updateFeatureFlag");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateFeatureFlag");
                Err(())
            }
        }
    }

    pub async fn toggle_feature_flag(&self, client: &ApiClient, id: &str) {
        let flag_opt = self.feature_flags.get().into_iter().find(|f| f.id == id);
        if let Some(flag) = flag_opt {
            let updates = serde_json::json!({ "enabled": !flag.enabled });
            let _ = self.update_feature_flag(client, id, updates).await;
        }
    }

    pub async fn update_rollout_percentage(&self, client: &ApiClient, id: &str, percentage: f64) {
        let updates = serde_json::json!({ "rollout_percentage": percentage });
        let _ = self.update_feature_flag(client, id, updates).await;
    }

    // -----------------------------------------------------------------------
    // Audit Logs
    // -----------------------------------------------------------------------

    pub async fn fetch_audit_logs(&self, client: &ApiClient) {
        self.start_op("fetchAuditLogs");
        match client.get::<serde_json::Value>("/audit-logs").await {
            Ok(data) => {
                if let Some(items) = data.get("items").and_then(|v| serde_json::from_value(v.clone()).ok()) {
                    self.audit_logs.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchAuditLogs");
    }

    // -----------------------------------------------------------------------
    // Stats
    // -----------------------------------------------------------------------

    pub async fn fetch_stats(&self, client: &ApiClient) {
        self.start_op("fetchStats");
        match client.get::<AdminStats>("/admin/stats").await {
            Ok(stats) => {
                self.stats.set(Some(stats));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchStats");
    }
}

impl Default for AdminStore {
    fn default() -> Self {
        Self::new()
    }
}
