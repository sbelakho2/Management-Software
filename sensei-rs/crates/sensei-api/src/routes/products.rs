//! Products route handlers.
//!
//! Provides CRUD endpoints for product/service catalog management.

use axum::{
    extract::{Path, Query, State},
    Json,
};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::domain::entities::Product;
use sensei_core::error::Result;
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;

/// Query parameters for listing products.
#[derive(Debug, Deserialize)]
pub struct ListProductsParams {
    pub category: Option<String>,
    pub product_type: Option<String>,
    pub page: Option<usize>,
    pub per_page: Option<usize>,
}

/// Request body for creating/updating a product.
#[derive(Debug, Deserialize)]
pub struct ProductRequest {
    pub sku: String,
    pub name: String,
    pub description: Option<String>,
    pub category: Option<String>,
    pub product_type: String,
    pub unit_of_measure: String,
    pub standard_cost: Option<f64>,
    pub selling_price: Option<f64>,
    pub min_stock_level: Option<f64>,
    pub max_stock_level: Option<f64>,
    pub current_stock: Option<f64>,
    /// Active state (defaults to `true` on create; keeps the stored value
    /// on update when omitted).
    pub is_active: Option<bool>,
    pub notes: Option<String>,
}

/// Product response.
#[derive(Debug, Serialize)]
pub struct ProductResponse {
    pub id: EntityId,
    pub tenant_id: TenantId,
    pub sku: String,
    pub name: String,
    pub description: Option<String>,
    pub category: Option<String>,
    pub product_type: String,
    pub unit_of_measure: String,
    pub standard_cost: Option<f64>,
    pub selling_price: Option<f64>,
    pub min_stock_level: Option<f64>,
    pub max_stock_level: Option<f64>,
    pub current_stock: f64,
    pub is_active: bool,
    pub notes: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

impl From<Product> for ProductResponse {
    fn from(p: Product) -> Self {
        Self {
            id: p.id,
            tenant_id: p.tenant_id,
            sku: p.sku,
            name: p.name,
            description: p.description,
            category: p.category,
            product_type: p.product_type,
            unit_of_measure: p.unit_of_measure,
            standard_cost: p.standard_cost,
            selling_price: p.selling_price,
            min_stock_level: p.min_stock_level,
            max_stock_level: p.max_stock_level,
            current_stock: p.current_stock,
            is_active: p.is_active,
            notes: p.notes,
            created_at: p.created_at,
            updated_at: p.updated_at,
        }
    }
}

/// List all products (paginated, filterable by category/type).
pub async fn list_products(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Query(params): Query<ListProductsParams>,
) -> Result<Json<PaginatedResponse<ProductResponse>>> {
    let tenant_id = user.tenant_id;
    let result = state
        .products_service
        .list_products(
            tenant_id,
            params.category.as_deref(),
            params.product_type.as_deref(),
            params.page,
            params.per_page,
        )
        .await?;
    let data: Vec<ProductResponse> = result.data.into_iter().map(ProductResponse::from).collect();
    Ok(Json(PaginatedResponse {
        data,
        total: result.total,
        page: result.page,
        per_page: result.per_page,
        total_pages: result.total_pages,
    }))
}

/// Create a new product.
pub async fn create_product(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Json(req): Json<ProductRequest>,
) -> Result<Json<ProductResponse>> {
    let tenant_id = user.tenant_id;
    let product = Product {
        id: EntityId::default(),
        tenant_id,
        sku: req.sku,
        name: req.name,
        description: req.description,
        category: req.category,
        product_type: req.product_type,
        unit_of_measure: req.unit_of_measure,
        standard_cost: req.standard_cost,
        selling_price: req.selling_price,
        min_stock_level: req.min_stock_level,
        max_stock_level: req.max_stock_level,
        current_stock: req.current_stock.unwrap_or(0.0),
        is_active: req.is_active.unwrap_or(true),
        notes: req.notes,
        created_at: now(),
        updated_at: now(),
    };
    let created = state
        .products_service
        .create_product(tenant_id, product)
        .await?;
    Ok(Json(ProductResponse::from(created)))
}

/// Get a product by ID.
pub async fn get_product(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<ProductResponse>> {
    let tenant_id = user.tenant_id;
    let product = state.products_service.get_product(tenant_id, id).await?;
    Ok(Json(ProductResponse::from(product)))
}

/// Update a product.
pub async fn update_product(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(req): Json<ProductRequest>,
) -> Result<Json<ProductResponse>> {
    let tenant_id = user.tenant_id;
    // Fetch the stored product so creation timestamps and the active flag
    // (when not overridden) survive the update.
    let existing = state.products_service.get_product(tenant_id, id).await?;
    let product = Product {
        id,
        tenant_id,
        sku: req.sku,
        name: req.name,
        description: req.description,
        category: req.category,
        product_type: req.product_type,
        unit_of_measure: req.unit_of_measure,
        standard_cost: req.standard_cost,
        selling_price: req.selling_price,
        min_stock_level: req.min_stock_level,
        max_stock_level: req.max_stock_level,
        current_stock: req.current_stock.unwrap_or(existing.current_stock),
        is_active: req.is_active.unwrap_or(existing.is_active),
        notes: req.notes,
        created_at: existing.created_at,
        updated_at: now(),
    };
    let updated = state
        .products_service
        .update_product(tenant_id, id, product)
        .await?;
    Ok(Json(ProductResponse::from(updated)))
}

/// Delete (deactivate) a product.
pub async fn delete_product(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<Json<serde_json::Value>> {
    let tenant_id = user.tenant_id;
    state.products_service.delete_product(tenant_id, id).await?;
    Ok(Json(serde_json::json!({
        "message": format!("Product {id} deactivated successfully")
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
            roles: vec!["admin".to_string()],
            sid: None,
        }
    }

    #[tokio::test]
    async fn test_create_product() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-001".to_string(),
            name: "Test Widget".to_string(),
            description: Some("A widget".to_string()),
            category: Some("Widgets".to_string()),
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: Some(10.0),
            selling_price: Some(25.0),
            min_stock_level: Some(5.0),
            max_stock_level: Some(100.0),
            current_stock: Some(50.0),
            is_active: None,
            notes: Some("Test product".to_string()),
        };
        let resp = create_product(user, State(state.clone()), Json(req))
            .await
            .unwrap();
        assert_eq!(resp.sku, "SKU-001");
        assert_eq!(resp.name, "Test Widget");
        assert_eq!(resp.current_stock, 50.0);
        assert!(resp.is_active);
    }

    #[tokio::test]
    async fn test_get_product() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-002".to_string(),
            name: "Get Widget".to_string(),
            description: None,
            category: None,
            product_type: "raw".to_string(),
            unit_of_measure: "kg".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: None,
            notes: None,
        };
        let created = create_product(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = get_product(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert_eq!(resp.name, "Get Widget");
    }

    #[tokio::test]
    async fn test_get_product_not_found() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let result = get_product(user, State(state.clone()), Path(EntityId::new_v4())).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_list_products() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-003".to_string(),
            name: "List Widget".to_string(),
            description: None,
            category: Some("Gadgets".to_string()),
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: None,
            notes: None,
        };
        let _ = create_product(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let params = ListProductsParams {
            category: None,
            product_type: None,
            page: None,
            per_page: None,
        };
        let resp = list_products(user, State(state.clone()), Query(params))
            .await
            .unwrap();
        assert_eq!(resp.total, 1);
    }

    #[tokio::test]
    async fn test_update_product() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-004".to_string(),
            name: "Old Name".to_string(),
            description: None,
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: None,
            notes: None,
        };
        let created = create_product(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let update_req = ProductRequest {
            sku: "SKU-004".to_string(),
            name: "Updated Name".to_string(),
            description: Some("Updated desc".to_string()),
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: Some(15.0),
            selling_price: Some(30.0),
            min_stock_level: Some(10.0),
            max_stock_level: Some(200.0),
            current_stock: Some(75.0),
            is_active: None,
            notes: None,
        };
        let resp = update_product(
            user,
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(resp.name, "Updated Name");
        assert_eq!(resp.standard_cost, Some(15.0));
        assert_eq!(resp.current_stock, 75.0);
    }

    #[tokio::test]
    async fn test_update_product_preserves_created_at_and_is_active() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-004A".to_string(),
            name: "Original".to_string(),
            description: None,
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: Some(false),
            notes: None,
        };
        let created = create_product(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        assert!(!created.is_active, "create must honor is_active=false");

        let update_req = ProductRequest {
            sku: "SKU-004A".to_string(),
            name: "Renamed".to_string(),
            description: None,
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: None,
            notes: None,
        };
        let resp = update_product(
            user.clone(),
            State(state.clone()),
            Path(created.id),
            Json(update_req),
        )
        .await
        .unwrap();
        assert_eq!(
            resp.created_at, created.created_at,
            "created_at must be preserved"
        );
        assert!(
            !resp.is_active,
            "is_active must be preserved when not overridden"
        );

        // Explicit is_active=true in the request must flip it back.
        let reactivate = ProductRequest {
            sku: "SKU-004A".to_string(),
            name: "Renamed".to_string(),
            description: None,
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: Some(true),
            notes: None,
        };
        let resp = update_product(
            user,
            State(state.clone()),
            Path(created.id),
            Json(reactivate),
        )
        .await
        .unwrap();
        assert!(resp.is_active);
    }

    #[tokio::test]
    async fn test_delete_product() {
        let (state, tid, uid) = test_state().await;
        let user = auth_user(tid, uid);
        let req = ProductRequest {
            sku: "SKU-005".to_string(),
            name: "Del Widget".to_string(),
            description: None,
            category: None,
            product_type: "finished".to_string(),
            unit_of_measure: "pcs".to_string(),
            standard_cost: None,
            selling_price: None,
            min_stock_level: None,
            max_stock_level: None,
            current_stock: None,
            is_active: None,
            notes: None,
        };
        let created = create_product(user.clone(), State(state.clone()), Json(req))
            .await
            .unwrap();
        let resp = delete_product(user.clone(), State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(resp.get("message").is_some());
        // Verify it's soft-deleted (is_active = false)
        let get_resp = get_product(user, State(state.clone()), Path(created.id))
            .await
            .unwrap();
        assert!(!get_resp.is_active);
    }
}
