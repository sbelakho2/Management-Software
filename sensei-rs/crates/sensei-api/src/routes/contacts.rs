//! Contacts route handlers.
//!
//! Provides CRUD endpoints for contact person management.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::Contact;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for listing contacts.
#[derive(Debug, Deserialize)]
pub struct ListContactsParams {
    pub account_id: Option<Uuid>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a contact.
#[derive(Debug, Deserialize)]
pub struct ContactRequest {
    pub account_id: Option<Uuid>,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub phone: Option<String>,
    pub job_title: Option<String>,
    pub department: Option<String>,
    pub is_primary: Option<bool>,
    pub notes: Option<String>,
    /// Active flag; `None` on update keeps the current value.
    pub is_active: Option<bool>,
}

/// Contact response.
#[derive(Debug, Serialize)]
pub struct ContactResponse {
    pub id: EntityId,
    pub tenant_id: TenantId,
    pub account_id: Option<EntityId>,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub phone: Option<String>,
    pub job_title: Option<String>,
    pub department: Option<String>,
    pub is_primary: bool,
    pub is_active: bool,
    pub notes: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<Contact> for ContactResponse {
    fn from(c: Contact) -> Self {
        Self {
            id: c.id,
            tenant_id: c.tenant_id,
            account_id: c.account_id,
            first_name: c.first_name,
            last_name: c.last_name,
            email: c.email,
            phone: c.phone,
            job_title: c.job_title,
            department: c.department,
            is_primary: c.is_primary,
            is_active: c.is_active,
            notes: c.notes,
            created_at: c.created_at,
            updated_at: c.updated_at,
        }
    }
}

/// List all contacts (paginated, filterable by account).
pub async fn list_contacts(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListContactsParams>,
) -> Result<Json<PaginatedResponse<ContactResponse>>> {
    user.require_permission("sales:account:read")?;
    let tenant_id = user.tenant_id;
    let result = state
        .contacts_service
        .list_contacts(tenant_id, params.account_id, params.page, params.per_page)
        .await?;
    let data: Vec<ContactResponse> = result.data.into_iter().map(ContactResponse::from).collect();
    Ok(Json(PaginatedResponse {
        data,
        total: result.total,
        page: result.page,
        per_page: result.per_page,
        total_pages: result.total_pages,
    }))
}

/// Create a new contact.
pub async fn create_contact(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ContactRequest>,
) -> Result<Json<ContactResponse>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    let contact = Contact {
        id: EntityId::default(),
        tenant_id,
        account_id: req.account_id,
        first_name: req.first_name,
        last_name: req.last_name,
        email: req.email,
        phone: req.phone,
        job_title: req.job_title,
        department: req.department,
        is_primary: req.is_primary.unwrap_or(false),
        is_active: req.is_active.unwrap_or(true),
        notes: req.notes,
        created_at: now(),
        updated_at: now(),
    };
    let created = state
        .contacts_service
        .create_contact(tenant_id, contact)
        .await?;
    Ok(Json(ContactResponse::from(created)))
}

/// Get a contact by ID.
pub async fn get_contact(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ContactResponse>> {
    user.require_permission("sales:account:read")?;
    let tenant_id = user.tenant_id;
    let contact = state.contacts_service.get_contact(tenant_id, id).await?;
    Ok(Json(ContactResponse::from(contact)))
}

/// Update a contact.
///
/// Preserves the original `created_at` and keeps the current `is_active`
/// unless the request explicitly provides a new value.
pub async fn update_contact(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ContactRequest>,
) -> Result<Json<ContactResponse>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    let existing = state.contacts_service.get_contact(tenant_id, id).await?;
    let contact = Contact {
        id,
        tenant_id,
        account_id: req.account_id,
        first_name: req.first_name,
        last_name: req.last_name,
        email: req.email,
        phone: req.phone,
        job_title: req.job_title,
        department: req.department,
        is_primary: req.is_primary.unwrap_or(existing.is_primary),
        is_active: req.is_active.unwrap_or(existing.is_active),
        notes: req.notes,
        created_at: existing.created_at,
        updated_at: now(),
    };
    let updated = state
        .contacts_service
        .update_contact(tenant_id, id, contact)
        .await?;
    Ok(Json(ContactResponse::from(updated)))
}

/// Delete (deactivate) a contact.
pub async fn delete_contact(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    user.require_permission("sales:account:manage")?;
    let tenant_id = user.tenant_id;
    state.contacts_service.delete_contact(tenant_id, id).await?;
    Ok(Json(serde_json::json!({
        "message": format!("Contact {id} deactivated successfully")
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
        let roles = vec![
            "user".to_string(),
            "tenant_admin".to_string(),
            "production_manager".to_string(),
            "quality_manager".to_string(),
            "purchasing_manager".to_string(),
            "sales_manager".to_string(),
            "finance_manager".to_string(),
            "inventory_manager".to_string(),
            "operator".to_string(),
        ];
        AuthenticatedUser {
            user_id,
            tenant_id,
            roles: roles.clone(),
            sid: None,
            // Explicit permissions (thirtieth-audit P0-10): require_permission
            // no longer falls back to the global registry, so direct
            // constructions carry the static expansion of their roles.
            permissions: sensei_auth::rbac::RbacService::new().expand_static(&roles),
        }
    }

    #[tokio::test]
    async fn test_create_contact() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "John".to_string(),
            last_name: "Doe".to_string(),
            email: "john@test.com".to_string(),
            phone: Some("+1-555-1111".to_string()),
            job_title: Some("Engineer".to_string()),
            department: Some("Engineering".to_string()),
            is_primary: Some(true),
            notes: Some("Test contact".to_string()),
            is_active: None,
        };
        let resp = create_contact(user, State(state.clone()), Json(req))
            .await
            .unwrap();
        assert_eq!(resp.first_name, "John");
        assert_eq!(resp.last_name, "Doe");
        assert_eq!(resp.email, "john@test.com");
        assert!(resp.is_primary);
        assert!(resp.is_active);
    }

    #[tokio::test]
    async fn test_get_contact() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "Jane".to_string(),
            last_name: "Smith".to_string(),
            email: "jane@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let created = create_contact(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = get_contact(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(resp.first_name, "Jane");
    }

    #[tokio::test]
    async fn test_get_contact_not_found() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let result = get_contact(user, State(state.clone()), Path(EntityId::new_v4())).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_list_contacts() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "List".to_string(),
            last_name: "User".to_string(),
            email: "list@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let _ = create_contact(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let params = ListContactsParams {
            account_id: None,
            page: None,
            per_page: None,
        };
        let resp = list_contacts(user, State(state.clone()), Query(params))
            .await
            .unwrap();
        assert_eq!(resp.total, 1);
    }

    #[tokio::test]
    async fn test_update_contact() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "Old".to_string(),
            last_name: "Name".to_string(),
            email: "old@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let created = create_contact(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let update_req = ContactRequest {
            account_id: None,
            first_name: "Updated".to_string(),
            last_name: "Name".to_string(),
            email: "updated@test.com".to_string(),
            phone: None,
            job_title: Some("Manager".to_string()),
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let resp = update_contact(
            user,
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(resp.first_name, "Updated");
        assert_eq!(resp.job_title, Some("Manager".to_string()));
    }

    #[tokio::test]
    async fn test_delete_contact() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "Del".to_string(),
            last_name: "User".to_string(),
            email: "del@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let created = create_contact(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = delete_contact(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(resp.get("message").is_some());
        // Verify it's soft-deleted (is_active = false)
        let get_resp = get_contact(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(!get_resp.is_active);
    }

    #[tokio::test]
    async fn test_update_contact_preserves_created_at_and_is_active() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ContactRequest {
            account_id: None,
            first_name: "Keep".to_string(),
            last_name: "Active".to_string(),
            email: "keep@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: Some(false),
        };
        let created = create_contact(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        assert!(!created.is_active);

        // Updating without is_active keeps the current value and preserves
        // created_at.
        let update_req = ContactRequest {
            account_id: None,
            first_name: "Kept".to_string(),
            last_name: "Active".to_string(),
            email: "keep@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: None,
        };
        let updated = update_contact(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(updated.created_at, created.created_at);
        assert!(!updated.is_active);

        // An explicit is_active=true must reactivate the contact.
        let reactivate_req = ContactRequest {
            account_id: None,
            first_name: "Kept".to_string(),
            last_name: "Active".to_string(),
            email: "keep@test.com".to_string(),
            phone: None,
            job_title: None,
            department: None,
            is_primary: None,
            notes: None,
            is_active: Some(true),
        };
        let reactivated = update_contact(
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
