//! TPS work surfaces API (items 64/67): Leader Standard Work, Standard
//! Work, Tier Meetings, Topology, Work Centers, Kanban, Training Matrix,
//! CTQ, Obeya and the Agent tool surface — every DTO mirrors the backend
//! contract exactly (item 3: one source of truth, never hand-redefined).

use crate::api::client::{ApiClient, ApiError};
use serde::{Deserialize, Serialize};

// ── Leader Standard Work ────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LswStandardDto {
    pub id: String,
    pub tenant_id: String,
    pub title: String,
    pub area: String,
    pub layer: u8,
    pub revision: i32,
    pub frequency: String,
    pub checklist_items: Vec<LswChecklistItemDto>,
    pub is_active: bool,
    pub created_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LswChecklistItemDto {
    pub id: String,
    pub description: String,
    pub expected_value: Option<String>,
    pub is_critical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LswOccurrenceDto {
    pub id: String,
    pub standard_id: String,
    pub tenant_id: String,
    pub checklist_revision: i32,
    pub due_at: String,
    pub assigned_leader: String,
    pub area: String,
    pub layer: u8,
    pub status: String,
    pub scheduled_at: String,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
}

pub async fn list_lsw_standards(client: &ApiClient) -> Result<Vec<LswStandardDto>, ApiError> {
    client.get("/api/v1/lsw/standards").await
}

pub async fn create_lsw_standard(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<LswStandardDto, ApiError> {
    client.post("/api/v1/lsw/standards", &req).await
}

pub async fn schedule_lsw_occurrence(
    client: &ApiClient,
    standard_id: &str,
    req: serde_json::Value,
) -> Result<LswOccurrenceDto, ApiError> {
    client
        .post(
            &format!("/api/v1/lsw/standards/{standard_id}/occurrences"),
            &req,
        )
        .await
}

// ── Standard Work ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StandardWorkDto {
    pub id: String,
    pub tenant_id: String,
    pub title: String,
    pub document_number: String,
    pub area: String,
    pub process: String,
    pub current_version: i32,
    pub status: String,
    pub steps: Vec<serde_json::Value>,
    pub cycle_time_seconds: Option<i32>,
    pub takt_time_seconds: Option<i32>,
    pub effective_from: Option<String>,
    pub effective_to: Option<String>,
    pub supersedes: Option<String>,
    pub version: u64,
    pub updated_at: String,
}

pub async fn list_standard_work(client: &ApiClient) -> Result<Vec<StandardWorkDto>, ApiError> {
    client.get("/api/v1/standard-work").await
}

pub async fn create_standard_work(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<StandardWorkDto, ApiError> {
    client.post("/api/v1/standard-work", &req).await
}

pub async fn submit_standard_work(
    client: &ApiClient,
    id: &str,
) -> Result<StandardWorkDto, ApiError> {
    client
        .post(
            &format!("/api/v1/standard-work/{id}/submit"),
            &serde_json::json!({}),
        )
        .await
}

pub async fn approve_standard_work(
    client: &ApiClient,
    id: &str,
    effective_from: Option<String>,
) -> Result<StandardWorkDto, ApiError> {
    client
        .post(
            &format!("/api/v1/standard-work/{id}/approve"),
            &serde_json::json!({ "notes": null, "effective_from": effective_from }),
        )
        .await
}

pub async fn reject_standard_work(
    client: &ApiClient,
    id: &str,
) -> Result<StandardWorkDto, ApiError> {
    client
        .post(
            &format!("/api/v1/standard-work/{id}/reject"),
            &serde_json::json!({}),
        )
        .await
}

pub async fn supersede_standard_work(
    client: &ApiClient,
    id: &str,
    replacement_id: Option<String>,
) -> Result<StandardWorkDto, ApiError> {
    client
        .post(
            &format!("/api/v1/standard-work/{id}/supersede"),
            &serde_json::json!({ "replacement_id": replacement_id }),
        )
        .await
}

// ── Tier Meetings ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TierMeetingDto {
    pub id: String,
    pub tenant_id: String,
    pub tier_level: u8,
    pub title: String,
    pub site_id: Option<String>,
    pub value_stream_id: Option<String>,
    pub work_center_id: Option<String>,
    pub shift_id: Option<String>,
    pub leader_id: Option<String>,
    pub attendee_ids: Vec<String>,
    pub status: String,
    pub area: Option<String>,
    pub scheduled_at: String,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub escalation_ids: Vec<String>,
}

pub async fn list_tier_meetings(client: &ApiClient) -> Result<Vec<TierMeetingDto>, ApiError> {
    client.get("/api/v1/tier-meetings").await
}

pub async fn schedule_tier_meeting(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<TierMeetingDto, ApiError> {
    client.post("/api/v1/tier-meetings", &req).await
}

pub async fn start_tier_meeting(client: &ApiClient, id: &str) -> Result<TierMeetingDto, ApiError> {
    client
        .post(
            &format!("/api/v1/tier-meetings/{id}/start"),
            &serde_json::json!({}),
        )
        .await
}

pub async fn complete_tier_meeting(
    client: &ApiClient,
    id: &str,
) -> Result<TierMeetingDto, ApiError> {
    client
        .post(
            &format!("/api/v1/tier-meetings/{id}/complete"),
            &serde_json::json!({}),
        )
        .await
}

pub async fn escalate_tier_issue(
    client: &ApiClient,
    id: &str,
    req: serde_json::Value,
) -> Result<TierMeetingDto, ApiError> {
    client
        .post(&format!("/api/v1/tier-meetings/{id}/escalate"), &req)
        .await
}

// ── Topology ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SiteDto {
    pub id: String,
    pub site_code: String,
    pub name: String,
    pub address: Option<String>,
    pub timezone: String,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValueStreamDto {
    pub id: String,
    pub site_id: String,
    pub name: String,
    pub description: Option<String>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductFamilyDto {
    pub id: String,
    pub site_id: Option<String>,
    pub name: String,
    pub description: Option<String>,
    pub is_active: bool,
}

pub async fn list_sites(client: &ApiClient) -> Result<Vec<SiteDto>, ApiError> {
    client.get("/api/v1/topology/sites").await
}

pub async fn create_site(client: &ApiClient, req: serde_json::Value) -> Result<SiteDto, ApiError> {
    client.post("/api/v1/topology/sites", &req).await
}

pub async fn list_value_streams(client: &ApiClient) -> Result<Vec<ValueStreamDto>, ApiError> {
    client.get("/api/v1/topology/value-streams").await
}

pub async fn create_value_stream(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<ValueStreamDto, ApiError> {
    client.post("/api/v1/topology/value-streams", &req).await
}

pub async fn list_product_families(client: &ApiClient) -> Result<Vec<ProductFamilyDto>, ApiError> {
    client.get("/api/v1/topology/product-families").await
}

pub async fn create_product_family(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<ProductFamilyDto, ApiError> {
    client.post("/api/v1/topology/product-families", &req).await
}

// ── Work Centers ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkCenterDto {
    pub id: String,
    pub work_center_number: String,
    pub name: String,
    pub description: String,
    pub work_center_type: String,
    pub department: Option<String>,
    pub location: Option<String>,
    pub is_active: bool,
    pub capacity_per_shift: i32,
    pub shifts_per_day: i32,
    pub efficiency: f64,
    pub available_hours_per_day: f64,
}

pub async fn list_work_centers(client: &ApiClient) -> Result<Vec<WorkCenterDto>, ApiError> {
    client.get("/api/v1/work-centers").await
}

pub async fn create_work_center(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<WorkCenterDto, ApiError> {
    client.post("/api/v1/work-centers", &req).await
}

// ── Kanban ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanBoardDto {
    pub id: String,
    pub name: String,
    pub description: String,
    pub columns: Vec<KanbanColumnDto>,
    pub created_by: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanColumnDto {
    pub id: String,
    pub name: String,
    pub position: i32,
    pub wip_limit: Option<i32>,
    pub cards: Vec<KanbanCardDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KanbanCardDto {
    pub id: String,
    pub title: String,
    pub description: String,
    pub priority: String,
    pub status: String,
    pub column_id: String,
    pub position: i32,
    pub assigned_to: Option<String>,
}

pub async fn list_kanban_boards(client: &ApiClient) -> Result<Vec<KanbanBoardDto>, ApiError> {
    client.get("/api/v1/kanban/boards").await
}

pub async fn create_kanban_board(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<KanbanBoardDto, ApiError> {
    client.post("/api/v1/kanban/boards", &req).await
}

pub async fn move_kanban_card(
    client: &ApiClient,
    card_id: &str,
    req: serde_json::Value,
) -> Result<KanbanCardDto, ApiError> {
    client
        .put(&format!("/api/v1/kanban/cards/{card_id}/move"), &req)
        .await
}

// ── Training Matrix ─────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingMatrixDto {
    pub id: String,
    pub employee_id: String,
    pub employee_name: String,
    pub skill_name: String,
    pub skill_category: String,
    pub proficiency_level: String,
    pub certification_id: Option<String>,
    pub last_assessed_at: Option<String>,
    pub valid_until: Option<String>,
    pub notes: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillGapDto {
    pub skill_name: String,
    pub skill_category: String,
    pub required_proficiency: String,
    pub available_count: usize,
    pub required_count: usize,
    pub gap: usize,
}

pub async fn list_training_matrix(client: &ApiClient) -> Result<Vec<TrainingMatrixDto>, ApiError> {
    client.get("/api/v1/training-matrix").await
}

pub async fn create_training_entry(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<TrainingMatrixDto, ApiError> {
    client.post("/api/v1/training-matrix", &req).await
}

pub async fn list_skill_gaps(client: &ApiClient) -> Result<Vec<SkillGapDto>, ApiError> {
    client.get("/api/v1/training-matrix/skill-gaps").await
}

// ── CTQ ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CtqDto {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: String,
    pub specification_limit_lower: Option<f64>,
    pub specification_limit_upper: Option<f64>,
    pub target_value: Option<f64>,
    pub unit: Option<String>,
    pub measurement_method: String,
    pub is_active: bool,
}

pub async fn list_ctq_characteristics(client: &ApiClient) -> Result<Vec<CtqDto>, ApiError> {
    client.get("/api/v1/ctq/characteristics").await
}

pub async fn create_ctq(client: &ApiClient, req: serde_json::Value) -> Result<CtqDto, ApiError> {
    client.post("/api/v1/ctq/characteristics", &req).await
}

// ── Obeya ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObeyaBoardDto {
    pub id: String,
    pub name: String,
    pub description: String,
    pub board_type: String,
    pub department: Option<String>,
    pub is_active: bool,
    pub items: Vec<ObeyaItemDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObeyaItemDto {
    pub id: String,
    pub title: String,
    pub description: String,
    pub category: String,
    pub priority: String,
    pub status: String,
    pub column: String,
    pub position: i32,
    pub assigned_to: Option<String>,
}

pub async fn list_obeya_boards(client: &ApiClient) -> Result<Vec<ObeyaBoardDto>, ApiError> {
    client.get("/api/v1/obeya/boards").await
}

pub async fn create_obeya_board(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<ObeyaBoardDto, ApiError> {
    client.post("/api/v1/obeya/boards", &req).await
}

// ── Agent tools ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentToolDto {
    pub name: String,
    pub description: String,
    pub risk: String,
    pub max_rows: i64,
}

pub async fn list_agent_tools(client: &ApiClient) -> Result<Vec<AgentToolDto>, ApiError> {
    client.get("/api/v1/agent/tools").await
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentExecuteResponse {
    pub tool_name: String,
    pub result: serde_json::Value,
    pub evidence: Vec<serde_json::Value>,
    pub verification: Option<serde_json::Value>,
}

pub async fn execute_agent_tool(
    client: &ApiClient,
    tool_name: &str,
    args: serde_json::Value,
) -> Result<AgentExecuteResponse, ApiError> {
    client
        .post(
            "/api/v1/agent/execute",
            &serde_json::json!({ "tool_name": tool_name, "args": args }),
        )
        .await
}

// ── Station (item 31) + interval board (item 32) ────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CurrentJobDto {
    pub work_order_id: String,
    pub wo_number: String,
    pub product_name: String,
    pub required_qty: i64,
    pub completed_qty: i64,
    pub remaining_qty: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PitchNowDto {
    pub target: i64,
    pub actual: i64,
    pub gap: i64,
    pub interval_start: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepNowDto {
    pub position: usize,
    pub total_steps: usize,
    pub description: String,
    pub expected_seconds: Option<i64>,
    pub is_critical: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StationSnapshotDto {
    pub current_job: Option<CurrentJobDto>,
    pub pitch: Option<PitchNowDto>,
    pub current_step: Option<StepNowDto>,
    pub quality_check: Option<String>,
    pub work_center_name: String,
    pub help_categories: Vec<String>,
    pub generated_at: String,
}

pub async fn get_station_snapshot(
    client: &ApiClient,
    work_center_id: Option<&str>,
) -> Result<StationSnapshotDto, ApiError> {
    match work_center_id {
        Some(wc) => {
            client
                .get(&format!("/api/v1/station/snapshot?work_center_id={wc}"))
                .await
        }
        None => client.get("/api/v1/station/snapshot").await,
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntervalAbnormalityDto {
    pub andon_number: String,
    pub issue_type: String,
    pub severity: String,
    pub created_at: String,
    pub response_seconds: Option<i64>,
    pub resolved: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntervalRowDto {
    pub interval_start: String,
    pub plan: i64,
    pub actual: i64,
    pub gap: i64,
    pub abnormalities: Vec<IntervalAbnormalityDto>,
}

pub async fn get_interval_board(
    client: &ApiClient,
    work_center_id: Option<&str>,
) -> Result<Vec<IntervalRowDto>, ApiError> {
    match work_center_id {
        Some(wc) => {
            client
                .get(&format!(
                    "/api/v1/station/interval-board?work_center_id={wc}"
                ))
                .await
        }
        None => client.get("/api/v1/station/interval-board").await,
    }
}

// ── Learning metrics (item 43) ──────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningMetricDto {
    pub key: String,
    pub label: String,
    pub value: f64,
    pub unit: String,
    pub better: String,
    pub target: Option<f64>,
    pub gap: Option<f64>,
    pub guidance: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LearningSnapshotDto {
    pub window_days: i64,
    pub metrics: Vec<LearningMetricDto>,
    pub learning_index: f64,
    pub generated_at: String,
}

pub async fn get_learning_metrics(client: &ApiClient) -> Result<LearningSnapshotDto, ApiError> {
    client.get("/api/v1/tps/learning-metrics").await
}

// ── Flow economics (items 36/38) ────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourcingFlowCostDto {
    pub option_label: String,
    pub unit_price: String,
    pub moq: String,
    pub lead_time_days: i64,
    pub on_time_delivery: String,
    pub inventory_days: String,
    pub trapped_cash: String,
    pub shortage_risk: String,
    pub guidance: String,
}

pub async fn sourcing_flow_cost(
    client: &ApiClient,
    req: serde_json::Value,
) -> Result<SourcingFlowCostDto, ApiError> {
    client
        .post("/api/v1/tps/flow-economics/sourcing", &req)
        .await
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WasteLineDto {
    pub key: String,
    pub label: String,
    pub value: String,
    pub guidance: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FinanceWasteDto {
    pub lines: Vec<WasteLineDto>,
    pub total_waste_annual: String,
}

pub async fn get_finance_waste(client: &ApiClient) -> Result<FinanceWasteDto, ApiError> {
    client.get("/api/v1/tps/flow-economics/waste").await
}

// ── Legacy-system integration (interoperability) ────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrationStatusDto {
    pub legacy_systems: Vec<String>,
    pub supported_entities: Vec<String>,
    pub entity_map_count: i64,
}

pub async fn get_integration_status(client: &ApiClient) -> Result<IntegrationStatusDto, ApiError> {
    client.get("/api/v1/integration/status").await
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImportResultDto {
    pub sensei_entity: String,
    pub sensei_id: String,
    pub updated: bool,
    pub legacy_system: String,
    pub legacy_id: String,
}

pub async fn import_legacy_record(
    client: &ApiClient,
    system: &str,
    entity: &str,
    legacy_id: &str,
    payload: serde_json::Value,
) -> Result<ImportResultDto, ApiError> {
    client
        .post(
            &format!("/api/v1/integration/{system}/{entity}"),
            &serde_json::json!({ "legacy_id": legacy_id, "payload": payload }),
        )
        .await
}
