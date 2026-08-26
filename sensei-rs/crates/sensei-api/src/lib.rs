//! # Sensei API Server
//!
//! Axum-based HTTP API server for the Sensei ERP system.
//!
//! This crate provides the main HTTP entrypoint, including:
//! - Router configuration with all API routes
//! - Middleware stack (auth, CORS, logging, request ID)
//! - Health check and metrics endpoints
//! - Error handling and response formatting
//! - Application state management

pub mod attachment_repository;
pub mod db_search_service;
pub mod db_stores;
pub mod error;
pub mod middleware;
pub mod router;
pub mod routes;
pub mod search_providers;
pub mod services;
pub mod state;
pub mod stores;

pub use error::*;
pub use router::*;
pub use state::*;
