//! Typed plant-topology repository (P1-1): the relational sites /
//! value_streams / product_families tables are authoritative — the generic
//! EntityStore JSON path cannot enforce "site exists, same tenant, active"
//! at the database level.

use crate::routes::topology::{ProductFamily, Site, ValueStream};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

#[derive(Clone)]
pub struct TopologyRepository {
    pool: Option<sqlx::PgPool>,
    memory_sites: Arc<RwLock<HashMap<Uuid, Site>>>,
    memory_streams: Arc<RwLock<HashMap<Uuid, ValueStream>>>,
    memory_families: Arc<RwLock<HashMap<Uuid, ProductFamily>>>,
}

impl TopologyRepository {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory_sites: Arc::new(RwLock::new(HashMap::new())),
            memory_streams: Arc::new(RwLock::new(HashMap::new())),
            memory_families: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn attach_pool(mut self, pool: sqlx::PgPool) -> Self {
        self.pool = Some(pool);
        self
    }

    // ── Sites ─────────────────────────────────────────────────────────
    pub async fn put_site(&self, site: &Site) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO sites (id, tenant_id, site_code, name, address, timezone, is_active) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7) \
                 ON CONFLICT (tenant_id, site_code) DO UPDATE \
                 SET name = $4, address = $5, timezone = $6, is_active = $7",
            )
            .bind(site.id)
            .bind(site.tenant_id)
            .bind(&site.site_code)
            .bind(&site.name)
            .bind(&site.address)
            .bind(&site.timezone)
            .bind(site.is_active)
            .execute(pool)
            .await
            .map_err(|e| format!("Site persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_sites
            .write()
            .await
            .insert(site.id, site.clone());
        Ok(())
    }

    pub async fn list_sites(&self, tenant_id: Uuid) -> Result<Vec<Site>, String> {
        if let Some(pool) = &self.pool {
            let rows: Vec<Site> = sqlx::query_as(
                "SELECT id, tenant_id, site_code, name, address, timezone, is_active \
                 FROM sites WHERE tenant_id = $1 ORDER BY site_code",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Site list failed: {e}"))?;
            return Ok(rows);
        }
        let mut out: Vec<Site> = self
            .memory_sites
            .read()
            .await
            .values()
            .filter(|s| s.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by(|a, b| a.site_code.cmp(&b.site_code));
        Ok(out)
    }

    // ── Value streams (same-tenant site FK enforced by SQL) ───────────
    pub async fn put_value_stream(&self, vs: &ValueStream) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO value_streams (id, tenant_id, site_id, name, description, is_active) \
                 VALUES ($1, $2, $3, $4, $5, $6) \
                 ON CONFLICT (tenant_id, site_id, name) DO UPDATE \
                 SET description = $5, is_active = $6",
            )
            .bind(vs.id)
            .bind(vs.tenant_id)
            .bind(vs.site_id)
            .bind(&vs.name)
            .bind(&vs.description)
            .bind(vs.is_active)
            .execute(pool)
            .await
            .map_err(|e| {
                format!("Value-stream persist failed (site must exist in the same tenant): {e}")
            })?;
            return Ok(());
        }
        self.memory_streams.write().await.insert(vs.id, vs.clone());
        Ok(())
    }

    pub async fn list_value_streams(&self, tenant_id: Uuid) -> Result<Vec<ValueStream>, String> {
        if let Some(pool) = &self.pool {
            let rows: Vec<ValueStream> = sqlx::query_as(
                "SELECT id, tenant_id, site_id, name, description, is_active \
                 FROM value_streams WHERE tenant_id = $1 ORDER BY name",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Value-stream list failed: {e}"))?;
            return Ok(rows);
        }
        let mut out: Vec<ValueStream> = self
            .memory_streams
            .read()
            .await
            .values()
            .filter(|s| s.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by(|a, b| a.name.cmp(&b.name));
        Ok(out)
    }

    // ── Product families ──────────────────────────────────────────────
    pub async fn put_product_family(&self, pf: &ProductFamily) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO product_families (id, tenant_id, site_id, name, description, is_active) \
                 VALUES ($1, $2, $3, $4, $5, $6) \
                 ON CONFLICT (tenant_id, site_id, name) DO UPDATE \
                 SET description = $5, is_active = $6",
            )
            .bind(pf.id)
            .bind(pf.tenant_id)
            .bind(pf.site_id)
            .bind(&pf.name)
            .bind(&pf.description)
            .bind(pf.is_active)
            .execute(pool)
            .await
            .map_err(|e| format!("Product-family persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_families.write().await.insert(pf.id, pf.clone());
        Ok(())
    }

    pub async fn list_product_families(
        &self,
        tenant_id: Uuid,
    ) -> Result<Vec<ProductFamily>, String> {
        if let Some(pool) = &self.pool {
            let rows: Vec<ProductFamily> = sqlx::query_as(
                "SELECT id, tenant_id, site_id, name, description, is_active \
                 FROM product_families WHERE tenant_id = $1 ORDER BY name",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Product-family list failed: {e}"))?;
            return Ok(rows);
        }
        let mut out: Vec<ProductFamily> = self
            .memory_families
            .read()
            .await
            .values()
            .filter(|f| f.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by(|a, b| a.name.cmp(&b.name));
        Ok(out)
    }
}
