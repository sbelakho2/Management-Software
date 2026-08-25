//! Email drafting store — AI-powered draft generation, templates, history.
//!
//! Port of [`frontend/src/stores/email-drafting-store.ts`](frontend/src/stores/email-drafting-store.ts).

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type EmailTone = String; // "formal" | "friendly" | "professional" | "urgent" | "casual"
pub type EmailPurpose = String; // "quote_followup" | "order_confirmation" | "shipping_notification" | ...
pub type DraftStatus = String; // "draft" | "review" | "approved" | "sent" | "discarded"
pub type Language = String; // "en" | "fr" | "de" | "es" | "ar"
pub type ComplianceCheckType = String; // "gdpr" | "sox" | "iso" | "internal"
pub type SuggestionType = String; // "tone" | "clarity" | "completeness" | "compliance"

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Recipient {
    pub email: String,
    pub name: Option<String>,
    pub role: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct EmailContext {
    pub recipients: Vec<Recipient>,
    pub subject: Option<String>,
    pub purpose: EmailPurpose,
    pub reference_id: Option<String>,
    pub reference_type: Option<String>,
    pub customer_name: Option<String>,
    pub language: Language,
    pub tone: EmailTone,
    pub urgency: String, // "low" | "normal" | "high" | "urgent"
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ThreadContext {
    pub thread_id: String,
    pub subject: String,
    pub previous_messages: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GenerationRequest {
    pub context: EmailContext,
    pub thread_context: Option<ThreadContext>,
    pub key_points: Vec<String>,
    pub additional_instructions: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GeneratedDraft {
    pub id: String,
    pub subject: String,
    pub body: String,
    pub tone: EmailTone,
    pub purpose: EmailPurpose,
    pub language: Language,
    pub status: DraftStatus,
    pub confidence_score: f64,
    pub compliance_checks: Vec<ComplianceCheck>,
    pub improvement_suggestions: Vec<ImprovementSuggestion>,
    pub created_at: String,
    pub updated_at: String,
    pub generated_by: String,
    pub reviewed_by: Option<String>,
    pub sent_at: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ComplianceCheck {
    pub check_type: ComplianceCheckType,
    pub status: String, // "passed" | "warning" | "failed"
    pub message: String,
    pub severity: String, // "info" | "warning" | "error"
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ImprovementSuggestion {
    pub suggestion_type: SuggestionType,
    pub original: String,
    pub suggested: String,
    pub reason: String,
    pub priority: String, // "low" | "medium" | "high"
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct EmailTemplate {
    pub id: String,
    pub name: String,
    pub purpose: EmailPurpose,
    pub subject_template: String,
    pub body_template: String,
    pub tone: EmailTone,
    pub language: Language,
    pub variables: Vec<String>,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DraftHistoryEntry {
    pub id: String,
    pub draft_id: String,
    pub action: String, // "created" | "updated" | "reviewed" | "approved" | "sent" | "discarded"
    pub user_id: String,
    pub comment: Option<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RecentRecipient {
    pub email: String,
    pub name: String,
    pub last_used: String,
    pub use_count: i32,
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

pub fn get_purpose_label(purpose: &str) -> &str {
    match purpose {
        "quote_followup" => "Quote Follow-up",
        "order_confirmation" => "Order Confirmation",
        "shipping_notification" => "Shipping Notification",
        "payment_reminder" => "Payment Reminder",
        "meeting_invitation" => "Meeting Invitation",
        "general" => "General",
        _ => purpose,
    }
}

pub fn get_tone_label(tone: &str) -> &str {
    match tone {
        "formal" => "Formal",
        "friendly" => "Friendly",
        "professional" => "Professional",
        "urgent" => "Urgent",
        "casual" => "Casual",
        _ => tone,
    }
}

pub fn get_language_label(language: &str) -> &str {
    match language {
        "en" => "English",
        "fr" => "French",
        "de" => "German",
        "es" => "Spanish",
        "ar" => "Arabic",
        _ => language,
    }
}

pub fn get_status_label(status: &str) -> &str {
    match status {
        "draft" => "Draft",
        "review" => "In Review",
        "approved" => "Approved",
        "sent" => "Sent",
        "discarded" => "Discarded",
        _ => status,
    }
}

pub fn get_status_color(status: &str) -> &str {
    match status {
        "draft" => "gray",
        "review" => "blue",
        "approved" => "green",
        "sent" => "purple",
        "discarded" => "red",
        _ => "gray",
    }
}

pub fn get_confidence_color(score: f64) -> &'static str {
    if score >= 0.8 {
        "green"
    } else if score >= 0.5 {
        "yellow"
    } else {
        "red"
    }
}

pub fn validate_recipient(recipient: &serde_json::Value) -> Vec<String> {
    let mut errors = Vec::new();
    if let Some(email) = recipient.get("email").and_then(|v| v.as_str()) {
        if !email.contains('@') {
            errors.push("Invalid email format".to_string());
        }
    } else {
        errors.push("Email is required".to_string());
    }
    errors
}

pub fn create_default_context(recipient: Recipient) -> EmailContext {
    EmailContext {
        recipients: vec![recipient],
        subject: None,
        purpose: "general".to_string(),
        reference_id: None,
        reference_type: None,
        customer_name: None,
        language: "en".to_string(),
        tone: "professional".to_string(),
        urgency: "normal".to_string(),
    }
}

// ---------------------------------------------------------------------------
// EmailDraftingStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct EmailDraftingStore {
    // Data
    pub drafts: RwSignal<Vec<GeneratedDraft>>,
    pub current_draft: RwSignal<Option<GeneratedDraft>>,
    pub recent_recipients: RwSignal<Vec<RecentRecipient>>,
    pub templates: RwSignal<Vec<EmailTemplate>>,
    pub draft_history: RwSignal<Vec<DraftHistoryEntry>>,

    // Loading & error
    pub is_generating: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
}

impl EmailDraftingStore {
    pub fn new() -> Self {
        Self {
            drafts: RwSignal::new(Vec::new()),
            current_draft: RwSignal::new(None),
            recent_recipients: RwSignal::new(Vec::new()),
            templates: RwSignal::new(Vec::new()),
            draft_history: RwSignal::new(Vec::new()),
            is_generating: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Draft generation
    // -----------------------------------------------------------------------

    pub async fn generate_draft(
        &self,
        client: &ApiClient,
        request: GenerationRequest,
    ) -> Result<GeneratedDraft, ApiError> {
        self.is_generating.set(true);
        self.error.set(None);

        match client
            .post::<GeneratedDraft, GenerationRequest>("/email-drafting/generate", &request)
            .await
        {
            Ok(draft) => {
                self.drafts.update(|d| d.push(draft.clone()));
                self.current_draft.set(Some(draft.clone()));
                self.is_generating.set(false);
                Ok(draft)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.is_generating.set(false);
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Draft CRUD
    // -----------------------------------------------------------------------

    pub fn update_draft(&self, id: &str, updates: serde_json::Value) {
        self.drafts.update(|drafts| {
            if let Some(draft) = drafts.iter_mut().find(|d| d.id == id) {
                if let Some(subject) = updates.get("subject").and_then(|v| v.as_str()) {
                    draft.subject = subject.to_string();
                }
                if let Some(body) = updates.get("body").and_then(|v| v.as_str()) {
                    draft.body = body.to_string();
                }
                if let Some(status) = updates.get("status").and_then(|v| v.as_str()) {
                    draft.status = status.to_string();
                }
                draft.updated_at = chrono::Utc::now().to_rfc3339();
            }
        });

        // Also update current_draft if it matches
        let is_current = self
            .current_draft
            .get()
            .map(|d| d.id == id)
            .unwrap_or(false);
        if is_current {
            let drafts = self.drafts.get();
            if let Some(updated) = drafts.into_iter().find(|d| d.id == id) {
                self.current_draft.set(Some(updated));
            }
        }
    }

    pub fn approve_draft(&self, id: &str, reviewer_id: &str) {
        self.update_draft(
            id,
            serde_json::json!({
                "status": "approved",
                "reviewed_by": reviewer_id,
            }),
        );
    }

    pub fn mark_sent(&self, id: &str) {
        self.update_draft(
            id,
            serde_json::json!({
                "status": "sent",
                "sent_at": chrono::Utc::now().to_rfc3339(),
            }),
        );
    }

    pub fn discard_draft(&self, id: &str, reason: Option<&str>) {
        let mut updates = serde_json::json!({ "status": "discarded" });
        if let Some(r) = reason {
            if let Some(obj) = updates.as_object_mut() {
                obj.insert(
                    "discard_reason".to_string(),
                    serde_json::Value::String(r.to_string()),
                );
            }
        }
        self.update_draft(id, updates);
    }

    pub async fn regenerate_draft(
        &self,
        client: &ApiClient,
        id: &str,
        feedback: Option<&str>,
    ) -> Result<GeneratedDraft, ApiError> {
        self.is_generating.set(true);
        self.error.set(None);

        let mut body = serde_json::json!({ "draft_id": id });
        if let Some(fb) = feedback {
            if let Some(obj) = body.as_object_mut() {
                obj.insert(
                    "feedback".to_string(),
                    serde_json::Value::String(fb.to_string()),
                );
            }
        }

        match client
            .post::<GeneratedDraft, serde_json::Value>("/email-drafting/regenerate", &body)
            .await
        {
            Ok(draft) => {
                self.drafts.update(|d| {
                    if let Some(pos) = d.iter().position(|x| x.id == draft.id) {
                        d[pos] = draft.clone();
                    } else {
                        d.push(draft.clone());
                    }
                });
                self.current_draft.set(Some(draft.clone()));
                self.is_generating.set(false);
                Ok(draft)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.is_generating.set(false);
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Recent recipients
    // -----------------------------------------------------------------------

    pub fn add_recent_recipient(&self, recipient: Recipient) {
        self.recent_recipients.update(|r| {
            // Remove if already exists
            r.retain(|x| x.email != recipient.email);
            // Add new
            r.insert(
                0,
                RecentRecipient {
                    email: recipient.email.clone(),
                    name: recipient.name.unwrap_or_default(),
                    last_used: chrono::Utc::now().to_rfc3339(),
                    use_count: 1,
                },
            );
            // Keep max 50
            if r.len() > 50 {
                r.pop();
            }
        });
    }

    pub fn remove_recent_recipient(&self, email: &str) {
        self.recent_recipients
            .update(|r| r.retain(|x| x.email != email));
    }

    // -----------------------------------------------------------------------
    // Templates
    // -----------------------------------------------------------------------

    pub fn add_template(&self, template: EmailTemplate) {
        self.templates.update(|t| t.push(template));
    }

    pub fn update_template(&self, id: &str, updates: serde_json::Value) {
        self.templates.update(|templates| {
            if let Some(t) = templates.iter_mut().find(|x| x.id == id) {
                if let Some(name) = updates.get("name").and_then(|v| v.as_str()) {
                    t.name = name.to_string();
                }
                if let Some(subject) = updates.get("subject_template").and_then(|v| v.as_str()) {
                    t.subject_template = subject.to_string();
                }
                if let Some(body) = updates.get("body_template").and_then(|v| v.as_str()) {
                    t.body_template = body.to_string();
                }
                if let Some(active) = updates.get("is_active").and_then(|v| v.as_bool()) {
                    t.is_active = active;
                }
                t.updated_at = chrono::Utc::now().to_rfc3339();
            }
        });
    }

    pub fn delete_template(&self, id: &str) {
        self.templates.update(|t| t.retain(|x| x.id != id));
    }

    pub fn get_templates_by_purpose(&self, purpose: &str) -> Vec<EmailTemplate> {
        self.templates
            .get()
            .into_iter()
            .filter(|t| t.purpose == purpose)
            .collect()
    }
}

impl Default for EmailDraftingStore {
    fn default() -> Self {
        Self::new()
    }
}
