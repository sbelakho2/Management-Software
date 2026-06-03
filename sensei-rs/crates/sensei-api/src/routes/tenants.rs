//! Tenants route handlers.
//!
//! Provides CRUD endpoints for tenant/organization management.

use axum::{Json, extract::{Path, State}};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::Tenant;
use sensei_core::error::Result;
use sensei_core::types::{TenantId, now};
use uuid::Uuid;

use crate::state::AppState;

/// Request body for creating/updating a tenant.
#[derive(Debug, Deserialize)]
pub struct TenantRequest {
    pub name: String,
    pub slug: String,
    pub features: Option<Vec<String>>,
}

/// Tenant response.
#[derive(Debug, Serialize)]
pub struct TenantResponse {
    pub id: TenantId,
    pub name: String,
    pub slug: String,
    pub is_active: bool,
    pub features: Vec<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<Tenant> for TenantResponse {
    fn from(t: Tenant) -> Self {
        Self {
            id: t.id,
            name: t.name,
            slug: t.slug,
            is_active: t.is_active,
            features: t.features,
            created_at: t.created_at,
            updated_at: t.updated_at,
        }
    }
}

/// List all tenants.
pub async fn list_tenants(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
) -> Result<Json<Vec<TenantResponse>>> {
    let tenants = state.tenants_service.list_tenants().await?;
    Ok(Json(tenants.into_iter().map(TenantResponse::from).collect()))
}

/// Create a new tenant.
pub async fn create_tenant(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<TenantRequest>,
) -> Result<Json<TenantResponse>> {
    let tenant = Tenant {
        id: TenantId::default(),
        name: req.name,
        slug: req.slug,
        is_active: true,
        features: req.features.unwrap_or_default(),
        created_at: now(),
        updated_at: now(),
    };
    let created = state.tenants_service.create_tenant(tenant).await?;
    Ok(Json(TenantResponse::from(created)))
}

/// Get a tenant by ID.
pub async fn get_tenant(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<TenantResponse>> {
    let tenant = state.tenants_service.get_tenant(id).await?;
    Ok(Json(TenantResponse::from(tenant)))
}

/// Update a tenant.
pub async fn update_tenant(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<TenantRequest>,
) -> Result<Json<TenantResponse>> {
    let tenant = Tenant {
        id,
        name: req.name,
        slug: req.slug,
        is_active: true,
        features: req.features.unwrap_or_default(),
        created_at: now(),
        updated_at: now(),
    };
    let updated = state.tenants_service.update_tenant(id, tenant).await?;
    Ok(Json(TenantResponse::from(updated)))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_auth::password::hash_password;
    use sensei_core::config::AppConfig;
    use sensei_core::types::EntityId;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    async fn test_state() -> (AppState, TenantId, EntityId) {
        let hash = hash_password("Test@1234").unwrap();
        let tenant_id = TenantId::new_v4();
        let users_service = InMemoryUsersService::with_admin(
            "admin@test.com", "Admin User", &hash, tenant_id,
        );
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
        let config = AppConfig::from_env().unwrap();
        let state = AppState::new(config, users_service);
        let admin = state.users_service.find_by_email("admin@test.com").await.unwrap();
        (state, tenant_id, admin.id)
    }

    fn auth_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
        AuthenticatedUser { user_id, tenant_id, roles: vec!["admin".to_string()] }
    }

    #[tokio::test]
    async fn test_create_tenant() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = TenantRequest {
            name: "Test Org".to_string(),
            slug: "test-org".to_string(),
            features: Some(vec!["quality".to_string(), "production".to_string()]),
        };
        let resp = create_tenant(user, State(state.clone()), Json(req))
            .await
            .unwrap();
        assert_eq!(resp.name, "Test Org");
        assert_eq!(resp.slug, "test-org");
        assert!(resp.is_active);
        assert!(resp.features.contains(&"quality".to_string()));
    }

    #[tokio::test]
    async fn test_get_tenant() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = TenantRequest {
            name: "Get Org".to_string(),
            slug: "get-org".to_string(),
            features: None,
        };
        let created = create_tenant(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = get_tenant(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(resp.name, "Get Org");
    }

    #[tokio::test]
    async fn test_get_tenant_not_found() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let result = get_tenant(user, State(state.clone()), Path(EntityId::new_v4())).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_list_tenants() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = TenantRequest {
            name: "List Org".to_string(),
            slug: "list-org".to_string(),
            features: None,
        };
        let _ = create_tenant(user.clone(), State(state.clone()), Json(req)).await.unwrap();
        let resp = list_tenants(user, State(state.clone())).await.unwrap();
        assert_eq!(resp.len(), 1);
    }

    #[tokio::test]
    async fn test_update_tenant() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = TenantRequest {
            name: "Old Name".to_string(),
            slug: "old-slug".to_string(),
            features: None,
        };
        let created = create_tenant(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let update_req = TenantRequest {
            name: "Updated Name".to_string(),
            slug: "updated-slug".to_string(),
            features: Some(vec!["hr".to_string()]),
        };
        let resp = update_tenant(user, State(state.clone()), Path(created.id), Json(update_req))
            .await
            .unwrap();
        assert_eq!(resp.name, "Updated Name");
        assert_eq!(resp.slug, "updated-slug");
        assert!(resp.features.contains(&"hr".to_string()));
    }
}
