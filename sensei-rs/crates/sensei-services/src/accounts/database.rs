//! PostgreSQL-backed accounts service using sqlx.
//!
//! Provides account (customer/supplier) management backed by the `accounts` database table.
//! Implements the [`AccountsService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::entities::Account;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{EntityId, TenantId};
use sensei_db::models::account::AccountModel;
use sqlx::PgPool;

use crate::accounts::AccountsService;

/// PostgreSQL-backed implementation of [`AccountsService`].
pub struct DatabaseAccountsService {
    pool: PgPool,
}

impl DatabaseAccountsService {
    /// Create a new [`DatabaseAccountsService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Database row for an account, including the `tax_id` column added by
/// migration 027 (the shared [`AccountModel`] does not carry it).
#[derive(Debug, Clone, sqlx::FromRow)]
struct AccountRow {
    #[sqlx(flatten)]
    model: AccountModel,
    tax_id: Option<String>,
}

/// Convert a database row into a domain [`Account`].
fn account_row_to_domain(r: AccountRow) -> Account {
    let m = r.model;
    Account {
        id: m.id,
        tenant_id: m.tenant_id,
        name: m.name,
        tax_id: r.tax_id,
        email: m.email,
        phone: m.phone,
        address_line1: m.address_line1,
        address_line2: m.address_line2,
        city: m.city,
        state: m.state,
        postal_code: m.postal_code,
        country: m.country,
        account_type: m.account_type,
        is_active: m.status == "active",
        notes: m.notes,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}

#[async_trait]
impl AccountsService for DatabaseAccountsService {
    async fn create_account(&self, tenant_id: TenantId, account: Account) -> Result<Account> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, AccountRow>(
            r#"
            INSERT INTO accounts (id, tenant_id, name, account_type, status, phone, email,
                                  address_line1, address_line2, city, state, postal_code,
                                  country, tax_id, notes, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id, tenant_id, name, account_type, status, tier, industry, website,
                      phone, email, address_line1, address_line2, city, state, postal_code,
                      country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
            "#,
        )
        .bind(account.id)
        .bind(tenant_id)
        .bind(&account.name)
        .bind(&account.account_type)
        .bind("active")
        .bind(&account.phone)
        .bind(&account.email)
        .bind(&account.address_line1)
        .bind(&account.address_line2)
        .bind(&account.city)
        .bind(&account.state)
        .bind(&account.postal_code)
        .bind(&account.country)
        .bind(&account.tax_id)
        .bind(&account.notes)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create account: {e}")))?;

        Ok(account_row_to_domain(model))
    }

    async fn get_account(&self, tenant_id: TenantId, id: EntityId) -> Result<Account> {
        let model = sqlx::query_as::<_, AccountRow>(
            r#"
            SELECT id, tenant_id, name, account_type, status, tier, industry, website,
                   phone, email, address_line1, address_line2, city, state, postal_code,
                   country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
            FROM accounts
            WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get account: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Account {id} not found")))?;

        Ok(account_row_to_domain(model))
    }

    async fn list_accounts(
        &self,
        tenant_id: TenantId,
        account_type: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Account>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let use_type_filter = account_type.is_some();
        let use_active_filter = is_active.is_some();
        let type_val = account_type.unwrap_or("");
        let status_val = if is_active.unwrap_or(true) {
            "active"
        } else {
            "inactive"
        };

        // Count query
        let count_sql = match (use_type_filter, use_active_filter) {
            (true, true) => {
                "SELECT COUNT(*) FROM accounts WHERE tenant_id = $1 AND account_type = $2 AND status = $3"
            }
            (true, false) => {
                "SELECT COUNT(*) FROM accounts WHERE tenant_id = $1 AND account_type = $2"
            }
            (false, true) => {
                "SELECT COUNT(*) FROM accounts WHERE tenant_id = $1 AND status = $2"
            }
            (false, false) => {
                "SELECT COUNT(*) FROM accounts WHERE tenant_id = $1"
            }
        };

        let total: i64 = match (use_type_filter, use_active_filter) {
            (true, true) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .bind(status_val)
                    .fetch_one(&self.pool)
                    .await
            }
            (true, false) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .fetch_one(&self.pool)
                    .await
            }
            (false, true) => {
                sqlx::query_scalar(count_sql)
                    .bind(tenant_id)
                    .bind(status_val)
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
        .map_err(|e| SenseiError::Database(format!("Failed to count accounts: {e}")))?;

        let total = total as usize;
        let total_pages = total.div_ceil(per_page).max(1);

        // Data query
        let data_sql = match (use_type_filter, use_active_filter) {
            (true, true) => {
                r#"
                SELECT id, tenant_id, name, account_type, status, tier, industry, website,
                       phone, email, address_line1, address_line2, city, state, postal_code,
                       country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
                FROM accounts
                WHERE tenant_id = $1 AND account_type = $2 AND status = $3
                ORDER BY created_at DESC
                LIMIT $4 OFFSET $5
                "#
            }
            (true, false) => {
                r#"
                SELECT id, tenant_id, name, account_type, status, tier, industry, website,
                       phone, email, address_line1, address_line2, city, state, postal_code,
                       country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
                FROM accounts
                WHERE tenant_id = $1 AND account_type = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                "#
            }
            (false, true) => {
                r#"
                SELECT id, tenant_id, name, account_type, status, tier, industry, website,
                       phone, email, address_line1, address_line2, city, state, postal_code,
                       country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
                FROM accounts
                WHERE tenant_id = $1 AND status = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                "#
            }
            (false, false) => {
                r#"
                SELECT id, tenant_id, name, account_type, status, tier, industry, website,
                       phone, email, address_line1, address_line2, city, state, postal_code,
                       country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
                FROM accounts
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                "#
            }
        };

        let models: Vec<AccountRow> = match (use_type_filter, use_active_filter) {
            (true, true) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .bind(status_val)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
            (true, false) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(type_val)
                    .bind(per_page as i64)
                    .bind(offset as i64)
                    .fetch_all(&self.pool)
                    .await
            }
            (false, true) => {
                sqlx::query_as(data_sql)
                    .bind(tenant_id)
                    .bind(status_val)
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
        .map_err(|e| SenseiError::Database(format!("Failed to list accounts: {e}")))?;

        let data = models.into_iter().map(account_row_to_domain).collect();

        Ok(PaginatedResponse {
            data,
            total,
            page,
            per_page,
            total_pages,
        })
    }

    async fn update_account(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        account: Account,
    ) -> Result<Account> {
        let now = Utc::now();
        let status_str = if account.is_active {
            "active"
        } else {
            "inactive"
        };

        let model = sqlx::query_as::<_, AccountRow>(
            r#"
            UPDATE accounts
            SET name = $3, account_type = $4, status = $5, phone = $6, email = $7,
                address_line1 = $8, address_line2 = $9, city = $10, state = $11,
                postal_code = $12, country = $13, tax_id = $14, notes = $15, updated_at = $16
            WHERE id = $1 AND tenant_id = $2
            RETURNING id, tenant_id, name, account_type, status, tier, industry, website,
                      phone, email, address_line1, address_line2, city, state, postal_code,
                      country, annual_revenue, parent_id, tax_id, notes, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&account.name)
        .bind(&account.account_type)
        .bind(status_str)
        .bind(&account.phone)
        .bind(&account.email)
        .bind(&account.address_line1)
        .bind(&account.address_line2)
        .bind(&account.city)
        .bind(&account.state)
        .bind(&account.postal_code)
        .bind(&account.country)
        .bind(&account.tax_id)
        .bind(&account.notes)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update account: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Account {id} not found")))?;

        // Verify tenant ownership.
        if model.model.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        Ok(account_row_to_domain(model))
    }

    async fn delete_account(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let now = Utc::now();

        let result = sqlx::query(
            r#"
            UPDATE accounts
            SET status = 'inactive', updated_at = $3
            WHERE id = $1 AND tenant_id = $2 AND status != 'inactive'
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to delete account: {e}")))?;

        if result.rows_affected() == 0 {
            // Check if the account exists at all, to distinguish NotFound from already-inactive.
            let exists = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM accounts WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to check account existence: {e}"))
            })?;

            if exists == 0 {
                return Err(SenseiError::NotFound(format!("Account {id} not found")));
            }
        }

        Ok(())
    }
}
