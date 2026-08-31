//! # Sensei Authentication & Authorization
//!
//! Provides authentication and authorization services including:
//! - JWT issuance and validation
//! - OAuth2/OIDC client integration
//! - Role-based access control (RBAC)
//! - Password hashing with Argon2
//! - Axum middleware for request authentication

pub mod authz_snapshot;
pub mod jwt;
pub mod middleware;
pub mod oauth2;
pub mod password;
pub mod rbac;
pub mod refresh_tokens;
