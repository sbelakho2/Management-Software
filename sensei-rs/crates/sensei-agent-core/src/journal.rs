//! Durable command journal (eighteenth audit P1-14): the bounded RAM
//! replay map in the ToolExecutor is a PERFORMANCE cache — it may
//! forget. This trait is the SYSTEM OF RECORD for idempotent tool
//! executions: a retried mutating tool with the same execution key must
//! replay the journaled result even after the RAM entry was evicted.

use uuid::Uuid;

/// Load/store execution results by (tenant, execution_key).
pub trait ExecutionJournal: Send + Sync {
    /// The journaled result for the key, if any (tenant-scoped).
    fn load(
        &self,
        tenant: Uuid,
        key: &str,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Option<serde_json::Value>> + Send + '_>>;

    /// Persist the result. Returns Err when the system of record could
    /// not be written — for MUTATING tools a failed journal write must
    /// fail the execution, never silently weaken idempotency.
    fn store(
        &self,
        tenant: Uuid,
        key: &str,
        tool: &str,
        result: &serde_json::Value,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), String>> + Send + '_>>;
}
