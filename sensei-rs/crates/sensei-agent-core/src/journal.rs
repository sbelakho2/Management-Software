//! Durable command journal (eighteenth audit P1-14, nineteenth audit
//! P1, twentieth audit P1): the bounded RAM replay map in the
//! ToolExecutor is a PERFORMANCE cache — it may forget. This trait is
//! the SYSTEM OF RECORD for idempotent tool executions, modeled as a
//! CLAIM STATE MACHINE with LEASES and FENCING TOKENS:
//!
//! ```text
//!            reserve() (attempt 1)            recover() by a new worker
//!   (absent) ──────────────────────► 'reserved' ────────────────────► 'executing'
//!                                        │                              │
//!      heartbeat() renews lease          │   lease expires              │
//!      (only the CURRENT claim owner)    ▼   OR NULL (legacy crash)     │
//!                                 recover() (attempt + 1) ◄─────────────┘
//!                                        │
//!         owner dispatches ──────────────┤
//!                                        ▼
//!   success ───────────────► complete() ──► 'succeeded'   ─┐ terminal:
//!   deterministic failure  ─► complete() ──► 'failed'      │ replayed by
//!   output-validation fail ─► complete() ──► 'failed'      │ every loser,
//!   timeout after dispatch ─► complete() ──► 'unknown_outcome' ─┐ never
//!                                            'reconcile_required' │ re-executed
//!                                            (recoverable at once ─┘ by status)
//! ```
//!
//! `reserve` atomically claims the key (exactly one concurrent caller
//! wins) and stores the claim OWNER + a random fencing TOKEN + a LEASE
//! (lease_expires_at = NOW() + lease). The winner dispatches and
//! `complete` transitions the row to a terminal or reconciliation state;
//! every loser loads the row and replays the outcome, Conflicts against a
//! LIVE lease, or `recover()`s an expired/reconciliation row and
//! re-dispatches ONCE (attempt bump). A crash after reservation no longer
//! leaves a permanently 'reserved' key: the lease expires and the next
//! worker reclaims it. `complete` and `heartbeat` are TOKEN-FENCED — a
//! stale owner (whose claim was recovered) can neither finish nor renew,
//! so a recovered command is never later completed by its previous owner.
//! Errors ALWAYS propagate — a journal that cannot be read must fail the
//! execution, never silently degrade into "no prior execution; go ahead".

use uuid::Uuid;

/// The outcome of an atomic `reserve()` claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReservationOutcome {
    /// This caller INSERTED the row (status='reserved') and owns the
    /// execution — proceed to dispatch. The returned claim_token is the
    /// fencing credential for complete()/heartbeat()/recover().
    Fresh { claim_token: String },
    /// The key was already present — another caller claimed it. Load the
    /// row and decide between replay ('succeeded'/'failed'), Conflict
    /// ('reserved'/'executing' with a LIVE lease) and recover()
    /// (expired lease or 'unknown_outcome'/'reconcile_required').
    AlreadyExists,
}

/// A journaled execution entry: its state-machine status plus the result.
pub type JournalEntry = (String, serde_json::Value);

/// Load/store execution results by (tenant, execution_key).
pub trait ExecutionJournal: Send + Sync {
    /// Atomically claim the key for this caller: INSERT ... ON CONFLICT
    /// DO NOTHING. Fresh if the row was inserted by THIS caller (with
    /// claim_owner, a random claim_token and lease_expires_at =
    /// NOW()+lease_seconds), AlreadyExists if the key is already present.
    /// Errors propagate as Err — a journal that cannot be reserved must
    /// never become "no prior execution; go ahead".
    fn reserve(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
        claim_owner: &str,
        lease_seconds: i64,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<ReservationOutcome, String>> + Send + '_>,
    >;

    /// The journaled (status, result) for the key, if any. Database
    /// errors are Err, never a silently-empty None.
    fn load(
        &self,
        tenant: Uuid,
        key: &str,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<Option<JournalEntry>, String>> + Send + '_>,
    >;

    /// Renew the claim's lease. Ok(true) when the lease was extended by
    /// this call; Ok(false) when it was REFUSED — the claim_token does
    /// not match (the row was recovered by another worker or already
    /// completed), the lease already expired, or the row is not in a
    /// leased state. Fencing: a STALE owner's heartbeat never renews.
    fn heartbeat(
        &self,
        tenant: Uuid,
        key: &str,
        claim_token: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>;

    /// Atomically reclaim a row whose lease has expired (or that carries
    /// no lease — a legacy pre-149 crash) or whose status is
    /// 'unknown_outcome'/'reconcile_required' (outcome ambiguous, must be
    /// reconciled now, lease or not). The reclaim is executed via an
    /// UPDATE that only touches reclaimable rows and returns the NEW
    /// claim_token; Ok(Some(token)) when this caller took over (status ->
    /// 'executing', attempt bumped, fresh lease), Ok(None) when the row is
    /// still held under a LIVE lease (caller must Conflict) or is
    /// terminal ('succeeded'/'failed' are never reclaimed).
    fn recover(
        &self,
        tenant: Uuid,
        key: &str,
        claim_owner: &str,
        lease_seconds: i64,
    ) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<Option<String>, String>> + Send + '_>,
    >;

    /// Transition the CLAIMED row to a terminal ('succeeded'/'failed') or
    /// reconciliation ('unknown_outcome'/'reconcile_required') status and
    /// persist the result. The update is TOKEN-FENCED: it only succeeds
    /// while claim_token matches — a stale owner whose claim was recovered
    /// gets Err and can never complete a command another worker recovered.
    fn complete(
        &self,
        tenant: Uuid,
        key: &str,
        claim_token: &str,
        status: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>>;
}
