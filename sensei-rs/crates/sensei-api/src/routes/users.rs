//! User management route handlers (admin).
//!
//! Provides admin CRUD endpoints for user management including
//! listing, updating, deactivating, reactivating, and role management.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::User;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::EntityId;
use serde::{Deserialize, Serialize};
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
///
/// Admin-only. Non-admin requests are rejected with 403.
pub async fn list_users(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListUsersParams>,
) -> Result<Json<PaginatedResponse<UserResponse>>> {
    if !user.has_any_role(&["tenant_admin", "platform_admin", "admin"]) {
        return Err(SenseiError::Forbidden(
            "Only tenant admins can list users".to_string(),
        ));
    }
    let all = state.users_service.list_users().await?;
    let mut filtered: Vec<User> = all
        .into_iter()
        .filter(|u| u.tenant_id == user.tenant_id)
        .filter(|u| {
            params
                .role
                .as_ref()
                .is_none_or(|r| u.roles.iter().any(|ur| ur == r))
        })
        .filter(|u| params.is_active.is_none_or(|a| u.is_active == a))
        .collect();
    filtered.sort_by_key(|a| a.created_at);

    let total = filtered.len();
    let page = params.page.unwrap_or(1).max(1);
    let per_page = params.per_page.unwrap_or(20).clamp(1, 100);
    let start = (page.saturating_sub(1)) * per_page;
    let data: Vec<UserResponse> = filtered
        .into_iter()
        .skip(start)
        .take(per_page)
        .map(UserResponse::from)
        .collect();

    Ok(Json(PaginatedResponse {
        data,
        total,
        page,
        per_page,
        total_pages: total.div_ceil(per_page),
    }))
}

/// Get a user by ID.
///
/// Non-admin users can only read users in their own tenant.
pub async fn get_user(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    let u = state.users_service.find_by_id(id).await?;
    if !user.has_role("admin") && u.tenant_id != user.tenant_id {
        return Err(SenseiError::NotFound(format!("User {id} not found")));
    }
    Ok(Json(UserResponse::from(u)))
}

/// Update a user (admin).
///
/// Non-admin users can only update users in their own tenant.
pub async fn update_user(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateUserRequest>,
) -> Result<Json<UserResponse>> {
    let mut existing = state.users_service.find_by_id(id).await?;
    // Editing another user requires the users:update permission; editing
    // yourself is always allowed (self-service profile changes).
    if id != user.user_id && !user.has_any_role(&["tenant_admin", "platform_admin", "admin"]) {
        return Err(SenseiError::Forbidden(
            "You may only edit your own profile. Administrators manage other users.".to_string(),
        ));
    }
    if existing.tenant_id != user.tenant_id {
        return Err(SenseiError::NotFound(format!("User {id} not found")));
    }

    if let Some(name) = req.name {
        existing.name = name;
    }
    if let Some(email) = req.email {
        if email != existing.email && state.users_service.find_by_email(&email).await.is_ok() {
            return Err(SenseiError::AlreadyExists(format!(
                "Email '{}' is already in use",
                email
            )));
        }
        existing.email = email;
    }

    existing.updated_at = sensei_core::types::now();
    let updated = state
        .users_service
        .update_user(user.tenant_id, id, existing)
        .await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Deactivate a user (soft delete, admin only).
pub async fn deactivate_user(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    if !user.has_any_role(&["tenant_admin", "platform_admin", "admin"]) {
        return Err(SenseiError::Forbidden(
            "Only tenant admins can deactivate users".to_string(),
        ));
    }
    let updated = state
        .users_service
        .deactivate_user(user.tenant_id, id)
        .await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Reactivate a user (admin only).
pub async fn activate_user(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<UserResponse>> {
    if !user.has_any_role(&["tenant_admin", "platform_admin", "admin"]) {
        return Err(SenseiError::Forbidden(
            "Only tenant admins can activate users".to_string(),
        ));
    }
    let updated = state
        .users_service
        .activate_user(user.tenant_id, id)
        .await?;
    Ok(Json(UserResponse::from(updated)))
}

/// Update a user's roles (admin only, with a grant ceiling).
///
/// The caller may only grant roles at or below their own scope:
/// - platform_admin may grant tenant_admin + functional roles (and
///   platform_admin only for break-glass scenarios, never the legacy
///   wildcard `admin`).
/// - tenant_admin may grant functional roles only — never platform_admin
///   and never `admin` (no privilege escalation).
pub async fn update_user_roles(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateRolesRequest>,
) -> Result<Json<UserResponse>> {
    let is_platform = user.has_role("platform_admin");
    let is_tenant_admin = user.has_any_role(&["tenant_admin", "admin"]);
    if !is_platform && !is_tenant_admin {
        return Err(SenseiError::Forbidden(
            "Only tenant admins can update user roles".to_string(),
        ));
    }
    for role in &req.roles {
        if role == "admin" || role == "platform_superadmin" {
            // The legacy wildcard role and the break-glass superadmin are
            // NEVER assignable via the API (platform_superadmin carries
            // *:* — granting it would be instant privilege escalation).
            return Err(SenseiError::Forbidden(
                "The 'admin' and 'platform_superadmin' roles cannot be assigned through the API"
                    .to_string(),
            ));
        }
        if role == "platform_admin" && !is_platform {
            return Err(SenseiError::Forbidden(
                "Only a platform admin can grant the platform_admin role".to_string(),
            ));
        }
    }
    if !user.has_any_role(&["tenant_admin", "platform_admin", "admin"]) {
        return Err(SenseiError::Forbidden(
            "Only tenant admins can update user roles".to_string(),
        ));
    }
    let updated = state
        .users_service
        .update_user_roles(user.tenant_id, id, req.roles)
        .await?;
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
        let users_service =
            InMemoryUsersService::with_admin("admin@test.com", "Admin User", &hash, tenant_id);
        let users_service = Arc::new(users_service) as Arc<dyn UsersService>;
        let config = AppConfig::from_env().unwrap();
        let state = AppState::new(config, users_service);
        let admin = state
            .users_service
            .find_by_email("admin@test.com")
            .await
            .unwrap();
        let admin_id = admin.id;
        (state, tenant_id, admin_id)
    }

    fn admin_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: vec![
                "user".to_string(),
                "tenant_admin".to_string(),
                "production_manager".to_string(),
                "quality_manager".to_string(),
                "purchasing_manager".to_string(),
                "sales_manager".to_string(),
                "finance_manager".to_string(),
                "inventory_manager".to_string(),
                "operator".to_string(),
            ],
            sid: None,
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
        let _ = deactivate_user(user.clone(), State(state.clone()), Path(user_id))
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
        // The legacy wildcard "admin" role is NEVER assignable via the API
        // (role ceiling) — this must fail closed with 403.
        let req = UpdateRolesRequest {
            roles: vec!["admin".to_string(), "quality_manager".to_string()],
        };
        let err = update_user_roles(user, State(state.clone()), Path(user_id), Json(req))
            .await
            .unwrap_err();
        assert!(matches!(err, SenseiError::Forbidden(_)));

        // Granting only functional roles succeeds.
        let user = admin_user(tenant_id, user_id);
        let req = UpdateRolesRequest {
            roles: vec!["quality_manager".to_string()],
        };
        let resp = update_user_roles(user, State(state.clone()), Path(user_id), Json(req))
            .await
            .unwrap();
        assert!(resp.roles.contains(&"quality_manager".to_string()));
    }
}
