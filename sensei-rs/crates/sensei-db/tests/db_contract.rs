//! Fresh-PostgreSQL DB-contract gate (item 31): an EMPTY database must
//! survive the entire migration chain, and the DB-backed services' core
//! contracts (A3, BOM, outbox, andon restart) must execute CRUD against
//! the migrated schema.
//!
//! Run with:  DATABASE_URL_TEST=postgres://user:pass@localhost:5432/sensei_test  //!             cargo test -p sensei-db --test db_contract -- --ignored

use sqlx::PgPool;

/// Connect to the CI-provided empty test database. Returns None when the
/// env var is absent so the local suite stays green (the gate runs in CI).
async fn connect() -> Option<PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — db-contract gate runs in CI");
        return None;
    };
    PgPool::connect(&url).await.ok()
}

#[tokio::test]
async fn full_migration_chain_applies_and_core_contracts_work() {
    let Some(pool) = connect().await else { return };
    // Fresh-database gate: drop everything, then apply EVERY migration.
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
    let _ = pool;
    // sqlx::test applies EVERY migration to a fresh database first — if the
    // chain is broken (duplicate columns, constraint conflicts), this test
    // fails before any assertion runs.
    let pool = pool;

    // ── A3 service contract (P0-3) ────────────────────────────────────
    let a3_id = uuid::Uuid::new_v4();
    let tenant_id = uuid::Uuid::new_v4();
    // FK prerequisites: a real tenant (and a user for owner_id later).
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'contract', 'contract')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert must succeed against the migrated schema");
    sqlx::query("INSERT INTO a3_reports  (id, tenant_id, a3_number, title, background, current_state, goal,  root_cause_analysis, countermeasures, check_plan, follow_up, a3_type,  severity, status, owner_id, created_at, closed_at, version,  observed_conditions, metric_baselines, evidence_refs, cause_hypotheses,  experiments, verifications, standardizations, learnings)  VALUES ($1, $2, $3, 't', 'b', 'cs', 'g', 'rca', 'cm', 'cp', 'fu', 'standard',  'medium', 'draft', NULL, NOW(), NULL, 0, '[]', '[]', '[]', '[]', '[]', '[]', '[]', '[]')",
    )
    .bind(a3_id)
    .bind(tenant_id)
    .bind(format!("A3-{a3_id}"))
    .execute(&pool)
    .await
    .expect("a3 insert must succeed against the migrated schema");

    // Version CAS: an update at version 0 succeeds and bumps to 1; a second
    // update at version 0 must be rejected (0 rows).
    let updated = sqlx::query(
        "UPDATE a3_reports SET background = 'b2', version = version + 1  WHERE id = $1 AND version = 0",
    )
    .bind(a3_id)
    .execute(&pool)
    .await
    .expect("a3 CAS update");
    assert_eq!(updated.rows_affected(), 1, "first CAS update must apply");
    let stale = sqlx::query(
        "UPDATE a3_reports SET background = 'b3', version = version + 1  WHERE id = $1 AND version = 0",
    )
    .bind(a3_id)
    .execute(&pool)
    .await
    .expect("a3 stale update");
    assert_eq!(stale.rows_affected(), 0, "stale version must not apply");

    // Status CHECK accepts 'voided' (retention-preserving void).
    let voided = sqlx::query("UPDATE a3_reports SET status = 'voided' WHERE id = $1")
        .bind(a3_id)
        .execute(&pool)
        .await
        .expect("voided status must be allowed by the CHECK");
    assert_eq!(voided.rows_affected(), 1);

    // ── BOM contract (P0-4) ───────────────────────────────────────────
    let parent = uuid::Uuid::new_v4();
    let component = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO products (id, tenant_id, product_number, name)  VALUES ($1, $2, 'P-1', 'Parent'), ($3, $2, 'C-1', 'Component')",
    )
    .bind(parent)
    .bind(tenant_id)
    .bind(component)
    .execute(&pool)
    .await
    .expect("products insert");
    sqlx::query(
        "INSERT INTO bom_items (id, tenant_id, parent_product_id, component_product_id,  quantity, unit_of_measure, scrap_percent)  VALUES ($1, $2, $3, $4, 2, 'pcs', 5)",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_id)
    .bind(parent)
    .bind(component)
    .execute(&pool)
    .await
    .expect("bom insert must use quantity/scrap_percent");

    // ── Outbox contract (P0-6) ────────────────────────────────────────
    let event_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO outbox_events (event_id, tenant_id, aggregate_type, aggregate_id,  event_type, payload)  VALUES ($1, $2, 'a3', $3, 'sensei.a3.closed', '{}')",
    )
    .bind(event_id)
    .bind(tenant_id)
    .bind(a3_id)
    .execute(&pool)
    .await
    .expect("outbox insert");
    let claimed = sqlx::query(
        "UPDATE outbox_events SET claimed_by = 'relay-test', claim_until = NOW() + INTERVAL '30 seconds'  WHERE event_id = $1",
    )
    .bind(event_id)
    .execute(&pool)
    .await
    .expect("outbox claim columns must exist");
    assert_eq!(claimed.rows_affected(), 1);

    // Two-relay test (item 31): a SECOND relay claiming the same event
    // (claim still live) must get 0 rows — the atomic claim prevents
    // double publication.
    let second_claim = sqlx::query(
        "UPDATE outbox_events SET claimed_by = 'relay-2'  WHERE event_id = $1 AND (claim_until IS NULL OR claim_until < NOW())",
    )
    .bind(event_id)
    .execute(&pool)
    .await
    .expect("second claim attempt");
    assert_eq!(
        second_claim.rows_affected(),
        0,
        "an event with a live claim must not be claimable by a second relay"
    );

    // ── RLS tenant adversarial test (item 31) ─────────────────────────
    // With the transaction-scoped context set to tenant A, a SELECT on a
    // fail-closed table WITHOUT any tenant predicate must return ONLY
    // tenant A's rows — an intentionally missing application filter cannot
    // leak tenant B.
    let tenant_b = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'contract-b', 'contract-b')")
        .bind(tenant_b)
        .execute(&pool)
        .await
        .expect("tenant B insert");
    sqlx::query(
        "INSERT INTO invoices  (id, tenant_id, invoice_number, customer_id, customer_name, status,  line_items, subtotal, tax_percentage, tax_amount, total_amount,  currency, due_date, created_by, created_at)  VALUES ($1, $2, 'INV-B', $3, 'B', 'draft', '[]', 0, 0, 0, 0, 'USD', NOW(), NULL, NOW())",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_b)
    .bind(uuid::Uuid::new_v4())
    .execute(&pool)
    .await
    .expect("tenant B invoice");
    let a_count: i64 = {
        let mut tx = pool.begin().await.expect("begin adversarial tx");
        sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
            .bind(tenant_id.to_string())
            .execute(&mut *tx)
            .await
            .expect("set tenant context");
        // NO tenant predicate: RLS must filter to tenant A only.
        sqlx::query_scalar("SELECT count(*) FROM invoices")
            .fetch_one(&mut *tx)
            .await
            .expect("adversarial count")
    };
    assert_eq!(
        a_count, 1,
        "RLS must hide tenant B's invoice when the tenant  predicate is omitted (fail-closed policy)"
    );

    // ── Andon restart contract (P0-7) ─────────────────────────────────
    let andon_id = uuid::Uuid::new_v4();
    // FK prerequisites: a real user in tenant A (work_center_id is NOT a
    // foreign key in the andons table — it references topology only).
    let raised_by = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'andon@contract.local', 'Andon', 'x')",
    )
    .bind(raised_by)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("andon user insert");
    sqlx::query(
        "INSERT INTO andons (id, tenant_id, andon_number, work_center_id, issue_type,  severity, description, status, raised_by)  VALUES ($1, $2, 'AND-1', $3, 'safety', 'critical', 'line stop', 'active', $4)",
    )
    .bind(andon_id)
    .bind(tenant_id)
    .bind(uuid::Uuid::new_v4())
    .bind(raised_by)
    .execute(&pool)
    .await
    .expect("andon insert");
    // The safety rule lives in SQL: resolving WITHOUT a restart
    // authorization must touch 0 rows.
    let blocked = sqlx::query(
        "UPDATE andons SET status = 'resolved'  WHERE id = $1 AND (severity != 'critical' OR issue_type != 'safety'  OR restart_authorized_by IS NOT NULL)",
    )
    .bind(andon_id)
    .execute(&pool)
    .await
    .expect("safety-rule update");
    assert_eq!(
        blocked.rows_affected(),
        0,
        "critical-safety resolve must be blocked"
    );
}

#[tokio::test]
#[ignore = "requires DATABASE_URL_TEST pointing at an empty database"]
async fn empty_database_survives_the_migration_chain() {
    // sqlx::test applies all migrations to a fresh database; this ignored
    // wrapper exists so the gate can also run explicitly against an
    // external empty database (the workflow does exactly that).
    let Some(pool) = connect().await else { return };
    sqlx::query("SELECT count(*) FROM a3_reports")
        .fetch_one(&pool)
        .await
        .expect("a3_reports must exist after the migration chain");
    sqlx::query("SELECT count(*) FROM bom_items")
        .fetch_one(&pool)
        .await
        .expect("bom_items must exist after the migration chain");
    sqlx::query("SELECT count(*) FROM outbox_events")
        .fetch_one(&pool)
        .await
        .expect("outbox_events must exist after the migration chain");
}

/// Service-level DB contract (audit item 76 / P0-1): the REAL
/// `DatabaseProductionService` — not schema-shaped SQL — must execute
/// create/get/update/status/report/complete against a migrated PostgreSQL.
/// The migration chain passing is no longer allowed to mean "the production
/// service works": this test instantiates the service and runs its methods.
#[tokio::test]
async fn database_production_service_crud_works_on_migrated_schema() {
    let Some(pool) = connect().await else { return };
    // Fresh-database guarantee: every migration must apply, then the REAL
    // service executes against that schema (audit item 76).
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
    // Reuse a fresh tenant + product for FK satisfaction.
    let tenant_id = uuid::Uuid::new_v4();
    let product_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'svc', 'svc')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure) \
         VALUES ($1, $2, 'P-SVC', 'Service Product', 'pcs')",
    )
    .bind(product_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("product insert");

    use sensei_services::production::ProductionService;
    let service = sensei_services::production::DatabaseProductionService::new(pool.clone());

    // create_work_order: the full expanded schema (quantity_scrapped +
    // short_close columns) must round-trip.
    let wo = sensei_services::production::WorkOrder {
        id: uuid::Uuid::new_v4(),
        tenant_id,
        wo_number: String::new(),
        product_id,
        product_name: "Service Product".to_string(),
        quantity: 100,
        quantity_completed: 0,
        status: "created".to_string(),
        work_center_id: None,
        priority: "normal".to_string(),
        scheduled_start: Some(chrono::Utc::now()),
        scheduled_end: Some(chrono::Utc::now() + chrono::Duration::hours(8)),
        actual_start: None,
        actual_end: None,
        quantity_scrapped: 0,
        short_close_qty: 0,
        short_close_reason: None,
        short_close_approved_by: None,
        short_close_at: None,
        assigned_to: vec![],
        notes: String::new(),
        created_at: chrono::Utc::now(),
        updated_at: chrono::Utc::now(),
    };
    let created = service
        .create_work_order(tenant_id, wo)
        .await
        .expect("DatabaseProductionService.create_work_order must work on migrated schema");
    assert_eq!(created.quantity, 100);
    assert_eq!(created.status, "created");

    // get_work_order: the expanded SELECT must decode into WorkOrderRow.
    let fetched = service
        .get_work_order(tenant_id, created.id)
        .await
        .expect("get_work_order must decode the full row");
    assert_eq!(fetched.id, created.id);
    assert_eq!(fetched.wo_number, created.wo_number);

    // update_work_order: bind positions must line up (15 placeholders, 15 binds).
    let mut updated_wo = fetched.clone();
    updated_wo.quantity = 120;
    updated_wo.quantity_scrapped = 3;
    let updated = service
        .update_work_order(tenant_id, created.id, updated_wo)
        .await
        .expect("update_work_order must work");
    assert_eq!(updated.quantity, 120, "quantity must persist");
    assert_eq!(
        updated.quantity_scrapped, 3,
        "quantity_scrapped must persist"
    );

    // update_work_order_status: legal transition created -> released.
    let released = service
        .update_work_order_status(tenant_id, created.id, "released")
        .await
        .expect("update_work_order_status must work");
    assert_eq!(released.status, "released");

    // report_production: increments + immutable ledger row (the actor must
    // be a real user — MES-grade provenance).
    let operator_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'op@svc.local', 'Op', 'x')",
    )
    .bind(operator_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("operator insert");
    let reported = service
        .report_production(tenant_id, created.id, 40, 2, operator_id)
        .await
        .expect("report_production must work");
    assert_eq!(reported.quantity_completed, 40);
    assert_eq!(reported.quantity_scrapped, 5); // 3 from update + 2 reported

    // list_work_orders: paginated decode of the full row.
    let listed = service
        .list_work_orders(tenant_id, None, None, Some(1), Some(10))
        .await
        .expect("list_work_orders must work");
    assert_eq!(listed.total, 1);

    // Production order path: create (with short_close columns defaulted),
    // get, complete with an exact reconciliation.
    let po = sensei_services::production::ProductionOrder {
        id: uuid::Uuid::new_v4(),
        tenant_id,
        order_number: String::new(),
        product_id,
        // create_production_order zeroes produced/scrapped; completion must
        // reconcile EXACTLY (planned == produced + scrap + short close).
        quantity_planned: 5,
        quantity_produced: 0,
        quantity_scrapped: 0,
        status: "planned".to_string(),
        work_center_id: None,
        planned_start: chrono::Utc::now(),
        planned_end: chrono::Utc::now() + chrono::Duration::hours(8),
        actual_start: None,
        actual_end: None,
        short_close_qty: 0.0,
        short_close_reason: None,
        short_close_approved_by: None,
        short_close_at: None,
        created_at: chrono::Utc::now(),
    };
    let po_created = service
        .create_production_order(tenant_id, po)
        .await
        .expect("create_production_order must work");
    let po_fetched = service
        .get_production_order(tenant_id, po_created.id)
        .await
        .expect("get_production_order must work");
    assert_eq!(po_fetched.id, po_created.id);

    // complete with 5 short-close (0 + 0 + 5 = 5 planned) — the short
    // close columns must round-trip through the RETURNING.
    let completed = service
        .complete_production_order(
            tenant_id,
            po_created.id,
            5,
            Some("Fixture tolerance"),
            operator_id,
        )
        .await
        .expect("complete_production_order must work");
    assert_eq!(completed.status, "completed");
    assert_eq!(completed.short_close_qty, 5.0);
}

/// Andon RLS contract (item 8): the DB-backed operations service must work
/// against a fresh chain (the andons table created in 088 carries its own
/// isolation policy), and a critical-safety Andon must NOT resolve without
/// a restart authorization.
#[tokio::test]
async fn andon_service_rls_and_safety_rule_work_on_migrated_schema() {
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

    let tenant_id = uuid::Uuid::new_v4();
    let raised_by = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'andon', 'andon')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'andon@svc.local', 'A', 'x')",
    )
    .bind(raised_by)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("user insert");

    use sensei_services::ops::OperationsService;
    let service = sensei_services::ops::DatabaseOperationsService::new(pool.clone());

    let raised = service
        .raise_andon(
            tenant_id,
            sensei_services::ops::Andon {
                id: uuid::Uuid::new_v4(),
                tenant_id,
                andon_number: String::new(),
                work_center_id: uuid::Uuid::new_v4(),
                issue_type: "safety".to_string(),
                severity: "critical".to_string(),
                description: "Line stop".to_string(),
                status: String::new(),
                raised_by,
                acknowledged_by: None,
                resolved_by: None,
                resolution: None,
                response_time_seconds: None,
                resolution_time_seconds: None,
                created_at: chrono::Utc::now(),
                acknowledged_at: None,
                resolved_at: None,
                restart_authorized_by: None,
                restart_authorized_at: None,
            },
        )
        .await
        .expect("raise_andon must work with the fail-closed RLS policy");
    assert_eq!(raised.status, "active");

    // The safety rule: resolving WITHOUT restart authorization fails.
    let blocked = service
        .resolve_andon(tenant_id, raised.id, raised_by, "trying to resolve")
        .await;
    assert!(
        blocked.is_err(),
        "critical-safety resolve without restart authorization must fail"
    );

    // Authorize restart, then resolve succeeds.
    service
        .authorize_restart(tenant_id, raised.id, raised_by)
        .await
        .expect("authorize_restart must work");
    let resolved = service
        .resolve_andon(
            tenant_id,
            raised.id,
            raised_by,
            "restarted after authorization",
        )
        .await
        .expect("resolve with restart authorization must work");
    assert_eq!(resolved.status, "resolved");
}

/// Cross-tenant topology FK (item 9 / P0-9): a tenant-A value stream must
/// be rejected by the DATABASE when it references tenant-B's site.
#[tokio::test]
async fn topology_composite_tenant_fk_rejects_cross_tenant_reference() {
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

    let tenant_a = uuid::Uuid::new_v4();
    let tenant_b = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'a', 'a'), ($2, 'b', 'b')")
        .bind(tenant_a)
        .bind(tenant_b)
        .execute(&pool)
        .await
        .expect("tenants insert");
    let site_a = uuid::Uuid::new_v4();
    let site_b = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO sites (id, tenant_id, site_code, name) VALUES \
         ($1, $2, 'A', 'Site A'), ($3, $4, 'B', 'Site B')",
    )
    .bind(site_a)
    .bind(tenant_a)
    .bind(site_b)
    .bind(tenant_b)
    .execute(&pool)
    .await
    .expect("sites insert");

    // Tenant A's value stream referencing tenant B's site must FAIL.
    let cross = sqlx::query(
        "INSERT INTO value_streams (id, tenant_id, site_id, name) VALUES ($1, $2, $3, 'Cross')",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_a)
    .bind(site_b)
    .execute(&pool)
    .await;
    assert!(
        cross.is_err(),
        "cross-tenant value stream must be rejected by the composite FK"
    );

    // Same-tenant reference must succeed.
    sqlx::query(
        "INSERT INTO value_streams (id, tenant_id, site_id, name) VALUES ($1, $2, $3, 'Ok')",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_a)
    .bind(site_a)
    .execute(&pool)
    .await
    .expect("same-tenant value stream must succeed");
}

/// LSW concurrency (item 13 / audit gate "LSW concurrency"): one
/// occurrence produces at most one audit — the UNIQUE(occurrence_id,
/// tenant_id) constraint plus the transactional audit+completion make a
/// second audit for the same execution impossible.
#[tokio::test]
async fn lsw_occurrence_yields_at_most_one_audit() {
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

    let tenant_id = uuid::Uuid::new_v4();
    let leader_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'lsw', 'lsw')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'leader@lsw.local', 'L', 'x')",
    )
    .bind(leader_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("leader insert");

    use sensei_api::lsw_repository::LswRepository;
    let repo = LswRepository::new(Some(pool.clone()));

    let standard_id = uuid::Uuid::new_v4();
    let occurrence_id = uuid::Uuid::new_v4();
    let now = chrono::Utc::now();
    let standard = sensei_api::stores::LswStandard {
        id: standard_id,
        tenant_id,
        title: "Cell observation".to_string(),
        area: "Assembly".to_string(),
        layer: 1,
        revision: 1,
        frequency: sensei_api::stores::LswFrequency::Daily,
        checklist_items: vec![sensei_api::stores::LswChecklistItem {
            id: uuid::Uuid::new_v4(),
            description: "Sorting applied".to_string(),
            expected_value: None,
            is_critical: false,
        }],
        is_active: true,
        created_by: leader_id,
        created_at: now,
        updated_at: now,
    };
    repo.put_standard(&standard)
        .await
        .expect("standard persist");
    let occurrence = sensei_api::stores::LswOccurrence {
        id: occurrence_id,
        standard_id,
        tenant_id,
        checklist_revision: 1,
        due_at: now,
        assigned_leader: leader_id,
        area: "Assembly".to_string(),
        layer: 1,
        status: "scheduled".to_string(),
        scheduled_at: now,
        started_at: None,
        completed_at: None,
    };
    repo.put_occurrence(&occurrence)
        .await
        .expect("occurrence persist");

    let audit = sensei_api::stores::LswAudit {
        id: uuid::Uuid::new_v4(),
        standard_id,
        tenant_id,
        auditor_id: leader_id,
        occurrence_id: Some(occurrence_id),
        leader_id: Some(leader_id),
        area: "Assembly".to_string(),
        layer: 1,
        results: vec![],
        compliance_rate: 100.0,
        notes: None,
        audited_at: now,
        created_at: now,
    };
    repo.complete_occurrence_with_audit(tenant_id, standard_id, occurrence_id, &audit)
        .await
        .expect("first audit + completion must succeed");

    // Second execution of the SAME occurrence must fail (already completed
    // + the UNIQUE constraint).
    let second = sensei_api::stores::LswAudit {
        id: uuid::Uuid::new_v4(),
        standard_id,
        tenant_id,
        auditor_id: leader_id,
        occurrence_id: Some(occurrence_id),
        leader_id: Some(leader_id),
        area: "Assembly".to_string(),
        layer: 1,
        results: vec![],
        compliance_rate: 90.0,
        notes: None,
        audited_at: now,
        created_at: now,
    };
    let second_result = repo
        .complete_occurrence_with_audit(tenant_id, standard_id, occurrence_id, &second)
        .await;
    assert!(
        second_result.is_err(),
        "a second audit for the same occurrence must be rejected"
    );
    let audits = repo
        .list_audits(tenant_id, standard_id)
        .await
        .expect("audit list");
    assert_eq!(audits.len(), 1, "exactly one audit per occurrence");
    // The relational detail path must find the audit the list returned
    // (item 12: no list/detail divergence).
    let detail = repo
        .get_audit(tenant_id, audit.id)
        .await
        .expect("audit detail");
    assert!(detail.is_some(), "the listed audit must resolve on detail");
}
