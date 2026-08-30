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
    // Item 61: TYPED nodes — the source and target must exist in their
    // typed tables and belong to the SAME tenant. Free-form UUIDs with no
    // existence proof are rejected (the database cannot FK them).
    for (entity_type, entity_id) in [
        (&req.source_type, req.source_id),
        (&req.target_type, req.target_id),
    ] {
        let exists: Option<Uuid> = match entity_type.as_str() {
            "abnormality" => {
                sqlx::query_scalar("SELECT id FROM andons WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            "work_center" => {
                sqlx::query_scalar("SELECT id FROM work_centers WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            "a3" => {
                sqlx::query_scalar("SELECT id FROM a3_reports WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            "standard" => sqlx::query_scalar(
                "SELECT id FROM standard_work_documents WHERE id = $1 AND tenant_id = $2",
            )
            .bind(entity_id)
            .bind(user.tenant_id)
            .fetch_optional(pool.as_ref())
            .await
            .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?,
            "action" | "task" => {
                sqlx::query_scalar("SELECT id FROM tasks WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            "experiment" | "work_order" => {
                sqlx::query_scalar("SELECT id FROM work_orders WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            "product" => {
                sqlx::query_scalar("SELECT id FROM products WHERE id = $1 AND tenant_id = $2")
                    .bind(entity_id)
                    .bind(user.tenant_id)
                    .fetch_optional(pool.as_ref())
                    .await
                    .map_err(|e| SenseiError::Database(format!("Node check failed: {e}")))?
            }
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unknown node type '{other}' — the graph only links typed nodes"
                )));
            }
        };
        if exists.is_none() {
            return Err(SenseiError::Validation(format!(
                "Graph node {entity_type}/{entity_id} does not exist in this tenant"
            )));
        }
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

/// Rebuild the derived graph from AUTHORITATIVE sources (item 63): the
/// graph is a reconstructable projection — an abnormality edge is
/// regenerated from the andons table, so a lost/partial projection can be
/// repaired without replaying the whole integration history.
pub async fn rebuild_graph(
    user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("knowledge:manage")?;
    let pool = state.db_pool.as_ref().ok_or_else(|| {
        SenseiError::Database("Knowledge graph requires the database".to_string())
    })?;
    // Regenerate the abnormality → occurred_at → work_center edges from
    // the authoritative andons table.
    let inserted = sqlx::query(
        "INSERT INTO knowledge_graph_edges  (tenant_id, source_type, source_id, relation, target_type, target_id)  SELECT a.tenant_id, 'abnormality', a.id, 'occurred_at', 'work_center', a.work_center_id  FROM andons a  WHERE a.tenant_id = $1 AND a.work_center_id IS NOT NULL  ON CONFLICT DO NOTHING",
    )
    .bind(user.tenant_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| SenseiError::Database(format!("Graph rebuild failed: {e}")))?;
    Ok(Json(serde_json::json!({
        "rebuilt": true,
        "edges_created": inserted.rows_affected(),
        "derived_from": "andons (authoritative)",
    })))
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

    // Item 62: object-level ACL — an edge is only returned when BOTH
    // endpoints are visible to the caller. The relationship itself can
    // reveal sensitive metadata even when the underlying object is not
    // readable (HR, finance, restricted projects), so the graph must not
    // leak it.
    let mut visible: Vec<GraphEdge> = Vec::new();
    for (id, st, si, rel, tt, ti, ca) in rows {
        let source_ok = node_visible_to(pool, user.tenant_id, &user.roles, &st, si).await?;
        let target_ok = node_visible_to(pool, user.tenant_id, &user.roles, &tt, ti).await?;
        if source_ok && target_ok {
            visible.push(GraphEdge {
                id,
                source_type: st,
                source_id: si,
                relation: rel,
                target_type: tt,
                target_id: ti,
                created_at: ca,
            });
        }
    }
    Ok(Json(visible))
}

/// Whether a graph node is visible to the caller (item 62): knowledge
/// packs carry `allowed_roles` in their entity_store row — an edge to a
/// restricted pack is filtered out. All other typed nodes are tenant-
/// scoped, so tenant membership is the ACL.
async fn node_visible_to(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    caller_roles: &[String],
    node_type: &str,
    node_id: Uuid,
) -> Result<bool> {
    if node_type != "knowledge_pack" {
        // Tenant-scoped typed nodes (abnormality, work_center, a3,
        // standard, work_order, product): tenant isolation is the ACL.
        return Ok(true);
    }
    let allowed: Option<serde_json::Value> = sqlx::query_scalar(
        "SELECT es.data->'allowed_roles' FROM entity_store es \
         WHERE es.tenant_id = $1 AND es.entity_type = 'knowledge_pack' AND es.id = $2",
    )
    .bind(tenant_id)
    .bind(node_id)
    .fetch_optional(pool)
    .await
    .map_err(|e| SenseiError::Database(format!("Node ACL read failed: {e}")))?;
    match allowed {
        None => Ok(true), // no restriction recorded
        Some(serde_json::Value::Array(roles)) if roles.is_empty() => Ok(true),
        Some(serde_json::Value::Array(roles)) => {
            let required: Vec<String> = roles
                .iter()
                .filter_map(|r| r.as_str().map(|s| s.to_string()))
                .collect();
            Ok(required.iter().any(|r| caller_roles.iter().any(|c| c == r)))
        }
        Some(_) => Ok(true),
    }
}
