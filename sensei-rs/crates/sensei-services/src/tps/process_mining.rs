//! Process mining (fifteenth audit 34/35, sixteenth audit 44/96): the
//! conformance check is a DIRECTLY-FOLLOWS analysis keyed PER CASE/OBJECT.
//! Events are grouped by the object they touch (recovered from the
//! `objects` JSONB), each case's events are ordered by occurred_at, and
//! the directly-follows transitions (e_i -> e_{i+1}) are aggregated ACROSS
//! cases — a real process graph. Hidden loops are detected WITHIN one
//! case's own sequence (the condition closed and reopened), never by
//! aggregating repeated event names across different objects.
//!
//! The recurrence signal is DETECTED FROM HISTORY: the report never tells
//! the user "you are now practicing TPS" — it shows the observed path,
//! the deviations, and the loops. The event log is authoritative and
//! bitemporal (occurred_at vs recorded_at); this module reads occurred_at
//! only.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use sqlx::Row;
use tracing::warn;
use uuid::Uuid;

/// One VERSIONED process definition (sixteenth audit item 46): the
/// expected path is DATA — a site improves its standard (new revision)
/// without recompiling. Conformance compares the observed transitions
/// against the revision applicable AT THE EVENT TIME, so a standard
/// change mid-window splits the window honestly. Columns map manually
/// from the JSONB `states` / `allowed_transitions` (FromRow via manual
/// mapping).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessDefinition {
    pub process_id: String,
    pub revision: i64,
    pub states: Vec<String>,
    pub allowed_transitions: Vec<(String, String)>,
}

impl<'r> sqlx::FromRow<'r, sqlx::postgres::PgRow> for ProcessDefinition {
    fn from_row(row: &'r sqlx::postgres::PgRow) -> std::result::Result<Self, sqlx::Error> {
        let states_value: serde_json::Value = row.try_get("states")?;
        let transitions_value: serde_json::Value = row.try_get("allowed_transitions")?;
        let states = states_value
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(str::to_string))
                    .collect()
            })
            .unwrap_or_default();
        let allowed_transitions = transitions_value
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| {
                        let pair = v.as_array()?;
                        Some((
                            pair.first()?.as_str()?.to_string(),
                            pair.get(1)?.as_str()?.to_string(),
                        ))
                    })
                    .collect()
            })
            .unwrap_or_default();
        Ok(ProcessDefinition {
            process_id: row.try_get("process_id")?,
            revision: row.try_get("revision")?,
            states,
            allowed_transitions,
        })
    }
}

/// A definition row plus its applicability window start — the public
/// struct deliberately excludes `applicable_from`, so conformance keeps
/// the versioned timeline internally.
#[derive(Debug, Clone)]
struct LoadedDefinition {
    def: ProcessDefinition,
    applicable_from: chrono::DateTime<chrono::Utc>,
}

/// The definition applicable AT `at`: the LATEST revision whose
/// `applicable_from` is <= the event time. Returns None when NO
/// definition exists for the process — the caller then uses the built-in
/// default path with a warning (a site that defines the process
/// overrides the compiled default; a site that does not keeps it).
pub async fn applicable_definition(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    process_id: &str,
    at: chrono::DateTime<chrono::Utc>,
) -> Result<Option<ProcessDefinition>> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin definition tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let exists: bool = sqlx::query_scalar(
        "SELECT EXISTS (SELECT 1 FROM process_definitions \
         WHERE tenant_id = $1 AND process_id = $2)",
    )
    .bind(tenant_id)
    .bind(process_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Process definition existence failed: {e}")))?;
    let def: Option<ProcessDefinition> = sqlx::query_as(
        "SELECT process_id, revision, states, allowed_transitions \
         FROM process_definitions \
         WHERE tenant_id = $1 AND process_id = $2 AND applicable_from <= $3 \
         ORDER BY applicable_from DESC, revision DESC \
         LIMIT 1",
    )
    .bind(tenant_id)
    .bind(process_id)
    .bind(at)
    .fetch_optional(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Process definition read failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Definition read commit failed: {e}")))?;
    if !exists {
        warn!(
            process = %process_id,
            "no process definition exists — conformance uses the compiled default path"
        );
    }
    Ok(def)
}

/// Insert the NEXT revision of a process definition (revision =
/// MAX(existing) + 1) — a site improves its standard WITHOUT recompiling;
/// conformance then compares against the revision applicable at each
/// event's time.
pub async fn upsert_process_definition(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    process_id: &str,
    states: Vec<String>,
    allowed_transitions: Vec<(String, String)>,
    applicable_from: chrono::DateTime<chrono::Utc>,
) -> Result<()> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin definition upsert tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let states_json = serde_json::to_value(&states)
        .map_err(|e| SenseiError::Internal(format!("states JSON encode failed: {e}")))?;
    let transitions_json = serde_json::to_value(&allowed_transitions)
        .map_err(|e| SenseiError::Internal(format!("transitions JSON encode failed: {e}")))?;
    sqlx::query(
        "INSERT INTO process_definitions \
             (tenant_id, process_id, revision, applicable_from, states, allowed_transitions) \
         VALUES ($1, $2, \
             COALESCE((SELECT MAX(revision) FROM process_definitions \
                       WHERE tenant_id = $1 AND process_id = $2), 0) + 1, \
             $3, $4, $5)",
    )
    .bind(tenant_id)
    .bind(process_id)
    .bind(applicable_from)
    .bind(states_json)
    .bind(transitions_json)
    .execute(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Process definition upsert failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Definition upsert commit failed: {e}")))?;
    Ok(())
}

/// Load every revision of one process's definition (with its
/// applicability start) for per-event-time lookup inside conformance.
async fn load_definitions(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    process_id: &str,
) -> Result<Vec<LoadedDefinition>> {
    type DefinitionRow = (
        String,
        i64,
        chrono::DateTime<chrono::Utc>,
        serde_json::Value,
        serde_json::Value,
    );
    let rows: Vec<DefinitionRow> = sqlx::query_as(
        "SELECT process_id, revision, applicable_from, states, allowed_transitions \
         FROM process_definitions \
         WHERE tenant_id = $1 AND process_id = $2 \
         ORDER BY applicable_from ASC, revision ASC",
    )
    .bind(tenant_id)
    .bind(process_id)
    .fetch_all(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Process definitions read failed: {e}")))?;
    Ok(rows
        .into_iter()
        .map(
            |(process_id, revision, applicable_from, states_value, transitions_value)| {
                let states = states_value
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(str::to_string))
                            .collect()
                    })
                    .unwrap_or_default();
                let allowed_transitions = transitions_value
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| {
                                let pair = v.as_array()?;
                                Some((
                                    pair.first()?.as_str()?.to_string(),
                                    pair.get(1)?.as_str()?.to_string(),
                                ))
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                LoadedDefinition {
                    def: ProcessDefinition {
                        process_id,
                        revision,
                        states,
                        allowed_transitions,
                    },
                    applicable_from,
                }
            },
        )
        .collect())
}

/// One actual step on the discovered path: an event type from the log and
/// how many times it was observed in the window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathStep {
    pub step: String,
    pub count: i64,
}

/// A hidden recurrence loop: one case (andon / ncr / a3 object) whose OWN
/// event sequence contains the SAME event type more than once — the
/// condition closed and came back. Per-case only: repeated event names
/// across different objects are never aggregated into a loop.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoopFinding {
    /// The repeated event type, e.g. `andon.raised` or `ncr.opened`.
    pub condition_key: String,
    /// How many times the condition re-opened in the window (occurrences
    /// of the event type minus the first).
    pub reopen_count: i64,
    /// Span between the first and last occurrence (days).
    pub window_days: i64,
    /// Plain-language guidance about the CONDITION — never TPS vocabulary.
    pub guidance: String,
}

/// The conformance report: expected canonical path vs the actual
/// directly-follows transitions discovered from the log (keyed per
/// case/object), the deviations, per-case variants, hidden loops, and
/// transition durations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConformanceReport {
    pub object_type: String,
    pub expected_path: Vec<String>,
    /// (from_step, to_step, count) — directly-follows pairs aggregated
    /// ACROSS every case's ordered event sequence, steps stripped of the
    /// object-type prefix.
    pub actual_transitions: Vec<(String, String, i64)>,
    /// (from_step, to_step, avg_seconds) — mean elapsed time between each
    /// directly-follows pair's events, aggregated across cases.
    pub transition_durations: Vec<(String, String, f64)>,
    /// Distinct full event sequences per case: (sequence, how many cases
    /// walked it).
    pub variants: Vec<(Vec<String>, u64)>,
    /// Transitions present in ACTUAL but not adjacent in EXPECTED, e.g.
    /// "acknowledged -> closed" when contained is expected between.
    pub deviations: Vec<String>,
    pub hidden_loops: Vec<LoopFinding>,
    /// The versioned process definition applicable at the latest event
    /// time in the window (None when the site defines no process — the
    /// compiled default path applies then).
    pub process_definition: Option<ProcessDefinition>,
}

/// Canonical (expected) path per object type. The path is the standard
/// sequence of steps the condition must pass through; a step may be
/// skipped in reality — that skip IS the deviation.
pub fn expected_path(object_type: &str) -> Vec<String> {
    match object_type {
        "andon" => vec![
            "raised",
            "acknowledged",
            "contained",
            "investigated",
            "verified",
            "closed",
        ]
        .into_iter()
        .map(str::to_string)
        .collect(),
        "ncr" => vec![
            "opened",
            "contained",
            "analyzed",
            "countermeasure",
            "verified",
            "closed",
        ]
        .into_iter()
        .map(str::to_string)
        .collect(),
        "a3" => vec![
            "opened",
            "hypothesis",
            "experiment",
            "verification",
            "standardization",
            "closed",
        ]
        .into_iter()
        .map(str::to_string)
        .collect(),
        _ => Vec::new(),
    }
}

const GUIDANCE_REOPEN: &str =
    "this condition keeps recurring — observe the work; the standard may not fit";

/// The event-log rows this module reads. Each row is tagged with its CASE
/// KEY — the object the event happened to — recovered from the `objects`
/// JSONB (the log links MANY objects per event; the object whose
/// `object_type` matches the queried type is the entity whose path we
/// mine). Events with no matching object fall back to their `source_id`.
struct LoggedEvent {
    id: Uuid,
    event_type: String,
    occurred_at: chrono::DateTime<chrono::Utc>,
    case_key: String,
}

/// Case key for one event: the FIRST object in the `objects` array whose
/// `object_type` matches the queried domain object ('andon.%' -> 'andon',
/// 'ncr.%' -> 'ncr', 'a3.%' -> 'a3'). Events WITHOUT a matching object are
/// grouped under their `source_id` when present, else skipped.
fn case_key(
    objects: &serde_json::Value,
    source_id: Option<&str>,
    object_type: &str,
) -> Option<String> {
    if let Some(arr) = objects.as_array() {
        for obj in arr {
            if obj.get("object_type").and_then(|v| v.as_str()) == Some(object_type) {
                if let Some(id) = obj.get("object_id") {
                    return Some(
                        id.as_str()
                            .map(str::to_string)
                            .unwrap_or_else(|| id.to_string()),
                    );
                }
            }
        }
    }
    source_id.map(str::to_string)
}

/// Transaction-scoped tenant context for the FORCE-RLS event log (the
/// policy is FAIL-CLOSED: missing context = no rows), same convention as
/// `crates/sensei-services/src/tps/organizational_memory.rs`.
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> Result<()> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Load the tenant's operational events for an object type within the
/// window, each row tagged with its mined case key (ordered by case key,
/// then occurred_at, then insert id for a deterministic sequence).
async fn load_events(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<Vec<LoggedEvent>> {
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin process-mining tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let events = load_events_tx(&mut tx, tenant_id, object_type, window_days).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Process-mining read commit failed: {e}")))?;
    Ok(events)
}

/// Event-loading inside an already tenant-scoped transaction (conformance
/// reads definitions and events in ONE tx so both see the same context).
async fn load_events_tx(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<Vec<LoggedEvent>> {
    let window_days = if window_days <= 0 { 30 } else { window_days };
    type MiningEventRow = (
        Uuid,
        String,
        chrono::DateTime<chrono::Utc>,
        serde_json::Value,
        Option<String>,
    );
    let rows: Vec<MiningEventRow> = sqlx::query_as(
        "SELECT id, event_type, occurred_at, objects, source_id \
             FROM operational_events \
             WHERE tenant_id = $1 AND event_type LIKE $2 \
               AND occurred_at > NOW() - $3::interval \
             ORDER BY occurred_at",
    )
    .bind(tenant_id)
    .bind(format!("{object_type}.%"))
    .bind(format!("{window_days} days"))
    .fetch_all(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Operational events read failed: {e}")))?;

    let mut events: Vec<LoggedEvent> = rows
        .into_iter()
        .filter_map(|(id, event_type, occurred_at, objects, source_id)| {
            case_key(&objects, source_id.as_deref(), object_type).map(|case_key| LoggedEvent {
                id,
                event_type,
                occurred_at,
                case_key,
            })
        })
        .collect();
    events.sort_by(|a, b| {
        (&a.case_key, a.occurred_at, a.id).cmp(&(&b.case_key, b.occurred_at, b.id))
    });
    Ok(events)
}

/// The actual step counts: event types seen in the window with their
/// frequency. NOTE: this is event-type frequency (ordered by first
/// occurrence), NOT the process graph — a per-object directly-follows
/// path with variants and deviations comes from `conformance_report`.
pub async fn discover_actual_path(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<Vec<PathStep>> {
    let events = load_events(pool, tenant_id, object_type, window_days).await?;
    let mut counts: std::collections::HashMap<&str, (i64, chrono::DateTime<chrono::Utc>)> =
        std::collections::HashMap::new();
    for ev in &events {
        let entry = counts
            .entry(ev.event_type.as_str())
            .or_insert((0, ev.occurred_at));
        entry.0 += 1;
    }
    let mut steps: Vec<PathStep> = counts
        .into_iter()
        .map(|(step, (count, _))| PathStep {
            step: step.to_string(),
            count,
        })
        .collect();
    steps.sort_by(|a, b| {
        let first_a = events
            .iter()
            .find(|e| e.event_type == a.step)
            .map(|e| e.occurred_at)
            .unwrap_or_default();
        let first_b = events
            .iter()
            .find(|e| e.event_type == b.step)
            .map(|e| e.occurred_at)
            .unwrap_or_default();
        first_a.cmp(&first_b).then_with(|| a.step.cmp(&b.step))
    });
    Ok(steps)
}

/// Conformance checking — PER-CASE directly-follows analysis: group the
/// operational_events log by case key (the object each event touches),
/// order each case's events by occurred_at, compute the directly-follows
/// pairs (e_i -> e_{i+1}) and aggregate transition counts ACROSS cases (a
/// real process graph). Deviations are transitions not adjacent in the
/// canonical path; variants are the distinct full sequences per case;
/// hidden loops are cases whose OWN sequence contains the same event type
/// more than once (per-case reopen — never cross-case aggregation);
/// transition_durations are the average seconds between each pair's
/// events.
pub async fn conformance_report(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<ConformanceReport> {
    let canonical = expected_path(object_type);
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin conformance tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let definitions = load_definitions(&mut tx, tenant_id, object_type).await?;
    if definitions.is_empty() {
        warn!(
            process = %object_type,
            "no process definition exists — conformance uses the compiled default path"
        );
    }
    let events = load_events_tx(&mut tx, tenant_id, object_type, window_days).await?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Conformance commit failed: {e}")))?;

    // Strip the object-type prefix ("andon.raised" -> "raised") so the
    // actual steps line up with the canonical path.
    let prefix = format!("{object_type}.");
    let step_name = |event_type: &str| -> String {
        event_type
            .strip_prefix(&prefix)
            .unwrap_or(event_type)
            .to_string()
    };

    // Directly-follows pairs aggregated ACROSS cases: (from, to) ->
    // (count, total_elapsed_seconds).
    let mut transition_counts: std::collections::HashMap<(String, String), (i64, f64)> =
        std::collections::HashMap::new();
    // Transitions whose occurrence was disallowed by the standard
    // applicable AT ITS EVENT TIME (the compiled default when the site
    // defines no process).
    let mut deviant_transitions: std::collections::HashSet<(String, String)> =
        std::collections::HashSet::new();
    // Distinct full sequences per case: sequence -> number of cases.
    let mut variant_counts: std::collections::HashMap<Vec<String>, u64> =
        std::collections::HashMap::new();
    // Hidden loops: one finding per case whose OWN sequence repeats an
    // event type (condition_key -> (occurrences, first, last)).
    let mut hidden_loops: Vec<LoopFinding> = Vec::new();

    // Expected adjacent pairs from the canonical path (the compiled
    // default — a site-defined revision overrides it when applicable).
    let mut expected_adjacent: std::collections::HashSet<(String, String)> =
        std::collections::HashSet::new();
    for pair in canonical.windows(2) {
        expected_adjacent.insert((pair[0].clone(), pair[1].clone()));
    }

    // The revision applicable AT a given event time: the latest revision
    // whose applicability window has started (definitions are sorted by
    // applicable_from ASC, revision ASC).
    let definition_at = |at: chrono::DateTime<chrono::Utc>| -> Option<&LoadedDefinition> {
        definitions.iter().rev().find(|d| d.applicable_from <= at)
    };

    // `load_events` sorts by (case_key, occurred_at, id); walk each case's
    // events as one contiguous chunk.
    let mut chunk_start = 0usize;
    while chunk_start < events.len() {
        let case = &events[chunk_start].case_key;
        let mut chunk_end = chunk_start;
        while chunk_end < events.len() && events[chunk_end].case_key == *case {
            chunk_end += 1;
        }
        let sequence = &events[chunk_start..chunk_end];

        let steps: Vec<String> = sequence.iter().map(|e| step_name(&e.event_type)).collect();
        *variant_counts.entry(steps.clone()).or_insert(0) += 1;

        for pair in sequence.windows(2) {
            let from = step_name(&pair[0].event_type);
            let to = step_name(&pair[1].event_type);
            let elapsed =
                (pair[1].occurred_at - pair[0].occurred_at).num_milliseconds() as f64 / 1000.0;
            let entry = transition_counts
                .entry((from.clone(), to.clone()))
                .or_insert((0, 0.0));
            entry.0 += 1;
            entry.1 += elapsed.max(0.0);

            // Conformance AT THE EVENT TIME (sixteenth audit item 46):
            // this occurrence is judged against the process revision
            // applicable when the transition completed. A transition the
            // applicable definition ALLOWS is never a deviation, even if
            // the compiled default would flag it.
            let allowed = match definition_at(pair[1].occurred_at) {
                Some(loaded) => {
                    if !loaded.def.allowed_transitions.is_empty() {
                        loaded
                            .def
                            .allowed_transitions
                            .contains(&(from.clone(), to.clone()))
                    } else if !loaded.def.states.is_empty() {
                        loaded
                            .def
                            .states
                            .windows(2)
                            .any(|w| w[0] == from && w[1] == to)
                    } else {
                        expected_adjacent.contains(&(from.clone(), to.clone()))
                    }
                }
                None => expected_adjacent.contains(&(from.clone(), to.clone())),
            };
            if !allowed {
                deviant_transitions.insert((from, to));
            }
        }

        // Per-case hidden loop: the SAME event type more than once in ONE
        // case's own sequence — the condition closed and came back. Keyed
        // by case so 100 NCRs each opened once can never look like 99
        // reopen loops.
        let mut case_loop_counts: std::collections::HashMap<
            &str,
            (
                i64,
                chrono::DateTime<chrono::Utc>,
                chrono::DateTime<chrono::Utc>,
            ),
        > = std::collections::HashMap::new();
        for ev in sequence {
            let entry = case_loop_counts.entry(ev.event_type.as_str()).or_insert((
                0,
                ev.occurred_at,
                ev.occurred_at,
            ));
            entry.0 += 1;
            entry.1 = entry.1.min(ev.occurred_at);
            entry.2 = entry.2.max(ev.occurred_at);
        }
        for (condition_key, (occurrences, first, last)) in case_loop_counts {
            if occurrences > 1 {
                hidden_loops.push(LoopFinding {
                    condition_key: condition_key.to_string(),
                    reopen_count: occurrences - 1,
                    window_days: (last - first).num_days().max(0),
                    guidance: GUIDANCE_REOPEN.to_string(),
                });
            }
        }

        chunk_start = chunk_end;
    }

    let mut actual_transitions: Vec<(String, String, i64)> = transition_counts
        .iter()
        .map(|((from, to), (count, _))| (from.clone(), to.clone(), *count))
        .collect();
    actual_transitions.sort();
    let mut transition_durations: Vec<(String, String, f64)> = transition_counts
        .into_iter()
        .map(|((from, to), (count, total))| {
            (from, to, if count > 0 { total / count as f64 } else { 0.0 })
        })
        .collect();
    transition_durations.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1.cmp(&b.1)));
    let mut variants: Vec<(Vec<String>, u64)> = variant_counts.into_iter().collect();
    variants.sort_by(|a, b| a.1.cmp(&b.1).then_with(|| a.0.cmp(&b.0)));

    // Deviations: transitions whose occurrence was disallowed by the
    // standard applicable at its event time — the applicable process
    // definition when the site defines one, else the compiled default
    // path (e.g. "closed" directly after "raised" — containment skipped).
    let mut deviations: Vec<String> = deviant_transitions
        .into_iter()
        .map(|(from, to)| format!("{from} -> {to}"))
        .collect();
    deviations.sort();
    deviations.dedup();

    hidden_loops.sort_by(|a, b| a.condition_key.cmp(&b.condition_key));

    // The definition applicable at the LATEST event time in the window —
    // the site's own standard when it defines the process, else None
    // (compiled default).
    let reference_time = events
        .iter()
        .map(|e| e.occurred_at)
        .max()
        .unwrap_or_else(chrono::Utc::now);
    let process_definition = definition_at(reference_time).map(|loaded| loaded.def.clone());

    Ok(ConformanceReport {
        object_type: object_type.to_string(),
        expected_path: canonical,
        actual_transitions,
        transition_durations,
        variants,
        deviations,
        hidden_loops,
        process_definition,
    })
}
