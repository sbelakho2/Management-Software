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
use chrono::{DateTime, Duration, Utc};
use sensei_core::db::tenant_tx::TenantTx;
use sensei_core::domain::value_objects::{CurrencyCode, Money};
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
/// A deterministic analytic line. `epistemic_status` distinguishes
/// MEASURED facts from INFERENCES: takt-derived expectations ("the line
/// is losing pitch") are hypotheses drawn from standard work, never
/// facts — a hypothesis must be confirmed at the line before acting
/// (sixteenth audit item: no fabricated pitch).
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
    #[serde(default = "default_epistemic_status")]
    pub epistemic_status: String,
}

fn default_epistemic_status() -> String {
    "fact".to_string()
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
            epistemic_status: "fact".to_string(),
        }
    }

    /// An INFERENCE from standard work (takt × elapsed time) — the label
    /// itself states the hypothesis so the reader can verify at the line.
    fn hypothesis(label: impl Into<String>, actual: f64, unit: impl Into<String>) -> Self {
        Self {
            epistemic_status: "hypothesis".to_string(),
            ..Self::fact(label, actual, unit)
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
    "buyer",
    "material_controller",
    "npi",
    "finance",
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
/// denies unscoped calls before any query runs. EVERY read runs inside
/// ONE [`TenantTx`] (sixteenth audit items 21/83): the RLS tenant context
/// is construction-time — a raw-pool read would depend on connection/RLS
/// configuration instead of the typed handle.
pub async fn build_role_analytics(
    pool: &PgPool,
    tenant_id: Uuid,
    role: &str,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
) -> Result<RoleAnalytics> {
    require_scope(role, site_id, work_center_id)?;

    let mut ttx = TenantTx::begin(pool, tenant_id)
        .await
        .map_err(|e| SenseiError::Database(format!("role analytics: begin tenant tx: {e}")))?;

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
            collect_work_center_view(&mut ttx, tenant_id, site_id, work_center_id, &mut analytics)
                .await?;
        }
        // Site roles: the aggregate flow view of the caller's site.
        "manager" | "site_manager" | "quality" | "planner" | "supervisor" => {
            collect_site_view(&mut ttx, tenant_id, site_id, work_center_id, &mut analytics).await?;
        }
        // Distinct supply/finance/readiness roles (item 29).
        "buyer" => collect_buyer_view(&mut ttx, tenant_id, site_id, &mut analytics).await?,
        "material_controller" => {
            collect_material_controller_view(
                &mut ttx,
                tenant_id,
                site_id,
                work_center_id,
                &mut analytics,
            )
            .await?;
        }
        "npi" => {
            collect_npi_view(&mut ttx, tenant_id, site_id, work_center_id, &mut analytics).await?;
        }
        "finance" => {
            collect_finance_view(&mut ttx, tenant_id, site_id, work_center_id, &mut analytics)
                .await?;
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
    collect_conditions(&mut ttx, tenant_id, site_id, work_center_id, &mut analytics).await?;

    ttx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("role analytics: commit tenant tx: {e}")))?;

    Ok(analytics)
}

/// Operator/team-lead view: the caller's own work center — andons, pitch
/// gaps, today's production, material starvation, skill coverage, last
/// abnormality. Every query is restricted by work_center_id (or site) and
/// runs on the shared [`TenantTx`].
async fn collect_work_center_view(
    ttx: &mut TenantTx<'_>,
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
        .fetch_all(&mut **ttx.tx())
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
    // with no usable takt means NO target (seventeenth audit item 14 —
    // an invented 60s expectation is never presented as plan-vs-actual),
    // and a MISSING standard means no pitch target exists at all
    // (STANDARD UNAVAILABLE guidance).
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
        .fetch_all(&mut **ttx.tx())
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
        // Seventeenth audit item 14: never manufacture a standard — a
        // missing standard OR a missing usable takt yields NO target
        // (the WHY line states the target is unavailable, so the UI can
        // never present an invented 60s expectation as plan-vs-actual).
        let expected = standard_id.zip(takt.filter(|t| *t > 0)).map(|(_, takt)| {
            let takt_seconds = takt as f64;
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
                    a.why.push(AnalyticLine::hypothesis(
                        format!(
                            "HYPOTHESIS — WO {wo_number} ({product_name}) is behind pitch: \
                             {completed} units completed vs ~{target:.1} expected at a {:.0}s takt; \
                             verify the line before acting",
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
    .fetch_one(&mut **ttx.tx())
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
    // The catalog probe stays readable for any role; the tenant-domain
    // count itself runs on the TenantTx (admitted by RLS).
    let skills_readable: bool = sqlx::query_scalar(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'employee_skills') \
            AND EXISTS (SELECT 1 FROM information_schema.columns \
                        WHERE table_name = 'employee_skills' AND column_name = 'work_center_id')",
    )
    .fetch_one(&mut **ttx.tx())
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
        .fetch_one(&mut **ttx.tx())
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
    .fetch_optional(&mut **ttx.tx())
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
    ttx: &mut TenantTx<'_>,
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
    .fetch_one(&mut **ttx.tx())
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
    .fetch_one(&mut **ttx.tx())
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
    .fetch_one(&mut **ttx.tx())
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
    .fetch_one(&mut **ttx.tx())
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
    .fetch_all(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: andon numbers: {e}")))?;

    for number in &open_andon_numbers {
        a.next.push(format!("respond to andon {number}"));
    }

    Ok(())
}

/// Buyer view (item 29): supplier commitments — open purchase orders and
/// the past-due ones that need expediting. Eighteenth audit P1-10: the
/// purchase-order domain carries NO site linkage in this tree
/// (`purchase_orders`, `suppliers`, `purchase_order_items` and `products`
/// all lack `site_id`), so there is NO site-filterable PO query — the
/// section FAILS CLOSED (`not_available_site_required`) instead of
/// returning tenant-wide purchase orders to a site-scoped buyer.
async fn collect_buyer_view(
    ttx: &mut TenantTx<'_>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    // Twentieth audit P1/P2: purchase_orders now carry receiving_site_id
    // (migration 152) — the buyer view is scoped honestly. A site-scoped
    // caller sees exactly their plant's procurement; a caller without a
    // site scope still fails closed (tenant-wide PO numbers are never
    // surfaced).
    let boundary = match site_id {
        Some(id) => format!("site {id}"),
        None => "no site scope".to_string(),
    };
    let Some(site_id) = site_id else {
        a.now.push(AnalyticLine::fact(
            "purchase order analytics",
            0.0,
            "not_available_site_required",
        ));
        a.why.push(AnalyticLine::fact(
            format!(
                "purchase orders are site-scoped (receiving_site_id) — open/past-due PO \
                 counts need a site; none is available for {boundary}"
            ),
            0.0,
            "not_available_site_required",
        ));
        return Ok(());
    };

    let (open_count, past_due_count): (i64, i64) = sqlx::query_as(
        "SELECT COUNT(*) FILTER (WHERE po.status NOT IN ('received','closed','cancelled'))::bigint, \
                COUNT(*) FILTER (WHERE po.status NOT IN ('received','closed','cancelled') \
                                 AND po.expected_date IS NOT NULL \
                                 AND COALESCE(po.expected_delivery, po.expected_date) \
                                      < NOW())::bigint \
         FROM purchase_orders po \
         WHERE po.tenant_id = $1 AND po.receiving_site_id = $2",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_one(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: buyer PO scope: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "open purchase orders",
        open_count as f64,
        "PO",
    ));
    a.why.push(AnalyticLine::fact(
        format!(
            "{past_due_count} open purchase order(s) for this site are PAST DUE              (expected date passed) — {boundary}"
        ),
        past_due_count as f64,
        "PO",
    ));
    a.next.push(format!(
        "expedite the {past_due_count} past-due purchase order(s) for this site"
    ));
    Ok(())
}

/// Material-controller view (item 29): line starvation risk — open work
/// orders whose SITE-level inventory cannot cover the remaining requirement.
/// Eighteenth audit P1-10: starvation is judged on `inventory_items` at the
/// site (migration 112 added `inventory_items.site_id`), never on
/// tenant-wide `products.quantity_on_hand`. The table carries
/// `quantity_on_hand` and `quantity_reserved` (no quarantine column), so
/// available = SUM(quantity_on_hand − quantity_reserved) at the site; no
/// site-scoped inbound data exists (`purchase_orders` is not site-linked),
/// so inbound is NOT added. The requirement is the open WO's remaining
/// units (`quantity − quantity_completed`) at the site.
async fn collect_material_controller_view(
    ttx: &mut TenantTx<'_>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    // Twenty-first audit item 12: REAL material starvation is
    // COMPONENT-level, exploded from the BOM — the finished-good proxy
    // is gone. demand(component) = SUM over open WOs of (remaining ×
    // bom.quantity); a WO starves when ANY of its components' demand
    // exceeds the site's available (on hand − reserved) inventory.
    let starved_count: i64 = sqlx::query_scalar(
        "WITH wo_open AS ( \
             SELECT wo.id, wo.product_id, \
                    (wo.quantity - COALESCE(wo.quantity_completed, 0))::double precision AS remaining \
             FROM work_orders wo \
             WHERE wo.tenant_id = $1 \
               AND wo.status IN ('created', 'released', 'in_progress') \
               AND ($2::uuid IS NULL OR wo.site_id = $2) \
               AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
               AND (wo.quantity - COALESCE(wo.quantity_completed, 0)) > 0 \
         ), \
         avail AS ( \
             SELECT ii.product_id, \
                    COALESCE(SUM(ii.quantity_on_hand - ii.quantity_reserved), 0)::double precision AS available \
             FROM inventory_items ii \
             WHERE ii.tenant_id = $1 AND ($2::uuid IS NULL OR ii.site_id = $2) \
             GROUP BY ii.product_id \
         ), \
         demand AS ( \
             SELECT b.component_product_id, \
                    SUM(w.remaining * b.quantity)::double precision AS needed \
             FROM wo_open w \
             JOIN bom_items b ON b.parent_product_id = w.product_id \
              AND b.tenant_id = $1 AND b.is_active = TRUE \
             GROUP BY b.component_product_id \
         ), \
         shortage AS ( \
             SELECT d.component_product_id, \
                    (d.needed - COALESCE(a.available, 0))::double precision AS deficit \
             FROM demand d \
             LEFT JOIN avail a ON a.product_id = d.component_product_id \
             WHERE d.needed > COALESCE(a.available, 0) \
         ) \
         SELECT COUNT(DISTINCT w.id)::bigint \
         FROM wo_open w \
         JOIN bom_items b ON b.parent_product_id = w.product_id \
          AND b.tenant_id = $1 AND b.is_active = TRUE \
         JOIN shortage s ON s.component_product_id = b.component_product_id",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_one(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: BOM starvation risk: {e}")))?;

    // The top shortage COMPONENTS (with deficits) so the material
    // controller knows WHAT to expedite, not just how many WOs starve.
    let deficits: Vec<(String, f64)> = sqlx::query_as(
        "WITH wo_open AS ( \
             SELECT wo.id, wo.product_id, \
                    (wo.quantity - COALESCE(wo.quantity_completed, 0))::double precision AS remaining \
             FROM work_orders wo \
             WHERE wo.tenant_id = $1 \
               AND wo.status IN ('created', 'released', 'in_progress') \
               AND ($2::uuid IS NULL OR wo.site_id = $2) \
               AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
               AND (wo.quantity - COALESCE(wo.quantity_completed, 0)) > 0 \
         ), \
         avail AS ( \
             SELECT ii.product_id, \
                    COALESCE(SUM(ii.quantity_on_hand - ii.quantity_reserved), 0)::double precision AS available \
             FROM inventory_items ii \
             WHERE ii.tenant_id = $1 AND ($2::uuid IS NULL OR ii.site_id = $2) \
             GROUP BY ii.product_id \
         ), \
         demand AS ( \
             SELECT b.component_product_id, \
                    SUM(w.remaining * b.quantity)::double precision AS needed \
             FROM wo_open w \
             JOIN bom_items b ON b.parent_product_id = w.product_id \
              AND b.tenant_id = $1 AND b.is_active = TRUE \
             GROUP BY b.component_product_id \
         ) \
         SELECT p.name, \
                (d.needed - COALESCE(a.available, 0))::float8 \
         FROM demand d \
         JOIN products p ON p.id = d.component_product_id AND p.tenant_id = $1 \
         LEFT JOIN avail a ON a.product_id = d.component_product_id \
         WHERE d.needed > COALESCE(a.available, 0) \
         ORDER BY (d.needed - COALESCE(a.available, 0)) DESC LIMIT 5",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_all(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: shortage components: {e}")))?;

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
                "{starved_count} open work orders cannot be covered by site inventory — the line can starve"
            ),
            starved_count as f64,
            "WO",
        ));
    }

    // The shortage COMPONENTS with their deficits (BOM-exploded) drive
    // the WHY/NEXT lines — the material controller sees WHAT to expedite.
    for (component, deficit) in &deficits {
        a.why.push(AnalyticLine::fact(
            format!(
                "component '{component}' is short by {deficit:.0} units against the \
                 BOM-exploded demand of open work orders at this site"
            ),
            *deficit,
            "units",
        ));
        a.next.push(format!(
            "expedite/allocate '{component}' before the line runs out"
        ));
    }
    if starved_count == 0 {
        a.why.push(AnalyticLine::fact(
            "no BOM-exploded component shortage for the open work orders in scope".to_string(),
            0.0,
            "units",
        ));
    }

    Ok(())
}

/// NPI view (item 29): readiness — for every open work order's product,
/// the NPI readiness is the fraction of REAL readiness signals that exist
/// in the schema: BOM (`bom_items`), route (`routings`), PFMEA
/// (`pfmea_lite`), control plan (`control_plans`), first article
/// (`first_article_inspections`) and process capability
/// (`process_capability_studies`). Eighteenth audit P1-10: the 90-day
/// product-age heuristic is NO LONGER the primary signal — a product with
/// no signal at all is `insufficient_evidence`, not "at risk because
/// young"; age is kept only as a minor secondary note.
const NPI_SIGNALS: [&str; 6] = [
    "BOM",
    "route",
    "PFMEA",
    "control plan",
    "first article",
    "process capability",
];

async fn collect_npi_view(
    ttx: &mut TenantTx<'_>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    type ReadinessRow = (
        String,
        String,
        DateTime<Utc>,
        bool,
        bool,
        bool,
        bool,
        bool,
        bool,
    );
    let readiness_rows: Vec<ReadinessRow> = sqlx::query_as(
        "SELECT wo.wo_number, p.name, p.created_at, \
                EXISTS (SELECT 1 FROM bom_items b \
                        WHERE b.parent_product_id = wo.product_id AND b.is_active) AS has_bom, \
                EXISTS (SELECT 1 FROM routings r \
                        WHERE r.product_id = wo.product_id AND r.is_active) AS has_route, \
                EXISTS (SELECT 1 FROM pfmea_lite f WHERE f.product_id = wo.product_id \
                        AND f.status IN ('completed','closed')) AS has_pfmea, \
                EXISTS (SELECT 1 FROM control_plans c WHERE c.product_id = wo.product_id \
                        AND c.status = 'active') AS has_control_plan, \
                EXISTS (SELECT 1 FROM first_article_inspections fai \
                        WHERE fai.product_id = wo.product_id \
                          AND fai.status = 'completed' AND fai.result = 'passed') AS has_fai, \
                EXISTS (SELECT 1 FROM process_capability_studies pcs \
                        WHERE pcs.product_id = wo.product_id \
                          AND pcs.ppk >= 1.33) AS has_capability \
         FROM work_orders wo \
         JOIN products p ON p.id = wo.product_id AND p.tenant_id = wo.tenant_id \
         WHERE wo.tenant_id = $1 \
           AND wo.status IN ('created', 'released', 'in_progress') \
           AND ($2::uuid IS NULL OR wo.site_id = $2) \
           AND ($3::uuid IS NULL OR wo.work_center_id = $3) \
         ORDER BY wo.created_at ASC \
         LIMIT 10",
    )
    .bind(tenant_id)
    .bind(site_id)
    .bind(work_center_id)
    .fetch_all(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: npi readiness: {e}")))?;

    a.now.push(AnalyticLine::fact(
        "products in NPI readiness review",
        readiness_rows.len() as f64,
        "product",
    ));

    for (wo_number, product, created_at, has_bom, has_route, has_pfmea, has_cp, has_fai, has_cap) in
        &readiness_rows
    {
        let present = [
            *has_bom, *has_route, *has_pfmea, *has_cp, *has_fai, *has_cap,
        ];
        let count = present.iter().filter(|b| **b).count();
        let missing: Vec<&str> = NPI_SIGNALS
            .iter()
            .zip(&present)
            .filter(|(_, present)| !**present)
            .map(|(name, _)| *name)
            .collect();
        // Readiness is the fraction of signals that EXIST for the product;
        // zero signals is `insufficient_evidence` — never an at-risk verdict
        // derived from product age.
        let status = match count {
            0 => "insufficient_evidence",
            6 => "ready",
            3..=5 => "partially_ready",
            _ => "at_risk",
        };
        let line = AnalyticLine::fact(
            format!("NPI readiness {product} ({status})"),
            count as f64,
            "signals",
        )
        .with_delta(6.0, count as f64)
        .with_date(*created_at);
        a.now.push(line.clone());
        if status == "at_risk" {
            a.abnormal.push(line);
        }

        // Minor secondary note only: product age is context, never the
        // primary readiness signal.
        let young = *created_at >= Utc::now() - Duration::days(90);
        let missing_text = if missing.is_empty() {
            "none".to_string()
        } else {
            missing.join(", ")
        };
        let mut why_text = format!(
            "WO {wo_number} runs {product}: NPI readiness {count}/6 signals present ({status}) — \
             missing: {missing_text}"
        );
        if young {
            why_text.push_str("; the product is under 90 days old (secondary note)");
        }
        a.why
            .push(AnalyticLine::fact(why_text, count as f64, "signals").with_date(*created_at));
        a.next.push(format!(
            "complete the missing NPI readiness signals for {product}: {missing_text}"
        ));
    }

    Ok(())
}

/// Map an ISO-4217 code from `country_policies.currency` onto the typed
/// [`CurrencyCode`]. Codes the value object does not cover (the policy
/// seeds include 'TND') fall back to `None` — the analytics then carry NO
/// currency label instead of assuming USD (eighteenth audit P1-10).
fn currency_code_from_iso(code: &str) -> Option<CurrencyCode> {
    match code {
        "USD" => Some(CurrencyCode::USD),
        "EUR" => Some(CurrencyCode::EUR),
        "GBP" => Some(CurrencyCode::GBP),
        "MAD" => Some(CurrencyCode::MAD),
        "JPY" => Some(CurrencyCode::JPY),
        "CNY" => Some(CurrencyCode::CNY),
        _ => None,
    }
}

/// The site's currency: `sites.country` → `country_policies.currency`
/// (eighteenth audit P1-10 — money is never hardcoded "USD"). `None` when
/// the site has no country, no policy row, or the code is unknown.
async fn site_currency_code(
    ttx: &mut TenantTx<'_>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
) -> Result<Option<CurrencyCode>> {
    let Some(site_id) = site_id else {
        return Ok(None);
    };
    let country: Option<String> =
        sqlx::query_scalar("SELECT country FROM sites WHERE id = $1 AND tenant_id = $2")
            .bind(site_id)
            .bind(tenant_id)
            .fetch_optional(&mut **ttx.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("role analytics: site country: {e}")))?;
    let Some(country) = country else {
        return Ok(None);
    };
    let currency: Option<String> = sqlx::query_scalar(
        "SELECT currency FROM country_policies WHERE tenant_id = $1 AND country = $2",
    )
    .bind(tenant_id)
    .bind(&country)
    .fetch_optional(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: country currency: {e}")))?;
    Ok(currency.as_deref().and_then(currency_code_from_iso))
}

/// Finance view (item 29): scrap at standard cost — scrapped quantity on
/// work orders multiplied by the product's standard cost (the
/// premium-freight-style proxy: defects carry real, quantified cost).
/// Eighteenth audit P1-10: the value carries the SITE's currency from
/// `country_policies` via the typed [`Money`] value object (never a
/// hardcoded "USD"/"$"), and nonzero scrap is compared against the
/// `scrap_rate` standard when a target exists; without a standard it is a
/// `no_standard` NOTE, never "abnormal".
async fn collect_finance_view(
    ttx: &mut TenantTx<'_>,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    work_center_id: Option<Uuid>,
    a: &mut RoleAnalytics,
) -> Result<()> {
    let (scrap_units, completed_units, scrap_value): (i64, i64, rust_decimal::Decimal) =
        sqlx::query_as(
            "SELECT COALESCE(SUM(wo.quantity_scrapped), 0)::bigint, \
                COALESCE(SUM(wo.quantity_completed), 0)::bigint, \
                COALESCE(SUM(wo.quantity_scrapped * COALESCE(p.standard_cost, 0)), 0)::numeric \
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
        .fetch_one(&mut **ttx.tx())
        .await
        .map_err(|e| SenseiError::Database(format!("role analytics: scrap value: {e}")))?;

    let currency = site_currency_code(ttx, tenant_id, site_id).await?;
    // The aggregate is Decimal end-to-end; the f64 boundary exists only
    // at the Money constructor (cents math) — never in the query path.
    let money = currency
        .map(|cc| Money::from_decimal_decimal(scrap_value, cc))
        .transpose()?;
    let value_unit = match money {
        Some(m) => m.currency.as_str().to_string(),
        None => "standard-cost value (currency not configured)".to_string(),
    };
    let value_text = match money {
        Some(m) => m.to_string(),
        None => format!("{scrap_value:.2}"),
    };

    a.now.push(AnalyticLine::fact(
        "scrap units on work orders",
        scrap_units as f64,
        "units",
    ));
    a.now.push(AnalyticLine::fact(
        "scrap value at standard cost",
        rust_decimal::prelude::ToPrimitive::to_f64(&scrap_value).unwrap_or(0.0),
        value_unit,
    ));
    if scrap_units > 0 {
        // The scrap standard: metric_definitions has NO target column in
        // this tree (checked via information_schema — the probe keeps the
        // comparison honest if a target appears later), so the `scrap_rate`
        // metric cannot supply a number. Nonzero scrap without a standard
        // is a `no_standard` NOTE, never an abnormality.
        let has_target_column: bool = sqlx::query_scalar(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns \
                            WHERE table_name = 'metric_definitions' AND column_name = 'target')",
        )
        .fetch_one(&mut **ttx.tx())
        .await
        .unwrap_or(false);
        let scrap_rate_target: Option<f64> = if has_target_column {
            sqlx::query_scalar::<_, Option<f64>>(
                "SELECT target FROM metric_definitions \
                 WHERE tenant_id = $1 AND metric_id = 'scrap_rate' AND active \
                 ORDER BY version DESC LIMIT 1",
            )
            .bind(tenant_id)
            .fetch_optional(&mut **ttx.tx())
            .await
            .map_err(|e| SenseiError::Database(format!("role analytics: scrap rate target: {e}")))?
            .flatten()
        } else {
            None
        };

        let produced = scrap_units + completed_units;
        let rate = if produced > 0 {
            scrap_units as f64 / produced as f64
        } else {
            1.0
        };
        match scrap_rate_target {
            Some(target) => {
                if rate > target {
                    a.abnormal.push(
                        AnalyticLine::fact("scrap rate vs standard", rate, "%")
                            .with_delta(target, rate),
                    );
                    a.why.push(AnalyticLine::fact(
                        format!(
                            "scrap rate {:.1}% exceeds the {:.1}% standard — defects carry real cost \
                             ({value_text} at standard cost)",
                            rate * 100.0,
                            target * 100.0,
                        ),
                        rate,
                        "%",
                    ));
                } else {
                    a.why.push(AnalyticLine::fact(
                        format!(
                            "scrap rate {:.1}% is within the {:.1}% standard",
                            rate * 100.0,
                            target * 100.0,
                        ),
                        rate,
                        "%",
                    ));
                }
            }
            None => {
                a.why.push(AnalyticLine::fact(
                    format!(
                        "{scrap_units} units scrapped ≈ {value_text} at standard cost — no_standard: \
                         no scrap_rate target is defined, so this is a note, not an abnormality"
                    ),
                    rust_decimal::prelude::ToPrimitive::to_f64(&scrap_value).unwrap_or(0.0),
                    "standard-cost value",
                ));
            }
        }
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
    .fetch_all(&mut **ttx.tx())
    .await
    .map_err(|e| SenseiError::Database(format!("role analytics: scrap list: {e}")))?;

    for (wo_number, product, qty, cost) in &scrap {
        let value = *qty as f64 * cost.unwrap_or(0.0);
        let line_value = currency
            .map(|cc| Money::from_decimal(value, cc))
            .transpose()?
            .map(|m| m.to_string())
            .unwrap_or_else(|| format!("{value:.2}"));
        a.why.push(AnalyticLine::fact(
            format!(
                "WO {wo_number} ({product}) scrapped {qty} units ≈ {line_value} at standard cost"
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
    ttx: &mut TenantTx<'_>,
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
    .fetch_all(&mut **ttx.tx())
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
    .fetch_all(&mut **ttx.tx())
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
