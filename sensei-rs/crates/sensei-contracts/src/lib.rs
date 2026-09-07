//! sensei-contracts (thirteenth audit, re-laid out in the thirty-first):
//! the CANONICAL request/response contracts shared by backend and
//! frontend. No independent DTO should exist twice unless there is a
//! deliberate boundary transformation — this crate is that single source.
//!
//! Layout:
//! - [`andon`]: Andon response + raise command.
//! - [`finance`]: narrow invoice/payment commands + shared view models.
//! - [`hr`]: shared HR surfaces (leave requests, timecards…).
//! - [`ops`]: shared continuous-improvement surfaces (Projects/A3/Risks…).
//! - [`pagination`]: the pagination envelope both sides speak.
//! - [`tps`]: learning/flow measurement surfaces.

pub mod andon;
pub mod finance;
pub mod hr;
pub mod ops;
pub mod pagination;
pub mod tps;

pub use andon::{AndonResponse, RaiseAndonRequest};
