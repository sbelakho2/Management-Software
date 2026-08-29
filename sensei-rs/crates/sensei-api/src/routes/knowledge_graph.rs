//! Knowledge graph (item 73): explicit edges between operational objects —
//! Abnormality deviates_from Standard, occurred_at WorkCenter, contained_by
//! Action, investigated_in A3, tested_by Experiment, changed
//! StandardRevision, recurred_as Abnormality. The endpoint records edges
//! and answers graph queries (what does this abnormality relate to?).

use axum::extract::{Path, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// One directed edge in the knowledge graph.
#[derive(Debug, Serialize)]
pub struct GraphEdge {
    pub id: Uuid,
    pub source_type: String,
    pub source_id: Uuid,
    pub relation: String,
    pub target_type: String,
    pub target_id: Uuid,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

/// Request to record an edge.
#[derive(Debug, Deserialize)]
pub struct RecordEdgeRequest {
    pub source_type: String,
    pub source_id: Uuid,
    pub relation: String,
    pub target_type: String,
    pub target_id: Uuid,
}

/// Record a knowledge-graph edge (admin/ops scope).
pub async fn record_edge(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<RecordEdgeRequest>,
) -> Result<Json<GraphEdge>> {
    user.require_permission("knowledge:manage")?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Knowledge graph requires the database".to_string())
    })?;
    // Relation must be from the canonical vocabulary (item 73) — prose
    // relations would make the graph useless for reasoning.
    let valid_relations = [
        "deviates_from",
        "occurred_at",
        "affected",
        "caused",
        "contained_by",
        "investigated_in",
        "tested_by",
        "changed",
        "recurred_as",
        "requires",
        "feeds",
    ];
    if !valid_relations.contains(&req.relation.as_str()) {
        return Err(SenseiError::Validation(format!(
            "Relation '{}' is not in the canonical vocabulary: {}",
            req.relation,
            valid_relations.join(", ")
        )));
    }
    let row: (Uuid, chrono::DateTime<chrono::Utc>) = sqlx::query_as(
        "INSERT INTO knowledge_graph_edges \
            (tenant_id, source_type, source_id, relation, target_type, target_id, created_by) \
         VALUES ($1, $2, $3, $4, $5, $6, $7) \
         ON CONFLICT (tenant_id, source_type, source_id, relation, target_type, target_id) \
         DO UPDATE SET created_at = knowledge_graph_edges.created_at \
         RETURNING id, created_at",
    )
    .bind(user.tenant_id)
    .bind(&req.source_type)
    .bind(req.source_id)
    .bind(&req.relation)
    .bind(&req.target_type)
    .bind(req.target_id)
    .bind(user.user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Edge record failed: {e}")))?;

    Ok(Json(GraphEdge {
        id: row.0,
        source_type: req.source_type,
        source_id: req.source_id,
        relation: req.relation,
        target_type: req.target_type,
        target_id: req.target_id,
        created_at: row.1,
    }))
}

/// Query the graph around an object: all outgoing and incoming edges
/// (depth 1 — the reasoning layer can walk further).
pub async fn edges_around(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path((entity_type, entity_id)): Path<(String, Uuid)>,
) -> Result<Json<Vec<GraphEdge>>> {
    user.require_permission("knowledge:read")?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Knowledge graph requires the database".to_string())
    })?;
    type GraphRow = (
        Uuid,
        String,
        Uuid,
        String,
        String,
        Uuid,
        chrono::DateTime<chrono::Utc>,
    );
    let rows: Vec<GraphRow> = sqlx::query_as(
        "SELECT id, source_type, source_id, relation, target_type, target_id, created_at \
             FROM knowledge_graph_edges \
             WHERE tenant_id = $1 \
               AND ((source_type = $2 AND source_id = $3) \
                 OR (target_type = $2 AND target_id = $3)) \
             ORDER BY created_at DESC LIMIT 200",
    )
    .bind(user.tenant_id)
    .bind(&entity_type)
    .bind(entity_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Graph query failed: {e}")))?;

    Ok(Json(
        rows.into_iter()
            .map(|(id, st, si, rel, tt, ti, ca)| GraphEdge {
                id,
                source_type: st,
                source_id: si,
                relation: rel,
                target_type: tt,
                target_id: ti,
                created_at: ca,
            })
            .collect(),
    ))
}
