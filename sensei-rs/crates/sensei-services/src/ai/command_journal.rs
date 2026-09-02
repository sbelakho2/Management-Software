//! Postgres-backed execution journal (eighteenth audit P1-14): the
//! durable system of record for idempotent tool executions
//! (command_journal, migration 142). FORCE RLS makes every access
//! tenant-scoped through the transaction context.

use std::sync::Arc;

use sensei_agent_core::journal::ExecutionJournal;
use sqlx::PgPool;
use uuid::Uuid;

use crate::tps::replication::with_tenant_tx;

/// Journal backed by the `command_journal` table.
pub struct PgExecutionJournal {
    pool: PgPool,
}

impl PgExecutionJournal {
    pub fn new(pool: PgPool) -> Arc<Self> {
        Arc::new(Self { pool })
    }
}

impl ExecutionJournal for PgExecutionJournal {
    fn load(
        &self,
        tenant: Uuid,
        key: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Option<serde_json::Value>> + Send + '_>>
    {
        let pool = self.pool.clone();
        let key = key.to_string();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    let row: Option<serde_json::Value> = sqlx::query_scalar(
                        "SELECT result FROM command_journal \
                         WHERE tenant_id = $1 AND execution_key = $2",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal load failed: {e}"
                        ))
                    })?;
                    Ok(row)
                })
            })
            .await
            .ok()
            .flatten()
        })
    }

    fn store(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>> {
        let pool = self.pool.clone();
        let key = key.to_string();
        let tool = tool.to_string();
        let result = result.clone();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    sqlx::query(
                        "INSERT INTO command_journal \
                             (tenant_id, execution_key, tool_name, result) \
                         VALUES ($1, $2, $3, $4) \
                         ON CONFLICT (tenant_id, execution_key) DO NOTHING",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&tool)
                    .bind(&result)
                    .execute(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal store failed: {e}"
                        ))
                    })?;
                    Ok(())
                })
            })
            .await
            .map_err(|e| e.to_string())
        })
    }
}
