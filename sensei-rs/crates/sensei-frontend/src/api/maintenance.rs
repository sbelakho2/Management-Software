//! Maintenance management API endpoints.
//!
//! Work Requests, PM Schedules, Equipment.

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkRequestDto {
    pub id: String,
    pub tenant_id: String,
    pub request_number: String,
    pub title: String,
    pub description: Option<String>,
    pub priority: String,
    pub status: String,
    pub asset_id: Option<String>,
    pub assigned_to: Option<String>,
    pub requested_by: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateWorkRequestRequest {
    pub title: String,
    pub description: Option<String>,
    pub priority: String,
    pub asset_id: Option<String>,
    pub assigned_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PmScheduleDto {
    pub id: String,
    pub tenant_id: String,
    pub schedule_number: String,
    pub title: String,
    pub asset_id: String,
    pub frequency_days: i32,
    pub assigned_to: Option<String>,
    pub last_performed: Option<String>,
    pub next_due: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreatePmScheduleRequest {
    pub title: String,
    pub asset_id: String,
    pub frequency_days: i32,
    pub assigned_to: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquipmentDto {
    pub id: String,
    pub tenant_id: String,
    pub equipment_code: String,
    pub name: String,
    pub equipment_type: String,
    pub location: Option<String>,
    pub status: String,
    pub serial_number: Option<String>,
    pub installed_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterEquipmentRequest {
    pub name: String,
    pub equipment_type: String,
    pub location: Option<String>,
    pub serial_number: Option<String>,
}

pub struct MaintenanceApi;

impl MaintenanceApi {
    // ---- Work Requests ----
    pub async fn list_work_requests(client: &ApiClient) -> Result<Vec<WorkRequestDto>, ApiError> {
        client.get("/api/v1/maintenance/work-requests").await
    }

    pub async fn get_work_request(client: &ApiClient, id: &str) -> Result<WorkRequestDto, ApiError> {
        client.get(&format!("/api/v1/maintenance/work-requests/{}", id)).await
    }

    pub async fn create_work_request(client: &ApiClient, req: &CreateWorkRequestRequest) -> Result<WorkRequestDto, ApiError> {
        client.post("/api/v1/maintenance/work-requests", req).await
    }

    pub async fn update_work_request_status(client: &ApiClient, id: &str, status: &str) -> Result<WorkRequestDto, ApiError> {
        #[derive(Serialize)]
        struct Body<'a> { status: &'a str }
        client.put(&format!("/api/v1/maintenance/work-requests/{}/status", id), &Body { status }).await
    }

    // ---- PM Schedules ----
    pub async fn list_pm_schedules(client: &ApiClient) -> Result<Vec<PmScheduleDto>, ApiError> {
        client.get("/api/v1/maintenance/pm-schedules").await
    }

    pub async fn get_pm_schedule(client: &ApiClient, id: &str) -> Result<PmScheduleDto, ApiError> {
        client.get(&format!("/api/v1/maintenance/pm-schedules/{}", id)).await
    }

    pub async fn create_pm_schedule(client: &ApiClient, req: &CreatePmScheduleRequest) -> Result<PmScheduleDto, ApiError> {
        client.post("/api/v1/maintenance/pm-schedules", req).await
    }

    // ---- Equipment ----
    pub async fn list_equipment(client: &ApiClient) -> Result<Vec<EquipmentDto>, ApiError> {
        client.get("/api/v1/maintenance/equipment").await
    }

    pub async fn get_equipment(client: &ApiClient, id: &str) -> Result<EquipmentDto, ApiError> {
        client.get(&format!("/api/v1/maintenance/equipment/{}", id)).await
    }

    pub async fn register_equipment(client: &ApiClient, req: &RegisterEquipmentRequest) -> Result<EquipmentDto, ApiError> {
        client.post("/api/v1/maintenance/equipment", req).await
    }
}
