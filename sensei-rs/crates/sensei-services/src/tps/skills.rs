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
#[allow(clippy::too_many_arguments)]
pub async fn record_qualification(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    principal_id: Uuid,
    skill_id: Uuid,
    level: SkillLevel,
    evidence: serde_json::Value,
) -> Result<()> {
    let level_str = level.as_str().to_string();
    with_tenant_tx(pool, tenant_id, move |tx| {
        Box::pin(async move {
            sqlx::query(
                "INSERT INTO skill_qualifications \
                    (id, tenant_id, principal_id, skill_id, level, demonstrated_at, evidence) \
                 VALUES ($1, $2, $3, $4, $5, NOW(), $6) \
                 ON CONFLICT (tenant_id, principal_id, skill_id) DO UPDATE \
                 SET level = EXCLUDED.level, \
                     demonstrated_at = NOW(), \
                     evidence = EXCLUDED.evidence, \
                     updated_at = NOW()",
            )
            .bind(Uuid::new_v4())
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .bind(&level_str)
            .bind(&evidence)
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
                          COUNT(*) FILTER (WHERE q.level = 'trainer')
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
