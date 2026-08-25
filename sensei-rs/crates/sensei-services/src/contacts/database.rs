//! PostgreSQL-backed contacts service using sqlx.
//!
//! Provides contact person management backed by the `contacts` database table.
//! Implements the [`ContactsService`] trait with real SQL queries.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::domain::entities::Contact;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{EntityId, TenantId};
use sensei_db::models::account::ContactModel;
use sqlx::PgPool;

use crate::contacts::ContactsService;

/// PostgreSQL-backed implementation of [`ContactsService`].
pub struct DatabaseContactsService {
    pool: PgPool,
}

impl DatabaseContactsService {
    /// Create a new [`DatabaseContactsService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

/// Database row for a contact, including the `department` and `is_primary`
/// columns added by migration 028 (the shared [`ContactModel`] does not
/// carry them).
#[derive(Debug, Clone, sqlx::FromRow)]
struct ContactRow {
    #[sqlx(flatten)]
    model: ContactModel,
    department: Option<String>,
    is_primary: bool,
}

/// Convert a database row into a domain [`Contact`].
fn contact_row_to_domain(r: ContactRow) -> Contact {
    let m = r.model;
    Contact {
        id: m.id,
        tenant_id: m.tenant_id,
        account_id: m.account_id,
        first_name: m.first_name,
        last_name: m.last_name,
        email: m.email.unwrap_or_default(),
        phone: m.phone,
        job_title: m.job_title,
        department: r.department,
        is_primary: r.is_primary,
        is_active: m.is_active,
        notes: m.notes,
        created_at: m.created_at,
        updated_at: m.updated_at,
    }
}

#[async_trait]
impl ContactsService for DatabaseContactsService {
    async fn create_contact(&self, tenant_id: TenantId, contact: Contact) -> Result<Contact> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, ContactRow>(
            r#"
            INSERT INTO contacts (id, tenant_id, first_name, last_name, email, phone,
                                  job_title, account_id, department, is_primary,
                                  notes, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id, tenant_id, first_name, last_name, email, phone, mobile,
                      job_title, account_id, department, is_primary,
                      notes, is_active, created_at, updated_at
            "#,
        )
        .bind(contact.id)
        .bind(tenant_id)
        .bind(&contact.first_name)
        .bind(&contact.last_name)
        .bind(&contact.email)
        .bind(&contact.phone)
        .bind(&contact.job_title)
        .bind(contact.account_id)
        .bind(&contact.department)
        .bind(contact.is_primary)
        .bind(&contact.notes)
        .bind(contact.is_active)
        .bind(now)
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to create contact: {e}")))?;

        Ok(contact_row_to_domain(model))
    }

    async fn get_contact(&self, tenant_id: TenantId, id: EntityId) -> Result<Contact> {
        let model = sqlx::query_as::<_, ContactRow>(
            r#"
            SELECT id, tenant_id, first_name, last_name, email, phone, mobile,
                   job_title, account_id, department, is_primary,
                   notes, is_active, created_at, updated_at
            FROM contacts
            WHERE id = $1 AND tenant_id = $2
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to get contact: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Contact {id} not found")))?;

        Ok(contact_row_to_domain(model))
    }

    async fn list_contacts(
        &self,
        tenant_id: TenantId,
        account_id: Option<EntityId>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Contact>> {
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let offset = (page - 1) * per_page;

        let use_account_filter = account_id.is_some();
        let account_val = account_id.unwrap_or_default();

        // Count query
        let count_sql = if use_account_filter {
            "SELECT COUNT(*) FROM contacts WHERE tenant_id = $1 AND account_id = $2"
        } else {
            "SELECT COUNT(*) FROM contacts WHERE tenant_id = $1"
        };

        let total: i64 = if use_account_filter {
            sqlx::query_scalar(count_sql)
                .bind(tenant_id)
                .bind(account_val)
                .fetch_one(&self.pool)
                .await
        } else {
            sqlx::query_scalar(count_sql)
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
        }
        .map_err(|e| SenseiError::Database(format!("Failed to count contacts: {e}")))?;

        let total = total as usize;
        let total_pages = total.div_ceil(per_page).max(1);

        // Data query
        let data_sql = if use_account_filter {
            r#"
            SELECT id, tenant_id, first_name, last_name, email, phone, mobile,
                   job_title, account_id, department, is_primary,
                   notes, is_active, created_at, updated_at
            FROM contacts
            WHERE tenant_id = $1 AND account_id = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            "#
        } else {
            r#"
            SELECT id, tenant_id, first_name, last_name, email, phone, mobile,
                   job_title, account_id, department, is_primary,
                   notes, is_active, created_at, updated_at
            FROM contacts
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            "#
        };

        let models: Vec<ContactRow> = if use_account_filter {
            sqlx::query_as(data_sql)
                .bind(tenant_id)
                .bind(account_val)
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        } else {
            sqlx::query_as(data_sql)
                .bind(tenant_id)
                .bind(per_page as i64)
                .bind(offset as i64)
                .fetch_all(&self.pool)
                .await
        }
        .map_err(|e| SenseiError::Database(format!("Failed to list contacts: {e}")))?;

        let data = models.into_iter().map(contact_row_to_domain).collect();

        Ok(PaginatedResponse {
            data,
            total,
            page,
            per_page,
            total_pages,
        })
    }

    async fn update_contact(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        contact: Contact,
    ) -> Result<Contact> {
        let now = Utc::now();

        let model = sqlx::query_as::<_, ContactRow>(
            r#"
            UPDATE contacts
            SET first_name = $3, last_name = $4, email = $5, phone = $6,
                job_title = $7, account_id = $8, department = $9, is_primary = $10,
                notes = $11, is_active = $12, updated_at = $13
            WHERE id = $1 AND tenant_id = $2
            RETURNING id, tenant_id, first_name, last_name, email, phone, mobile,
                      job_title, account_id, department, is_primary,
                      notes, is_active, created_at, updated_at
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&contact.first_name)
        .bind(&contact.last_name)
        .bind(&contact.email)
        .bind(&contact.phone)
        .bind(&contact.job_title)
        .bind(contact.account_id)
        .bind(&contact.department)
        .bind(contact.is_primary)
        .bind(&contact.notes)
        .bind(contact.is_active)
        .bind(now)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update contact: {e}")))?
        .ok_or_else(|| SenseiError::NotFound(format!("Contact {id} not found")))?;

        // Verify tenant ownership.
        if model.model.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden("Cross-tenant access denied".to_string()));
        }

        Ok(contact_row_to_domain(model))
    }

    async fn delete_contact(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let now = Utc::now();

        let result = sqlx::query(
            r#"
            UPDATE contacts
            SET is_active = false, updated_at = $3
            WHERE id = $1 AND tenant_id = $2 AND is_active = true
            "#,
        )
        .bind(id)
        .bind(tenant_id)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to delete contact: {e}")))?;

        if result.rows_affected() == 0 {
            // Check if the contact exists at all, to distinguish NotFound from already-inactive.
            let exists = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM contacts WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to check contact existence: {e}")))?;

            if exists == 0 {
                return Err(SenseiError::NotFound(format!("Contact {id} not found")));
            }
        }

        Ok(())
    }
}
