//! Authorization snapshot (sixteenth audit items 5/24): created ONCE at
//! request start and carried through HTTP → context → retrieval → cache
//! → model program → tool execution → verifier → write. A consequential
//! write verifies is_still_current before commit — closing the TOCTOU
//! gap where retrieval runs under one permission state and execution
//! under another.

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AuthzSnapshot {
    pub tenant: uuid::Uuid,
    pub principal: uuid::Uuid,
    pub policy_revision: u64,
    pub relationship_revision: u64,
    pub principal_revision: u64,
    pub scope_site: Option<uuid::Uuid>,
    pub permission_digest: [u8; 32],
}

impl AuthzSnapshot {
    /// The cache salt: a revocation (any revision bump) changes the
    /// digest and invalidates every derived cache key.
    pub fn cache_salt(&self) -> String {
        format!(
            "{}-{}-{}",
            self.policy_revision, self.relationship_revision, self.principal_revision
        )
    }

    /// TOCTOU guard: before a consequential write, re-read the current
    /// revisions and confirm nothing changed since this snapshot was
    /// created. A mismatch means the permission state moved — the write
    /// must be re-authorized, not performed.
    ///
    /// Direct SQL read, deliberately NOT a service call: sensei-services
    /// depends on sensei-auth, so a services dependency here would be
    /// circular. The authorization_revisions table is tenant-scoped and
    /// the read runs under the request's own tenant.
    pub async fn is_still_current(&self, pool: &sqlx::PgPool) -> bool {
        let row: std::result::Result<Option<(i64, i64, i64)>, sqlx::Error> = sqlx::query_as(
            "SELECT policy_revision, relationship_revision, principal_revision \
             FROM authorization_revisions WHERE tenant_id = $1",
        )
        .bind(self.tenant)
        .fetch_optional(pool)
        .await;
        match row {
            Ok(Some((policy, relationship, principal))) => {
                policy as u64 == self.policy_revision
                    && relationship as u64 == self.relationship_revision
                    && principal as u64 == self.principal_revision
            }
            _ => false, // DB unavailable or no row = NOT current (fail closed)
        }
    }
}
