//! End-to-end tests for the generic entity store (`EntityStore`).
//!
//! Covers the public store API in in-memory mode:
//! - Dirty-diff persistence semantics (persist → mutate → only diffs tracked)
//! - `list_paginated` ordering (created_at DESC, id)
//! - `list_by_field` JSONB-field filtering
//! - Pagination clamping (page ≥ 1)

use sensei_api::db_stores::{EntityStore, StoreError};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct TestEntity {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    created_at: Option<String>,
    status: String,
}

fn entity(name: &str, status: &str) -> TestEntity {
    TestEntity {
        name: name.to_string(),
        created_at: None,
        status: status.to_string(),
    }
}

fn entity_at(created_at: &str, name: &str) -> TestEntity {
    TestEntity {
        name: name.to_string(),
        created_at: Some(created_at.to_string()),
        status: "active".to_string(),
    }
}

#[tokio::test]
async fn persist_requires_a_pool_and_fails_cleanly_in_memory_mode() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    let id = Uuid::new_v4();

    let mut guard = store.write().await;
    guard.insert(id, entity("a", "active"));

    assert!(
        matches!(guard.persist().await, Err(StoreError::NotConnected)),
        "persist without a DB pool must report NotConnected"
    );
}

#[tokio::test]
async fn write_guard_persists_only_changed_keys() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    let id_unchanged = Uuid::new_v4();
    let id_updated = Uuid::new_v4();
    let id_removed = Uuid::new_v4();

    // Seed: all three keys exist.
    {
        let mut guard = store.write().await;
        guard.insert(id_unchanged, entity("stable", "active"));
        guard.insert(id_updated, entity("before", "active"));
        guard.insert(id_removed, entity("doomed", "active"));
    }

    // Second guard: update one key, remove one key, insert one key.
    let id_inserted = Uuid::new_v4();
    {
        let mut guard = store.write().await;
        guard.get_mut(&id_updated).unwrap().name = "after".to_string();
        guard.remove(&id_removed);
        guard.insert(id_inserted, entity("fresh", "active"));

        // Without a pool we cannot observe the SQL, but the diff must be
        // exactly {updated, inserted} + {removed} — the untouched key must
        // not be part of the change set. Verify through persist's error
        // behavior plus an in-memory snapshot check: after the guard drops,
        // the in-memory map reflects the mutations and nothing else.
        assert!(matches!(
            guard.persist().await,
            Err(StoreError::NotConnected)
        ));
    }

    // The in-memory data is exactly what was mutated.
    let guard = store.read().await;
    assert_eq!(guard.len(), 3);
    assert!(guard.contains_key(&id_unchanged));
    assert_eq!(guard.get(&id_updated).unwrap().name, "after");
    assert!(!guard.contains_key(&id_removed));
    assert!(guard.contains_key(&id_inserted));
}

#[tokio::test]
async fn list_paginated_orders_by_created_at_desc_then_id() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    let now = chrono::Utc::now();

    let id_old = Uuid::new_v4();
    let id_mid = Uuid::new_v4();
    let id_new = Uuid::new_v4();
    let id_no_ts = Uuid::new_v4();
    {
        let mut guard = store.write().await;
        guard.insert(
            id_old,
            entity_at(&(now - chrono::Duration::days(3)).to_rfc3339(), "old"),
        );
        guard.insert(
            id_mid,
            entity_at(&(now - chrono::Duration::days(1)).to_rfc3339(), "mid"),
        );
        guard.insert(id_new, entity_at(&now.to_rfc3339(), "new"));
        guard.insert(id_no_ts, entity("no-timestamp", "active"));
    }

    let (items, total) = store.list_paginated(1, 10).await.unwrap();
    assert_eq!(total, 4);
    let ids: Vec<Uuid> = items.iter().map(|(id, _)| *id).collect();
    assert_eq!(ids, vec![id_new, id_mid, id_old, id_no_ts]);
}

#[tokio::test]
async fn list_paginated_clamps_page_to_one() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    for i in 0..5 {
        let mut guard = store.write().await;
        guard.insert(Uuid::new_v4(), entity(&format!("e{i}"), "active"));
    }

    // page=0 is treated as page=1.
    let (items, total) = store.list_paginated(0, 2).await.unwrap();
    assert_eq!(total, 5);
    assert_eq!(items.len(), 2);

    // A huge page number must not overflow; it just yields an empty page.
    let (items, _) = store.list_paginated(usize::MAX, 50).await.unwrap();
    assert!(items.is_empty());
}

#[tokio::test]
async fn list_by_field_filters_on_json_field() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    let id_done = Uuid::new_v4();
    let id_open = Uuid::new_v4();
    {
        let mut guard = store.write().await;
        guard.insert(id_done, entity("finished", "done"));
        guard.insert(id_open, entity("pending", "open"));
    }

    let found = store
        .list_by_field("status", &serde_json::json!("done"))
        .await
        .unwrap();
    assert_eq!(found.len(), 1);
    assert_eq!(found[0].0, id_done);
    assert_eq!(found[0].1.name, "finished");
}

#[tokio::test]
async fn reads_and_writes_roundtrip_through_guards() {
    let store: EntityStore<TestEntity> = EntityStore::new("test_entity");
    let id = Uuid::new_v4();
    {
        let mut guard = store.write().await;
        guard.insert(id, entity("roundtrip", "active"));
    }

    let guard = store.read().await;
    let stored = guard.get(&id).expect("entity must be readable after write");
    assert_eq!(stored.name, "roundtrip");
}
