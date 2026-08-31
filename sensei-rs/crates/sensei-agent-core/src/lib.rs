//! sensei-agent-core: the security-critical foundation for tool-bound AI
//! (items 92-117 of the Sensei audit).
//!
//! The large model is never the source of authority — it is the reasoning
//! coordinator. This crate provides the contracts that keep it honest:
//! server-created context, risk-annotated tools, evidence-carrying
//! results, a classified claim ledger and a deterministic verifier.

pub mod claims;
pub mod context;
pub mod context_kernel;
pub mod evidence;
pub mod tools;
pub mod verifier;
