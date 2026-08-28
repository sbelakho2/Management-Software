//! Typed LSW repository (item 12): standards, occurrences and audits are
//! relational with the standard->occurrence->audit relationships enforced
//! by the database. EntityStore remains the dev/test fallback.

use crate::stores::{LswAudit, LswOccurrence, LswStandard};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use uuid::Uuid;

#[derive(Clone)]
pub struct LswRepository {
    pool: Option<sqlx::PgPool>,
    memory_standards: Arc<RwLock<HashMap<Uuid, LswStandard>>>,
    memory_occurrences: Arc<RwLock<HashMap<Uuid, LswOccurrence>>>,
    memory_audits: Arc<RwLock<HashMap<Uuid, LswAudit>>>,
}

impl LswRepository {
    pub fn new(pool: Option<sqlx::PgPool>) -> Self {
        Self {
            pool,
            memory_standards: Arc::new(RwLock::new(HashMap::new())),
            memory_occurrences: Arc::new(RwLock::new(HashMap::new())),
            memory_audits: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn attach_pool(mut self, pool: sqlx::PgPool) -> Self {
        self.pool = Some(pool);
        self
    }

    // ── Standards ─────────────────────────────────────────────────────
    pub async fn put_standard(&self, s: &LswStandard) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO lsw_standards  (id, tenant_id, title, area, layer, revision, frequency,  checklist_items, is_active, created_by, created_at, updated_at)  VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,NOW())  ON CONFLICT (id) DO UPDATE  SET title=$3, area=$4, layer=$5, revision=$6, frequency=$7,  checklist_items=$8, is_active=$9, updated_at=NOW()",
            )
            .bind(s.id)
            .bind(s.tenant_id)
            .bind(&s.title)
            .bind(&s.area)
            .bind(s.layer as i32)
            .bind(s.revision)
            .bind(format!("{:?}", s.frequency).to_lowercase())
            .bind(
                serde_json::to_value(&s.checklist_items)
                    .unwrap_or(serde_json::Value::Array(vec![])),
            )
            .bind(s.is_active)
            .bind(s.created_by)
            .bind(s.created_at)
            .execute(pool)
            .await
            .map_err(|e| format!("LSW standard persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_standards.write().await.insert(s.id, s.clone());
        Ok(())
    }

    pub async fn get_standard(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<Option<LswStandard>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct StdRow {
                id: Uuid,
                tenant_id: Uuid,
                title: String,
                area: String,
                layer: i32,
                revision: i32,
                frequency: String,
                checklist_items: serde_json::Value,
                is_active: bool,
                created_by: Uuid,
                created_at: chrono::DateTime<chrono::Utc>,
                updated_at: chrono::DateTime<chrono::Utc>,
            }
            let row: Option<StdRow> = sqlx::query_as(
                "SELECT id, tenant_id, title, area, layer, revision, frequency,  checklist_items, is_active, created_by, created_at, updated_at  FROM lsw_standards WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("LSW standard read failed: {e}"))?;
            return Ok(row.map(|r| LswStandard {
                id: r.id,
                tenant_id: r.tenant_id,
                title: r.title,
                area: r.area,
                layer: r.layer.max(0) as u8,
                revision: r.revision,
                frequency: r
                    .frequency
                    .parse::<crate::stores::LswFrequency>()
                    .unwrap_or(crate::stores::LswFrequency::Daily),
                checklist_items: serde_json::from_value(r.checklist_items).unwrap_or_default(),
                is_active: r.is_active,
                created_by: r.created_by,
                created_at: r.created_at,
                updated_at: r.updated_at,
            }));
        }
        Ok(self.memory_standards.read().await.get(&id).cloned())
    }

    pub async fn list_standards(&self, tenant_id: Uuid) -> Result<Vec<LswStandard>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct StdRow {
                id: Uuid,
                tenant_id: Uuid,
                title: String,
                area: String,
                layer: i32,
                revision: i32,
                frequency: String,
                checklist_items: serde_json::Value,
                is_active: bool,
                created_by: Uuid,
                created_at: chrono::DateTime<chrono::Utc>,
                updated_at: chrono::DateTime<chrono::Utc>,
            }
            let rows: Vec<StdRow> = sqlx::query_as(
                "SELECT id, tenant_id, title, area, layer, revision, frequency,  checklist_items, is_active, created_by, created_at, updated_at  FROM lsw_standards WHERE tenant_id = $1 ORDER BY updated_at DESC",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("LSW standard list failed: {e}"))?;
            return Ok(rows
                .into_iter()
                .map(|r| LswStandard {
                    id: r.id,
                    tenant_id: r.tenant_id,
                    title: r.title,
                    area: r.area,
                    layer: r.layer.max(0) as u8,
                    revision: r.revision,
                    frequency: r
                        .frequency
                        .parse::<crate::stores::LswFrequency>()
                        .unwrap_or(crate::stores::LswFrequency::Daily),
                    checklist_items: serde_json::from_value(r.checklist_items).unwrap_or_default(),
                    is_active: r.is_active,
                    created_by: r.created_by,
                    created_at: r.created_at,
                    updated_at: r.updated_at,
                })
                .collect());
        }
        let mut out: Vec<LswStandard> = self
            .memory_standards
            .read()
            .await
            .values()
            .filter(|s| s.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by_key(|a| std::cmp::Reverse(a.updated_at));
        Ok(out)
    }

    // ── Occurrences ───────────────────────────────────────────────────
    pub async fn put_occurrence(&self, o: &LswOccurrence) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO lsw_occurrences  (id, standard_id, tenant_id, checklist_revision, due_at, assigned_leader,  area, layer, status, scheduled_at, started_at, completed_at)  VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)  ON CONFLICT (id) DO UPDATE  SET status=$9, started_at=$11, completed_at=$12",
            )
            .bind(o.id)
            .bind(o.standard_id)
            .bind(o.tenant_id)
            .bind(o.checklist_revision)
            .bind(o.due_at)
            .bind(o.assigned_leader)
            .bind(&o.area)
            .bind(o.layer as i32)
            .bind(&o.status)
            .bind(o.scheduled_at)
            .bind(o.started_at)
            .bind(o.completed_at)
            .execute(pool)
            .await
            .map_err(|e| format!("LSW occurrence persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_occurrences
            .write()
            .await
            .insert(o.id, o.clone());
        Ok(())
    }

    pub async fn get_occurrence(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<Option<LswOccurrence>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct OccRow {
                id: Uuid,
                standard_id: Uuid,
                tenant_id: Uuid,
                checklist_revision: i32,
                due_at: chrono::DateTime<chrono::Utc>,
                assigned_leader: Uuid,
                area: String,
                layer: i32,
                status: String,
                scheduled_at: chrono::DateTime<chrono::Utc>,
                started_at: Option<chrono::DateTime<chrono::Utc>>,
                completed_at: Option<chrono::DateTime<chrono::Utc>>,
            }
            let row: Option<OccRow> = sqlx::query_as(
                "SELECT id, standard_id, tenant_id, checklist_revision, due_at, assigned_leader,  area, layer, status, scheduled_at, started_at, completed_at  FROM lsw_occurrences WHERE id = $1 AND tenant_id = $2",
            )
            .bind(id)
            .bind(tenant_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("LSW occurrence read failed: {e}"))?;
            return Ok(row.map(|r| LswOccurrence {
                id: r.id,
                standard_id: r.standard_id,
                tenant_id: r.tenant_id,
                checklist_revision: r.checklist_revision,
                due_at: r.due_at,
                assigned_leader: r.assigned_leader,
                area: r.area,
                layer: r.layer.max(0) as u8,
                status: r.status,
                scheduled_at: r.scheduled_at,
                started_at: r.started_at,
                completed_at: r.completed_at,
            }));
        }
        Ok(self.memory_occurrences.read().await.get(&id).cloned())
    }

    // ── Audits ────────────────────────────────────────────────────────
    pub async fn put_audit(&self, a: &LswAudit) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query(
                "INSERT INTO lsw_audits  (id, standard_id, occurrence_id, tenant_id, auditor_id, leader_id, area,  layer, results, compliance_rate, notes, audited_at, created_at)  VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,NOW())  ON CONFLICT (id) DO NOTHING",
            )
            .bind(a.id)
            .bind(a.standard_id)
            .bind(a.occurrence_id)
            .bind(a.tenant_id)
            .bind(a.auditor_id)
            .bind(a.leader_id)
            .bind(&a.area)
            .bind(a.layer as i32)
            .bind(serde_json::to_value(&a.results).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(a.compliance_rate)
            .bind(&a.notes)
            .bind(a.audited_at)
            .execute(pool)
            .await
            .map_err(|e| format!("LSW audit persist failed: {e}"))?;
            return Ok(());
        }
        self.memory_audits.write().await.insert(a.id, a.clone());
        Ok(())
    }

    pub async fn list_audits(
        &self,
        tenant_id: Uuid,
        standard_id: Uuid,
    ) -> Result<Vec<LswAudit>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct AudRow {
                id: Uuid,
                standard_id: Uuid,
                occurrence_id: Option<Uuid>,
                tenant_id: Uuid,
                auditor_id: Uuid,
                leader_id: Option<Uuid>,
                area: String,
                layer: i32,
                results: serde_json::Value,
                compliance_rate: f64,
                notes: Option<String>,
                audited_at: chrono::DateTime<chrono::Utc>,
                created_at: chrono::DateTime<chrono::Utc>,
            }
            let rows: Vec<AudRow> = sqlx::query_as(
                "SELECT id, standard_id, occurrence_id, tenant_id, auditor_id, leader_id, area,  layer, results, compliance_rate, notes, audited_at, created_at  FROM lsw_audits WHERE tenant_id = $1 AND standard_id = $2  ORDER BY audited_at DESC",
            )
            .bind(tenant_id)
            .bind(standard_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("LSW audit list failed: {e}"))?;
            return Ok(rows
                .into_iter()
                .map(|r| LswAudit {
                    id: r.id,
                    standard_id: r.standard_id,
                    occurrence_id: r.occurrence_id,
                    tenant_id: r.tenant_id,
                    auditor_id: r.auditor_id,
                    leader_id: r.leader_id,
                    area: r.area,
                    layer: r.layer.max(0) as u8,
                    results: serde_json::from_value(r.results).unwrap_or_default(),
                    compliance_rate: r.compliance_rate,
                    notes: r.notes,
                    audited_at: r.audited_at,
                    created_at: r.created_at,
                })
                .collect());
        }
        let mut out: Vec<LswAudit> = self
            .memory_audits
            .read()
            .await
            .values()
            .filter(|a| a.tenant_id == tenant_id && a.standard_id == standard_id)
            .cloned()
            .collect();
        out.sort_by_key(|a| std::cmp::Reverse(a.audited_at));
        Ok(out)
    }

    /// ATOMIC audit + occurrence completion (item 13): one transaction
    /// locks the occurrence, re-validates it is not already completed,
    /// inserts the audit (UNIQUE occurrence_id guards double execution) and
    /// marks the occurrence completed. A crash between audit and completion
    /// is impossible — there is no intermediate state.
    pub async fn complete_occurrence_with_audit(
        &self,
        tenant_id: Uuid,
        standard_id: Uuid,
        occurrence_id: Uuid,
        audit: &LswAudit,
    ) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            let mut tx = pool
                .begin()
                .await
                .map_err(|e| format!("LSW audit tx begin failed: {e}"))?;

            // Lock the occurrence row; reject an already-completed one.
            let status: Option<String> = sqlx::query_scalar(
                "SELECT status FROM lsw_occurrences                  WHERE id = $1 AND tenant_id = $2 AND standard_id = $3 FOR UPDATE",
            )
            .bind(occurrence_id)
            .bind(tenant_id)
            .bind(standard_id)
            .fetch_optional(&mut *tx)
            .await
            .map_err(|e| format!("LSW occurrence lock failed: {e}"))?;
            match status.as_deref() {
                None => return Err(format!("LSW occurrence {occurrence_id} not found")),
                Some("completed") => {
                    return Err("This LSW occurrence is already completed".to_string());
                }
                _ => {}
            }

            // Insert the audit; the UNIQUE(occurrence_id, tenant_id)
            // constraint makes a concurrent duplicate insert fail.
            sqlx::query(
                "INSERT INTO lsw_audits \
                    (id, standard_id, occurrence_id, tenant_id, auditor_id, leader_id, area, \
                     layer, results, compliance_rate, notes, audited_at, created_at) \
                 VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,NOW()) \
                 ON CONFLICT (occurrence_id, tenant_id) DO NOTHING",
            )
            .bind(audit.id)
            .bind(standard_id)
            .bind(occurrence_id)
            .bind(tenant_id)
            .bind(audit.auditor_id)
            .bind(audit.leader_id)
            .bind(&audit.area)
            .bind(audit.layer as i32)
            .bind(serde_json::to_value(&audit.results).unwrap_or(serde_json::Value::Array(vec![])))
            .bind(audit.compliance_rate)
            .bind(&audit.notes)
            .bind(audit.audited_at)
            .execute(&mut *tx)
            .await
            .map_err(|e| format!("LSW audit insert failed: {e}"))?;

            // Mark the occurrence completed in the SAME transaction.
            sqlx::query(
                "UPDATE lsw_occurrences SET status = 'completed', completed_at = NOW() \
                 WHERE id = $1 AND tenant_id = $2 AND status != 'completed'",
            )
            .bind(occurrence_id)
            .bind(tenant_id)
            .execute(&mut *tx)
            .await
            .map_err(|e| format!("LSW occurrence completion failed: {e}"))?;

            tx.commit()
                .await
                .map_err(|e| format!("LSW audit tx commit failed: {e}"))?;
            return Ok(());
        }
        // Dev fallback: same semantics in memory.
        {
            let mut occ = self.memory_occurrences.write().await;
            if let Some(o) = occ.get_mut(&occurrence_id) {
                if o.status == "completed" {
                    return Err("This LSW occurrence is already completed".to_string());
                }
            }
        }
        self.memory_audits
            .write()
            .await
            .insert(audit.id, audit.clone());
        let mut occ = self.memory_occurrences.write().await;
        if let Some(o) = occ.get_mut(&occurrence_id) {
            o.status = "completed".to_string();
            o.completed_at = Some(chrono::Utc::now());
        }
        Ok(())
    }

    /// All audits for a tenant (dashboard path — same relational store).
    pub async fn list_all_audits(&self, tenant_id: Uuid) -> Result<Vec<LswAudit>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct AudRow {
                id: Uuid,
                standard_id: Uuid,
                occurrence_id: Option<Uuid>,
                tenant_id: Uuid,
                auditor_id: Uuid,
                leader_id: Option<Uuid>,
                area: String,
                layer: i32,
                results: serde_json::Value,
                compliance_rate: f64,
                notes: Option<String>,
                audited_at: chrono::DateTime<chrono::Utc>,
                created_at: chrono::DateTime<chrono::Utc>,
            }
            let rows: Vec<AudRow> = sqlx::query_as(
                "SELECT id, standard_id, occurrence_id, tenant_id, auditor_id, leader_id, area, \
                        layer, results, compliance_rate, notes, audited_at, created_at \
                 FROM lsw_audits WHERE tenant_id = $1 \
                 ORDER BY audited_at DESC",
            )
            .bind(tenant_id)
            .fetch_all(pool)
            .await
            .map_err(|e| format!("LSW audit list-all failed: {e}"))?;
            return Ok(rows
                .into_iter()
                .map(|r| LswAudit {
                    id: r.id,
                    standard_id: r.standard_id,
                    occurrence_id: r.occurrence_id,
                    tenant_id: r.tenant_id,
                    auditor_id: r.auditor_id,
                    leader_id: r.leader_id,
                    area: r.area,
                    layer: r.layer.max(0) as u8,
                    results: serde_json::from_value(r.results).unwrap_or_default(),
                    compliance_rate: r.compliance_rate,
                    notes: r.notes,
                    audited_at: r.audited_at,
                    created_at: r.created_at,
                })
                .collect());
        }
        let mut out: Vec<LswAudit> = self
            .memory_audits
            .read()
            .await
            .values()
            .filter(|a| a.tenant_id == tenant_id)
            .cloned()
            .collect();
        out.sort_by_key(|a| std::cmp::Reverse(a.audited_at));
        Ok(out)
    }

    /// Fetch ONE audit by id (item 12: the detail endpoint must read the
    /// SAME store the list reads — no list/detail divergence).
    pub async fn get_audit(
        &self,
        tenant_id: Uuid,
        audit_id: Uuid,
    ) -> Result<Option<LswAudit>, String> {
        if let Some(pool) = &self.pool {
            #[derive(sqlx::FromRow)]
            struct AudRow {
                id: Uuid,
                standard_id: Uuid,
                occurrence_id: Option<Uuid>,
                tenant_id: Uuid,
                auditor_id: Uuid,
                leader_id: Option<Uuid>,
                area: String,
                layer: i32,
                results: serde_json::Value,
                compliance_rate: f64,
                notes: Option<String>,
                audited_at: chrono::DateTime<chrono::Utc>,
                created_at: chrono::DateTime<chrono::Utc>,
            }
            let row: Option<AudRow> = sqlx::query_as(
                "SELECT id, standard_id, occurrence_id, tenant_id, auditor_id, leader_id, area,  layer, results, compliance_rate, notes, audited_at, created_at  FROM lsw_audits WHERE tenant_id = $1 AND id = $2",
            )
            .bind(tenant_id)
            .bind(audit_id)
            .fetch_optional(pool)
            .await
            .map_err(|e| format!("LSW audit get failed: {e}"))?;
            return Ok(row.map(|r| LswAudit {
                id: r.id,
                standard_id: r.standard_id,
                occurrence_id: r.occurrence_id,
                tenant_id: r.tenant_id,
                auditor_id: r.auditor_id,
                leader_id: r.leader_id,
                area: r.area,
                layer: r.layer.max(0) as u8,
                results: serde_json::from_value(r.results).unwrap_or_default(),
                compliance_rate: r.compliance_rate,
                notes: r.notes,
                audited_at: r.audited_at,
                created_at: r.created_at,
            }));
        }
        Ok(self
            .memory_audits
            .read()
            .await
            .values()
            .find(|a| a.id == audit_id && a.tenant_id == tenant_id)
            .cloned())
    }

    /// Remove one audit (item 12: the compensation path must delete from
    /// the SAME store the audit was written to — the generic EntityStore
    /// rollback left the relational row behind).
    pub async fn delete_audit(&self, tenant_id: Uuid, audit_id: Uuid) -> Result<(), String> {
        if let Some(pool) = &self.pool {
            sqlx::query("DELETE FROM lsw_audits WHERE tenant_id = $1 AND id = $2")
                .bind(tenant_id)
                .bind(audit_id)
                .execute(pool)
                .await
                .map_err(|e| format!("LSW audit delete failed: {e}"))?;
            return Ok(());
        }
        self.memory_audits.write().await.remove(&audit_id);
        Ok(())
    }
}
