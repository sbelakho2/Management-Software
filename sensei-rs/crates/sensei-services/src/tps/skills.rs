//! TWI skill graph (fifteenth audit 37-39): skill levels with evidence
//! and recency; turnover-resilience metrics (bus factor, trainer
//! coverage, single-person knowledge concentration).
//!
//! The vulnerability "Shift 2 is technically staffed but only one person
//! can independently run AOI programming" must be DETECTABLE: coverage
//! reports the number of principals who can run a skill independently
//! (`bus_factor`) and flags `single_point` when that number is exactly
//! one.
//!
//! Multi-shift competency (nineteenth audit item P1): the current state
//! lives in `competency_projection`, keyed by
//! (tenant, principal, skill, site, shift) — one row PER demonstrated
//! site/shift scope, updated by every recorded qualification
//! (source_evidence_id links to the immutable evidence row).
//! `skill_qualifications` keeps the single current level for backward
//! compatibility (its shift_id stays anchored to the FIRST
//! demonstration), and site/shift-aware coverage reads the projection's
//! STRUCTURAL columns instead of the first-shift anchor.
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
/// Every recorded qualification also appends ONE immutable row to
/// `skill_qualification_evidence` (eighteenth audit P1-9) in the same
/// transaction: the standard revision, assessor and evidence object
/// travel verbatim, and the demonstration site/shift context is anchored
/// there — a later qualification on another shift NEVER overwrites the
/// first shift anchor (the conflict path updates level/evidence only).
/// A SAME-LEVEL re-demonstration is NOT discarded (nineteenth audit P1):
/// it appends a further evidence row and refreshes the projection, so a
/// demonstration on Shift B is never lost.
///
/// The CURRENT-STATE projection (`competency_projection`, nineteenth
/// audit P1) is upserted per scope in the same transaction: one row per
/// (site, shift) the principal has demonstrated the skill on, carrying
/// the new level and the new evidence row's id as `source_evidence_id`.
/// The projection site is the resolved demonstration site; a shift-less
/// demonstration falls back to the existing anchor (the FIRST-recorded
/// qualification shift's site, then the principal's active role-slot
/// assignment site) — when nothing is anchored the site stays NULL and
/// coverage resolves it at query time from the assignment.
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
            // The scope for this demonstration (twentieth audit P1): the
            // shift's site when a shift is given; else the first-recorded
            // anchor site; else the active assignment site. Resolved
            // BEFORE the transition decision so the state machine is
            // scoped, never global.
            let scope_site_id: Option<Uuid> = if let Some(shift) = shift_id {
                let site: Option<Option<Uuid>> = sqlx::query_scalar(
                    "SELECT site_id FROM shifts WHERE tenant_id = $1 AND id = $2",
                )
                .bind(tenant_id)
                .bind(shift)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to read demonstration shift: {e}"))
                })?;
                match site.flatten() {
                    Some(site) => Some(site),
                    None => {
                        return Err(SenseiError::Validation(
                            "the demonstration shift does not exist in this tenant".to_string(),
                        ))
                    }
                }
            } else {
                let anchor_site: Option<Option<Uuid>> = sqlx::query_scalar(
                    "SELECT sh.site_id FROM skill_qualifications q \
                     JOIN shifts sh ON sh.id = q.shift_id \
                     WHERE q.tenant_id = $1 AND q.principal_id = $2 AND q.skill_id = $3",
                )
                .bind(tenant_id)
                .bind(principal_id)
                .bind(skill_id)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to read qualification site anchor: {e}"))
                })?;
                match anchor_site.flatten() {
                    Some(site) => Some(site),
                    None => {
                        let assignment_site: Option<Option<Uuid>> = sqlx::query_scalar(
                            "SELECT rs.scope_site_id FROM principal_assignments pa \
                             JOIN role_slots rs ON rs.id = pa.slot_id \
                             WHERE pa.tenant_id = $1 AND pa.principal_id = $2 \
                               AND pa.ended_at IS NULL LIMIT 1",
                        )
                        .bind(tenant_id)
                        .bind(principal_id)
                        .fetch_optional(&mut **tx)
                        .await
                        .map_err(|e| {
                            SenseiError::Database(format!(
                                "Failed to read assignment site anchor: {e}"
                            ))
                        })?;
                        assignment_site.flatten()
                    }
                }
            };

            // Twentieth audit P1: the CURRENT state is read from the
            // SCOPED projection — a Trainer on Shift A never blocks
            // recording Independent on Shift B. The global
            // skill_qualifications row is only the legacy fallback.
            let scoped_current: Option<String> = sqlx::query_scalar(
                "SELECT cp.level FROM competency_projection cp \
                 WHERE cp.tenant_id = $1 AND cp.principal_id = $2 AND cp.skill_id = $3 \
                   AND cp.site_id = $4 \
                   AND cp.shift_id IS NOT DISTINCT FROM $5 \
                   AND cp.valid_until > NOW() AND cp.revoked_at IS NULL \
                 ORDER BY cp.updated_at DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .bind(scope_site_id)
            .bind(shift_id)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to read scoped qualification: {e}"))
            })?;
            let current: SkillLevel = match scoped_current {
                Some(level) => SkillLevel::from_stored(&level),
                None => match sqlx::query_scalar::<_, String>(
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
                },
            };

            // The demonstration SHIFT context (eighteenth audit P1-9): the
            // shift must exist and its site becomes the evidence anchor — a
            // qualification on a shift that does not exist is a validation
            // error.
            let demonstration_site_id = scope_site_id;

            // Same-level re-demonstration (nineteenth audit P1) is a REAL
            // demonstration, not a no-op: it is NOT discarded here — the
            // evidence row and the per-scope projection row are appended
            // below, so multi-shift history accumulates. Only a DEMOTION
            // is rejected: a higher state is never overwritten with a
            // lower one without an explicit revocation path.
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
            // The evidence row's standard revision and assessor identity
            // (P1-9): they travel VERBATIM into the append-only history.
            let standard_revision = evidence
                .get("standard_revision")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string();
            let assessor = evidence
                .get("assessor_id")
                .and_then(|v| v.as_str())
                .unwrap_or_default();
            let assessor_id = Uuid::parse_str(assessor).map_err(|_| {
                SenseiError::Validation(format!(
                    "evidence assessor_id must be a valid UUID: {assessor}"
                ))
            })?;
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

            // The controlled ladder: only adjacent moves (or a SAME-LEVEL
            // re-demonstration, which is not a move), unless the
            // prior-competence bypass documented above applies.
            if current != level && !prior_competence_bypass && !allowed_transition(current, level) {
                return Err(SenseiError::Validation(
                    QualificationError::ImpossibleJump.message().to_string(),
                ));
            }

            // The qualification row is the CURRENT-STATE anchor: the FIRST
            // record pins the shift it was demonstrated on, and the
            // conflict path NEVER touches shift_id (P1-9) — a qualification
            // on Shift B cannot overwrite the Shift A anchor.
            sqlx::query(
                "INSERT INTO skill_qualifications \
                    (id, tenant_id, principal_id, skill_id, level, demonstrated_at, evidence, shift_id) \
                 VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7) \
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
            .bind(shift_id)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to record qualification: {e}")))?;

            // The projection site (nineteenth audit P1): the resolved
            // demonstration site when the record carries a shift;
            // otherwise the existing anchor — the FIRST-recorded
            // qualification shift's site (skill_qualifications pins
            // shift_id on first insert and the conflict path never
            // touches it), then the principal's active role-slot
            // assignment site. Nothing anchored => NULL (coverage
            // resolves the site at query time from the assignment).
            let projection_site_id = match demonstration_site_id {
                Some(site) => Some(site),
                None => {
                    let anchor_site: Option<Option<Uuid>> = sqlx::query_scalar(
                        "SELECT sh.site_id FROM skill_qualifications q \
                         JOIN shifts sh ON sh.id = q.shift_id \
                         WHERE q.tenant_id = $1 AND q.principal_id = $2 AND q.skill_id = $3",
                    )
                    .bind(tenant_id)
                    .bind(principal_id)
                    .bind(skill_id)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!(
                            "Failed to read qualification site anchor: {e}"
                        ))
                    })?;
                    match anchor_site.flatten() {
                        Some(site) => Some(site),
                        None => {
                            let assignment_site: Option<Option<Uuid>> = sqlx::query_scalar(
                                "SELECT rs.scope_site_id FROM principal_assignments pa \
                                 JOIN role_slots rs ON rs.id = pa.slot_id \
                                 WHERE pa.tenant_id = $1 AND pa.principal_id = $2 \
                                   AND pa.ended_at IS NULL \
                                 LIMIT 1",
                            )
                            .bind(tenant_id)
                            .bind(principal_id)
                            .fetch_optional(&mut **tx)
                            .await
                            .map_err(|e| {
                                SenseiError::Database(format!(
                                    "Failed to read assignment site anchor: {e}"
                                ))
                            })?;
                            assignment_site.flatten()
                        }
                    }
                }
            };

            // Append-only evidence history (P1-9): ONE immutable row per
            // recorded qualification — INCLUDING same-level
            // re-demonstrations (nineteenth audit P1) — in the SAME
            // transaction. The demonstration site/shift context survives
            // forever, so multi-shift qualification stays fully
            // representable; the returned id becomes the projection's
            // source_evidence_id.
            let evidence_id: Uuid = sqlx::query_scalar(
                "INSERT INTO skill_qualification_evidence \
                    (tenant_id, principal_id, skill_id, standard_revision, demonstrated_at, \
                     demonstration_site_id, demonstration_shift_id, assessor_id, evidence, \
                     prior_competence) \
                 VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7, $8, $9) \
                 RETURNING id",
            )
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .bind(&standard_revision)
            .bind(demonstration_site_id)
            .bind(shift_id)
            .bind(assessor_id)
            .bind(&evidence)
            .bind(&prior_competence)
            .fetch_one(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to record qualification evidence: {e}"))
            })?;

            // The CURRENT-STATE projection (nineteenth audit P1): one row
            // per (site, shift) scope the principal demonstrated the
            // skill on. The UNIQUE key's nullable components are
            // COALESCEd in the conflict target to match the functional
            // unique index, so the "any site / any shift" bucket
            // UPSERTs instead of growing. Level changes are the only
            // updates — demotion is already rejected above, so the
            // projection never downgrades without revocation.
            sqlx::query(
                "INSERT INTO competency_projection \
                    (tenant_id, principal_id, skill_id, site_id, shift_id, level, \
                     source_evidence_id, valid_from, valid_until, standard_revision, \
                     updated_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), \
                         NOW() + INTERVAL '12 months', $8, NOW()) \
                 ON CONFLICT (tenant_id, principal_id, skill_id, \
                              COALESCE(site_id, '00000000-0000-0000-0000-000000000000'), \
                              COALESCE(shift_id, '00000000-0000-0000-0000-000000000000')) \
                 DO UPDATE SET level = EXCLUDED.level, \
                               source_evidence_id = EXCLUDED.source_evidence_id, \
                               valid_from = EXCLUDED.valid_from, \
                               valid_until = EXCLUDED.valid_until, \
                               standard_revision = EXCLUDED.standard_revision, \
                               updated_at = NOW()",
            )
            .bind(tenant_id)
            .bind(principal_id)
            .bind(skill_id)
            .bind(projection_site_id)
            .bind(shift_id)
            .bind(&level_str)
            .bind(evidence_id)
            .bind(&standard_revision)
            .execute(&mut **tx)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to upsert competency projection: {e}"))
            })?;
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

/// Site/shift-aware coverage (sixteenth audit item 38 + nineteenth audit
/// P1): the bus factor scoped to one site/shift. The scope is now
/// STRUCTURAL — it reads the `competency_projection` rows directly
/// (`cp.site_id` / `cp.shift_id`), never the single first-shift anchor
/// on `skill_qualifications` and never slot-name substring matching.
/// A principal demonstrated on Shift A is visible on Shift A only; a
/// Shift B demonstration adds its own projection row and shifts the
/// coverage. Shift-less projection rows (recorded without a shift and
/// without an anchored site) keep the item-38 semantics: their site
/// resolves at query time from the principal's ACTIVE role-slot
/// assignment (`principal_assignments` -> `role_slots.scope_site_id`).
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
                          COUNT(*) FILTER (WHERE cp.level IN ('independent','trainer')
                                           AND cp.valid_until > NOW()
                                           AND cp.revoked_at IS NULL),
                          COUNT(*) FILTER (WHERE cp.level = 'trainer'
                                           AND cp.valid_until > NOW()
                                           AND cp.revoked_at IS NULL)
                   FROM skills s
                   LEFT JOIN competency_projection cp ON cp.skill_id = s.id AND cp.tenant_id = s.tenant_id
                         AND ($2::uuid IS NULL
                              OR cp.site_id = $2
                              OR (cp.shift_id IS NULL AND cp.site_id IS NULL
                                  AND EXISTS (SELECT 1 FROM principal_assignments pa
                                              JOIN role_slots rs ON rs.id = pa.slot_id
                                              WHERE pa.tenant_id = cp.tenant_id
                                                AND pa.principal_id = cp.principal_id
                                                AND pa.ended_at IS NULL
                                                AND rs.scope_site_id = $2)))
                         AND ($3::uuid IS NULL OR cp.shift_id = $3)
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

#[cfg(test)]
mod tests {
    use super::*;

    /// Connect to the CI-provided test database. Returns None when the env
    /// var is absent so the local suite stays green (the gate runs in CI).
    async fn connect() -> Option<sqlx::PgPool> {
        let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
            eprintln!("SKIP: DATABASE_URL_TEST not set — evidence-history tests run in CI");
            return None;
        };
        sqlx::PgPool::connect(&url).await.ok()
    }

    async fn drop_all_tables(pool: &sqlx::PgPool) {
        sqlx::query(
            r#"DO $$ DECLARE r RECORD; BEGIN
                 FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                     EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
                 END LOOP;
             END $$"#,
        )
        .execute(pool)
        .await
        .expect("drop all tables");
    }

    fn evidence(assessor_id: Uuid) -> serde_json::Value {
        serde_json::json!({
            "standard_revision": "AOI-OP-01/r1",
            "assessor_id": assessor_id.to_string(),
            "observed_cycles": 4,
            "checks_passed": ["program loads"],
        })
    }

    /// Eighteenth audit P1-9: a qualification recorded on Shift B must NOT
    /// overwrite the Shift A anchor. The qualification row keeps the FIRST
    /// recorded shift (the conflict path never touches shift_id), and the
    /// append-only evidence history holds BOTH demonstrations.
    #[tokio::test]
    async fn qualification_history_preserves_both_shift_anchors() {
        let Some(pool) = connect().await else { return };
        drop_all_tables(&pool).await;
        sensei_db::migrations::run_migrations(&pool)
            .await
            .expect("the ENTIRE migration chain must apply to an empty database");

        let tenant_id = Uuid::new_v4();
        let principal_id = Uuid::new_v4();
        let assessor_id = Uuid::new_v4();
        let site_a = Uuid::new_v4();
        let site_b = Uuid::new_v4();
        let shift_a = Uuid::new_v4();
        let shift_b = Uuid::new_v4();

        // Setup (tenants/users/skills carry fail-closed RLS: run under the
        // tenant context).
        with_tenant_tx(&pool, tenant_id, move |tx| {
            Box::pin(async move {
                sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'p1-9', 'p1-9')")
                    .bind(tenant_id)
                    .execute(&mut **tx)
                    .await
                    .expect("tenant insert");
                sqlx::query(
                    "INSERT INTO users (id, tenant_id, email, name, password_hash) \
                     VALUES ($1, $2, 'p@x.local', 'P', 'x')",
                )
                .bind(principal_id)
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("principal insert");
                sqlx::query(
                    "INSERT INTO users (id, tenant_id, email, name, password_hash) \
                     VALUES ($1, $2, 'a@x.local', 'A', 'x')",
                )
                .bind(assessor_id)
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("assessor insert");
                sqlx::query(
                    "INSERT INTO sites (id, tenant_id, site_code, name) \
                     VALUES ($1, $2, 'A', 'Site A'), ($3, $2, 'B', 'Site B')",
                )
                .bind(site_a)
                .bind(tenant_id)
                .bind(site_b)
                .execute(&mut **tx)
                .await
                .expect("sites insert");
                sqlx::query(
                    "INSERT INTO shifts (id, tenant_id, site_id, name, start_time, end_time) \
                     VALUES ($1, $2, $3, 'A', '08:00', '16:00'), \
                            ($4, $2, $5, 'B', '16:00', '00:00')",
                )
                .bind(shift_a)
                .bind(tenant_id)
                .bind(site_a)
                .bind(shift_b)
                .bind(site_b)
                .execute(&mut **tx)
                .await
                .expect("shifts insert");
                Ok(())
            })
        })
        .await
        .expect("setup tx");

        let skill_uuid = create_skill(&pool, tenant_id, "aoi", "AOI", None, None, true)
            .await
            .expect("create skill");

        // Shift A anchor: learning demonstrated on shift A.
        record_qualification(
            &pool,
            tenant_id,
            principal_id,
            skill_uuid,
            SkillLevel::Learning,
            evidence(assessor_id),
            None,
            Some(shift_a),
        )
        .await
        .expect("qualification on shift A");

        // Shift B: promotion to supervised on shift B — the SECOND record
        // must NOT overwrite the first evidence row.
        record_qualification(
            &pool,
            tenant_id,
            principal_id,
            skill_uuid,
            SkillLevel::Supervised,
            evidence(assessor_id),
            None,
            Some(shift_b),
        )
        .await
        .expect("qualification on shift B");

        // The evidence history holds BOTH shifts (append-only), and the
        // qualification anchor retains the FIRST shift.
        let (evidence_rows, shift_a_anchors, shift_b_anchors, qualification_anchor): (
            i64,
            i64,
            i64,
            Option<Uuid>,
        ) = with_tenant_tx(&pool, tenant_id, move |tx| {
            Box::pin(async move {
                let counts: (i64, i64, i64) = sqlx::query_as(
                    "SELECT COUNT(*), \
                            COUNT(*) FILTER (WHERE demonstration_shift_id = $1), \
                            COUNT(*) FILTER (WHERE demonstration_shift_id = $2) \
                     FROM skill_qualification_evidence \
                     WHERE tenant_id = $3 AND principal_id = $4 AND skill_id = $5",
                )
                .bind(shift_a)
                .bind(shift_b)
                .bind(tenant_id)
                .bind(principal_id)
                .bind(skill_uuid)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Evidence read failed: {e}")))?;
                let anchor: Option<Uuid> = sqlx::query_scalar(
                    "SELECT shift_id FROM skill_qualifications \
                     WHERE tenant_id = $1 AND principal_id = $2 AND skill_id = $3",
                )
                .bind(tenant_id)
                .bind(principal_id)
                .bind(skill_uuid)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Qualification read failed: {e}")))?;
                Ok((counts.0, counts.1, counts.2, anchor))
            })
        })
        .await
        .expect("read evidence history");

        assert_eq!(
            evidence_rows, 2,
            "two recorded qualifications must append TWO immutable evidence rows"
        );
        assert_eq!(
            shift_a_anchors, 1,
            "the Shift A evidence row must survive the Shift B record"
        );
        assert_eq!(
            shift_b_anchors, 1,
            "the Shift B evidence row must be recorded"
        );
        assert_eq!(
            qualification_anchor,
            Some(shift_a),
            "skill_qualifications.shift_id must retain the FIRST-recorded anchor"
        );
    }

    /// Eighteenth audit P1-9: a qualification on a shift that does not
    /// exist is a validation error (the demonstration context is resolved
    /// from real shift rows, never invented).
    #[tokio::test]
    async fn qualification_with_unknown_shift_is_rejected() {
        let Some(pool) = connect().await else { return };
        drop_all_tables(&pool).await;
        sensei_db::migrations::run_migrations(&pool)
            .await
            .expect("the ENTIRE migration chain must apply to an empty database");

        let tenant_id = Uuid::new_v4();
        let principal_id = Uuid::new_v4();
        let assessor_id = Uuid::new_v4();
        with_tenant_tx(&pool, tenant_id, move |tx| {
            Box::pin(async move {
                sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'p1-9b', 'p1-9b')")
                    .bind(tenant_id)
                    .execute(&mut **tx)
                    .await
                    .expect("tenant insert");
                sqlx::query(
                    "INSERT INTO users (id, tenant_id, email, name, password_hash) \
                     VALUES ($1, $2, 'p2@x.local', 'P', 'x')",
                )
                .bind(principal_id)
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("principal insert");
                sqlx::query(
                    "INSERT INTO users (id, tenant_id, email, name, password_hash) \
                     VALUES ($1, $2, 'a2@x.local', 'A', 'x')",
                )
                .bind(assessor_id)
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("assessor insert");
                Ok(())
            })
        })
        .await
        .expect("setup tx");

        let skill_uuid = create_skill(&pool, tenant_id, "aoi2", "AOI 2", None, None, false)
            .await
            .expect("create skill");

        let err = record_qualification(
            &pool,
            tenant_id,
            principal_id,
            skill_uuid,
            SkillLevel::Learning,
            evidence(assessor_id),
            None,
            Some(Uuid::new_v4()), // a shift that does not exist
        )
        .await
        .expect_err("a missing demonstration shift must be a validation error");
        assert!(
            matches!(err, SenseiError::Validation(_)),
            "expected Validation, got {err:?}"
        );
    }

    /// Nineteenth audit P1: multi-shift competency from evidence. A
    /// SAME-LEVEL demonstration on Shift B is NOT discarded (the old
    /// early return dropped it before any write): it appends a SECOND
    /// immutable evidence row and a SECOND competency_projection row (one
    /// per shift scope), and coverage for Shift B sees the principal.
    #[tokio::test]
    async fn same_level_demonstration_accumulates_per_shift_projection() {
        let Some(pool) = connect().await else { return };
        drop_all_tables(&pool).await;
        sensei_db::migrations::run_migrations(&pool)
            .await
            .expect("the ENTIRE migration chain must apply to an empty database");

        let tenant_id = Uuid::new_v4();
        let principal_id = Uuid::new_v4();
        let assessor_id = Uuid::new_v4();
        let site_id = Uuid::new_v4();
        let shift_a = Uuid::new_v4();
        let shift_b = Uuid::new_v4();

        // Setup (tenants/users/sites/shifts carry fail-closed RLS: run
        // under the tenant context).
        with_tenant_tx(&pool, tenant_id, move |tx| {
            Box::pin(async move {
                sqlx::query(
                    "INSERT INTO tenants (id, name, slug) VALUES ($1, 'p1-multi', 'p1-multi')",
                )
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("tenant insert");
                sqlx::query(
                    "INSERT INTO users (id, tenant_id, email, name, password_hash) \
                     VALUES ($1, $2, 'p3@x.local', 'P', 'x'), ($3, $2, 'a3@x.local', 'A', 'x')",
                )
                .bind(principal_id)
                .bind(tenant_id)
                .bind(assessor_id)
                .execute(&mut **tx)
                .await
                .expect("users insert");
                sqlx::query(
                    "INSERT INTO sites (id, tenant_id, site_code, name) \
                     VALUES ($1, $2, 'S', 'Site')",
                )
                .bind(site_id)
                .bind(tenant_id)
                .execute(&mut **tx)
                .await
                .expect("site insert");
                sqlx::query(
                    "INSERT INTO shifts (id, tenant_id, site_id, name, start_time, end_time) \
                     VALUES ($1, $2, $3, 'A', '08:00', '16:00'), \
                            ($4, $2, $3, 'B', '16:00', '00:00')",
                )
                .bind(shift_a)
                .bind(tenant_id)
                .bind(site_id)
                .bind(shift_b)
                .execute(&mut **tx)
                .await
                .expect("shifts insert");
                Ok(())
            })
        })
        .await
        .expect("setup tx");

        let skill_uuid = create_skill(&pool, tenant_id, "aoi3", "AOI 3", None, None, true)
            .await
            .expect("create skill");

        // Shift A: the principal demonstrates INDEPENDENT (prior
        // competence, assessed by a different user).
        record_qualification(
            &pool,
            tenant_id,
            principal_id,
            skill_uuid,
            SkillLevel::Independent,
            evidence(assessor_id),
            Some(serde_json::json!({
                "justification": "5 years AOI programming experience",
                "assessor_id": assessor_id.to_string(),
                "standard_revision": "AOI-OP-01/r1",
                "observed_cycles": 3,
            })),
            Some(shift_a),
        )
        .await
        .expect("qualification on shift A");

        // Shift B: the SAME level (independent) re-demonstrated on a
        // different shift. The old early return discarded this before any
        // write — it must now append evidence + projection for shift B.
        record_qualification(
            &pool,
            tenant_id,
            principal_id,
            skill_uuid,
            SkillLevel::Independent,
            evidence(assessor_id),
            None,
            Some(shift_b),
        )
        .await
        .expect("same-level qualification on shift B");

        // TWO evidence rows (one per shift), TWO projection rows (one per
        // shift), and the qualification anchor retains the FIRST shift.
        let (evidence_rows, projection_rows, shift_a_proj, shift_b_proj, anchor): (
            i64,
            i64,
            i64,
            i64,
            Option<Uuid>,
        ) = with_tenant_tx(&pool, tenant_id, move |tx| {
            Box::pin(async move {
                let evidence_rows: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM skill_qualification_evidence \
                     WHERE tenant_id = $1 AND principal_id = $2 AND skill_id = $3",
                )
                .bind(tenant_id)
                .bind(principal_id)
                .bind(skill_uuid)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Evidence read failed: {e}")))?;
                let (projection_rows, shift_a_proj, shift_b_proj): (i64, i64, i64) =
                    sqlx::query_as(
                        "SELECT COUNT(*), \
                                COUNT(*) FILTER (WHERE shift_id = $1), \
                                COUNT(*) FILTER (WHERE shift_id = $2) \
                         FROM competency_projection \
                         WHERE tenant_id = $3 AND principal_id = $4 AND skill_id = $5",
                    )
                    .bind(shift_a)
                    .bind(shift_b)
                    .bind(tenant_id)
                    .bind(principal_id)
                    .bind(skill_uuid)
                    .fetch_one(&mut **tx)
                    .await
                    .map_err(|e| SenseiError::Database(format!("Projection read failed: {e}")))?;
                let anchor: Option<Uuid> = sqlx::query_scalar(
                    "SELECT shift_id FROM skill_qualifications \
                     WHERE tenant_id = $1 AND principal_id = $2 AND skill_id = $3",
                )
                .bind(tenant_id)
                .bind(principal_id)
                .bind(skill_uuid)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Qualification read failed: {e}")))?;
                Ok((
                    evidence_rows,
                    projection_rows,
                    shift_a_proj,
                    shift_b_proj,
                    anchor,
                ))
            })
        })
        .await
        .expect("read evidence + projection");

        assert_eq!(
            evidence_rows, 2,
            "the same-level Shift B demonstration must append a SECOND evidence row"
        );
        assert_eq!(
            projection_rows, 2,
            "one competency_projection row PER demonstrated shift"
        );
        assert_eq!(shift_a_proj, 1, "the Shift A projection row exists");
        assert_eq!(shift_b_proj, 1, "the Shift B projection row exists");
        assert_eq!(
            anchor,
            Some(shift_a),
            "skill_qualifications.shift_id must retain the FIRST-recorded anchor"
        );

        // Coverage on Shift B sees the principal (structural shift filter
        // over competency_projection), and Shift A coverage is intact.
        let cov_b = skill_coverage_at(&pool, tenant_id, Some(site_id), Some(shift_b))
            .await
            .expect("coverage for shift B");
        let b = cov_b
            .iter()
            .find(|c| c.skill_id == "aoi3")
            .expect("AOI 3 in shift-B coverage");
        assert_eq!(
            b.bus_factor, 1,
            "shift-B coverage must see the principal demonstrated on shift B"
        );
        let cov_a = skill_coverage_at(&pool, tenant_id, Some(site_id), Some(shift_a))
            .await
            .expect("coverage for shift A");
        let a = cov_a
            .iter()
            .find(|c| c.skill_id == "aoi3")
            .expect("AOI 3 in shift-A coverage");
        assert_eq!(
            a.bus_factor, 1,
            "shift-A coverage must see the principal demonstrated on shift A"
        );
    }
}
