//! PostgreSQL-backed supply chain service using sqlx.
//!
//! Provides RFQ, quote, sales order, purchase order, inventory, and stock
//! movement management backed by PostgreSQL tables. Implements [`SupplyChainService`].

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde_json;
use sqlx::PgPool;
use uuid::Uuid;

use super::{
    InventoryItem, POItem, PurchaseOrder, Quote, QuoteLineItem, RFQItem, ReceiveStockCommand,
    SalesOrder, SalesOrderItem, StockMove, SupplyChainService, RFQ,
};
use crate::tps::replication::with_tenant_tx;

/// PostgreSQL-backed implementation of [`SupplyChainService`].
/// Transaction-scoped tenant context for RLS (SET LOCAL app.tenant_id).
async fn set_tenant_context(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
) -> std::result::Result<(), SenseiError> {
    sqlx::query("SELECT set_config('app.tenant_id', $1, true)")
        .bind(tenant_id.to_string())
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to set tenant context: {e}")))?;
    Ok(())
}

/// Apply a signed quantity delta to the inventory row of ONE site at
/// `location`, creating the row when it does not exist (receipts create
/// stock). The site is part of the predicate: two sites may stock the
/// same product at the same location name, and a delta is NEVER applied
/// tenant-globally.
async fn apply_inventory_delta(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
    product_id: Uuid,
    location: &str,
    delta: i64,
) -> Result<()> {
    apply_inventory_delta_with_lot(tx, tenant_id, site_id, product_id, location, None, delta).await
}

/// Lot-aware signed delta (twenty-fifth audit P1): like
/// [`apply_inventory_delta`] but the affected row may carry a specific
/// `lot_number` (the manual receipt command and the compensating
/// reversal both preserve the lot identity of the row they touch).
async fn apply_inventory_delta_with_lot(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
    product_id: Uuid,
    location: &str,
    lot_number: Option<&str>,
    delta: i64,
) -> Result<()> {
    // The unique index on (tenant, site, product, location, lot_number)
    // treats NULL lot numbers as distinct, so update-then-insert is used
    // instead of ON CONFLICT.
    // Never clamp an inventory transaction: an issue that would drive
    // the balance negative must be REJECTED so the ledger and the
    // balance can never disagree.
    let updated = sqlx::query(
        "UPDATE inventory_items \
         SET quantity_on_hand = quantity_on_hand + $1::double precision, \
             quantity_available = quantity_on_hand + $1::double precision - quantity_reserved \
         WHERE tenant_id = $2 AND site_id = $3 AND product_id = $4 AND location = $5 \
           AND lot_number IS NOT DISTINCT FROM $6 \
           AND quantity_on_hand + $1::double precision >= 0",
    )
    .bind(delta)
    .bind(tenant_id)
    .bind(site_id)
    .bind(product_id)
    .bind(location)
    .bind(lot_number)
    .execute(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to update inventory: {e}")))?;

    if updated.rows_affected() == 0 {
        // No row exists for (tenant, site, product, location, lot): only a
        // positive (receipt-like) delta may create stock. Issuing from
        // nothing is a rejected transaction.
        if delta < 0 {
            return Err(SenseiError::Validation(format!(
                "Insufficient stock at '{location}' for product {product_id}: \
                 {delta} units would drive the balance negative"
            )));
        }
        sqlx::query(
            "INSERT INTO inventory_items \
             (id, tenant_id, site_id, product_id, location, quantity_on_hand, quantity_reserved, quantity_available, lot_number) \
             VALUES ($1, $2, $3, $4, $5, $6, 0, $6, $7)",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(site_id)
        .bind(product_id)
        .bind(location)
        .bind(delta)
        .bind(lot_number)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create inventory row: {e}")))?;
    }
    Ok(())
}

/// The SITE's receiving location (twenty-fifth audit P1): the site's
/// CONFIGURED default receiving location from `site_manifests` when one
/// exists, else the literal site-local label 'receiving'. A receiving
/// location is a property OF THE SITE — it is NEVER a label discovered
/// tenant-wide from another plant's inventory rows.
async fn site_receiving_location(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
) -> Result<String> {
    let configured: Option<String> = sqlx::query_scalar(
        "SELECT default_receiving_location FROM site_manifests \
         WHERE tenant_id = $1 AND site_id = $2",
    )
    .bind(tenant_id)
    .bind(site_id)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to read site receiving location: {e}")))?;
    Ok(configured
        .filter(|l| !l.trim().is_empty())
        .unwrap_or_else(|| "receiving".to_string()))
}

/// Resolve the receiving location for a SITE: the product's first known
/// inventory location AT THAT SITE, falling back to the SITE's receiving
/// location ([`site_receiving_location`]) when the site has no row — a
/// receipt still lands on a site-owned row because
/// [`apply_inventory_delta`] stamps the site on creation. There is NO
/// tenant-wide fallback: another plant's label is never borrowed.
async fn resolve_stock_location(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    site_id: Uuid,
    product_id: Uuid,
) -> Result<String> {
    let location: Option<String> = sqlx::query_scalar(
        "SELECT location FROM inventory_items \
         WHERE tenant_id = $1 AND product_id = $2 AND site_id = $3 \
         ORDER BY created_at LIMIT 1",
    )
    .bind(tenant_id)
    .bind(product_id)
    .bind(site_id)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to resolve stock location: {e}")))?;
    if let Some(location) = location {
        return Ok(location);
    }
    site_receiving_location(tx, tenant_id, site_id).await
}

pub struct DatabaseSupplyChainService {
    pool: PgPool,
}

impl DatabaseSupplyChainService {
    /// Create a new [`DatabaseSupplyChainService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Tenant-wide fallback location for a product (the first inventory row
/// ever created), or the warehouse default `main`.
async fn fallback_product_location(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    product_id: Uuid,
) -> Result<String> {
    let loc: Option<String> = sqlx::query_scalar(
        "SELECT location FROM inventory_items \
         WHERE tenant_id = $1 AND product_id = $2 \
         ORDER BY created_at LIMIT 1",
    )
    .bind(tenant_id)
    .bind(product_id)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to resolve stock location: {e}")))?;
    Ok(loc.unwrap_or_else(|| "main".to_string()))
}

/// The DISTINCT sites owning inventory rows at (tenant, product,
/// location). `entitled` narrows to the caller's site scope; `None` (the
/// unscoped path) considers every site-carrying row. Rows with a NULL
/// site are never candidates.
async fn sites_at_location(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    product_id: Uuid,
    location: &str,
    entitled: Option<&[Uuid]>,
) -> Result<Vec<Uuid>> {
    let mut sql = String::from(
        "SELECT DISTINCT site_id FROM inventory_items \
         WHERE tenant_id = $1 AND product_id = $2 AND location = $3 \
           AND site_id IS NOT NULL",
    );
    if entitled.is_some() {
        sql.push_str(" AND site_id = ANY($4)");
    }
    let mut q = sqlx::query_scalar(&sql)
        .bind(tenant_id)
        .bind(product_id)
        .bind(location);
    if let Some(sites) = entitled {
        q = q.bind(sites);
    }
    q.fetch_all(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to scope inventory rows: {e}")))
}

/// The first entitled inventory row of a product (site within
/// `entitled`): used as the location default when the caller names none.
async fn entitled_anchor_row(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    product_id: Uuid,
    entitled: &[Uuid],
) -> Result<Option<(String, Uuid)>> {
    let anchor: Option<(String, Uuid)> = sqlx::query_as(
        "SELECT location, site_id FROM inventory_items \
         WHERE tenant_id = $1 AND product_id = $2 AND site_id = ANY($3) \
         ORDER BY created_at LIMIT 1",
    )
    .bind(tenant_id)
    .bind(product_id)
    .bind(entitled)
    .fetch_optional(&mut **tx)
    .await
    .map_err(|e| SenseiError::Database(format!("Failed to resolve entitled row: {e}")))?;
    Ok(anchor)
}

/// The SINGLE site owning rows at (tenant, product, location) — `None`
/// when no row is site-attributable, Err(Validation) when several sites
/// own a row there (the effect could not be attributed to one row).
/// `entitled` narrows to the caller's site scope.
async fn resolve_single_site(
    tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
    tenant_id: Uuid,
    product_id: Uuid,
    location: &str,
    entitled: Option<&[Uuid]>,
) -> Result<Option<Uuid>> {
    let rows = sites_at_location(tx, tenant_id, product_id, location, entitled).await?;
    match rows.as_slice() {
        [site] => Ok(Some(*site)),
        [] => Ok(None),
        _ => Err(SenseiError::Validation(format!(
            "Inventory at '{location}' for product {product_id} is owned by \
             multiple sites — the move cannot be attributed to one site"
        ))),
    }
}

// ---------------------------------------------------------------------------
// Row structs
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
struct RfqRow {
    id: Uuid,
    tenant_id: Uuid,
    rfq_number: String,
    supplier_id: Uuid,
    supplier_name: String,
    status: String,
    items: serde_json::Value,
    notes: String,
    created_by: Uuid,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct QuoteRow {
    id: Uuid,
    tenant_id: Uuid,
    quote_number: String,
    rfq_id: Option<Uuid>,
    customer_id: Uuid,
    customer_name: String,
    status: String,
    line_items: serde_json::Value,
    total_amount: rust_decimal::Decimal,
    currency: String,
    valid_until: chrono::DateTime<Utc>,
    created_by: Uuid,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct SalesOrderRow {
    id: Uuid,
    tenant_id: Uuid,
    order_number: String,
    customer_id: Uuid,
    customer_name: String,
    status: String,
    line_items: serde_json::Value,
    total_amount: rust_decimal::Decimal,
    currency: String,
    delivery_date: Option<chrono::DateTime<Utc>>,
    shipping_address: String,
    created_by: Uuid,
    created_at: chrono::DateTime<Utc>,
    fulfilling_site_id: Option<Uuid>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct PurchaseOrderRow {
    id: Uuid,
    tenant_id: Uuid,
    po_number: String,
    supplier_id: Uuid,
    supplier_name: String,
    status: String,
    line_items: serde_json::Value,
    total_amount: rust_decimal::Decimal,
    currency: String,
    expected_delivery: Option<chrono::DateTime<Utc>>,
    created_by: Uuid,
    created_at: chrono::DateTime<Utc>,
    receiving_site_id: Option<Uuid>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct InventoryRow {
    id: Uuid,
    tenant_id: Uuid,
    product_id: Uuid,
    product_name: String,
    quantity_on_hand: i64,
    quantity_reserved: i64,
    quantity_available: i64,
    location: String,
    lot_number: Option<String>,
    reorder_point: i64,
    reorder_quantity: i64,
    updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
struct StockMoveRow {
    id: Uuid,
    tenant_id: Uuid,
    product_id: Uuid,
    product_name: String,
    quantity: i64,
    move_type: String,
    from_location: Option<String>,
    to_location: String,
    reference_type: Option<String>,
    reference_id: Option<Uuid>,
    /// The real schema stores the actor in the nullable `moved_by`
    /// column (moves recorded by PO receipts have no actor).
    created_by: Option<Uuid>,
    created_at: chrono::DateTime<Utc>,
    /// Twenty-fifth audit P1: the public ledger state — the move's site,
    /// its status and the full reversal linkage.
    site_id: Option<Uuid>,
    status: String,
    reversed_by: Option<Uuid>,
    reversed_at: Option<chrono::DateTime<Utc>>,
    reversal_reason: Option<String>,
    reversal_of: Option<Uuid>,
    reversed_by_move: Option<Uuid>,
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

fn rfq_row_to_domain(r: RfqRow) -> RFQ {
    let items: Vec<RFQItem> = serde_json::from_value(r.items).unwrap_or_default();
    RFQ {
        id: r.id,
        tenant_id: r.tenant_id,
        rfq_number: r.rfq_number,
        supplier_id: r.supplier_id,
        supplier_name: r.supplier_name,
        status: r.status,
        items,
        notes: r.notes,
        created_by: r.created_by,
        created_at: r.created_at,
    }
}

fn quote_row_to_domain(r: QuoteRow) -> Quote {
    let line_items: Vec<QuoteLineItem> = serde_json::from_value(r.line_items).unwrap_or_default();
    Quote {
        id: r.id,
        tenant_id: r.tenant_id,
        quote_number: r.quote_number,
        rfq_id: r.rfq_id,
        customer_id: r.customer_id,
        customer_name: r.customer_name,
        status: r.status,
        line_items,
        total_amount: r.total_amount,
        currency: r.currency,
        valid_until: r.valid_until,
        created_by: r.created_by,
        created_at: r.created_at,
    }
}

fn so_row_to_domain(r: SalesOrderRow) -> SalesOrder {
    let line_items: Vec<SalesOrderItem> = serde_json::from_value(r.line_items).unwrap_or_default();
    SalesOrder {
        id: r.id,
        tenant_id: r.tenant_id,
        order_number: r.order_number,
        customer_id: r.customer_id,
        customer_name: r.customer_name,
        status: r.status,
        line_items,
        total_amount: r.total_amount,
        currency: r.currency,
        delivery_date: r.delivery_date,
        shipping_address: r.shipping_address,
        created_by: r.created_by,
        created_at: r.created_at,
        fulfilling_site_id: r.fulfilling_site_id,
    }
}

fn po_row_to_domain(r: PurchaseOrderRow) -> PurchaseOrder {
    let line_items: Vec<POItem> = serde_json::from_value(r.line_items).unwrap_or_default();
    PurchaseOrder {
        id: r.id,
        tenant_id: r.tenant_id,
        po_number: r.po_number,
        supplier_id: r.supplier_id,
        supplier_name: r.supplier_name,
        status: r.status,
        line_items,
        total_amount: r.total_amount,
        currency: r.currency,
        expected_delivery: r.expected_delivery,
        created_by: r.created_by,
        created_at: r.created_at,
        receiving_site_id: r.receiving_site_id,
    }
}

fn inv_row_to_domain(r: InventoryRow) -> InventoryItem {
    InventoryItem {
        id: r.id,
        tenant_id: r.tenant_id,
        product_id: r.product_id,
        product_name: r.product_name,
        quantity_on_hand: r.quantity_on_hand,
        quantity_reserved: r.quantity_reserved,
        quantity_available: r.quantity_available,
        location: r.location,
        lot_number: r.lot_number,
        reorder_point: r.reorder_point,
        reorder_quantity: r.reorder_quantity,
        updated_at: r.updated_at,
    }
}

fn sm_row_to_domain(r: StockMoveRow) -> StockMove {
    StockMove {
        id: r.id,
        tenant_id: r.tenant_id,
        product_id: r.product_id,
        product_name: r.product_name,
        quantity: r.quantity,
        move_type: r.move_type,
        from_location: r.from_location,
        to_location: r.to_location,
        reference_type: r.reference_type,
        reference_id: r.reference_id,
        // NULL moved_by (receipt-recorded moves) surfaces as the nil
        // actor rather than fabricating one.
        created_by: r.created_by.unwrap_or_default(),
        created_at: r.created_at,
        site_id: r.site_id,
        status: r.status,
        reversed_by: r.reversed_by,
        reversed_at: r.reversed_at,
        reversal_reason: r.reversal_reason,
        reversal_of: r.reversal_of,
        reversed_by_move: r.reversed_by_move,
    }
}

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items,
        total: count as usize,
        page,
        per_page,
        total_pages: (count as usize).max(1).div_ceil(per_page),
    }
}

fn gen_id() -> (Uuid, String) {
    let id = Uuid::new_v4();
    let suffix = id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string();
    (id, suffix)
}

#[async_trait]
impl SupplyChainService for DatabaseSupplyChainService {
    // ── RFQ ─────────────────────────────────────────────────────────────

    async fn create_rfq(&self, tenant_id: Uuid, rfq: RFQ) -> Result<RFQ> {
        let now = Utc::now();
        let (id, suffix) = gen_id();
        let rfq_number = format!("RFQ-{}-{}", now.format("%Y%m%d"), suffix);
        let items_json =
            serde_json::to_value(&rfq.items).unwrap_or(serde_json::Value::Array(vec![]));

        let row = sqlx::query_as::<_, RfqRow>(
            r#"INSERT INTO rfqs (id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at)
               VALUES ($1,$2,$3,$4,$5,'draft',$6,$7,$8,$9)
               RETURNING id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at"#,
        )
        .bind(id).bind(tenant_id).bind(&rfq_number).bind(rfq.supplier_id).bind(&rfq.supplier_name)
        .bind(&items_json).bind(&rfq.notes).bind(rfq.created_by).bind(now)
        .fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to create RFQ: {e}")))?;

        Ok(rfq_row_to_domain(row))
    }

    async fn get_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        let row = sqlx::query_as::<_, RfqRow>(
            "SELECT id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at FROM rfqs WHERE id=$1 AND tenant_id=$2",
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get RFQ: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        Ok(rfq_row_to_domain(row))
    }

    async fn list_rfqs(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<RFQ>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let items: Vec<RfqRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at FROM rfqs
               WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list RFQs: {e}")))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM rfqs WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)",
        )
        .bind(tenant_id)
        .bind(status)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to count RFQs: {e}")))?;
        Ok(paginate(
            items.into_iter().map(rfq_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn update_rfq_status(&self, tenant_id: Uuid, id: Uuid, status: &str) -> Result<RFQ> {
        let row = sqlx::query_as::<_, RfqRow>(
            r#"UPDATE rfqs SET status=$1 WHERE id=$2 AND tenant_id=$3
               RETURNING id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at"#,
        ).bind(status).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to update RFQ status: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        Ok(rfq_row_to_domain(row))
    }

    // ── Quotes ──────────────────────────────────────────────────────────

    async fn create_quote(&self, tenant_id: Uuid, quote: Quote) -> Result<Quote> {
        let now = Utc::now();
        let (id, suffix) = gen_id();
        let quote_number = format!("QTE-{}-{}", now.format("%Y%m%d"), suffix);
        let li_json =
            serde_json::to_value(&quote.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = quote.line_items.iter().map(|li| li.net_price).sum();

        let row = sqlx::query_as::<_, QuoteRow>(
            r#"INSERT INTO quotes (id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,'draft',$7,$8,$9,$10,$11,$12)
               RETURNING id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at"#,
        ).bind(id).bind(tenant_id).bind(&quote_number).bind(quote.rfq_id).bind(quote.customer_id)
            .bind(&quote.customer_name).bind(&li_json).bind(total).bind(&quote.currency)
            .bind(quote.valid_until).bind(quote.created_by).bind(now)
            .fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to create quote: {e}")))?;
        Ok(quote_row_to_domain(row))
    }

    async fn get_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let row = sqlx::query_as::<_, QuoteRow>(
            "SELECT id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at FROM quotes WHERE id=$1 AND tenant_id=$2",
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get quote: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(quote_row_to_domain(row))
    }

    async fn list_quotes(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Quote>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let items: Vec<QuoteRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at FROM quotes
               WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list quotes: {e}")))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quotes WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)",
        )
        .bind(tenant_id)
        .bind(status)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to count quotes: {e}")))?;
        Ok(paginate(
            items.into_iter().map(quote_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn approve_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let row = sqlx::query_as::<_, QuoteRow>(
            r#"UPDATE quotes SET status='approved' WHERE id=$1 AND tenant_id=$2
               RETURNING id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at"#,
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to approve quote: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(quote_row_to_domain(row))
    }

    async fn convert_quote_to_order(
        &self,
        tenant_id: Uuid,
        quote_id: Uuid,
        actor_id: Uuid,
    ) -> Result<SalesOrder> {
        let quote = self.get_quote(tenant_id, quote_id).await?;
        let now = Utc::now();
        let (id, suffix) = gen_id();
        let order_number = format!("SO-{}-{}", now.format("%Y%m%d"), suffix);
        let so_items: Vec<SalesOrderItem> = quote
            .line_items
            .iter()
            .map(|li| SalesOrderItem {
                product_id: li.product_id,
                product_name: li.product_name.clone(),
                quantity: li.quantity,
                unit_price: li.unit_price,
                delivered_quantity: 0,
            })
            .collect();
        let li_json = serde_json::to_value(&so_items).unwrap_or(serde_json::Value::Array(vec![]));

        let row = sqlx::query_as::<_, SalesOrderRow>(
            r#"INSERT INTO sales_orders (id, tenant_id, so_number, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id)
               VALUES ($1,$2,$3,$3,$4,$5,'draft',$6,$7,$8,NULL,'',$9,$10,NULL)
               RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#,
        ).bind(id).bind(tenant_id).bind(&order_number).bind(quote.customer_id).bind(&quote.customer_name)
            .bind(&li_json).bind(quote.total_amount).bind(&quote.currency).bind(actor_id).bind(now)
            .fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to convert quote to order: {e}")))?;

        sqlx::query("UPDATE quotes SET status='converted' WHERE id=$1 AND tenant_id=$2")
            .bind(quote_id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to update quote status: {e}")))?;

        Ok(so_row_to_domain(row))
    }

    // ── Sales Orders ────────────────────────────────────────────────────

    async fn get_sales_order_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<SalesOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no sales order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, SalesOrderRow>(
                    "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders WHERE id=$1 AND tenant_id=$2 AND fulfilling_site_id = ANY($3)",
                ).bind(id).bind(tenant_id).bind(&sites).fetch_optional(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to get scoped sales order: {e}")))?
                    .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
                Ok(so_row_to_domain(row))
            })
        })
        .await
    }

    async fn list_sales_orders_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SalesOrder>> {
        if authorized_sites.is_empty() {
            let page = page.unwrap_or(1).max(1);
            let per_page = per_page.unwrap_or(20).clamp(1, 100);
            return Ok(paginate(Vec::new(), 0, page, per_page));
        }
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let status_owned = status.map(|x| x.to_string());
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let items: Vec<SalesOrderRow> = sqlx::query_as(
                    "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders \
                     WHERE tenant_id=$1 AND fulfilling_site_id = ANY($2) \
                       AND ($3::text IS NULL OR status=$3) \
                     ORDER BY created_at DESC LIMIT $4 OFFSET $5",
                ).bind(tenant_id).bind(&sites).bind(&status_owned).bind(per_page as i64).bind(offset as i64)
                    .fetch_all(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to list scoped sales orders: {e}")))?;
                let count: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM sales_orders WHERE tenant_id=$1 AND fulfilling_site_id = ANY($2) \
                     AND ($3::text IS NULL OR status=$3)",
                )
                .bind(tenant_id).bind(&sites).bind(&status_owned)
                .fetch_one(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to count scoped sales orders: {e}")))?;
                Ok(paginate(
                    items.into_iter().map(so_row_to_domain).collect(),
                    count,
                    page,
                    per_page,
                ))
            })
        })
        .await
    }

    async fn get_purchase_order_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<PurchaseOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, PurchaseOrderRow>(
                    "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders WHERE id=$1 AND tenant_id=$2 AND receiving_site_id = ANY($3)",
                ).bind(id).bind(tenant_id).bind(&sites).fetch_optional(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to get scoped purchase order: {e}")))?
                    .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;
                Ok(po_row_to_domain(row))
            })
        })
        .await
    }

    async fn list_purchase_orders_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PurchaseOrder>> {
        if authorized_sites.is_empty() {
            let page = page.unwrap_or(1).max(1);
            let per_page = per_page.unwrap_or(20).clamp(1, 100);
            return Ok(paginate(Vec::new(), 0, page, per_page));
        }
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let status_owned = status.map(|x| x.to_string());
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let items: Vec<PurchaseOrderRow> = sqlx::query_as(
                    "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders \
                     WHERE tenant_id=$1 AND receiving_site_id = ANY($2) \
                       AND ($3::text IS NULL OR status=$3) \
                     ORDER BY created_at DESC LIMIT $4 OFFSET $5",
                ).bind(tenant_id).bind(&sites).bind(&status_owned).bind(per_page as i64).bind(offset as i64)
                    .fetch_all(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to list scoped purchase orders: {e}")))?;
                let count: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM purchase_orders WHERE tenant_id=$1 AND receiving_site_id = ANY($2) \
                     AND ($3::text IS NULL OR status=$3)",
                )
                .bind(tenant_id).bind(&sites).bind(&status_owned)
                .fetch_one(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to count scoped purchase orders: {e}")))?;
                Ok(paginate(
                    items.into_iter().map(po_row_to_domain).collect(),
                    count,
                    page,
                    per_page,
                ))
            })
        })
        .await
    }

    async fn create_sales_order(&self, tenant_id: Uuid, order: SalesOrder) -> Result<SalesOrder> {
        let now = Utc::now();
        let (id, suffix) = gen_id();
        let order_number = format!("SO-{}-{}", now.format("%Y%m%d"), suffix);
        let li_json =
            serde_json::to_value(&order.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = order
            .line_items
            .iter()
            .map(|li| rust_decimal::Decimal::from(li.quantity) * li.unit_price)
            .sum();
        let customer_id = order.customer_id;
        let customer_name = order.customer_name;
        let currency = order.currency;
        let delivery_date = order.delivery_date;
        let shipping_address = order.shipping_address;
        let created_by = order.created_by;
        let fulfilling_site_id = order.fulfilling_site_id;

        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, SalesOrderRow>(
                    r#"INSERT INTO sales_orders (id, tenant_id, so_number, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id)
                       VALUES ($1,$2,$3,$3,$4,$5,'draft',$6,$7,$8,$9,$10,$11,$12,$13)
                       RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#,
                ).bind(id).bind(tenant_id).bind(&order_number).bind(customer_id).bind(&customer_name)
                    .bind(&li_json).bind(total).bind(&currency).bind(delivery_date).bind(&shipping_address).bind(created_by).bind(now)
                    .bind(fulfilling_site_id)
                    .fetch_one(&mut **tx).await.map_err(|e| SenseiError::Database(format!("Failed to create sales order: {e}")))?;
                Ok(so_row_to_domain(row))
            })
        })
        .await
    }

    async fn get_sales_order(&self, tenant_id: Uuid, id: Uuid) -> Result<SalesOrder> {
        let row = sqlx::query_as::<_, SalesOrderRow>(
            "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders WHERE id=$1 AND tenant_id=$2",
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get sales order: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
        Ok(so_row_to_domain(row))
    }

    async fn list_sales_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SalesOrder>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let items: Vec<SalesOrderRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders
               WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list sales orders: {e}")))?;
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM sales_orders WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)")
            .bind(tenant_id).bind(status).fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to count sales orders: {e}")))?;
        Ok(paginate(
            items.into_iter().map(so_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn update_sales_order_status(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
        status: &str,
    ) -> Result<SalesOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no sales order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        // Status transitions STAMP the immutable shipment timestamps
        // (migration 133) — confirmed on first confirm, shipped on first
        // ship, delivered on first deliver; the anchors are NEVER
        // rewritten by later transitions.
        //
        // ANTI-GAMING RULE (migration 139): the COMMITMENT anchors
        // (committed_date, original_requested_date) are also written here
        // via COALESCE — ONCE at first confirmation, from the delivery
        // promise in force at that moment. A later confirmation, edit or
        // status transition can never rewrite them, so the OTD metric
        // cannot be improved by editing dates after the fact.
        // Twenty-first audit item 9: an order that will feed plant
        // delivery metrics must carry its fulfilling site from the FIRST
        // confirmation — without the site anchor the order cannot
        // contribute to any site's OTD and confirmation is refused.
        // Twenty-third audit P0: the caller's site boundary is part of
        // THE SAME predicate as the write — an order whose fulfilling
        // site is NULL or outside `authorized_sites` is indistinguishable
        // from a nonexistent order, so the transition can never be
        // applied to a foreign row.
        let stamp = "CASE                        WHEN $1 = 'confirmed' AND confirmed_at IS NULL THEN NOW()                        WHEN $1 IN ('shipped') AND shipped_at IS NULL THEN NOW()                        WHEN $1 IN ('delivered') AND delivered_at IS NULL THEN NOW()                      END";
        let status_owned = status.to_string();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, SalesOrderRow>(
                    &format!(
                        r#"UPDATE sales_orders SET status=$1,
                               confirmed_at          = COALESCE(confirmed_at, {stamp}),
                               shipped_at            = COALESCE(shipped_at, {stamp}),
                               delivered_at          = COALESCE(delivered_at, {stamp}),
                               committed_date        = COALESCE(committed_date, CASE WHEN $1 = 'confirmed' THEN delivery_date END),
                               original_requested_date = COALESCE(original_requested_date, CASE WHEN $1 = 'confirmed' THEN delivery_date END),
                               commitment_revision   = CASE WHEN $1 = 'confirmed' THEN 1 ELSE commitment_revision END,
                               actual_ship_date      = COALESCE(actual_ship_date, CASE WHEN $1 = 'shipped' THEN NOW() END),
                               actual_delivery_date  = COALESCE(actual_delivery_date, CASE WHEN $1 = 'delivered' THEN NOW() END)
                           WHERE id=$2 AND tenant_id=$3 AND fulfilling_site_id = ANY($4)
                           RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#
                    ),
                ).bind(&status_owned).bind(id).bind(tenant_id).bind(&sites).fetch_optional(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to update sales order status: {e}")))?
                    .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
                Ok(so_row_to_domain(row))
            })
        })
        .await
    }

    async fn assign_fulfillment_site(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        order_id: Uuid,
        site_id: Uuid,
    ) -> Result<SalesOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no sales order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        // The fulfilling site is IMMUTABLE once set (SalesOrder doc): a
        // re-anchor to a DIFFERENT site is refused, re-assigning the
        // SAME site is a no-op, and only a NULL anchor is filled.
        // Twenty-third audit P0: the caller's site boundary is embedded
        // in the same predicate as the write — a NULL anchor may only be
        // filled with a site inside `authorized_sites`, and an order
        // already anchored OUTSIDE the caller's scope is
        // indistinguishable from a nonexistent order.
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;
        // Read the row's site INSIDE the tx under FOR UPDATE; the read is
        // itself scoped so a foreign anchor never even surfaces.
        let existing: Option<Option<Uuid>> = sqlx::query_scalar(
            "SELECT fulfilling_site_id FROM sales_orders \
             WHERE id = $1 AND tenant_id = $2 \
               AND (fulfilling_site_id IS NULL OR fulfilling_site_id = ANY($3)) \
             FOR UPDATE",
        )
        .bind(order_id)
        .bind(tenant_id)
        .bind(&sites)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to read order site anchor: {e}")))?;
        match existing {
            None => Err(SenseiError::NotFound(format!(
                "Sales order {order_id} not found"
            ))),
            Some(Some(existing_site)) => {
                if existing_site != site_id {
                    return Err(SenseiError::Validation(format!(
                        "sales order {order_id} already names fulfilling site {existing_site} — \
                         the fulfilling site is immutable"
                    )));
                }
                // Same-site no-op: return the locked row.
                let row = sqlx::query_as::<_, SalesOrderRow>(
                    "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders WHERE id=$1 AND tenant_id=$2",
                ).bind(order_id).bind(tenant_id).fetch_one(&mut *tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to reload sales order: {e}")))?;
                tx.commit()
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
                Ok(so_row_to_domain(row))
            }
            Some(None) => {
                // NULL anchor: fill it with the requested site ONLY when
                // that site is inside the caller's entitlement — the
                // boundary is in the same predicate as the UPDATE.
                let row = sqlx::query_as::<_, SalesOrderRow>(
                    r#"UPDATE sales_orders SET fulfilling_site_id=$3
                       WHERE id=$1 AND tenant_id=$2 AND fulfilling_site_id IS NULL
                         AND $3::uuid = ANY($4)
                       RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#,
                ).bind(order_id).bind(tenant_id).bind(site_id).bind(&sites)
                    .fetch_optional(&mut *tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to assign fulfilling site: {e}")))?
                    .ok_or_else(|| SenseiError::NotFound(format!("Sales order {order_id} not found")))?;
                tx.commit()
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
                Ok(so_row_to_domain(row))
            }
        }
    }

    async fn confirm_sales_order_with_site(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        order_id: Uuid,
        site_id: Uuid,
    ) -> Result<SalesOrder> {
        self.assign_fulfillment_site(tenant_id, authorized_sites, order_id, site_id)
            .await?;
        self.update_sales_order_status(tenant_id, authorized_sites, order_id, "confirmed")
            .await
    }

    // ── Purchase Orders ─────────────────────────────────────────────────

    async fn create_purchase_order(
        &self,
        tenant_id: Uuid,
        po: PurchaseOrder,
    ) -> Result<PurchaseOrder> {
        let now = Utc::now();
        let (id, suffix) = gen_id();
        let po_number = format!("PO-{}-{}", now.format("%Y%m%d"), suffix);
        let li_json =
            serde_json::to_value(&po.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = po
            .line_items
            .iter()
            .map(|li| rust_decimal::Decimal::from(li.quantity_ordered) * li.unit_price)
            .sum();
        let supplier_id = po.supplier_id;
        let supplier_name = po.supplier_name;
        let currency = po.currency;
        let expected_delivery = po.expected_delivery;
        let created_by = po.created_by;
        let receiving_site_id = po.receiving_site_id;

        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let row = sqlx::query_as::<_, PurchaseOrderRow>(
                    r#"INSERT INTO purchase_orders (id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id)
                       VALUES ($1,$2,$3,$4,$5,'draft',$6,$7,$8,$9,$10,$11,$12)
                       RETURNING id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id"#,
                ).bind(id).bind(tenant_id).bind(&po_number).bind(supplier_id).bind(&supplier_name)
                    .bind(&li_json).bind(total).bind(&currency).bind(expected_delivery).bind(created_by).bind(now)
                    .bind(receiving_site_id)
                    .fetch_one(&mut **tx).await.map_err(|e| SenseiError::Database(format!("Failed to create PO: {e}")))?;
                Ok(po_row_to_domain(row))
            })
        })
        .await
    }

    async fn get_purchase_order(&self, tenant_id: Uuid, id: Uuid) -> Result<PurchaseOrder> {
        let row = sqlx::query_as::<_, PurchaseOrderRow>(
            "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders WHERE id=$1 AND tenant_id=$2",
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get PO: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;
        Ok(po_row_to_domain(row))
    }

    async fn list_purchase_orders(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PurchaseOrder>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let items: Vec<PurchaseOrderRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders
               WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(status).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list POs: {e}")))?;
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM purchase_orders WHERE tenant_id=$1 AND ($2::text IS NULL OR status=$2)")
            .bind(tenant_id).bind(status).fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to count POs: {e}")))?;
        Ok(paginate(
            items.into_iter().map(po_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn receive_po_line(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        po_id: Uuid,
        product_id: Uuid,
        quantity_received: i64,
    ) -> Result<PurchaseOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        if quantity_received <= 0 {
            return Err(SenseiError::Validation(
                "Received quantity must be positive".to_string(),
            ));
        }
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                // Load the PO's JSONB line items and supplier, then update
                // them. Twenty-third audit P0: the scope boundary is part
                // of the guard read — a PO whose receiving site is NULL or
                // outside `authorized_sites` is indistinguishable from a
                // nonexistent PO, so no line update, stock movement or
                // inventory effect can happen for it.
                let row: PurchaseOrderRow = sqlx::query_as(
                    r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status,
                              line_items, total_amount, currency, expected_delivery, created_by, created_at,
                              receiving_site_id
                       FROM purchase_orders WHERE id=$1 AND tenant_id=$2
                         AND receiving_site_id = ANY($3) FOR UPDATE"#,
                )
                .bind(po_id)
                .bind(tenant_id)
                .bind(&sites)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to get PO: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?;

                // Twenty-fourth audit P0: the receipt's inventory effects
                // are attributed to the PO's OWN receiving site — never to
                // a tenant-global stock row. A site-less PO is refuseable
                // here even though the guard already proved the site is
                // inside the caller's entitlement.
                let site_id = row.receiving_site_id.ok_or_else(|| {
                    SenseiError::Validation(format!(
                        "Purchase order {po_id} names no receiving site — \
                         the receipt cannot be attributed to a site"
                    ))
                })?;

                let mut items: Vec<POItem> = serde_json::from_value(row.line_items).map_err(
                    |e| {
                        tracing::error!(po_id = %po_id, "Failed to deserialize PO line items: {e}");
                        SenseiError::Database(format!(
                            "Purchase order {po_id} has corrupt line items: {e}"
                        ))
                    },
                )?;

                let mut found = false;
                for item in &mut items {
                    if item.product_id == product_id {
                        let remaining = item.quantity_ordered - item.quantity_received;
                        if quantity_received > remaining {
                            return Err(SenseiError::Validation(format!(
                                "Receiving {quantity_received} units of product {product_id} \
                                 exceeds the remaining {remaining} units on PO {po_id}"
                            )));
                        }
                        item.quantity_received += quantity_received;
                        found = true;
                        break;
                    }
                }
                if !found {
                    return Err(SenseiError::NotFound(format!(
                        "Product {product_id} not found in purchase order {po_id}"
                    )));
                }
                let all_received = items
                    .iter()
                    .all(|i| i.quantity_received >= i.quantity_ordered);
                let new_status = if all_received {
                    "received"
                } else {
                    "partially_received"
                };
                let li_json = serde_json::to_value(&items).map_err(|e| {
                    SenseiError::Database(format!("Failed to serialize PO line items: {e}"))
                })?;

                // Effects apply only to the scoped row: the same site
                // boundary is repeated in the state UPDATE.
                sqlx::query("UPDATE purchase_orders SET line_items=$1, status=$2, updated_at=NOW() WHERE id=$3 AND tenant_id=$4 AND receiving_site_id = ANY($5)")
                    .bind(&li_json).bind(new_status).bind(po_id).bind(tenant_id).bind(&sites)
                    .execute(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to receive PO line: {e}")))?;

                // Update inventory at the product's first known location AT
                // THE PO'S SITE; a receipt with no site-A row CREATES the
                // row stamped with the PO's site.
                let location = resolve_stock_location(
&mut *tx, tenant_id, site_id, product_id)
                    .await?;
                apply_inventory_delta(
                    &mut *tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    quantity_received,
                )
                .await?;

                // Record the stock move (site-stamped) and goods receipt
                // inside the same transaction.
                sqlx::query(
                    "INSERT INTO stock_moves (id, tenant_id, site_id, product_id, from_location, to_location, quantity, move_type, reference_type, reference_id, moved_at, created_at) \
                     VALUES ($1,$2,$3,$4,NULL,$5,$6,'receipt','purchase_order',$7,NOW(),NOW())",
                )
                .bind(Uuid::new_v4()).bind(tenant_id).bind(site_id).bind(product_id).bind(&location)
                .bind(quantity_received).bind(po_id)
                .execute(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to record stock move: {e}")))?;

                // The goods receipt status describes THIS receipt, not the
                // PO: a partial line receipt is never 'fully_received'.
                let receipt_status = if all_received {
                    "fully_received"
                } else {
                    "partially_received"
                };
                sqlx::query(
                    "INSERT INTO goods_receipts (id, tenant_id, receipt_number, purchase_order_id, supplier_id, status, receipt_date, created_at, updated_at) \
                     VALUES ($1,$2,$3,$4,$5,$6,NOW(),NOW(),NOW())",
                )
                .bind(Uuid::new_v4()).bind(tenant_id)
                .bind(format!("GR-{}-{}", Utc::now().format("%Y%m%d"), Uuid::new_v4().as_simple()))
                .bind(po_id).bind(row.supplier_id).bind(receipt_status)
                .execute(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to record goods receipt: {e}")))?;

                let updated: PurchaseOrderRow = sqlx::query_as(
                    r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status,
                              line_items, total_amount, currency, expected_delivery, created_by, created_at,
                              receiving_site_id
                       FROM purchase_orders WHERE id=$1 AND tenant_id=$2"#,
                )
                .bind(po_id)
                .bind(tenant_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to reload PO: {e}")))?;

                Ok(po_row_to_domain(updated))
            })
        })
        .await
    }

    // ── Inventory ───────────────────────────────────────────────────────

    async fn get_inventory(&self, tenant_id: Uuid, product_id: Uuid) -> Result<Vec<InventoryItem>> {
        let rows = sqlx::query_as::<_, InventoryRow>(
            "SELECT id, tenant_id, product_id, \
                    (SELECT name FROM products WHERE products.id = inventory_items.product_id) \
                        AS product_name, \
                    COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point, \
                    0::bigint AS reorder_quantity, \
                    quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint, \
                    location, lot_number, updated_at \
             FROM inventory_items WHERE product_id=$1 AND tenant_id=$2",
        ).bind(product_id).bind(tenant_id).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get inventory: {e}")))?;
        Ok(rows.into_iter().map(inv_row_to_domain).collect())
    }

    async fn list_inventory(
        &self,
        tenant_id: Uuid,
        location: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<InventoryItem>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        let items: Vec<InventoryRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, product_id,
                      (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                          AS product_name,
                      COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                      0::bigint AS reorder_quantity,
                      quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                      location, lot_number, updated_at
               FROM inventory_items
               WHERE tenant_id=$1 AND ($2::text IS NULL OR location=$2) ORDER BY product_name LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(location).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list inventory: {e}")))?;
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM inventory_items WHERE tenant_id=$1 AND ($2::text IS NULL OR location=$2)")
            .bind(tenant_id).bind(location).fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to count inventory: {e}")))?;
        Ok(paginate(
            items.into_iter().map(inv_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn adjust_inventory(
        &self,
        tenant_id: Uuid,
        product_id: Uuid,
        location: &str,
        quantity_change: i64,
        reason: &str,
    ) -> Result<InventoryItem> {
        // An adjustment without a reason is not an inventory transaction.
        if reason.trim().is_empty() {
            return Err(SenseiError::Validation(
                "An inventory adjustment requires a reason".to_string(),
            ));
        }
        // Adjusting stock at a location that has no row is an error — never
        // auto-create an inventory row for an arbitrary location name.
        // Twenty-fourth audit P0: an adjustment targets ONE site's row.
        // The site is derived from the rows at (tenant, product, location)
        // — when more than one site owns a row there (same location name at
        // two sites), the adjustment cannot be attributed and is REFUSED
        // instead of mutating tenant-globally.
        let mut tx =
            self.pool.begin().await.map_err(|e| {
                SenseiError::Database(format!("Failed to begin adjustment tx: {e}"))
            })?;

        let sites: Vec<Uuid> = sqlx::query_scalar(
            "SELECT DISTINCT site_id FROM inventory_items \
             WHERE tenant_id=$1 AND product_id=$2 AND location=$3 AND site_id IS NOT NULL",
        )
        .bind(tenant_id)
        .bind(product_id)
        .bind(location)
        .fetch_all(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to resolve adjustment site: {e}")))?;
        let site_id = match sites.as_slice() {
            [] => {
                return Err(if quantity_change < 0 {
                    SenseiError::Validation(format!(
                        "Insufficient stock at '{location}' for product {product_id}: \
                         {quantity_change} would drive the balance negative"
                    ))
                } else {
                    SenseiError::NotFound(format!(
                        "Inventory for product {product_id} at {location} not found"
                    ))
                });
            }
            [site] => *site,
            _ => {
                return Err(SenseiError::Validation(format!(
                    "Inventory at '{location}' for product {product_id} is owned by \
                     multiple sites — an unscoped adjustment cannot be attributed \
                     to one site's balance"
                )));
            }
        };

        let row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items
               SET quantity_on_hand = quantity_on_hand + $1::double precision,
                   quantity_available = quantity_on_hand + $1::double precision - quantity_reserved
               WHERE product_id=$2 AND tenant_id=$3 AND site_id=$4 AND location=$5
                 AND quantity_on_hand + $1::double precision >= 0
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(quantity_change).bind(product_id).bind(tenant_id).bind(site_id).bind(location)
            .fetch_optional(&mut *tx).await
            .map_err(|e| SenseiError::Database(format!("Failed to adjust inventory: {e}")))?
            .ok_or_else(|| {
                if quantity_change < 0 {
                    SenseiError::Validation(format!(
                        "Insufficient stock at '{location}' for product {product_id}: \
                         {quantity_change} would drive the balance negative"
                    ))
                } else {
                    SenseiError::NotFound(format!(
                        "Inventory for product {product_id} at {location} not found"
                    ))
                }
            })?;

        // The ledger row: inventory never changes without a corresponding
        // stock transaction. The real stock_moves schema has no
        // product_name/created_by columns — the move records the id,
        // quantity and locations (product_name is read from products).
        sqlx::query(
            "INSERT INTO stock_moves \
                (id, tenant_id, site_id, product_id, quantity, move_type, \
                 from_location, to_location, reference_type, reference_id, moved_at, created_at) \
             VALUES ($1, $2, $3, $4, $5, 'adjustment', $6, $7, 'inventory_adjustment', NULL, NOW(), NOW())",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(site_id)
        .bind(product_id)
        .bind(quantity_change.abs())
        .bind(location)
        .bind(location)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record adjustment ledger: {e}")))?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit adjustment tx: {e}")))?;
        Ok(inv_row_to_domain(row))
    }

    // ── Stock Movements ─────────────────────────────────────────────────

    async fn create_stock_move(&self, tenant_id: Uuid, stock_move: StockMove) -> Result<StockMove> {
        let now = Utc::now();
        let id = Uuid::new_v4();

        // Validation BEFORE any write: a negative quantity inverts the
        // movement semantics, an unknown move type would leave the ledger
        // and the balance disagreeing, and a transfer without a source
        // would create stock out of nothing.
        if stock_move.quantity <= 0 {
            return Err(SenseiError::Validation(
                "Stock move quantity must be positive".to_string(),
            ));
        }
        match stock_move.move_type.as_str() {
            "receipt" | "delivery" | "issue" | "transfer" | "adjustment" => {}
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unknown stock move type '{other}'"
                )));
            }
        }
        if stock_move.move_type == "transfer"
            && (stock_move
                .from_location
                .as_deref()
                .is_none_or(|l| l.is_empty())
                || stock_move.to_location.is_empty())
        {
            return Err(SenseiError::Validation(
                "A transfer requires both a source and a destination location".to_string(),
            ));
        }

        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;
        set_tenant_context(&mut tx, tenant_id).await?;

        let product_id = stock_move.product_id;
        let from_location = stock_move.from_location.as_deref().map(str::to_string);
        let to_location = stock_move.to_location.clone();

        // Twenty-fourth audit P0: the move is stamped with the site of the
        // inventory row it derives its effect from. This unscoped path has
        // no caller entitlement, so the site is whatever SINGLE site owns
        // the anchor row — a row owned by several sites (or no site) is
        // unresolvable and the move is REFUSED (never a tenant-global
        // effect). Scoped callers use [`create_stock_move_scoped`].
        // Fails closed: the move's site must be resolvable before ANY write.
        let (location, site_id) = match stock_move.move_type.as_str() {
            "receipt" | "delivery" | "issue" | "adjustment" => {
                let location = match stock_move.move_type.as_str() {
                    "receipt" => match to_location.as_str() {
                        "" => fallback_product_location(&mut tx, tenant_id, product_id).await?,
                        l => l.to_string(),
                    },
                    "delivery" | "issue" => match from_location.as_ref() {
                        Some(l) if !l.is_empty() => l.clone(),
                        _ => fallback_product_location(&mut tx, tenant_id, product_id).await?,
                    },
                    // adjustment
                    _ => match from_location.as_ref() {
                        Some(l) if !l.is_empty() => l.clone(),
                        _ => to_location.clone(),
                    },
                };
                let site = resolve_single_site(&mut tx, tenant_id, product_id, &location, None)
                    .await?
                    .ok_or_else(|| {
                        SenseiError::Validation(format!(
                            "No site-attributable inventory row exists for product \
                                 {product_id} at '{location}' — the move cannot be \
                                 recorded without a site"
                        ))
                    })?;
                (location, site)
            }
            "transfer" => {
                let from = from_location.clone().unwrap_or_default();
                let source_site = resolve_single_site(&mut tx, tenant_id, product_id, &from, None)
                    .await?
                    .ok_or_else(|| {
                        SenseiError::Validation(format!(
                            "No site-attributable inventory row exists for product \
                                 {product_id} at source '{from}' — the transfer cannot be \
                                 recorded without a site"
                        ))
                    })?;
                let to = match to_location.as_str() {
                    "" => fallback_product_location(&mut tx, tenant_id, product_id).await?,
                    l => l.to_string(),
                };
                let dest_site =
                    resolve_single_site(&mut tx, tenant_id, product_id, &to, None).await?;
                if let Some(dest_site) = dest_site {
                    if dest_site != source_site {
                        return Err(SenseiError::Validation(format!(
                            "Transfer source '{from}' and destination '{to}' are stocked \
                             at DIFFERENT sites — one move cannot span sites; issue at \
                             the source site and receipt at the destination site instead"
                        )));
                    }
                }
                (from, source_site)
            }
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unsupported stock move type '{other}'"
                )));
            }
        };

        // The real stock_moves schema stores no product_name (it is read
        // from products) and its move_type CHECK admits receipt/issue/
        // transfer/adjustment — a 'delivery' is stored as its schema
        // equivalent 'issue' (identical semantics in the branch below).
        let stored_move_type: &str = if stock_move.move_type == "delivery" {
            "issue"
        } else {
            &stock_move.move_type
        };
        let row = sqlx::query_as::<_, StockMoveRow>(
            r#"INSERT INTO stock_moves (id, tenant_id, site_id, product_id, quantity, move_type, from_location, to_location, reference_type, reference_id, moved_by, moved_at, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                         quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                         moved_by AS created_by, created_at, site_id, status, reversed_by, reversed_at, reversal_reason, reversal_of, reversed_by_move"#,
        ).bind(id).bind(tenant_id).bind(site_id).bind(product_id)
            .bind(stock_move.quantity).bind(stored_move_type).bind(&stock_move.from_location)
            .bind(&stock_move.to_location).bind(&stock_move.reference_type).bind(stock_move.reference_id)
            .bind(stock_move.created_by).bind(now).bind(now)
            .fetch_one(&mut *tx).await.map_err(|e| SenseiError::Database(format!("Failed to create stock move: {e}")))?;

        // Apply the inventory effect inside the same transaction, honouring
        // the move semantics: receipts credit the destination, issues/debits
        // the source, transfers move between both, adjustments apply to the
        // named location — ALWAYS on the resolved site's row.
        match stock_move.move_type.as_str() {
            "receipt" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            "delivery" | "issue" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
            }
            "transfer" => {
                // Hard rule (item 126): an inventory transfer must balance
                // (Σ location deltas = 0). The rule is the gate.
                crate::tps::rules::check_transfer_balance(&[
                    (product_id, -stock_move.quantity),
                    (product_id, stock_move.quantity),
                ])
                .map_err(|v| SenseiError::Validation(v.message().to_string()))?;
                let to = match to_location.as_str() {
                    "" => location.clone(),
                    l => l.to_string(),
                };
                // Source is validated present; debit it strictly.
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &to,
                    stock_move.quantity,
                )
                .await?;
            }
            "adjustment" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            // Unreachable: move types are validated before the insert. Kept
            // as a hard error so the ledger can never silently diverge.
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unsupported stock move type '{other}'"
                )));
            }
        }

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit stock move: {e}")))?;

        Ok(sm_row_to_domain(row))
    }

    async fn list_stock_moves(
        &self,
        tenant_id: Uuid,
        product_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<StockMove>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;
        // stock_moves is FORCE-RLS (migration 160) — tenant context is
        // required even for the unscoped legacy list (twenty-fourth
        // audit P0: RLS rows are invisible without app.tenant_id).
        let (items, count): (Vec<StockMoveRow>, i64) = with_tenant_tx(&self.pool, tenant_id, |tx| {
            Box::pin(async move {
                let items: Vec<StockMoveRow> = sqlx::query_as(
                    r#"SELECT id, tenant_id, product_id,
                              (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                              quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                              moved_by AS created_by, created_at,
                              site_id, status, reversed_by, reversed_at, reversal_reason, reversal_of, reversed_by_move
                       FROM stock_moves
                       WHERE tenant_id=$1 AND ($2::uuid IS NULL OR product_id=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
                ).bind(tenant_id).bind(product_id).bind(per_page as i64).bind(offset as i64).fetch_all(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to list stock moves: {e}")))?;
                let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM stock_moves WHERE tenant_id=$1 AND ($2::uuid IS NULL OR product_id=$2)")
                    .bind(tenant_id).bind(product_id).fetch_one(&mut **tx).await.map_err(|e| SenseiError::Database(format!("Failed to count stock moves: {e}")))?;
                Ok((items, count))
            })
        }).await?;
        Ok(paginate(
            items.into_iter().map(sm_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    /// Scoped listing (twenty-fourth audit P0): only moves whose site is
    /// among `authorized_sites` are returned (a foreign or site-less move
    /// never surfaces); an EMPTY entitlement matches nothing.
    async fn list_stock_moves_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        product_id: Option<Uuid>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<StockMove>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        if authorized_sites.is_empty() {
            return Ok(paginate(Vec::new(), 0, page, per_page));
        }
        let offset = (page - 1) * per_page;
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                let items: Vec<StockMoveRow> = sqlx::query_as(
                    r#"SELECT id, tenant_id, product_id,
                              (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                              quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                              moved_by AS created_by, created_at,
                              site_id, status, reversed_by, reversed_at, reversal_reason, reversal_of, reversed_by_move
                       FROM stock_moves
                       WHERE tenant_id=$1 AND site_id = ANY($2)
                         AND ($3::uuid IS NULL OR product_id=$3)
                       ORDER BY created_at DESC LIMIT $4 OFFSET $5"#,
                ).bind(tenant_id).bind(&sites).bind(product_id).bind(per_page as i64).bind(offset as i64)
                    .fetch_all(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to list scoped stock moves: {e}")))?;
                let count: i64 = sqlx::query_scalar(
                    "SELECT COUNT(*) FROM stock_moves WHERE tenant_id=$1 AND site_id = ANY($2) AND ($3::uuid IS NULL OR product_id=$3)",
                )
                .bind(tenant_id).bind(&sites).bind(product_id).fetch_one(&mut **tx).await
                .map_err(|e| SenseiError::Database(format!("Failed to count scoped stock moves: {e}")))?;
                Ok(paginate(
                    items.into_iter().map(sm_row_to_domain).collect(),
                    count,
                    page,
                    per_page,
                ))
            })
        })
        .await
    }

    // ── RFQ Mutations ──────────────────────────────────────────────────

    async fn update_rfq(&self, tenant_id: Uuid, id: Uuid, rfq: RFQ) -> Result<RFQ> {
        let items_json =
            serde_json::to_value(&rfq.items).unwrap_or(serde_json::Value::Array(vec![]));
        let row = sqlx::query_as::<_, RfqRow>(
            r#"UPDATE rfqs SET supplier_id=$1, supplier_name=$2, items=$3, notes=$4 WHERE id=$5 AND tenant_id=$6
               RETURNING id, tenant_id, rfq_number, supplier_id, supplier_name, status, items, notes, created_by, created_at"#,
        ).bind(rfq.supplier_id).bind(&rfq.supplier_name).bind(&items_json).bind(&rfq.notes).bind(id).bind(tenant_id)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update RFQ: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("RFQ {id} not found")))?;
        Ok(rfq_row_to_domain(row))
    }

    async fn delete_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        // RFQs are business history: they are CANCELLED, never erased.
        let r = sqlx::query("UPDATE rfqs SET status='cancelled' WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to cancel RFQ: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("RFQ {id} not found")));
        }
        Ok(())
    }

    async fn submit_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        self.update_rfq_status(tenant_id, id, "sent").await
    }
    async fn cancel_rfq(&self, tenant_id: Uuid, id: Uuid) -> Result<RFQ> {
        self.update_rfq_status(tenant_id, id, "cancelled").await
    }

    // ── Quote Mutations ─────────────────────────────────────────────────

    async fn update_quote(&self, tenant_id: Uuid, id: Uuid, quote: Quote) -> Result<Quote> {
        let li_json =
            serde_json::to_value(&quote.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = quote.line_items.iter().map(|li| li.net_price).sum();
        let row = sqlx::query_as::<_, QuoteRow>(
            r#"UPDATE quotes SET customer_id=$1, customer_name=$2, line_items=$3, total_amount=$4, currency=$5, valid_until=$6 WHERE id=$7 AND tenant_id=$8
               RETURNING id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at"#,
        ).bind(quote.customer_id).bind(&quote.customer_name).bind(&li_json).bind(total).bind(&quote.currency).bind(quote.valid_until).bind(id).bind(tenant_id)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update quote: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(quote_row_to_domain(row))
    }

    async fn delete_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        // Quotes are business history: they are CANCELLED, never erased.
        let r = sqlx::query("UPDATE quotes SET status='cancelled' WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to cancel quote: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Quote {id} not found")));
        }
        Ok(())
    }

    async fn submit_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let row = sqlx::query_as::<_, QuoteRow>(
            r#"UPDATE quotes SET status='submitted' WHERE id=$1 AND tenant_id=$2
               RETURNING id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at"#,
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to submit quote: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(quote_row_to_domain(row))
    }

    async fn accept_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        self.approve_quote(tenant_id, id).await
    }
    async fn reject_quote(&self, tenant_id: Uuid, id: Uuid) -> Result<Quote> {
        let row = sqlx::query_as::<_, QuoteRow>(
            r#"UPDATE quotes SET status='rejected' WHERE id=$1 AND tenant_id=$2
               RETURNING id, tenant_id, quote_number, rfq_id, customer_id, customer_name, status, line_items, total_amount, currency, valid_until, created_by, created_at"#,
        ).bind(id).bind(tenant_id).fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to reject quote: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Quote {id} not found")))?;
        Ok(quote_row_to_domain(row))
    }

    // ── Sales Order Mutations ───────────────────────────────────────────

    async fn update_sales_order(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
        order: SalesOrder,
    ) -> Result<SalesOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no sales order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        let li_json =
            serde_json::to_value(&order.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = order
            .line_items
            .iter()
            .map(|li| rust_decimal::Decimal::from(li.quantity) * li.unit_price)
            .sum();
        let row = sqlx::query_as::<_, SalesOrderRow>(
            r#"UPDATE sales_orders SET customer_id=$1, customer_name=$2, line_items=$3, total_amount=$4, currency=$5, delivery_date=$6, shipping_address=$7 WHERE id=$8 AND tenant_id=$9 AND fulfilling_site_id = ANY($10)
               RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#,
        ).bind(order.customer_id).bind(&order.customer_name).bind(&li_json).bind(total).bind(&order.currency).bind(order.delivery_date).bind(&order.shipping_address).bind(id).bind(tenant_id).bind(&sites)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update sales order: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
        Ok(so_row_to_domain(row))
    }

    async fn delete_sales_order(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<()> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no sales order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        let r = sqlx::query("DELETE FROM sales_orders WHERE id=$1 AND tenant_id=$2 AND fulfilling_site_id = ANY($3)")
            .bind(id)
            .bind(tenant_id)
            .bind(&sites)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete sales order: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Sales order {id} not found")));
        }
        Ok(())
    }

    // ── Purchase Order Mutations ────────────────────────────────────────

    async fn update_purchase_order(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
        po: PurchaseOrder,
    ) -> Result<PurchaseOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        let li_json =
            serde_json::to_value(&po.line_items).unwrap_or(serde_json::Value::Array(vec![]));
        let total: rust_decimal::Decimal = po
            .line_items
            .iter()
            .map(|li| rust_decimal::Decimal::from(li.quantity_ordered) * li.unit_price)
            .sum();
        let row = sqlx::query_as::<_, PurchaseOrderRow>(
            r#"UPDATE purchase_orders SET supplier_id=$1, supplier_name=$2, line_items=$3, total_amount=$4, currency=$5, expected_delivery=$6 WHERE id=$7 AND tenant_id=$8 AND receiving_site_id = ANY($9)
               RETURNING id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id"#,
        ).bind(po.supplier_id).bind(&po.supplier_name).bind(&li_json).bind(total).bind(&po.currency).bind(po.expected_delivery).bind(id).bind(tenant_id).bind(&sites)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update PO: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;
        Ok(po_row_to_domain(row))
    }

    async fn delete_purchase_order(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<()> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        let r = sqlx::query("DELETE FROM purchase_orders WHERE id=$1 AND tenant_id=$2 AND receiving_site_id = ANY($3)")
            .bind(id)
            .bind(tenant_id)
            .bind(&sites)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete PO: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!(
                "Purchase order {id} not found"
            )));
        }
        Ok(())
    }

    async fn receive_full_po(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<PurchaseOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                // Twenty-third audit P0: the scope boundary is part of the
                // guard read — a PO whose receiving site is NULL or outside
                // `authorized_sites` is indistinguishable from a nonexistent
                // PO, so the full receipt is rejected BEFORE any line
                // update, stock movement or inventory effect happens.
                let row: PurchaseOrderRow = sqlx::query_as(
                    r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status,
                              line_items, total_amount, currency, expected_delivery, created_by, created_at,
                              receiving_site_id
                       FROM purchase_orders WHERE id=$1 AND tenant_id=$2
                         AND receiving_site_id = ANY($3) FOR UPDATE"#,
                )
                .bind(id)
                .bind(tenant_id)
                .bind(&sites)
                .fetch_optional(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to get PO: {e}")))?
                .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;

                // Twenty-fourth audit P0: every inventory effect below is
                // attributed to the PO's OWN receiving site.
                let site_id = row.receiving_site_id.ok_or_else(|| {
                    SenseiError::Validation(format!(
                        "Purchase order {id} names no receiving site — \
                         the receipt cannot be attributed to a site"
                    ))
                })?;

                if row.status == "received" || row.status == "cancelled" {
                    return Err(SenseiError::Validation(format!(
                        "Cannot receive PO with status: {}",
                        row.status
                    )));
                }

                let mut items: Vec<POItem> = serde_json::from_value(row.line_items).map_err(
                    |e| {
                        tracing::error!(po_id = %id, "Failed to deserialize PO line items: {e}");
                        SenseiError::Database(format!(
                            "Purchase order {id} has corrupt line items: {e}"
                        ))
                    },
                )?;

                // Capture the remaining quantity per line BEFORE marking
                // them received.
                let mut remaining: Vec<(Uuid, String, i64)> = Vec::new();
                for item in &mut items {
                    let to_receive = item.quantity_ordered - item.quantity_received;
                    if to_receive > 0 {
                        remaining.push((item.product_id, item.product_name.clone(), to_receive));
                        item.quantity_received += to_receive;
                    }
                }

                let li_json = serde_json::to_value(&items).map_err(|e| {
                    SenseiError::Database(format!("Failed to serialize PO line items: {e}"))
                })?;
                // Effects apply only to the scoped row: the same site
                // boundary is repeated in the state UPDATE.
                sqlx::query("UPDATE purchase_orders SET line_items=$1, status='received', updated_at=NOW() WHERE id=$2 AND tenant_id=$3 AND receiving_site_id = ANY($4)")
                    .bind(&li_json).bind(id).bind(tenant_id).bind(&sites)
                    .execute(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to receive full PO: {e}")))?;

                // Update inventory at each line's first known location AT
                // THE PO'S SITE; lines with no site row create one stamped
                // with the PO's site.
                for (product_id, _product_name, qty) in &remaining {
                    let location = resolve_stock_location(
&mut *tx, tenant_id, site_id, *product_id)
                        .await?;
                    apply_inventory_delta(
                        &mut *tx,
                        tenant_id,
                        site_id,
                        *product_id,
                        &location,
                        *qty,
                    )
                    .await?;
                    sqlx::query(
                        "INSERT INTO stock_moves (id, tenant_id, site_id, product_id, from_location, to_location, quantity, move_type, reference_type, reference_id, moved_at, created_at) \
                         VALUES ($1,$2,$3,$4,NULL,$5,$6,'receipt','purchase_order',$7,NOW(),NOW())",
                    )
                    .bind(Uuid::new_v4()).bind(tenant_id).bind(site_id).bind(product_id).bind(&location)
                    .bind(qty).bind(id)
                    .execute(&mut **tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to record stock move: {e}")))?;
                }

                let updated: PurchaseOrderRow = sqlx::query_as(
                    r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status,
                              line_items, total_amount, currency, expected_delivery, created_by, created_at,
                              receiving_site_id
                       FROM purchase_orders WHERE id=$1 AND tenant_id=$2"#,
                )
                .bind(id)
                .bind(tenant_id)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to reload PO: {e}")))?;

                // Item 28: the receipt (state mutation + inventory +
                // ledger) and its integration-driving event are ONE
                // transaction.
                sensei_db::outbox::enqueue_outbox(
                    tx,
                    tenant_id,
                    "purchase_order",
                    id,
                    "sensei.supply-chain.po.received",
                    serde_json::json!({
                        "po_number": updated.po_number,
                        "supplier_id": updated.supplier_id,
                        "received_lines": remaining.iter().map(|(pid, name, qty)| {
                            serde_json::json!({ "product_id": pid, "product_name": name, "quantity": qty })
                        }).collect::<Vec<_>>(),
                    }),
                )
                .await?;

                Ok(po_row_to_domain(updated))
            })
        })
        .await
    }

    async fn assign_receiving_site(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        po_id: Uuid,
        site_id: Uuid,
    ) -> Result<PurchaseOrder> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no purchase order is authorized".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        // The receiving site is IMMUTABLE once set (PurchaseOrder doc):
        // re-anchoring to a DIFFERENT site is refused, re-assigning the
        // SAME site is a no-op, and only a NULL anchor is filled.
        // Twenty-third audit P0: the caller's site boundary is embedded
        // in the same predicate as the write — a NULL anchor may only be
        // filled with a site inside `authorized_sites`, and a PO already
        // anchored OUTSIDE the caller's scope is indistinguishable from a
        // nonexistent PO.
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;
        // Read the row's site INSIDE the tx under FOR UPDATE; the read is
        // itself scoped so a foreign anchor never even surfaces.
        let existing: Option<Option<Uuid>> = sqlx::query_scalar(
            "SELECT receiving_site_id FROM purchase_orders \
             WHERE id = $1 AND tenant_id = $2 \
               AND (receiving_site_id IS NULL OR receiving_site_id = ANY($3)) \
             FOR UPDATE",
        )
        .bind(po_id)
        .bind(tenant_id)
        .bind(&sites)
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to read PO receiving site: {e}")))?;
        match existing {
            None => Err(SenseiError::NotFound(format!(
                "Purchase order {po_id} not found"
            ))),
            Some(Some(existing_site)) => {
                if existing_site != site_id {
                    return Err(SenseiError::Validation(format!(
                        "purchase order {po_id} already names receiving site {existing_site} — \
                         the receiving site is immutable"
                    )));
                }
                // Same-site no-op: return the locked row.
                let row = sqlx::query_as::<_, PurchaseOrderRow>(
                    "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders WHERE id=$1 AND tenant_id=$2",
                ).bind(po_id).bind(tenant_id).fetch_one(&mut *tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to reload PO: {e}")))?;
                tx.commit()
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
                Ok(po_row_to_domain(row))
            }
            Some(None) => {
                // NULL anchor: fill it with the requested site ONLY when
                // that site is inside the caller's entitlement — the
                // boundary is in the same predicate as the UPDATE.
                let row = sqlx::query_as::<_, PurchaseOrderRow>(
                    r#"UPDATE purchase_orders SET receiving_site_id=$3
                       WHERE id=$1 AND tenant_id=$2 AND receiving_site_id IS NULL
                         AND $3::uuid = ANY($4)
                       RETURNING id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id"#,
                ).bind(po_id).bind(tenant_id).bind(site_id).bind(&sites)
                    .fetch_optional(&mut *tx).await
                    .map_err(|e| SenseiError::Database(format!("Failed to assign receiving site: {e}")))?
                    .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?;
                tx.commit()
                    .await
                    .map_err(|e| SenseiError::Database(format!("Failed to commit tx: {e}")))?;
                Ok(po_row_to_domain(row))
            }
        }
    }

    // ── Inventory Mutations ─────────────────────────────────────────────

    async fn update_inventory(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        _item: InventoryItem,
    ) -> Result<InventoryItem> {
        // The real `inventory_items` row has no writable attributes
        // beyond the quantities (adjust) and its location — the domain's
        // reorder fields live on `products`, which is NOT rewritten from
        // an inventory update. The update is therefore a scope-checked
        // touch: it proves the row exists (NotFound otherwise) and
        // returns the truthful projection.
        let row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items SET updated_at = NOW()
               WHERE id=$1 AND tenant_id=$2
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(id).bind(tenant_id)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update inventory: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Inventory item {id} not found")))?;
        Ok(inv_row_to_domain(row))
    }

    async fn delete_inventory(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM inventory_items WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete inventory: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!(
                "Inventory item {id} not found"
            )));
        }
        Ok(())
    }

    // ── Stock Move Mutations ────────────────────────────────────────────

    /// Reverse a stock movement (twenty-fourth audit P0; twenty-fifth
    /// audit P1 compensating reversal): a stock move is a LEDGER row —
    /// never erased. The reversal is ONE transaction that:
    ///
    ///   1. loads the original move scoped — its site must be inside
    ///      `authorized_sites` and it must still be 'posted' (a foreign,
    ///      site-less or already-reversed move is indistinguishable from
    ///      a nonexistent one: NotFound, and nothing changes);
    ///   2. posts a NEW compensating move of the OPPOSITE direction at
    ///      the SAME site (receipt → issue, issue → receipt, transfer
    ///      with source/destination swapped, adjustment → issue), with
    ///      `reversal_of` = original id and the reversal's actor/
    ///      timestamp/reason stamped on the compensating row, and marks
    ///      the ORIGINAL row 'reversed' with the same stamps plus
    ///      `reversed_by_move` = the compensating id;
    ///   3. applies the INVERSE inventory delta to the same
    ///      site/product/location/lot so the balance returns — a
    ///      receipt of +10 reversed is a compensating −10 at its own
    ///      location. If the inverse physical move is impossible
    ///      (insufficient stock at that row), the reversal FAILS with a
    ///      Validation error naming the controlled discrepancy — the
    ///      ledger and the balance are never allowed to diverge
    ///      silently.
    async fn reverse_stock_move(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        move_id: Uuid,
        actor: Uuid,
        reason: &str,
    ) -> Result<()> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::Forbidden(
                "no operational scope — no stock move is authorized".to_string(),
            ));
        }
        if reason.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A stock move reversal requires a reason".to_string(),
            ));
        }
        let sites = authorized_sites.to_vec();
        let reason_owned = reason.trim().to_string();
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                // (1) The scoped guard read: the original move must be
                // posted and inside the caller's site entitlement.
                let original: Option<(Uuid, Uuid, Option<String>, String, i64, String, Option<String>)> =
                    sqlx::query_as(
                        "SELECT site_id, product_id, from_location, to_location, quantity::bigint, \
                                move_type, lot_number \
                         FROM stock_moves \
                         WHERE id = $1 AND tenant_id = $2 AND site_id = ANY($3) \
                           AND status = 'posted' \
                         FOR UPDATE",
                    )
                    .bind(move_id)
                    .bind(tenant_id)
                    .bind(&sites)
                    .fetch_optional(&mut **tx)
                    .await
                    .map_err(|e| {
                        SenseiError::Database(format!("Failed to load stock move for reversal: {e}"))
                    })?;
                let (site_id, product_id, from_location, to_location, quantity, move_type, lot_number) =
                    original.ok_or_else(|| {
                        SenseiError::NotFound(format!("Stock move {move_id} not found"))
                    })?;
                // The compensating delta returns the balance at the same
                // site/product/location/lot — a lot-bearing original is
                // required to still be resolvable, never silently dropped.
                let (delta_location, delta_lot) = (to_location.clone(), lot_number.clone());
                if lot_number.as_deref().is_some_and(|l| l.trim().is_empty()) {
                    return Err(SenseiError::Validation(format!(
                        "Stock move {move_id} carries a blank lot number — \
                         the reversal cannot be attributed to a lot row"
                    )));
                }

                // (2) The compensating move: the OPPOSITE direction of the
                // schema move types (the stock_moves CHECK admits
                // receipt/issue/transfer/adjustment — 'delivery' rows are
                // stored as 'issue'). A transfer compensation swaps its
                // source and destination; a receipt compensates as an
                // issue out of the location it filled (and vice versa);
                // an adjustment (which deposited at its location)
                // compensates as an issue from that location.
                let (comp_type, comp_from, comp_to): (String, Option<String>, String) =
                    match move_type.as_str() {
                        "receipt" => ("issue".to_string(), Some(to_location.clone()), String::new()),
                        "issue" => (
                            "receipt".to_string(),
                            None,
                            from_location.clone().unwrap_or_else(|| to_location.clone()),
                        ),
                        "transfer" => {
                            let source = from_location.clone().ok_or_else(|| {
                                SenseiError::Validation(format!(
                                    "Stock move {move_id} is a transfer without a source \
                                     location — its reversal cannot be compensated"
                                ))
                            })?;
                            (
                                "transfer".to_string(),
                                Some(to_location.clone()),
                                source,
                            )
                        }
                        // 'adjustment' and any unmapped type: withdraw what
                        // the original deposited at its location.
                        _ => ("issue".to_string(), Some(to_location.clone()), String::new()),
                    };
                let comp_id = Uuid::new_v4();
                let now = chrono::Utc::now();
                sqlx::query(
                    "INSERT INTO stock_moves \
                        (id, tenant_id, site_id, product_id, from_location, to_location, quantity, \
                         move_type, lot_number, reference_type, reference_id, moved_by, moved_at, created_at, \
                         status, reversed_by, reversed_at, reversal_reason, reversal_of) \
                     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,'posted',$15,$16,$17,$18)",
                )
                .bind(comp_id)
                .bind(tenant_id)
                .bind(site_id)
                .bind(product_id)
                .bind(&comp_from)
                .bind(&comp_to)
                .bind(quantity)
                .bind(&comp_type)
                .bind(&lot_number)
                .bind("reversal")
                .bind(move_id)
                .bind(actor)
                .bind(now)
                .bind(now)
                .bind(actor)
                .bind(now)
                .bind(&reason_owned)
                .bind(move_id)
                .execute(&mut **tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to post compensating move: {e}"))
                })?;

                // Mark the ORIGINAL row reversed, linked to the
                // compensating entry that undid its effect.
                let r = sqlx::query(
                    "UPDATE stock_moves \
                     SET status = 'reversed', reversed_by = $1, \
                         reversed_at = NOW(), reversal_reason = $2, \
                         reversed_by_move = $3 \
                     WHERE id = $4 AND tenant_id = $5 AND site_id = ANY($6) \
                       AND status = 'posted'",
                )
                .bind(actor)
                .bind(&reason_owned)
                .bind(comp_id)
                .bind(move_id)
                .bind(tenant_id)
                .bind(&sites)
                .execute(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to reverse stock move: {e}")))?;
                if r.rows_affected() == 0 {
                    return Err(SenseiError::NotFound(format!(
                        "Stock move {move_id} not found"
                    )));
                }

                // (3) The INVERSE inventory delta on the SAME
                // site/product/location/lot, so the balance returns. An
                // impossible inverse physical move (insufficient stock)
                // FAILS the reversal with the controlled-discrepancy
                // message; the whole transaction rolls back — the ledger
                // and the balance can never silently disagree.
                match move_type.as_str() {
                    "receipt" => {
                        apply_inventory_delta_with_lot(
                            tx,
                            tenant_id,
                            site_id,
                            product_id,
                            &delta_location,
                            delta_lot.as_deref(),
                            -quantity,
                        )
                        .await
                        .map_err(|e| {
                            SenseiError::Validation(format!(
                                "Cannot reverse receipt move {move_id}: {e}"
                            ))
                        })?;
                    }
                    "issue" => {
                        let loc = from_location
                            .clone()
                            .unwrap_or_else(|| to_location.clone());
                        apply_inventory_delta_with_lot(
                            tx,
                            tenant_id,
                            site_id,
                            product_id,
                            &loc,
                            delta_lot.as_deref(),
                            quantity,
                        )
                        .await?;
                    }
                    "transfer" => {
                        // +q back at the source, −q back out of the
                        // destination (the destination debit may fail on
                        // insufficiency — the source credit has already
                        // been applied inside the same transaction, so a
                        // failure rolls BOTH back).
                        apply_inventory_delta_with_lot(
                            tx,
                            tenant_id,
                            site_id,
                            product_id,
                            &from_location.clone().unwrap_or_default(),
                            delta_lot.as_deref(),
                            quantity,
                        )
                        .await?;
                        apply_inventory_delta_with_lot(
                            tx,
                            tenant_id,
                            site_id,
                            product_id,
                            &delta_location,
                            delta_lot.as_deref(),
                            -quantity,
                        )
                        .await
                        .map_err(|e| {
                            SenseiError::Validation(format!(
                                "Cannot reverse transfer move {move_id}: {e}"
                            ))
                        })?;
                    }
                    // 'adjustment' and any unmapped type: withdraw what
                    // the original deposited at its location.
                    _ => {
                        apply_inventory_delta_with_lot(
                            tx,
                            tenant_id,
                            site_id,
                            product_id,
                            &delta_location,
                            delta_lot.as_deref(),
                            -quantity,
                        )
                        .await
                        .map_err(|e| {
                            SenseiError::Validation(format!(
                                "Cannot reverse adjustment move {move_id}: {e}"
                            ))
                        })?;
                    }
                }
                Ok(())
            })
        })
        .await
    }

    /// MANUAL first receipt (twenty-fifth audit P1): receive stock at the
    /// caller's SINGLE authorized ACTIVE site — resolved server-side from
    /// `authorized_sites` (empty or ambiguous -> Validation, never a
    /// client-named site). The receipt creates the inventory row at that
    /// site (at the command's location, or the site-local receiving
    /// location when none is named) and posts a 'receipt' stock move
    /// stamped with the site, all in one transaction.
    async fn receive_stock(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        req: ReceiveStockCommand,
    ) -> Result<StockMove> {
        let site_id = match authorized_sites {
            [site] => *site,
            [] => {
                return Err(SenseiError::Validation(
                    "No authorized site is available — a manual stock receipt \
                     must be attributed to the caller's active site"
                        .to_string(),
                ))
            }
            _ => {
                return Err(SenseiError::Validation(format!(
                    "The caller is authorized at {} sites — a manual stock \
                     receipt must be attributed to the single ACTIVE site",
                    authorized_sites.len()
                )))
            }
        };
        if req.quantity <= 0 {
            return Err(SenseiError::Validation(
                "Received quantity must be positive".to_string(),
            ));
        }
        if req.reason.trim().is_empty() {
            return Err(SenseiError::Validation(
                "A manual stock receipt requires a reason".to_string(),
            ));
        }
        let lot = req
            .lot
            .as_deref()
            .map(str::trim)
            .filter(|l| !l.is_empty())
            .map(str::to_string);
        let product_id = req.product_id;
        let quantity = req.quantity;
        with_tenant_tx(&self.pool, tenant_id, move |tx| {
            Box::pin(async move {
                // The receiving location: the command's location when it
                // names one, else the SITE's receiving location
                // (site-configured or the site-local 'receiving' label) —
                // never a label discovered tenant-wide.
                let location = match req.location.as_deref() {
                    Some(l) if !l.trim().is_empty() => l.trim().to_string(),
                    _ => resolve_stock_location(&mut *tx, tenant_id, site_id, product_id).await?,
                };
                apply_inventory_delta_with_lot(
                    &mut *tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    lot.as_deref(),
                    quantity,
                )
                .await?;
                let row = sqlx::query_as::<_, StockMoveRow>(
                    r#"INSERT INTO stock_moves (id, tenant_id, site_id, product_id, quantity, move_type, from_location, to_location, lot_number, reference_type, reference_id, moved_at, created_at)
                       VALUES ($1,$2,$3,$4,$5,'receipt',NULL,$6,$7,'manual_receipt',NULL,NOW(),NOW())
                       RETURNING id, tenant_id, product_id,
                                 (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                                 quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                                 moved_by AS created_by, created_at,
                                 site_id, status, reversed_by, reversed_at, reversal_reason, reversal_of, reversed_by_move"#,
                )
                .bind(Uuid::new_v4())
                .bind(tenant_id)
                .bind(site_id)
                .bind(product_id)
                .bind(quantity)
                .bind(&location)
                .bind(&lot)
                .fetch_one(&mut **tx)
                .await
                .map_err(|e| SenseiError::Database(format!("Failed to record stock receipt: {e}")))?;
                Ok(sm_row_to_domain(row))
            })
        })
        .await
    }

    // ── Site-entitled inventory (twenty-third audit P0/P1) ─────────────
    //
    // Every scoped operation intersects the affected inventory_items
    // rows with the caller's RequestContext site entitlement via
    // `site_id = ANY(authorized_sites)`. The predicate lives in the
    // SQL — an EMPTY entitlement matches NOTHING (never a tenant-wide
    // fallback) — and a row whose site is NULL (created outside any
    // site context) or FOREIGN is indistinguishable from a nonexistent
    // row: reads never return it, mutations fail with NotFound BEFORE
    // any quantity change.

    async fn get_inventory_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        product_id: Uuid,
    ) -> Result<Vec<InventoryItem>> {
        if authorized_sites.is_empty() {
            return Ok(Vec::new());
        }
        let sites = authorized_sites.to_vec();
        let rows = sqlx::query_as::<_, InventoryRow>(
            "SELECT id, tenant_id, product_id, \
                    (SELECT name FROM products WHERE products.id = inventory_items.product_id) \
                        AS product_name, \
                    COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point, \
                    0::bigint AS reorder_quantity, \
                    quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint, \
                    location, lot_number, updated_at \
             FROM inventory_items \
             WHERE product_id=$1 AND tenant_id=$2 AND site_id = ANY($3)",
        ).bind(product_id).bind(tenant_id).bind(&sites).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get scoped inventory: {e}")))?;
        Ok(rows.into_iter().map(inv_row_to_domain).collect())
    }

    async fn list_inventory_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        location: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<InventoryItem>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        if authorized_sites.is_empty() {
            return Ok(paginate(Vec::new(), 0, page, per_page));
        }
        let offset = (page - 1) * per_page;
        let sites = authorized_sites.to_vec();
        let items: Vec<InventoryRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, product_id,
                      (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                          AS product_name,
                      COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                      0::bigint AS reorder_quantity,
                      quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                      location, lot_number, updated_at
               FROM inventory_items
               WHERE tenant_id=$1 AND site_id = ANY($2)
                 AND ($3::text IS NULL OR location=$3) ORDER BY product_name LIMIT $4 OFFSET $5"#,
        ).bind(tenant_id).bind(&sites).bind(location).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list scoped inventory: {e}")))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM inventory_items WHERE tenant_id=$1 AND site_id = ANY($2) AND ($3::text IS NULL OR location=$3)",
        )
        .bind(tenant_id).bind(&sites).bind(location).fetch_one(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to count scoped inventory: {e}")))?;
        Ok(paginate(
            items.into_iter().map(inv_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
    }

    async fn adjust_inventory_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        product_id: Uuid,
        location: &str,
        quantity_change: i64,
        reason: &str,
    ) -> Result<InventoryItem> {
        // An adjustment without a reason is not an inventory transaction.
        if reason.trim().is_empty() {
            return Err(SenseiError::Validation(
                "An inventory adjustment requires a reason".to_string(),
            ));
        }
        // Empty entitlement matches nothing: no row can be authorized.
        if authorized_sites.is_empty() {
            return Err(SenseiError::NotFound(format!(
                "Inventory for product {product_id} at {location} not found"
            )));
        }
        let sites = authorized_sites.to_vec();
        let mut tx =
            self.pool.begin().await.map_err(|e| {
                SenseiError::Database(format!("Failed to begin adjustment tx: {e}"))
            })?;

        // Twenty-fourth audit P0: an adjustment targets EXACTLY ONE row.
        // Resolve the single site among the entitled rows at (tenant,
        // product, location): none entitled -> the row is indistinguishable
        // from nonexistent (NotFound); several entitled sites own a row at
        // this location name -> the adjustment cannot be attributed and is
        // refused (Validation) instead of mutating several sites' balances.
        let entitled_sites: Vec<Uuid> = sqlx::query_scalar(
            "SELECT DISTINCT site_id FROM inventory_items \
             WHERE product_id=$1 AND tenant_id=$2 AND location=$3 \
               AND site_id = ANY($4)",
        )
        .bind(product_id)
        .bind(tenant_id)
        .bind(location)
        .bind(&sites)
        .fetch_all(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to resolve adjustment site: {e}")))?;
        let site_id = match entitled_sites.as_slice() {
            [] => {
                return Err(SenseiError::NotFound(format!(
                    "Inventory for product {product_id} at {location} not found"
                )));
            }
            [site] => *site,
            _ => {
                return Err(SenseiError::Validation(format!(
                    "Inventory at '{location}' for product {product_id} is owned by \
                     multiple entitled sites — the adjustment cannot be \
                     attributed to one site's balance"
                )));
            }
        };

        let maybe_row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items
               SET quantity_on_hand = quantity_on_hand + $1::double precision,
                   quantity_available = quantity_on_hand + $1::double precision - quantity_reserved
               WHERE product_id=$2 AND tenant_id=$3 AND location=$4
                 AND site_id = $5
                 AND quantity_on_hand + $1::double precision >= 0
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(quantity_change).bind(product_id).bind(tenant_id).bind(location).bind(site_id)
            .fetch_optional(&mut *tx).await
            .map_err(|e| SenseiError::Database(format!("Failed to adjust scoped inventory: {e}")))?;
        let row = match maybe_row {
            Some(row) => row,
            None => {
                // The resolved entitled row exists (site_id above) but the
                // negativity guard rejected the change: an insufficiency,
                // never a disappearance.
                return Err(SenseiError::Validation(format!(
                    "Insufficient stock at '{location}' for product {product_id}: \
                     {quantity_change} would drive the balance negative"
                )));
            }
        };

        // The ledger row: inventory never changes without a corresponding
        // stock transaction (schema-true columns — no product_name or
        // created_by on stock_moves). The move is stamped with the site it
        // adjusted.
        sqlx::query(
            "INSERT INTO stock_moves \
                (id, tenant_id, site_id, product_id, quantity, move_type, \
                 from_location, to_location, reference_type, reference_id, moved_at, created_at) \
             VALUES ($1, $2, $3, $4, $5, 'adjustment', $6, $7, 'inventory_adjustment', NULL, NOW(), NOW())",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
        .bind(site_id)
        .bind(product_id)
        .bind(quantity_change.abs())
        .bind(location)
        .bind(location)
        .execute(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to record adjustment ledger: {e}")))?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit adjustment tx: {e}")))?;
        Ok(inv_row_to_domain(row))
    }

    async fn create_stock_move_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        stock_move: StockMove,
    ) -> Result<StockMove> {
        // Validation BEFORE any write (mirrors create_stock_move).
        if stock_move.quantity <= 0 {
            return Err(SenseiError::Validation(
                "Stock move quantity must be positive".to_string(),
            ));
        }
        match stock_move.move_type.as_str() {
            "receipt" | "delivery" | "issue" | "transfer" | "adjustment" => {}
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unknown stock move type '{other}'"
                )));
            }
        }
        if stock_move.move_type == "transfer"
            && (stock_move
                .from_location
                .as_deref()
                .is_none_or(|l| l.is_empty())
                || stock_move.to_location.is_empty())
        {
            return Err(SenseiError::Validation(
                "A transfer requires both a source and a destination location".to_string(),
            ));
        }
        if authorized_sites.is_empty() {
            return Err(SenseiError::NotFound(format!(
                "No inventory row of product {} is inside the caller's site scope",
                stock_move.product_id
            )));
        }
        let sites = authorized_sites.to_vec();
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;
        set_tenant_context(&mut tx, tenant_id).await?;

        let now = Utc::now();
        let id = Uuid::new_v4();
        let product_id = stock_move.product_id;
        let from_location = stock_move.from_location.as_deref().map(str::to_string);
        let to_location = stock_move.to_location.clone();

        // SITE SCOPE FIRST (twenty-fourth audit P0): the move's authority
        // derives through the source/destination inventory ROW sites, and
        // the move is stamped with the SINGLE site its rows live at. A
        // location owned by several ENTITLED sites is ambiguous (the delta
        // could not be attributed to one row) — Validation; a location
        // with no entitled row is indistinguishable from a nonexistent one
        // (NotFound), and NO quantity changes — the transaction rolls
        // back.

        // Resolve the move's site and the location(s) its effects touch
        // BEFORE any write: the INSERT below is stamped with the site.
        let (location, dest_location, site_id) = match stock_move.move_type.as_str() {
            "receipt" => {
                let (location, site_id) = match to_location.as_str() {
                    "" => entitled_anchor_row(&mut tx, tenant_id, product_id, &sites)
                        .await?
                        .ok_or_else(|| {
                            SenseiError::NotFound(format!(
                                "No inventory row of product {product_id} is inside the \
                                 caller's site scope"
                            ))
                        })?,
                    l => {
                        let site =
                            resolve_single_site(&mut tx, tenant_id, product_id, l, Some(&sites))
                                .await?
                                .ok_or_else(|| {
                                    SenseiError::NotFound(format!(
                                        "Inventory for product {product_id} at location '{l}' is \
                                 outside the caller's site scope"
                                    ))
                                })?;
                        (l.to_string(), site)
                    }
                };
                (location, None, site_id)
            }
            "delivery" | "issue" => {
                let (location, site_id) = match from_location.as_ref() {
                    Some(l) if !l.is_empty() => {
                        let site =
                            resolve_single_site(&mut tx, tenant_id, product_id, l, Some(&sites))
                                .await?
                                .ok_or_else(|| {
                                    SenseiError::NotFound(format!(
                                        "Inventory for product {product_id} at location '{l}' is \
                                 outside the caller's site scope"
                                    ))
                                })?;
                        (l.clone(), site)
                    }
                    _ => entitled_anchor_row(&mut tx, tenant_id, product_id, &sites)
                        .await?
                        .ok_or_else(|| {
                            SenseiError::NotFound(format!(
                                "No inventory row of product {product_id} is inside the \
                                 caller's site scope"
                            ))
                        })?,
                };
                (location, None, site_id)
            }
            "transfer" => {
                // Source is required by the validation above; its site is
                // the move's site.
                let from = from_location.clone().unwrap_or_default();
                let source_site =
                    resolve_single_site(&mut tx, tenant_id, product_id, &from, Some(&sites))
                        .await?
                        .ok_or_else(|| {
                            SenseiError::NotFound(format!(
                                "Inventory for product {product_id} at location '{from}' is \
                                 outside the caller's site scope"
                            ))
                        })?;
                let to = to_location.clone();
                let dest_site =
                    resolve_single_site(&mut tx, tenant_id, product_id, &to, Some(&sites))
                        .await?
                        .ok_or_else(|| {
                            SenseiError::NotFound(format!(
                                "Inventory for product {product_id} at location '{to}' is \
                                 outside the caller's site scope"
                            ))
                        })?;
                if dest_site != source_site {
                    return Err(SenseiError::Validation(format!(
                        "Transfer source '{from}' and destination '{to}' are stocked at \
                         DIFFERENT sites — one move cannot span sites; issue at the \
                         source site and receipt at the destination site instead"
                    )));
                }
                (from, Some(to), source_site)
            }
            "adjustment" => {
                let location = match from_location {
                    Some(l) if !l.is_empty() => l,
                    _ => to_location,
                };
                let site_id =
                    resolve_single_site(&mut tx, tenant_id, product_id, &location, Some(&sites))
                        .await?
                        .ok_or_else(|| {
                            SenseiError::NotFound(format!(
                                "Inventory for product {product_id} at location \
                                 '{location}' is outside the caller's site scope"
                            ))
                        })?;
                (location, None, site_id)
            }
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unsupported stock move type '{other}'"
                )));
            }
        };

        // A 'delivery' is stored as its schema equivalent 'issue' (the
        // stock_moves move_type CHECK admits receipt/issue/transfer/
        // adjustment); product_name is read from products.
        let stored_move_type: &str = if stock_move.move_type == "delivery" {
            "issue"
        } else {
            &stock_move.move_type
        };
        let row = sqlx::query_as::<_, StockMoveRow>(
            r#"INSERT INTO stock_moves (id, tenant_id, site_id, product_id, quantity, move_type, from_location, to_location, reference_type, reference_id, moved_by, moved_at, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                         quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                         moved_by AS created_by, created_at, site_id, status, reversed_by, reversed_at, reversal_reason, reversal_of, reversed_by_move"#,
        ).bind(id).bind(tenant_id).bind(site_id).bind(product_id)
            .bind(stock_move.quantity).bind(stored_move_type).bind(&stock_move.from_location)
            .bind(&stock_move.to_location).bind(&stock_move.reference_type).bind(stock_move.reference_id)
            .bind(stock_move.created_by).bind(now).bind(now)
            .fetch_one(&mut *tx).await.map_err(|e| SenseiError::Database(format!("Failed to create scoped stock move: {e}")))?;

        // Apply the inventory effect inside the same transaction, honouring
        // the move semantics — ALWAYS on the resolved site's row.
        match stock_move.move_type.as_str() {
            "receipt" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            "delivery" | "issue" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
            }
            "transfer" => {
                // Hard rule (item 126): an inventory transfer must balance
                // (Σ location deltas = 0). The rule is the gate.
                crate::tps::rules::check_transfer_balance(&[
                    (product_id, -stock_move.quantity),
                    (product_id, stock_move.quantity),
                ])
                .map_err(|v| SenseiError::Validation(v.message().to_string()))?;
                let to = dest_location.unwrap_or_default();
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &to,
                    stock_move.quantity,
                )
                .await?;
            }
            "adjustment" => {
                apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    site_id,
                    product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            other => {
                return Err(SenseiError::Validation(format!(
                    "Unsupported stock move type '{other}'"
                )));
            }
        }

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit stock move: {e}")))?;

        Ok(sm_row_to_domain(row))
    }

    async fn update_inventory_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
        _item: InventoryItem,
    ) -> Result<InventoryItem> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::NotFound(format!(
                "Inventory item {id} not found"
            )));
        }
        let sites = authorized_sites.to_vec();
        let row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items SET updated_at = NOW()
               WHERE id=$1 AND tenant_id=$2 AND site_id = ANY($3)
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(id).bind(tenant_id).bind(&sites)
            .fetch_optional(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to update scoped inventory: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Inventory item {id} not found")))?;
        Ok(inv_row_to_domain(row))
    }

    async fn delete_inventory_scoped(
        &self,
        tenant_id: Uuid,
        authorized_sites: &[Uuid],
        id: Uuid,
    ) -> Result<()> {
        if authorized_sites.is_empty() {
            return Err(SenseiError::NotFound(format!(
                "Inventory item {id} not found"
            )));
        }
        let sites = authorized_sites.to_vec();
        let r = sqlx::query(
            "DELETE FROM inventory_items WHERE id=$1 AND tenant_id=$2 AND site_id = ANY($3)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&sites)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to delete scoped inventory: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!(
                "Inventory item {id} not found"
            )));
        }
        Ok(())
    }
}
