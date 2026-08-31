//! TenantTx (sixteenth audit items 21/83): the typed tenant database
//! handle. Only this type exposes tenant-owned repositories — a raw
//! PgPool cannot be used for tenant-domain reads without an explicit
//! TenantTx, which makes the SET LOCAL app.tenant_id context
//! construction-time, not a per-function afterthought.

use sqlx::postgres::PgPool;
use sqlx::{PgConnection, Postgres, Transaction};
use uuid::Uuid;

pub struct TenantTx<'a> {
    tx: Transaction<'a, Postgres>,
    pub tenant_id: Uuid,
}

impl<'a> TenantTx<'a> {
    /// Begin a tenant-scoped transaction: SET LOCAL app.tenant_id is
    /// established HERE — every statement on this handle is admitted by
    /// FORCE RLS for exactly this tenant.
    pub async fn begin(pool: &PgPool, tenant_id: Uuid) -> Result<Self, String> {
        let mut tx = pool.begin().await.map_err(|e| e.to_string())?;
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .map_err(|e| e.to_string())?;
        Ok(Self { tx, tenant_id })
    }

    pub fn tx(&mut self) -> &mut Transaction<'a, Postgres> {
        &mut self.tx
    }

    /// Escape hatch for sqlx queries that need the raw connection.
    pub fn conn(&mut self) -> &mut PgConnection {
        self.tx.as_mut()
    }

    pub async fn commit(self) -> Result<(), String> {
        self.tx.commit().await.map_err(|e| e.to_string())
    }

    pub async fn rollback(self) -> Result<(), String> {
        self.tx.rollback().await.map_err(|e| e.to_string())
    }
}
