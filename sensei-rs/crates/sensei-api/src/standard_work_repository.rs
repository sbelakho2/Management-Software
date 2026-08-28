//! Typed standard-work repository (item 12): controlled documents are
//! relational with the version relationship enforced by the DB, and
//! optimistic concurrency is ATOMIC in SQL (the version increment happens
//! in the UPDATE's WHERE). EntityStore remains the dev/test fallback.

use crate::stores::{StandardWorkDocument, StandardWorkVersion};
use chrono::{DateTime, Utc};

/// SQL row for standard_work_documents (migration 085).
#[derive(sqlx::FromRow)]
struct SwRow {
    id: Uuid,
    tenant_id: Uuid,
    title: String,
    document_number: String,
    area: String,
    process: String,
    current_version: i32,
    status: String,
    steps: serde_json::Value,
    required_skills: serde_json::Value,
    cycle_time_seconds: Option<i32>,
    takt_time_seconds: Option<i32>,
    quality_checks: serde_json::Value,
    safety_notes: serde_json::Value,
    tools_required: serde_json::Value,
    materials_required: serde_json::Value,
    attachments: serde_json::Value,
    approved_by: Option<Uuid>,
    approved_at: Option<DateTime<Utc>>,
    version: i64,
    created_by: Uuid,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
}

fn map_sw_row(r: SwRow) -> StandardWorkDocument {
    StandardWorkDocument {
        id: r.id,
        tenant_id: r.tenant_id,
        title: r.title,
        document_number: r.document_number,
        area: r.area,
        process: r.process,
        current_version: r.current_version,
        status: r
            .status
            .parse::<crate::stores::SwStatus>()
            .unwrap_or(crate::stores::SwStatus::Draft),
        steps: serde_json::from_value(r.steps).unwrap_or_default(),
        required_skills: serde_json::from_value(r.required_skills).unwrap_or_default(),
        cycle_time_seconds: r.cycle_time_seconds,
        takt_time_seconds: r.takt_time_seconds,
        quality_checks: serde_json::from_value(r.quality_checks).unwrap_or_default(),
        safety_notes: serde_json::from_value(r.safety_notes).unwrap_or_default(),
        tools_required: serde_json::from_value(r.tools_required).unwrap_or_default(),
        materials_required: serde_json::from_value(r.materials_required).unwrap_or_default(),
        attachments: serde_json::from_value(r.attachments).unwrap_or_default(),
        approved_by: r.approved_by,
        approved_at: r.approved_at,
        version: r.version.max(0) as u64,
        created_by: r.created_by,
        created_at: r.created_at,
        updated_at: r.updated_at,
    }
}
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

#[derive(Clone)]
pub struct StandardWorkRepository {
    pool: Option<sqlx::PgPool>,
    memory: Arc<RwLock<HashMap<Uuid, StandardWorkDocument>>>,
    memory_versions: Arc<RwLock<HashMap<Uuid, StandardWorkVersion>>>,
}

impl StandardWorkRepository {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory: Arc::new(RwLock::new(HashMap::new())),
            memory_versions: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn attach_pool(mut self, pool: sqlx::PgPool) -> Self {
        self.pool = Some(pool);
        self
    }

    /// Put a document; when `expected_version` is Some, the row updates
    /// ONLY if it still holds that version (atomic CAS) and increments.
    pub async fn put(
        &self,
        doc: &StandardWorkDocument,
        expected_version: Option<u64>,
    ) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            let row = sqlx::query_as::<_, (Uuid, i64)>(
                "INSERT INTO standard_work_documents \\
                    (id, tenant_id, title, document_number, area, process, current_version, \\
                     status, steps, required_skills, cycle_time_seconds, takt_time_seconds, \\
                     quality_checks, safety_notes, tools_required, materials_required, \\
                     attachments, approved_by, approved_at, version, created_by, created_at, updated_at) \\
                 VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,NOW()) \\
                 ON CONFLICT (tenant_id, document_number) DO UPDATE \\
                 SET title=$3, area=$5, process=$6, steps=$9, required_skills=$10, \\
                     cycle_time_seconds=$11, takt_time_seconds=$12, quality_checks=$13, \\
                     safety_notes=$14, tools_required=$15, materials_required=$16, \\
                     attachments=$17, approved_by=$18, approved_at=$19, updated_at=NOW(), \\
                     version = standard_work_documents.version + 1 \\
                 WHERE standard_work_documents.id = $1 \\
                   AND ($24::bigint IS NULL OR standard_work_documents.version = $24) \\
                 RETURNING id, version",
            )
            .bind(doc.id)
            .bind(doc.tenant_id)
            .bind(&doc.title)
            .bind(&doc.document_number)
            .bind(&doc.area)
            .bind(&doc.process)
            .bind(doc.current_version)
            .bind(format!("{:?}", doc.status).to_lowercase())
            .bind(serde_json::to_value(&doc.steps).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(serde_json::to_value(&doc.required_skills).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(doc.cycle_time_seconds)
            .bind(doc.takt_time_seconds)
            .bind(serde_json::to_value(&doc.quality_checks).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(serde_json::to_value(&doc.safety_notes).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(serde_json::to_value(&doc.tools_required).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(serde_json::to_value(&doc.materials_required).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(serde_json::to_value(&doc.attachments).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(doc.approved_by)
            .bind(doc.approved_at)
            .bind(doc.version as i64)
            .bind(doc.created_by)
            .bind(doc.created_at)
            .bind(expected_version.map(|v| v as i64))
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("Standard-work persist failed: {e}"))?;
            if row.is_none() {
                return Err(format!(
                    "VERSION_CONFLICT: standard work {} was modified concurrently (expected version {:?})",
                    doc.id, expected_version
                ));
            }
            return Ok(());
        }
        if let Some(expected) = expected_version {
            let guard = self.memory.read().await;
            if let Some(existing) = guard.get(&doc.id) {
                if existing.version != expected {
                    return Err(format!(
                        "VERSION_CONFLICT: standard work {} was modified concurrently",
                        doc.id
                    ));
                }
            }
            drop(guard);
        }
        let mut guard = self.memory.write().await;
        let mut doc = doc.clone();
        doc.version += 1;
        guard.insert(doc.id, doc);
        Ok(())
    }

    pub async fn get(&self, tenant_id: Uuid, id: Uuid) -> Result<Option<StandardWorkDocument>, String> {
        if let Some(pool) = &self.pool {
            let row: Option<SwRow> = sqlx::query_as(
                "SELECT id, tenant_id, title, document_number, area, process, current_version, \
                        status::text, steps, required_skills, cycle_time_seconds, takt_time_seconds, \
                        quality_checks, safety_notes, tools_required, materials_required, \
                        attachments, approved_by, approved_at, version, created_by, \
                        created_at, updated_at \
                 FROM standard_work_documents WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("Standard-work read failed: {e}"))?;
            return Ok(row.map(map_sw_row));
        }
        Ok(self.memory.read().await.get(&id).cloned())
    }

    pub async fn list(&self, tenant_id: Uuid) -> Result<Vec<StandardWorkDocument>, String> {
        if let Some(pool) = &self.pool {
            let rows: Vec<SwRow> = sqlx::query_as(
                "SELECT id, tenant_id, title, document_number, area, process, current_version, \
                        status::text, steps, required_skills, cycle_time_seconds, takt_time_seconds, \
                        quality_checks, safety_notes, tools_required, materials_required, \
                        attachments, approved_by, approved_at, version, created_by, \
                        created_at, updated_at \
                 FROM standard_work_documents WHERE tenant_id = $1 ORDER BY updated_at DESC",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Standard-work list failed: {e}"))?;
            return Ok(rows.into_iter().map(map_sw_row).collect());
        }
        let mut out: Vec<StandardWorkDocument> = self
            .memory
            .read()
            .await
            .values()
            .filter(|d| d.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
        Ok(out)
    }

    pub async fn put_version(&self, v: &StandardWorkVersion) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO standard_work_versions \\
                    (id, document_id, tenant_id, version_number, snapshot, change_notes, created_by, created_at) \\
                 VALUES ($1,$2,$3,$4,$5,$6,$7,$8) \\
                 ON CONFLICT (document_id, version_number) DO NOTHING",
            )
            .bind(v.id)
            .bind(v.document_id)
            .bind(v.tenant_id)
            .bind(v.version_number)
            .bind(&v.snapshot)
            .bind(&v.change_notes)
            .bind(v.created_by)
            .bind(v.created_at)
            .execute(pool)
            .await
            .map_err(|e| format!("Standard-work version persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_versions.write().await.insert(v.id, v.clone());
        Ok(())
    }

    pub async fn list_versions(
        &self,
        tenant_id: Uuid,
        document_id: Uuid,
    ) -> Result<Vec<StandardWorkVersion>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct VerRow {
                id: Uuid,
                document_id: Uuid,
                tenant_id: Uuid,
                version_number: i32,
                snapshot: serde_json::Value,
                change_notes: Option<String>,
                created_by: Uuid,
                created_at: DateTime<Utc>,
            }
            let rows: Vec<VerRow> = sqlx::query_as(
                "SELECT id, document_id, tenant_id, version_number, snapshot, change_notes, \
                        created_by, created_at \
                 FROM standard_work_versions \
                 WHERE tenant_id = $1 AND document_id = $2 ORDER BY version_number DESC",
            )
            .bind(tenant_id)
            .bind(document_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("Standard-work versions read failed: {e}"))?;
            return Ok(rows
                .into_iter()
                .map(|r| StandardWorkVersion {
                    id: r.id,
                    document_id: r.document_id,
                    tenant_id: r.tenant_id,
                    version_number: r.version_number,
                    snapshot: r.snapshot,
                    change_notes: r.change_notes,
                    created_by: r.created_by,
                    created_at: r.created_at,
                })
                .collect());
        }
        let mut out: Vec<StandardWorkVersion> = self
            .memory_versions
            .read()
            .await
            .values()
            .filter(|v| v.tenant_id == tenant_id && v.document_id == document_id)
            .cloned()
            .collect();
        out.sort_by_key(|a| std::cmp::Reverse(a.version_number));
        Ok(out)
    }
}
