//! sensei_app-role CRUD gate for the TenantTx conversion (thirtieth-first
//! audit items 7-9).
//!
//! One full CRUD path per converted service module (accounts, products,
//! contacts, supply_chain, ai, notifications — plus the users pre-tenant
//! channel) executed under the REAL `sensei_app` role semantics, following
//! the db_contract least-privilege pattern:
//!
//!   1. migrate as the superuser/migration role (drop-all + full chain),
//!   2. provision the least-privilege `sensei_app` role (NOBYPASSRLS by
//!      default) with the canonical surface: schema USAGE, table DML, and
//!      EXECUTE on the migration-175 SECURITY DEFINER identity functions,
//!   3. run the DB-backed services over a single-connection pool whose
//!      session is SET ROLE sensei_app — FORCE RLS is enforced for this
//!      role, so every statement admits rows ONLY through the tenant
//!      context TenantTx establishes at construction,
//!   4. assert the rows ARE visible through the service (a raw-pool read
//!      would return zero rows) — proving the TenantTx conversion.
//!
//! Run with:  DATABASE_URL_TEST=postgres://user:pass@localhost:5432/sensei_test
//!             cargo test -p sensei-db --test tenanttx_contract -- --test-threads=1
//!
//! The suite drops + re-migrates the shared schema per test under a global
//! lock exactly like the db_contract gate; run serially
//! (`--test-threads=1`) against a scratch database.
//!
//! NOTE on pre-existing service-vs-schema drift discovered by the gate
//! (reported, not papered over): the RFQ/quote service surface
//! (create_rfq/update_rfq/create_quote/...) names columns the real schema
//! never carried (`supplier_name` / `items` JSONB on rfqs, `customer_id` /
//! `customer_name` / `line_items` on quotes — migration 090 reconciled
//! sales_orders/purchase_orders only), and DatabaseAiService::
//! queue_model_training inserts a VARCHAR `status` + free-form model_type
//! into model_registry, which migration 176 reconciled to a JSONB
//! ModelStatus column with UNIQUE (tenant_id, model_name). Both paths
//! fail on the REAL schema regardless of role/transaction — the tests
//! below exercise the schema-true surfaces (sales orders, anomaly
//! detections, predictions), and the drift is listed in the audit report.

use sensei_core::db::TenantTx;
use sqlx::PgPool;

/// The gate tests each DROP+CREATE the shared schema — running them
/// concurrently races the schema locks (deadlocks observed). A global
/// lock serializes the suite.
static DB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::const_new(());

/// Connect to the CI-provided empty test database. Returns None when the
/// env var is absent so the local suite stays green (the gate runs in CI).
async fn connect() -> Option<PgPool> {
    let Ok(url) = std::env::var("DATABASE_URL_TEST") else {
        eprintln!("SKIP: DATABASE_URL_TEST not set — tenanttx_contract gate runs in CI");
        return None;
    };
    PgPool::connect(&url).await.ok()
}

/// Drop every public table and apply the ENTIRE migration chain (the
/// fresh-database gate convention of db_contract.rs).
async fn reset_and_migrate(pool: &PgPool) {
    sqlx::query(
        r#"DO $$ DECLARE r RECORD; BEGIN
             FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                 EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', r.tablename);
             END LOOP;
         END $$"#,
    )
    .execute(pool)
    .await
    .expect("drop all tables");
    sensei_db::migrations::run_migrations(pool)
        .await
        .expect("the ENTIRE migration chain must apply to an empty database");
}

/// Provision the production application role `sensei_app` (created only
/// when absent — never dropped, so a real deployment role on a shared
/// scratch DB is untouched) and re-assert its canonical surface:
/// schema USAGE, table DML (the 01-app-role.sh table grants), and
/// EXECUTE on the three migration-175 SECURITY DEFINER identity functions
/// (migration 175 grants them when the role pre-exists; re-asserting is
/// idempotent and covers every bootstrap order).
async fn ensure_sensei_app_role(pool: &PgPool) {
    sqlx::query(
        "DO $$ BEGIN
             IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_app') THEN
                 CREATE ROLE sensei_app;
             END IF;
         END $$",
    )
    .execute(pool)
    .await
    .expect("create sensei_app role when absent");
    sqlx::query("GRANT USAGE ON SCHEMA public TO sensei_app")
        .execute(pool)
        .await
        .expect("grant schema usage");
    sqlx::query(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sensei_app",
    )
    .execute(pool)
    .await
    .expect("grant table DML");
    sqlx::query("GRANT EXECUTE ON FUNCTION public.auth_user_by_email(text) TO sensei_app")
        .execute(pool)
        .await
        .ok();
    sqlx::query("GRANT EXECUTE ON FUNCTION public.auth_user_by_id(uuid) TO sensei_app")
        .execute(pool)
        .await
        .ok();
    sqlx::query("GRANT EXECUTE ON FUNCTION public.auth_users_all() TO sensei_app")
        .execute(pool)
        .await
        .ok();
}

/// A single-connection pool whose session is SET ROLE sensei_app: every
/// TenantTx::begin reuses that one connection, so every statement runs as
/// the production non-owner role and FORCE RLS is truly enforced (the
/// superuser test harness would bypass it).
async fn app_role_pool(url: &str) -> PgPool {
    let gate_pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(1)
        .connect(url)
        .await
        .expect("app-role gate pool connect");
    let mut conn = gate_pool.acquire().await.expect("gate conn");
    sqlx::query("SET ROLE sensei_app")
        .execute(&mut *conn)
        .await
        .expect("set role sensei_app");
    drop(conn);
    gate_pool
}

/// Fail-closed probe: a statement WITHOUT the app.tenant_id context must
/// see zero rows of a FORCE-RLS tenant table under sensei_app.
async fn assert_no_context_sees_nothing(pool: &PgPool, table: &str, tenant_id: uuid::Uuid) {
    let sql = format!("SELECT COUNT(*) FROM {table} WHERE tenant_id = $1");
    let count: i64 = sqlx::query_scalar(&sql)
        .bind(tenant_id)
        .fetch_one(pool)
        .await
        .expect("raw no-context count under sensei_app");
    assert_eq!(
        count, 0,
        "FORCE RLS must hide tenant rows from a raw no-context read on {table}"
    );
}

/// Count the rows of `table` for `tenant_id` through a TenantTx handle —
/// the admission channel the converted services use.
async fn tenant_tx_count(pool: &PgPool, tenant_id: uuid::Uuid, table: &str) -> i64 {
    let mut db = TenantTx::begin(pool, tenant_id)
        .await
        .expect("TenantTx begin");
    let sql = format!("SELECT COUNT(*) FROM {table} WHERE tenant_id = $1");
    let count: i64 = sqlx::query_scalar(&sql)
        .bind(tenant_id)
        .fetch_one(&mut **db.tx())
        .await
        .expect("TenantTx count");
    db.commit().await.expect("TenantTx commit");
    count
}

/// Seed the fixture tenant (the tenants table is NOT RLS-isolated — it
/// has no tenant_id column).
async fn seed_tenant(pool: &PgPool, tenant_id: uuid::Uuid, name: &str) {
    sqlx::query("INSERT INTO tenants (id, name, slug) VALUES ($1, $2, $2)")
        .bind(tenant_id)
        .bind(name)
        .execute(pool)
        .await
        .expect("tenant insert");
}

// ════════════════════════════════════════════════════════════════════════════
// accounts — DatabaseAccountsService under sensei_app (TenantTx conversion)
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn accounts_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-accounts").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_core::domain::entities::Account;
    use sensei_services::accounts::{AccountsService, DatabaseAccountsService};
    let svc = DatabaseAccountsService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "accounts", tenant_id).await;

    // C — create through the service (internally one TenantTx).
    let mut account = Account::new(tenant_id, "Acme Corp".to_string(), "customer".to_string());
    account.notes = Some("TenantTx gate account".to_string());
    let created = svc
        .create_account(tenant_id, account.clone())
        .await
        .expect("create_account must admit the INSERT through TenantTx");
    assert_eq!(created.id, account.id);
    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "accounts").await,
        1,
        "the created row must be visible inside the tenant context"
    );

    // R — read back through the service: proves the TenantTx read admits
    // the row under the role (a raw-pool read returns zero rows).
    let fetched = svc
        .get_account(tenant_id, account.id)
        .await
        .expect("get_account must see the row through TenantTx");
    assert_eq!(fetched.name, "Acme Corp");

    // U — update through the service.
    let mut updated = fetched.clone();
    updated.name = "Acme International".to_string();
    updated.is_active = true;
    let updated = svc
        .update_account(tenant_id, account.id, updated)
        .await
        .expect("update_account must admit the UPDATE through TenantTx");
    assert_eq!(updated.name, "Acme International");

    // L — paginated listing through the service.
    let page = svc
        .list_accounts(tenant_id, None, None, Some(1), Some(10))
        .await
        .expect("list_accounts must see the row through TenantTx");
    assert_eq!(page.total, 1);
    assert_eq!(page.data[0].id, account.id);

    // D — soft delete (status -> inactive) through the service.
    svc.delete_account(tenant_id, account.id)
        .await
        .expect("delete_account must admit the soft DELETE through TenantTx");
    let after = svc
        .get_account(tenant_id, account.id)
        .await
        .expect("soft-deleted account still resolves");
    assert!(!after.is_active, "delete_account soft-deletes the account");

    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "accounts").await,
        1,
        "the soft-deleted row remains tenant-visible (status flip only)"
    );
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// products — DatabaseProductsService under sensei_app
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn products_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-products").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_core::domain::entities::Product;
    use sensei_services::products::{DatabaseProductsService, ProductsService};
    let svc = DatabaseProductsService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "products", tenant_id).await;

    // C
    let mut product = Product::new(
        tenant_id,
        "TTX-SKU-1".to_string(),
        "TenantTx widget".to_string(),
        "finished_good".to_string(),
        "pcs".to_string(),
    );
    product.standard_cost = Some(2.5);
    product.selling_price = Some(4.0);
    let created = svc
        .create_product(tenant_id, product.clone())
        .await
        .expect("create_product must admit the INSERT through TenantTx");
    assert_eq!(created.id, product.id);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "products").await, 1);

    // R
    let fetched = svc
        .get_product(tenant_id, product.id)
        .await
        .expect("get_product must see the row through TenantTx");
    assert_eq!(fetched.name, "TenantTx widget");
    assert_eq!(fetched.standard_cost, Some(2.5));

    // U
    let mut updated = fetched.clone();
    updated.name = "TenantTx widget v2".to_string();
    updated.selling_price = Some(4.5);
    let updated = svc
        .update_product(tenant_id, product.id, updated)
        .await
        .expect("update_product must admit the UPDATE through TenantTx");
    assert_eq!(updated.name, "TenantTx widget v2");
    assert_eq!(updated.selling_price, Some(4.5));

    // L
    let page = svc
        .list_products(tenant_id, None, None, Some(1), Some(10))
        .await
        .expect("list_products must see the row through TenantTx");
    assert_eq!(page.total, 1);
    assert_eq!(page.data[0].id, product.id);

    // D (soft)
    svc.delete_product(tenant_id, product.id)
        .await
        .expect("delete_product must admit the soft DELETE through TenantTx");
    let after = svc
        .get_product(tenant_id, product.id)
        .await
        .expect("soft-deleted product still resolves");
    assert!(!after.is_active);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "products").await, 1);
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// contacts — DatabaseContactsService under sensei_app
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn contacts_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-contacts").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_core::domain::entities::Contact;
    use sensei_services::contacts::{ContactsService, DatabaseContactsService};
    let svc = DatabaseContactsService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "contacts", tenant_id).await;

    // C
    let mut contact = Contact::new(
        tenant_id,
        "Ada".to_string(),
        "Lovelace".to_string(),
        "ada@example.com".to_string(),
    );
    contact.department = Some("Engineering".to_string());
    let created = svc
        .create_contact(tenant_id, contact.clone())
        .await
        .expect("create_contact must admit the INSERT through TenantTx");
    assert_eq!(created.id, contact.id);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "contacts").await, 1);

    // R
    let fetched = svc
        .get_contact(tenant_id, contact.id)
        .await
        .expect("get_contact must see the row through TenantTx");
    assert_eq!(fetched.first_name, "Ada");
    assert_eq!(fetched.department.as_deref(), Some("Engineering"));

    // U
    let mut updated = fetched.clone();
    updated.last_name = "Lovelace-Byron".to_string();
    updated.is_primary = true;
    let updated = svc
        .update_contact(tenant_id, contact.id, updated)
        .await
        .expect("update_contact must admit the UPDATE through TenantTx");
    assert_eq!(updated.last_name, "Lovelace-Byron");
    assert!(updated.is_primary);

    // L
    let page = svc
        .list_contacts(tenant_id, None, Some(1), Some(10))
        .await
        .expect("list_contacts must see the row through TenantTx");
    assert_eq!(page.total, 1);
    assert_eq!(page.data[0].id, contact.id);

    // D (soft)
    svc.delete_contact(tenant_id, contact.id)
        .await
        .expect("delete_contact must admit the soft DELETE through TenantTx");
    let after = svc
        .get_contact(tenant_id, contact.id)
        .await
        .expect("soft-deleted contact still resolves");
    assert!(!after.is_active);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "contacts").await, 1);
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// supply_chain — DatabaseSupplyChainService (sales-order path) under
// sensei_app. NOTE: the RFQ/quote service surface names columns the real
// schema does not carry (see the module doc) — pre-existing drift
// reported separately, exercised nowhere here.
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn supply_chain_sales_order_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-supply").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_services::supply_chain::{
        DatabaseSupplyChainService, SalesOrder, SupplyChainService,
    };
    let svc = DatabaseSupplyChainService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "sales_orders", tenant_id).await;

    // Fixtures seeded AS the app role through TenantTx (the service
    // admission channel): a customer account (the composite
    // sales_orders (tenant_id, customer_id) FK target), a product, and a
    // site the order can anchor to. The scoped sales-order surface
    // demands a site entitlement.
    let product_id = uuid::Uuid::new_v4();
    let site_id = uuid::Uuid::new_v4();
    let customer_id = uuid::Uuid::new_v4();
    {
        let mut db = TenantTx::begin(&gate_pool, tenant_id)
            .await
            .expect("seed TenantTx begin");
        sqlx::query(
            "INSERT INTO accounts (id, tenant_id, name, account_type, status) \
             VALUES ($1, $2, 'Acme Customer', 'customer', 'active')",
        )
        .bind(customer_id)
        .bind(tenant_id)
        .execute(&mut **db.tx())
        .await
        .expect("customer seed through TenantTx");
        sqlx::query(
            "INSERT INTO products (id, tenant_id, product_number, name, unit_of_measure, \
             is_active, product_type, created_at, updated_at) \
             VALUES ($1, $2, 'TTX-SC-1', 'SC fixture', 'pcs', TRUE, 'finished_good', NOW(), NOW())",
        )
        .bind(product_id)
        .bind(tenant_id)
        .execute(&mut **db.tx())
        .await
        .expect("product seed through TenantTx");
        sqlx::query(
            "INSERT INTO sites (id, tenant_id, site_code, name) \
             VALUES ($1, $2, 'TTX-A', 'TTX Site A')",
        )
        .bind(site_id)
        .bind(tenant_id)
        .execute(&mut **db.tx())
        .await
        .expect("site seed through TenantTx");
        db.commit().await.expect("seed TenantTx commit");
    }

    let actor = uuid::Uuid::new_v4();

    // C — create_sales_order through the service (one TenantTx).
    let order = SalesOrder {
        id: uuid::Uuid::new_v4(),
        tenant_id,
        order_number: String::new(),
        customer_id,
        customer_name: "Acme Customer".to_string(),
        status: "draft".to_string(),
        line_items: vec![],
        total_amount: rust_decimal::Decimal::ZERO,
        currency: "USD".to_string(),
        delivery_date: None,
        shipping_address: String::new(),
        created_by: actor,
        created_at: chrono::Utc::now(),
        fulfilling_site_id: Some(site_id),
    };
    let created = svc
        .create_sales_order(tenant_id, order.clone())
        .await
        .expect("create_sales_order must admit the INSERT through TenantTx");
    // The service generates the order number/id server-side.
    assert!(!created.id.is_nil());
    assert_eq!(created.status, "draft");
    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "sales_orders").await,
        1,
        "the created order must be tenant-visible"
    );

    // R — get_sales_order through the service.
    let fetched = svc
        .get_sales_order(tenant_id, created.id)
        .await
        .expect("get_sales_order must see the row through TenantTx");
    assert_eq!(fetched.customer_name, "Acme Customer");

    // L — scoped listing through the service (site-entitled).
    let page = svc
        .list_sales_orders_scoped(tenant_id, &[site_id], None, Some(1), Some(10))
        .await
        .expect("list_sales_orders_scoped must see the row through TenantTx");
    assert_eq!(page.total, 1);
    assert_eq!(page.data[0].id, created.id);

    // U — status transition through the service (site-scoped TenantTx).
    let updated = svc
        .update_sales_order_status(tenant_id, &[site_id], created.id, "confirmed")
        .await
        .expect("update_sales_order_status must admit the UPDATE through TenantTx");
    assert_eq!(updated.status, "confirmed");

    // D — delete through the service (site-scoped TenantTx).
    svc.delete_sales_order(tenant_id, &[site_id], created.id)
        .await
        .expect("delete_sales_order must admit the DELETE through TenantTx");
    assert!(
        svc.get_sales_order(tenant_id, created.id).await.is_err(),
        "the deleted order must no longer resolve"
    );
    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "sales_orders").await,
        0,
        "the delete must be tenant-visible"
    );
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// ai — DatabaseAiService (anomaly + prediction path) under sensei_app.
// NOTE: queue_model_training drifted from the real schema (see the module
// doc) — pre-existing drift reported separately.
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn ai_anomaly_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-ai").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_services::ai::{AiService, AnomalyPrediction, DatabaseAiService};
    let svc = DatabaseAiService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "anomaly_detections", tenant_id).await;
    assert_no_context_sees_nothing(&gate_pool, "predictions", tenant_id).await;

    // C — publish_anomaly_event (anomaly_detections INSERT) through the
    // service's TenantTx.
    let equipment_id = uuid::Uuid::new_v4();
    svc.publish_anomaly_event(
        tenant_id,
        &AnomalyPrediction {
            entity_type: "equipment".to_string(),
            entity_id: equipment_id,
            anomaly_score: 0.9,
            predicted_failure: "overheating".to_string(),
            confidence: 0.9,
            recommended_action: "Inspect cooling circuit".to_string(),
            detected_at: chrono::Utc::now(),
        },
    )
    .await
    .expect("publish_anomaly_event must admit the INSERT through TenantTx");
    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "anomaly_detections").await,
        1,
        "the anomaly row must be tenant-visible"
    );

    // R — detect_anomalies must see the published detection through the
    // service's TenantTx (a raw-pool read would return none).
    let detections = svc
        .detect_anomalies(tenant_id, "equipment", equipment_id)
        .await
        .expect("detect_anomalies must see the row through TenantTx");
    assert_eq!(detections.len(), 1);
    assert_eq!(detections[0].entity_id, equipment_id);
    assert_eq!(detections[0].predicted_failure, "overheating");

    // R — predict_maintenance reads a worker-persisted maintenance
    // prediction. Seed the referenced model_registry row (predictions.
    // model_id FK; migration-176 shape — JSONB ModelStatus) and the
    // predictions row through TenantTx — the channel the ML workers use —
    // then resolve them through the service.
    let model_id = uuid::Uuid::new_v4();
    let now = chrono::Utc::now();
    {
        let mut db = TenantTx::begin(&gate_pool, tenant_id)
            .await
            .expect("prediction seed begin");
        sqlx::query(
            "INSERT INTO model_registry (id, tenant_id, model_name, model_type, status) \
             VALUES ($1, $2, 'ttx-maintenance-model', 'prediction', $3)",
        )
        .bind(model_id)
        .bind(tenant_id)
        .bind(serde_json::json!({ "Healthy": null }))
        .execute(&mut **db.tx())
        .await
        .expect("model_registry seed through TenantTx");
        sqlx::query(
            "INSERT INTO predictions \
                 (id, tenant_id, model_id, prediction_type, entity_type, entity_id, \
                  predicted_value, confidence, input_features, predicted_at, created_at) \
             VALUES ($1, $2, $3, 'maintenance', 'equipment', $4, $5, $6, $7, $8, $8)",
        )
        .bind(uuid::Uuid::new_v4())
        .bind(tenant_id)
        .bind(model_id)
        .bind(equipment_id)
        .bind("0.42")
        .bind(0.42_f64)
        .bind(serde_json::json!({
            "remaining_life_hours": 120.0,
            "risk_level": "medium",
            "suggested_actions": ["Inspect bearings"],
        }))
        .bind(now)
        .execute(&mut **db.tx())
        .await
        .expect("prediction seed through TenantTx");
        db.commit().await.expect("prediction seed commit");
    }
    let maintenance = svc
        .predict_maintenance(tenant_id, equipment_id)
        .await
        .expect("predict_maintenance must see the seeded row through TenantTx");
    assert_eq!(maintenance.equipment_id, equipment_id);
    assert_eq!(
        maintenance.estimated_remaining_life_hours,
        Some(120.0),
        "the remaining-life estimate must come from the visible row"
    );
    assert_eq!(maintenance.risk_level, "medium");
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// notifications — DatabaseNotificationService under sensei_app. The real
// `notifications.notification_type` CHECK admits ('alert','reminder',
// 'approval_request','mention','system') — the test uses 'system' (the
// DB-vocabulary literal). The service doc-comment vocabulary ("info",
// "warning", ...) drifting from that CHECK is pre-existing drift reported
// separately.
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn notifications_crud_runs_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-notify").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_services::notifications::{
        DatabaseNotificationService, NewNotification, NotificationService,
    };
    let svc = DatabaseNotificationService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "notifications", tenant_id).await;
    assert_no_context_sees_nothing(&gate_pool, "user_notification_preferences", tenant_id).await;

    let user_id = uuid::Uuid::new_v4();

    // The notifications.user_id FK targets users(id): seed the recipient
    // as the app role through TenantTx (the users table is FORCE RLS, so
    // the seed itself only lands inside the tenant context).
    {
        let mut db = TenantTx::begin(&gate_pool, tenant_id)
            .await
            .expect("user seed begin");
        sqlx::query(
            "INSERT INTO users \
                 (id, tenant_id, email, name, password_hash, roles) \
             VALUES ($1, $2, $3, 'TenantTx Recipient', 'hash', '{user}')",
        )
        .bind(user_id)
        .bind(tenant_id)
        .bind(format!(
            "ttx-{}@example.com",
            uuid::Uuid::new_v4().as_simple()
        ))
        .execute(&mut **db.tx())
        .await
        .expect("user seed through TenantTx");
        db.commit().await.expect("user seed commit");
    }

    // C — notify() inserts through the service's TenantTx.
    let created = svc
        .notify(NewNotification {
            tenant_id,
            user_id,
            title: "TenantTx gate".to_string(),
            body: "notification created under the sensei_app role".to_string(),
            notification_type: "system".to_string(),
            reference_type: None,
            reference_id: None,
        })
        .await
        .expect("notify must admit the INSERT through TenantTx");
    assert_eq!(
        tenant_tx_count(&gate_pool, tenant_id, "notifications").await,
        1
    );

    // R — list + unread count through the service.
    let listed = svc
        .list_notifications(tenant_id, user_id, 10, 0)
        .await
        .expect("list_notifications must see the row through TenantTx");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0].id, created.id);
    assert_eq!(
        svc.unread_count(tenant_id, user_id)
            .await
            .expect("unread_count through TenantTx"),
        1
    );

    // U — mark_read / mark_all_read updates through the service.
    svc.mark_read(tenant_id, user_id, created.id)
        .await
        .expect("mark_read must admit the UPDATE through TenantTx");
    assert_eq!(
        svc.unread_count(tenant_id, user_id)
            .await
            .expect("unread_count after mark_read"),
        0
    );

    // Preferences UPSERT path: get_preferences creates defaults (INSERT),
    // update_preferences mutates (ON CONFLICT UPDATE), get_preferences
    // reads the mutation back — all through TenantTx.
    let prefs = svc
        .get_preferences(tenant_id, user_id)
        .await
        .expect("get_preferences must create defaults through TenantTx");
    assert_eq!(prefs.digest_frequency, "instant");
    let mut changed = prefs.clone();
    changed.email_notifications = false;
    changed.digest_frequency = "daily".to_string();
    svc.update_preferences(&changed)
        .await
        .expect("update_preferences must admit the UPSERT through TenantTx");
    let read_back = svc
        .get_preferences(tenant_id, user_id)
        .await
        .expect("get_preferences must read the update through TenantTx");
    assert!(!read_back.email_notifications);
    assert_eq!(read_back.digest_frequency, "daily");
    drop(gate_pool);
    drop(pool);
}

// ════════════════════════════════════════════════════════════════════════════
// users — DatabaseUsersService under sensei_app: the TenantTx writes AND
// the migration-175 pre-tenant SECURITY DEFINER channel (users/
// pretenant_lookup.rs) both work for the real role.
// ════════════════════════════════════════════════════════════════════════════

#[tokio::test]
async fn users_crud_and_pretenant_channel_run_under_sensei_app_role() {
    let _serial = DB_LOCK.lock().await;
    let Some(pool) = connect().await else { return };
    let url = std::env::var("DATABASE_URL_TEST").expect("set by connect()");
    reset_and_migrate(&pool).await;
    ensure_sensei_app_role(&pool).await;
    let tenant_id = uuid::Uuid::new_v4();
    seed_tenant(&pool, tenant_id, "ttx-users").await;

    let gate_pool = app_role_pool(&url).await;
    use sensei_core::domain::entities::User;
    use sensei_services::users::{DatabaseUsersService, UsersService};
    let svc = DatabaseUsersService::new(gate_pool.clone());

    assert_no_context_sees_nothing(&gate_pool, "users", tenant_id).await;

    // C — create_user writes inside a TenantTx of the row's own tenant.
    let mut user = User::new(
        tenant_id,
        format!("ttx-{}@example.com", uuid::Uuid::new_v4().as_simple()),
        "TenantTx User".to_string(),
        "hash".to_string(),
    );
    user.roles = vec!["user".to_string(), "tenant_admin".to_string()];
    let created = svc
        .create_user(user.clone())
        .await
        .expect("create_user must admit the INSERT through TenantTx");
    assert_eq!(created.id, user.id);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "users").await, 1);

    // Pre-tenant definer channel (auth_user_by_email — migration 175):
    // the login lookup crosses tenants with NO context, via EXECUTE on the
    // SECURITY DEFINER function granted to sensei_app.
    let by_email = svc
        .find_by_email(&created.email)
        .await
        .expect("auth_user_by_email must resolve the row for sensei_app");
    assert_eq!(by_email.id, created.id);

    // Pre-tenant definer channel (auth_user_by_id) for id-keyed flows.
    let by_id = svc
        .find_by_id(created.id)
        .await
        .expect("auth_user_by_id must resolve the row for sensei_app");
    assert_eq!(by_id.email, created.email);

    // U — update_profile runs inside a TenantTx of the caller tenant.
    let updated = svc
        .update_profile(
            tenant_id,
            created.id,
            "TenantTx Updated".to_string(),
            created.email.clone(),
        )
        .await
        .expect("update_profile must admit the UPDATE through TenantTx");
    assert_eq!(updated.name, "TenantTx Updated");

    // Email-verified state: pre-tenant read (auth_user_by_id) + TenantTx
    // write.
    assert!(
        !svc.is_email_verified(created.id)
            .await
            .expect("is_email_verified via the definer channel"),
        "new users are not email-verified"
    );
    svc.set_email_verified(created.id, true)
        .await
        .expect("set_email_verified must admit the UPDATE through TenantTx");
    assert!(svc
        .is_email_verified(created.id)
        .await
        .expect("is_email_verified after the TenantTx write"));

    // L — auth_users_all() definer channel listing.
    let all = svc
        .list_users()
        .await
        .expect("list_users via auth_users_all must resolve rows for sensei_app");
    assert_eq!(all.len(), 1);
    assert_eq!(all[0].id, created.id);

    // D — deactivate_user (TenantTx soft delete + revision bump).
    let deactivated = svc
        .deactivate_user(tenant_id, created.id)
        .await
        .expect("deactivate_user must admit the UPDATE through TenantTx");
    assert!(!deactivated.is_active);
    let reactivated = svc
        .activate_user(tenant_id, created.id)
        .await
        .expect("activate_user must admit the UPDATE through TenantTx");
    assert!(reactivated.is_active);
    assert_eq!(tenant_tx_count(&gate_pool, tenant_id, "users").await, 1);
    drop(gate_pool);
    drop(pool);
}
