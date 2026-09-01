//! TWI skill graph (fifteenth audit 37-39): skill levels with evidence
//! and recency; turnover-resilience metrics (bus factor, trainer
//! coverage, single-person knowledge concentration).
//!
//! The vulnerability "Shift 2 is technically staffed but only one person
//! can independently run AOI programming" must be DETECTABLE: coverage
//! reports the number of principals who can run a skill independently
//! (`bus_factor`) and flags `single_point` when that number is exactly
//! one.
use sensei_core::error::{Result, SenseiError};
use uuid::Uuid;

/// The TWI skill ladder: a principal is observed, demonstrates, runs
/// supervised, then independently, and finally trains others. Promotion
/// is always explicit evidence-based (see [`record_qualification`]).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SkillLevel {
    Unexposed,
    Learning,
    Supervised,
    Independent,
    Trainer,
}

impl SkillLevel {
    /// The ordinal position on the ladder (0..4).
    pub fn rank(self) -> i64 {
        match self {
            SkillLevel::Unexposed => 0,
            SkillLevel::Learning => 1,
            SkillLevel::Supervised => 2,
            SkillLevel::Independent => 3,
            SkillLevel::Trainer => 4,
        }
    }

    /// The storage value (matches the `skill_qualifications.level` CHECK).
    pub fn as_str(self) -> &'static str {
        match self {
            SkillLevel::Unexposed => "unexposed",
            SkillLevel::Learning => "learning",
            SkillLevel::Supervised => "supervised",
            SkillLevel::Independent => "independent",
            SkillLevel::Trainer => "trainer",
        }
    }

    /// Parse the stored level string back into the ladder state (any
    /// unrecognized value degrades to [`SkillLevel::Unexposed`]).
    pub fn from_stored(value: &str) -> SkillLevel {
        match value {
            "learning" => SkillLevel::Learning,
            "supervised" => SkillLevel::Supervised,
            "independent" => SkillLevel::Independent,
            "trainer" => SkillLevel::Trainer,
            _ => SkillLevel::Unexposed,
        }
    }
}

/// Qualification transition state machine (sixteenth audit item 34):
/// only adjacent ladder moves are allowed; a higher state is never
/// overwritten with a lower one without an explicit revocation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QualificationError {
    ImpossibleJump,
    DemotionWithoutRevocation,
    SelfAssessment,
    MissingStandardRevision,
}

impl QualificationError {
    /// The human-readable contract violation behind the error variant.
    fn message(self) -> &'static str {
        match self {
            QualificationError::ImpossibleJump => {
                "impossible skill jump — qualification is a \
                 controlled ladder; exceptional prior competence requires a \
                 RecognitionOfPriorCompetence workflow"
            }
            QualificationError::DemotionWithoutRevocation => {
                "demotion requires an explicit \
                 revocation path — a higher state is never overwritten with a lower one"
            }
            QualificationError::SelfAssessment => "critical skills prohibit self-qualification",
            QualificationError::MissingStandardRevision => {
                "qualification evidence must \
                 reference the exact standard revision, an assessor, observed cycles and checks"
            }
        }
    }
}

pub fn allowed_transition(current: SkillLevel, requested: SkillLevel) -> bool {
    use SkillLevel::*;
    matches!(
        (current, requested),
        (Unexposed, Learning)
            | (Learning, Supervised)
            | (Supervised, Independent)
            | (Independent, Trainer)
    )
}

/// One TWI job step. The `reasons` field is REQUIRED to exist (the WHY is
/// essential to the TWI model) even when it is empty for trivial steps —
/// enforced by serde: a payload missing `reasons` fails to deserialize.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct JobStep {
    pub action: String,
    pub key_points: Vec<String>,
    pub reasons: Vec<String>, // "do X because Y" — the WHY is essential
    pub hazards: Vec<String>,
    pub checks: Vec<String>,
}

/// Validate one job step's TWI shape: the action must be non-empty; the
/// reasons field's EXISTENCE is enforced by the type itself.
pub fn validate_step(step: &JobStep) -> std::result::Result<(), String> {
    if step.action.trim().is_empty() {
        return Err("each job step must have an action".to_string());
    }
    Ok(())
}

/// Coverage for one skill: how many principals can run it independently
/// and how many can train it. `single_point` is the detectable
/// turnover-resilience vulnerability (exactly ONE person can do it).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SkillCoverage {
    pub skill_id: String,
    pub name: String,
    pub critical: bool,
    pub independent_count: i64, // level >= independent
    pub trainer_count: i64,
    pub bus_factor: i64,    // how many can do it independently
    pub single_point: bool, // exactly ONE person can do it
}

// ---------------------------------------------------------------------------
// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id) —
// same convention as ops/database.rs. Every read/write here establishes
// the context: the policies are FAIL-CLOSED (missing context = no rows).
// ---------------------------------------------------------------------------

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

/// Run `f` inside a transaction with the RLS tenant context set.
async fn with_tenant_tx<T, F>(pool: &sqlx::PgPool, tenant_id: Uuid, f: F) -> Result<T>
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

/// Create a skill (idempotent on `(tenant_id, skill_id)` — returns the
/// skill's id either way).
pub async fn create_skill(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    skill_id: &str,
    name: &str,
    process: Option<&str>,
    standard_id: Option<&str>,
    critical: bool,
) -> Result<Uuid> {
    let id = Uuid::new_v4();
    let skill_id = skill_id.to_string();
    let name = name.to_string();
    let process = process.map(str::to_string);
    let standard_id = standard_id.map(str::to_string);
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let inserted: Option<Uuid> = sqlx::query_scalar(
                "INSERT INTO skills (id, tenant_id, skill_id, name, process, standard_id, critical) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7) \
                 ON CONFLICT (tenant_id, skill_id) DO NOTHING \
                 RETURNING id",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(&skill_id)
            .bind(&name)
            .bind(&process)
            .bind(&standard_id)
            .bind(critical)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to create skill: {e}")))?;
            match inserted {
                Some(id) => Ok(id),
                None => sqlx::query_scalar(
                    "SELECT id FROM skills WHERE tenant_id = $1 AND skill_id = $2",
                )
                .bind(tenant_id)
                .bind(&skill_id)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to read skill: {e}")))?
                .ok_or_else(|| {
                    SenseiError::NotFound(format!("Skill {skill_id} not found"))
                }),
            }
        })
    })
    .await
}

/// Create a job standard under a skill (TWI: action/key points/REASONS/
/// hazards/checks). Validates the TWI step shape before writing.
#[allow(clippy::too_many_arguments)]
pub async fn create_job_standard(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    skill_id: &str,
    standard_id: &str,
    revision: i64,
    process: &str,
    title: &str,
    steps: Vec<JobStep>,
) -> Result<Uuid> {
    for step in &steps {
        validate_step(step)
            .map_err(|msg| SenseiError::Validation(format!("Invalid job step: {msg}")))?;
    }
    let steps_json = serde_json::to_value(&steps)
        .map_err(|e| SenseiError::Validation(format!("Invalid steps JSON: {e}")))?;
    let id = Uuid::new_v4();
    let skill_id = skill_id.to_string();
    let standard_id = standard_id.to_string();
    let process = process.to_string();
    let title = title.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // The standard hangs under an existing skill (URL namespace).
            let skill_exists: bool = sqlx::query_scalar(
                "SELECT EXISTS(SELECT 1 FROM skills WHERE tenant_id = $1 AND skill_id = $2)",
            )
            .bind(tenant_id)
            .bind(&skill_id)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to check skill: {e}")))?;
            if !skill_exists {
                return Err(SenseiError::NotFound(format!(
                    "Skill {skill_id} not found"
                )));
            }
            sqlx::query(
                "INSERT INTO job_standards (id, tenant_id, standard_id, revision, process, title, steps) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7) \
                 ON CONFLICT (tenant_id, standard_id, revision) DO NOTHING",
            )
            .bind(id)
            .bind(tenant_id)
            .bind(standard_id)
            .bind(revision)
            .bind(process)
            .bind(title)
            .bind(&steps_json)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to create job standard: {e}")))?;
            Ok(id)
        })
    })
    .await
}

/// Record a demonstration/observation that moves a principal up the
/// skill ladder (observed -> demonstrated -> supervised -> independent ->
/// trainer). Promotion is always explicit evidence-based: every upsert
/// stamps `demonstrated_at = NOW()` and stores the evidence.
///
/// The ladder is a controlled state machine (sixteenth audit item 34):
/// only ADJACENT moves are allowed, a higher state is never overwritten
/// with a lower one without an explicit revocation, and an evidence
/// object must reference the EXACT job-standard revision, an assessor,
/// observed cycles and the checks passed (items 34/35). Critical skills
/// prohibit self-qualification (item 36). Exceptional prior competence
/// can justify a jump via `prior_competence` — the
/// RecognitionOfPriorCompetence bypass — but only into
/// Independent/Trainer, never self-assessed.
#[allow(clippy::too_many_arguments)]
pub async fn record_qualification(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    principal_id: Uuid,
    skill_id: Uuid,
    level: SkillLevel,
    evidence: serde_json::Value,
    prior_competence: Option<serde_json::Value>,
    shift_id: Option<Uuid>,
) -> Result<()> {
    let level_str = level.as_str().to_string();
    let principal_str = principal_id.to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // The CURRENT state is read from storage — the machine is
            // checked against what is actually recorded, not the request.
            let current: SkillLevel = match sqlx::query_scalar::<_, String>(
                "SELECT level FROM skill_qualifications \
                     WHERE tenant_id = $1 AND principal_id = $2 AND skill_id = $3",
            )
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to read qualification: {e}")))?
            {
                Some(level) => SkillLevel::from_stored(&level),
                None => SkillLevel::Unexposed,
            };

            // No-op: re-recording the SAME level changes nothing.
            if current == level {
                return Ok(());
            }
            // Demotion: a higher state is never overwritten with a lower
            // one without an explicit revocation path.
            if level.rank() < current.rank() {
                return Err(SenseiError::Validation(
                    QualificationError::DemotionWithoutRevocation
                        .message()
                        .to_string(),
                ));
            }

            // Whether the skill is critical (item 36: no self-qualification).
            let critical: bool =
                sqlx::query_scalar("SELECT critical FROM skills WHERE tenant_id = $1 AND id = $2")
                    .bind(tenant_id)
                    .bind(skill_id)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to read skill: {e}")))?;

            // Evidence is STRUCTURED (items 34/35): the exact standard
            // revision, an assessor identity, observed cycles (u16) and
            // the checks passed — anything else is not evidence.
            let evidence_valid = |ev: &serde_json::Value| -> bool {
                let Some(obj) = ev.as_object() else {
                    return false;
                };
                let standard_revision = obj
                    .get("standard_revision")
                    .and_then(|v| v.as_str())
                    .is_some_and(|s| !s.is_empty());
                let assessor = obj
                    .get("assessor_id")
                    .and_then(|v| v.as_str())
                    .is_some_and(|s| !s.is_empty());
                let observed_cycles = obj
                    .get("observed_cycles")
                    .and_then(|v| v.as_u64())
                    .is_some_and(|n| n <= u16::MAX as u64);
                let checks_passed = obj.get("checks_passed").is_some_and(|v| v.is_array());
                standard_revision && assessor && observed_cycles && checks_passed
            };
            if !evidence_valid(&evidence) {
                return Err(SenseiError::Validation(
                    QualificationError::MissingStandardRevision
                        .message()
                        .to_string(),
                ));
            }
            // Critical skills prohibit self-qualification (item 36): the
            // assessor must be a DIFFERENT principal.
            if critical {
                let assessor = evidence
                    .get("assessor_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default();
                if assessor == principal_str {
                    return Err(SenseiError::Validation(
                        QualificationError::SelfAssessment.message().to_string(),
                    ));
                }
            }

            // RecognitionOfPriorCompetence bypass (item 34): documented
            // prior competence justifies a jump, but only into
            // Independent/Trainer, and never self-assessed (item 36).
            let prior_competence_bypass = if let Some(pc) = &prior_competence {
                let documented = pc.as_object().is_some_and(|obj| {
                    let assessor = obj
                        .get("assessor_id")
                        .and_then(|v| v.as_str())
                        .is_some_and(|s| !s.is_empty());
                    let standard_revision = obj
                        .get("standard_revision")
                        .and_then(|v| v.as_str())
                        .is_some_and(|s| !s.is_empty());
                    let observed_cycles = obj
                        .get("observed_cycles")
                        .and_then(|v| v.as_u64())
                        .is_some_and(|n| n >= 3);
                    assessor && standard_revision && observed_cycles
                });
                if !documented {
                    return Err(SenseiError::Validation(
                        "prior competence evidence must document an assessor, the exact \
                         standard revision and >= 3 observed cycles"
                            .to_string(),
                    ));
                }
                let pc_assessor = pc
                    .get("assessor_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default();
                if pc_assessor == principal_str {
                    return Err(SenseiError::Validation(
                        "prior competence cannot be self-assessed — the assessor must be a \
                         different principal (audit item 36)"
                            .to_string(),
                    ));
                }
                matches!(level, SkillLevel::Independent | SkillLevel::Trainer)
            } else {
                false
            };

            // The controlled ladder: only adjacent moves, unless the
            // prior-competence bypass documented above applies.
            if !prior_competence_bypass && !allowed_transition(current, level) {
                return Err(SenseiError::Validation(
                    QualificationError::ImpossibleJump.message().to_string(),
                ));
            }

            sqlx::query(
                "INSERT INTO skill_qualifications \
                    (id, tenant_id, principal_id, skill_id, level, demonstrated_at, evidence, shift_id) \
                 VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7) \
                 ON CONFLICT (tenant_id, principal_id, skill_id) DO UPDATE \
                 SET level = EXCLUDED.level, \
                     demonstrated_at = NOW(), \
                     evidence = EXCLUDED.evidence, \
                     shift_id = EXCLUDED.shift_id, \
                     updated_at = NOW()",
            )
            .bind(Uuid::new_v4())
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .bind(&level_str)
            .bind(&evidence)
            .bind(shift_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to record qualification: {e}")))?;
            Ok(())
        })
    })
    .await
}

/// Coverage for every skill in the tenant — the skill graph the
/// leadership sees (fifteenth audit 38). Expired qualifications do not
/// count as independently capable.
pub async fn skill_coverage(pool: &sqlx::PgPool, tenant_id: Uuid) -> Result<Vec<SkillCoverage>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows: Vec<(String, String, bool, i64, i64)> = sqlx::query_as(
                r#"SELECT s.skill_id, s.name, s.critical,
                          COUNT(*) FILTER (WHERE q.level IN ('independent','trainer')
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW())),
                          COUNT(*) FILTER (WHERE q.level = 'trainer'
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW()))
                   FROM skills s
                   LEFT JOIN skill_qualifications q ON q.skill_id = s.id AND q.tenant_id = s.tenant_id
                   WHERE s.tenant_id = $1 GROUP BY s.id, s.skill_id, s.name, s.critical"#,
            )
            .bind(tenant_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Skill coverage failed: {e}")))?;
            Ok(rows
                .into_iter()
                .map(|(skill_id, name, critical, independent_count, trainer_count)| {
                    SkillCoverage {
                        skill_id,
                        name,
                        critical,
                        independent_count,
                        trainer_count,
                        bus_factor: independent_count,
                        single_point: independent_count == 1,
                    }
                })
                .collect())
        })
    })
    .await
}

/// Site/shift-aware coverage (sixteenth audit item 38): the bus factor
/// scoped to one site's role-slot assignment context. The principal's
/// site is derived from their ACTIVE role-slot assignment
/// (`principal_assignments` -> `role_slots.scope_site_id`), so a
/// qualification only counts when the principal is currently assigned to
/// a slot on that site. Qualifications themselves carry no shift — shift
/// awareness is a documented approximation over role-slot assignment
/// context: the `shift` parameter matches the slot name
/// (`role_slots.slot_name LIKE '%' || shift || '%'`, e.g. slots named
/// `Planner_Tangier_A` carry the shift in their name).
pub async fn skill_coverage_at(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    site_id: Option<Uuid>,
    shift_id: Option<Uuid>,
) -> Result<Vec<SkillCoverage>> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            let rows: Vec<(String, String, bool, i64, i64)> = sqlx::query_as(
                r#"SELECT s.skill_id, s.name, s.critical,
                          COUNT(*) FILTER (WHERE q.level IN ('independent','trainer')
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW())
                                           AND ($2::uuid IS NULL OR pa.principal_id IS NOT NULL)),
                          COUNT(*) FILTER (WHERE q.level = 'trainer'
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW())
                                           AND ($2::uuid IS NULL OR pa.principal_id IS NOT NULL))
                   FROM skills s
                   LEFT JOIN skill_qualifications q ON q.skill_id = s.id AND q.tenant_id = s.tenant_id
                         AND ($3::uuid IS NULL OR q.shift_id = $3)
                   LEFT JOIN principal_assignments pa
                          ON pa.principal_id = q.principal_id AND pa.tenant_id = q.tenant_id
                         AND pa.ended_at IS NULL
                         AND ($2::uuid IS NULL OR pa.principal_id IN (
                             SELECT pa2.principal_id FROM principal_assignments pa2
                             JOIN role_slots rs2 ON rs2.id = pa2.slot_id
                             WHERE pa2.ended_at IS NULL AND rs2.scope_site_id = $2))
                   WHERE s.tenant_id = $1
                   GROUP BY s.id, s.skill_id, s.name, s.critical"#,
            )
            .bind(tenant_id)
            .bind(site_id)
            .bind(shift_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Site skill coverage failed: {e}")))?;
            Ok(rows
                .into_iter()
                .map(|(skill_id, name, critical, independent_count, trainer_count)| {
                    SkillCoverage {
                        skill_id,
                        name,
                        critical,
                        independent_count,
                        trainer_count,
                        bus_factor: independent_count,
                        single_point: independent_count == 1,
                    }
                })
                .collect())
        })
    })
    .await
}

/// Turnover resilience (fifteenth audit 39/63): the site-level risk
/// view — how many people can run each critical operation, where
/// knowledge concentrates in ONE person, and whether trainers exist.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct TurnoverRisk {
    pub critical_skills: i64,
    pub single_point_skills: i64, // exactly one independent person
    pub single_point_ratio: f64,
    pub critical_with_2plus: i64,  // the key metric: >= 2 independent
    pub critical_2plus_ratio: f64, // % of critical ops with >= 2 independent
    pub trainer_coverage: f64,     // share of critical skills with >= 1 trainer
    pub knowledge_concentration: Vec<SkillCoverage>, // the single-point list
    pub guidance: Vec<String>,
}

/// The continuous turnover-resilience view (audit item 39): computed
/// from the same skill graph as coverage, always available.
pub async fn turnover_risk(pool: &sqlx::PgPool, tenant_id: Uuid) -> Result<TurnoverRisk> {
    // Reuse skill_coverage (computed over ALL skills with the critical
    // flag, not just critical ones); derive the site-level risk view:
    //   critical_skills = count of critical skills
    //   single_point_skills = count where single_point
    //   critical_with_2plus = count of critical skills with independent_count >= 2
    //   trainer_coverage = critical skills with trainer_count >= 1 / critical_skills
    let coverage = skill_coverage(pool, tenant_id).await?;
    let critical: Vec<&SkillCoverage> = coverage.iter().filter(|c| c.critical).collect();
    let critical_skills = critical.len() as i64;
    let single_point_skills = critical.iter().filter(|c| c.single_point).count() as i64;
    let critical_with_2plus = critical.iter().filter(|c| c.independent_count >= 2).count() as i64;
    let trained = critical.iter().filter(|c| c.trainer_count >= 1).count() as f64;
    let no_trainer = critical.iter().filter(|c| c.trainer_count == 0).count();

    let ratio = |n: i64| -> f64 {
        if critical_skills == 0 {
            0.0
        } else {
            n as f64 / critical_skills as f64
        }
    };

    let mut guidance = Vec::new();
    if single_point_skills > 0 {
        guidance.push(format!(
            "{single_point_skills} critical operation(s) depend on a SINGLE person — cross-train now"
        ));
    }
    if no_trainer > 0 {
        guidance.push(format!(
            "{no_trainer} critical skill(s) have no qualified trainer"
        ));
    }
    if critical_skills > 0 && single_point_skills == 0 && no_trainer == 0 {
        guidance.push("critical operations are covered by >= 2 independent people".to_string());
    }

    Ok(TurnoverRisk {
        critical_skills,
        single_point_skills,
        single_point_ratio: ratio(single_point_skills),
        critical_with_2plus,
        critical_2plus_ratio: ratio(critical_with_2plus),
        trainer_coverage: if critical_skills == 0 {
            0.0
        } else {
            trained / critical_skills as f64
        },
        knowledge_concentration: critical
            .iter()
            .filter(|c| c.single_point)
            .map(|c| (*c).clone())
            .collect(),
        guidance,
    })
}

// ---------------------------------------------------------------------------
// Skill-risk forecasting (fifteenth audit items 39/63 + P3): what happens
// to coverage if ONE principal leaves TOMORROW. Succession gaps are
// detectable BEFORE they happen — the forecast is a what-if over the same
// skill graph, never a verdict.
// ---------------------------------------------------------------------------

/// The what-if view for one departing principal.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DepartureForecast {
    pub departing_principal_id: Uuid,
    pub skills_impacted: Vec<SkillImpact>,
    pub guidance: Vec<String>,
}

/// Coverage impact on one critical skill if the principal leaves.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SkillImpact {
    pub skill_id: String,
    pub name: String,
    pub critical: bool,
    pub independents_before: i64,
    pub independents_after: i64,
    /// The departing principal is the ONLY independent — the skill's
    /// independent coverage collapses to zero when they leave.
    pub becomes_single_point: bool,
    /// At least one qualified trainer remains after the departure.
    pub trainer_remaining: bool,
}

/// Forecast: for every CRITICAL skill the departing principal runs
/// independently (level independent/trainer, not expired), recompute the
/// independent and trainer counts EXCLUDING that principal. Guidance
/// surfaces the succession gaps: "skill X becomes single-point if the
/// principal leaves — cross-train now" / "skill X loses its only
/// trainer".
pub async fn forecast_departure(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    departing_principal_id: Uuid,
) -> Result<DepartureForecast> {
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            // One row per critical skill the principal qualifies on:
            //   before = independents INCLUDING the principal,
            //   after  = independents EXCLUDING the principal,
            //   trainers_after = trainers EXCLUDING the principal.
            let rows: Vec<(String, String, bool, i64, i64, i64)> = sqlx::query_as(
                r#"SELECT s.skill_id, s.name, s.critical,
                          COUNT(*) FILTER (WHERE q.level IN ('independent','trainer')
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW())),
                          COUNT(*) FILTER (WHERE q.level IN ('independent','trainer')
                                           AND q.principal_id <> $2
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW())),
                          COUNT(*) FILTER (WHERE q.level = 'trainer'
                                           AND q.principal_id <> $2
                                           AND (q.expires_at IS NULL OR q.expires_at > NOW()))
                   FROM skills s
                   JOIN skill_qualifications q ON q.skill_id = s.id AND q.tenant_id = s.tenant_id
                   WHERE s.tenant_id = $1 AND s.critical
                     AND EXISTS (
                         SELECT 1 FROM skill_qualifications q2
                         WHERE q2.skill_id = s.id AND q2.tenant_id = s.tenant_id
                           AND q2.principal_id = $2
                           AND q2.level IN ('independent','trainer')
                           AND (q2.expires_at IS NULL OR q2.expires_at > NOW())
                     )
                   GROUP BY s.id, s.skill_id, s.name, s.critical"#,
            )
            .bind(tenant_id)
            .bind(departing_principal_id)
            .fetch_all(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Departure forecast failed: {e}")))?;

            let mut skills_impacted = Vec::new();
            let mut guidance = Vec::new();
            for (skill_id, name, critical, independents_before, independents_after, trainers_after)
                in rows
            {
                let becomes_single_point = independents_before == 1;
                let trainer_remaining = trainers_after > 0;
                if becomes_single_point {
                    guidance.push(format!(
                        "skill {name} becomes single-point if the principal leaves — cross-train now"
                    ));
                }
                if !trainer_remaining {
                    guidance.push(format!("skill {name} loses its only trainer"));
                }
                skills_impacted.push(SkillImpact {
                    skill_id,
                    name,
                    critical,
                    independents_before,
                    independents_after,
                    becomes_single_point,
                    trainer_remaining,
                });
            }
            Ok(DepartureForecast {
                departing_principal_id,
                skills_impacted,
                guidance,
            })
        })
    })
    .await
}
