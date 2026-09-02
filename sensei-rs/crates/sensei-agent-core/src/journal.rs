//! Durable command journal (eighteenth audit P1-14, nineteenth audit
//! P1): the bounded RAM replay map in the ToolExecutor is a PERFORMANCE
//! cache — it may forget. This trait is the SYSTEM OF RECORD for
//! idempotent tool executions, modeled as a CLAIM STATE MACHINE:
//! `reserve` atomically claims the key (exactly one concurrent caller
//! wins), the winner dispatches and `complete` transitions the row to
//! 'succeeded' or 'failed'; every loser loads the row and replays the
//! outcome instead of re-executing. Errors ALWAYS propagate — a journal
//! that cannot be read must fail the execution, never silently degrade
//! into "no prior execution; go ahead".

use uuid::Uuid;

/// The outcome of an atomic `reserve()` claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReservationOutcome {
    /// This caller INSERTED the row (status='reserved') and owns the
    /// execution — proceed to dispatch.
    Fresh,
    /// The key was already present — another caller claimed it. Load the
    /// row and decide between replay ('succeeded'/'failed') and
    /// Conflict ('reserved'/'executing').
    AlreadyExists,
}

/// A journaled execution entry: its state-machine status plus the result.
pub type JournalEntry = (String, serde_json::Value);

/// Load/store execution results by (tenant, execution_key).
pub trait ExecutionJournal: Send + Sync {
    /// Atomically claim the key for this caller: INSERT ... ON CONFLICT
    /// DO NOTHING. Fresh if the row was inserted by THIS caller,
    /// AlreadyExists if the key is already present. Errors propagate as
    /// Err — a journal that cannot be reserved must never become
    /// "no prior execution; go ahead".
    fn reserve(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
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

    /// Transition the claimed row to a terminal status ('succeeded' or
    /// 'failed') and persist the result. For MUTATING tools a failed
    /// write must fail the execution, never silently weaken idempotency.
    fn complete(
        &self,
        tenant: Uuid,
        key: &str,
        status: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>>;
}
