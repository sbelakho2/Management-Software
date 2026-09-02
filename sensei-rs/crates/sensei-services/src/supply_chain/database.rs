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
    InventoryItem, POItem, PurchaseOrder, Quote, QuoteLineItem, RFQItem, SalesOrder,
    SalesOrderItem, StockMove, SupplyChainService, RFQ,
};

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

pub struct DatabaseSupplyChainService {
    pool: PgPool,
}

impl DatabaseSupplyChainService {
    /// Create a new [`DatabaseSupplyChainService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Apply a signed quantity delta to an inventory row at `location`,
    /// creating the row when it does not exist (receipts create stock).
    async fn apply_inventory_delta(
        &self,
        tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
        tenant_id: Uuid,
        product_id: Uuid,
        location: &str,
        delta: i64,
    ) -> Result<()> {
        // The unique index on (tenant, product, location, lot_number) treats
        // NULL lot numbers as distinct, so update-then-insert is used instead
        // of ON CONFLICT.
        // Never clamp an inventory transaction: an issue that would drive
        // the balance negative must be REJECTED so the ledger and the
        // balance can never disagree.
        let updated = sqlx::query(
            "UPDATE inventory_items \
             SET quantity_on_hand = quantity_on_hand + $1::double precision, \
                 quantity_available = quantity_on_hand + $1::double precision - quantity_reserved \
             WHERE tenant_id = $2 AND product_id = $3 AND location = $4 AND lot_number IS NULL \
               AND quantity_on_hand + $1::double precision >= 0",
        )
        .bind(delta)
        .bind(tenant_id)
        .bind(product_id)
        .bind(location)
        .execute(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update inventory: {e}")))?;

        if updated.rows_affected() == 0 {
            // No row exists: only a positive (receipt-like) delta may
            // create stock. Issuing from nothing is a rejected transaction.
            if delta < 0 {
                return Err(SenseiError::Validation(format!(
                    "Insufficient stock at '{location}' for product {product_id}: \
                     {delta} units would drive the balance negative"
                )));
            }
            sqlx::query(
                "INSERT INTO inventory_items \
                 (id, tenant_id, product_id, location, quantity_on_hand, quantity_reserved, quantity_available, lot_number) \
                 VALUES ($1, $2, $3, $4, $5, 0, $5, NULL)",
            )
            .bind(Uuid::new_v4())
            .bind(tenant_id)
            .bind(product_id)
            .bind(location)
            .bind(delta)
            .execute(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to create inventory row: {e}")))?;
        }
        Ok(())
    }

    /// Resolve the receiving location: the product's first known inventory
    /// location, or the warehouse default (`main`) when none exists.
    async fn resolve_stock_location(
        &self,
        tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
        tenant_id: Uuid,
        product_id: Uuid,
    ) -> Result<String> {
        let location: Option<String> = sqlx::query_scalar(
            "SELECT location FROM inventory_items \
             WHERE tenant_id = $1 AND product_id = $2 \
             ORDER BY created_at LIMIT 1",
        )
        .bind(tenant_id)
        .bind(product_id)
        .fetch_optional(&mut **tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to resolve stock location: {e}")))?;
        Ok(location.unwrap_or_else(|| "main".to_string()))
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
        let row = sqlx::query_as::<_, SalesOrderRow>(
            "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders WHERE id=$1 AND tenant_id=$2 AND fulfilling_site_id = ANY($3)",
        ).bind(id).bind(tenant_id).bind(authorized_sites).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get scoped sales order: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
        Ok(so_row_to_domain(row))
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
        let items: Vec<SalesOrderRow> = sqlx::query_as(
            "SELECT id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id FROM sales_orders \
             WHERE tenant_id=$1 AND fulfilling_site_id = ANY($2) \
               AND ($3::text IS NULL OR status=$3) \
             ORDER BY created_at DESC LIMIT $4 OFFSET $5",
        ).bind(tenant_id).bind(authorized_sites).bind(&status_owned).bind(per_page as i64).bind(offset as i64)
            .fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list scoped sales orders: {e}")))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM sales_orders WHERE tenant_id=$1 AND fulfilling_site_id = ANY($2) \
             AND ($3::text IS NULL OR status=$3)",
        )
        .bind(tenant_id).bind(authorized_sites).bind(&status_owned)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count scoped sales orders: {e}")))?;
        Ok(paginate(
            items.into_iter().map(so_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
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
        let row = sqlx::query_as::<_, PurchaseOrderRow>(
            "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders WHERE id=$1 AND tenant_id=$2 AND receiving_site_id = ANY($3)",
        ).bind(id).bind(tenant_id).bind(authorized_sites).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to get scoped purchase order: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;
        Ok(po_row_to_domain(row))
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
        let items: Vec<PurchaseOrderRow> = sqlx::query_as(
            "SELECT id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id FROM purchase_orders \
             WHERE tenant_id=$1 AND receiving_site_id = ANY($2) \
               AND ($3::text IS NULL OR status=$3) \
             ORDER BY created_at DESC LIMIT $4 OFFSET $5",
        ).bind(tenant_id).bind(authorized_sites).bind(&status_owned).bind(per_page as i64).bind(offset as i64)
            .fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list scoped purchase orders: {e}")))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM purchase_orders WHERE tenant_id=$1 AND receiving_site_id = ANY($2) \
             AND ($3::text IS NULL OR status=$3)",
        )
        .bind(tenant_id).bind(authorized_sites).bind(&status_owned)
        .fetch_one(&self.pool).await
        .map_err(|e| SenseiError::Database(format!("Failed to count scoped purchase orders: {e}")))?;
        Ok(paginate(
            items.into_iter().map(po_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
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

        let row = sqlx::query_as::<_, SalesOrderRow>(
            r#"INSERT INTO sales_orders (id, tenant_id, so_number, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id)
               VALUES ($1,$2,$3,$3,$4,$5,'draft',$6,$7,$8,$9,$10,$11,$12,$13)
               RETURNING id, tenant_id, order_number, customer_id, customer_name, status, line_items, total_amount, currency, delivery_date, shipping_address, created_by, created_at, fulfilling_site_id"#,
        ).bind(id).bind(tenant_id).bind(&order_number).bind(order.customer_id).bind(&order.customer_name)
            .bind(&li_json).bind(total).bind(&order.currency).bind(order.delivery_date).bind(&order.shipping_address).bind(order.created_by).bind(now)
            .bind(order.fulfilling_site_id)
            .fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to create sales order: {e}")))?;
        Ok(so_row_to_domain(row))
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
        ).bind(status).bind(id).bind(tenant_id).bind(&sites).fetch_optional(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to update sales order status: {e}")))?
            .ok_or_else(|| SenseiError::NotFound(format!("Sales order {id} not found")))?;
        Ok(so_row_to_domain(row))
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

        let row = sqlx::query_as::<_, PurchaseOrderRow>(
            r#"INSERT INTO purchase_orders (id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id)
               VALUES ($1,$2,$3,$4,$5,'draft',$6,$7,$8,$9,$10,$11,$12)
               RETURNING id, tenant_id, po_number, supplier_id, supplier_name, status, line_items, total_amount, currency, expected_delivery, created_by, created_at, receiving_site_id"#,
        ).bind(id).bind(tenant_id).bind(&po_number).bind(po.supplier_id).bind(&po.supplier_name)
            .bind(&li_json).bind(total).bind(&po.currency).bind(po.expected_delivery).bind(po.created_by).bind(now)
            .bind(po.receiving_site_id)
            .fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to create PO: {e}")))?;
        Ok(po_row_to_domain(row))
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
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;

        // Load the PO's JSONB line items and supplier, then update them.
        // Twenty-third audit P0: the scope boundary is part of the guard
        // read — a PO whose receiving site is NULL or outside
        // `authorized_sites` is indistinguishable from a nonexistent PO,
        // so no line update, stock movement or inventory effect can
        // happen for it.
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
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get PO: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {po_id} not found")))?;

        let mut items: Vec<POItem> = serde_json::from_value(row.line_items).map_err(|e| {
            tracing::error!(po_id = %po_id, "Failed to deserialize PO line items: {e}");
            SenseiError::Database(format!(
                "Purchase order {po_id} has corrupt line items: {e}"
            ))
        })?;

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

        // Effects apply only to the scoped row: the same site boundary is
        // repeated in the state UPDATE.
        sqlx::query("UPDATE purchase_orders SET line_items=$1, status=$2, updated_at=NOW() WHERE id=$3 AND tenant_id=$4 AND receiving_site_id = ANY($5)")
            .bind(&li_json).bind(new_status).bind(po_id).bind(tenant_id).bind(&sites)
            .execute(&mut *tx).await
            .map_err(|e| SenseiError::Database(format!("Failed to receive PO line: {e}")))?;

        // Update inventory at the product's first known location.
        let location = self
            .resolve_stock_location(&mut tx, tenant_id, product_id)
            .await?;
        self.apply_inventory_delta(&mut tx, tenant_id, product_id, &location, quantity_received)
            .await?;

        // Record the stock move and goods receipt inside the same transaction.
        sqlx::query(
            "INSERT INTO stock_moves (id, tenant_id, product_id, from_location, to_location, quantity, move_type, reference_type, reference_id, moved_at, created_at) \
             VALUES ($1,$2,$3,NULL,$4,$5,'receipt','purchase_order',$6,NOW(),NOW())",
        )
        .bind(Uuid::new_v4()).bind(tenant_id).bind(product_id).bind(&location)
        .bind(quantity_received).bind(po_id)
        .execute(&mut *tx).await
        .map_err(|e| SenseiError::Database(format!("Failed to record stock move: {e}")))?;

        // The goods receipt status describes THIS receipt, not the PO:
        // a partial line receipt is never 'fully_received'.
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
        .execute(&mut *tx).await
        .map_err(|e| SenseiError::Database(format!("Failed to record goods receipt: {e}")))?;

        let updated: PurchaseOrderRow = sqlx::query_as(
            r#"SELECT id, tenant_id, po_number, supplier_id, supplier_name, status,
                      line_items, total_amount, currency, expected_delivery, created_by, created_at,
                      receiving_site_id
               FROM purchase_orders WHERE id=$1 AND tenant_id=$2"#,
        )
        .bind(po_id)
        .bind(tenant_id)
        .fetch_one(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to reload PO: {e}")))?;

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit receipt: {e}")))?;

        Ok(po_row_to_domain(updated))
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
        let mut tx =
            self.pool.begin().await.map_err(|e| {
                SenseiError::Database(format!("Failed to begin adjustment tx: {e}"))
            })?;

        let row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items
               SET quantity_on_hand = quantity_on_hand + $1::double precision,
                   quantity_available = quantity_on_hand + $1::double precision - quantity_reserved
               WHERE product_id=$2 AND tenant_id=$3 AND location=$4
                 AND quantity_on_hand + $1::double precision >= 0
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(quantity_change).bind(product_id).bind(tenant_id).bind(location)
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
                (id, tenant_id, product_id, quantity, move_type, \
                 from_location, to_location, reference_type, reference_id, moved_at, created_at) \
             VALUES ($1, $2, $3, $4, 'adjustment', $5, $6, 'inventory_adjustment', NULL, NOW(), NOW())",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
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
            r#"INSERT INTO stock_moves (id, tenant_id, product_id, quantity, move_type, from_location, to_location, reference_type, reference_id, moved_by, moved_at, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                         quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                         moved_by AS created_by, created_at"#,
        ).bind(id).bind(tenant_id).bind(stock_move.product_id)
            .bind(stock_move.quantity).bind(stored_move_type).bind(&stock_move.from_location)
            .bind(&stock_move.to_location).bind(&stock_move.reference_type).bind(stock_move.reference_id)
            .bind(stock_move.created_by).bind(now).bind(now)
            .fetch_one(&mut *tx).await.map_err(|e| SenseiError::Database(format!("Failed to create stock move: {e}")))?;

        // Apply the inventory effect inside the same transaction, honouring
        // the move semantics: receipts credit the destination, issues/debits
        // the source, transfers move between both, adjustments apply to the
        // named location.
        let from_location = stock_move.from_location.as_deref().map(str::to_string);
        let to_location = stock_move.to_location.clone();

        match stock_move.move_type.as_str() {
            "receipt" => {
                let location = match to_location.as_str() {
                    "" => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                    l => l.to_string(),
                };
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            "delivery" | "issue" => {
                let location = match from_location {
                    Some(l) if !l.is_empty() => l,
                    _ => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                };
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
            }
            "transfer" => {
                // Hard rule (item 126): an inventory transfer must balance
                // (Σ location deltas = 0). The rule is the gate.
                crate::tps::rules::check_transfer_balance(&[
                    (stock_move.product_id, -stock_move.quantity),
                    (stock_move.product_id, stock_move.quantity),
                ])
                .map_err(|v| SenseiError::Validation(v.message().to_string()))?;
                // Source is validated present; debit it strictly.
                let from = from_location.clone().unwrap_or_default();
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &from,
                    -stock_move.quantity,
                )
                .await?;
                let to = match to_location.as_str() {
                    "" => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                    l => l.to_string(),
                };
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &to,
                    stock_move.quantity,
                )
                .await?;
            }
            "adjustment" => {
                let location = match from_location {
                    Some(l) if !l.is_empty() => l,
                    _ => to_location,
                };
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
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
        let items: Vec<StockMoveRow> = sqlx::query_as(
            r#"SELECT id, tenant_id, product_id,
                      (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                      quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                      moved_by AS created_by, created_at
               FROM stock_moves
               WHERE tenant_id=$1 AND ($2::uuid IS NULL OR product_id=$2) ORDER BY created_at DESC LIMIT $3 OFFSET $4"#,
        ).bind(tenant_id).bind(product_id).bind(per_page as i64).bind(offset as i64).fetch_all(&self.pool).await
            .map_err(|e| SenseiError::Database(format!("Failed to list stock moves: {e}")))?;
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM stock_moves WHERE tenant_id=$1 AND ($2::uuid IS NULL OR product_id=$2)")
            .bind(tenant_id).bind(product_id).fetch_one(&self.pool).await.map_err(|e| SenseiError::Database(format!("Failed to count stock moves: {e}")))?;
        Ok(paginate(
            items.into_iter().map(sm_row_to_domain).collect(),
            count,
            page,
            per_page,
        ))
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
        let mut tx = self
            .pool
            .begin()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to begin transaction: {e}")))?;

        // Twenty-third audit P0: the scope boundary is part of the guard
        // read — a PO whose receiving site is NULL or outside
        // `authorized_sites` is indistinguishable from a nonexistent PO,
        // so the full receipt is rejected BEFORE any line update, stock
        // movement or inventory effect happens.
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
        .fetch_optional(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get PO: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Purchase order {id} not found")))?;

        if row.status == "received" || row.status == "cancelled" {
            return Err(SenseiError::Validation(format!(
                "Cannot receive PO with status: {}",
                row.status
            )));
        }

        let mut items: Vec<POItem> = serde_json::from_value(row.line_items).map_err(|e| {
            tracing::error!(po_id = %id, "Failed to deserialize PO line items: {e}");
            SenseiError::Database(format!("Purchase order {id} has corrupt line items: {e}"))
        })?;

        // Capture the remaining quantity per line BEFORE marking them received.
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
        // Effects apply only to the scoped row: the same site boundary is
        // repeated in the state UPDATE.
        sqlx::query("UPDATE purchase_orders SET line_items=$1, status='received', updated_at=NOW() WHERE id=$2 AND tenant_id=$3 AND receiving_site_id = ANY($4)")
            .bind(&li_json).bind(id).bind(tenant_id).bind(&sites)
            .execute(&mut *tx).await
            .map_err(|e| SenseiError::Database(format!("Failed to receive full PO: {e}")))?;

        // Update inventory for the quantities captured before the mutation.
        for (product_id, _product_name, qty) in &remaining {
            let location = self
                .resolve_stock_location(&mut tx, tenant_id, *product_id)
                .await?;
            self.apply_inventory_delta(&mut tx, tenant_id, *product_id, &location, *qty)
                .await?;
            sqlx::query(
                "INSERT INTO stock_moves (id, tenant_id, product_id, from_location, to_location, quantity, move_type, reference_type, reference_id, moved_at, created_at) \
                 VALUES ($1,$2,$3,NULL,$4,$5,'receipt','purchase_order',$6,NOW(),NOW())",
            )
            .bind(Uuid::new_v4()).bind(tenant_id).bind(product_id).bind(&location)
            .bind(qty).bind(id)
            .execute(&mut *tx).await
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
        .fetch_one(&mut *tx)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to reload PO: {e}")))?;

        // Item 28: the receipt (state mutation + inventory + ledger) and
        // its integration-driving event are ONE transaction.
        sensei_db::outbox::enqueue_outbox(
            &mut tx,
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

        tx.commit()
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to commit full receipt: {e}")))?;

        Ok(po_row_to_domain(updated))
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

    async fn delete_stock_move(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM stock_moves WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to delete stock move: {e}")))?;
        if r.rows_affected() == 0 {
            return Err(SenseiError::NotFound(format!("Stock move {id} not found")));
        }
        Ok(())
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

        let maybe_row = sqlx::query_as::<_, InventoryRow>(
            r#"UPDATE inventory_items
               SET quantity_on_hand = quantity_on_hand + $1::double precision,
                   quantity_available = quantity_on_hand + $1::double precision - quantity_reserved
               WHERE product_id=$2 AND tenant_id=$3 AND location=$4
                 AND site_id = ANY($5)
                 AND quantity_on_hand + $1::double precision >= 0
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = inventory_items.product_id)
                             AS product_name,
                         COALESCE((SELECT reorder_point FROM products WHERE products.id = inventory_items.product_id), 0)::bigint AS reorder_point,
                         0::bigint AS reorder_quantity,
                         quantity_on_hand::bigint, quantity_reserved::bigint, quantity_available::bigint,
                         location, lot_number, updated_at"#,
        ).bind(quantity_change).bind(product_id).bind(tenant_id).bind(location).bind(&sites)
            .fetch_optional(&mut *tx).await
            .map_err(|e| SenseiError::Database(format!("Failed to adjust scoped inventory: {e}")))?;
        let row = match maybe_row {
            Some(row) => row,
            None => {
                // The negativity guard above failed OR no entitled row
                // matched. Prove which: an ENTITLED row that exists but
                // cannot absorb the change is an insufficiency
                // (Validation); anything else (foreign site, NULL site,
                // no row at all) is indistinguishable from a nonexistent
                // row (NotFound).
                let entitled: Option<Uuid> = sqlx::query_scalar(
                    "SELECT id FROM inventory_items \
                     WHERE product_id=$1 AND tenant_id=$2 AND location=$3 \
                       AND site_id = ANY($4) LIMIT 1",
                )
                .bind(product_id)
                .bind(tenant_id)
                .bind(location)
                .bind(&sites)
                .fetch_optional(&mut *tx)
                .await
                .map_err(|e| {
                    SenseiError::Database(format!("Failed to probe scoped inventory row: {e}"))
                })?;
                return Err(match entitled {
                    Some(_) if quantity_change < 0 => SenseiError::Validation(format!(
                        "Insufficient stock at '{location}' for product {product_id}: \
                         {quantity_change} would drive the balance negative"
                    )),
                    _ => SenseiError::NotFound(format!(
                        "Inventory for product {product_id} at {location} not found"
                    )),
                });
            }
        };

        // The ledger row: inventory never changes without a corresponding
        // stock transaction (schema-true columns — no product_name or
        // created_by on stock_moves).
        sqlx::query(
            "INSERT INTO stock_moves \
                (id, tenant_id, product_id, quantity, move_type, \
                 from_location, to_location, reference_type, reference_id, moved_at, created_at) \
             VALUES ($1, $2, $3, $4, 'adjustment', $5, $6, 'inventory_adjustment', NULL, NOW(), NOW())",
        )
        .bind(Uuid::new_v4())
        .bind(tenant_id)
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
        // A 'delivery' is stored as its schema equivalent 'issue' (the
        // stock_moves move_type CHECK admits receipt/issue/transfer/
        // adjustment); product_name is read from products.
        let stored_move_type: &str = if stock_move.move_type == "delivery" {
            "issue"
        } else {
            &stock_move.move_type
        };
        let row = sqlx::query_as::<_, StockMoveRow>(
            r#"INSERT INTO stock_moves (id, tenant_id, product_id, quantity, move_type, from_location, to_location, reference_type, reference_id, moved_by, moved_at, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
               RETURNING id, tenant_id, product_id,
                         (SELECT name FROM products WHERE products.id = stock_moves.product_id) AS product_name,
                         quantity::bigint, move_type, from_location, to_location, reference_type, reference_id,
                         moved_by AS created_by, created_at"#,
        ).bind(id).bind(tenant_id).bind(stock_move.product_id)
            .bind(stock_move.quantity).bind(stored_move_type).bind(&stock_move.from_location)
            .bind(&stock_move.to_location).bind(&stock_move.reference_type).bind(stock_move.reference_id)
            .bind(stock_move.created_by).bind(now).bind(now)
            .fetch_one(&mut *tx).await.map_err(|e| SenseiError::Database(format!("Failed to create scoped stock move: {e}")))?;

        // SITE SCOPE FIRST: the move's authority derives through the
        // source/destination inventory ROW sites. Every row the move will
        // touch must already exist with its site inside `authorized_sites`
        // (foreign / site-less / absent row -> NotFound, and NO quantity
        // change happens — the transaction rolls back).
        let from_location = stock_move.from_location.as_deref().map(str::to_string);
        let to_location = stock_move.to_location.clone();

        // Prove the row at (product, location) is entitled.
        let require_entitled = async |tx: &mut sqlx::Transaction<'_, sqlx::Postgres>,
                                      location: &str|
               -> std::result::Result<(), SenseiError> {
            let probe: Option<Uuid> = sqlx::query_scalar(
                "SELECT id FROM inventory_items \
                 WHERE tenant_id = $1 AND product_id = $2 AND location = $3 \
                   AND site_id = ANY($4) LIMIT 1",
            )
            .bind(tenant_id)
            .bind(stock_move.product_id)
            .bind(location)
            .bind(&sites)
            .fetch_optional(&mut **tx)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to scope inventory row: {e}")))?;
            if probe.is_none() {
                return Err(SenseiError::NotFound(format!(
                    "Inventory for product {} at location '{location}' is outside the \
                     caller's site scope",
                    stock_move.product_id
                )));
            }
            Ok(())
        };

        match stock_move.move_type.as_str() {
            "receipt" => {
                let location = match to_location.as_str() {
                    "" => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                    l => l.to_string(),
                };
                require_entitled(&mut tx, &location).await?;
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &location,
                    stock_move.quantity,
                )
                .await?;
            }
            "delivery" | "issue" => {
                let location = match from_location {
                    Some(l) if !l.is_empty() => l,
                    _ => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                };
                require_entitled(&mut tx, &location).await?;
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &location,
                    -stock_move.quantity,
                )
                .await?;
            }
            "transfer" => {
                // Hard rule (item 126): an inventory transfer must balance
                // (Σ location deltas = 0). The rule is the gate.
                crate::tps::rules::check_transfer_balance(&[
                    (stock_move.product_id, -stock_move.quantity),
                    (stock_move.product_id, stock_move.quantity),
                ])
                .map_err(|v| SenseiError::Validation(v.message().to_string()))?;
                let from = from_location.clone().unwrap_or_default();
                require_entitled(&mut tx, &from).await?;
                let to = match to_location.as_str() {
                    "" => {
                        self.resolve_stock_location(&mut tx, tenant_id, stock_move.product_id)
                            .await?
                    }
                    l => l.to_string(),
                };
                require_entitled(&mut tx, &to).await?;
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &from,
                    -stock_move.quantity,
                )
                .await?;
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
                    &to,
                    stock_move.quantity,
                )
                .await?;
            }
            "adjustment" => {
                let location = match from_location {
                    Some(l) if !l.is_empty() => l,
                    _ => to_location,
                };
                require_entitled(&mut tx, &location).await?;
                self.apply_inventory_delta(
                    &mut tx,
                    tenant_id,
                    stock_move.product_id,
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
