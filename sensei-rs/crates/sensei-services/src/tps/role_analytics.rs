//! Role-specific analytics (fifteenth audit 48-68 + A14): the response
//! shape is NOW / ABNORMAL / WHY / NEXT / LEARN for EVERY role — what
//! needs attention, why, and what to do about it. No universal
//! dashboards, no operator ranking.
use chrono::{DateTime, Utc};
use sensei_core::error::{Result, SenseiError};
use sqlx::PgPool;
use uuid::Uuid;

/// The role analytics response: every role receives the SAME six-field
/// shape; the role decides which sections carry facts and the SCOPE
/// (site + work center) decides which facts are visible at all.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RoleAnalytics {
    pub role: String,
    pub scope_site_id: Option<Uuid>,
    pub scope_work_center_id: Option<Uuid>,
    pub now: Vec<AnalyticLine>,
    pub abnormal: Vec<AnalyticLine>,
    pub why: Vec<AnalyticLine>,
    pub next: Vec<String>,
    pub learn: Vec<String>,
    pub generated_at: DateTime<Utc>,
}

/// One deterministic analytic fact. `target`/`actual`/`delta` keep the
/// plan-vs-actual contract (delta = actual − target, negative = behind);
/// `first_divergence` and `check_date` anchor the line to observable
/// evidence, never to per-person comparison.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AnalyticLine {
    pub label: String,
    pub target: Option<f64>,
    pub actual: f64,
    pub delta: Option<f64>,
    pub unit: String,
    pub first_divergence: Option<String>,
    pub owner: Option<String>,
    pub check_date: Option<String>,
}

impl AnalyticLine {
    fn fact(label: impl Into<String>, actual: f64, unit: impl Into<String>) -> Self {
        Self {
            label: label.into(),
            target: None,
            actual,
            delta: None,
            unit: unit.into(),
            first_divergence: None,
            owner: None,
            check_date: None,
        }
    }

    fn with_date(mut self, date: DateTime<Utc>) -> Self {
        self.first_divergence = Some(date.date_naive().to_string());
        self.check_date = Some(date.date_naive().to_string());
        self
    }

    fn with_delta(mut self, target: f64, actual: f64) -> Self {
        self.target = Some(target);
        self.delta = Some(actual - target);
        self
    }
}

/// Roles whose analytics are the CALLER'S WORK CENTER detail view.
fn is_work_center_role(role: &str) -> bool {
    matches!(role, "operator" | "team_lead")
}

/// Roles whose analytics are the SITE aggregate view.
fn is_site_role(role: &str) -> bool {
    matches!(role, "manager" | "site_manager" | "quality" | "planner")
}

/// Build the role analytics for a caller. The role decides the sections;
/// the SCOPE (site + work center) restricts every query — an operator
/// never sees another line's queue, and the plan-vs-actual is always
/// target/actual/delta/first divergence.
pub async fn build_role_analytics(
    pool: &PgPool,
    tenant_id: Uuid,
    role: &str,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
) -> Result<RoleAnalytics> {
    let mut analytics = RoleAnalytics {
        role: role.to_string(),
        scope_site_id: site_id,
        scope_work_center_id: work_center_id,
        now: Vec::new(),
        abnormal: Vec::new(),
        why: Vec::new(),
        next: Vec::new(),
        learn: Vec::new(),
        generated_at: Utc::now(),
    };

    if is_work_center_role(role) {
        collect_work_center_view(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;
    } else if is_site_role(role) {
        collect_site_view(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;
    } else {
        return Err(SenseiError::Validation(format!(
            "role '{role}' has no analytics definition (operator/team_lead/manager/site_manager/quality/planner)"
        )));
    }

    // Shared, scope-restricted: open conditions feed ABNORMAL/WHY/NEXT,
    // recurring conditions feed LEARN — for EVERY role.
    collect_conditions(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;

    Ok(analytics)
}

/// Operator/team-lead view: the caller's own work center — andons, pitch
/// gaps, today's production, material starvation, skill coverage, last
/// abnormality. Every query is restricted by work_center_id (or site).
async fn collect_work_center_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    // Active/acknowledged andons in scope: status 'active' is abnormal.
    type AndonRow = (
        String,
        String,
        String,
        Option<String>,
        String,
        DateTime<Utc>,
        Option<String>,
    );
    let andons: Vec<AndonRow> =
        sqlx::query_as(
            "SELECT a.andon_number, a.issue_type, a.severity, a.description, a.status, a.created_at, wc.name \
             FROM andons a \
             LEFT JOIN work_centers wc ON wc.id = a.work_center_id AND wc.tenant_id = a.tenant_id \
             WHERE a.tenant_id = $1 \
               AND a.status IN ('active', 'acknowledged') \
               AND ($2::uuid IS NULL OR a.work_center_id = $2) \
               AND ($3::uuid IS NULL OR a.site_id = $3) \
             ORDER BY a.created_at ASC \
             LIMIT 20",
        )
        .bind(tenant_id)
        .bind(work_center_id)
        .bind(site_id)
        .fetch_all(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("role analytics: andons in scope: {e}")))?;

    for (number, issue_type, severity, description, status, created_at, wc_name) in &andons {
        let label = format!("andon {number} ({issue_type})");
        let line = AnalyticLine::fact(label.clone(), 1.0, "andon").with_date(*created_at);
        a.now.push(line.clone());
        if status == "active" {
            a.abnormal.push(line);
            a.why.push(AnalyticLine::fact(
                format!(
                    "andon {number} is {status} ({issue_type}/{severity}) — line help is required"
                ),
                1.0,
                "andon",
            ));
            a.next
                .push(format!("respond to andon {number} ({issue_type})"));
        }
        if let Some(desc) = description {
            if !desc.is_empty() {
                a.why.push(AnalyticLine::fact(
                    format!("andon {number}: {desc}"),
                    1.0,
                    "andon",
                ));
            }
        }
        if status == "active" {
            if let Some(name) = wc_name {
                a.next.push(format!(
                    "observe the work at {name} while the andon {number} is open"
                ));
            }
        }
    }

    // Pitch gaps: in_progress WOs where completed < quantity — the work
    // center is behind the pitch standard.
    type PitchGapRow = (
        String,
        i64,
        i64,
        String,
        Option<String>,
        Option<DateTime<Utc>>,
    );
    let pitch_gaps: Vec<PitchGapRow> =
        sqlx::query_as(
            "SELECT wo.wo_number, wo.quantity, wo.quantity_completed, wo.product_name, wc.name, wo.scheduled_start \
             FROM work_orders wo \
             LEFT JOIN work_centers wc ON wc.id = wo.work_center_id AND wc.tenant_id = wo.tenant_id \
             WHERE wo.tenant_id = $1 \
               AND wo.status = 'in_progress' \
               AND wo.quantity_completed < wo.quantity \
               AND ($2::uuid IS NULL OR wo.work_center_id = $2) \
               AND ($3::uuid IS NULL OR wo.site_id = $3) \
             ORDER BY wo.scheduled_end ASC NULLS LAST, wo.created_at ASC \
             LIMIT 10",
        )
        .bind(tenant_id)
        .bind(work_center_id)
        .bind(site_id)
        .fetch_all(pool)
        .await
        .map_err(|e| SenseiError::Database(format!("role analytics: pitch gaps: {e}")))?;

    for (wo_number, quantity, completed, product_name, wc_name, started) in &pitch_gaps {
        let target = *quantity as f64;
        let actual = *completed as f64;
        let mut line = AnalyticLine::fact(
            format!("WO {wo_number} pitch gap ({product_name})"),
            actual,
            "units",
        )
        .with_delta(target, actual);
        if let Some(started) = started {
            line = line.with_date(*started);
        }
        a.now.push(line.clone());
        a.abnormal.push(line);
        a.why.push(AnalyticLine::fact(
            format!("WO {wo_number} is in_progress with {completed}/{quantity} units completed — behind pitch"),
            actual,
            "units",
        ));
        a.next.push(format!(
            "observe the material queue at {}",
            wc_name.as_deref().unwrap_or("the work center")
        ));
    }

    // Production events today (scoped through the work order linkage when
    // a work center is given).
    let (events_today, good_today, scrap_today): (i64, i64, i64) = sqlx::query_as(
        "SELECT COUNT(*)::bigint, \
                COALESCE(SUM(pe.good_qty), 0)::bigint, \
                COALESCE(SUM(pe.scrap_qty), 0)::bigint \
         FROM production_events pe \
         WHERE pe.tenant_id = $1 \
           AND pe.occurred_at >= date_trunc('day', NOW()) \
           AND ($2::uuid IS NULL OR pe.work_order_id IN ( \
                 SELECT w.id FROM work_orders w \
                 WHERE w.tenant_id = $1 AND w.work_center_id = $2)) \
           AND ($3::uuid IS NULL OR pe.site_id = $3)",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: production events: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "production events today",
        events_today as f64,
        "event",
    ));
    a.now.push(AnalyticLine::fact(
        "good units produced today",
        good_today as f64,
        "units",
    ));
    a.now.push(AnalyticLine::fact(
        "scrap units today",
        scrap_today as f64,
        "units",
    ));
    if scrap_today > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "scrap units today",
            scrap_today as f64,
            "units",
        ));
        a.why.push(AnalyticLine::fact(
            format!("{scrap_today} units were scrapped today — the process deviated from standard"),
            scrap_today as f64,
            "units",
        ));
    }

    // Skill coverage (qualifications): optional surface — a missing or
    // differently-shaped skills table degrades to no line, never an error.
    let skills_readable: bool = sqlx::query_scalar(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'employee_skills') \
            AND EXISTS (SELECT 1 FROM information_schema.columns \
                        WHERE table_name = 'employee_skills' AND column_name = 'work_center_id')",
    )
    .fetch_one(pool)
    .await
    .unwrap_or(false);
    if skills_readable {
        if let Ok(uncovered) = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*)::bigint \
             FROM employee_skills es \
             WHERE es.tenant_id = $1 \
               AND ($2::uuid IS NULL OR es.work_center_id = $2) \
               AND es.status IS DISTINCT FROM 'qualified'",
        )
        .bind(tenant_id)
        .bind(work_center_id)
        .fetch_one(pool)
        .await
        {
            let line = AnalyticLine::fact(
                "skill coverage gaps at the work center",
                uncovered as f64,
                "skill",
            );
            a.now.push(line.clone());
            if uncovered > 0 {
                a.abnormal.push(line);
                a.why.push(AnalyticLine::fact(
                    "the work center has skill coverage gaps — the standard may not be sustainable",
                    uncovered as f64,
                    "skill",
                ));
            }
        }
    }

    // Last abnormality: the most recent condition in scope (any status).
    let last: Option<(String, String, DateTime<Utc>)> = sqlx::query_as(
        "SELECT oc.condition_number, oc.subject_type, oc.created_at \
         FROM operational_conditions oc \
         WHERE oc.tenant_id = $1 \
           AND ($2::uuid IS NULL OR oc.scope_work_center_id = $2) \
           AND ($3::uuid IS NULL OR oc.scope_site_id = $3) \
         ORDER BY oc.created_at DESC \
         LIMIT 1",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: last abnormality: {e}")))?;
    if let Some((number, subject_type, created_at)) = last {
        a.now.push(
            AnalyticLine::fact(
                format!("last abnormality: {number} ({subject_type})"),
                1.0,
                "abnormality",
            )
            .with_date(created_at),
        );
    }

    Ok(())
}

/// Manager/site view: flow, WIP, scrap and andon response aggregated over
/// the caller's site (work center still narrows when present).
async fn collect_site_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    // Flow: open WOs + unfinished units (WIP) in scope.
    let (open_wos, wip): (i64, i64) = sqlx::query_as(
        "SELECT COUNT(*)::bigint, \
                COALESCE(SUM(wo.quantity - wo.quantity_completed), 0)::bigint \
         FROM work_orders wo \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND ($2::uuid IS NULL OR wo.work_center_id = $2) \
           AND ($3::uuid IS NULL OR wo.site_id = $3)",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: open work orders: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "open work orders",
        open_wos as f64,
        "WO",
    ));
    a.now.push(AnalyticLine::fact(
        "work in progress (unfinished units)",
        wip as f64,
        "units",
    ));
    if open_wos > 0 {
        a.next.push(format!(
            "review the flow: {open_wos} open work orders in scope"
        ));
    }

    // Quality: scrap recorded on work orders in scope.
    let scrap: i64 = sqlx::query_scalar(
        "SELECT COALESCE(SUM(wo.quantity_scrapped), 0)::bigint \
         FROM work_orders wo \
         WHERE wo.tenant_id = $1 \
           AND wo.status <> 'cancelled' \
           AND ($2::uuid IS NULL OR wo.work_center_id = $2) \
           AND ($3::uuid IS NULL OR wo.site_id = $3)",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: scrap: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "scrap on work orders",
        scrap as f64,
        "units",
    ));
    if scrap > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "scrap on work orders",
            scrap as f64,
            "units",
        ));
        a.why.push(AnalyticLine::fact(
            format!("{scrap} units of scrap recorded — the process deviated from standard"),
            scrap as f64,
            "units",
        ));
    }

    // Andon response: open count + resolved response latency in scope.
    let (open_andons, _): (i64, f64) = sqlx::query_as(
        "SELECT COUNT(*)::bigint, \
                COALESCE(AVG(a.response_time_seconds), 0)::float8 \
         FROM andons a \
         WHERE a.tenant_id = $1 \
           AND a.status IN ('active', 'acknowledged') \
           AND ($2::uuid IS NULL OR a.work_center_id = $2) \
           AND ($3::uuid IS NULL OR a.site_id = $3)",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: open andons: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "open andons",
        open_andons as f64,
        "andon",
    ));
    if open_andons > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "open andons",
            open_andons as f64,
            "andon",
        ));
        a.why.push(AnalyticLine::fact(
            format!("{open_andons} andons are open — responders are not closing them"),
            open_andons as f64,
            "andon",
        ));
    }

    let (resolved_count, avg_response): (i64, f64) = sqlx::query_as(
        "SELECT COUNT(*)::bigint, \
                COALESCE(AVG(a.response_time_seconds), 0)::float8 \
         FROM andons a \
         WHERE a.tenant_id = $1 \
           AND a.status = 'resolved' \
           AND a.response_time_seconds IS NOT NULL \
           AND ($2::uuid IS NULL OR a.work_center_id = $2) \
           AND ($3::uuid IS NULL OR a.site_id = $3)",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: andon response: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "average andon response (resolved)",
        avg_response,
        "seconds",
    ));
    a.now.push(AnalyticLine::fact(
        "resolved andons",
        resolved_count as f64,
        "andon",
    ));

    // The open andon numbers for deterministic NEXT actions.
    let open_andon_numbers: Vec<String> = sqlx::query_scalar(
        "SELECT a.andon_number \
         FROM andons a \
         WHERE a.tenant_id = $1 \
           AND a.status = 'active' \
           AND ($2::uuid IS NULL OR a.work_center_id = $2) \
           AND ($3::uuid IS NULL OR a.site_id = $3) \
         ORDER BY a.created_at ASC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: andon numbers: {e}")))?;

    for number in &open_andon_numbers {
        a.next.push(format!("respond to andon {number}"));
    }

    Ok(())
}

/// Shared for EVERY role: open conditions are abnormalities (with a
/// deterministic why/next); recurring conditions (recurrence_count >= 2)
/// feed LEARN.
async fn collect_conditions(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let conditions: Vec<(String, String, String, DateTime<Utc>)> = sqlx::query_as(
        "SELECT oc.condition_number, oc.subject_type, oc.status, oc.created_at \
         FROM operational_conditions oc \
         WHERE oc.tenant_id = $1 \
           AND oc.status IN ('open', 'responding', 'contained', 'investigating') \
           AND ($2::uuid IS NULL OR oc.scope_work_center_id = $2) \
           AND ($3::uuid IS NULL OR oc.scope_site_id = $3) \
         ORDER BY oc.created_at ASC \
         LIMIT 20",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: conditions: {e}")))?;

    for (number, subject_type, status, created_at) in &conditions {
        let label = format!("condition {number} ({subject_type})");
        let line = AnalyticLine::fact(label, 1.0, "condition").with_date(*created_at);
        a.now.push(line.clone());
        a.abnormal.push(line);
        a.why.push(AnalyticLine::fact(
            format!(
                "condition {number} is {status} — the expected {subject_type} state is not met"
            ),
            1.0,
            "condition",
        ));
        a.next
            .push(format!("respond to condition {number} ({subject_type})"));
        if subject_type == "material" {
            a.next
                .push("observe the material queue at the work center".to_string());
        }
    }

    let recurring: Vec<(String, String, i32)> = sqlx::query_as(
        "SELECT oc.condition_number, oc.subject_type, \
                COALESCE((oc.learning ->> 'recurrence_count')::int, 0) AS rc \
         FROM operational_conditions oc \
         WHERE oc.tenant_id = $1 \
           AND COALESCE((oc.learning ->> 'recurrence_count')::int, 0) >= 2 \
           AND ($2::uuid IS NULL OR oc.scope_work_center_id = $2) \
           AND ($3::uuid IS NULL OR oc.scope_site_id = $3) \
         ORDER BY oc.created_at DESC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(work_center_id)
    .bind(site_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: recurring conditions: {e}")))?;

    for (number, subject_type, count) in &recurring {
        a.learn.push(format!(
            "condition {number} ({subject_type}) has recurred {count} times — this condition keeps \
             recurring — observe the work; the standard may not fit"
        ));
    }

    Ok(())
}
