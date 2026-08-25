//! Risk Management route handlers.
//!
//! The `/api/v1/risk/*` surface is an alias of the canonical
//! `/api/v1/ops/risks/*` handlers. Re-exporting the ops handlers guarantees
//! both surfaces behave identically instead of drifting apart.

pub use super::ops::{create_risk, delete_risk, get_risk, list_risks, mitigate_risk, update_risk};
