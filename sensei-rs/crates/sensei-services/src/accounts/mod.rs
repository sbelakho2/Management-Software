//! Accounts/Companies domain service.
//!
//! Provides account management for customer and supplier companies.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::Account;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use std::collections::HashMap;
use tokio::sync::RwLock;

mod database;
pub use database::DatabaseAccountsService;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Account management service.
#[async_trait]
pub trait AccountsService: Send + Sync {
    /// Create a new account.
    async fn create_account(&self, tenant_id: TenantId, account: Account) -> Result<Account>;

    /// Get an account by ID.
    async fn get_account(&self, tenant_id: TenantId, id: EntityId) -> Result<Account>;

    /// List accounts with optional type filter and pagination.
    async fn list_accounts(
        &self,
        tenant_id: TenantId,
        account_type: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Account>>;

    /// Update an account.
    async fn update_account(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        account: Account,
    ) -> Result<Account>;

    /// Delete (deactivate) an account.
    async fn delete_account(&self, tenant_id: TenantId, id: EntityId) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`AccountsService`].
pub struct InMemoryAccountsService {
    accounts: RwLock<HashMap<EntityId, Account>>,
}

impl InMemoryAccountsService {
    /// Create a new empty [`InMemoryAccountsService`].
    pub fn new() -> Self {
        Self {
            accounts: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryAccountsService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl AccountsService for InMemoryAccountsService {
    async fn create_account(&self, tenant_id: TenantId, mut account: Account) -> Result<Account> {
        account.id = sensei_core::types::new_id();
        account.tenant_id = tenant_id;
        account.created_at = now();
        account.updated_at = now();
        let id = account.id;
        self.accounts.write().await.insert(id, account.clone());
        Ok(account)
    }

    async fn get_account(&self, _tenant_id: TenantId, id: EntityId) -> Result<Account> {
        let store = self.accounts.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Account {id} not found")))
    }

    async fn list_accounts(
        &self,
        tenant_id: TenantId,
        account_type: Option<&str>,
        is_active: Option<bool>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Account>> {
        let store = self.accounts.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|a| {
                a.tenant_id == tenant_id
                    && account_type.is_none_or(|t| a.account_type == t)
                    && is_active.is_none_or(|act| a.is_active == act)
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_account(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        account: Account,
    ) -> Result<Account> {
        let mut store = self.accounts.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Account {id} not found")))?;

        if existing.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        existing.name = account.name;
        existing.tax_id = account.tax_id;
        existing.email = account.email;
        existing.phone = account.phone;
        existing.address_line1 = account.address_line1;
        existing.address_line2 = account.address_line2;
        existing.city = account.city;
        existing.state = account.state;
        existing.postal_code = account.postal_code;
        existing.country = account.country;
        existing.account_type = account.account_type;
        existing.is_active = account.is_active;
        existing.notes = account.notes;
        existing.updated_at = now();

        Ok(existing.clone())
    }

    async fn delete_account(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let mut store = self.accounts.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Account {id} not found")))?;

        if existing.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        existing.is_active = false;
        existing.updated_at = now();
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use sensei_core::domain::entities::Account;
    use uuid::Uuid;

    fn make_service() -> InMemoryAccountsService {
        InMemoryAccountsService::new()
    }

    fn tenant_id() -> TenantId {
        Uuid::parse_str("11111111-1111-1111-1111-111111111111").unwrap()
    }

    fn other_tenant() -> TenantId {
        Uuid::parse_str("22222222-2222-2222-2222-222222222222").unwrap()
    }

    #[tokio::test]
    async fn test_create_and_get_account() {
        let svc = make_service();
        let tid = tenant_id();
        let account = Account::new(tid, "Acme Corp".into(), "customer".into());

        let created = svc.create_account(tid, account).await.unwrap();
        assert_eq!(created.name, "Acme Corp");
        assert_eq!(created.account_type, "customer");
        assert!(created.is_active);

        let fetched = svc.get_account(tid, created.id).await.unwrap();
        assert_eq!(fetched.name, "Acme Corp");
        assert_eq!(fetched.id, created.id);
    }

    #[tokio::test]
    async fn test_get_account_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.get_account(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_list_accounts() {
        let svc = make_service();
        let tid = tenant_id();

        let a1 = Account::new(tid, "Customer A".into(), "customer".into());
        let a2 = Account::new(tid, "Supplier B".into(), "supplier".into());
        let a3 = Account::new(tid, "Both C".into(), "both".into());

        svc.create_account(tid, a1).await.unwrap();
        svc.create_account(tid, a2).await.unwrap();
        svc.create_account(tid, a3).await.unwrap();

        // All accounts for tenant.
        let all = svc
            .list_accounts(tid, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(all.data.len(), 3);

        // Filter by type.
        let cust = svc
            .list_accounts(tid, Some("customer"), None, None, None)
            .await
            .unwrap();
        assert_eq!(cust.data.len(), 1);
        assert_eq!(cust.data[0].account_type, "customer");

        // Pagination.
        let paged = svc
            .list_accounts(tid, None, None, Some(1), Some(2))
            .await
            .unwrap();
        assert_eq!(paged.data.len(), 2);
        assert_eq!(paged.total, 3);
    }

    #[tokio::test]
    async fn test_list_accounts_tenant_isolation() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();

        svc.create_account(t1, Account::new(t1, "T1 Co".into(), "customer".into()))
            .await
            .unwrap();
        svc.create_account(t2, Account::new(t2, "T2 Inc".into(), "supplier".into()))
            .await
            .unwrap();

        let t1_list = svc.list_accounts(t1, None, None, None, None).await.unwrap();
        assert_eq!(t1_list.data.len(), 1);
        assert_eq!(t1_list.data[0].name, "T1 Co");

        let t2_list = svc.list_accounts(t2, None, None, None, None).await.unwrap();
        assert_eq!(t2_list.data.len(), 1);
        assert_eq!(t2_list.data[0].name, "T2 Inc");
    }

    #[tokio::test]
    async fn test_update_account() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc
            .create_account(tid, Account::new(tid, "Old Name".into(), "customer".into()))
            .await
            .unwrap();

        let mut updated = created.clone();
        updated.name = "New Name".into();
        updated.email = Some("new@example.com".into());

        let result = svc
            .update_account(tid, created.id, updated.clone())
            .await
            .unwrap();
        assert_eq!(result.name, "New Name");
        assert_eq!(result.email, Some("new@example.com".into()));
    }

    #[tokio::test]
    async fn test_update_account_cross_tenant_forbidden() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();
        let created = svc
            .create_account(t1, Account::new(t1, "Acme".into(), "customer".into()))
            .await
            .unwrap();

        let err = svc
            .update_account(t2, created.id, created)
            .await
            .unwrap_err();
        assert!(err.to_string().contains("Cross-tenant") || err.to_string().contains("Forbidden"));
    }

    #[tokio::test]
    async fn test_delete_account_soft_delete() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc
            .create_account(tid, Account::new(tid, "Acme".into(), "customer".into()))
            .await
            .unwrap();

        svc.delete_account(tid, created.id).await.unwrap();

        // After soft-delete, account should be inactive.
        let fetched = svc.get_account(tid, created.id).await.unwrap();
        assert!(!fetched.is_active);
    }

    #[tokio::test]
    async fn test_delete_account_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.delete_account(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_account_lifecycle() {
        let svc = make_service();
        let tid = tenant_id();

        // Create
        let a = svc
            .create_account(tid, Account::new(tid, "Lifecycle Co".into(), "both".into()))
            .await
            .unwrap();
        assert!(a.is_active);

        // List — should appear
        let list = svc
            .list_accounts(tid, None, None, None, None)
            .await
            .unwrap();
        assert_eq!(list.data.len(), 1);

        // Soft delete
        svc.delete_account(tid, a.id).await.unwrap();
        let deleted = svc.get_account(tid, a.id).await.unwrap();
        assert!(!deleted.is_active);

        // Update after soft-delete (should still work)
        let mut upd = deleted.clone();
        upd.name = "Reborn Co".into();
        let reborn = svc.update_account(tid, a.id, upd).await.unwrap();
        assert_eq!(reborn.name, "Reborn Co");
    }
}
