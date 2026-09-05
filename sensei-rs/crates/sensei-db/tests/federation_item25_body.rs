//! Thirtieth audit item 25 DB gate: federation honest end-to-end
//! application state — target-generated application receipts, real
//! registered projectors, and a source 'application_confirmed' terminal
//! state that ACK can never manufacture. Each test DROP+CREATEs the
//! shared schema, so a global lock serializes the suite within this
//! binary (same convention as `db_contract.rs`).
//!
//! Run with:  DATABASE_URL_TEST=postgres://user:pass@localhost:5432/sensei_test
//!            cargo test -p sensei-db --test federation_item25_body

use sqlx::PgPool;

/// The gate tests each DROP+CREATE the shared schema — running them
/// concurrently races the schema locks (deadlocks observed). A global
/// lock serializes the suite: every test acquires it before touching the
/// database.
static DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// Connect to the CI-provided empty test database. Returns None when the
/// env var is absent so the local suite stays green (the gate runs in CI).
async fn connect() -> Option<PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — db-contract gate runs in CI");
        return None;
    };
    PgPool::connect(&url).await.ok()
}

/// Thirtieth audit item 25 (federation target apply — real projectors
/// and target-generated receipts): the successor of the twenty-sixth/
/// twenty-seventh-audit guard. `ack()` is still the queue-side consume
/// acknowledgement ONLY — it marks the source queue row 'acked' and
/// NEVER writes the replication inbox, never writes an application
/// receipt, and never produces 'application_confirmed'. Delivery
/// (`deliver_to_target_inbox`) reserves the projection in the TARGET
/// tenant's inbox (status 'received') and records the delivery binding
/// (`source_queue_id` + `payload_hash`); `apply_target_projection` now
/// runs a REGISTERED projector (the `andon` canonical-event mirror),
/// transitions received -> applying -> applied, and binds the
/// server-created application receipt (`replication_receipts`) carrying
/// the full binding identity. The source row is confirmed
/// ('application_confirmed') ONLY when the confirmation poll observes
/// that target-generated receipt — source-manufactured receipt rows
/// (which FORCE RLS lets a source write in its OWN slice) are excluded
/// by the session-bound SECURITY DEFINER ownership filter, so a
/// source-side actor can never manufacture the target-application fact.
#[tokio::test]
async fn federation_target_apply_inbox_receipt_guard() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    sqlx::query(
        r#"DO $$ DECLARE r RECORD; BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                 EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
             END LOOP;
         END $$"#,
    )
    .execute(&pool)
    .await
    .expect("drop all tables");
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");

    let source_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30apply', 't30apply')")
        .bind(source_tenant)
        .execute(&pool)
        .await
        .expect("source tenant insert");
    // The projector mirrors into the TARGET's canonical event store
    // (operational_events.tenant_id has an FK to tenants), so the target
    // must be a real tenant row too.
    let target_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30target', 't30target')")
        .bind(target_tenant)
        .execute(&pool)
        .await
        .expect("target tenant insert");

    use sensei_services::tps::replication;

    let site_id = uuid::Uuid::new_v4();
    let entity_a = uuid::Uuid::new_v4();
    let source_event = uuid::Uuid::new_v4();
    let target_site = uuid::Uuid::new_v4();
    let occurred_at = chrono::Utc::now() - chrono::Duration::minutes(5);
    // The canonical server-built projection envelope (the exact shape
    // `authorize_projection` emits: source_event + event_type +
    // occurred_at + scope_site + the event's own payload).
    let projection = serde_json::json!({
        "source_event": source_event,
        "event_type": "andon.raised",
        "occurred_at": occurred_at.to_rfc3339(),
        "scope_site": site_id,
        "payload": { "issue_type": "quality", "severity": "high" },
    });
    let envelope = replication::ReplicationEnvelope {
        schema_version: 1,
        source_event_id: Some(source_event.to_string()),
        source_site: Some(site_id),
        projection_type: "andon.raised".to_string(),
        projection_revision: 1,
        data_policy: "internal".to_string(),
        payload: projection.clone(),
    };
    let edge = replication::FederationEdge {
        source_tenant,
        source_site: Some(site_id),
        target_tenant,
        target_site: Some(target_site),
        target_jurisdiction: replication::Jurisdiction::MA,
        allowed_data_classes: vec![
            replication::DataPolicy::Public,
            replication::DataPolicy::Internal,
            replication::DataPolicy::Confidential,
            replication::DataPolicy::Restricted,
            replication::DataPolicy::Personal,
        ],
        residency_policy: replication::ResidencyPolicy::CorporateAllowed,
        policy_revision: 1,
    };
    replication::enqueue_projection(
        &pool,
        source_tenant,
        Some(site_id),
        "andon",
        entity_a,
        projection.clone(),
        Some(&source_event.to_string()),
        &envelope,
        Some(&replication::Jurisdiction::MA),
        &edge,
    )
    .await
    .expect("enqueue must succeed site-locally");

    let claimed = replication::claim_batch(&pool, source_tenant, 10)
        .await
        .expect("claim must work");
    assert_eq!(claimed.len(), 1, "exactly one claimable projection");
    let entry = &claimed[0];
    assert_eq!(entry.entity_type, "andon");
    assert_eq!(entry.target_tenant_id, Some(target_tenant));
    assert_eq!(entry.target_site_id, Some(target_site));
    let event_uuid =
        uuid::Uuid::parse_str(entry.source_event_id.as_deref().expect("source event id"))
            .expect("the enqueued source event id is a UUID");
    let queue_id = entry.id;
    let local_hash = replication::projection_payload_hash(&entry.projection)
        .expect("the local payload hash computes");

    async fn inbox_count_for(pool: &sqlx::PgPool, tenant_id: uuid::Uuid) -> i64 {
        let mut tx = pool.begin().await.expect("inbox tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let n: i64 =
            sqlx::query_scalar("SELECT count(*) FROM replication_inbox WHERE tenant_id = $1")
                .bind(tenant_id)
                .fetch_one(&mut *tx)
                .await
                .expect("inbox count");
        tx.commit().await.expect("inbox tx commit");
        n
    }

    async fn receipt_count_for(pool: &sqlx::PgPool, tenant_id: uuid::Uuid) -> i64 {
        let mut tx = pool.begin().await.expect("receipt tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let n: i64 =
            sqlx::query_scalar("SELECT count(*) FROM replication_receipts WHERE tenant_id = $1")
                .bind(tenant_id)
                .fetch_one(&mut *tx)
                .await
                .expect("receipt count");
        tx.commit().await.expect("receipt tx commit");
        n
    }

    async fn queue_status(pool: &sqlx::PgPool, tenant_id: uuid::Uuid, id: uuid::Uuid) -> String {
        let mut tx = pool.begin().await.expect("status tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let s: String = sqlx::query_scalar("SELECT status FROM site_replication_log WHERE id = $1")
            .bind(id)
            .fetch_one(&mut *tx)
            .await
            .expect("status read");
        tx.commit().await.expect("status tx commit");
        s
    }

    async fn inbox_state(
        pool: &sqlx::PgPool,
        tenant_id: uuid::Uuid,
        event: uuid::Uuid,
    ) -> Option<(String, Option<chrono::DateTime<chrono::Utc>>)> {
        let mut tx = pool.begin().await.expect("inbox state tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let row: Option<(String, Option<chrono::DateTime<chrono::Utc>>)> = sqlx::query_as(
            "SELECT status, apply_started_at FROM replication_inbox \
             WHERE tenant_id = $1 AND source_event_id = $2",
        )
        .bind(tenant_id)
        .bind(event)
        .fetch_optional(&mut *tx)
        .await
        .expect("inbox state read");
        tx.commit().await.expect("inbox state tx commit");
        row
    }

    async fn mirror_events(
        pool: &sqlx::PgPool,
        tenant_id: uuid::Uuid,
        source_event: uuid::Uuid,
    ) -> i64 {
        let mut tx = pool.begin().await.expect("mirror tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let n: i64 = sqlx::query_scalar(
            "SELECT count(*) FROM operational_events \
             WHERE tenant_id = $1 AND source_system = 'federation' AND source_id = $2",
        )
        .bind(tenant_id)
        .bind(source_event.to_string())
        .fetch_one(&mut *tx)
        .await
        .expect("mirror count");
        tx.commit().await.expect("mirror tx commit");
        n
    }

    // ── 1. ack() alone: delivery to the consumer, NOT an application ──
    replication::ack(
        &pool,
        source_tenant,
        entry.id,
        entry.claim_token.expect("lease token"),
    )
    .await
    .expect("ack must succeed");
    assert_eq!(
        queue_status(&pool, source_tenant, entry.id).await,
        "acked",
        "the consume marks the source queue row acked"
    );
    assert_eq!(inbox_count_for(&pool, source_tenant).await, 0);
    assert_eq!(
        inbox_count_for(&pool, target_tenant).await,
        0,
        "ack() alone creates NO inbox row under the target tenant"
    );
    assert_eq!(
        receipt_count_for(&pool, target_tenant).await,
        0,
        "ack() alone creates NO application receipt"
    );

    // ── 2. ACK alone NEVER produces application_confirmed ─────────────
    // The confirmation poll runs with no receipt anywhere: the acked row
    // stays 'acked' (awaiting the target-generated receipt) — the ack
    // path can never manufacture the terminal state.
    let no_receipt = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        no_receipt.confirmed, 0,
        "nothing is confirmed without a receipt"
    );
    assert_eq!(
        no_receipt.awaiting_receipt, 1,
        "the acked row is awaiting its target receipt"
    );
    assert_eq!(
        queue_status(&pool, source_tenant, entry.id).await,
        "acked",
        "ACK alone never moves the row to application_confirmed"
    );

    // ── 3. SOURCE-MANUFACTURED receipts are never observed ────────────
    // FORCE RLS lets the SOURCE tenant write inbox + receipt rows in its
    // OWN slice (tenant_id = its context). The strongest attack binds the
    // correct queue id, source event and payload hash. The session-bound
    // DEFINER view excludes every receipt whose owner is NOT its own
    // destination tenant — a source-owned receipt is never exposed, so
    // the manufactured rows cannot drive confirmation.
    {
        let mut tx = pool.begin().await.expect("manufacture tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(source_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set source tenant context");
        let fake_inbox = uuid::Uuid::new_v4();
        sqlx::query(
            "INSERT INTO replication_inbox \
                 (id, tenant_id, source_tenant_id, source_queue_id, source_site_id, \
                  source_event_id, projection_type, projection_revision, target_tenant_id, \
                  target_site_id, payload_hash, status, received_at, apply_started_at, applied_at) \
             VALUES ($1, $2, $2, $3, $4, $5, 'andon.raised', 1, $6, $7, $8, 'applied', \
                     NOW(), NOW(), NOW())",
        )
        .bind(fake_inbox)
        .bind(source_tenant)
        .bind(queue_id)
        .bind(entry.site_id)
        .bind(event_uuid)
        .bind(target_tenant)
        .bind(target_site)
        .bind(&local_hash)
        .execute(&mut *tx)
        .await
        .expect("a source-owned fake inbox row is writable in its own slice");
        sqlx::query(
            "INSERT INTO replication_receipts \
                 (tenant_id, source_tenant_id, source_queue_id, source_site_id, \
                  source_event_id, target_tenant_id, target_site_id, target_inbox_id, \
                  projection_type, projection_revision, payload_hash, received_at, applied_at) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'andon.raised', 1, $9, NOW(), NOW())",
        )
        .bind(source_tenant)
        .bind(source_tenant)
        .bind(queue_id)
        .bind(entry.site_id)
        .bind(event_uuid)
        .bind(target_tenant)
        .bind(target_site)
        .bind(fake_inbox)
        .bind(&local_hash)
        .execute(&mut *tx)
        .await
        .expect("a source-owned fake receipt row is writable in its own slice");
        tx.commit().await.expect("manufacture tx commit");
    }
    assert_eq!(
        receipt_count_for(&pool, source_tenant).await,
        1,
        "the fake receipt lives in the SOURCE slice"
    );
    let still_awaiting = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        still_awaiting.confirmed, 0,
        "a source-manufactured receipt is NEVER observed — the receipt must be owned by \
         its destination tenant"
    );
    assert_eq!(
        still_awaiting.awaiting_receipt, 1,
        "the row still awaits a real target-generated receipt"
    );
    assert_eq!(
        queue_status(&pool, source_tenant, entry.id).await,
        "acked",
        "the source-manufacture attack cannot confirm the row"
    );

    // ── 4. apply_target_projection before any delivery: refused ───────
    {
        let mut tx = pool.begin().await.expect("apply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        let err = replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect_err("an unreserved projection cannot be applied");
        tx.commit().await.expect("apply tx commit");
        assert!(
            matches!(
                err,
                sensei_core::error::SenseiError::Validation(ref msg)
                    if msg.contains("no inbox receipt is reserved for andon")
            ),
            "apply without a delivery is refused loudly (no reserved inbox row)"
        );
    }

    // ── 5. deliver_to_target_inbox: TARGET inbox reservation + binding ─
    let delivered = replication::deliver_to_target_inbox(&pool, source_tenant, entry)
        .await
        .expect("delivery must reserve the target inbox");
    assert!(delivered, "the first delivery inserts the receipt");
    assert_eq!(
        inbox_count_for(&pool, target_tenant).await,
        1,
        "exactly ONE receipt is reserved in the TARGET tenant's inbox"
    );
    assert_eq!(
        inbox_count_for(&pool, source_tenant).await,
        1,
        "the source slice holds only its manufactured fake inbox row"
    );
    {
        let mut tx = pool.begin().await.expect("receipt shape tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        type Receipt = (
            uuid::Uuid, // source_tenant_id
            uuid::Uuid, // source_queue_id
            uuid::Uuid, // target_tenant_id
            Option<uuid::Uuid>,
            String,                        // projection_type
            i64,                           // projection_revision
            String,                        // status
            String,                        // payload_hash
            chrono::DateTime<chrono::Utc>, // received_at
        );
        let receipt: Option<Receipt> = sqlx::query_as(
            "SELECT source_tenant_id, source_queue_id, target_tenant_id, target_site_id, \
                    projection_type, projection_revision, status, payload_hash, received_at \
             FROM replication_inbox WHERE tenant_id = $1 AND source_event_id = $2",
        )
        .bind(target_tenant)
        .bind(event_uuid)
        .fetch_optional(&mut *tx)
        .await
        .expect("receipt shape read");
        tx.commit().await.expect("shape tx commit");
        let (src_tenant, src_queue, tgt_tenant, tgt_site, ptype, prev, status, hash, _received) =
            receipt.expect("the real receipt exists under the target tenant");
        assert_eq!(
            src_tenant, source_tenant,
            "the receipt records the SOURCE tenant"
        );
        assert_eq!(
            src_queue, queue_id,
            "the receipt binds the SOURCE QUEUE row"
        );
        assert_eq!(
            tgt_tenant, target_tenant,
            "the receipt owner IS the target tenant"
        );
        assert_eq!(
            tgt_site,
            Some(target_site),
            "the receipt names the destination site"
        );
        assert_eq!(
            ptype, "andon.raised",
            "the receipt pins the projection identity"
        );
        assert_eq!(prev, 1, "the receipt pins the projection revision");
        assert_eq!(
            status, "received",
            "delivery reserves with status 'received'"
        );
        assert_eq!(
            hash, local_hash,
            "delivery binds the payload hash of the delivered projection"
        );
    }

    // ── 6. A second delivery (a redelivery) is refused ATOMICALLY ─────
    let redelivered = replication::deliver_to_target_inbox(&pool, source_tenant, entry)
        .await
        .expect("the redelivery must not error");
    assert!(
        !redelivered,
        "a duplicate delivery is refused — no second receipt"
    );
    assert_eq!(inbox_count_for(&pool, target_tenant).await, 1);

    // ── 7. reserve_target_inbox (the raw-argument receipt form) ────────
    let dup = replication::reserve_target_inbox(
        &pool,
        target_tenant,
        source_tenant,
        queue_id,
        entry.site_id,
        event_uuid,
        &entry.projection_type,
        entry.projection_revision,
        target_tenant,
        entry.target_site_id,
        &local_hash,
    )
    .await
    .expect("the raw-argument receipt insert must not error");
    assert!(!dup, "the same key is already reserved — refused");
    let misowned = replication::reserve_target_inbox(
        &pool,
        source_tenant,
        source_tenant,
        queue_id,
        entry.site_id,
        event_uuid,
        &entry.projection_type,
        entry.projection_revision,
        target_tenant,
        entry.target_site_id,
        &local_hash,
    )
    .await;
    assert!(
        matches!(
            misowned,
            Err(sensei_core::error::SenseiError::Validation(_))
        ),
        "a receipt whose owner is not its destination is refused"
    );

    // ── 8. apply_target_projection: the REGISTERED projector runs ─────
    // The inbox row is reserved in 'received' with a matching delivery
    // hash; the entry's entity type ('andon') has a REGISTERED projector
    // (the canonical-event mirror), so the apply now performs the real
    // business write and transitions received -> applying -> applied.
    let inbox_before = inbox_state(&pool, target_tenant, event_uuid)
        .await
        .expect("the inbox row exists under the target");
    assert_eq!(inbox_before.0, "received");
    let (inbox_id, inbox_received_at): (uuid::Uuid, chrono::DateTime<chrono::Utc>) = {
        let mut tx = pool.begin().await.expect("inbox id tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let row: (uuid::Uuid, chrono::DateTime<chrono::Utc>) = sqlx::query_as(
            "SELECT id, received_at FROM replication_inbox \
             WHERE tenant_id = $1 AND source_event_id = $2",
        )
        .bind(target_tenant)
        .bind(event_uuid)
        .fetch_one(&mut *tx)
        .await
        .expect("inbox id read");
        tx.commit().await.expect("inbox id tx commit");
        row
    };
    {
        let mut tx = pool.begin().await.expect("apply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect("a registered projector must apply the projection");
        tx.commit().await.expect("apply tx commit");
    }
    let (state, started_at) = inbox_state(&pool, target_tenant, event_uuid)
        .await
        .expect("the inbox row exists under the target");
    assert_eq!(
        state, "applied",
        "the registered projector transitioned the row to 'applied'"
    );
    assert!(
        started_at.is_some(),
        "the applied projection records apply_started_at"
    );
    assert_eq!(
        mirror_events(&pool, target_tenant, event_uuid).await,
        1,
        "the registered projector REALLY landed the projection in the target's \
         canonical event store"
    );

    // ── 9. The target-generated receipt binds the full identity ───────
    assert_eq!(
        receipt_count_for(&pool, target_tenant).await,
        1,
        "apply created exactly ONE target-generated receipt"
    );
    {
        let mut tx = pool.begin().await.expect("receipt bind tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        type Bound = (
            uuid::Uuid, // source_tenant_id
            uuid::Uuid, // source_queue_id
            Option<uuid::Uuid>,
            uuid::Uuid, // source_event_id
            uuid::Uuid, // target_tenant_id
            Option<uuid::Uuid>,
            uuid::Uuid,                    // target_inbox_id
            String,                        // projection_type
            i64,                           // projection_revision
            String,                        // payload_hash
            chrono::DateTime<chrono::Utc>, // received_at
        );
        let bound: Option<Bound> = sqlx::query_as(
            "SELECT source_tenant_id, source_queue_id, source_site_id, source_event_id, \
                    target_tenant_id, target_site_id, target_inbox_id, projection_type, \
                    projection_revision, payload_hash, received_at \
             FROM replication_receipts WHERE tenant_id = $1",
        )
        .bind(target_tenant)
        .fetch_optional(&mut *tx)
        .await
        .expect("receipt binding read");
        tx.commit().await.expect("bind tx commit");
        let (
            src_tenant,
            src_queue,
            src_site,
            src_event,
            tgt_tenant,
            tgt_site,
            inbox,
            ptype,
            prev,
            hash,
            received,
        ) = bound.expect("the receipt exists");
        assert_eq!(src_tenant, source_tenant, "binding: source_tenant_id");
        assert_eq!(src_queue, queue_id, "binding: source_queue_id");
        assert_eq!(src_site, Some(site_id), "binding: source_site_id");
        assert_eq!(src_event, event_uuid, "binding: source_event_id");
        assert_eq!(tgt_tenant, target_tenant, "binding: target_tenant_id");
        assert_eq!(tgt_site, Some(target_site), "binding: target_site_id");
        assert_eq!(inbox, inbox_id, "binding: target_inbox_id");
        assert_eq!(ptype, "andon.raised", "binding: projection_type");
        assert_eq!(prev, 1, "binding: projection_revision");
        assert_eq!(hash, local_hash, "binding: payload_hash");
        assert_eq!(
            received, inbox_received_at,
            "binding: received_at is the inbox delivery time"
        );
    }

    // ── 10. Projector idempotency: a re-apply applies ONCE ────────────
    {
        let mut tx = pool.begin().await.expect("reapply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect("an already-applied row converges — never a second apply");
        tx.commit().await.expect("reapply tx commit");
    }
    assert_eq!(
        mirror_events(&pool, target_tenant, event_uuid).await,
        1,
        "duplicate delivery/apply applies the business projection ONCE"
    );
    assert_eq!(
        receipt_count_for(&pool, target_tenant).await,
        1,
        "duplicate delivery/apply creates exactly ONE receipt"
    );
    assert_eq!(inbox_count_for(&pool, target_tenant).await, 1);

    // ── 11. The source confirms ONLY on the target-generated receipt ──
    let confirmed_report = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        confirmed_report.confirmed, 1,
        "the target-generated receipt (owned by the target, hash matching) confirms the row"
    );
    assert_eq!(confirmed_report.awaiting_receipt, 0);
    assert_eq!(confirmed_report.receipt_payload_mismatch, 0);
    assert_eq!(
        queue_status(&pool, source_tenant, entry.id).await,
        "application_confirmed",
        "the source row reaches its terminal application_confirmed state"
    );
    {
        let mut tx = pool.begin().await.expect("confirmed tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(source_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let confirmed_at: Option<chrono::DateTime<chrono::Utc>> =
            sqlx::query_scalar("SELECT confirmed_at FROM site_replication_log WHERE id = $1")
                .bind(entry.id)
                .fetch_one(&mut *tx)
                .await
                .expect("confirmed_at read");
        tx.commit().await.expect("confirmed tx commit");
        assert!(
            confirmed_at.is_some(),
            "the confirmation stamps confirmed_at"
        );
    }
}

/// Thirtieth audit item 25 — full pipeline on the `work_order` projector
/// (the second registered entity type): source event -> target received
/// -> target applying -> target applied (real mirror write) ->
/// target-generated receipt -> source application_confirmed — while an
/// ACK-only sibling row stays 'acked' forever (no receipt, no
/// confirmation). Also pins the store-level mirror idempotency: a
/// duplicate delivery + re-apply after the row is 'applied' changes
/// nothing (one mirror, one receipt, one inbox row).
#[tokio::test]
async fn federation_end_to_end_receipt_confirmation() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    sqlx::query(
        r#"DO $$ DECLARE r RECORD; BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                 EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
             END LOOP;
         END $$"#,
    )
    .execute(&pool)
    .await
    .expect("drop all tables");
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");

    let source_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30pipe', 't30pipe')")
        .bind(source_tenant)
        .execute(&pool)
        .await
        .expect("source tenant insert");
    let target_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30pipedst', 't30pipedst')")
        .bind(target_tenant)
        .execute(&pool)
        .await
        .expect("target tenant insert");

    use sensei_services::tps::replication;

    let site_id = uuid::Uuid::new_v4();
    let order = uuid::Uuid::new_v4();
    let source_event = uuid::Uuid::new_v4();
    let target_site = uuid::Uuid::new_v4();
    let occurred_at = chrono::Utc::now() - chrono::Duration::hours(1);
    let projection = serde_json::json!({
        "source_event": source_event,
        "event_type": "production.work-order.status-changed",
        "occurred_at": occurred_at.to_rfc3339(),
        "scope_site": site_id,
        "payload": { "status": "completed", "qty": 120 },
    });
    let envelope = replication::ReplicationEnvelope {
        schema_version: 1,
        source_event_id: Some(source_event.to_string()),
        source_site: Some(site_id),
        projection_type: "production.work-order.status-changed".to_string(),
        projection_revision: 1,
        data_policy: "internal".to_string(),
        payload: projection.clone(),
    };
    let edge = replication::FederationEdge {
        source_tenant,
        source_site: Some(site_id),
        target_tenant,
        target_site: Some(target_site),
        target_jurisdiction: replication::Jurisdiction::TN,
        allowed_data_classes: vec![
            replication::DataPolicy::Public,
            replication::DataPolicy::Internal,
            replication::DataPolicy::Confidential,
            replication::DataPolicy::Restricted,
            replication::DataPolicy::Personal,
        ],
        residency_policy: replication::ResidencyPolicy::CorporateAllowed,
        policy_revision: 1,
    };
    replication::enqueue_projection(
        &pool,
        source_tenant,
        Some(site_id),
        "work_order",
        order,
        projection.clone(),
        Some(&source_event.to_string()),
        &envelope,
        Some(&replication::Jurisdiction::TN),
        &edge,
    )
    .await
    .expect("enqueue must succeed site-locally");

    let claimed = replication::claim_batch(&pool, source_tenant, 10)
        .await
        .expect("claim must work");
    assert_eq!(claimed.len(), 1, "exactly one claimable projection");
    let entry = &claimed[0];
    assert_eq!(entry.entity_type, "work_order");

    async fn statuses(pool: &sqlx::PgPool, tenant_id: uuid::Uuid) -> Vec<String> {
        let mut tx = pool.begin().await.expect("status tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let rows: Vec<String> = sqlx::query_scalar(
            "SELECT status FROM site_replication_log WHERE tenant_id = $1 ORDER BY created_at",
        )
        .bind(tenant_id)
        .fetch_all(&mut *tx)
        .await
        .expect("statuses read");
        tx.commit().await.expect("status tx commit");
        rows
    }

    async fn count_where(pool: &sqlx::PgPool, tenant_id: uuid::Uuid, table: &str) -> i64 {
        let mut tx = pool.begin().await.expect("count tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let sql = format!("SELECT count(*) FROM {table} WHERE tenant_id = $1");
        let n: i64 = sqlx::query_scalar(&sql)
            .bind(tenant_id)
            .fetch_one(&mut *tx)
            .await
            .expect("count read");
        tx.commit().await.expect("count tx commit");
        n
    }

    // The FULL receiving pipeline, one step at a time.
    // (1) target received: delivery reserves the target inbox.
    let delivered = replication::deliver_to_target_inbox(&pool, source_tenant, entry)
        .await
        .expect("delivery must reserve the target inbox");
    assert!(delivered, "first delivery inserts the inbox row");
    // (2) target applying -> applied: the registered work_order projector
    //     really lands the projection in the target's canonical store.
    {
        let mut tx = pool.begin().await.expect("apply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect("the registered work_order projector must apply");
        tx.commit().await.expect("apply tx commit");
    }
    assert_eq!(
        count_where(&pool, target_tenant, "replication_inbox").await,
        1,
        "one inbox row"
    );
    assert_eq!(
        count_where(&pool, target_tenant, "replication_receipts").await,
        1,
        "one target-generated receipt"
    );
    assert_eq!(
        count_where(&pool, target_tenant, "operational_events").await,
        1,
        "the work_order projection really landed in the target's canonical event store"
    );
    // The receipt is bound to the projection identity + payload hash.
    {
        let mut tx = pool.begin().await.expect("receipt read tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let (ptype, hash): (String, String) = sqlx::query_as(
            "SELECT projection_type, payload_hash FROM replication_receipts WHERE tenant_id = $1",
        )
        .bind(target_tenant)
        .fetch_one(&mut *tx)
        .await
        .expect("receipt read");
        tx.commit().await.expect("receipt tx commit");
        assert_eq!(ptype, "production.work-order.status-changed");
        assert_eq!(
            hash,
            replication::projection_payload_hash(&entry.projection).expect("local hash"),
            "the receipt binds the payload hash of the delivered projection"
        );
    }
    // (3) ACK: delivery to the consumer — the row is acked, never
    //     application_confirmed by the ACK itself.
    replication::ack(
        &pool,
        source_tenant,
        entry.id,
        entry.claim_token.expect("lease token"),
    )
    .await
    .expect("ack must succeed");
    let before_confirm = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        before_confirm.confirmed, 1,
        "the receipt already existed when the row was acked — the poll confirms it"
    );
    assert_eq!(
        statuses(&pool, source_tenant).await,
        vec!["application_confirmed".to_string()],
        "receipt observed -> application_confirmed"
    );
    // (4) Idempotency after the terminal state: a duplicate delivery and
    //     a re-apply change NOTHING (one mirror event, one receipt).
    let again = replication::deliver_to_target_inbox(&pool, source_tenant, entry)
        .await
        .expect("redelivery must not error");
    assert!(!again, "duplicate delivery is refused");
    {
        let mut tx = pool.begin().await.expect("reapply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect("an already-applied row converges — never a second error");
        tx.commit().await.expect("reapply tx commit");
    }
    assert_eq!(
        count_where(&pool, target_tenant, "replication_inbox").await,
        1
    );
    assert_eq!(
        count_where(&pool, target_tenant, "replication_receipts").await,
        1
    );
    assert_eq!(
        count_where(&pool, target_tenant, "operational_events").await,
        1
    );

    // (5) The ACK-only negative: a SECOND event is delivered to the
    //     consumer (ACK) but never delivered/applied at the target — the
    //     row stays 'acked' forever: ACK alone never produces
    //     target_applied or application_confirmed, even while ANOTHER
    //     row of the same tenant is confirmed.
    let event_two = uuid::Uuid::new_v4();
    let projection_two = serde_json::json!({
        "source_event": event_two,
        "event_type": "andon.resolved",
        "occurred_at": occurred_at.to_rfc3339(),
        "scope_site": site_id,
        "payload": { "resolution": "cleaned" },
    });
    let envelope_two = replication::ReplicationEnvelope {
        schema_version: 1,
        source_event_id: Some(event_two.to_string()),
        source_site: Some(site_id),
        projection_type: "andon.resolved".to_string(),
        projection_revision: 1,
        data_policy: "internal".to_string(),
        payload: projection_two.clone(),
    };
    replication::enqueue_projection(
        &pool,
        source_tenant,
        Some(site_id),
        "andon",
        order,
        projection_two.clone(),
        Some(&event_two.to_string()),
        &envelope_two,
        Some(&replication::Jurisdiction::TN),
        &edge,
    )
    .await
    .expect("second enqueue must succeed");
    let second_claim = replication::claim_batch(&pool, source_tenant, 10)
        .await
        .expect("second claim must work");
    assert_eq!(second_claim.len(), 1, "the second event is claimable");
    let entry_two = &second_claim[0];
    replication::ack(
        &pool,
        source_tenant,
        entry_two.id,
        entry_two.claim_token.expect("lease token"),
    )
    .await
    .expect("ack-only must succeed");
    let ack_only = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        ack_only.confirmed, 0,
        "the ACK-only row is NOT confirmed — no receipt exists for it"
    );
    assert_eq!(
        ack_only.awaiting_receipt, 1,
        "the ACK-only row awaits a receipt it will never get"
    );
    let s = statuses(&pool, source_tenant).await;
    assert_eq!(s.len(), 2, "both queue rows present");
    assert_eq!(
        s[1], "acked",
        "ACK alone never produces application_confirmed"
    );
    // Delivering/applying the second event NOW confirms it: confirmation
    // tracks the target application, not the ACK timing.
    replication::deliver_to_target_inbox(&pool, source_tenant, entry_two)
        .await
        .expect("second delivery");
    {
        let mut tx = pool.begin().await.expect("apply two tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        replication::apply_target_projection(&mut tx, source_tenant, entry_two)
            .await
            .expect("second apply must succeed");
        tx.commit().await.expect("apply two tx commit");
    }
    let after_two = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(
        after_two.confirmed, 1,
        "the second row confirms on its own receipt"
    );
    let s = statuses(&pool, source_tenant).await;
    assert_eq!(s[1], "application_confirmed");
}

/// Thirtieth audit item 25 (d): a payload_hash MISMATCH between what
/// delivery recorded and what an apply is about to apply is recorded
/// 'reconcile_required' — never 'applied'. The apply verifies the hash
/// of the projection against the delivery binding before any projector
/// runs: a tampered/redelivered payload (same key, different content)
/// cannot land a business write, and no receipt is bound for it.
#[tokio::test]
async fn federation_apply_payload_mismatch_reconcile_required() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    sqlx::query(
        r#"DO $$ DECLARE r RECORD; BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                 EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
             END LOOP;
         END $$"#,
    )
    .execute(&pool)
    .await
    .expect("drop all tables");
    sensei_db::migrations::run_migrations(&pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");

    let source_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30mismatch', 't30mismatch')")
        .bind(source_tenant)
        .execute(&pool)
        .await
        .expect("source tenant insert");
    let target_tenant = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 't30mmdst', 't30mmdst')")
        .bind(target_tenant)
        .execute(&pool)
        .await
        .expect("target tenant insert");

    use sensei_services::tps::replication;

    let site_id = uuid::Uuid::new_v4();
    let entity_a = uuid::Uuid::new_v4();
    let source_event = uuid::Uuid::new_v4();
    let occurred_at = chrono::Utc::now() - chrono::Duration::minutes(3);
    let projection = serde_json::json!({
        "source_event": source_event,
        "event_type": "andon.raised",
        "occurred_at": occurred_at.to_rfc3339(),
        "scope_site": site_id,
        "payload": { "issue_type": "quality", "severity": "high" },
    });
    let envelope = replication::ReplicationEnvelope {
        schema_version: 1,
        source_event_id: Some(source_event.to_string()),
        source_site: Some(site_id),
        projection_type: "andon.raised".to_string(),
        projection_revision: 1,
        data_policy: "internal".to_string(),
        payload: projection.clone(),
    };
    let edge = replication::FederationEdge {
        source_tenant,
        source_site: Some(site_id),
        target_tenant,
        target_site: None,
        target_jurisdiction: replication::Jurisdiction::MA,
        allowed_data_classes: vec![
            replication::DataPolicy::Public,
            replication::DataPolicy::Internal,
            replication::DataPolicy::Confidential,
            replication::DataPolicy::Restricted,
            replication::DataPolicy::Personal,
        ],
        residency_policy: replication::ResidencyPolicy::CorporateAllowed,
        policy_revision: 1,
    };
    replication::enqueue_projection(
        &pool,
        source_tenant,
        Some(site_id),
        "andon",
        entity_a,
        projection.clone(),
        Some(&source_event.to_string()),
        &envelope,
        Some(&replication::Jurisdiction::MA),
        &edge,
    )
    .await
    .expect("enqueue must succeed site-locally");

    let claimed = replication::claim_batch(&pool, source_tenant, 10)
        .await
        .expect("claim must work");
    assert_eq!(claimed.len(), 1);
    let entry = &claimed[0];
    let event_uuid =
        uuid::Uuid::parse_str(entry.source_event_id.as_deref().expect("source event id"))
            .expect("the enqueued source event id is a UUID");
    let original_hash = replication::projection_payload_hash(&entry.projection)
        .expect("the delivered hash computes");

    async fn inbox_state(
        pool: &sqlx::PgPool,
        tenant_id: uuid::Uuid,
        event: uuid::Uuid,
    ) -> Option<(String, Option<chrono::DateTime<chrono::Utc>>)> {
        let mut tx = pool.begin().await.expect("inbox state tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let row: Option<(String, Option<chrono::DateTime<chrono::Utc>>)> = sqlx::query_as(
            "SELECT status, failed_at FROM replication_inbox \
             WHERE tenant_id = $1 AND source_event_id = $2",
        )
        .bind(tenant_id)
        .bind(event)
        .fetch_optional(&mut *tx)
        .await
        .expect("inbox state read");
        tx.commit().await.expect("inbox state tx commit");
        row
    }

    async fn target_counts(pool: &sqlx::PgPool, tenant_id: uuid::Uuid) -> (i64, i64, i64) {
        let mut tx = pool.begin().await.expect("count tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        let inbox: i64 =
            sqlx::query_scalar("SELECT count(*) FROM replication_inbox WHERE tenant_id = $1")
                .bind(tenant_id)
                .fetch_one(&mut *tx)
                .await
                .expect("inbox count");
        let receipts: i64 =
            sqlx::query_scalar("SELECT count(*) FROM replication_receipts WHERE tenant_id = $1")
                .bind(tenant_id)
                .fetch_one(&mut *tx)
                .await
                .expect("receipt count");
        let mirror: i64 = sqlx::query_scalar(
            "SELECT count(*) FROM operational_events \
             WHERE tenant_id = $1 AND source_system = 'federation'",
        )
        .bind(tenant_id)
        .fetch_one(&mut *tx)
        .await
        .expect("mirror count");
        tx.commit().await.expect("count tx commit");
        (inbox, receipts, mirror)
    }

    // Delivery binds the hash of the REAL payload.
    replication::deliver_to_target_inbox(&pool, source_tenant, entry)
        .await
        .expect("delivery must reserve the target inbox");

    // The apply arrives with a TAMPERED payload: same queue id, same
    // source event, same key — but different content (severity changed),
    // so its hash no longer matches what delivery recorded.
    let mut tampered = entry.clone();
    tampered.projection = serde_json::json!({
        "source_event": source_event,
        "event_type": "andon.raised",
        "occurred_at": occurred_at.to_rfc3339(),
        "scope_site": site_id,
        "payload": { "issue_type": "quality", "severity": "low" },
    });
    assert_ne!(
        replication::projection_payload_hash(&tampered.projection).expect("tampered hash"),
        original_hash,
        "the tampered payload must hash differently"
    );
    let err = {
        let mut tx = pool.begin().await.expect("mismatch apply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        let result = replication::apply_target_projection(&mut tx, source_tenant, &tampered)
            .await
            .expect_err("a payload mismatch must refuse the apply");
        tx.commit().await.expect("mismatch apply tx commit");
        result
    };
    assert!(
        matches!(
            err,
            sensei_core::error::SenseiError::Validation(ref msg)
                if msg.contains("payload hash mismatch")
        ),
        "the apply refused with the hash-mismatch Validation error"
    );
    // The failure is recorded: 'reconcile_required' instead of applied —
    // no projector ran, no mirror landed, no receipt was bound.
    let (state, failed_at) = inbox_state(&pool, target_tenant, event_uuid)
        .await
        .expect("the inbox row exists under the target");
    assert_eq!(
        state, "reconcile_required",
        "a payload mismatch is recorded reconcile_required — never applied"
    );
    assert!(failed_at.is_some(), "the failed apply records failed_at");
    let (inbox, receipts, mirror) = target_counts(&pool, target_tenant).await;
    assert_eq!(inbox, 1, "one inbox row");
    assert_eq!(
        receipts, 0,
        "no receipt is bound for an unapplied projection"
    );
    assert_eq!(
        mirror, 0,
        "no business write landed for the mismatched payload"
    );

    // A re-apply of the ORIGINAL payload is refused too: reconciliation
    // owns the row — a fresh apply is never silently retried.
    {
        let mut tx = pool.begin().await.expect("reconcile apply tx begin");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(target_tenant.to_string())
            .execute(&mut *tx)
            .await
            .expect("set target tenant context");
        let err = replication::apply_target_projection(&mut tx, source_tenant, entry)
            .await
            .expect_err("a reconcile_required row cannot be silently re-applied");
        tx.commit().await.expect("apply tx commit");
        assert!(
            matches!(
                err,
                sensei_core::error::SenseiError::Validation(ref msg)
                    if msg.contains("reconcile_required")
            ),
            "apply on a failed row is refused until reconciliation happens"
        );
    }

    // The source row never acked and never confirms: no receipt exists.
    let report = replication::confirm_application_receipts(&pool, source_tenant, 100)
        .await
        .expect("confirmation poll must work");
    assert_eq!(report.confirmed, 0, "nothing to confirm");
    assert_eq!(report.awaiting_receipt, 0, "the queue row is not acked");
}
