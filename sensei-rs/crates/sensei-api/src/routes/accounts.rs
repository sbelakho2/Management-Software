//! Accounts/Companies route handlers.
//!
//! Provides CRUD endpoints for customer and supplier account management.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::Account;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for listing accounts.
#[derive(Debug, Deserialize)]
pub struct ListAccountsParams {
    pub account_type: Option<String>,
    pub is_active: Option<bool>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating an account.
#[derive(Debug, Deserialize)]
pub struct AccountRequest {
    pub name: String,
    pub tax_id: Option<String>,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub address_line1: Option<String>,
    pub address_line2: Option<String>,
    pub city: Option<String>,
    pub state: Option<String>,
    pub postal_code: Option<String>,
    pub country: Option<String>,
    pub account_type: String,
    pub notes: Option<String>,
    /// Active flag; `None` on update keeps the current value.
    pub is_active: Option<bool>,
}

/// Account response.
#[derive(Debug, Serialize)]
pub struct AccountResponse {
    pub id: EntityId,
    pub tenant_id: TenantId,
    pub name: String,
    pub tax_id: Option<String>,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub address_line1: Option<String>,
    pub address_line2: Option<String>,
    pub city: Option<String>,
    pub state: Option<String>,
    pub postal_code: Option<String>,
    pub country: Option<String>,
    pub account_type: String,
    pub is_active: bool,
    pub notes: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<Account> for AccountResponse {
    fn from(a: Account) -> Self {
        Self {
            id: a.id,
            tenant_id: a.tenant_id,
            name: a.name,
            tax_id: a.tax_id,
            email: a.email,
            phone: a.phone,
            address_line1: a.address_line1,
            address_line2: a.address_line2,
            city: a.city,
            state: a.state,
            postal_code: a.postal_code,
            country: a.country,
            account_type: a.account_type,
            is_active: a.is_active,
            notes: a.notes,
            created_at: a.created_at,
            updated_at: a.updated_at,
        }
    }
}

/// List all accounts (paginated, filterable).
pub async fn list_accounts(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListAccountsParams>,
) -> Result<Json<PaginatedResponse<AccountResponse>>> {
    user.require_permission("sales:account:read")?;
    let tenant_id = user.tenant_id;
    let result = state
        .accounts_service
        .list_accounts(
            tenant_id,
            params.account_type.as_deref(),
            params.is_active,
            params.page,
            params.per_page,
        )
        .await?;
    let data: Vec<AccountResponse> = result.data.into_iter().map(AccountResponse::from).collect();
    Ok(Json(PaginatedResponse {
        data,
        total: result.total,
        page: result.page,
        per_page: result.per_page,
        total_pages: result.total_pages,
    }))
}

/// Create a new account.
pub async fn create_account(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<AccountRequest>,
) -> Result<Json<AccountResponse>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    let account = Account {
        id: EntityId::default(),
        tenant_id,
        name: req.name,
        tax_id: req.tax_id,
        email: req.email,
        phone: req.phone,
        address_line1: req.address_line1,
        address_line2: req.address_line2,
        city: req.city,
        state: req.state,
        postal_code: req.postal_code,
        country: req.country,
        account_type: req.account_type,
        is_active: req.is_active.unwrap_or(true),
        notes: req.notes,
        created_at: now(),
        updated_at: now(),
    };
    let created = state
        .accounts_service
        .create_account(tenant_id, account)
        .await?;
    Ok(Json(AccountResponse::from(created)))
}

/// Get an account by ID.
pub async fn get_account(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<AccountResponse>> {
    user.require_permission("sales:account:read")?;
    let tenant_id = user.tenant_id;
    let account = state.accounts_service.get_account(tenant_id, id).await?;
    Ok(Json(AccountResponse::from(account)))
}

/// Update an account.
///
/// Preserves the original `created_at` and keeps the current `is_active`
/// unless the request explicitly provides a new value.
pub async fn update_account(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<AccountRequest>,
) -> Result<Json<AccountResponse>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    let existing = state.accounts_service.get_account(tenant_id, id).await?;
    let account = Account {
        id,
        tenant_id,
        name: req.name,
        tax_id: req.tax_id,
        email: req.email,
        phone: req.phone,
        address_line1: req.address_line1,
        address_line2: req.address_line2,
        city: req.city,
        state: req.state,
        postal_code: req.postal_code,
        country: req.country,
        account_type: req.account_type,
        is_active: req.is_active.unwrap_or(existing.is_active),
        notes: req.notes,
        created_at: existing.created_at,
        updated_at: now(),
    };
    let updated = state
        .accounts_service
        .update_account(tenant_id, id, account)
        .await?;
    Ok(Json(AccountResponse::from(updated)))
}

/// Delete (deactivate) an account.
pub async fn delete_account(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    state.accounts_service.delete_account(tenant_id, id).await?;
    Ok(Json(serde_json::json!({
        "message": format!("Account {id} deactivated successfully")
    })))
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
        (state, tenant_id, admin.id)
    }

    fn auth_user(tenant_id: TenantId, user_id: EntityId) -> AuthenticatedUser {
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
            // Empty request-local permission set: the legacy RBAC registry
            // backs require_permission in direct-construction tests.
            permissions: std::collections::HashSet::new(),
        }
    }

    #[tokio::test]
    async fn test_create_account() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "Test Corp".to_string(),
            tax_id: Some("123-456".to_string()),
            email: Some("corp@test.com".to_string()),
            phone: Some("+1-555-0000".to_string()),
            address_line1: Some("123 Main St".to_string()),
            address_line2: None,
            city: Some("Springfield".to_string()),
            state: Some("IL".to_string()),
            postal_code: Some("62701".to_string()),
            country: Some("US".to_string()),
            account_type: "customer".to_string(),
            notes: Some("Test account".to_string()),
            is_active: None,
        };
        let resp = create_account(user, State(state.clone()), Json(req))
            .await
            .unwrap();
        assert_eq!(resp.name, "Test Corp");
        assert_eq!(resp.account_type, "customer");
        assert!(resp.is_active);
    }

    #[tokio::test]
    async fn test_get_account() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "Get Corp".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "supplier".to_string(),
            notes: None,
            is_active: None,
        };
        let created = create_account(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = get_account(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(resp.name, "Get Corp");
    }

    #[tokio::test]
    async fn test_get_account_not_found() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let result = get_account(user, State(state.clone()), Path(EntityId::new_v4())).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_list_accounts() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "List Corp".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: None,
        };
        let _ = create_account(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let params = ListAccountsParams {
            account_type: None,
            is_active: None,
            page: None,
            per_page: None,
        };
        let resp = list_accounts(user, State(state.clone()), Query(params))
            .await
            .unwrap();
        assert_eq!(resp.total, 1);
    }

    #[tokio::test]
    async fn test_update_account() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "Old Name".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: None,
        };
        let created = create_account(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let update_req = AccountRequest {
            name: "Updated Name".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: None,
        };
        let resp = update_account(
            user,
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(resp.name, "Updated Name");
    }

    #[tokio::test]
    async fn test_delete_account() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "Del Corp".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: None,
        };
        let created = create_account(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = delete_account(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(resp.get("message").is_some());
        // Verify it's soft-deleted (is_active = false)
        let get_resp = get_account(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(!get_resp.is_active);
    }

    #[tokio::test]
    async fn test_update_account_preserves_created_at_and_honors_is_active() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = AccountRequest {
            name: "Preserve Corp".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: Some(false),
        };
        let created = create_account(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        assert!(!created.is_active);

        // Updating without is_active keeps the current value (false) and
        // preserves created_at.
        let update_req = AccountRequest {
            name: "Preserved Name".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: None,
        };
        let updated = update_account(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(updated.created_at, created.created_at);
        assert!(!updated.is_active);

        // An explicit is_active=true must reactivate it.
        let reactivate_req = AccountRequest {
            name: "Preserved Name".to_string(),
            tax_id: None,
            email: None,
            phone: None,
            address_line1: None,
            address_line2: None,
            city: None,
            state: None,
            postal_code: None,
            country: None,
            account_type: "customer".to_string(),
            notes: None,
            is_active: Some(true),
        };
        let reactivated = update_account(
            user,
            State(state.clone()),
            Path(created.id),
            Json(reactivate_req),
        )
        .await
        .unwrap();
        assert!(reactivated.is_active);
    }
}
