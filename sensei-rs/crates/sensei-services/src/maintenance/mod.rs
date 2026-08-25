//! Maintenance domain services.
//!
//! Provides work request management, preventive maintenance (PM) scheduling,
//! and equipment tracking with in-memory storage for development and testing.
//!
//! # Key Concepts
//!
//! - **Work Requests** – ad‑hoc maintenance requests submitted by operators
//!   or supervisors when equipment issues are identified.
//! - **PM Schedules** – recurring maintenance tasks defined by frequency
//!   (in days) for each piece of equipment.
//! - **Equipment Records** – the master register of all machinery, tools,
//!   vehicles, and facility assets.

mod database;
pub use database::DatabaseMaintenanceService;

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sensei_core::domain::events::{DomainEvent, PMScheduleTriggeredEvent};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{TenantId, new_id, now};
use sensei_event_bus::bus::EventBus;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// DTOs
// ---------------------------------------------------------------------------

/// A maintenance work request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaintenanceWorkRequest {
    /// Unique identifier.
    pub id: Uuid,
    /// Tenant that owns this request.
    pub tenant_id: Uuid,
    /// Equipment that requires maintenance.
    pub equipment_id: Uuid,
    /// Short title of the request.
    pub title: String,
    /// Detailed description of the issue.
    pub description: String,
    /// Priority: "low", "medium", "high", "critical".
    pub priority: String,
    /// Status: "submitted", "approved", "in_progress", "completed", "cancelled".
    pub status: String,
    /// User who submitted the request.
    pub requested_by: Uuid,
    /// User assigned to perform the work.
    pub assigned_to: Option<Uuid>,
    /// Timestamp when the request was created.
    pub created_at: DateTime<Utc>,
    /// Timestamp when the work was completed.
    pub completed_at: Option<DateTime<Utc>>,
}

/// A preventive maintenance (PM) schedule.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PMSchedule {
    /// Unique identifier.
    pub id: Uuid,
    /// Tenant that owns this schedule.
    pub tenant_id: Uuid,
    /// Equipment subject to this PM.
    pub equipment_id: Uuid,
    /// Name of the PM task.
    pub task_name: String,
    /// How often the PM should be performed (in days).
    pub frequency_days: i32,
    /// Last time the PM was performed.
    pub last_performed: Option<DateTime<Utc>>,
    /// Next due date for the PM.
    pub next_due: DateTime<Utc>,
    /// Users/technicians assigned to this PM schedule.
    pub assigned_to: Vec<Uuid>,
    /// Whether this schedule is active.
    pub is_active: bool,
}

/// A registered piece of equipment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquipmentRecord {
    /// Unique identifier.
    pub id: Uuid,
    /// Tenant that owns this equipment.
    pub tenant_id: Uuid,
    /// Human-readable equipment code (e.g. "EQ-20260602-0001").
    pub equipment_code: String,
    /// Descriptive name of the equipment.
    pub name: String,
    /// Type: "machine", "tool", "vehicle", "facility".
    pub equipment_type: String,
    /// Physical location within the facility.
    pub location: String,
    /// Status: "operational", "under_maintenance", "decommissioned".
    pub status: String,
    /// Date the equipment was installed.
    pub install_date: DateTime<Utc>,
    /// Last maintenance date (set when entering `under_maintenance`).
    pub last_maintenance: Option<DateTime<Utc>>,
    /// When the most recent maintenance work was completed (set when
    /// transitioning back to `operational`).
    #[serde(default)]
    pub maintenance_completed_at: Option<DateTime<Utc>>,
    /// Overall Equipment Effectiveness percentage.
    pub oee_percentage: f64,
}

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Maintenance management service covering work requests, PM schedules,
/// and equipment records.
#[async_trait]
pub trait MaintenanceService: Send + Sync {
    // ── Work Requests ───────────────────────────────────────────────────

    /// Create a new maintenance work request.
    async fn create_work_request(
        &self,
        tenant_id: TenantId,
        request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest>;

    /// Get a work request by ID.
    async fn get_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
    ) -> Result<MaintenanceWorkRequest>;

    /// List work requests, optionally filtered by status and/or priority, with pagination.
    async fn list_work_requests(
        &self,
        tenant_id: TenantId,
        status: Option<&str>,
        priority: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MaintenanceWorkRequest>>;

    /// Update the status of a work request.
    async fn update_work_request_status(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<MaintenanceWorkRequest>;

    /// Assign a user to a work request.
    async fn assign_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        assigned_to: Uuid,
    ) -> Result<MaintenanceWorkRequest>;

    // ── PM Schedules ───────────────────────────────────────────────────

    /// Create a new PM schedule.
    async fn create_pm_schedule(
        &self,
        tenant_id: TenantId,
        schedule: PMSchedule,
    ) -> Result<PMSchedule>;

    /// Get a PM schedule by ID.
    async fn get_pm_schedule(
        &self,
        tenant_id: TenantId,
        id: Uuid,
    ) -> Result<PMSchedule>;

    /// List PM schedules, optionally filtered by equipment, with pagination.
    async fn list_pm_schedules(
        &self,
        tenant_id: TenantId,
        equipment_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PMSchedule>>;

    /// Mark a PM task as completed, updating its next_due date.
    async fn complete_pm_task(
        &self,
        tenant_id: TenantId,
        schedule_id: Uuid,
    ) -> Result<PMSchedule>;

    /// Get all PM schedules that are past their next_due date.
    async fn get_overdue_pm_tasks(
        &self,
        tenant_id: TenantId,
    ) -> Result<Vec<PMSchedule>>;

    // ── Equipment ──────────────────────────────────────────────────────

    /// Register a new piece of equipment.
    async fn register_equipment(
        &self,
        tenant_id: TenantId,
        equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord>;

    /// Get an equipment record by ID.
    async fn get_equipment(
        &self,
        tenant_id: TenantId,
        id: Uuid,
    ) -> Result<EquipmentRecord>;

    /// List equipment, optionally filtered by type and/or status, with pagination.
    async fn list_equipment(
        &self,
        tenant_id: TenantId,
        equipment_type: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EquipmentRecord>>;

    /// Update the status of an equipment record.
    async fn update_equipment_status(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<EquipmentRecord>;
    /// Update a work request.
    async fn update_work_request(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest>;
    /// Delete a work request.
    async fn delete_work_request(&self, tenant_id: TenantId, id: Uuid) -> Result<()>;
    /// Update a PM schedule.
    async fn update_pm_schedule(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        schedule: PMSchedule,
    ) -> Result<PMSchedule>;
    /// Delete a PM schedule.
    async fn delete_pm_schedule(&self, tenant_id: TenantId, id: Uuid) -> Result<()>;
    /// Update an equipment record.
    async fn update_equipment(
        &self,
        tenant_id: TenantId,
        id: Uuid,
        equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord>;
    /// Delete an equipment record.
    async fn delete_equipment(&self, tenant_id: TenantId, id: Uuid) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of the [`MaintenanceService`] trait.
///
/// Stores work requests, PM schedules, and equipment records in
/// [`HashMap`]s protected by [`RwLock`]s. Generates sequential equipment
/// codes and automatically computes next_due dates for PM schedules.
pub struct InMemoryMaintenanceService {
    work_requests: RwLock<HashMap<Uuid, MaintenanceWorkRequest>>,
    pm_schedules: RwLock<HashMap<Uuid, PMSchedule>>,
    equipment: RwLock<HashMap<Uuid, EquipmentRecord>>,
    equipment_counter: RwLock<u64>,
    wr_counter: RwLock<u64>,
    event_bus: Option<Arc<dyn EventBus>>,
}

impl InMemoryMaintenanceService {
    /// Create a new empty [`InMemoryMaintenanceService`].
    pub fn new(event_bus: Option<Arc<dyn EventBus>>) -> Self {
        Self {
            work_requests: RwLock::new(HashMap::new()),
            pm_schedules: RwLock::new(HashMap::new()),
            equipment: RwLock::new(HashMap::new()),
            equipment_counter: RwLock::new(0),
            wr_counter: RwLock::new(0),
            event_bus,
        }
    }

    async fn publish_event(&self, event: impl DomainEvent + 'static) {
        if let Some(ref bus) = self.event_bus {
            if let Err(e) = bus.publish(&event).await {
                tracing::warn!("Failed to publish event {}: {}", event.event_type(), e);
            }
        }
    }

    fn generate_equipment_code(counter: u64) -> String {
        format!("EQ-{}-{:04}", Utc::now().format("%Y%m%d"), counter)
    }

    fn compute_next_due(last_performed: Option<DateTime<Utc>>, frequency_days: i32) -> DateTime<Utc> {
        let base = last_performed.unwrap_or_else(Utc::now);
        base + chrono::Duration::days(frequency_days as i64)
    }
}

impl Default for InMemoryMaintenanceService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl MaintenanceService for InMemoryMaintenanceService {
    // ── Work Requests ───────────────────────────────────────────────────

    async fn create_work_request(
        &self,
        tenant_id: TenantId,
        mut request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest> {
        let mut counter = self.wr_counter.write().await;
        *counter += 1;
        drop(counter);

        request.id = new_id();
        request.tenant_id = tenant_id;
        request.created_at = now();
        request.completed_at = None;
        if request.status.is_empty() {
            request.status = "submitted".to_string();
        }
        if request.priority.is_empty() {
            request.priority = "medium".to_string();
        }

        self.work_requests
            .write()
            .await
            .insert(request.id, request.clone());

        Ok(request)
    }

    async fn get_work_request(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
    ) -> Result<MaintenanceWorkRequest> {
        self.work_requests
            .read()
            .await
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))
    }

    async fn list_work_requests(
        &self,
        _tenant_id: TenantId,
        status: Option<&str>,
        priority: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MaintenanceWorkRequest>> {
        let requests = self.work_requests.read().await;
        let items: Vec<_> = requests
            .values()
            .filter(|wr| status.is_none_or(|s| wr.status == s))
            .filter(|wr| priority.is_none_or(|p| wr.priority == p))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_work_request_status(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<MaintenanceWorkRequest> {
        let mut requests = self.work_requests.write().await;
        let wr = requests
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        wr.status = status.to_string();
        if status == "completed" {
            wr.completed_at = Some(now());
        }

        Ok(wr.clone())
    }

    async fn assign_work_request(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        assigned_to: Uuid,
    ) -> Result<MaintenanceWorkRequest> {
        let mut requests = self.work_requests.write().await;
        let wr = requests
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Work request {id} not found")))?;

        wr.assigned_to = Some(assigned_to);
        if wr.status == "submitted" {
            wr.status = "approved".to_string();
        }

        Ok(wr.clone())
    }

    // ── PM Schedules ───────────────────────────────────────────────────

    async fn create_pm_schedule(
        &self,
        tenant_id: TenantId,
        mut schedule: PMSchedule,
    ) -> Result<PMSchedule> {
        schedule.id = new_id();
        schedule.tenant_id = tenant_id;
        schedule.next_due =
            Self::compute_next_due(schedule.last_performed, schedule.frequency_days);

        self.pm_schedules
            .write()
            .await
            .insert(schedule.id, schedule.clone());

        Ok(schedule)
    }

    async fn get_pm_schedule(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
    ) -> Result<PMSchedule> {
        self.pm_schedules
            .read()
            .await
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {id} not found")))
    }

    async fn list_pm_schedules(
        &self,
        _tenant_id: TenantId,
        equipment_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PMSchedule>> {
        let schedules = self.pm_schedules.read().await;
        let items: Vec<_> = schedules
            .values()
            .filter(|s| equipment_id.is_none_or(|eid| s.equipment_id == eid))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn complete_pm_task(
        &self,
        tenant_id: TenantId,
        schedule_id: Uuid,
    ) -> Result<PMSchedule> {
        let mut schedules = self.pm_schedules.write().await;
        let schedule = schedules
            .get_mut(&schedule_id)
            .ok_or_else(|| SenseiError::NotFound(format!("PM schedule {schedule_id} not found")))?;

        let now_ts = now();
        schedule.last_performed = Some(now_ts);
        schedule.next_due = Self::compute_next_due(Some(now_ts), schedule.frequency_days);

        let result = schedule.clone();
        drop(schedules);
        self.publish_event(PMScheduleTriggeredEvent::new(
            tenant_id,
            result.id,
            result.equipment_id,
            result.next_due.to_string(),
        ))
        .await;
        Ok(result)
    }

    async fn get_overdue_pm_tasks(
        &self,
        _tenant_id: TenantId,
    ) -> Result<Vec<PMSchedule>> {
        let schedules = self.pm_schedules.read().await;
        let now_ts = now();
        Ok(schedules
            .values()
            .filter(|s| s.is_active && s.next_due < now_ts)
            .cloned()
            .collect())
    }

    // ── Equipment ──────────────────────────────────────────────────────

    async fn register_equipment(
        &self,
        tenant_id: TenantId,
        mut equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord> {
        let mut counter = self.equipment_counter.write().await;
        *counter += 1;
        equipment.id = new_id();
        equipment.tenant_id = tenant_id;
        equipment.equipment_code = Self::generate_equipment_code(*counter);
        equipment.install_date = now();
        equipment.last_maintenance = None;
        drop(counter);

        self.equipment
            .write()
            .await
            .insert(equipment.id, equipment.clone());

        Ok(equipment)
    }

    async fn get_equipment(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
    ) -> Result<EquipmentRecord> {
        self.equipment
            .read()
            .await
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))
    }

    async fn list_equipment(
        &self,
        _tenant_id: TenantId,
        equipment_type: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EquipmentRecord>> {
        let eqs = self.equipment.read().await;
        let items: Vec<_> = eqs
            .values()
            .filter(|e| equipment_type.is_none_or(|t| e.equipment_type == t))
            .filter(|e| status.is_none_or(|s| e.status == s))
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_equipment_status(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        status: &str,
    ) -> Result<EquipmentRecord> {
        let mut eqs = self.equipment.write().await;
        let eq = eqs
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;

        eq.status = status.to_string();
        if status == "under_maintenance" {
            eq.last_maintenance = Some(now());
        } else if status == "operational" {
            // Coming back from maintenance records when the work completed.
            eq.maintenance_completed_at = Some(now());
        }

        Ok(eq.clone())
    }
    // ── New: Update / Delete ─────────────────────────────────────────────

    async fn update_work_request(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        request: MaintenanceWorkRequest,
    ) -> Result<MaintenanceWorkRequest> {
        let mut store = self.work_requests.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("WorkRequest {id} not found")))?;
        existing.title = request.title;
        existing.description = request.description;
        existing.priority = request.priority;
        existing.status = request.status;
        existing.assigned_to = request.assigned_to;
        // Preserve: id, tenant_id, equipment_id, requested_by, created_at, completed_at
        Ok(existing.clone())
    }

    async fn delete_work_request(&self, _tenant_id: TenantId, id: Uuid) -> Result<()> {
        let mut store = self.work_requests.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("WorkRequest {id} not found")))?;
        Ok(())
    }

    async fn update_pm_schedule(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        schedule: PMSchedule,
    ) -> Result<PMSchedule> {
        let mut store = self.pm_schedules.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PMSchedule {id} not found")))?;
        existing.task_name = schedule.task_name;
        existing.frequency_days = schedule.frequency_days;
        existing.assigned_to = schedule.assigned_to;
        existing.is_active = schedule.is_active;
        // Preserve: id, tenant_id, equipment_id, last_performed, next_due
        Ok(existing.clone())
    }

    async fn delete_pm_schedule(&self, _tenant_id: TenantId, id: Uuid) -> Result<()> {
        let mut store = self.pm_schedules.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("PMSchedule {id} not found")))?;
        Ok(())
    }

    async fn update_equipment(
        &self,
        _tenant_id: TenantId,
        id: Uuid,
        equipment: EquipmentRecord,
    ) -> Result<EquipmentRecord> {
        let mut store = self.equipment.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;
        existing.name = equipment.name;
        existing.equipment_type = equipment.equipment_type;
        existing.location = equipment.location;
        existing.status = equipment.status;
        // Preserve: id, tenant_id, equipment_code, install_date, last_maintenance, oee_percentage
        Ok(existing.clone())
    }

    async fn delete_equipment(&self, _tenant_id: TenantId, id: Uuid) -> Result<()> {
        let mut store = self.equipment.write().await;
        store
            .remove(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Equipment {id} not found")))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_and_get_work_request() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        let req = MaintenanceWorkRequest {
            id: Uuid::nil(),
            tenant_id,
            equipment_id: Uuid::new_v4(),
            title: "Replace hydraulic hose".to_string(),
            description: "Hydraulic hose on press #3 is leaking.".to_string(),
            priority: "high".to_string(),
            status: "submitted".to_string(),
            requested_by: Uuid::new_v4(),
            assigned_to: None,
            created_at: Utc::now(),
            completed_at: None,
        };

        let created = service.create_work_request(tenant_id, req).await.unwrap();
        assert_ne!(created.id, Uuid::nil(), "should assign a real UUID");

        let fetched = service.get_work_request(tenant_id, created.id).await.unwrap();
        assert_eq!(fetched.title, "Replace hydraulic hose");
    }

    #[tokio::test]
    async fn test_list_work_requests_with_filter() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        for i in 0..3 {
            let req = MaintenanceWorkRequest {
                id: Uuid::nil(),
                tenant_id,
                equipment_id: Uuid::new_v4(),
                title: format!("Request {}", i),
                description: "Test".to_string(),
                priority: if i == 0 { "critical".to_string() } else { "low".to_string() },
                status: "submitted".to_string(),
                requested_by: Uuid::new_v4(),
                assigned_to: None,
                created_at: Utc::now(),
                completed_at: None,
            };
            service.create_work_request(tenant_id, req).await.unwrap();
        }

        // Filter by priority
        let critical = service
            .list_work_requests(tenant_id, None, Some("critical"), None, None)
            .await
            .unwrap();
        assert_eq!(critical.data.len(), 1);

        let all = service
            .list_work_requests(tenant_id, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(all.data.len(), 3);
    }

    #[tokio::test]
    async fn test_work_request_status_update() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        let req = MaintenanceWorkRequest {
            id: Uuid::nil(),
            tenant_id,
            equipment_id: Uuid::new_v4(),
            title: "Test".to_string(),
            description: "Test".to_string(),
            priority: "low".to_string(),
            status: "submitted".to_string(),
            requested_by: Uuid::new_v4(),
            assigned_to: None,
            created_at: Utc::now(),
            completed_at: None,
        };

        let created = service.create_work_request(tenant_id, req).await.unwrap();
        let updated = service
            .update_work_request_status(tenant_id, created.id, "completed")
            .await
            .unwrap();
        assert_eq!(updated.status, "completed");
        assert!(updated.completed_at.is_some());
    }

    #[tokio::test]
    async fn test_assign_work_request() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();
        let assignee = Uuid::new_v4();

        let req = MaintenanceWorkRequest {
            id: Uuid::nil(),
            tenant_id,
            equipment_id: Uuid::new_v4(),
            title: "Test".to_string(),
            description: "Test".to_string(),
            priority: "medium".to_string(),
            status: "submitted".to_string(),
            requested_by: Uuid::new_v4(),
            assigned_to: None,
            created_at: Utc::now(),
            completed_at: None,
        };

        let created = service.create_work_request(tenant_id, req).await.unwrap();
        let assigned = service
            .assign_work_request(tenant_id, created.id, assignee)
            .await
            .unwrap();
        assert_eq!(assigned.assigned_to, Some(assignee));
        assert_eq!(assigned.status, "approved");
    }

    #[tokio::test]
    async fn test_pm_schedule_lifecycle() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        let schedule = PMSchedule {
            id: Uuid::nil(),
            tenant_id,
            equipment_id: Uuid::new_v4(),
            task_name: "Lubrication".to_string(),
            frequency_days: 30,
            last_performed: None,
            next_due: Utc::now(),
            assigned_to: vec![],
            is_active: true,
        };

        let created = service.create_pm_schedule(tenant_id, schedule).await.unwrap();
        assert!(
            created.next_due > Utc::now() - chrono::Duration::hours(1),
            "next_due should be computed"
        );

        // Complete the task
        let completed = service
            .complete_pm_task(tenant_id, created.id)
            .await
            .unwrap();
        assert!(completed.last_performed.is_some());
        assert!(
            completed.next_due > completed.last_performed.unwrap(),
            "next_due should be after last_performed"
        );
    }

    #[tokio::test]
    async fn test_get_overdue_pm_tasks() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        // Create an overdue schedule by setting last_performed far in the past
        let far_past = Utc::now() - chrono::Duration::days(100);
        let schedule = PMSchedule {
            id: Uuid::nil(),
            tenant_id,
            equipment_id: Uuid::new_v4(),
            task_name: "Overdue task".to_string(),
            frequency_days: 7,
            last_performed: Some(far_past),
            next_due: far_past + chrono::Duration::days(7),
            assigned_to: vec![],
            is_active: true,
        };

        let created = service.create_pm_schedule(tenant_id, schedule).await.unwrap();
        assert!(
            created.next_due < Utc::now(),
            "should be overdue"
        );

        let overdue = service.get_overdue_pm_tasks(tenant_id).await.unwrap();
        assert!(!overdue.is_empty(), "should find overdue tasks");
    }

    #[tokio::test]
    async fn test_equipment_crud() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        let eq = EquipmentRecord {
            id: Uuid::nil(),
            tenant_id,
            equipment_code: String::new(),
            name: "CNC Milling Machine #7".to_string(),
            equipment_type: "machine".to_string(),
            location: "Building A, Bay 3".to_string(),
            status: "operational".to_string(),
            install_date: Utc::now(),
            last_maintenance: None,
            maintenance_completed_at: None,
            oee_percentage: 85.3,
        };

        let registered = service.register_equipment(tenant_id, eq).await.unwrap();
        assert!(
            !registered.equipment_code.is_empty(),
            "should generate equipment code"
        );
        assert!(registered.equipment_code.starts_with("EQ-"));

        // Update status
        let updated = service
            .update_equipment_status(tenant_id, registered.id, "under_maintenance")
            .await
            .unwrap();
        assert_eq!(updated.status, "under_maintenance");
        assert!(updated.last_maintenance.is_some());

        // Returning to operational records when maintenance completed.
        let operational = service
            .update_equipment_status(tenant_id, registered.id, "operational")
            .await
            .unwrap();
        assert!(operational.maintenance_completed_at.is_some());

        // List with filter
        let machines = service
            .list_equipment(tenant_id, Some("machine"), None, None, None)
            .await
            .unwrap();
        assert_eq!(machines.data.len(), 1);

        let under_maint = service
            .list_equipment(tenant_id, None, Some("under_maintenance"), None, None)
            .await
            .unwrap();
        assert_eq!(under_maint.data.len(), 1);
    }

    #[tokio::test]
    async fn test_equipment_not_found() {
        let service = InMemoryMaintenanceService::new(None);
        let tenant_id = Uuid::new_v4();

        let result = service.get_equipment(tenant_id, Uuid::new_v4()).await;
        assert!(result.is_err(), "should return error for non-existent equipment");
    }
}
