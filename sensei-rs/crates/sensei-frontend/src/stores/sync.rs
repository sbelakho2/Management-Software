//! Sync (offline queue / optimistic updates) reactive store.
//!
//! Mirrors the Zustand [`sync-store.ts`](frontend/src/stores/sync-store.ts) store.

use leptos::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A pending operation awaiting sync.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PendingOperation {
    pub id: String,
    pub operation_type: String,
    pub entity_type: String,
    pub entity_id: Option<String>,
    pub payload: serde_json::Value,
    pub status: String,
    pub retry_count: i32,
    pub created_at: String,
    pub last_error: Option<String>,
}

/// An optimistically created entity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimisticEntity {
    pub id: String,
    pub entity_type: String,
    pub data: serde_json::Value,
}

/// Reactive store for sync/offline queue state.
#[derive(Debug, Clone)]
pub struct SyncStore {
    /// Queue of pending operations to sync.
    pub pending_operations: RwSignal<Vec<PendingOperation>>,
    /// Optimistically created entities.
    pub optimistic_entities: RwSignal<Vec<OptimisticEntity>>,
    /// Whether a sync is in progress.
    pub is_syncing: RwSignal<bool>,
    /// Timestamp of last successful sync.
    pub last_sync_at: RwSignal<Option<String>>,
    /// Last sync error, if any.
    pub sync_error: RwSignal<Option<String>>,
    /// Whether the client is online.
    pub is_online: RwSignal<bool>,
}

impl SyncStore {
    pub fn new() -> Self {
        Self {
            pending_operations: RwSignal::new(Vec::new()),
            optimistic_entities: RwSignal::new(Vec::new()),
            is_syncing: RwSignal::new(false),
            last_sync_at: RwSignal::new(None),
            sync_error: RwSignal::new(None),
            is_online: RwSignal::new(true),
        }
    }

    // ── Operation queue ──────────────────────────────────────────────────────

    /// Add a pending operation to the queue.
    pub fn add_operation(&self, operation: PendingOperation) {
        self.pending_operations.update(|ops| ops.push(operation));
    }

    /// Remove a pending operation by ID.
    pub fn remove_operation(&self, id: &str) {
        self.pending_operations
            .update(|ops| ops.retain(|op| op.id != id));
    }

    /// Update the status of a pending operation.
    pub fn update_operation_status(&self, id: &str, status: &str, error: Option<&str>) {
        self.pending_operations.update(|ops| {
            if let Some(op) = ops.iter_mut().find(|op| op.id == id) {
                op.status = status.to_string();
                if let Some(msg) = error {
                    op.last_error = Some(msg.to_string());
                }
            }
        });
    }

    /// Increment the retry count for a pending operation.
    pub fn increment_retry(&self, id: &str) {
        self.pending_operations.update(|ops| {
            if let Some(op) = ops.iter_mut().find(|op| op.id == id) {
                op.retry_count += 1;
            }
        });
    }

    /// Remove all completed operations from the queue.
    pub fn clear_completed_operations(&self) {
        self.pending_operations
            .update(|ops| ops.retain(|op| op.status != "completed"));
    }

    // ── Optimistic entities ──────────────────────────────────────────────────

    /// Add an optimistically created entity.
    pub fn add_optimistic_entity(&self, entity: OptimisticEntity) {
        self.optimistic_entities.update(|entities| entities.push(entity));
    }

    /// Update an optimistically created entity by ID.
    pub fn update_optimistic_entity(&self, id: &str, data: serde_json::Value) {
        self.optimistic_entities.update(|entities| {
            if let Some(entity) = entities.iter_mut().find(|e| e.id == id) {
                entity.data = data;
            }
        });
    }

    /// Remove an optimistic entity by ID.
    pub fn remove_optimistic_entity(&self, id: &str) {
        self.optimistic_entities
            .update(|entities| entities.retain(|e| e.id != id));
    }

    /// Get an optimistic entity by ID.
    pub fn get_optimistic_entity(&self, id: &str) -> Option<OptimisticEntity> {
        self.optimistic_entities
            .get()
            .into_iter()
            .find(|e| e.id == id)
            .map(|e| e.clone())
    }

    // ── Sync state ───────────────────────────────────────────────────────────

    /// Set the syncing flag.
    pub fn set_syncing(&self, syncing: bool) {
        self.is_syncing.set(syncing);
    }

    /// Set the last sync timestamp.
    pub fn set_last_sync_at(&self, timestamp: &str) {
        self.last_sync_at.set(Some(timestamp.to_string()));
    }

    /// Set a sync error.
    pub fn set_sync_error(&self, error: Option<&str>) {
        self.sync_error.set(error.map(|s| s.to_string()));
    }

    /// Set online/offline status.
    pub fn set_online(&self, online: bool) {
        self.is_online.set(online);
    }

    // ── Computed helpers ─────────────────────────────────────────────────────

    /// Get the number of pending operations.
    pub fn get_pending_count(&self) -> usize {
        self.pending_operations.get().len()
    }

    /// Get all failed operations.
    pub fn get_failed_operations(&self) -> Vec<PendingOperation> {
        self.pending_operations
            .get()
            .into_iter()
            .filter(|op| op.status == "failed")
            .collect()
    }

    /// Retry all failed operations by resetting their status to "pending".
    pub fn retry_failed_operations(&self) {
        self.pending_operations.update(|ops| {
            for op in ops.iter_mut() {
                if op.status == "failed" {
                    op.status = "pending".to_string();
                }
            }
        });
    }

    /// Clear all pending operations and optimistic entities.
    pub fn clear_all(&self) {
        self.pending_operations.set(Vec::new());
        self.optimistic_entities.set(Vec::new());
        self.sync_error.set(None);
    }
}

impl Default for SyncStore {
    fn default() -> Self {
        Self::new()
    }
}
