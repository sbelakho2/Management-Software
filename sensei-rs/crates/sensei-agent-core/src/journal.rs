//! Durable command journal (eighteenth audit P1-14, nineteenth audit
//! P1, twentieth audit P1, twenty-seventh audit P0): the bounded RAM
//! replay map in the ToolExecutor is a PERFORMANCE cache — it may
//! forget. This trait is the SYSTEM OF RECORD for idempotent tool
//! executions, modeled as a CLAIM STATE MACHINE with LEASES and
//! FENCING TOKENS:
//!
//! ```text
//!   reserve() (attempt 1)            begin_dispatch() by the claim owner
//!   (absent) ──────────────► 'reserved' ────────────────────────► 'dispatching'
//!                              │  ▲                                   │
//!   heartbeat() renews lease   │  │ lease expires: reclaimable         │ dispatch runs —
//!   (only the CURRENT owner)  │  │ ONLY while 'reserved' (the row      │ the MUTATION
//!                              │  │ has provably never been            │ happens here
//!   recover() reclaims ONLY    │  │ dispatched): recover() hands        ▼
//!   an expired 'reserved' row  │  │ a fresh token and the NEW owner   success / deterministic
//!   (never dispatched — safe   │  │ MUST pass begin_dispatch before   failure / validation
//!   to re-dispatch); the new   │  │ ANY dispatch (attempt bump)       failure / timeout
//!   owner must still pass      │  │                                     │
//!   begin_dispatch first       │  │   lease expires while              ▼
//!                              │  │   'dispatching'/'executing':   complete() ─► terminal
//!                              │  │   NEVER auto-reclaimed —            'succeeded' / 'failed'
//!                              ▼  │   recover()/expired handling        'unknown_outcome' /
//!                                      marks 'reconcile_required'       'reconcile_required'
//!                                      (the mutation MAY have           (never re-executed —
//!                                       happened; a human reconciles)   replayed by every loser)
//! ```
//!
//! `reserve` atomically claims the key (exactly one concurrent caller
//! wins) and stores the claim OWNER + a random fencing TOKEN + a LEASE
//! (lease_expires_at = NOW() + lease). The row is left at 'reserved' —
//! PROVABLY NEVER DISPATCHED. The winner must then pass the DURABLE
//! PRE-DISPATCH GATE `begin_dispatch` (a token- and lease-checked
//! transition to 'dispatching') and ONLY after that UPDATE lands does
//! the mutation run. `complete` transitions the row to a terminal or
//! reconciliation state; every loser loads the row and replays the
//! outcome, Conflicts against a LIVE lease, or `recover()`s an
//! expired 'reserved' row and re-dispatches ONCE more (attempt bump),
//! always through the `begin_dispatch` gate again. A crash after
//! reservation no longer leaves a permanently 'reserved' key: the lease
//! expires and the next worker reclaims it. A crash AFTER the gate
//! (row 'dispatching', mutation possibly in flight) is NEVER
//! auto-redispatched: lease expiry marks the row 'reconcile_required'
//! for a human — a terminal-write failure can no longer masquerade as a
//! clean pre-mutation crash (twenty-seventh audit P0). `complete` and
//! `heartbeat` are TOKEN-FENCED — a stale owner (whose claim was
//! recovered) can neither finish nor renew, so a recovered command is
//! never later completed by its previous owner. Errors ALWAYS propagate
//! — a journal that cannot be read must fail the execution, never
//! silently degrade into "no prior execution; go ahead".

use uuid::Uuid;

/// The outcome of an atomic `reserve()` claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReservationOutcome {
    /// This caller INSERTED the row (status='reserved') and owns the
    /// execution — proceed to the `begin_dispatch()` gate. The returned
    /// claim_token is the fencing credential for
    /// begin_dispatch()/complete()/heartbeat()/recover(). The row is
    /// 'reserved' (provably never dispatched): the mutation may run
    /// ONLY after `begin_dispatch()` durably transitions it to
    /// 'dispatching'.
    Fresh { claim_token: String },
    /// The key was already present — another caller claimed it. Load the
    /// row and decide between replay ('succeeded'/'failed'), Conflict
    /// ('reserved'/'dispatching'/'executing' with a LIVE lease),
    /// recover() (an EXPIRED 'reserved' row — never dispatched) and
    /// Conflict-on-reconciliation (expired 'dispatching'/'executing'
    /// rows or 'unknown_outcome'/'reconcile_required').
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

    /// The DURABLE PRE-DISPATCH GATE (twenty-seventh audit P0): the
    /// mutation may run ONLY after the claim row durably transitioned
    /// from 'reserved' (provably never dispatched) to 'dispatching'.
    /// The transition is token- and lease-checked: Ok(true) means this
    /// call performed the UPDATE (row was still 'reserved', claim_token
    /// matched and the lease had not expired) and dispatch MAY proceed;
    /// Ok(false) means the gate was REFUSED (row not 'reserved' — it was
    /// already dispatched/recovered/completed — or the token does not
    /// match, or the lease expired) and dispatch MUST NOT run. A crash
    /// after this gate leaves the row 'dispatching', which is never
    /// auto-reclaimed: a terminal-write failure or lease expiry can no
    /// longer look like a clean pre-mutation crash.
    fn begin_dispatch(
        &self,
        tenant: Uuid,
        key: &str,
        claim_token: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>;

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
    /// leased state ('reserved'/'dispatching'/'executing'). Fencing: a
    /// STALE owner's heartbeat never renews.
    fn heartbeat(
        &self,
        tenant: Uuid,
        key: &str,
        claim_token: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<bool, String>> + Send + '_>>;

    /// Atomically reclaim a row whose lease has expired (or that carries
    /// no lease — a legacy pre-149 crash) — but ONLY while its status is
    /// 'reserved' (twenty-seventh audit P0): a 'reserved' row has
    /// provably never been dispatched, so re-dispatching it once more
    /// (attempt bump) is safe. The reclaim is executed via an UPDATE
    /// that only touches such rows and returns the NEW claim_token;
    /// Ok(Some(token)) when this caller took over (status stays
    /// 'reserved' with a fresh lease — the caller MUST then pass
    /// `begin_dispatch` before any dispatch). A row that reached
    /// 'dispatching' or 'executing' with an expired lease is NEVER
    /// auto-reclaimed: the mutation MAY already have happened, so this
    /// call marks it 'reconcile_required' (clearing the claim so the
    /// stale owner is fenced out) and returns Ok(None). Ok(None) also
    /// covers a row still held under a LIVE lease (caller must Conflict)
    /// and terminal rows ('succeeded'/'failed' are never reclaimed).
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
