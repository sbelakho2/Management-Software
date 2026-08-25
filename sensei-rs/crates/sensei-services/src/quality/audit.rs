//! Audit services: Audit evidence packing, audit trail timeline,
//! and quality certification gate.
//!
//! Ported from Python's `audit_evidence.py`, `audit_trail_timeline.py`,
//! and `quality_certification_gate.py`.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{EntityId, TenantId, new_id, now};

use super::models::{
    Audit, AuditAccessLevel, AuditChangeType, AuditChecklistItem, AuditEntityType,
    AuditEntry, AuditFieldType, AuditFinding,
    AuditPackage, AuditStatus, AuditType,
    CertificationCheckResult, DiffResult, EvidenceRecord, EvidenceType,
    FieldChange, FindingSeverity, FindingStatus, PackageStatus,
    RelatedEntity, Timeline, TimelineFilter, TimelineGroup,
};

use ring::digest::{Context, SHA256};
use hmac::{Hmac, Mac};
use sha2::Sha256;

// HMAC-SHA256 type alias
type HmacSha256 = Hmac<Sha256>;

/// Audit evidence service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait AuditEvidenceService: Send + Sync {
    /// Create an evidence record with SHA-256 content hash.
    async fn create_evidence(
        &self,
        tenant_id: TenantId,
        audit_id: EntityId,
        evidence_type: EvidenceType,
        title: String,
        description: String,
        content: &[u8],
        file_path: Option<String>,
        created_by: Option<EntityId>,
    ) -> Result<EvidenceRecord>;

    /// List evidence for an audit.
    async fn list_evidence(&self, audit_id: EntityId) -> Result<Vec<EvidenceRecord>>;

    /// Verify evidence integrity by recomputing SHA-256 hash.
    async fn verify_evidence_integrity(
        &self,
        evidence_id: EntityId,
        content: &[u8],
    ) -> Result<bool>;

    /// Create an evidence package.
    async fn create_package(
        &self,
        tenant_id: TenantId,
        audit_id: EntityId,
        title: String,
    ) -> Result<AuditPackage>;

    /// Add evidence to a package.
    async fn add_evidence_to_package(
        &self,
        package_id: EntityId,
        evidence_id: EntityId,
    ) -> Result<AuditPackage>;

    /// Seal a package with HMAC-SHA256 signature.
    async fn seal_package(&self, package_id: EntityId) -> Result<AuditPackage>;

    /// Verify package integrity.
    async fn verify_package_integrity(&self, package_id: EntityId) -> Result<bool>;

    /// List packages for an audit.
    async fn list_packages(&self, audit_id: EntityId) -> Result<Vec<AuditPackage>>;

    /// Export a package as a portable JSON value.
    async fn export_package(&self, package_id: EntityId) -> Result<serde_json::Value>;
}

/// Audit trail timeline service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait AuditTrailService: Send + Sync {
    /// Register field metadata for automatic diff generation.
    async fn register_field(&self, field_name: &str, label: &str, field_type: AuditFieldType);

    /// Calculate diff between old and new values.
    async fn calculate_diff(
        &self,
        old_values: &serde_json::Value,
        new_values: &serde_json::Value,
    ) -> DiffResult;

    /// Record a create event.
    async fn record_create(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        created_by: Option<EntityId>,
        metadata: Option<serde_json::Value>,
    ) -> Result<AuditEntry>;

    /// Record an update event with field-level diff.
    async fn record_update(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        old_values: &serde_json::Value,
        new_values: &serde_json::Value,
        changed_by: Option<EntityId>,
        metadata: Option<serde_json::Value>,
    ) -> Result<AuditEntry>;

    /// Record a status change event.
    async fn record_status_change(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        old_status: &str,
        new_status: &str,
        changed_by: Option<EntityId>,
    ) -> Result<AuditEntry>;

    /// Record a delete event.
    async fn record_delete(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        deleted_by: Option<EntityId>,
    ) -> Result<AuditEntry>;

    /// Record a comment event.
    async fn record_comment(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        comment: &str,
        commented_by: Option<EntityId>,
    ) -> Result<AuditEntry>;

    /// Record an approval event.
    async fn record_approval(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        approved_by: Option<EntityId>,
        notes: Option<&str>,
    ) -> Result<AuditEntry>;

    /// Record a rejection event.
    async fn record_rejection(
        &self,
        tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        rejected_by: Option<EntityId>,
        reason: &str,
    ) -> Result<AuditEntry>;

    /// Get the timeline for an entity.
    async fn get_entity_timeline(
        &self,
        entity_id: EntityId,
        filter: Option<TimelineFilter>,
    ) -> Result<Timeline>;

    /// Get entity history.
    async fn get_entity_history(
        &self,
        entity_id: EntityId,
        limit: u64,
    ) -> Result<Vec<AuditEntry>>;

    /// Get user activity.
    async fn get_user_activity(
        &self,
        user_id: EntityId,
        limit: u64,
    ) -> Result<Vec<AuditEntry>>;

    /// Clean up old entries.
    async fn cleanup_old_entries(&self, retention_days: u64) -> Result<u64>;

    /// Get audit trail statistics.
    async fn get_statistics(&self) -> Result<serde_json::Value>;
}

/// Quality certification gate trait.
#[async_trait]
pub trait CertificationGate: Send + Sync {
    /// Check if a user is certified to perform inspections.
    async fn assert_user_can_record_inspection(
        &self,
        tenant_id: TenantId,
        user_id: Option<EntityId>,
        station_id: Option<u32>,
        product_id: Option<u32>,
    ) -> Result<CertificationCheckResult>;
}

// ---------------------------------------------------------------------------
// Audit Management (Schedule, Checklist, Findings)
// ---------------------------------------------------------------------------

/// Audit management service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait AuditManagementService: Send + Sync {
    /// Schedule an audit.
    async fn schedule_audit(
        &self,
        tenant_id: TenantId,
        audit_type: AuditType,
        title: String,
        scope: String,
        area: String,
        auditor_id: Option<EntityId>,
        lead_auditor_id: Option<EntityId>,
        scheduled_date: Option<DateTime<Utc>>,
    ) -> Result<Audit>;

    /// Start an audit.
    async fn start_audit(&self, audit_id: EntityId) -> Result<Audit>;

    /// Complete an audit.
    async fn complete_audit(&self, audit_id: EntityId) -> Result<Audit>;

    /// Get an audit by ID.
    async fn get_audit(&self, audit_id: EntityId) -> Result<Audit>;

    /// List audits with optional status filter.
    async fn list_audits(
        &self,
        tenant_id: TenantId,
        status: Option<AuditStatus>,
        audit_type: Option<AuditType>,
    ) -> Result<Vec<Audit>>;

    /// Answer a checklist item in an audit.
    async fn answer_checklist_item(
        &self,
        audit_id: EntityId,
        question: String,
        expected_evidence: String,
        is_conforming: Option<bool>,
        observations: Option<String>,
    ) -> Result<AuditChecklistItem>;

    /// Add a finding to an audit.
    async fn add_finding(
        &self,
        audit_id: EntityId,
        severity: FindingSeverity,
        description: String,
        clause: Option<String>,
        area: Option<String>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<AuditFinding>;

    /// Implement a finding action.
    async fn implement_finding_action(
        &self,
        finding_id: EntityId,
        implementation_notes: String,
    ) -> Result<AuditFinding>;

    /// Verify and close a finding.
    async fn verify_close_finding(
        &self,
        finding_id: EntityId,
        verified_by: EntityId,
        verification_notes: String,
    ) -> Result<AuditFinding>;

    /// List audits due.
    async fn list_audits_due(&self, tenant_id: TenantId, as_of: Option<DateTime<Utc>>) -> Result<Vec<Audit>>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// SHA-256 hash helper.
fn sha256_hash(data: &[u8]) -> String {
    let mut context = Context::new(&SHA256);
    context.update(data);
    let digest = context.finish();
    hex::encode(digest.as_ref())
}

/// HMAC-SHA256 sign helper.
fn hmac_sha256_sign(key: &[u8], data: &[u8]) -> Result<String> {
    let mut mac = HmacSha256::new_from_slice(key)
        .map_err(|e| SenseiError::Internal(format!("HMAC key error: {e}")))?;
    mac.update(data);
    let result = mac.finalize();
    Ok(hex::encode(result.into_bytes().as_slice()))
}

/// Combined in-memory audit services.
pub struct InMemoryAuditService {
    evidence: tokio::sync::RwLock<Vec<EvidenceRecord>>,
    packages: tokio::sync::RwLock<Vec<AuditPackage>>,
    audit_entries: tokio::sync::RwLock<Vec<AuditEntry>>,
    audits: tokio::sync::RwLock<Vec<Audit>>,
    checklists: tokio::sync::RwLock<Vec<AuditChecklistItem>>,
    findings: tokio::sync::RwLock<Vec<AuditFinding>>,
    field_metadata: tokio::sync::RwLock<std::collections::HashMap<String, (String, AuditFieldType)>>,
    signing_key: Vec<u8>,
    audit_counter: tokio::sync::RwLock<u64>,
    finding_counter: tokio::sync::RwLock<u64>,
}

impl InMemoryAuditService {
    /// Create a new empty service with an optional signing key.
    ///
    /// When no key is passed explicitly, the `AUDIT_SIGNING_KEY` environment
    /// variable is used. The built-in development default is only accepted in
    /// development builds; in release builds it logs a prominent warning so
    /// deployments cannot silently rely on a public key.
    pub fn new(signing_key: Option<Vec<u8>>) -> Self {
        let signing_key = match signing_key {
            Some(k) => k,
            None => match std::env::var("AUDIT_SIGNING_KEY") {
                Ok(k) if !k.is_empty() => k.into_bytes(),
                _ => {
                    let dev_default = b"default-signing-key-change-in-production".to_vec();
                    if cfg!(debug_assertions) {
                        tracing::warn!("Using built-in development audit signing key");
                    } else {
                        tracing::error!(
                            "AUDIT_SIGNING_KEY is not set; audit package signatures are signed \
                             with the well-known development key. Set AUDIT_SIGNING_KEY in production."
                        );
                    }
                    dev_default
                }
            },
        };
        Self {
            evidence: tokio::sync::RwLock::new(Vec::new()),
            packages: tokio::sync::RwLock::new(Vec::new()),
            audit_entries: tokio::sync::RwLock::new(Vec::new()),
            audits: tokio::sync::RwLock::new(Vec::new()),
            checklists: tokio::sync::RwLock::new(Vec::new()),
            findings: tokio::sync::RwLock::new(Vec::new()),
            field_metadata: tokio::sync::RwLock::new(std::collections::HashMap::new()),
            signing_key,
            audit_counter: tokio::sync::RwLock::new(0),
            finding_counter: tokio::sync::RwLock::new(0),
        }
    }
}

impl Default for InMemoryAuditService {
    fn default() -> Self {
        Self::new(None)
    }
}

#[async_trait]
impl AuditEvidenceService for InMemoryAuditService {
    async fn create_evidence(
        &self,
        _tenant_id: TenantId,
        audit_id: EntityId,
        evidence_type: EvidenceType,
        title: String,
        description: String,
        content: &[u8],
        file_path: Option<String>,
        created_by: Option<EntityId>,
    ) -> Result<EvidenceRecord> {
        let content_hash = sha256_hash(content);

        let record = EvidenceRecord {
            id: new_id(),
            audit_id,
            evidence_type,
            title,
            description,
            content_hash,
            file_path,
            created_by,
            created_at: now(),
        };

        self.evidence.write().await.push(record.clone());
        Ok(record)
    }

    async fn list_evidence(&self, audit_id: EntityId) -> Result<Vec<EvidenceRecord>> {
        let evidence = self.evidence.read().await;
        Ok(evidence.iter().filter(|e| e.audit_id == audit_id).cloned().collect())
    }

    async fn verify_evidence_integrity(
        &self,
        evidence_id: EntityId,
        content: &[u8],
    ) -> Result<bool> {
        let evidence = self.evidence.read().await;
        let record = evidence
            .iter()
            .find(|e| e.id == evidence_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Evidence {evidence_id} not found")))?;

        let computed_hash = sha256_hash(content);
        Ok(computed_hash == record.content_hash)
    }

    async fn create_package(
        &self,
        _tenant_id: TenantId,
        audit_id: EntityId,
        title: String,
    ) -> Result<AuditPackage> {
        let pkg = AuditPackage {
            id: new_id(),
            audit_id,
            title,
            status: PackageStatus::Draft,
            evidence_ids: Vec::new(),
            package_hash: None,
            signature: None,
            sealed_at: None,
            created_at: now(),
        };

        self.packages.write().await.push(pkg.clone());
        Ok(pkg)
    }

    async fn add_evidence_to_package(
        &self,
        package_id: EntityId,
        evidence_id: EntityId,
    ) -> Result<AuditPackage> {
        // Verify evidence exists
        let evidence = self.evidence.read().await;
        evidence
            .iter()
            .find(|e| e.id == evidence_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Evidence {evidence_id} not found")))?;
        drop(evidence);

        let mut packages = self.packages.write().await;
        let pkg = packages
            .iter_mut()
            .find(|p| p.id == package_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Package {package_id} not found")))?;

        if pkg.status != PackageStatus::Draft {
            return Err(SenseiError::Validation(
                "Cannot add evidence to a sealed or exported package".to_string(),
            ));
        }

        if !pkg.evidence_ids.contains(&evidence_id) {
            pkg.evidence_ids.push(evidence_id);
        }

        Ok(pkg.clone())
    }

    async fn seal_package(&self, package_id: EntityId) -> Result<AuditPackage> {
        let mut packages = self.packages.write().await;
        let pkg = packages
            .iter_mut()
            .find(|p| p.id == package_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Package {package_id} not found")))?;

        if pkg.status != PackageStatus::Draft {
            return Err(SenseiError::Validation("Package is already sealed or exported".to_string()));
        }

        // Compute package hash from sorted evidence IDs
        let mut sorted_ids = pkg.evidence_ids.clone();
        sorted_ids.sort();
        let canonical = serde_json::json!({
            "package_id": pkg.id,
            "audit_id": pkg.audit_id,
            "evidence_ids": sorted_ids,
            "title": pkg.title,
        });
        let canonical_bytes = serde_json::to_vec(&canonical)
            .map_err(|e| SenseiError::Serialization(e.to_string()))?;

        let package_hash = sha256_hash(&canonical_bytes);
        let signature = hmac_sha256_sign(&self.signing_key, &canonical_bytes)?;

        pkg.status = PackageStatus::Sealed;
        pkg.package_hash = Some(package_hash);
        pkg.signature = Some(signature);
        pkg.sealed_at = Some(now());

        Ok(pkg.clone())
    }

    async fn verify_package_integrity(&self, package_id: EntityId) -> Result<bool> {
        let packages = self.packages.read().await;
        let pkg = packages
            .iter()
            .find(|p| p.id == package_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Package {package_id} not found")))?;

        if pkg.status == PackageStatus::Draft {
            return Err(SenseiError::Validation("Package has not been sealed yet".to_string()));
        }

        let package_hash = pkg.package_hash.as_ref()
            .ok_or_else(|| SenseiError::NotFound("Package hash not found".to_string()))?;

        let signature = pkg.signature.as_ref()
            .ok_or_else(|| SenseiError::NotFound("Package signature not found".to_string()))?;

        // Recompute hash
        let mut sorted_ids = pkg.evidence_ids.clone();
        sorted_ids.sort();
        let canonical = serde_json::json!({
            "package_id": pkg.id,
            "audit_id": pkg.audit_id,
            "evidence_ids": sorted_ids,
            "title": pkg.title,
        });
        let canonical_bytes = serde_json::to_vec(&canonical)
            .map_err(|e| SenseiError::Serialization(e.to_string()))?;

        let recomputed_hash = sha256_hash(&canonical_bytes);
        if &recomputed_hash != package_hash {
            return Ok(false);
        }

        // Verify HMAC signature
        let computed_sig = hmac_sha256_sign(&self.signing_key, &canonical_bytes)?;
        Ok(&computed_sig == signature)
    }

    async fn list_packages(&self, audit_id: EntityId) -> Result<Vec<AuditPackage>> {
        let packages = self.packages.read().await;
        Ok(packages.iter().filter(|p| p.audit_id == audit_id).cloned().collect())
    }

    async fn export_package(&self, package_id: EntityId) -> Result<serde_json::Value> {
        let packages = self.packages.read().await;
        let pkg = packages
            .iter()
            .find(|p| p.id == package_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Package {package_id} not found")))?;

        if pkg.status == PackageStatus::Draft {
            return Err(SenseiError::Validation("Cannot export a draft package".to_string()));
        }

        let evidence_list = {
            let evidence = self.evidence.read().await;
            evidence
                .iter()
                .filter(|e| pkg.evidence_ids.contains(&e.id))
                .map(|e| serde_json::json!({
                    "id": e.id,
                    "title": e.title,
                    "evidence_type": format!("{:?}", e.evidence_type),
                    "content_hash": e.content_hash,
                    "created_at": e.created_at,
                }))
                .collect::<Vec<_>>()
        };

        Ok(serde_json::json!({
            "package": {
                "id": pkg.id,
                "audit_id": pkg.audit_id,
                "title": pkg.title,
                "status": format!("{:?}", pkg.status),
                "package_hash": pkg.package_hash,
                "signature": pkg.signature,
                "sealed_at": pkg.sealed_at,
                "created_at": pkg.created_at,
            },
            "evidence": evidence_list,
            "evidence_count": evidence_list.len(),
        }))
    }
}

#[async_trait]
impl AuditTrailService for InMemoryAuditService {
    async fn register_field(&self, field_name: &str, label: &str, field_type: AuditFieldType) {
        let mut metadata = self.field_metadata.write().await;
        metadata.insert(field_name.to_string(), (label.to_string(), field_type));
    }

    async fn calculate_diff(
        &self,
        old_values: &serde_json::Value,
        new_values: &serde_json::Value,
    ) -> DiffResult {
        let metadata = self.field_metadata.read().await;
        let mut field_changes = Vec::new();

        if let (Some(old_map), Some(new_map)) = (old_values.as_object(), new_values.as_object()) {
            // Find changed fields
            for (key, new_val) in new_map {
                let old_val = old_map.get(key);
                if old_val != Some(new_val) {
                    let (label, field_type) = metadata.get(key)
                        .cloned()
                        .unwrap_or_else(|| (key.clone(), AuditFieldType::Text));

                    field_changes.push(FieldChange {
                        field_name: label,
                        old_value: old_val.map(|v| v.to_string()),
                        new_value: Some(new_val.to_string()),
                        field_type,
                    });
                }
            }

            // Find removed fields
            for (key, old_val) in old_map {
                if !new_map.contains_key(key) {
                    let (label, field_type) = metadata.get(key)
                        .cloned()
                        .unwrap_or_else(|| (key.clone(), AuditFieldType::Text));

                    field_changes.push(FieldChange {
                        field_name: label,
                        old_value: Some(old_val.to_string()),
                        new_value: None,
                        field_type,
                    });
                }
            }
        }

        let change_count = field_changes.len();
        DiffResult {
            has_changes: change_count > 0,
            field_changes,
            change_count,
        }
    }

    async fn record_create(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        created_by: Option<EntityId>,
        metadata: Option<serde_json::Value>,
    ) -> Result<AuditEntry> {
        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Create,
            format!("Created {}", entity_summary),
            Vec::new(),
            Vec::new(),
            created_by,
            AuditAccessLevel::Public,
            metadata,
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_update(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        old_values: &serde_json::Value,
        new_values: &serde_json::Value,
        changed_by: Option<EntityId>,
        metadata: Option<serde_json::Value>,
    ) -> Result<AuditEntry> {
        let diff = self.calculate_diff(old_values, new_values).await;
        if !diff.has_changes {
            return Err(SenseiError::Validation("No changes detected".to_string()));
        }

        let summary = format!(
            "Updated {} — {} field(s) changed",
            entity_summary,
            diff.change_count
        );

        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Update,
            summary,
            diff.field_changes,
            Vec::new(),
            changed_by,
            AuditAccessLevel::Public,
            metadata,
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_status_change(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        old_status: &str,
        new_status: &str,
        changed_by: Option<EntityId>,
    ) -> Result<AuditEntry> {
        let field_changes = vec![
            FieldChange {
                field_name: "status".to_string(),
                old_value: Some(old_status.to_string()),
                new_value: Some(new_status.to_string()),
                field_type: AuditFieldType::Enum,
            },
        ];

        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::StatusChange,
            format!("{} status changed: {} → {}", entity_summary, old_status, new_status),
            field_changes,
            Vec::new(),
            changed_by,
            AuditAccessLevel::Public,
            None,
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_delete(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        entity_summary: String,
        deleted_by: Option<EntityId>,
    ) -> Result<AuditEntry> {
        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Delete,
            format!("Deleted {}", entity_summary),
            Vec::new(),
            Vec::new(),
            deleted_by,
            AuditAccessLevel::Internal,
            None,
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_comment(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        comment: &str,
        commented_by: Option<EntityId>,
    ) -> Result<AuditEntry> {
        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Comment,
            format!("Comment added: {:.100}", comment),
            Vec::new(),
            Vec::new(),
            commented_by,
            AuditAccessLevel::Public,
            Some(serde_json::json!({"comment": comment})),
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_approval(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        approved_by: Option<EntityId>,
        notes: Option<&str>,
    ) -> Result<AuditEntry> {
        let summary = match notes {
            Some(n) => format!("Approved: {:.100}", n),
            None => "Approved".to_string(),
        };

        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Approval,
            summary,
            Vec::new(),
            Vec::new(),
            approved_by,
            AuditAccessLevel::Public,
            notes.map(|n| serde_json::json!({"notes": n})),
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn record_rejection(
        &self,
        _tenant_id: TenantId,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        rejected_by: Option<EntityId>,
        reason: &str,
    ) -> Result<AuditEntry> {
        let entry = self._build_entry(
            entity_id,
            entity_type,
            AuditChangeType::Rejection,
            format!("Rejected: {:.200}", reason),
            Vec::new(),
            Vec::new(),
            rejected_by,
            AuditAccessLevel::Public,
            Some(serde_json::json!({"reason": reason})),
        );

        self.audit_entries.write().await.push(entry.clone());
        Ok(entry)
    }

    async fn get_entity_timeline(
        &self,
        entity_id: EntityId,
        filter: Option<TimelineFilter>,
    ) -> Result<Timeline> {
        let entries = self.audit_entries.read().await;
        let mut filtered: Vec<AuditEntry> = entries
            .iter()
            .filter(|e| e.entity_id == entity_id)
            .cloned()
            .collect();

        // Apply additional filters
        if let Some(f) = filter {
            if let Some(entity_types) = f.entity_types {
                filtered.retain(|e| entity_types.contains(&e.entity_type));
            }
            if let Some(change_types) = f.change_types {
                filtered.retain(|e| change_types.contains(&e.change_type));
            }
            if let Some(user_id) = f.user_id {
                filtered.retain(|e| e.changed_by == Some(user_id));
            }
            if let Some(date_from) = f.date_from {
                filtered.retain(|e| e.occurred_at >= date_from);
            }
            if let Some(date_to) = f.date_to {
                filtered.retain(|e| e.occurred_at <= date_to);
            }
            if let Some(ref search) = f.search_text {
                let search_lower = search.to_lowercase();
                filtered.retain(|e| e.summary.to_lowercase().contains(&search_lower));
            }
        }

        // Sort most recent first
        filtered.sort_by_key(|b| std::cmp::Reverse(b.occurred_at));

        let total_count = filtered.len() as u64;

        // Group by date
        let groups = self._group_by_date(&filtered);

        Ok(Timeline {
            groups,
            total_count,
            has_more: false,
        })
    }

    async fn get_entity_history(
        &self,
        entity_id: EntityId,
        limit: u64,
    ) -> Result<Vec<AuditEntry>> {
        let entries = self.audit_entries.read().await;
        let mut entity_entries: Vec<AuditEntry> = entries
            .iter()
            .filter(|e| e.entity_id == entity_id)
            .cloned()
            .collect();

        entity_entries.sort_by_key(|b| std::cmp::Reverse(b.occurred_at));
        entity_entries.truncate(limit as usize);

        Ok(entity_entries)
    }

    async fn get_user_activity(
        &self,
        user_id: EntityId,
        limit: u64,
    ) -> Result<Vec<AuditEntry>> {
        let entries = self.audit_entries.read().await;
        let mut user_entries: Vec<AuditEntry> = entries
            .iter()
            .filter(|e| e.changed_by == Some(user_id))
            .cloned()
            .collect();

        user_entries.sort_by_key(|b| std::cmp::Reverse(b.occurred_at));
        user_entries.truncate(limit as usize);

        Ok(user_entries)
    }

    async fn cleanup_old_entries(&self, retention_days: u64) -> Result<u64> {
        let cutoff = now() - chrono::Duration::days(retention_days as i64);
        let mut entries = self.audit_entries.write().await;
        let before = entries.len();

        entries.retain(|e| e.occurred_at >= cutoff);

        let removed = (before - entries.len()) as u64;
        Ok(removed)
    }

    async fn get_statistics(&self) -> Result<serde_json::Value> {
        let entries = self.audit_entries.read().await;
        let audits = self.audits.read().await;

        let mut type_counts: std::collections::HashMap<String, u64> = std::collections::HashMap::new();
        for entry in entries.iter() {
            let key = format!("{:?}", entry.change_type);
            *type_counts.entry(key).or_default() += 1;
        }

        Ok(serde_json::json!({
            "total_entries": entries.len(),
            "total_audits": audits.len(),
            "by_change_type": type_counts,
        }))
    }
}

impl InMemoryAuditService {
    #[allow(clippy::too_many_arguments)]
    fn _build_entry(
        &self,
        entity_id: EntityId,
        entity_type: AuditEntityType,
        change_type: AuditChangeType,
        summary: String,
        field_changes: Vec<FieldChange>,
        related_entities: Vec<RelatedEntity>,
        changed_by: Option<EntityId>,
        access_level: AuditAccessLevel,
        metadata: Option<serde_json::Value>,
    ) -> AuditEntry {
        AuditEntry {
            id: new_id(),
            entity_id,
            entity_type,
            change_type,
            summary,
            field_changes,
            related_entities,
            changed_by,
            access_level,
            metadata,
            occurred_at: now(),
        }
    }

    fn _group_by_date(&self, entries: &[AuditEntry]) -> Vec<TimelineGroup> {
        let mut groups: std::collections::BTreeMap<String, Vec<AuditEntry>> = std::collections::BTreeMap::new();

        for entry in entries {
            let date = entry.occurred_at.date_naive();
            let today = chrono::Utc::now().date_naive();
            let duration = today - date;
            let days_ago = duration.num_days();

            let label = match days_ago {
                0 => "Today".to_string(),
                1 => "Yesterday".to_string(),
                d if d <= 7 => format!("{} days ago", d),
                _ => date.format("%B %d, %Y").to_string(),
            };

            groups.entry(label).or_default().push(entry.clone());
        }

        groups
            .into_iter()
            .map(|(label, entries)| TimelineGroup {
                label,
                date: now(), // approximate
                entries,
            })
            .collect()
    }
}

// ---------------------------------------------------------------------------
// Certification Gate
// ---------------------------------------------------------------------------

/// A user certification record used by the in-memory certification gate.
#[derive(Debug, Clone)]
pub struct UserCertification {
    /// The skill or certification type ID.
    pub skill_id: u32,
    /// Optional inspection type this certification covers.
    pub inspection_type: Option<String>,
    /// When the certification expires (None = never expires).
    pub expires_at: Option<chrono::DateTime<chrono::Utc>>,
}

/// In-memory certification gate that checks stored user certifications.
///
/// Maintains an internal map of user → certifications and verifies that the
/// user holds a valid (non-expired) certification before allowing inspection
/// recording. If no certifications are registered for a user, the gate denies
/// access by default.
pub struct InMemoryCertificationGate {
    certifications: tokio::sync::RwLock<std::collections::HashMap<EntityId, Vec<UserCertification>>>,
}

impl InMemoryCertificationGate {
    /// Create a new empty certification gate.
    pub fn new() -> Self {
        Self {
            certifications: tokio::sync::RwLock::new(std::collections::HashMap::new()),
        }
    }

    /// Register a certification for a user.
    pub async fn register_certification(&self, user_id: EntityId, cert: UserCertification) {
        self.certifications
            .write()
            .await
            .entry(user_id)
            .or_default()
            .push(cert);
    }

    /// List all certifications for a user.
    pub async fn list_certifications(&self, user_id: EntityId) -> Vec<UserCertification> {
        self.certifications
            .read()
            .await
            .get(&user_id)
            .cloned()
            .unwrap_or_default()
    }
}

impl Default for InMemoryCertificationGate {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl CertificationGate for InMemoryCertificationGate {
    async fn assert_user_can_record_inspection(
        &self,
        _tenant_id: TenantId,
        user_id: Option<EntityId>,
        _station_id: Option<u32>,
        _product_id: Option<u32>,
    ) -> Result<CertificationCheckResult> {
        let user_id = match user_id {
            Some(uid) => uid,
            None => {
                return Ok(CertificationCheckResult {
                    is_allowed: false,
                    required_skill_ids: Vec::new(),
                    missing_skill_ids: Vec::new(),
                    message: Some("No user ID provided — cannot verify certifications.".to_string()),
                });
            }
        };

        let certs = self.certifications.read().await;
        let user_certs = match certs.get(&user_id) {
            Some(c) => c,
            None => {
                return Ok(CertificationCheckResult {
                    is_allowed: false,
                    required_skill_ids: Vec::new(),
                    missing_skill_ids: Vec::new(),
                    message: Some(format!(
                        "User {user_id} has no certifications on file. \
                         Register a certification before recording inspections."
                    )),
                });
            }
        };

        let now = chrono::Utc::now();
        let all_skill_ids: Vec<u32> = user_certs.iter().map(|c| c.skill_id).collect();
        let valid: Vec<&UserCertification> = user_certs
            .iter()
            .filter(|c| c.expires_at.is_none_or(|exp| exp > now))
            .collect();

        if valid.is_empty() {
            let expired_skills: Vec<u32> = user_certs
                .iter()
                .filter(|c| c.expires_at.is_some_and(|exp| exp <= now))
                .map(|c| c.skill_id)
                .collect();

            return Ok(CertificationCheckResult {
                is_allowed: false,
                required_skill_ids: all_skill_ids,
                missing_skill_ids: expired_skills,
                message: Some(format!(
                    "All certifications for user {user_id} have expired. \
                     Renew at least one certification to record inspections."
                )),
            });
        }

        let valid_skill_ids: Vec<u32> = valid.iter().map(|c| c.skill_id).collect();
        let missing: Vec<u32> = all_skill_ids
            .iter()
            .filter(|sid| !valid_skill_ids.contains(sid))
            .copied()
            .collect();

        let missing_count = missing.len();
        let valid_count = valid_skill_ids.len();
        Ok(CertificationCheckResult {
            is_allowed: true,
            required_skill_ids: all_skill_ids,
            missing_skill_ids: missing,
            message: if missing_count == 0 {
                None
            } else {
                Some(format!(
                    "User {user_id} has {valid_count} valid and {missing_count} expired certification(s).",
                ))
            },
        })
    }
}

// ---------------------------------------------------------------------------
// Audit Management (In-Memory)
// ---------------------------------------------------------------------------

#[async_trait]
impl AuditManagementService for InMemoryAuditService {
    async fn schedule_audit(
        &self,
        _tenant_id: TenantId,
        audit_type: AuditType,
        title: String,
        scope: String,
        area: String,
        auditor_id: Option<EntityId>,
        lead_auditor_id: Option<EntityId>,
        scheduled_date: Option<DateTime<Utc>>,
    ) -> Result<Audit> {
        let mut counter = self.audit_counter.write().await;
        *counter += 1;
        let audit_number = format!("AUD-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter);

        let audit = Audit {
            id: new_id(),
            audit_number,
            audit_type,
            status: AuditStatus::Scheduled,
            title,
            scope,
            area,
            auditor_id,
            lead_auditor_id,
            scheduled_date,
            start_date: None,
            completion_date: None,
            checklist_items: Vec::new(),
            created_at: now(),
            updated_at: now(),
        };

        self.audits.write().await.push(audit.clone());
        Ok(audit)
    }

    async fn start_audit(&self, audit_id: EntityId) -> Result<Audit> {
        let mut audits = self.audits.write().await;
        let audit = audits
            .iter_mut()
            .find(|a| a.id == audit_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Audit {audit_id} not found")))?;

        if audit.status != AuditStatus::Scheduled && audit.status != AuditStatus::Planned {
            return Err(SenseiError::Validation(
                format!("Cannot start audit {audit_id}: status is {:?}", audit.status),
            ));
        }

        audit.status = AuditStatus::InProgress;
        audit.start_date = Some(now());
        audit.updated_at = now();

        Ok(audit.clone())
    }

    async fn complete_audit(&self, audit_id: EntityId) -> Result<Audit> {
        let mut audits = self.audits.write().await;
        let audit = audits
            .iter_mut()
            .find(|a| a.id == audit_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Audit {audit_id} not found")))?;

        if audit.status != AuditStatus::InProgress {
            return Err(SenseiError::Validation(
                format!("Cannot complete audit {audit_id}: status is {:?}", audit.status),
            ));
        }

        audit.status = AuditStatus::Completed;
        audit.completion_date = Some(now());
        audit.updated_at = now();

        Ok(audit.clone())
    }

    async fn get_audit(&self, audit_id: EntityId) -> Result<Audit> {
        self.audits
            .read()
            .await
            .iter()
            .find(|a| a.id == audit_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("Audit {audit_id} not found")))
    }

    async fn list_audits(
        &self,
        _tenant_id: TenantId,
        status: Option<AuditStatus>,
        audit_type: Option<AuditType>,
    ) -> Result<Vec<Audit>> {
        let audits = self.audits.read().await;
        Ok(audits
            .iter()
            .filter(|a| status.is_none_or(|s| a.status == s))
            .filter(|a| audit_type.is_none_or(|t| a.audit_type == t))
            .cloned()
            .collect())
    }

    async fn answer_checklist_item(
        &self,
        audit_id: EntityId,
        question: String,
        expected_evidence: String,
        is_conforming: Option<bool>,
        observations: Option<String>,
    ) -> Result<AuditChecklistItem> {
        // Verify audit exists
        self.get_audit(audit_id).await?;

        let item = AuditChecklistItem {
            id: new_id(),
            audit_id,
            question,
            expected_evidence,
            is_conforming,
            observations,
        };

        self.checklists.write().await.push(item.clone());

        // Update audit checklist
        let mut audits = self.audits.write().await;
        if let Some(audit) = audits.iter_mut().find(|a| a.id == audit_id) {
            audit.checklist_items.push(item.clone());
            audit.updated_at = now();
        }

        Ok(item)
    }

    async fn add_finding(
        &self,
        audit_id: EntityId,
        severity: FindingSeverity,
        description: String,
        clause: Option<String>,
        area: Option<String>,
        due_date: Option<DateTime<Utc>>,
    ) -> Result<AuditFinding> {
        // Verify audit exists
        self.get_audit(audit_id).await?;

        let mut counter = self.finding_counter.write().await;
        *counter += 1;
        let finding_number = format!("F-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter);

        let finding = AuditFinding {
            id: new_id(),
            audit_id,
            finding_number,
            severity,
            status: FindingStatus::Open,
            description,
            clause,
            area,
            implementation_notes: None,
            verified_by: None,
            verification_notes: None,
            due_date,
            created_at: now(),
            updated_at: now(),
        };

        self.findings.write().await.push(finding.clone());
        Ok(finding)
    }

    async fn implement_finding_action(
        &self,
        finding_id: EntityId,
        implementation_notes: String,
    ) -> Result<AuditFinding> {
        let mut findings = self.findings.write().await;
        let finding = findings
            .iter_mut()
            .find(|f| f.id == finding_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Finding {finding_id} not found")))?;

        finding.status = FindingStatus::Implemented;
        finding.implementation_notes = Some(implementation_notes);
        finding.updated_at = now();

        Ok(finding.clone())
    }

    async fn verify_close_finding(
        &self,
        finding_id: EntityId,
        verified_by: EntityId,
        verification_notes: String,
    ) -> Result<AuditFinding> {
        let mut findings = self.findings.write().await;
        let finding = findings
            .iter_mut()
            .find(|f| f.id == finding_id)
            .ok_or_else(|| SenseiError::NotFound(format!("Finding {finding_id} not found")))?;

        finding.status = FindingStatus::Closed;
        finding.verified_by = Some(verified_by);
        finding.verification_notes = Some(verification_notes);
        finding.updated_at = now();

        Ok(finding.clone())
    }

    async fn list_audits_due(&self, _tenant_id: TenantId, as_of: Option<DateTime<Utc>>) -> Result<Vec<Audit>> {
        let as_of_date = as_of.unwrap_or_else(now);
        let audits = self.audits.read().await;
        Ok(audits
            .iter()
            .filter(|a| {
                a.scheduled_date.is_some_and(|d| d <= as_of_date)
                    && (a.status == AuditStatus::Scheduled || a.status == AuditStatus::Planned)
            })
            .cloned()
            .collect())
    }
}
