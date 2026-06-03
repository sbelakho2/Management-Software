//! User management route handlers (admin).
//!
//! Provides admin CRUD endpoints for user management including
//! listing, updating, deactivating, reactivating, and role management.

use axum::{Json, extract::{Path, Query, State}};
use serde::{Deserialize, Serialize};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::EntityId;
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for listing users.
#[derive(Debug, Deserialize)]
pub struct ListUsersParams {
    pub role: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for updating a user (admin).
#[derive(Debug, Deserialize)]
pub struct UpdateUserRequest {
    pub name: Option<String>,
    pub email: Option<String>,
}

/// Request body for updating user roles (admin).
#[derive(Debug, Deserialize)]
pub struct UpdateRolesRequest {
    pub roles: Vec<String>,
}

/// User response (without password hash).
#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: EntityId,
    pub tenant_id: EntityId,
    pub email: String,
    pub name: String,
    pub roles: Vec<String>,
    pub is_active: bool,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<User> for UserResponse {
    fn from(u: User) -> Self {
        Self {
            id: u.id,
            tenant_id: u.tenant_id,
            email: u.email,
            name: u.name,
            roles: u.roles,
            is_active: u.is_active,
            created_at: u.created_at,
            updated_at: u.updated_at,
        }
    }
}

/// Generic message response.
#[derive(Debug, Serialize)]
pub struct MessageResponse {
    pub message: String,
}

/// List all users (paginated, with optional role filter).
pub async fn list_users(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListUsersParams>,
) -> Result<Json<PaginatedResponse<UserResponse>>> {
    let result = state
        .users_service
        .list_users_paginated(
            params.role.as_deref(),
            params.is_active,
            params.page,
            params.per_page,
        )
        .await?;

    let data: Vec<UserResponse> = result.data.into_iter().map(UserResponse::from).collect();
    Ok(Json(PaginatedResponse {
        data,
        total: result.total,
        page: result.page,
        per_page: result.per_page,
        total_pages: result.total_pages,
    }))
}

/// Get a user by ID.
pub async fn get_user(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    let u = state.users_service.find_by_id(id).await?;
    Ok(Json(UserResponse::from(u)))
}

/// Update a user (admin).
pub async fn update_user(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateUserRequest>,
) -> Result<Json<UserResponse>> {
    let mut existing = state.users_service.find_by_id(id).await?;

    if let Some(name) = req.name {
        existing.name = name;
    }
    if let Some(email) = req.email {
        if email != existing.email
            && state.users_service.find_by_email(&email).await.is_ok()
        {
            return Err(SenseiError::AlreadyExists(format!(
                "Email '{}' is already in use",
                email
            )));
        }
        existing.email = email;
    }

    existing.updated_at = sensei_core::types::now();
    let updated = state.users_service.update_user(id, existing).await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Deactivate a user (soft delete, admin only).
pub async fn deactivate_user(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    let updated = state.users_service.deactivate_user(id).await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Reactivate a user (admin only).
pub async fn activate_user(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    let updated = state.users_service.activate_user(id).await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Update a user's roles (admin only).
pub async fn update_user_roles(
    _user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateRolesRequest>,
) -> Result<Json<UserResponse>> {
    let updated = state.users_service.update_user_roles(id, req.roles).await?;
    Ok(Json(UserResponse::from(updated)))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use axum::extract::Query;
    use sensei_auth::password::hash_password;
    use sensei_core::config::AppConfig;
    use sensei_core::types::TenantId;
    use sensei_services::users::{InMemoryUsersService, UsersService};
    use std::sync::Arc;

    /// Helper to build an AppState seeded with a test user.
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
        let admin_id = admin.id;
        (state, tenant_id, admin_id)
    }

    fn admin_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: vec!["admin".to_string()],
        }
    }

    #[tokio::test]
    async fn test_list_users() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let params = ListUsersParams {
            role: None,
            is_active: None,
            page: None,
            per_page: None,
        };
        let resp = list_users(user, State(state.clone()), Query(params))
            .await
            .unwrap();
        assert_eq!(resp.total, 1);
        assert_eq!(resp.data.len(), 1);
        assert_eq!(resp.data[0].email, "admin@test.com");
    }

    #[tokio::test]
    async fn test_list_users_paginated() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let params = ListUsersParams {
            role: None,
            is_active: None,
            page: Some(1),
            per_page: Some(10),
        };
        let resp = list_users(user, State(state.clone()), Query(params))
            .await
            .unwrap();
        assert_eq!(resp.total, 1);
        assert_eq!(resp.data.len(), 1);
        assert_eq!(resp.page, 1);
        assert_eq!(resp.per_page, 10);
        assert_eq!(resp.total_pages, 1);
    }

    #[tokio::test]
    async fn test_get_user() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let resp = get_user(user, State(state.clone()), Path(user_id))
            .await
            .unwrap();
        assert_eq!(resp.email, "admin@test.com");
    }

    #[tokio::test]
    async fn test_get_user_not_found() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let result = get_user(user, State(state.clone()), Path(EntityId::new_v4())).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_update_user_name() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let req = UpdateUserRequest {
            name: Some("Updated Admin".to_string()),
            email: None,
        };
        let resp = update_user(user, State(state.clone()), Path(user_id), Json(req))
            .await
            .unwrap();
        assert_eq!(resp.name, "Updated Admin");
        assert_eq!(resp.email, "admin@test.com");
    }

    #[tokio::test]
    async fn test_deactivate_user() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let resp = deactivate_user(user, State(state.clone()), Path(user_id))
            .await
            .unwrap();
        assert!(!resp.is_active);
    }

    #[tokio::test]
    async fn test_activate_user() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);

        // First deactivate
        let _ = deactivate_user(
            user.clone(),
            State(state.clone()),
            Path(user_id),
        )
        .await
        .unwrap();

        // Then reactivate
        let resp = activate_user(user, State(state.clone()), Path(user_id))
            .await
            .unwrap();
        assert!(resp.is_active);
    }

    #[tokio::test]
    async fn test_update_user_roles() {
        let (state, tenant_id, user_id) = test_state().await;
        let user = admin_user(tenant_id, user_id);
        let req = UpdateRolesRequest {
            roles: vec!["admin".to_string(), "manager".to_string()],
        };
        let resp = update_user_roles(user, State(state.clone()), Path(user_id), Json(req))
            .await
            .unwrap();
        assert!(resp.roles.contains(&"manager".to_string()));
    }
}
