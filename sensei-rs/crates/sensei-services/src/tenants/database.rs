//! PostgreSQL-backed tenants service using sqlx.
//!
//! Provides tenant/organization management backed by the `tenants` database table.
//! Implements the [`TenantsService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::entities::Tenant;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::TenantId;
use sensei_db::models::TenantModel;
use sqlx::PgPool;

use crate::tenants::TenantsService;

/// PostgreSQL-backed implementation of [`TenantsService`].
pub struct DatabaseTenantsService {
    pool: PgPool,
}

impl DatabaseTenantsService {
    /// Create a new [`DatabaseTenantsService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Convert a database [`TenantModel`] into a domain [`Tenant`].
///
/// A corrupt JSONB `features` payload is logged and surfaced as a database
/// error — it is never silently replaced with an empty feature list.
fn tenant_model_to_domain(m: TenantModel) -> Result<Tenant> {
    let features: Vec<String> = serde_json::from_value(m.features.clone()).map_err(|e| {
        tracing::error!(tenant_id = %m.id, "Tenant features JSONB is corrupt: {e}");
        SenseiError::Database(format!("Tenant {} has corrupt features: {e}", m.id))
    })?;
    Ok(Tenant {
        id: m.id,
        name: m.name,
        slug: m.slug,
        is_active: m.is_active,
        features,
        created_at: m.created_at,
        updated_at: m.updated_at,
    })
}

#[async_trait]
impl TenantsService for DatabaseTenantsService {
    async fn create_tenant(&self, tenant: Tenant) -> Result<Tenant> {
        let now = Utc::now();
        let features_json = serde_json::to_value(&tenant.features)
            .map_err(|e| SenseiError::Serialization(e.to_string()))?;

        let model = sqlx::query_as::<_, TenantModel>(
            r#"
            INSERT INTO tenants (id, name, slug, is_active, features, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, name, slug, is_active, features, created_at, updated_at
            "#,
        )
        .bind(tenant.id)
        .bind(&tenant.name)
        .bind(&tenant.slug)
        .bind(tenant.is_active)
        .bind(&features_json)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create tenant: {e}")))?;

        tenant_model_to_domain(model)
    }

    async fn get_tenant(&self, id: TenantId) -> Result<Tenant> {
        let model = sqlx::query_as::<_, TenantModel>(
            "SELECT id, name, slug, is_active, features, created_at, updated_at FROM tenants WHERE id = $1",
        )
        .bind(id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get tenant: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Tenant {id} not found")))?;

        tenant_model_to_domain(model)
    }

    async fn list_tenants(&self) -> Result<Vec<Tenant>> {
        let models = sqlx::query_as::<_, TenantModel>(
            "SELECT id, name, slug, is_active, features, created_at, updated_at FROM tenants ORDER BY created_at DESC",
        )
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to list tenants: {e}")))?;

        models
            .into_iter()
            .map(tenant_model_to_domain)
            .collect::<Result<Vec<_>>>()
    }

    async fn update_tenant(&self, id: TenantId, tenant: Tenant) -> Result<Tenant> {
        let now = Utc::now();
        let features_json = serde_json::to_value(&tenant.features)
            .map_err(|e| SenseiError::Serialization(e.to_string()))?;

        let model = sqlx::query_as::<_, TenantModel>(
            r#"
            UPDATE tenants
            SET name = $2, slug = $3, is_active = $4, features = $5, updated_at = $6
            WHERE id = $1
            RETURNING id, name, slug, is_active, features, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(&tenant.name)
        .bind(&tenant.slug)
        .bind(tenant.is_active)
        .bind(&features_json)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update tenant: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Tenant {id} not found")))?;

        tenant_model_to_domain(model)
    }
}
