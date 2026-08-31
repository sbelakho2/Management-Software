//! Process mining (fifteenth audit 34/35): conformance checking —
//! discover the ACTUAL transition path from the operational_events log
//! and compare it to the EXPECTED canonical path. Hidden loops (a
//! condition that closes and reopens) are the most valuable TPS signal.
//!
//! The recurrence signal is DETECTED FROM HISTORY: the report never tells
//! the user "you are now practicing TPS" — it shows the observed path,
//! the deviations, and the loops. The event log is authoritative and
//! bitemporal (occurred_at vs recorded_at); this module reads occurred_at
//! only.

use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// One actual step on the discovered path: an event type from the log and
/// how many times it was observed in the window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathStep {
    pub step: String,
    pub count: i64,
}

/// A hidden recurrence loop: one entity (andon / ncr / a3) whose event
/// sequence contains the SAME event type more than once — the condition
/// closed and came back.
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
/// transitions discovered from the log, the deviations, and hidden loops.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConformanceReport {
    pub object_type: String,
    pub expected_path: Vec<String>,
    /// (from_step, to_step, count) — consecutive transitions observed in
    /// the log, steps stripped of the object-type prefix.
    pub actual_transitions: Vec<(String, String, i64)>,
    /// Transitions present in ACTUAL but not adjacent in EXPECTED, e.g.
    /// "acknowledged -> closed" when contained is expected between.
    pub deviations: Vec<String>,
    pub hidden_loops: Vec<LoopFinding>,
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

/// The event-log rows this module reads: the entity the event belongs to
/// is recovered from the `objects` JSONB (the log links MANY objects per
/// event; the object whose `object_type` matches the queried type is the
/// entity whose path we mine).
struct LoggedEvent {
    id: Uuid,
    event_type: String,
    occurred_at: chrono::DateTime<chrono::Utc>,
    entity_id: String,
}

fn entity_id_from_objects(objects: &serde_json::Value, object_type: &str) -> Option<String> {
    let arr = objects.as_array()?;
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
    arr.first().and_then(|obj| obj.get("object_id")).map(|id| {
        id.as_str()
            .map(str::to_string)
            .unwrap_or_else(|| id.to_string())
    })
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
/// window, each row tagged with its mined entity id (ordered by entity,
/// then occurred_at, then insert id for a deterministic sequence).
async fn load_events(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<Vec<LoggedEvent>> {
    let window_days = if window_days <= 0 { 30 } else { window_days };
    let mut tx = pool
        .begin()
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to begin process-mining tx: {e}")))?;
    set_tenant_context(&mut tx, tenant_id).await?;
    let rows: Vec<(
        Uuid,
        String,
        chrono::DateTime<chrono::Utc>,
        serde_json::Value,
    )> = sqlx::query_as(
        "SELECT id, event_type, occurred_at, objects \
             FROM operational_events \
             WHERE tenant_id = $1 AND event_type LIKE $2 \
               AND occurred_at > NOW() - $3::interval \
             ORDER BY occurred_at",
    )
    .bind(tenant_id)
    .bind(format!("{object_type}.%"))
    .bind(format!("{window_days} days"))
    .fetch_all(&mut *tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Operational events read failed: {e}")))?;
    tx.commit()
        .await
        .map_err(|e| SenseiError::Database(format!("Process-mining read commit failed: {e}")))?;

    let mut events: Vec<LoggedEvent> = rows
        .into_iter()
        .filter_map(|(id, event_type, occurred_at, objects)| {
            entity_id_from_objects(&objects, object_type).map(|entity_id| LoggedEvent {
                id,
                event_type,
                occurred_at,
                entity_id,
            })
        })
        .collect();
    events.sort_by(|a, b| {
        (&a.entity_id, a.occurred_at, a.id).cmp(&(&b.entity_id, b.occurred_at, b.id))
    });
    Ok(events)
}

/// The actual step counts: event types seen in the window, ordered by
/// their first occurrence (the path the operation ACTUALLY walked).
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

/// Conformance checking: pull the actual transition path from the
/// operational_events log, compare it to the canonical expected path, and
/// surface deviations plus hidden recurrence loops.
pub async fn conformance_report(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    object_type: &str,
    window_days: i64,
) -> Result<ConformanceReport> {
    let canonical = expected_path(object_type);
    let events = load_events(pool, tenant_id, object_type, window_days).await?;

    // Strip the object-type prefix ("andon.raised" -> "raised") so the
    // actual steps line up with the canonical path.
    let prefix = format!("{object_type}.");
    let step_name = |event_type: &str| -> String {
        event_type
            .strip_prefix(&prefix)
            .unwrap_or(event_type)
            .to_string()
    };

    // Consecutive transitions per entity: (from, to) counted across every
    // entity's ordered sequence.
    let mut transition_counts: std::collections::HashMap<(String, String), i64> =
        std::collections::HashMap::new();
    // Hidden loops per entity: event type -> (occurrences, first, last).
    let mut loop_counts: std::collections::HashMap<
        &str,
        (
            i64,
            chrono::DateTime<chrono::Utc>,
            chrono::DateTime<chrono::Utc>,
        ),
    > = std::collections::HashMap::new();

    let mut chunk_start = 0usize;
    while chunk_start < events.len() {
        let entity = &events[chunk_start].entity_id;
        let mut chunk_end = chunk_start;
        while chunk_end < events.len() && events[chunk_end].entity_id == *entity {
            chunk_end += 1;
        }
        let sequence = &events[chunk_start..chunk_end];
        for pair in sequence.windows(2) {
            let from = step_name(&pair[0].event_type);
            let to = step_name(&pair[1].event_type);
            *transition_counts.entry((from, to)).or_insert(0) += 1;
        }
        for ev in sequence {
            let entry = loop_counts.entry(ev.event_type.as_str()).or_insert((
                0,
                ev.occurred_at,
                ev.occurred_at,
            ));
            entry.0 += 1;
            entry.1 = entry.1.min(ev.occurred_at);
            entry.2 = entry.2.max(ev.occurred_at);
        }
        chunk_start = chunk_end;
    }

    let mut actual_transitions: Vec<(String, String, i64)> = transition_counts
        .into_iter()
        .map(|((from, to), count)| (from, to, count))
        .collect();
    actual_transitions.sort();

    // Expected adjacent pairs from the canonical path.
    let mut expected_adjacent: std::collections::HashSet<(String, String)> =
        std::collections::HashSet::new();
    for pair in canonical.windows(2) {
        expected_adjacent.insert((pair[0].clone(), pair[1].clone()));
    }

    // Deviations: actual transitions that are NOT adjacent in the
    // expected path (e.g. "closed" directly after "raised" — containment
    // skipped).
    let mut deviations: Vec<String> = actual_transitions
        .iter()
        .filter(|(from, to, _)| !expected_adjacent.contains(&(from.clone(), to.clone())))
        .map(|(from, to, _)| format!("{from} -> {to}"))
        .collect();
    deviations.sort();
    deviations.dedup();

    // Hidden loops: the same event type appearing more than once in one
    // entity's sequence — a condition that closed and reopened.
    let mut hidden_loops: Vec<LoopFinding> = loop_counts
        .into_iter()
        .filter(|(_, (occurrences, _, _))| *occurrences > 1)
        .map(|(condition_key, (occurrences, first, last))| LoopFinding {
            condition_key: condition_key.to_string(),
            reopen_count: occurrences - 1,
            window_days: (last - first).num_days().max(0),
            guidance: GUIDANCE_REOPEN.to_string(),
        })
        .collect();
    hidden_loops.sort_by(|a, b| a.condition_key.cmp(&b.condition_key));

    Ok(ConformanceReport {
        object_type: object_type.to_string(),
        expected_path: canonical,
        actual_transitions,
        deviations,
        hidden_loops,
    })
}
