//! Durable workflow state: the status machine every checkpointed
//! transition advances. `WorkflowStatus` is the model-invocation state
//! (serde snake_case), `WorkflowState` is the resume point a crashed
//! workflow is rebuilt from.

use serde::{Deserialize, Serialize};

/// The full durable state of a workflow at a checkpoint.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorkflowState {
    /// The workflow instance identifier (e.g. `corrective_action.investigate:<condition_id>`).
    pub workflow_id: String,
    /// The status the workflow holds at this checkpoint.
    pub status: WorkflowStatus,
    /// The step the workflow currently occupies.
    pub current_step: String,
    /// The durable payload of the workflow at this checkpoint.
    pub payload: serde_json::Value,
    /// Monotonic checkpoint sequence number (resume point).
    pub checkpoint: u64,
}

/// The status of a workflow instance. A model invocation advances the
/// workflow through these states; every advance is durable.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkflowStatus {
    /// Created but not yet started.
    Pending,
    /// Executing steps.
    Running,
    /// Blocked on a human approval.
    AwaitingApproval,
    /// Blocked waiting for evidence to be recorded.
    AwaitingEvidence,
    /// Finished successfully.
    Completed,
    /// Failed — the workflow stopped on an error.
    Failed,
    /// Failed and compensated (reverted / stakeholders notified).
    Compensated,
}

impl WorkflowStatus {
    /// The database representation (matches the `status` column values).
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Running => "running",
            Self::AwaitingApproval => "awaiting_approval",
            Self::AwaitingEvidence => "awaiting_evidence",
            Self::Completed => "completed",
            Self::Failed => "failed",
            Self::Compensated => "compensated",
        }
    }
}
