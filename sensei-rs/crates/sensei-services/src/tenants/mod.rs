//! Tenants domain service.
//!
//! Provides tenant/organization management for the multi-tenant system.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::Tenant;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{TenantId, now};
use std::collections::HashMap;
use tokio::sync::RwLock;

mod database;
pub use database::DatabaseTenantsService;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Tenant management service.
#[async_trait]
pub trait TenantsService: Send + Sync {
    /// Create a new tenant.
    async fn create_tenant(&self, tenant: Tenant) -> Result<Tenant>;

    /// Get a tenant by ID.
    async fn get_tenant(&self, id: TenantId) -> Result<Tenant>;

    /// List all tenants.
    async fn list_tenants(&self) -> Result<Vec<Tenant>>;

    /// Update a tenant.
    async fn update_tenant(&self, id: TenantId, tenant: Tenant) -> Result<Tenant>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`TenantsService`].
pub struct InMemoryTenantsService {
    tenants: RwLock<HashMap<TenantId, Tenant>>,
}

impl InMemoryTenantsService {
    /// Create a new empty [`InMemoryTenantsService`].
    pub fn new() -> Self {
        Self {
            tenants: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryTenantsService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl TenantsService for InMemoryTenantsService {
    async fn create_tenant(&self, mut tenant: Tenant) -> Result<Tenant> {
        tenant.id = sensei_core::types::new_id();
        tenant.created_at = now();
        tenant.updated_at = now();
        let id = tenant.id;
        self.tenants.write().await.insert(id, tenant.clone());
        Ok(tenant)
    }

    async fn get_tenant(&self, id: TenantId) -> Result<Tenant> {
        let store = self.tenants.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Tenant {id} not found")))
    }

    async fn list_tenants(&self) -> Result<Vec<Tenant>> {
        let store = self.tenants.read().await;
        Ok(store.values().cloned().collect())
    }

    async fn update_tenant(&self, id: TenantId, tenant: Tenant) -> Result<Tenant> {
        let mut store = self.tenants.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Tenant {id} not found")))?;

        existing.name = tenant.name;
        existing.slug = tenant.slug;
        existing.is_active = tenant.is_active;
        existing.features = tenant.features;
        existing.updated_at = now();

        Ok(existing.clone())
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::entities::Tenant;
    use uuid::Uuid;

    fn make_service() -> InMemoryTenantsService {
        InMemoryTenantsService::new()
    }

    #[tokio::test]
    async fn test_create_and_get_tenant() {
        let svc = make_service();
        let tenant = Tenant::new("Acme Corp".into(), "acme".into());

        let created = svc.create_tenant(tenant).await.unwrap();
        assert_eq!(created.name, "Acme Corp");
        assert_eq!(created.slug, "acme");
        assert!(created.is_active);

        let fetched = svc.get_tenant(created.id).await.unwrap();
        assert_eq!(fetched.name, "Acme Corp");
        assert_eq!(fetched.id, created.id);
    }

    #[tokio::test]
    async fn test_get_tenant_not_found() {
        let svc = make_service();
        let err = svc.get_tenant(Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_list_tenants() {
        let svc = make_service();

        svc.create_tenant(Tenant::new("Alpha".into(), "alpha".into()))
            .await.unwrap();
        svc.create_tenant(Tenant::new("Beta".into(), "beta".into()))
            .await.unwrap();

        let list = svc.list_tenants().await.unwrap();
        assert_eq!(list.len(), 2);
    }

    #[tokio::test]
    async fn test_update_tenant() {
        let svc = make_service();
        let created = svc
            .create_tenant(Tenant::new("Old Name".into(), "old-slug".into()))
            .await
            .unwrap();

        let mut upd = created.clone();
        upd.name = "New Name".into();
        upd.slug = "new-slug".into();

        let result = svc.update_tenant(created.id, upd).await.unwrap();
        assert_eq!(result.name, "New Name");
        assert_eq!(result.slug, "new-slug");
    }

    #[tokio::test]
    async fn test_update_tenant_not_found() {
        let svc = make_service();
        let err = svc
            .update_tenant(Uuid::new_v4(), Tenant::new("Nope".into(), "nope".into()))
            .await
            .unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_tenant_initial_features_empty() {
        let svc = make_service();
        let created = svc
            .create_tenant(Tenant::new("Empty Features".into(), "empty".into()))
            .await
            .unwrap();
        assert!(created.features.is_empty());
    }

    #[tokio::test]
    async fn test_tenant_with_features() {
        let svc = make_service();
        let mut tenant = Tenant::new("Full Feat".into(), "full".into());
        tenant.features = vec!["quality".into(), "finance".into()];

        let created = svc.create_tenant(tenant).await.unwrap();
        assert_eq!(
            created.features,
            vec!["quality".to_string(), "finance".to_string()]
        );
    }

    #[tokio::test]
    async fn test_tenant_lifecycle() {
        let svc = make_service();

        let t = svc
            .create_tenant(Tenant::new("Lifecycle".into(), "lc".into()))
            .await
            .unwrap();
        assert!(t.is_active);

        // Deactivate via update.
        let mut upd = t.clone();
        upd.is_active = false;
        let deactivated = svc.update_tenant(t.id, upd).await.unwrap();
        assert!(!deactivated.is_active);

        // Reactivate via update.
        let mut upd2 = deactivated.clone();
        upd2.is_active = true;
        let reactivated = svc.update_tenant(t.id, upd2).await.unwrap();
        assert!(reactivated.is_active);
    }
}
