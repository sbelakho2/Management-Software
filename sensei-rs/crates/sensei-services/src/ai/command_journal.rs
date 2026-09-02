//! Postgres-backed execution journal (eighteenth audit P1-14, nineteenth
//! audit P1): the durable system of record for idempotent tool
//! executions (command_journal, migrations 142 + 144). FORCE RLS makes
//! every access tenant-scoped through the transaction context.
//!
//! Concurrency safety: `reserve` is the atomic claim — a single
//! `INSERT ... ON CONFLICT DO NOTHING RETURNING id` decides in one
//! round-trip whether THIS caller won (a row came back) or lost
//! (AlreadyExists). The old SELECT-then-INSERT sequence let two
//! concurrent identical requests both dispatch; the claim never does.

use std::sync::Arc;

use sensei_agent_core::journal::{ExecutionJournal, ReservationOutcome};
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
    fn reserve(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<ReservationOutcome, String>> + Send + '_>,
    > {
        let pool = self.pool.clone();
        let key = key.to_string();
        let tool = tool.to_string();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    // Atomic claim: the unique (tenant_id, execution_key)
                    // constraint makes ON CONFLICT DO NOTHING the arbiter —
                    // exactly one concurrent caller sees a RETURNING row.
                    let claimed: Option<Uuid> = sqlx::query_scalar(
                        "INSERT INTO command_journal \
                             (tenant_id, execution_key, tool_name, status, claimed_at, result) \
                         VALUES ($1, $2, $3, 'reserved', NOW(), '{}'::jsonb) \
                         ON CONFLICT (tenant_id, execution_key) DO NOTHING \
                         RETURNING id",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&tool)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal reserve failed: {e}"
                        ))
                    })?;
                    Ok(if claimed.is_some() {
                        ReservationOutcome::Fresh
                    } else {
                        ReservationOutcome::AlreadyExists
                    })
                })
            })
            .await
            .map_err(|e| e.to_string())
        })
    }

    fn load(
        &self,
        tenant: Uuid,
        key: &str,
    ) -> std::pin::Pin<
        Box<
            dyn std::future::Future<Output = Result<Option<(String, serde_json::Value)>, String>>
                + Send
                + '_,
        >,
    > {
        let pool = self.pool.clone();
        let key = key.to_string();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    let row: Option<(String, serde_json::Value)> = sqlx::query_as(
                        "SELECT status, result FROM command_journal \
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
            .map_err(|e| e.to_string())
        })
    }

    fn complete(
        &self,
        tenant: Uuid,
        key: &str,
        status: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>> {
        let pool = self.pool.clone();
        let key = key.to_string();
        let status = status.to_string();
        let result = result.clone();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    sqlx::query(
                        "UPDATE command_journal \
                         SET status = $3, result = $4 \
                         WHERE tenant_id = $1 AND execution_key = $2",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&status)
                    .bind(&result)
                    .execute(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal complete failed: {e}"
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
