//! PostgreSQL-backed products service using sqlx.
//!
//! Provides product/service catalog management backed by the `products` database table.
//! Implements the [`ProductsService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::entities::Product;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{EntityId, TenantId};
use sensei_db::models::ProductModel;
use sqlx::PgPool;

use crate::products::ProductsService;

/// PostgreSQL-backed implementation of [`ProductsService`].
pub struct DatabaseProductsService {
    pool: PgPool,
}

impl DatabaseProductsService {
    /// Create a new [`DatabaseProductsService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Database row for a product, including the `max_stock_level` and `notes`
/// columns added by migration 029 (the shared [`ProductModel`] does not
/// carry them).
#[derive(Debug, Clone, sqlx::FromRow)]
struct ProductRow {
    #[sqlx(flatten)]
    model: ProductModel,
    max_stock_level: Option<f64>,
    notes: Option<String>,
}

/// Convert a database row into a domain [`Product`].
fn product_row_to_domain(r: ProductRow) -> Product {
    let m = r.model;
    Product {
        id: m.id,
        tenant_id: m.tenant_id,
        sku: m.product_number,
        name: m.name,
        description: m.description,
        category: m.category,
        product_type: m.product_type,
        unit_of_measure: m.unit_of_measure,
        standard_cost: m.standard_cost,
        selling_price: m.list_price,
        min_stock_level: m.reorder_point,
        max_stock_level: r.max_stock_level,
        current_stock: m.quantity_on_hand,
        is_active: m.is_active,
        notes: r.notes,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}

#[async_trait]
impl ProductsService for DatabaseProductsService {
    async fn create_product(&self, tenant_id: TenantId, product: Product) -> Result<Product> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, ProductRow>(
            r#"
            INSERT INTO products (id, tenant_id, product_number, name, description, category,
                                  unit_of_measure, standard_cost, list_price, quantity_on_hand,
                                  reorder_point, is_active, product_type,
                                  max_stock_level, notes, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id, tenant_id, product_number, name, description, category,
                      unit_of_measure, standard_cost, list_price, quantity_on_hand,
                      reorder_point, is_active, product_type,
                      max_stock_level, notes, created_at, updated_at
            "#,
        )
        .bind(product.id)
        .bind(tenant_id)
        .bind(&product.sku)
        .bind(&product.name)
        .bind(&product.description)
        .bind(&product.category)
        .bind(&product.unit_of_measure)
        .bind(product.standard_cost)
        .bind(product.selling_price)
        .bind(product.current_stock)
        .bind(product.min_stock_level)
        .bind(product.is_active)
        .bind(&product.product_type)
        .bind(product.max_stock_level)
        .bind(&product.notes)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create product: {e}")))?;

        Ok(product_row_to_domain(model))
    }

    async fn get_product(&self, tenant_id: TenantId, id: EntityId) -> Result<Product> {
        let model = sqlx::query_as::<_, ProductRow>(
            r#"
            SELECT id, tenant_id, product_number, name, description, category,
                   unit_of_measure, standard_cost, list_price, quantity_on_hand,
                   reorder_point, is_active, product_type,
                   max_stock_level, notes, created_at, updated_at
            FROM products
            WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get product: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Product {id} not found")))?;

        Ok(product_row_to_domain(model))
    }

    async fn list_products(
        &self,
        tenant_id: TenantId,
        category: Option<&str>,
        product_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Product>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let use_category_filter = category.is_some();
        let use_type_filter = product_type.is_some();
        let category_val = category.unwrap_or("");
        let type_val = product_type.unwrap_or("");

        // Build count query
        let count_sql = match (use_category_filter, use_type_filter) {
            (true, true) => {
                "SELECT COUNT(*) FROM products WHERE tenant_id = $1 AND category = $2 AND product_type = $3"
            }
            (true, false) => {
                "SELECT COUNT(*) FROM products WHERE tenant_id = $1 AND category = $2"
            }
            (false, true) => {
                "SELECT COUNT(*) FROM products WHERE tenant_id = $1 AND product_type = $2"
            }
            (false, false) => {
                "SELECT COUNT(*) FROM products WHERE tenant_id = $1"
            }
        };

        let total: i64 = match (use_category_filter, use_type_filter) {
            (true, true) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(category_val)
                    .bind(type_val)
                    .fetch_one(&self.pool)
                    .await
            }
            (true, false) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(category_val)
                    .fetch_one(&self.pool)
                    .await
            }
            (false, true) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .fetch_one(&self.pool)
                    .await
            }
            (false, false) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .fetch_one(&self.pool)
                    .await
            }
        }
        .map_err(|e| SenseiError::Database(format!("Failed to count products: {e}")))?;

        let total = total as usize;
        let total_pages = total.div_ceil(per_page).max(1);

        // Build data query
        let data_sql = match (use_category_filter, use_type_filter) {
            (true, true) => {
                r#"
                SELECT id, tenant_id, product_number, name, description, category,
                       unit_of_measure, standard_cost, list_price, quantity_on_hand,
                       reorder_point, is_active, product_type,
                       max_stock_level, notes, created_at, updated_at
                FROM products
                WHERE tenant_id = $1 AND category = $2 AND product_type = $3
                ORDER BY created_at DESC
                LIMIT $4 OFFSET $5
                "#
            }
            (true, false) => {
                r#"
                SELECT id, tenant_id, product_number, name, description, category,
                       unit_of_measure, standard_cost, list_price, quantity_on_hand,
                       reorder_point, is_active, product_type,
                       max_stock_level, notes, created_at, updated_at
                FROM products
                WHERE tenant_id = $1 AND category = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                "#
            }
            (false, true) => {
                r#"
                SELECT id, tenant_id, product_number, name, description, category,
                       unit_of_measure, standard_cost, list_price, quantity_on_hand,
                       reorder_point, is_active, product_type,
                       max_stock_level, notes, created_at, updated_at
                FROM products
                WHERE tenant_id = $1 AND product_type = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                "#
            }
            (false, false) => {
                r#"
                SELECT id, tenant_id, product_number, name, description, category,
                       unit_of_measure, standard_cost, list_price, quantity_on_hand,
                       reorder_point, is_active, product_type,
                       max_stock_level, notes, created_at, updated_at
                FROM products
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                "#
            }
        };

        let models: Vec<ProductRow> = match (use_category_filter, use_type_filter) {
            (true, true) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(category_val)
                    .bind(type_val)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
            (true, false) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(category_val)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
            (false, true) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
            (false, false) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
        }
        .map_err(|e| SenseiError::Database(format!("Failed to list products: {e}")))?;

        let data = models.into_iter().map(product_row_to_domain).collect();

        Ok(PaginatedResponse {
            data,
            total,
            page,
            per_page,
            total_pages,
        })
    }

    async fn update_product(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        product: Product,
    ) -> Result<Product> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, ProductRow>(
            r#"
            UPDATE products
            SET product_number = $3, name = $4, description = $5, category = $6,
                unit_of_measure = $7, standard_cost = $8, list_price = $9,
                quantity_on_hand = $10, reorder_point = $11, is_active = $12,
                product_type = $13, max_stock_level = $14, notes = $15, updated_at = $16
            WHERE id = $1 AND tenant_id = $2
            RETURNING id, tenant_id, product_number, name, description, category,
                      unit_of_measure, standard_cost, list_price, quantity_on_hand,
                      reorder_point, is_active, product_type,
                      max_stock_level, notes, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&product.sku)
        .bind(&product.name)
        .bind(&product.description)
        .bind(&product.category)
        .bind(&product.unit_of_measure)
        .bind(product.standard_cost)
        .bind(product.selling_price)
        .bind(product.current_stock)
        .bind(product.min_stock_level)
        .bind(product.is_active)
        .bind(&product.product_type)
        .bind(product.max_stock_level)
        .bind(&product.notes)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update product: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Product {id} not found")))?;

        // Verify tenant ownership.
        if model.model.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden("Cross-tenant access denied".to_string()));
        }

        Ok(product_row_to_domain(model))
    }

    async fn delete_product(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let now = Utc::now();

        let result = sqlx::query(
            r#"
            UPDATE products
            SET is_active = false, updated_at = $3
            WHERE id = $1 AND tenant_id = $2 AND is_active = true
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to delete product: {e}")))?;

        if result.rows_affected() == 0 {
            // Check if the product exists at all, to distinguish NotFound from already-inactive.
            let exists = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM products WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to check product existence: {e}")))?;

            if exists == 0 {
                return Err(SenseiError::NotFound(format!("Product {id} not found")));
            }
        }

        Ok(())
    }
}
