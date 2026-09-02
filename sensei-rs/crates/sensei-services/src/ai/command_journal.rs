//! Postgres-backed execution journal (eighteenth audit P1-14, nineteenth
//! audit P1, twentieth audit P1): the durable system of record for
//! idempotent tool executions (command_journal, migrations 142 + 144 +
//! 149). FORCE RLS makes every access tenant-scoped through the
//! transaction context.
//!
//! Concurrency safety: `reserve` is the atomic claim — a single
//! `INSERT ... ON CONFLICT DO NOTHING RETURNING claim_token` decides in
//! one round-trip whether THIS caller won (Fresh + token) or lost
//! (AlreadyExists). The old SELECT-then-INSERT sequence let two
//! concurrent identical requests both dispatch; the claim never does.
//!
//! Leases + fencing (twentieth audit P1): a claim stores claim_owner, a
//! random claim_token and lease_expires_at = NOW()+lease. `recover`
//! atomically reclaims rows whose lease expired (or whose status is
//! 'unknown_outcome'/'reconcile_required') and hands the new owner a
//! fresh token; `complete` and `heartbeat` only act while the caller's
//! token matches the row — a stale owner whose claim was recovered is
//! fenced out and can never complete or renew a command it no longer
//! owns.

use std::sync::Arc;

use rand::Rng;
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

/// A fresh random fencing token (32 random bytes, hex-encoded — fits the
/// VARCHAR(64) column).
fn new_claim_token() -> String {
    let bytes: [u8; 32] = rand::thread_rng().gen();
    hex::encode(bytes)
}

impl ExecutionJournal for PgExecutionJournal {
    fn reserve(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
        claim_owner: &str,
        lease_seconds: i64,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<ReservationOutcome, String>> + Send + '_>,
    > {
        let pool = self.pool.clone();
        let key = key.to_string();
        let tool = tool.to_string();
        let claim_owner = claim_owner.to_string();
        let claim_token = new_claim_token();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    // Atomic claim: the unique (tenant_id, execution_key)
                    // constraint makes ON CONFLICT DO NOTHING the arbiter —
                    // exactly one concurrent caller sees a RETURNING row.
                    // The winner carries an owner, a fencing token and a
                    // lease, so a crash after reservation expires instead
                    // of stranding the key as 'reserved' forever.
                    let claimed: Option<String> = sqlx::query_scalar(
                        "INSERT INTO command_journal \
                             (tenant_id, execution_key, tool_name, status, claimed_at, result, \
                              claim_owner, claim_token, lease_expires_at, last_heartbeat) \
                         VALUES ($1, $2, $3, 'reserved', NOW(), '{}'::jsonb, \
                                 $4, $5, NOW() + make_interval(secs => $6::float8), NOW()) \
                         ON CONFLICT (tenant_id, execution_key) DO NOTHING \
                         RETURNING claim_token",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&tool)
                    .bind(&claim_owner)
                    .bind(&claim_token)
                    .bind(lease_seconds)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal reserve failed: {e}"
                        ))
                    })?;
                    Ok(if let Some(claim_token) = claimed {
                        ReservationOutcome::Fresh { claim_token }
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

    fn heartbeat(
        &self,
        tenant: Uuid,
        key: &str,
        claim_token: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>
    {
        let pool = self.pool.clone();
        let key = key.to_string();
        let claim_token = claim_token.to_string();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    // Renew by sliding the lease horizon forward by the
                    // row's own lease window (lease_expires_at minus the
                    // previous heartbeat) — a constant horizon under
                    // regular heartbeats, with no stored lease constant.
                    // Fencing: the token must match, the row must still be
                    // in a leased state and the lease must not already
                    // have expired — a STALE owner (claim recovered) or an
                    // expired claim is refused.
                    let renewed: Option<Uuid> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET lease_expires_at = NOW() + (lease_expires_at - last_heartbeat), \
                             last_heartbeat = NOW() \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND claim_token = $3 \
                           AND status IN ('reserved', 'executing') \
                           AND lease_expires_at >= NOW() \
                         RETURNING id",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&claim_token)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal heartbeat failed: {e}"
                        ))
                    })?;
                    Ok(renewed.is_some())
                })
            })
            .await
            .map_err(|e| e.to_string())
        })
    }

    fn recover(
        &self,
        tenant: Uuid,
        key: &str,
        claim_owner: &str,
        lease_seconds: i64,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<Option<String>, String>> + Send + '_>,
    > {
        let pool = self.pool.clone();
        let key = key.to_string();
        let claim_owner = claim_owner.to_string();
        let claim_token = new_claim_token();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    // Atomic reclaim — one UPDATE decides: the row is only
                    // touched when it is reclaimable (expired lease, or
                    // NULL lease = a legacy pre-149 crash, or an
                    // ambiguous-outcome status that must be reconciled
                    // NOW). Terminal rows and rows under a LIVE lease are
                    // never matched. The winner gets a fresh token, a
                    // fresh lease and an attempt bump.
                    let claimed: Option<String> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET status = 'executing', \
                             claim_owner = $3, \
                             claim_token = $4, \
                             lease_expires_at = NOW() + make_interval(secs => $5::float8), \
                             last_heartbeat = NOW(), \
                             claimed_at = NOW(), \
                             attempt = attempt + 1, \
                             result = '{}'::jsonb \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND status IN ('reserved', 'executing', \
                                          'unknown_outcome', 'reconcile_required') \
                           AND (status IN ('unknown_outcome', 'reconcile_required') \
                                OR lease_expires_at IS NULL \
                                OR lease_expires_at < NOW()) \
                         RETURNING claim_token",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&claim_owner)
                    .bind(&claim_token)
                    .bind(lease_seconds)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal recover failed: {e}"
                        ))
                    })?;
                    Ok(claimed)
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
        claim_token: &str,
        status: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>> {
        let pool = self.pool.clone();
        let key = key.to_string();
        let claim_token = claim_token.to_string();
        let status = status.to_string();
        let result = result.clone();
        Box::pin(async move {
            with_tenant_tx(&pool, tenant, move |tx| {
                Box::pin(async move {
                    // Token-FENCED: the update only lands while THIS
                    // caller's token still owns the row. A stale owner
                    // whose claim was recovered (token replaced) or
                    // already completed (token cleared) matches nothing —
                    // it can never complete a command another worker
                    // recovered.
                    let updated: Option<Uuid> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET status = $4, result = $5, \
                             claim_owner = NULL, claim_token = NULL, \
                             lease_expires_at = NULL, last_heartbeat = NULL \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND claim_token = $3 \
                         RETURNING id",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&claim_token)
                    .bind(&status)
                    .bind(&result)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal complete failed: {e}"
                        ))
                    })?;
                    if updated.is_none() {
                        return Err(sensei_core::error::SenseiError::Database(
                            "command journal complete failed: claim_token mismatch \
                             (stale owner fenced — the claim was recovered or completed)"
                                .to_string(),
                        ));
                    }
                    Ok(())
                })
            })
            .await
            .map_err(|e| e.to_string())
        })
    }
}
