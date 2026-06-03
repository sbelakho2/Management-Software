//! Training reactive store.
//!
//! Mirrors the Zustand [`training.ts`](frontend/src/stores/training.ts) store.

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// A skill definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillDto {
    pub id: String,
    pub name: String,
    pub category: Option<String>,
    pub description: Option<String>,
    pub created_at: Option<String>,
}

/// A training course / program.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingDto {
    pub id: String,
    pub title: String,
    pub description: Option<String>,
    pub skill_id: Option<String>,
    pub duration_hours: Option<f64>,
    pub training_type: Option<String>,
    pub status: Option<String>,
    pub created_at: Option<String>,
}

/// A training record (enrollment / completion).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingRecordDto {
    pub id: String,
    pub user_id: String,
    pub training_id: String,
    pub status: String,
    pub score: Option<f64>,
    pub completed_at: Option<String>,
    pub notes: Option<String>,
    pub created_at: Option<String>,
}

/// A user's skill proficiency record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserSkillDto {
    pub id: String,
    pub user_id: String,
    pub skill_id: String,
    pub proficiency: String,
    pub certified: bool,
    pub certificate_number: Option<String>,
    pub issue_date: Option<String>,
    pub expiry_date: Option<String>,
    pub created_at: Option<String>,
}

/// Reactive store for training and skills data.
#[derive(Debug, Clone)]
pub struct TrainingStore {
    /// List of skills.
    pub skills: RwSignal<Vec<SkillDto>>,
    /// List of training courses.
    pub trainings: RwSignal<Vec<TrainingDto>>,
    /// Training records.
    pub records: RwSignal<Vec<TrainingRecordDto>>,
    /// User skill records.
    pub user_skills: RwSignal<Vec<UserSkillDto>>,
    /// Whether a fetch is in flight.
    pub is_loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl TrainingStore {
    pub fn new() -> Self {
        Self {
            skills: RwSignal::new(Vec::new()),
            trainings: RwSignal::new(Vec::new()),
            records: RwSignal::new(Vec::new()),
            user_skills: RwSignal::new(Vec::new()),
            is_loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch all skills.
    pub async fn fetch_skills(&self, client: &ApiClient) {
        self.is_loading.set(true);
        self.error.set(None);
        match client.get::<Vec<SkillDto>>("/api/v1/training/skills").await {
            Ok(data) => self.skills.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch all training courses.
    pub async fn fetch_trainings(&self, client: &ApiClient) {
        self.is_loading.set(true);
        self.error.set(None);
        match client.get::<Vec<TrainingDto>>("/api/v1/training/courses").await {
            Ok(data) => self.trainings.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch training records.
    pub async fn fetch_records(&self, client: &ApiClient) {
        self.is_loading.set(true);
        self.error.set(None);
        match client.get::<Vec<TrainingRecordDto>>("/api/v1/training/records").await {
            Ok(data) => self.records.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Fetch user skills for a given user.
    pub async fn fetch_user_skills(&self, client: &ApiClient, user_id: &str) {
        self.is_loading.set(true);
        self.error.set(None);
        match client
            .get::<Vec<UserSkillDto>>(&format!("/api/v1/training/user/{}/skills", user_id))
            .await
        {
            Ok(data) => self.user_skills.set(data),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.is_loading.set(false);
    }

    /// Enroll a user in a training course.
    pub async fn enroll_in_training(
        &self,
        client: &ApiClient,
        training_id: &str,
        user_id: &str,
        notes: Option<&str>,
    ) -> Result<TrainingRecordDto, ApiError> {
        let payload = serde_json::json!({
            "training_id": training_id,
            "user_id": user_id,
            "notes": notes,
        });
        let record: TrainingRecordDto =
            client.post("/api/v1/training/enroll", &payload).await?;
        self.records.update(|r| r.push(record.clone()));
        Ok(record)
    }

    /// Register a certification for a user (two-step: find/create user-skill + certify).
    pub async fn register_certification(
        &self,
        client: &ApiClient,
        user_id: &str,
        skill_id: &str,
        proficiency: &str,
        issue_date: Option<&str>,
        expiry_date: Option<&str>,
        certificate_number: Option<&str>,
        notes: Option<&str>,
    ) -> Result<UserSkillDto, ApiError> {
        let payload = serde_json::json!({
            "user_id": user_id,
            "skill_id": skill_id,
            "proficiency": proficiency,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "certificate_number": certificate_number,
            "notes": notes,
        });
        let user_skill: UserSkillDto =
            client.post("/api/v1/training/certify", &payload).await?;
        self.user_skills.update(|s| s.push(user_skill.clone()));
        Ok(user_skill)
    }
}

impl Default for TrainingStore {
    fn default() -> Self {
        Self::new()
    }
}
