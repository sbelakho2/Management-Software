//! HTTP API client for communicating with the sensei-api backend.

pub mod accounts;
pub mod ai;
pub mod analytics;
pub mod andon;
pub mod auth;
pub mod client;
pub mod contacts;
pub mod executive;
pub mod finance;
pub mod hr;
pub mod maintenance;
pub mod ops;
pub mod production;
pub mod products;
pub mod quality;
pub mod rfq;
pub mod supply_chain;
pub mod task;
pub mod today;
pub mod tps;

pub use client::ApiClient;
