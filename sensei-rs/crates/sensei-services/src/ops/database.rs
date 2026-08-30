//! PostgreSQL-backed operations service using sqlx.
//!
//! Provides Andon, project, A3 report, and risk management
//! backed by PostgreSQL tables. Implements [`OperationsService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde_json;
use sqlx::PgPool;
use uuid::Uuid;

use super::{Andon, OperationsService, Project, Risk, A3};

/// PostgreSQL-backed implementation of [`OperationsService`].
/// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id).
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> std::result::Result<(), SenseiError> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Run `f` inside a transaction with the RLS tenant context set — every
/// andon path (reads included) must establish the context: the policy is
/// FAIL-CLOSED (missing context = no rows).
async fn with_tenant_tx<T, F>(pool: &PgPool, tenant_id: Uuid, f: F) -> Result<T>
where
    F: for<'t> FnOnce(
        &'t mut sqlx::Transaction<'_, sqlx::Postgres>,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = std::result::Result<T, SenseiError>> + Send + 't>,
    >,
{
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin tenant tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let result = f(&mut tx).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to commit tenant tx: {e}")))?;
    Ok(result)
}

pub struct DatabaseOperationsService {
    pool: PgPool,
}

impl DatabaseOperationsService {
    /// Create a new [`DatabaseOperationsService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

// ---------------------------------------------------------------------------
// Row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct AndonRow {
    id: Uuid,
    tenant_id: Uuid,
    andon_number: String,
    work_center_id: Uuid,
    issue_type: String,
    severity: String,
    description: String,
    status: String,
    raised_by: Uuid,
    acknowledged_by: Option<Uuid>,
    resolved_by: Option<Uuid>,
    resolution: Option<String>,
    response_time_seconds: Option<i64>,
    resolution_time_seconds: Option<i64>,
    created_at: chrono::DateTime<Utc>,
    acknowledged_at: Option<chrono::DateTime<Utc>>,
    resolved_at: Option<chrono::DateTime<Utc>>,
    restart_authorized_by: Option<Uuid>,
    restart_authorized_at: Option<chrono::DateTime<Utc>>,
    abnormal_condition_observed_at: Option<chrono::DateTime<Utc>>,
    contained_at: Option<chrono::DateTime<Utc>>,
    contained_by: Option<Uuid>,
    contained_note: Option<String>,
    escalated: bool,
    escalated_at: Option<chrono::DateTime<Utc>>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct ProjectRow {
    id: Uuid,
    tenant_id: Uuid,
    project_code: String,
    name: String,
    description: String,
    category: String,
    status: String,
    priority: String,
    owner_id: Uuid,
    team_members: serde_json::Value,
    planned_start: Option<chrono::DateTime<Utc>>,
    planned_end: Option<chrono::DateTime<Utc>>,
    actual_start: Option<chrono::DateTime<Utc>>,
    actual_end: Option<chrono::DateTime<Utc>>,
    budget: Option<rust_decimal::Decimal>,
    savings_realized: Option<rust_decimal::Decimal>,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct A3Row {
    id: Uuid,
    tenant_id: Uuid,
    a3_number: String,
    title: String,
    background: String,
    current_state: String,
    goal: String,
    root_cause_analysis: String,
    countermeasures: String,
    check_plan: String,
    follow_up: String,
    a3_type: String,
    severity: String,
    status: String,
    owner_id: Uuid,
    created_at: chrono::DateTime<Utc>,
    closed_at: Option<chrono::DateTime<Utc>>,
    version: i64,
    observed_conditions: serde_json::Value,
    metric_baselines: serde_json::Value,
    evidence_refs: serde_json::Value,
    cause_hypotheses: serde_json::Value,
    experiments: serde_json::Value,
    verifications: serde_json::Value,
    standardizations: serde_json::Value,
    learnings: serde_json::Value,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct RiskRow {
    id: Uuid,
    tenant_id: Uuid,
    risk_number: String,
    title: String,
    description: String,
    category: String,
    likelihood: String,
    impact: String,
    risk_score: i32,
    mitigation: String,
    contingency: String,
    status: String,
    owner_id: Uuid,
    created_at: chrono::DateTime<Utc>,
    mitigated_at: Option<chrono::DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn andon_row_to_domain(r: AndonRow) -> Andon {
    Andon {
        id: r.id,
        tenant_id: r.tenant_id,
        andon_number: r.andon_number,
        work_center_id: r.work_center_id,
        issue_type: r.issue_type,
        severity: r.severity,
        description: r.description,
        status: r.status,
        raised_by: r.raised_by,
        acknowledged_by: r.acknowledged_by,
        resolved_by: r.resolved_by,
        resolution: r.resolution,
        response_time_seconds: r.response_time_seconds,
        resolution_time_seconds: r.resolution_time_seconds,
        created_at: r.created_at,
        acknowledged_at: r.acknowledged_at,
        resolved_at: r.resolved_at,
        restart_authorized_by: r.restart_authorized_by,
        restart_authorized_at: r.restart_authorized_at,
        abnormal_condition_observed_at: r.abnormal_condition_observed_at,
        contained_at: r.contained_at,
        contained_by: r.contained_by,
        contained_note: r.contained_note,
        escalated: r.escalated,
        escalated_at: r.escalated_at,
    }
}

fn project_row_to_domain(r: ProjectRow) -> Project {
    let team_members: Vec<Uuid> = serde_json::from_value(r.team_members).unwrap_or_default();
    Project {
        id: r.id,
        tenant_id: r.tenant_id,
        project_code: r.project_code,
        name: r.name,
        description: r.description,
        category: r.category,
        status: r.status,
        priority: r.priority,
        owner_id: r.owner_id,
        team_members,
        planned_start: r.planned_start,
        planned_end: r.planned_end,
        actual_start: r.actual_start,
        actual_end: r.actual_end,
        budget: r.budget,
        savings_realized: r.savings_realized,
        created_at: r.created_at,
    }
}

fn a3_row_to_domain(r: A3Row) -> A3 {
    A3 {
        id: r.id,
        tenant_id: r.tenant_id,
        a3_number: r.a3_number,
        title: r.title,
        background: r.background,
        current_state: r.current_state,
        goal: r.goal,
        root_cause_analysis: r.root_cause_analysis,
        countermeasures: r.countermeasures,
        check_plan: r.check_plan,
        follow_up: r.follow_up,
        a3_type: r.a3_type,
        severity: r.severity,
        status: r.status,
        version: r.version.max(0) as u64,
        owner_id: r.owner_id,
        created_at: r.created_at,
        closed_at: r.closed_at,
        observed_conditions: r
            .observed_conditions
            .as_array()
            .cloned()
            .unwrap_or_default(),
        metric_baselines: r.metric_baselines.as_array().cloned().unwrap_or_default(),
        evidence_refs: r
            .evidence_refs
            .as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default(),
        cause_hypotheses: r.cause_hypotheses.as_array().cloned().unwrap_or_default(),
        experiments: r.experiments.as_array().cloned().unwrap_or_default(),
        verifications: r.verifications.as_array().cloned().unwrap_or_default(),
        standardizations: r.standardizations.as_array().cloned().unwrap_or_default(),
        learnings: r.learnings.as_array().cloned().unwrap_or_default(),
    }
}

fn risk_row_to_domain(r: RiskRow) -> Risk {
    Risk {
        id: r.id,
        tenant_id: r.tenant_id,
        risk_number: r.risk_number,
        title: r.title,
        description: r.description,
        category: r.category,
        likelihood: r.likelihood,
        impact: r.impact,
        risk_score: r.risk_score,
        mitigation: r.mitigation,
        contingency: r.contingency,
        status: r.status,
        owner_id: r.owner_id,
        created_at: r.created_at,
        mitigated_at: r.mitigated_at,
    }
}

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items,
        total: count as usize,
        page,
        per_page,
        total_pages: (count as usize).max(1).div_ceil(per_page),
    }
}

fn likelihood_score(l: &str) -> i32 {
    match l {
        "rare" => 1,
        "unlikely" => 2,
        "possible" => 3,
        "likely" => 4,
        "almost_certain" => 5,
        _ => 3,
    }
}

fn impact_score(i: &str) -> i32 {
    match i {
        "insignificant" => 1,
        "minor" => 2,
        "moderate" => 3,
        "major" => 4,
        "catastrophic" => 5,
        _ => 3,
    }
}

#[async_trait]
impl OperationsService for DatabaseOperationsService {
    // ── Andon ───────────────────────────────────────────────────────────

    async fn raise_andon(&self, tenant_id: Uuid, andon: Andon) -> Result<Andon> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let andon_number = format!(
            "AND-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );

        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    r#"INSERT INTO andons (id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,'active',$8,NULL,NULL,NULL,NULL,NULL,$9,NULL,NULL,NULL,NULL,$10,$11,$12,$13,FALSE,NULL)
                       RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at"#,
                )
                .bind(id).bind(tenant_id).bind(&andon_number).bind(andon.work_center_id)
                .bind(&andon.issue_type).bind(&andon.severity).bind(&andon.description)
                .bind(andon.raised_by).bind(now)
                .bind(andon.abnormal_condition_observed_at)
                .bind(andon.contained_at)
                .bind(andon.contained_by)
                .bind(&andon.contained_note)
                .fetch_one(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to raise andon: {e}")))
            })
        }).await?;

        Ok(andon_row_to_domain(row))
    }

    async fn acknowledge_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        acknowledged_by: Uuid,
    ) -> Result<Andon> {
        let now = Utc::now();
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    r#"UPDATE andons SET status='acknowledged', acknowledged_by=$1, acknowledged_at=$2,
                        response_time_seconds=EXTRACT(EPOCH FROM ($2 - created_at))::bigint
                       WHERE id=$3 AND tenant_id=$4 AND status='active'
                       RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at"#,
                )
                .bind(acknowledged_by).bind(now).bind(id).bind(tenant_id)
                .fetch_optional(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to acknowledge andon: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found or not active")))
            })
        }).await?;

        Ok(andon_row_to_domain(row))
    }

    async fn escalate_andon(&self, tenant_id: Uuid, id: Uuid, escalated_by: Uuid) -> Result<Andon> {
        // Item 41: escalation is a REAL state transition through the same
        // command path — active Andons are acknowledged AND flagged for
        // tier review; already-acknowledged ones are flagged in place.
        let now = Utc::now();
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    r#"UPDATE andons SET escalated=TRUE, escalated_at=$1, status=CASE
                           WHEN status='active' THEN 'acknowledged' ELSE status END,
                           acknowledged_by=COALESCE(acknowledged_by, $2),
                           acknowledged_at=COALESCE(acknowledged_at, $1),
                           response_time_seconds=COALESCE(response_time_seconds, EXTRACT(EPOCH FROM ($1 - created_at))::bigint)
                       WHERE id=$3 AND tenant_id=$4 AND status NOT IN ('resolved','voided')
                       RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at, escalated, escalated_at"#,
                )
                .bind(now).bind(escalated_by).bind(id).bind(tenant_id)
                .fetch_optional(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to escalate andon: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found or already closed")))
            })
        }).await?;

        Ok(andon_row_to_domain(row))
    }

    async fn resolve_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        resolved_by: Uuid,
        resolution: &str,
    ) -> Result<Andon> {
        // HARD RULE, enforced ATOMICALLY in SQL: a critical-safety Andon
        // can only be resolved when a restart authorization exists — the
        // condition is part of the UPDATE's WHERE, so there is no
        // read/check/write race between replicas.
        let now = Utc::now();
        let resolution_owned = resolution.to_string();
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, AndonRow>(
                    r#"UPDATE andons SET status='resolved', resolved_by=$1, resolution=$2, resolved_at=$3,
                        resolution_time_seconds=EXTRACT(EPOCH FROM ($3 - created_at))::bigint,
                        response_time_seconds=COALESCE(response_time_seconds, EXTRACT(EPOCH FROM ($3 - created_at))::bigint)
                       WHERE id=$4 AND tenant_id=$5 AND status NOT IN ('resolved','closed')
                         AND (severity != 'critical' OR issue_type != 'safety' OR restart_authorized_by IS NOT NULL)
                       RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at"#,
                )
                .bind(resolved_by).bind(&resolution_owned).bind(now).bind(id).bind(tenant_id)
                .fetch_optional(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to resolve andon: {e}")))?;

                let Some(row) = row else {
                    // Distinguish: not found / already resolved / safety rule.
                    let state: Option<(String, String, Option<Uuid>, String)> = sqlx::query_as(
                        "SELECT severity, issue_type, restart_authorized_by, status FROM andons \
                         WHERE id = $1 AND tenant_id = $2",
                    )
                    .bind(id)
                    .bind(tenant_id)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to read andon state: {e}")))?;
                    match state {
                None => return Err(SenseiError::NotFound(format!("Andon {id} not found"))),
                Some((_, _, _, status)) if status == "resolved" || status == "closed" => {
                    return Err(SenseiError::Conflict(format!(
                        "Andon {id} is already {status}"
                    )));
                }
                    Some((severity, issue_type, restart_authorized_by, _)) => {
                        return Err(crate::tps::rules::check_safety_restart(
                            severity == "critical" && issue_type == "safety",
                            restart_authorized_by.is_some(),
                        )
                        .map_err(|v| SenseiError::Conflict(v.message().to_string()))
                        .map_err(|_| {
                            SenseiError::Conflict(
                                "Andon state changed concurrently — retry".to_string(),
                            )
                        })
                        .unwrap_err());
                    }
                }
                };

                Ok(row)
            })
        })
        .await?;

        Ok(andon_row_to_domain(row))
    }

    async fn authorize_restart(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        authorized_by: Uuid,
    ) -> Result<Andon> {
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    "UPDATE andons SET restart_authorized_by = $3, restart_authorized_at = NOW() \
                     WHERE id = $1 AND tenant_id = $2 \
                     RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, \
                               description, status, raised_by, acknowledged_by, resolved_by, resolution, \
                               response_time_seconds, resolution_time_seconds, created_at, \
                               acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at",
                )
                .bind(id)
                .bind(tenant_id)
                .bind(authorized_by)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to authorize restart: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))
            })
        }).await?;
        Ok(andon_row_to_domain(row))
    }

    async fn get_andon(&self, tenant_id: Uuid, id: Uuid) -> Result<Andon> {
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    "SELECT id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at FROM andons WHERE id = $1 AND tenant_id = $2",
                )
                .bind(id).bind(tenant_id)
                .fetch_optional(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to get andon: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))
            })
        }).await?;

        Ok(andon_row_to_domain(row))
    }

    async fn list_andons(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        work_center_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Andon>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let status_owned = status.map(|s| s.to_string());

        let (items, count) = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                let items: Vec<AndonRow> = sqlx::query_as(
                    r#"SELECT id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at
                       FROM andons WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::uuid IS NULL OR work_center_id=$3)
                       ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
                )
                .bind(tenant_id).bind(&status_owned).bind(work_center_id).bind(per_page as i64).bind(offset as i64)
                .fetch_all(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to list andons: {e}")))?;

                let count: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM andons WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::uuid IS NULL OR work_center_id=$3)",
                )
                .bind(tenant_id).bind(&status_owned).bind(work_center_id).fetch_one(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to count andons: {e}")))?;
                Ok((items, count))
            })
        }).await?;

        Ok(paginate(
            items.into_iter().map(andon_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    // ── Projects ────────────────────────────────────────────────────────

    async fn create_project(&self, tenant_id: Uuid, project: Project) -> Result<Project> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let project_code = format!(
            "PRJ-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );
        let team_json =
            serde_json::to_value(&project.team_members).unwrap_or(serde_json::Value::Array(vec![]));

        let row = sqlx::query_as::<_, ProjectRow>(
            r#"INSERT INTO projects (id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,'not_started',$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
               RETURNING id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at"#,
        )
        .bind(id).bind(tenant_id).bind(&project_code).bind(&project.name).bind(&project.description)
        .bind(&project.category).bind(&project.priority).bind(project.owner_id).bind(&team_json)
        .bind(project.planned_start).bind(project.planned_end).bind(project.actual_start).bind(project.actual_end)
        .bind(project.budget).bind(project.savings_realized).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create project: {e}")))?;

        Ok(project_row_to_domain(row))
    }

    async fn get_project(&self, tenant_id: Uuid, id: Uuid) -> Result<Project> {
        let row = sqlx::query_as::<_, ProjectRow>(
            "SELECT id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at FROM projects WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get project: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;

        Ok(project_row_to_domain(row))
    }

    async fn list_projects(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Project>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<ProjectRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at
               FROM projects WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR category=$3)
               ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(status).bind(category).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list projects: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM projects WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR category=$3)",
        )
        .bind(tenant_id).bind(status).bind(category).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count projects: {e}")))?;

        Ok(paginate(
            items.into_iter().map(project_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn complete_project(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        savings_realized: f64,
    ) -> Result<Project> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, ProjectRow>(
            r#"UPDATE projects SET status='completed', actual_end=$1, savings_realized=$2
               WHERE id=$3 AND tenant_id=$4
               RETURNING id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at"#,
        )
        .bind(now).bind(savings_realized).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to complete project: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;

        Ok(project_row_to_domain(row))
    }

    // ── A3 ──────────────────────────────────────────────────────────────

    async fn create_a3(&self, tenant_id: Uuid, a3: A3) -> Result<A3> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let a3_number = format!(
            "A3-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );

        // Thirteenth audit: the A3 row and its created EVENT are ONE
        // transaction — a committed A3 can never lose its event to a
        // post-commit publish failure (the old best-effort warn-and-drop).
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin A3 tx: {e}")))?;
        let row = sqlx::query_as::<_, A3Row>(
            r#"INSERT INTO a3_reports (id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'draft',$14,$15,NULL,
                       $16,$17,$18,$19,$20,$21,$22,$23)
               RETURNING id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings"#,
        )
        .bind(id).bind(tenant_id).bind(&a3_number).bind(&a3.title).bind(&a3.background)
        .bind(&a3.current_state).bind(&a3.goal).bind(&a3.root_cause_analysis)
        .bind(&a3.countermeasures).bind(&a3.check_plan).bind(&a3.follow_up)
        .bind(&a3.a3_type).bind(&a3.severity)
        .bind(a3.owner_id).bind(now)
        .bind(serde_json::to_value(&a3.observed_conditions).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.metric_baselines).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.evidence_refs).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.cause_hypotheses).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.experiments).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.verifications).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.standardizations).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.learnings).unwrap_or(serde_json::Value::Array(vec![])))
        .fetch_one(&mut *tx)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create A3: {e}")))?;
        // The A3-created event rides the SAME transaction (thirteenth
        // audit): a committed A3 can never lose its event.
        sensei_db::outbox::enqueue_outbox(
            &mut tx,
            tenant_id,
            "a3",
            id,
            "sensei.ops.a3.created",
            serde_json::json!({
                "a3_number": a3_number,
                "title": a3.title,
                "a3_type": a3.a3_type,
                "severity": a3.severity,
            }),
        )
        .await?;
        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit A3: {e}")))?;

        Ok(a3_row_to_domain(row))
    }

    async fn get_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<A3> {
        let row = sqlx::query_as::<_, A3Row>(
            "SELECT id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings FROM a3_reports WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get A3: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;

        Ok(a3_row_to_domain(row))
    }

    async fn list_a3s(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<A3>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<A3Row> = sqlx::query_as(
            r#"SELECT id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings
               FROM a3_reports WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)
               ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        )
        .bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list A3s: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM a3_reports WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)",
        )
        .bind(tenant_id).bind(status).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count A3s: {e}")))?;

        Ok(paginate(
            items.into_iter().map(a3_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn close_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<A3> {
        // An A3 cannot close because somebody clicked Close: the
        // countermeasures (root_cause_analysis/countermeasures) and the
        // verification plan (check_plan/follow_up) must be recorded first.
        let existing = sqlx::query_as::<_, A3Row>(
            r#"SELECT id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings
               FROM a3_reports WHERE id=$1 AND tenant_id=$2"#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get A3: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;
        if existing.countermeasures.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: no countermeasures recorded".to_string(),
            ));
        }
        if existing.check_plan.trim().is_empty() || existing.follow_up.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: the verification plan (check_plan/follow_up) is empty —                  record the target metrics and verification window first"
                    .to_string(),
            ));
        }
        // Closing is evidence-driven: at least one VERIFICATION record
        // (metric observed after the countermeasure) must be populated.
        let verifications = existing
            .verifications
            .as_array()
            .map(|a| a.len())
            .unwrap_or(0);
        if verifications == 0 {
            return Err(SenseiError::Validation(
                "A3 cannot be closed: no verification evidence recorded (verifications is empty)"
                    .to_string(),
            ));
        }

        let now = Utc::now();
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin close tx: {e}")))?;
        set_tenant_context(&mut tx, tenant_id).await?;

        let row = sqlx::query_as::<_, A3Row>(
            r#"UPDATE a3_reports SET status='closed', closed_at=$1, version = version + 1 WHERE id=$2 AND tenant_id=$3
               RETURNING id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings"#,
        )
        .bind(now).bind(id).bind(tenant_id)
        .fetch_optional(&mut *tx)
        .await.map_err(|e| SenseiError::Database(format!("Failed to close A3: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("A3 {id} not found")))?;

        // Outbox row in the SAME transaction: the close event is never
        // lost to a post-commit publish failure.
        sqlx::query(
            "INSERT INTO outbox_events \
                (event_id, tenant_id, aggregate_type, aggregate_id, event_type, payload) \
             VALUES ($1, $2, 'a3', $3, 'sensei.a3.closed', $4)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(id)
        .bind(serde_json::json!({ "a3_number": row.a3_number }))
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            SenseiError::Database(format!("Failed to write A3 close outbox event: {e}"))
        })?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit close tx: {e}")))?;

        Ok(a3_row_to_domain(row))
    }

    // ── Risk ────────────────────────────────────────────────────────────

    async fn create_risk(&self, tenant_id: Uuid, risk: Risk) -> Result<Risk> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        let risk_number = format!(
            "RSK-{}-{}",
            now.format("%Y%m%d"),
            &id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8]
        );
        let risk_score = likelihood_score(&risk.likelihood) * impact_score(&risk.impact);

        let row = sqlx::query_as::<_, RiskRow>(
            r#"INSERT INTO risks (id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'identified',$12,$13,NULL)
               RETURNING id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at"#,
        )
        .bind(id).bind(tenant_id).bind(&risk_number).bind(&risk.title).bind(&risk.description)
        .bind(&risk.category).bind(&risk.likelihood).bind(&risk.impact).bind(risk_score)
        .bind(&risk.mitigation).bind(&risk.contingency).bind(risk.owner_id).bind(now)
        .fetch_one(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to create risk: {e}")))?;

        Ok(risk_row_to_domain(row))
    }

    async fn get_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<Risk> {
        let row = sqlx::query_as::<_, RiskRow>(
            "SELECT id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at FROM risks WHERE id = $1 AND tenant_id = $2",
        )
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to get risk: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;

        Ok(risk_row_to_domain(row))
    }

    async fn list_risks(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        category: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Risk>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let items: Vec<RiskRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at
               FROM risks WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR category=$3)
               ORDER BY risk_score DESC LIMIT $4 OFFSET $5"#,
        )
        .bind(tenant_id).bind(status).bind(category).bind(per_page as i64).bind(offset as i64)
        .fetch_all(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to list risks: {e}")))?;

        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM risks WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) AND ($3::text IS NULL OR category=$3)",
        )
        .bind(tenant_id).bind(status).bind(category).fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count risks: {e}")))?;

        Ok(paginate(
            items.into_iter().map(risk_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn mitigate_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<Risk> {
        let now = Utc::now();
        let row = sqlx::query_as::<_, RiskRow>(
            r#"UPDATE risks SET status='mitigated', mitigated_at=$1 WHERE id=$2 AND tenant_id=$3
               RETURNING id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at"#,
        )
        .bind(now).bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to mitigate risk: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;

        Ok(risk_row_to_domain(row))
    }

    // ── Update/Delete for Andon ─────────────────────────────────────────

    async fn update_andon(&self, tenant_id: Uuid, id: Uuid, andon: Andon) -> Result<Andon> {
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                sqlx::query_as::<_, AndonRow>(
                    r#"UPDATE andons SET issue_type=$1, severity=$2, description=$3 WHERE id=$4 AND tenant_id=$5
                       RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, description, status, raised_by, acknowledged_by, resolved_by, resolution, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at"#,
                )
                .bind(&andon.issue_type).bind(&andon.severity).bind(&andon.description).bind(id).bind(tenant_id)
                .fetch_optional(&mut **tx)
                .await.map_err(|e| SenseiError::Database(format!("Failed to update andon: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Andon {id} not found")))
            })
        }).await?;

        Ok(andon_row_to_domain(row))
    }

    async fn void_andon(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        actor_id: Uuid,
        reason: &str,
    ) -> Result<Andon> {
        // The critical-safety rule applies to voiding too: a safety Andon
        // cannot avoid the resolve guard by going down the void path.
        let reason_owned = format!("VOIDED: {reason}");
        let row = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, AndonRow>(
                    "UPDATE andons SET status = 'voided', resolved_by = $3, resolution = $4 \
                     WHERE id = $1 AND tenant_id = $2 \
                       AND (severity != 'critical' OR issue_type != 'safety' OR restart_authorized_by IS NOT NULL) \
                     RETURNING id, tenant_id, andon_number, work_center_id, issue_type, severity, \
                               description, status, raised_by, acknowledged_by, resolved_by, \
                               resolution, response_time_seconds, resolution_time_seconds, \
                               created_at, acknowledged_at, resolved_at, restart_authorized_by, restart_authorized_at, abnormal_condition_observed_at, contained_at, contained_by, contained_note, escalated, escalated_at",
                )
                .bind(id)
                .bind(tenant_id)
                .bind(actor_id)
                .bind(&reason_owned)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to void andon: {e}")))?;

                let Some(row) = row else {
                    let state: Option<(String, String, Option<Uuid>)> = sqlx::query_as(
                        "SELECT severity, issue_type, restart_authorized_by FROM andons \
                         WHERE id = $1 AND tenant_id = $2",
                    )
                    .bind(id)
                    .bind(tenant_id)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to read andon state: {e}")))?;
                    return match state {
                        None => Err(SenseiError::NotFound(format!("Andon {id} not found"))),
                        Some((severity, issue_type, restart_authorized_by)) => {
                            crate::tps::rules::check_safety_restart(
                                severity == "critical" && issue_type == "safety",
                                restart_authorized_by.is_some(),
                            )
                            .map_err(|v| SenseiError::Conflict(v.message().to_string()))
                            .and(Err(SenseiError::Conflict(
                                "Andon state changed concurrently — retry".to_string(),
                            )))
                        }
                    };
                };
                Ok(row)
            })
        }).await?;
        Ok(andon_row_to_domain(row))
    }

    // ── Update/Delete for Project ───────────────────────────────────────

    async fn update_project(&self, tenant_id: Uuid, id: Uuid, project: Project) -> Result<Project> {
        let team_json =
            serde_json::to_value(&project.team_members).unwrap_or(serde_json::Value::Array(vec![]));
        let row = sqlx::query_as::<_, ProjectRow>(
            r#"UPDATE projects SET name=$1, description=$2, category=$3, priority=$4, owner_id=$5, team_members=$6, planned_start=$7, planned_end=$8, budget=$9
               WHERE id=$10 AND tenant_id=$11
               RETURNING id, tenant_id, project_code, name, description, category, status, priority, owner_id, team_members, planned_start, planned_end, actual_start, actual_end, budget, savings_realized, created_at"#,
        )
        .bind(&project.name).bind(&project.description).bind(&project.category).bind(&project.priority)
        .bind(project.owner_id).bind(&team_json).bind(project.planned_start).bind(project.planned_end).bind(project.budget)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update project: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Project {id} not found")))?;

        Ok(project_row_to_domain(row))
    }

    async fn delete_project(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM projects WHERE id = $1 AND tenant_id = $2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete project: {e}")))?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Project {id} not found")));
        }
        Ok(())
    }

    // ── Update/Delete for A3 ────────────────────────────────────────────

    async fn update_a3(&self, tenant_id: Uuid, id: Uuid, a3: A3) -> Result<A3> {
        // Optimistic concurrency is ATOMIC in SQL: the row updates ONLY
        // when it still holds the caller's expected version, and the
        // version increments in the same statement. Two replicas that both
        // read version 0 cannot both succeed — the loser gets 0 rows -> 409.
        let expected = a3.version;
        let row = sqlx::query_as::<_, A3Row>(
            r#"UPDATE a3_reports SET title=$1, background=$2, current_state=$3, goal=$4, root_cause_analysis=$5, countermeasures=$6, check_plan=$7, follow_up=$8, a3_type=$9, severity=$10,
                                   observed_conditions=$13, metric_baselines=$14, evidence_refs=$15, cause_hypotheses=$16, experiments=$17, verifications=$18, standardizations=$19, learnings=$20,
                                   version = version + 1
               WHERE id=$11 AND tenant_id=$12 AND version=$21
               RETURNING id, tenant_id, a3_number, title, background, current_state, goal, root_cause_analysis, countermeasures, check_plan, follow_up, a3_type, severity, status, owner_id, created_at, closed_at, version, observed_conditions, metric_baselines, evidence_refs, cause_hypotheses, experiments, verifications, standardizations, learnings"#,
        )
        .bind(&a3.title).bind(&a3.background).bind(&a3.current_state).bind(&a3.goal)
        .bind(&a3.root_cause_analysis).bind(&a3.countermeasures).bind(&a3.check_plan).bind(&a3.follow_up)
        .bind(&a3.a3_type).bind(&a3.severity)
        .bind(id).bind(tenant_id)
        .bind(serde_json::to_value(&a3.observed_conditions).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.metric_baselines).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.evidence_refs).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.cause_hypotheses).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.experiments).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.verifications).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.standardizations).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(serde_json::to_value(&a3.learnings).unwrap_or(serde_json::Value::Array(vec![])))
        .bind(expected as i64)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update A3: {e}")))?
        .ok_or_else(|| {
            SenseiError::Conflict(format!(
                "VERSION_CONFLICT: A3 {id} was modified concurrently (expected version {expected})"
            ))
        })?;

        Ok(a3_row_to_domain(row))
    }

    async fn delete_a3(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        // A3 learning history is never physically erased: abandoned draft
        // cases are voided and retained.
        let result = sqlx::query(
            "UPDATE a3_reports SET status = 'voided' WHERE id = $1 AND tenant_id = $2 \
             AND status = 'draft'",
        )
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to void A3: {e}")))?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::Validation(
                "Only draft A3 cases can be voided; published/closed history is retained"
                    .to_string(),
            ));
        }
        Ok(())
    }

    // ── Update/Delete for Risk ──────────────────────────────────────────

    async fn update_risk(&self, tenant_id: Uuid, id: Uuid, risk: Risk) -> Result<Risk> {
        let risk_score = likelihood_score(&risk.likelihood) * impact_score(&risk.impact);
        let row = sqlx::query_as::<_, RiskRow>(
            r#"UPDATE risks SET title=$1, description=$2, category=$3, likelihood=$4, impact=$5, risk_score=$6, mitigation=$7, contingency=$8, owner_id=$9
               WHERE id=$10 AND tenant_id=$11
               RETURNING id, tenant_id, risk_number, title, description, category, likelihood, impact, risk_score, mitigation, contingency, status, owner_id, created_at, mitigated_at"#,
        )
        .bind(&risk.title).bind(&risk.description).bind(&risk.category).bind(&risk.likelihood)
        .bind(&risk.impact).bind(risk_score).bind(&risk.mitigation).bind(&risk.contingency).bind(risk.owner_id)
        .bind(id).bind(tenant_id)
        .fetch_optional(&self.pool)
        .await.map_err(|e| SenseiError::Database(format!("Failed to update risk: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Risk {id} not found")))?;

        Ok(risk_row_to_domain(row))
    }

    async fn delete_risk(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let result = sqlx::query("DELETE FROM risks WHERE id = $1 AND tenant_id = $2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete risk: {e}")))?;
        if result.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Risk {id} not found")));
        }
        Ok(())
    }
}
