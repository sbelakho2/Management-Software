//! Postgres-backed execution journal (eighteenth audit P1-14, nineteenth
//! audit P1, twentieth audit P1, twenty-seventh audit P0): the durable
//! system of record for idempotent tool executions (command_journal,
//! migrations 142 + 144 + 149). FORCE RLS makes every access
//! tenant-scoped through the transaction context.
//!
//! Concurrency safety: `reserve` is the atomic claim — a single
//! `INSERT ... ON CONFLICT DO NOTHING RETURNING claim_token` decides in
//! one round-trip whether THIS caller won (Fresh + token) or lost
//! (AlreadyExists). The old SELECT-then-INSERT sequence let two
//! concurrent identical requests both dispatch; the claim never does.
//!
//! Leases + fencing (twentieth audit P1; twenty-first audit item 8;
//! twenty-seventh audit P0): a claim stores claim_owner, a random
//! claim_token and lease_expires_at = NOW()+lease. reserve() leaves the
//! row 'reserved' — PROVABLY NEVER DISPATCHED. The executor must pass
//! the DURABLE PRE-DISPATCH GATE `begin_dispatch`, a token- and
//! lease-checked UPDATE to 'dispatching', and ONLY then does the
//! mutation run: a crash AFTER the gate can never masquerade as a clean
//! pre-mutation crash. `recover` atomically reclaims ONLY pre-mutation
//! crash rows — an EXPIRED 'reserved' row (never dispatched) — and
//! hands the new owner a fresh token while the row STAYS 'reserved'
//! (the new owner must still pass `begin_dispatch` before dispatching).
//! Rows that reached 'dispatching'/'executing' with an expired lease
//! (the mutation MAY have happened) are NEVER auto-reclaimed:
//! `recover` marks them 'reconcile_required' (claim fields cleared —
//! the stale owner is fenced out) and they await human reconciliation.
//! Ambiguous-outcome rows ('unknown_outcome'/'reconcile_required') are
//! likewise never reclaimable. `complete` and `heartbeat` only act
//! while the caller's token matches the row — a stale owner whose claim
//! was recovered is fenced out and can never complete or renew a
//! command it no longer owns.

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

    fn begin_dispatch(
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
                    // Twenty-seventh audit P0: the DURABLE PRE-DISPATCH
                    // GATE. reserve() left the row 'reserved' (provably
                    // never dispatched); the mutation may run ONLY after
                    // THIS token- and lease-checked UPDATE durably moves
                    // the row to 'dispatching'. A row not in 'reserved',
                    // a mismatched token (stale owner — the claim was
                    // recovered or completed) or an expired lease is
                    // REFUSED (0 rows): dispatch must not run. Once the
                    // row is 'dispatching', a crash or terminal-write
                    // failure can no longer masquerade as a clean
                    // pre-mutation crash — an expired 'dispatching' row
                    // is never auto-redispatched (see recover()).
                    let began: Option<Uuid> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET status = 'dispatching', last_heartbeat = NOW() \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND claim_token = $3 \
                           AND status = 'reserved' \
                           AND (lease_expires_at IS NULL OR lease_expires_at > NOW()) \
                         RETURNING id",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(&claim_token)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal begin_dispatch failed: {e}"
                        ))
                    })?;
                    Ok(began.is_some())
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
                    // in a leased state ('reserved' — pre-gate —
                    // 'dispatching' — gate passed, mutation possibly in
                    // flight — or 'executing') and the lease must not
                    // already have expired — a STALE owner (claim
                    // recovered) or an expired claim is refused.
                    let renewed: Option<Uuid> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET lease_expires_at = NOW() + (lease_expires_at - last_heartbeat), \
                             last_heartbeat = NOW() \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND claim_token = $3 \
                           AND status IN ('reserved', 'dispatching', 'executing') \
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
                    // Twenty-seventh audit P0: recover() reclaims ONLY a
                    // PRE-MUTATION crash — an EXPIRED 'reserved' row (it
                    // has provably never been dispatched; the mutation
                    // cannot have happened). The reclaim is one atomic
                    // UPDATE: the winner gets a fresh token, a fresh
                    // lease and an attempt bump while the row STAYS
                    // 'reserved' — the new owner must still pass
                    // begin_dispatch() before any dispatch. Rows that
                    // reached 'dispatching'/'executing' (the mutation MAY
                    // have happened) with an expired lease (or none — a
                    // legacy crash) are NEVER auto-reclaimed: the second
                    // UPDATE marks them 'reconcile_required' and clears
                    // the claim (the stale owner is fenced out) so a
                    // human reconciles the outcome. Terminal rows, rows
                    // under a LIVE lease and ambiguous-outcome rows
                    // ('unknown_outcome'/'reconcile_required') are never
                    // matched by either UPDATE.
                    let claimed: Option<String> = sqlx::query_scalar(
                        "UPDATE command_journal \
                         SET status = 'reserved', \
                             claim_owner = $3, \
                             claim_token = $4, \
                             lease_expires_at = NOW() + make_interval(secs => $5::float8), \
                             last_heartbeat = NOW(), \
                             claimed_at = NOW(), \
                             attempt = attempt + 1, \
                             result = '{}'::jsonb \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND status = 'reserved' \
                           AND (lease_expires_at IS NULL OR lease_expires_at < NOW()) \
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
                    if claimed.is_some() {
                        return Ok(claimed);
                    }
                    // Not reclaimable: an expired (or lease-less)
                    // 'dispatching'/'executing' row means the mutation may
                    // already have happened — never re-dispatch it
                    // automatically. Transition it to 'reconcile_required'
                    // (clearing the claim fenced the stale owner out).
                    sqlx::query(
                        "UPDATE command_journal \
                         SET status = 'reconcile_required', \
                             result = $3, \
                             claim_owner = NULL, \
                             claim_token = NULL, \
                             lease_expires_at = NULL, \
                             last_heartbeat = NULL \
                         WHERE tenant_id = $1 AND execution_key = $2 \
                           AND status IN ('dispatching', 'executing') \
                           AND (lease_expires_at IS NULL OR lease_expires_at < NOW())",
                    )
                    .bind(tenant)
                    .bind(&key)
                    .bind(serde_json::json!({
                        "error": "lease expired while the command was dispatching/\
                                  executing — the mutation may have happened; automatic \
                                  re-dispatch is blocked, reconcile the row before retrying"
                    }))
                    .execute(&mut **tx)
                    .await
                    .map_err(|e| {
                        sensei_core::error::SenseiError::Database(format!(
                            "command journal recover (reconcile marking) failed: {e}"
                        ))
                    })?;
                    Ok(None)
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
