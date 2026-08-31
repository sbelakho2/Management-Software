//! Role-specific analytics (fifteenth audit 48-68 + A14, sixteenth audit
//! 29-32): the response shape is NOW / ABNORMAL / WHY / NEXT / LEARN for
//! EVERY role — what needs attention, why, and what to do about it. No
//! universal dashboards, no operator ranking.
//!
//! Sixteenth-audit guarantees:
//! - item 29: buyer / material_controller / npi / finance have their own
//!   DISTINCT analytics branches (open-PO past-due, line starvation risk,
//!   new-product readiness, scrap-at-standard-cost);
//! - item 30: the pitch gap is a function of ELAPSED TIME vs the
//!   standard's takt (expected = elapsed_seconds / takt_seconds), never a
//!   "unfinished work order = behind" heuristic;
//! - item 31: every role REQUIRES its operational scope — an unscoped
//!   call DENIES (Forbidden) instead of silently returning tenant-wide
//!   results;
//! - item 32: the active role is resolved by an EXPLICIT documented
//!   priority ([`ANALYTICS_ROLE_PRIORITY`]), never by the arbitrary order
//!   of the user's roles vector.
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

/// The explicit analytics role PRIORITY (item 32): a user with several
/// roles sees the analytics of the HIGHEST-priority role — independent of
/// the arbitrary order of the `user.roles` vector. The priority is a
/// stable product definition; changing it is a product decision.
pub const ANALYTICS_ROLE_PRIORITY: &[&str] = &[
    "site_manager",
    "manager",
    "quality",
    "planner",
    "supervisor",
    "team_lead",
    "operator",
];

/// Resolve the ACTIVE analytics role (item 32): returns the FIRST role of
/// `user_roles` that appears in [`ANALYTICS_ROLE_PRIORITY`] — the
/// priority decides, NOT the vector order:
/// `select_active_role(&["operator", "quality"])` is `quality`, while
/// `select_active_role(&["operator"])` is `operator`. Returns `None` when
/// no role has an analytics definition.
pub fn select_active_role(user_roles: &[String]) -> Option<String> {
    ANALYTICS_ROLE_PRIORITY
        .iter()
        .find(|candidate| user_roles.iter().any(|role| role == *candidate))
        .map(|role| (*role).to_string())
}

/// SCOPE GATE (item 31): an unscoped call must NEVER degrade to
/// tenant-wide results — the `(scope IS NULL OR ...)` form is forbidden
/// for roles that REQUIRE a scope. operator/team_lead require a
/// work-center scope; every other defined role (manager, site_manager,
/// quality, planner, supervisor, buyer, material_controller, npi,
/// finance) requires a SITE scope. Only a hypothetical 'ceo'/'corporate'
/// role could be unscoped — it does not exist yet, so ALL roles require
/// their scope now. The typed error is `Forbidden` (403): the caller has
/// no operational assignment (the `MissingOperationalAssignment`
/// semantics this surface must refuse — `sensei-core` carries no such
/// variant in this tree, so `Forbidden` carries the message).
fn require_scope(role: &str, site_id: Option<Uuid>, work_center_id: Option<Uuid>) -> Result<()> {
    match role {
        "operator" | "team_lead" => {
            if work_center_id.is_none() {
                return Err(SenseiError::Forbidden(format!(
                    "missing operational assignment: role '{role}' requires a work-center scope \
                     — unscoped analytics are not allowed"
                )));
            }
        }
        _ => {
            if site_id.is_none() {
                return Err(SenseiError::Forbidden(format!(
                    "missing operational assignment: role '{role}' requires a site scope \
                     — unscoped analytics are not allowed"
                )));
            }
        }
    }
    Ok(())
}

/// Build the role analytics for a caller. The role decides the sections;
/// the SCOPE (site + work center) restricts every query — an operator
/// never sees another line's queue, the plan-vs-actual is always
/// target/actual/delta/first divergence, and the scope gate (item 31)
/// denies unscoped calls before any query runs.
pub async fn build_role_analytics(
    pool: &PgPool,
    tenant_id: Uuid,
    role: &str,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
) -> Result<RoleAnalytics> {
    require_scope(role, site_id, work_center_id)?;

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

    match role {
        // Work-center roles: the caller's OWN work center.
        "operator" | "team_lead" => {
            collect_work_center_view(pool, tenant_id, site_id, work_center_id, &mut analytics)
                .await?;
        }
        // Site roles: the aggregate flow view of the caller's site.
        "manager" | "site_manager" | "quality" | "planner" | "supervisor" => {
            collect_site_view(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;
        }
        // Distinct supply/finance/readiness roles (item 29).
        "buyer" => collect_buyer_view(pool, tenant_id, site_id, &mut analytics).await?,
        "material_controller" => {
            collect_material_controller_view(
                pool,
                tenant_id,
                site_id,
                work_center_id,
                &mut analytics,
            )
            .await?;
        }
        "npi" => {
            collect_npi_view(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;
        }
        "finance" => {
            collect_finance_view(pool, tenant_id, site_id, work_center_id, &mut analytics).await?;
        }
        other => {
            return Err(SenseiError::Validation(format!(
                "role '{other}' has no analytics definition \
                 (operator/team_lead/manager/site_manager/quality/planner/supervisor/\
                 buyer/material_controller/npi/finance)"
            )));
        }
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

    // Pitch gaps (item 30): for every released/in_progress WO the plan
    // target is a function of ELAPSED TIME vs the standard's takt —
    // expected = elapsed_seconds / takt_seconds. A WO that merely has
    // unfinished units is NOT behind pitch; it is behind only when
    // completed < expected. The standard's takt comes from the WO's
    // standard_work_id -> standard_work_documents join; a standard row
    // with no takt falls back to 60s; a MISSING standard means no pitch
    // target exists at all (STANDARD UNAVAILABLE guidance).
    // BEHIND_TOLERANCE_UNITS absorbs clock skew between the DB NOW() used
    // at insert and the service clock at read (a sub-second skew must
    // never manufacture a "behind" false positive).
    const BEHIND_TOLERANCE_UNITS: f64 = 0.5;
    type PitchGapRow = (
        String,
        String,
        Option<String>,
        Option<DateTime<Utc>>,
        Option<DateTime<Utc>>,
        DateTime<Utc>,
        Option<Uuid>,
        Option<i32>,
        i64,
    );
    let pitch_gaps: Vec<PitchGapRow> =
        sqlx::query_as(
            "SELECT wo.wo_number, wo.product_name, wc.name, \
                    wo.actual_start, wo.scheduled_start, wo.created_at, \
                    sw.id, sw.takt_time_seconds, wo.quantity_completed \
             FROM work_orders wo \
             LEFT JOIN work_centers wc ON wc.id = wo.work_center_id AND wc.tenant_id = wo.tenant_id \
             LEFT JOIN standard_work_documents sw ON sw.id = wo.standard_work_id AND sw.tenant_id = wo.tenant_id \
             WHERE wo.tenant_id = $1 \
               AND wo.status IN ('released', 'in_progress') \
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

    let now = Utc::now();
    for (
        wo_number,
        product_name,
        wc_name,
        actual_start,
        scheduled_start,
        created_at,
        standard_id,
        takt,
        completed,
    ) in &pitch_gaps
    {
        let started = actual_start.or(*scheduled_start).or(Some(*created_at));
        // Standard missing -> no pitch target; standard present -> takt
        // (60s fallback when the standard carries no takt).
        let expected = standard_id.map(|_| {
            let takt_seconds = takt.filter(|t| *t > 0).unwrap_or(60) as f64;
            started
                .map(|s| now.signed_duration_since(s).num_seconds().max(0) as f64 / takt_seconds)
                .unwrap_or(0.0)
        });
        let wc_label = wc_name.as_deref().unwrap_or("work center");
        let label = format!("pitch gap {wc_label}");
        let actual = *completed as f64;
        let mut line = match expected {
            Some(target) => {
                AnalyticLine::fact(label.clone(), actual, "units").with_delta(target, actual)
            }
            None => AnalyticLine::fact(label.clone(), actual, "units"),
        };
        if let Some(started) = started {
            line = line.with_date(started);
        }
        a.now.push(line.clone());
        match expected {
            Some(target) => {
                let gap = actual - target;
                if gap < -BEHIND_TOLERANCE_UNITS {
                    a.abnormal.push(line.clone());
                    a.why.push(AnalyticLine::fact(
                        format!(
                            "WO {wo_number} ({product_name}) is behind pitch: {completed} units \
                             completed vs ~{target:.1} expected at a {:.0}s takt — the line is losing pitch",
                            takt.filter(|t| *t > 0).unwrap_or(60) as f64,
                        ),
                        actual,
                        "units",
                    ));
                    a.next
                        .push(format!("observe the material queue at {wc_label}"));
                }
            }
            None => {
                a.why.push(AnalyticLine::fact(
                    format!(
                        "WO {wo_number} ({product_name}): STANDARD UNAVAILABLE — no pitch target"
                    ),
                    actual,
                    "units",
                ));
            }
        }
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

/// Buyer view (item 29): supplier commitments — open purchase orders and
/// the past-due ones that need expediting. NOTE: `purchase_orders` carries
/// no site column in this tree, so the tenant + required-site gate
/// (item 31) is the available boundary; when POs gain a site column the
/// site_id binding belongs here.
async fn collect_buyer_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let (open_pos, past_due): (i64, i64) = sqlx::query_as(
        "SELECT COUNT(*)::bigint, \
                COUNT(*) FILTER (WHERE COALESCE(po.expected_delivery, po.expected_date) < NOW())::bigint \
         FROM purchase_orders po \
         WHERE po.tenant_id = $1 \
           AND po.status NOT IN ('received', 'cancelled', 'closed')",
    )
    .bind(tenant_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: buyer open POs: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "open purchase orders",
        open_pos as f64,
        "PO",
    ));
    a.now.push(AnalyticLine::fact(
        "purchase orders past due (expedite count)",
        past_due as f64,
        "PO",
    ));
    if past_due > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "purchase orders past due (expedite count)",
            past_due as f64,
            "PO",
        ));
    }

    type PastDueRow = (String, DateTime<Utc>);
    let past_due_pos: Vec<PastDueRow> = sqlx::query_as(
        "SELECT po.po_number, COALESCE(po.expected_delivery, po.expected_date) \
         FROM purchase_orders po \
         WHERE po.tenant_id = $1 \
           AND po.status NOT IN ('received', 'cancelled', 'closed') \
           AND COALESCE(po.expected_delivery, po.expected_date) < NOW() \
         ORDER BY COALESCE(po.expected_delivery, po.expected_date) ASC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: buyer past-due POs: {e}")))?;

    for (po_number, due) in &past_due_pos {
        a.why.push(
            AnalyticLine::fact(
                format!(
                    "PO {po_number} was due {due} and is still open — the supplier commitment was missed"
                ),
                1.0,
                "PO",
            )
            .with_date(*due),
        );
        a.next.push(format!("expedite PO {po_number}"));
    }

    let _ = site_id;
    Ok(())
}

/// Material-controller view (item 29): line starvation risk — open work
/// orders whose product has ZERO inventory balance (the simplified
/// starvation proxy: no stock to pull from).
async fn collect_material_controller_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let starved_count: i64 = sqlx::query_scalar(
        "SELECT COUNT(*)::bigint \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND COALESCE(p.quantity_on_hand, 0) <= 0 \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3)",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: starvation risk: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "work orders at starvation risk",
        starved_count as f64,
        "WO",
    ));
    if starved_count > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "work orders at starvation risk",
            starved_count as f64,
            "WO",
        ));
        a.why.push(AnalyticLine::fact(
            format!(
                "{starved_count} open work orders have zero stock for their product — the line can starve"
            ),
            starved_count as f64,
            "WO",
        ));
    }

    type StarvedRow = (String, String, f64);
    let starved: Vec<StarvedRow> = sqlx::query_as(
        "SELECT wo.wo_number, p.name, p.quantity_on_hand \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND COALESCE(p.quantity_on_hand, 0) <= 0 \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
         ORDER BY wo.created_at ASC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: starvation list: {e}")))?;

    for (wo_number, product, stock) in &starved {
        a.why.push(AnalyticLine::fact(
            format!(
                "WO {wo_number} ({product}) has {stock} on hand — material must be pulled before it starts"
            ),
            1.0,
            "WO",
        ));
        a.next
            .push(format!("release material for {product} (WO {wo_number})"));
    }

    Ok(())
}

/// NPI view (item 29): readiness proxy — open work orders for products
/// created less than 90 days ago (the newest products are the least
/// likely to have proven, stable standard work).
async fn collect_npi_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let new_product_count: i64 = sqlx::query_scalar(
        "SELECT COUNT(*)::bigint \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND p.created_at >= NOW() - interval '90 days' \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3)",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: npi readiness: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "open work orders on products under 90 days old",
        new_product_count as f64,
        "WO",
    ));
    if new_product_count > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "open work orders on products under 90 days old",
            new_product_count as f64,
            "WO",
        ));
    }

    type NewProductRow = (String, String, DateTime<Utc>);
    let new_products: Vec<NewProductRow> = sqlx::query_as(
        "SELECT wo.wo_number, p.name, p.created_at \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND p.created_at >= NOW() - interval '90 days' \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
         ORDER BY p.created_at ASC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: npi list: {e}")))?;

    for (wo_number, product, created_at) in &new_products {
        a.why.push(
            AnalyticLine::fact(
                format!(
                    "WO {wo_number} runs {product}, a product only {created_at} — the process may not be ready"
                ),
                1.0,
                "WO",
            )
            .with_date(*created_at),
        );
        a.next
            .push(format!("verify standard work exists for {product}"));
    }

    Ok(())
}

/// Finance view (item 29): scrap at standard cost — scrapped quantity on
/// work orders multiplied by the product's standard cost (the
/// premium-freight-style proxy: defects carry real, quantified cost).
async fn collect_finance_view(
    pool: &PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let (scrap_units, scrap_value): (i64, f64) = sqlx::query_as(
        "SELECT COALESCE(SUM(wo.quantity_scrapped), 0)::bigint, \
                COALESCE(SUM(wo.quantity_scrapped * COALESCE(p.standard_cost, 0)), 0)::float8 \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status <> 'cancelled' \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3)",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_one(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: scrap value: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "scrap units on work orders",
        scrap_units as f64,
        "units",
    ));
    a.now.push(AnalyticLine::fact(
        "scrap value at standard cost",
        scrap_value,
        "USD",
    ));
    if scrap_units > 0 {
        a.abnormal.push(AnalyticLine::fact(
            "scrap value at standard cost",
            scrap_value,
            "USD",
        ));
        a.why.push(AnalyticLine::fact(
            format!(
                "{scrap_units} units scrapped ≈ ${scrap_value:.2} at standard cost — defects carry real cost"
            ),
            scrap_value,
            "USD",
        ));
    }

    type ScrapRow = (String, String, i64, Option<f64>);
    let scrap: Vec<ScrapRow> = sqlx::query_as(
        "SELECT wo.wo_number, p.name, wo.quantity_scrapped, p.standard_cost \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status <> 'cancelled' \
           AND wo.quantity_scrapped > 0 \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
         ORDER BY wo.quantity_scrapped DESC NULLS LAST \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_all(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: scrap list: {e}")))?;

    for (wo_number, product, qty, cost) in &scrap {
        let value = *qty as f64 * cost.unwrap_or(0.0);
        a.why.push(AnalyticLine::fact(
            format!(
                "WO {wo_number} ({product}) scrapped {qty} units ≈ ${value:.2} at standard cost"
            ),
            *qty as f64,
            "units",
        ));
        a.next
            .push(format!("investigate the scrap cause on WO {wo_number}"));
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
