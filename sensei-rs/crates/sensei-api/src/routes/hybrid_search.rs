//! Hybrid retrieval route (item 24): lexical + dense + authority-weighted
//! knowledge search. The embedding leg is deterministic and local.

use axum::extract::{Query, State};
use axum::Json;
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::SenseiError;

use crate::state::AppState;

#[derive(Debug, serde::Deserialize)]
pub struct HybridSearchParams {
    pub q: String,
    #[serde(default = "default_limit")]
    pub limit: i64,
}

fn default_limit() -> i64 {
    20
}

pub async fn hybrid_search(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<HybridSearchParams>,
) -> Result<Json<serde_json::Value>, SenseiError> {
    user.require_permission("knowledge:read")?;
    let Some(pool) = state.db_pool.as_ref() else {
        return Err(SenseiError::Internal(
            "Hybrid search requires the database-backed pool".to_string(),
        ));
    };
    let hits = crate::services::hybrid_retrieval::hybrid_search(
        pool,
        user.tenant_id,
        &params.q,
        &user.roles,
        params.limit,
    )
    .await
    .map_err(SenseiError::Internal)?;
    Ok(Json(serde_json::json!({
        "query": params.q,
        "results": hits,
    })))
}
