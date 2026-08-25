//! Products domain service.
//!
//! Provides product/service catalog management.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::Product;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use std::collections::HashMap;
use tokio::sync::RwLock;

mod database;
pub use database::DatabaseProductsService;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Product management service.
#[async_trait]
pub trait ProductsService: Send + Sync {
    /// Create a new product.
    async fn create_product(&self, tenant_id: TenantId, product: Product) -> Result<Product>;

    /// Get a product by ID.
    async fn get_product(&self, tenant_id: TenantId, id: EntityId) -> Result<Product>;

    /// List products with optional category/type filter and pagination.
    async fn list_products(
        &self,
        tenant_id: TenantId,
        category: Option<&str>,
        product_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Product>>;

    /// Update a product.
    async fn update_product(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        product: Product,
    ) -> Result<Product>;

    /// Delete (deactivate) a product.
    async fn delete_product(&self, tenant_id: TenantId, id: EntityId) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`ProductsService`].
pub struct InMemoryProductsService {
    products: RwLock<HashMap<EntityId, Product>>,
}

impl InMemoryProductsService {
    /// Create a new empty [`InMemoryProductsService`].
    pub fn new() -> Self {
        Self {
            products: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryProductsService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ProductsService for InMemoryProductsService {
    async fn create_product(&self, tenant_id: TenantId, mut product: Product) -> Result<Product> {
        product.id = sensei_core::types::new_id();
        product.tenant_id = tenant_id;
        product.created_at = now();
        product.updated_at = now();
        let id = product.id;
        self.products.write().await.insert(id, product.clone());
        Ok(product)
    }

    async fn get_product(&self, _tenant_id: TenantId, id: EntityId) -> Result<Product> {
        let store = self.products.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Product {id} not found")))
    }

    async fn list_products(
        &self,
        tenant_id: TenantId,
        category: Option<&str>,
        product_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Product>> {
        let store = self.products.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|p| {
                p.tenant_id == tenant_id
                    && category.is_none_or(|c| p.category.as_deref() == Some(c))
                    && product_type.is_none_or(|t| p.product_type == t)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_product(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        product: Product,
    ) -> Result<Product> {
        let mut store = self.products.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Product {id} not found")))?;

        if existing.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        existing.sku = product.sku;
        existing.name = product.name;
        existing.description = product.description;
        existing.category = product.category;
        existing.product_type = product.product_type;
        existing.unit_of_measure = product.unit_of_measure;
        existing.standard_cost = product.standard_cost;
        existing.selling_price = product.selling_price;
        existing.min_stock_level = product.min_stock_level;
        existing.max_stock_level = product.max_stock_level;
        existing.current_stock = product.current_stock;
        existing.is_active = product.is_active;
        existing.notes = product.notes;
        existing.updated_at = now();

        Ok(existing.clone())
    }

    async fn delete_product(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let mut store = self.products.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Product {id} not found")))?;

        if existing.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        existing.is_active = false;
        existing.updated_at = now();
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::entities::Product;
    use uuid::Uuid;

    fn make_service() -> InMemoryProductsService {
        InMemoryProductsService::new()
    }

    fn tenant_id() -> TenantId {
        Uuid::parse_str("11111111-1111-1111-1111-111111111111").unwrap()
    }

    fn other_tenant() -> TenantId {
        Uuid::parse_str("22222222-2222-2222-2222-222222222222").unwrap()
    }

    fn sample_product(tid: TenantId) -> Product {
        Product::new(
            tid,
            "SKU-001".into(),
            "Widget".into(),
            "finished_good".into(),
            "pcs".into(),
        )
    }

    #[tokio::test]
    async fn test_create_and_get_product() {
        let svc = make_service();
        let tid = tenant_id();
        let product = sample_product(tid);

        let created = svc.create_product(tid, product).await.unwrap();
        assert_eq!(created.sku, "SKU-001");
        assert_eq!(created.name, "Widget");
        assert!(created.is_active);

        let fetched = svc.get_product(tid, created.id).await.unwrap();
        assert_eq!(fetched.sku, "SKU-001");
    }

    #[tokio::test]
    async fn test_get_product_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.get_product(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_list_products() {
        let svc = make_service();
        let tid = tenant_id();

        let mut p1 = sample_product(tid);
        p1.category = Some("Electronics".into());
        let mut p2 = sample_product(tid);
        p2.sku = "SKU-002".into();
        p2.name = "Gadget".into();
        p2.category = Some("Electronics".into());
        p2.product_type = "subassembly".into();
        let mut p3 = sample_product(tid);
        p3.sku = "SKU-003".into();
        p3.name = "Service A".into();
        p3.category = Some("Services".into());
        p3.product_type = "service".into();

        svc.create_product(tid, p1).await.unwrap();
        svc.create_product(tid, p2).await.unwrap();
        svc.create_product(tid, p3).await.unwrap();

        // All products.
        let all = svc
            .list_products(tid, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(all.data.len(), 3);

        // Filter by category.
        let electronics = svc
            .list_products(tid, Some("Electronics"), None, None, None)
            .await
            .unwrap();
        assert_eq!(electronics.data.len(), 2);

        // Filter by product_type.
        let services = svc
            .list_products(tid, None, Some("service"), None, None)
            .await
            .unwrap();
        assert_eq!(services.data.len(), 1);

        // Pagination.
        let paged = svc
            .list_products(tid, None, None, Some(1), Some(2))
            .await
            .unwrap();
        assert_eq!(paged.data.len(), 2);
        assert_eq!(paged.total, 3);
    }

    #[tokio::test]
    async fn test_list_products_tenant_isolation() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();

        svc.create_product(t1, sample_product(t1)).await.unwrap();
        svc.create_product(t2, sample_product(t2)).await.unwrap();

        let t1_list = svc.list_products(t1, None, None, None, None).await.unwrap();
        assert_eq!(t1_list.data.len(), 1);

        let t2_list = svc.list_products(t2, None, None, None, None).await.unwrap();
        assert_eq!(t2_list.data.len(), 1);
    }

    #[tokio::test]
    async fn test_update_product() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc.create_product(tid, sample_product(tid)).await.unwrap();

        let mut upd = created.clone();
        upd.name = "Super Widget".into();
        upd.selling_price = Some(29.99);

        let result = svc.update_product(tid, created.id, upd).await.unwrap();
        assert_eq!(result.name, "Super Widget");
        assert_eq!(result.selling_price, Some(29.99));
    }

    #[tokio::test]
    async fn test_update_product_cross_tenant_forbidden() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();
        let created = svc.create_product(t1, sample_product(t1)).await.unwrap();

        let err = svc
            .update_product(t2, created.id, created)
            .await
            .unwrap_err();
        assert!(err.to_string().contains("Cross-tenant") || err.to_string().contains("Forbidden"));
    }

    #[tokio::test]
    async fn test_delete_product_soft_delete() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc.create_product(tid, sample_product(tid)).await.unwrap();

        svc.delete_product(tid, created.id).await.unwrap();

        let fetched = svc.get_product(tid, created.id).await.unwrap();
        assert!(!fetched.is_active);
    }

    #[tokio::test]
    async fn test_delete_product_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.delete_product(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_product_stock_fields() {
        let svc = make_service();
        let tid = tenant_id();

        let mut p = sample_product(tid);
        p.standard_cost = Some(10.0);
        p.selling_price = Some(25.0);
        p.min_stock_level = Some(5.0);
        p.max_stock_level = Some(100.0);
        p.current_stock = 50.0;

        let created = svc.create_product(tid, p).await.unwrap();
        assert_eq!(created.standard_cost, Some(10.0));
        assert_eq!(created.current_stock, 50.0);

        // Update stock.
        let mut upd = created.clone();
        upd.current_stock = 75.0;
        let updated = svc.update_product(tid, created.id, upd).await.unwrap();
        assert_eq!(updated.current_stock, 75.0);
    }

    #[tokio::test]
    async fn test_product_lifecycle() {
        let svc = make_service();
        let tid = tenant_id();

        let p = svc.create_product(tid, sample_product(tid)).await.unwrap();
        assert!(p.is_active);

        // Soft delete
        svc.delete_product(tid, p.id).await.unwrap();
        let deleted = svc.get_product(tid, p.id).await.unwrap();
        assert!(!deleted.is_active);

        // Re-activate
        let mut upd = deleted.clone();
        upd.is_active = true;
        let reactivated = svc.update_product(tid, p.id, upd).await.unwrap();
        assert!(reactivated.is_active);
    }
}
