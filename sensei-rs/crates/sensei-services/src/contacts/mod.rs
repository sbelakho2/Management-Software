//! Contacts domain service.
//!
//! Provides contact person management linked to accounts.
//! Uses an in-memory store backed by a `HashMap` for development and testing.

use async_trait::async_trait;
use sensei_core::domain::entities::Contact;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use sensei_core::types::{now, EntityId, TenantId};
use std::collections::HashMap;
use tokio::sync::RwLock;

mod database;
pub use database::DatabaseContactsService;

// ---------------------------------------------------------------------------
// Trait
// ---------------------------------------------------------------------------

/// Contact management service.
#[async_trait]
pub trait ContactsService: Send + Sync {
    /// Create a new contact.
    async fn create_contact(&self, tenant_id: TenantId, contact: Contact) -> Result<Contact>;

    /// Get a contact by ID.
    async fn get_contact(&self, tenant_id: TenantId, id: EntityId) -> Result<Contact>;

    /// List contacts with optional account filter and pagination.
    async fn list_contacts(
        &self,
        tenant_id: TenantId,
        account_id: Option<EntityId>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Contact>>;

    /// Update a contact.
    async fn update_contact(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        contact: Contact,
    ) -> Result<Contact>;

    /// Delete (deactivate) a contact.
    async fn delete_contact(&self, tenant_id: TenantId, id: EntityId) -> Result<()>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// In-memory implementation of [`ContactsService`].
pub struct InMemoryContactsService {
    contacts: RwLock<HashMap<EntityId, Contact>>,
}

impl InMemoryContactsService {
    /// Create a new empty [`InMemoryContactsService`].
    pub fn new() -> Self {
        Self {
            contacts: RwLock::new(HashMap::new()),
        }
    }
}

impl Default for InMemoryContactsService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ContactsService for InMemoryContactsService {
    async fn create_contact(&self, tenant_id: TenantId, mut contact: Contact) -> Result<Contact> {
        contact.id = sensei_core::types::new_id();
        contact.tenant_id = tenant_id;
        contact.created_at = now();
        contact.updated_at = now();
        let id = contact.id;
        self.contacts.write().await.insert(id, contact.clone());
        Ok(contact)
    }

    async fn get_contact(&self, _tenant_id: TenantId, id: EntityId) -> Result<Contact> {
        let store = self.contacts.read().await;
        store
            .get(&id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Contact {id} not found")))
    }

    async fn list_contacts(
        &self,
        tenant_id: TenantId,
        account_id: Option<EntityId>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Contact>> {
        let store = self.contacts.read().await;
        let items: Vec<_> = store
            .values()
            .filter(|c| {
                c.tenant_id == tenant_id && account_id.is_none_or(|aid| c.account_id == Some(aid))
            })
            .cloned()
            .collect();
        Ok(PaginatedResponse::new(items, page, per_page))
    }

    async fn update_contact(
        &self,
        tenant_id: TenantId,
        id: EntityId,
        contact: Contact,
    ) -> Result<Contact> {
        let mut store = self.contacts.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Contact {id} not found")))?;

        if existing.tenant_id != tenant_id {
            return Err(SenseiError::Forbidden(
                "Cross-tenant access denied".to_string(),
            ));
        }

        existing.first_name = contact.first_name;
        existing.last_name = contact.last_name;
        existing.email = contact.email;
        existing.phone = contact.phone;
        existing.job_title = contact.job_title;
        existing.department = contact.department;
        existing.is_primary = contact.is_primary;
        existing.is_active = contact.is_active;
        existing.notes = contact.notes;
        existing.account_id = contact.account_id;
        existing.updated_at = now();

        Ok(existing.clone())
    }

    async fn delete_contact(&self, tenant_id: TenantId, id: EntityId) -> Result<()> {
        let mut store = self.contacts.write().await;
        let existing = store
            .get_mut(&id)
            .ok_or_else(|| SenseiError::NotFound(format!("Contact {id} not found")))?;

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
    use sensei_core::domain::entities::Contact;
    use uuid::Uuid;

    fn make_service() -> InMemoryContactsService {
        InMemoryContactsService::new()
    }

    fn tenant_id() -> TenantId {
        Uuid::parse_str("11111111-1111-1111-1111-111111111111").unwrap()
    }

    fn other_tenant() -> TenantId {
        Uuid::parse_str("22222222-2222-2222-2222-222222222222").unwrap()
    }

    fn sample_contact(tid: TenantId) -> Contact {
        Contact::new(tid, "John".into(), "Doe".into(), "john@example.com".into())
    }

    #[tokio::test]
    async fn test_create_and_get_contact() {
        let svc = make_service();
        let tid = tenant_id();
        let contact = sample_contact(tid);

        let created = svc.create_contact(tid, contact).await.unwrap();
        assert_eq!(created.first_name, "John");
        assert_eq!(created.last_name, "Doe");
        assert_eq!(created.email, "john@example.com");
        assert!(created.is_active);

        let fetched = svc.get_contact(tid, created.id).await.unwrap();
        assert_eq!(fetched.email, "john@example.com");
    }

    #[tokio::test]
    async fn test_get_contact_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.get_contact(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_list_contacts() {
        let svc = make_service();
        let tid = tenant_id();
        let aid = Uuid::new_v4();

        let mut c1 = sample_contact(tid);
        c1.account_id = Some(aid);
        let mut c2 = sample_contact(tid);
        c2.first_name = "Jane".into();
        c2.account_id = Some(aid);
        let mut c3 = sample_contact(tid);
        c3.email = "other@example.com".into();
        c3.account_id = None;

        svc.create_contact(tid, c1).await.unwrap();
        svc.create_contact(tid, c2).await.unwrap();
        svc.create_contact(tid, c3).await.unwrap();

        // All contacts for tenant.
        let all = svc.list_contacts(tid, None, None, None).await.unwrap();
        assert_eq!(all.data.len(), 3);

        // Filter by account_id.
        let filtered = svc.list_contacts(tid, Some(aid), None, None).await.unwrap();
        assert_eq!(filtered.data.len(), 2);

        // Pagination.
        let paged = svc
            .list_contacts(tid, None, Some(1), Some(2))
            .await
            .unwrap();
        assert_eq!(paged.data.len(), 2);
        assert_eq!(paged.total, 3);
    }

    #[tokio::test]
    async fn test_list_contacts_tenant_isolation() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();

        svc.create_contact(t1, sample_contact(t1)).await.unwrap();
        svc.create_contact(t2, sample_contact(t2)).await.unwrap();

        let t1_list = svc.list_contacts(t1, None, None, None).await.unwrap();
        assert_eq!(t1_list.data.len(), 1);

        let t2_list = svc.list_contacts(t2, None, None, None).await.unwrap();
        assert_eq!(t2_list.data.len(), 1);
    }

    #[tokio::test]
    async fn test_update_contact() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc.create_contact(tid, sample_contact(tid)).await.unwrap();

        let mut upd = created.clone();
        upd.first_name = "Jane".into();
        upd.job_title = Some("Engineer".into());

        let result = svc.update_contact(tid, created.id, upd).await.unwrap();
        assert_eq!(result.first_name, "Jane");
        assert_eq!(result.job_title, Some("Engineer".into()));
    }

    #[tokio::test]
    async fn test_update_contact_cross_tenant_forbidden() {
        let svc = make_service();
        let t1 = tenant_id();
        let t2 = other_tenant();
        let created = svc.create_contact(t1, sample_contact(t1)).await.unwrap();

        let err = svc
            .update_contact(t2, created.id, created)
            .await
            .unwrap_err();
        assert!(err.to_string().contains("Cross-tenant") || err.to_string().contains("Forbidden"));
    }

    #[tokio::test]
    async fn test_delete_contact_soft_delete() {
        let svc = make_service();
        let tid = tenant_id();
        let created = svc.create_contact(tid, sample_contact(tid)).await.unwrap();

        svc.delete_contact(tid, created.id).await.unwrap();

        let fetched = svc.get_contact(tid, created.id).await.unwrap();
        assert!(!fetched.is_active);
    }

    #[tokio::test]
    async fn test_delete_contact_not_found() {
        let svc = make_service();
        let tid = tenant_id();
        let err = svc.delete_contact(tid, Uuid::new_v4()).await.unwrap_err();
        assert!(err.to_string().contains("not found"));
    }

    #[tokio::test]
    async fn test_contact_lifecycle() {
        let svc = make_service();
        let tid = tenant_id();

        let c = svc.create_contact(tid, sample_contact(tid)).await.unwrap();
        assert!(c.is_active);

        svc.delete_contact(tid, c.id).await.unwrap();
        let deleted = svc.get_contact(tid, c.id).await.unwrap();
        assert!(!deleted.is_active);

        // Re-activate via update.
        let mut upd = deleted.clone();
        upd.is_active = true;
        let reactivated = svc.update_contact(tid, c.id, upd).await.unwrap();
        assert!(reactivated.is_active);
    }
}
