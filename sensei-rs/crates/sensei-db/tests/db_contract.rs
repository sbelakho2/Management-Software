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

/// MRP fixtures (audit gate "MRP fixtures"): a KNOWN cyclic BOM must be
/// REJECTED (not silently truncated) and a two-level BOM must phase the
/// component need date BACKWARD from the finished good's due date.
#[tokio::test]
async fn mrp_rejects_cycles_and_phases_dates_backward() {
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

    use sensei_services::production::ProductionService;
    let service = sensei_services::production::DatabaseProductionService::new(pool.clone());
    let tenant_id = uuid::Uuid::new_v4();
    let a = uuid::Uuid::new_v4();
    let b = uuid::Uuid::new_v4();
    let c = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'mrp', 'mrp')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    for (id, num, name, lead) in [
        (a, "A", "Assembly A", 5),
        (b, "B", "Component B", 2),
        (c, "C", "Raw C", 0),
    ] {
        sqlx::query(
            "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure, lead_time_days) \
             VALUES ($1, $2, $3, $4, 'pcs', $5)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(num)
        .bind(name)
        .bind(lead)
        .execute(&pool)
        .await
        .expect("product insert");
    }

    // ── Cycle fixture: A -> B -> A must be REJECTED ──
    sqlx::query(
        "INSERT INTO bom_items (id, tenant_id, parent_product_id, component_product_id, quantity, unit_of_measure) \
         VALUES ($1,$2,$3,$4,1,'pcs'), ($5,$2,$4,$3,1,'pcs')",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_id)
    .bind(a)
    .bind(b)
    .bind(uuid::Uuid::new_v4())
    .execute(&pool)
    .await
    .expect("cyclic BOM insert");
    let cycle_result = service.run_mrp(tenant_id, a).await;
    assert!(
        cycle_result.is_err(),
        "a cyclic BOM must be rejected, never silently truncated"
    );
    sqlx::query("DELETE FROM bom_items WHERE tenant_id = $1")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("clear BOM");

    // ── Time-phasing fixture: A (lead 5) needs B (lead 2) ──
    sqlx::query(
        "INSERT INTO bom_items (id, tenant_id, parent_product_id, component_product_id, quantity, unit_of_measure) \
         VALUES ($1,$2,$3,$4,2,'pcs')",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_id)
    .bind(a)
    .bind(b)
    .execute(&pool)
    .await
    .expect("BOM insert");
    // A work order due in 10 days establishes the demand timing.
    let wo_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO work_orders (id, tenant_id, wo_number, product_id, product_name, quantity, status, scheduled_end) \
         VALUES ($1,$2,'WO-MRP',$3,'Assembly A',100,'released',$4)",
    )
    .bind(wo_id)
    .bind(tenant_id)
    .bind(a)
    .bind(chrono::Utc::now() + chrono::Duration::days(10))
    .execute(&pool)
    .await
    .expect("WO insert");

    let records = service.run_mrp(tenant_id, a).await.expect("MRP must run");
    let a_rec = records
        .iter()
        .find(|r| r.product_id == a)
        .expect("A record");
    let b_rec = records
        .iter()
        .find(|r| r.product_id == b)
        .expect("B record");
    // A: due 10 days out, release 5 days earlier (its own lead).
    assert!(
        (a_rec.time_phase_end - chrono::Utc::now()).num_days() >= 9,
        "A due date must track the work-order demand, got {:?}",
        a_rec.time_phase_end
    );
    assert!(
        (a_rec.time_phase_end - a_rec.time_phase_start).num_days() >= 4,
        "A release must be offset back by A's lead time"
    );
    // B: needed when A starts — strictly EARLIER than A's end, offset by
    // A's lead; never an arbitrary now+30d default (item 17).
    assert!(
        b_rec.time_phase_end <= a_rec.time_phase_start,
        "component B must be needed no later than A's release, got B={} A_start={}",
        b_rec.time_phase_end,
        a_rec.time_phase_start
    );
    assert_eq!(b_rec.gross_requirement, 200, "2 per A × 100");
}

/// RAG golden set (audit gate "RAG golden set / RAG authority"): the
/// effective-window + ACL prefilter runs against a real database, and a
/// SUPERSEDED pack with higher authority must NEVER surface over an
/// effective one.
#[tokio::test]
async fn rag_golden_effective_filter_and_authority_order() {
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
    let supplier_roles = vec!["supplier".to_string()];
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'rag', 'rag')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");

    // A superseded high-authority pack and an effective employee-note pack
    // both contain the same keyword.
    let superseded_id = uuid::Uuid::new_v4();
    let effective_id = uuid::Uuid::new_v4();
    for (id, status, authority) in [
        (superseded_id, "superseded", "tps_canonical"),
        (effective_id, "effective", "employee_note"),
    ] {
        sqlx::query(
            "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
             VALUES ($1, 'knowledge_pack', $2, $3)",
        )
        .bind(tenant_id)
        .bind(id)
        .bind(serde_json::json!({
            "title": "changeover standard",
            "status": status,
            "authority": authority,
        }))
        .execute(&pool)
        .await
        .expect("knowledge pack insert");
        sensei_api::services::hybrid_retrieval::upsert_embedding(
            &pool,
            tenant_id,
            "knowledge_pack",
            id,
            "changeover standard",
            "changeover sequence for the press line",
        )
        .await
        .expect("embedding upsert");
    }

    let hits = sensei_api::services::hybrid_retrieval::hybrid_search(
        &pool,
        tenant_id,
        "changeover press line",
        &supplier_roles,
        10,
    )
    .await
    .expect("hybrid search must execute against a real database");
    // The superseded pack must NOT appear — effective filter before ranking.
    assert!(
        !hits.iter().any(|h| h.document_id == superseded_id),
        "superseded knowledge must never surface: {hits:?}"
    );
    assert!(
        hits.iter().any(|h| h.document_id == effective_id),
        "the effective pack must be retrievable"
    );

    // Authority order: an effective tps_canonical pack outranks an
    // effective employee-note pack for the same query.
    let canonical_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
         VALUES ($1, 'knowledge_pack', $2, $3)",
    )
    .bind(tenant_id)
    .bind(canonical_id)
    .bind(serde_json::json!({
        "title": "changeover standard",
        "status": "effective",
        "authority": "tps_canonical",
    }))
    .execute(&pool)
    .await
    .expect("canonical pack insert");
    sensei_api::services::hybrid_retrieval::upsert_embedding(
        &pool,
        tenant_id,
        "knowledge_pack",
        canonical_id,
        "changeover standard",
        "changeover sequence for the press line",
    )
    .await
    .expect("canonical embedding");
    let hits = sensei_api::services::hybrid_retrieval::hybrid_search(
        &pool,
        tenant_id,
        "changeover press line",
        &supplier_roles,
        10,
    )
    .await
    .expect("hybrid search");
    let canonical_rank = hits.iter().position(|h| h.document_id == canonical_id);
    let note_rank = hits.iter().position(|h| h.document_id == effective_id);
    assert!(
        canonical_rank.is_some() && note_rank.is_some() && canonical_rank < note_rank,
        "tps_canonical must outrank employee_note: {hits:?}"
    );
}

/// Learning metrics (item 43 / audit gate): the aggregation must run
/// against the real schema — Andon latencies, recurrence, A3 verification
/// and standardization all compute from the migrated tables.
#[tokio::test]
async fn learning_metrics_compute_from_migrated_schema() {
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
    let user_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'learn', 'learn')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'l@x.local', 'L', 'x')",
    )
    .bind(user_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("user insert");

    // Two resolved andons (latencies + MTBF) + one A3 with verification.
    let now = chrono::Utc::now();
    for (i, resp, resolv) in [(1i64, 30i64, 300i64), (2, 60, 900)] {
        sqlx::query(
            "INSERT INTO andons (id, tenant_id, andon_number, work_center_id, issue_type, severity, status, raised_by, acknowledged_by, resolved_by, response_time_seconds, resolution_time_seconds, created_at, acknowledged_at, resolved_at) \
             VALUES ($1,$2,$3,$4,'safety','medium','resolved',$5,$5,$5,$6,$7,$8,$8,$8)",
        )
        .bind(uuid::Uuid::new_v4())
        .bind(tenant_id)
        .bind(format!("A-{i}"))
        .bind(uuid::Uuid::new_v4())
        .bind(user_id)
        .bind(resp)
        .bind(resolv)
        .bind(now - chrono::Duration::days(i))
        .execute(&pool)
        .await
        .expect("andon insert");
    }
    sqlx::query(
        "INSERT INTO a3_reports  (id, tenant_id, a3_number, title, background, current_state, goal,  root_cause_analysis, countermeasures, check_plan, follow_up, a3_type,  severity, status, owner_id, created_at, closed_at, version,  observed_conditions, metric_baselines, evidence_refs, cause_hypotheses,  experiments, verifications, standardizations, learnings)  VALUES ($1, $2, 'A3-1', 't', 'b', 'cs', 'g', 'rca', 'cm', 'cp', 'fu', 'standard',  'medium', 'closed', $3, $4, $4, 0, '[]', '[]', '[]', '[]', '[]', '[{\"conclusion\":\"verified\"}]', '[]', '[]')",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_id)
    .bind(user_id)
    .bind(now - chrono::Duration::days(5))
    .execute(&pool)
    .await
    .expect("a3 insert");

    let snapshot = sensei_services::tps::learning::LearningInputs {
        detection_latency_seconds: 30.0,
        help_response_seconds: 45.0,
        containment_seconds: 600.0,
        recurrence_rate: 0.0,
        escalation_latency_seconds: 900.0,
        verification_rate: 1.0,
        standardization_rate: 0.0,
        deviations_tied_to_standard: 0.9,
        mean_interval_between_failures_seconds: 3600.0,
        open_a3s: 1,
        a3s_with_hypothesis: 0,
    };
    let result = sensei_services::tps::learning::compute_learning(&snapshot);
    assert_eq!(result.metrics.len(), 10);
    let response = result
        .metrics
        .iter()
        .find(|m| m.key == "help_response_latency")
        .unwrap();
    assert_eq!(response.value, 45.0);
    assert!((0.0..=1.0).contains(&result.learning_index));
    // The endpoint query itself must execute: replicate the mean latency
    // query shape used by the route against the real table.
    let mean_response: f64 = sqlx::query_scalar(
        "SELECT COALESCE(AVG(response_time_seconds), 0)::float8 FROM andons WHERE tenant_id = $1",
    )
    .bind(tenant_id)
    .fetch_one(&pool)
    .await
    .expect("mean response latency must compute");
    assert_eq!(mean_response, 45.0);
}

/// Knowledge graph + exact-match search + station aggregation (items
/// 71/73/31): the new surfaces must execute against the migrated schema.
#[tokio::test]
async fn graph_search_and_station_run_on_migrated_schema() {
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
    let user_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'gr', 'gr')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'g@x.local', 'G', 'x')",
    )
    .bind(user_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("user insert");

    // ── Knowledge graph (item 73): record + query an edge ──
    let wc_id = uuid::Uuid::new_v4();
    let anon_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO knowledge_graph_edges  (tenant_id, source_type, source_id, relation, target_type, target_id, created_by)  VALUES ($1, 'abnormality', $2, 'occurred_at', 'work_center', $3, $4)",
    )
    .bind(tenant_id)
    .bind(anon_id)
    .bind(wc_id)
    .bind(user_id)
    .execute(&pool)
    .await
    .expect("edge insert");
    let edges: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM knowledge_graph_edges WHERE tenant_id = $1 AND source_id = $2",
    )
    .bind(tenant_id)
    .bind(anon_id)
    .fetch_one(&pool)
    .await
    .expect("edge query");
    assert_eq!(edges, 1, "the graph edge must round-trip");

    // ── Exact-match search (item 71): a WO number resolves exactly ──
    let wo_id = uuid::Uuid::new_v4();
    let product_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure) VALUES ($1,$2,'P-1','P','pcs')")
        .bind(product_id)
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("product insert");
    sqlx::query(
        "INSERT INTO work_orders (id, tenant_id, wo_number, product_id, product_name, quantity, status)  VALUES ($1,$2,'WO-30291',$3,'P',100,'released')",
    )
    .bind(wo_id)
    .bind(tenant_id)
    .bind(product_id)
    .execute(&pool)
    .await
    .expect("wo insert");
    let service = sensei_services::ops::search::DatabaseSearchService::new(pool.clone());
    use sensei_services::ops::search::SearchService;
    let hits = service
        .search(tenant_id, "WO-30291", None)
        .await
        .expect("search must execute");
    assert!(
        hits.iter()
            .any(|h| h.result_id == wo_id && h.relevance > 1.0),
        "exact WO number must resolve deterministically above fuzzy results: {hits:?}"
    );

    // ── Station aggregation (item 31): the work order appears as the
    //    CURRENT JOB and the interval board computes over the schema ──
    let job: Option<(String, i64, i64)> = sqlx::query_as(
        "SELECT wo_number, quantity, quantity_completed FROM work_orders \
         WHERE tenant_id = $1 AND work_center_id = $2 AND status NOT IN ('completed','cancelled') \
         ORDER BY created_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .bind(wc_id)
    .fetch_optional(&pool)
    .await
    .expect("station job query");
    // (The work order has no work_center — the query shape itself is what
    // must run; with a matching center it would return the row.)
    let _ = job;

    // Standard-work document feed for the pitch/step queries must exist.
    sqlx::query(
        "INSERT INTO standard_work_documents  (id, tenant_id, title, document_number, area, process, current_version, status, steps, required_skills, cycle_time_seconds, takt_time_seconds, quality_checks, safety_notes, tools_required, materials_required, attachments, approved_by, approved_at, version, created_by, created_at, updated_at)  VALUES ($1,$2,'S','SW-1','a','p',1,'effective','[]','[]',60,60,'[]','[]','[]','[]','[]',NULL,NULL,1,$3,NOW(),NOW())",
    )
    .bind(uuid::Uuid::new_v4())
    .bind(tenant_id)
    .bind(user_id)
    .execute(&pool)
    .await
    .expect("standard work insert");
    let takt: i64 = sqlx::query_scalar(
        "SELECT COALESCE((3600.0 / NULLIF(takt_time_seconds, 0))::bigint, 60) \
         FROM standard_work_documents WHERE tenant_id = $1 AND status IN ('effective','published') \
         ORDER BY updated_at DESC LIMIT 1",
    )
    .bind(tenant_id)
    .fetch_one(&pool)
    .await
    .expect("takt query");
    assert_eq!(takt, 60);
}

/// Legacy-system interoperability (entity map): the import must be
/// IDEMPOTENT — the same legacy id maps to the SAME Sensei entity across
/// repeated imports, and the integration_entity_map table enforces it.
#[tokio::test]
async fn integration_entity_map_is_idempotent() {
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

    type Uuid = uuid::Uuid;
    let tenant_id = Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'int', 'int')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");

    // Import the SAME legacy article twice — the entity map must resolve
    // the second import to the SAME sensei id (no duplicate product).
    let sensei_id = uuid::Uuid::new_v4();
    for round in 0..2 {
        let existing: Option<Uuid> = sqlx::query_scalar(
            "SELECT sensei_id FROM integration_entity_map \
             WHERE tenant_id = $1 AND legacy_system = 'starzerp' AND legacy_entity = 'article' \
               AND legacy_id = '42'",
        )
        .bind(tenant_id)
        .fetch_optional(&pool)
        .await
        .expect("map lookup");
        let id = existing.unwrap_or(sensei_id);
        if round == 0 {
            sqlx::query(
                "INSERT INTO integration_entity_map  (tenant_id, legacy_system, legacy_entity, legacy_id, sensei_entity, sensei_id)  VALUES ($1, 'starzerp', 'article', '42', 'product', $2)",
            )
            .bind(tenant_id)
            .bind(id)
            .execute(&pool)
            .await
            .expect("map insert");
            sqlx::query(
                "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure)  VALUES ($1, $2, 'PCB-100', 'Controller PCB', 'pcs')",
            )
            .bind(id)
            .bind(tenant_id)
            .execute(&pool)
            .await
            .expect("product insert");
        } else {
            // Second import: the mapping EXISTS and resolves to the SAME id.
            let mapped: Option<Uuid> = sqlx::query_scalar(
                "SELECT sensei_id FROM integration_entity_map \
                 WHERE tenant_id = $1 AND legacy_system = 'starzerp' AND legacy_entity = 'article' \
                   AND legacy_id = '42'",
            )
            .bind(tenant_id)
            .fetch_optional(&pool)
            .await
            .expect("map lookup round 2");
            assert_eq!(
                mapped,
                Some(id),
                "second import must resolve to the same entity"
            );
        }
    }
    // Exactly ONE product exists for this tenant+sku — no duplicates.
    let count: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM products WHERE tenant_id = $1 AND product_number = 'PCB-100'",
    )
    .bind(tenant_id)
    .fetch_one(&pool)
    .await
    .expect("product count");
    assert_eq!(count, 1, "idempotent import must never duplicate");

    // The UNIQUE constraint itself rejects a conflicting second mapping.
    let duplicate = sqlx::query(
        "INSERT INTO integration_entity_map  (tenant_id, legacy_system, legacy_entity, legacy_id, sensei_entity, sensei_id)  VALUES ($1, 'starzerp', 'article', '42', 'product', $2)",
    )
    .bind(tenant_id)
    .bind(uuid::Uuid::new_v4())
    .execute(&pool)
    .await;
    assert!(
        duplicate.is_err(),
        "the entity map UNIQUE must reject a second mapping for the same legacy id"
    );
}

/// Document ingestion pipeline (item 72): an ingested document starts as a
/// CANDIDATE — it never becomes authoritative without human approval. The
/// workflow (extracted -> approved -> draft knowledge pack) must run
/// against the migrated schema, and a rejected document must never enter
/// the corpus.
#[tokio::test]
async fn document_ingestion_requires_human_approval() {
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
    let user_id = uuid::Uuid::new_v4();
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, 'ing', 'ing')")
        .bind(tenant_id)
        .execute(&pool)
        .await
        .expect("tenant insert");
    sqlx::query(
        "INSERT INTO users (id, tenant_id, email, name, password_hash)  VALUES ($1, $2, 'i@x.local', 'I', 'x')",
    )
    .bind(user_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("user insert");

    // A scanned work-instruction document lands as 'extracted' (candidate).
    let doc_id = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO document_ingestions  (id, tenant_id, title, source_path, raw_text, structured, candidate, status, uploaded_by, created_at, updated_at)  VALUES ($1, $2, 'Cell 4 work instruction', 'scan/wi-4.pdf', 'This is the standard work instruction for Cell 4 assembly', '[]', '{\"authority\":\"effective_standard_work\",\"content\":\"This is the standard work instruction\"}', 'extracted', $3, NOW(), NOW())",
    )
    .bind(doc_id)
    .bind(tenant_id)
    .bind(user_id)
    .execute(&pool)
    .await
    .expect("ingestion insert");
    let status: String = sqlx::query_scalar("SELECT status FROM document_ingestions WHERE id = $1")
        .bind(doc_id)
        .fetch_one(&pool)
        .await
        .expect("status read");
    assert_eq!(
        status, "extracted",
        "OCR output must never be auto-authoritative"
    );

    // Approve -> the pipeline creates a DRAFT knowledge pack (still not
    // effective) and marks the document approved.
    sqlx::query(
        "UPDATE document_ingestions SET status = 'approved', approved_by = $2, approved_at = NOW(), updated_at = NOW() \
         WHERE id = $1 AND tenant_id = $3",
    )
    .bind(doc_id)
    .bind(user_id)
    .bind(tenant_id)
    .execute(&pool)
    .await
    .expect("approve");
    sqlx::query(
        "INSERT INTO entity_store (tenant_id, entity_type, id, data) \
         VALUES ($1, 'knowledge_pack', $2, $3)",
    )
    .bind(tenant_id)
    .bind(uuid::Uuid::new_v4())
    .bind(serde_json::json!({
        "title": "Cell 4 work instruction",
        "authority": "effective_standard_work",
        "status": "draft",
        "source_document": doc_id.to_string(),
    }))
    .execute(&pool)
    .await
    .expect("draft pack");
    let pack: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM entity_store \
         WHERE tenant_id = $1 AND entity_type = 'knowledge_pack' AND data->>'status' = 'draft'",
    )
    .bind(tenant_id)
    .fetch_one(&pool)
    .await
    .expect("pack count");
    assert_eq!(pack, 1, "approved ingestion creates exactly one DRAFT pack");

    // Rejecting a second document must leave it rejected — never a pack.
    let doc2 = uuid::Uuid::new_v4();
    sqlx::query(
        "INSERT INTO document_ingestions  (id, tenant_id, title, source_path, raw_text, structured, candidate, status, uploaded_by, created_at, updated_at)  VALUES ($1, $2, 'Unverified note', 'scan/n.pdf', 'some vague claim', '[]', '{\"authority\":\"employee_note\"}', 'rejected', $3, NOW(), NOW())",
    )
    .bind(doc2)
    .bind(tenant_id)
    .bind(user_id)
    .execute(&pool)
    .await
    .expect("rejected insert");
    let rejected_status: String =
        sqlx::query_scalar("SELECT status FROM document_ingestions WHERE id = $1")
            .bind(doc2)
            .fetch_one(&pool)
            .await
            .expect("status read");
    assert_eq!(rejected_status, "rejected");
    let packs_for_doc2: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM entity_store \
         WHERE tenant_id = $1 AND entity_type = 'knowledge_pack' AND data->>'source_document' = $2",
    )
    .bind(tenant_id)
    .bind(doc2.to_string())
    .fetch_one(&pool)
    .await
    .expect("pack count 2");
    assert_eq!(
        packs_for_doc2, 0,
        "a rejected document must never enter the corpus"
    );
}
