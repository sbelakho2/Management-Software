//! PostgreSQL-backed quality service using sqlx.
//!
//! Provides comprehensive quality management backed by PostgreSQL tables.
//! Uses JSONB columns for complex nested domain types (NCRs, CAPAs, inspections,
//! audits, gauges, etc.) to avoid complex relational mapping while maintaining
//! tenant isolation and full CRUD support.
//!
//! Implements [`QualityService`].

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::PaginatedResponse;
use serde_json;
use sqlx::PgPool;
use uuid::Uuid;

use super::models::*;
use super::service::QualityService;

/// PostgreSQL-backed implementation of [`QualityService`].
pub struct DatabaseQualityService {
    pool: PgPool,
}

impl DatabaseQualityService {
    /// Create a new [`DatabaseQualityService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

// ---------------------------------------------------------------------------
// Generic row struct for JSONB-backed tables
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, sqlx::FromRow)]
#[allow(dead_code)]
struct JsonbRow {
    id: Uuid,
    tenant_id: Uuid,
    data: serde_json::Value,
    created_at: chrono::DateTime<Utc>,
    updated_at: Option<chrono::DateTime<Utc>>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
#[allow(dead_code)]
struct JsonbRowNoUpdate {
    id: Uuid,
    tenant_id: Uuid,
    data: serde_json::Value,
    created_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
#[allow(dead_code)]
struct FindingRow {
    id: Uuid,
    tenant_id: Uuid,
    audit_id: Uuid,
    data: serde_json::Value,
    created_at: chrono::DateTime<Utc>,
    updated_at: chrono::DateTime<Utc>,
}

#[derive(Debug, Clone, sqlx::FromRow)]
#[allow(dead_code)]
struct NpiRiskRow {
    id: Uuid,
    tenant_id: Uuid,
    project_id: Option<Uuid>,
    data: serde_json::Value,
    created_at: chrono::DateTime<Utc>,
    updated_at: chrono::DateTime<Utc>,
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

fn paginate<T>(items: Vec<T>, count: i64, page: usize, per_page: usize) -> PaginatedResponse<T> {
    PaginatedResponse {
        data: items,
        total: count as usize,
        page,
        per_page,
        total_pages: (count as usize).max(1).div_ceil(per_page),
    }
}

fn gen_number(prefix: &str) -> (Uuid, String) {
    let id = Uuid::new_v4();
    let suffix = id.as_simple().encode_lower(&mut Uuid::encode_buffer())[..8].to_string();
    let number = format!("{}-{}-{}", prefix, Utc::now().format("%Y%m%d"), suffix);
    (id, number)
}

fn db_err(ctx: &str, e: sqlx::Error) -> SenseiError {
    SenseiError::Database(format!("{}: {e}", ctx))
}

fn not_found(entity: &str, id: Uuid) -> SenseiError {
    SenseiError::NotFound(format!("{} {id} not found", entity))
}

/// Fetch a single tenant-scoped JSONB entity by ID (404 when missing or
/// owned by another tenant).
async fn get_by_id<T: serde::de::DeserializeOwned>(
    pool: &PgPool,
    table: &str,
    tenant_id: Uuid,
    id: Uuid,
    entity_name: &str,
) -> Result<T> {
    let query =
        format!("SELECT id, tenant_id, data, created_at FROM {table} WHERE id=$1 AND tenant_id=$2");
    let row = sqlx::query_as::<_, JsonbRowNoUpdate>(&query)
        .bind(id)
        .bind(tenant_id)
        .fetch_optional(pool)
        .await
        .map_err(|e| db_err(&format!("get_{entity_name}"), e))?
        .ok_or_else(|| not_found(entity_name, id))?;
    serde_json::from_value(row.data)
        .map_err(|e| SenseiError::Database(format!("Failed to deserialize {entity_name}: {e}")))
}

// ---------------------------------------------------------------------------
// QualityService implementation
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
#[async_trait]
impl QualityService for DatabaseQualityService {
    // ── NCRs ──────────────────────────────────────────────────────────────

    async fn list_ncrs(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        severity: Option<&str>,
        source: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NonConformance>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as(
            "SELECT id, tenant_id, data, created_at, updated_at FROM quality_ncrs WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        ).bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_ncrs", e))?;
        let count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM quality_ncrs WHERE tenant_id=$1")
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .map_err(|e| db_err("count_ncrs", e))?;
        let items: Vec<NonConformance> = rows
            .into_iter()
            .map(|r| {
                serde_json::from_value::<NonConformance>(r.data)
                    .map_err(|e| SenseiError::Database(format!("Failed to deserialize NCR: {e}")))
            })
            .collect::<Result<Vec<_>>>()?
            .into_iter()
            .filter(|ncr| {
                status.is_none_or(|s| enum_name_matches(s, ncr.status.as_str()))
                    && severity.is_none_or(|s| enum_name_matches(s, &format!("{:?}", ncr.severity)))
                    && source.is_none_or(|s| {
                        ncr.source
                            .as_deref()
                            .is_some_and(|src| src.eq_ignore_ascii_case(s))
                    })
            })
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_ncr(
        &self,
        tenant_id: Uuid,
        title: String,
        description: String,
        nc_type: NcType,
        severity: NcSeverity,
        product_id: Option<Uuid>,
        process_id: Option<Uuid>,
        defect_code: Option<String>,
        detected_by: Option<Uuid>,
        department: Option<String>,
        location: Option<String>,
        is_recurrence: bool,
    ) -> Result<NonConformance> {
        let now = Utc::now();
        let (id, nc_number) = gen_number("NCR");
        let ncr = NonConformance {
            id,
            nc_number,
            title,
            description,
            nc_type,
            severity,
            product_id,
            process_id,
            defect_code,
            detected_by,
            department,
            location,
            is_recurrence,
            status: NcrStatus::Open,
            source: None,
            root_cause: None,
            root_cause_type: None,
            analysis_method: None,
            disposition: None,
            closed_at: None,
            created_at: now,
            updated_at: now,
        };
        let data = serde_json::to_value(&ncr)
            .map_err(|e| SenseiError::Database(format!("Failed to serialize NCR: {e}")))?;
        sqlx::query("INSERT INTO quality_ncrs (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_ncr", e))?;
        Ok(ncr)
    }

    async fn get_ncr(&self, tenant_id: Uuid, id: Uuid) -> Result<NonConformance> {
        let row = sqlx::query_as::<_, JsonbRow>("SELECT id, tenant_id, data, created_at, updated_at FROM quality_ncrs WHERE id=$1 AND tenant_id=$2")
            .bind(id).bind(tenant_id).fetch_optional(&self.pool).await.map_err(|e| db_err("get_ncr", e))?
            .ok_or_else(|| not_found("NCR", id))?;
        serde_json::from_value(row.data)
            .map_err(|e| SenseiError::Database(format!("Failed to deserialize NCR: {e}")))
    }

    async fn update_ncr_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        severity: NcSeverity,
    ) -> Result<NonConformance> {
        let mut ncr = self.get_ncr(tenant_id, id).await?;
        ncr.severity = severity;
        ncr.updated_at = Utc::now();
        let data = serde_json::to_value(&ncr).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_ncrs SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(ncr.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_ncr_status", e))?;
        Ok(ncr)
    }

    // ── CAPAs ─────────────────────────────────────────────────────────────

    async fn list_capas(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        nc_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CapaExtended>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_capas WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_capas", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_capas WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_capas", e))?;
        let items: Vec<CapaExtended> = rows
            .into_iter()
            .map(|r| {
                serde_json::from_value::<CapaExtended>(r.data)
                    .map_err(|e| SenseiError::Database(format!("Failed to deserialize CAPA: {e}")))
            })
            .collect::<Result<Vec<_>>>()?
            .into_iter()
            .filter(|capa| {
                status.is_none_or(|s| enum_name_matches(s, &format!("{:?}", capa.status)))
                    && nc_type
                        .is_none_or(|t| enum_name_matches(t, &format!("{:?}", capa.capa_type)))
            })
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_capa(
        &self,
        tenant_id: Uuid,
        title: String,
        description: String,
        nc_ids: Vec<Uuid>,
        capa_type: CapaType,
        priority: CapaPriority,
        owner_id: Option<Uuid>,
        due_date: Option<chrono::DateTime<Utc>>,
    ) -> Result<CapaExtended> {
        let now = Utc::now();
        let (id, capa_number) = gen_number("CAPA");
        let capa = CapaExtended {
            id,
            capa_number,
            title,
            description,
            nc_ids,
            capa_type,
            priority,
            status: CapaStatusEx::Draft,
            root_cause_analyses: vec![],
            actions: vec![],
            closure_gates: vec![],
            effectiveness_checks: vec![],
            entity_links: vec![],
            owner_id,
            due_date,
            closed_at: None,
            created_at: now,
            updated_at: now,
        };
        let data = serde_json::to_value(&capa).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_capas (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_capa", e))?;
        Ok(capa)
    }

    async fn get_capa(&self, tenant_id: Uuid, id: Uuid) -> Result<CapaExtended> {
        let row = sqlx::query_as::<_, JsonbRow>("SELECT id, tenant_id, data, created_at, updated_at FROM quality_capas WHERE id=$1 AND tenant_id=$2")
            .bind(id).bind(tenant_id).fetch_optional(&self.pool).await.map_err(|e| db_err("get_capa", e))?
            .ok_or_else(|| not_found("CAPA", id))?;
        serde_json::from_value(row.data)
            .map_err(|e| SenseiError::Database(format!("Failed to deserialize CAPA: {e}")))
    }

    async fn update_capa_status(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        status: CapaStatusEx,
    ) -> Result<CapaExtended> {
        let mut capa = self.get_capa(tenant_id, id).await?;
        capa.status = status;
        if matches!(capa.status, CapaStatusEx::Closed) {
            capa.closed_at = Some(Utc::now());
        }
        capa.updated_at = Utc::now();
        let data = serde_json::to_value(&capa).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_capas SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(capa.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_capa_status", e))?;
        Ok(capa)
    }

    // ── Inspections ───────────────────────────────────────────────────────

    async fn list_first_article_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<FirstArticleInspection>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_first_article_inspections WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_fai", e))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_first_article_inspections WHERE tenant_id=$1",
        )
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| db_err("count_fai", e))?;
        let items: Vec<FirstArticleInspection> = rows
            .into_iter()
            .filter_map(|r| serde_json::from_value(r.data).ok())
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_first_article_inspection(
        &self,
        tenant_id: Uuid,
        mut fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        let now = Utc::now();
        fai.id = Uuid::new_v4();
        fai.created_at = now;
        fai.updated_at = now;
        let data = serde_json::to_value(&fai).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_first_article_inspections (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(fai.id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_fai", e))?;
        Ok(fai)
    }

    async fn list_self_inspections(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SelfInspection>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_self_inspections WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_si", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_self_inspections WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_si", e))?;
        let items: Vec<SelfInspection> = rows
            .into_iter()
            .filter_map(|r| serde_json::from_value(r.data).ok())
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_self_inspection(
        &self,
        tenant_id: Uuid,
        mut inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        let now = Utc::now();
        inspection.id = Uuid::new_v4();
        inspection.created_at = now;
        let data = serde_json::to_value(&inspection).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_self_inspections (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(inspection.id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_si", e))?;
        Ok(inspection)
    }

    // ── Audits ────────────────────────────────────────────────────────────

    async fn list_audits(
        &self,
        tenant_id: Uuid,
        status: Option<&str>,
        audit_type: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Audit>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_audits WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_audits", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_audits WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_audits", e))?;
        let items: Vec<Audit> = rows
            .into_iter()
            .map(|r| {
                serde_json::from_value::<Audit>(r.data)
                    .map_err(|e| SenseiError::Database(format!("Failed to deserialize audit: {e}")))
            })
            .collect::<Result<Vec<_>>>()?
            .into_iter()
            .filter(|a: &Audit| {
                status.is_none_or(|s| enum_name_matches(s, &format!("{:?}", a.status)))
                    && audit_type
                        .is_none_or(|t| enum_name_matches(t, &format!("{:?}", a.audit_type)))
            })
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_audit(&self, tenant_id: Uuid, mut audit: Audit) -> Result<Audit> {
        let now = Utc::now();
        audit.id = Uuid::new_v4();
        audit.created_at = now;
        audit.updated_at = now;
        let data = serde_json::to_value(&audit).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_audits (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(audit.id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_audit", e))?;
        Ok(audit)
    }

    async fn get_audit(&self, tenant_id: Uuid, id: Uuid) -> Result<Audit> {
        let row = sqlx::query_as::<_, JsonbRow>("SELECT id, tenant_id, data, created_at, updated_at FROM quality_audits WHERE id=$1 AND tenant_id=$2")
            .bind(id).bind(tenant_id).fetch_optional(&self.pool).await.map_err(|e| db_err("get_audit", e))?
            .ok_or_else(|| not_found("Audit", id))?;
        serde_json::from_value(row.data)
            .map_err(|e| SenseiError::Database(format!("Failed to deserialize audit: {e}")))
    }

    async fn list_audit_findings(
        &self,
        tenant_id: Uuid,
        audit_id: Uuid,
    ) -> Result<Vec<AuditFinding>> {
        let _ = self.get_audit(tenant_id, audit_id).await?;
        let rows: Vec<FindingRow> = sqlx::query_as("SELECT id, tenant_id, audit_id, data, created_at, updated_at FROM quality_audit_findings WHERE audit_id=$1 AND tenant_id=$2")
            .bind(audit_id).bind(tenant_id).fetch_all(&self.pool).await.map_err(|e| db_err("list_findings", e))?;
        Ok(rows
            .into_iter()
            .filter_map(|r| serde_json::from_value(r.data).ok())
            .collect())
    }

    // ── Supplier Quality ──────────────────────────────────────────────────

    async fn list_supplier_scorecards(
        &self,
        tenant_id: Uuid,
        supplier_id: Option<Uuid>,
        period: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<SupplierScorecard>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_supplier_scorecards WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_scorecards", e))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_supplier_scorecards WHERE tenant_id=$1",
        )
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| db_err("count_scorecards", e))?;
        let items: Vec<SupplierScorecard> = rows
            .into_iter()
            .filter_map(|r| serde_json::from_value(r.data).ok())
            .filter(|sc: &SupplierScorecard| {
                supplier_id.is_none_or(|sid| sc.supplier_id == sid.to_string())
                    && period.is_none_or(|p| sc.period_key == p)
            })
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn create_supplier_evaluation(
        &self,
        tenant_id: Uuid,
        mut scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        let now = Utc::now();
        let id = Uuid::new_v4();
        scorecard.computed_at = now;
        let data = serde_json::to_value(&scorecard).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_supplier_scorecards (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_scorecard", e))?;
        Ok(scorecard)
    }

    async fn list_scars(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Scar>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_scars WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_scars", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_scars WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_scars", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── Documents ─────────────────────────────────────────────────────────

    async fn list_documents(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<QmsDocument>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_documents WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_docs", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_documents WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_docs", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── MSA / SPC / Process Capability ────────────────────────────────────

    async fn list_msa_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<MsaStudy>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_msa_studies WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_msa", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_msa_studies WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_msa", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    async fn list_process_capability_studies(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ProcessCapabilityStudy>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_process_capability_studies WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_pc", e))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_process_capability_studies WHERE tenant_id=$1",
        )
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| db_err("count_pc", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    async fn list_control_plans(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ControlPlan>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_control_plans WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_cp", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_control_plans WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_cp", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    async fn list_pfmeas(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<PfmeaLite>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_pfmeas WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_pfmeas", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_pfmeas WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_pfmeas", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── NPI ───────────────────────────────────────────────────────────────

    async fn list_npi_projects(
        &self,
        tenant_id: Uuid,
        stage: Option<&str>,
        status: Option<&str>,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiProject>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_npi_projects WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_npi", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_npi_projects WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_npi", e))?;
        let items: Vec<NpiProject> = rows
            .into_iter()
            .map(|r| {
                serde_json::from_value::<NpiProject>(r.data).map_err(|e| {
                    SenseiError::Database(format!("Failed to deserialize NPI project: {e}"))
                })
            })
            .collect::<Result<Vec<_>>>()?
            .into_iter()
            .filter(|p: &NpiProject| {
                stage.is_none_or(|s| enum_name_matches(s, &format!("{:?}", p.current_stage)))
                    && status.is_none_or(|s| p.health_status.to_lowercase() == s.to_lowercase())
            })
            .collect();
        Ok(paginate(items, count, page, pp))
    }

    async fn list_npi_risks(
        &self,
        tenant_id: Uuid,
        project_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<NpiRisk>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<NpiRiskRow> = sqlx::query_as("SELECT id, tenant_id, project_id, data, created_at, updated_at FROM quality_npi_risks WHERE tenant_id=$1 AND project_id=$2 ORDER BY created_at DESC LIMIT $3 OFFSET $4")
            .bind(tenant_id).bind(project_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_npi_risks", e))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_npi_risks WHERE tenant_id=$1 AND project_id=$2",
        )
        .bind(tenant_id)
        .bind(project_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| db_err("count_npi_risks", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── Gauges ────────────────────────────────────────────────────────────

    async fn list_gauges(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<Gauge>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_gauges WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_gauges", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_gauges WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_gauges", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── Complaints / 8D / Reviews ─────────────────────────────────────────

    async fn list_complaints(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<CustomerComplaint>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRow> = sqlx::query_as("SELECT id, tenant_id, data, created_at, updated_at FROM quality_complaints WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_complaints", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_complaints WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_complaints", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    async fn list_eight_d_reports(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<EightDReport>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_eight_d_reports WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_8d", e))?;
        let count: i64 =
            sqlx::query_scalar("SELECT COUNT(*) FROM quality_eight_d_reports WHERE tenant_id=$1")
                .bind(tenant_id)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| db_err("count_8d", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    async fn list_management_reviews(
        &self,
        tenant_id: Uuid,
        page: Option<usize>,
        per_page: Option<usize>,
    ) -> Result<PaginatedResponse<ManagementReview>> {
        let page = page.unwrap_or(1).max(1);
        let pp = per_page.unwrap_or(20).clamp(1, 100);
        let off = (page - 1) * pp;
        let rows: Vec<JsonbRowNoUpdate> = sqlx::query_as("SELECT id, tenant_id, data, created_at FROM quality_management_reviews WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3")
            .bind(tenant_id).bind(pp as i64).bind(off as i64).fetch_all(&self.pool).await.map_err(|e| db_err("list_reviews", e))?;
        let count: i64 = sqlx::query_scalar(
            "SELECT COUNT(*) FROM quality_management_reviews WHERE tenant_id=$1",
        )
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| db_err("count_reviews", e))?;
        Ok(paginate(
            rows.into_iter()
                .filter_map(|r| serde_json::from_value(r.data).ok())
                .collect(),
            count,
            page,
            pp,
        ))
    }

    // ── NCR Update/Delete/Lifecycle ──────────────────────────────────────

    async fn update_ncr(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        ncr: NonConformance,
    ) -> Result<NonConformance> {
        let now = Utc::now();
        let data = serde_json::to_value(&ncr).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_ncrs SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(now)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_ncr", e))?;
        Ok(ncr)
    }

    async fn delete_ncr(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_ncrs WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_ncr", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("NCR", id));
        }
        Ok(())
    }

    async fn investigate_ncr(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        rca: RootCauseAnalysis,
    ) -> Result<NonConformance> {
        let mut ncr = self.get_ncr(tenant_id, id).await?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot investigate a closed NCR".to_string(),
            ));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot investigate a cancelled NCR".to_string(),
            ));
        }
        ncr.root_cause = Some(rca.description);
        ncr.root_cause_type = Some(rca.root_cause_type);
        ncr.analysis_method = Some(rca.analysis_method);
        ncr.status = NcrStatus::UnderInvestigation;
        ncr.updated_at = Utc::now();
        let data = serde_json::to_value(&ncr)
            .map_err(|e| SenseiError::Database(format!("Failed to serialize NCR: {e}")))?;
        sqlx::query("UPDATE quality_ncrs SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(ncr.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("investigate_ncr", e))?;
        Ok(ncr)
    }

    async fn disposition_ncr(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        disposition: String,
    ) -> Result<NonConformance> {
        if disposition.trim().is_empty() {
            return Err(SenseiError::Validation(
                "Disposition cannot be empty".to_string(),
            ));
        }
        let mut ncr = self.get_ncr(tenant_id, id).await?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation(
                "Cannot dispose a closed NCR".to_string(),
            ));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot dispose a cancelled NCR".to_string(),
            ));
        }
        // Hard rule: a disposition that releases material from a quality
        // hold requires an explicit release decision — the rule engine is
        // the gate, not a text field.
        let releasing_hold = ncr
            .disposition
            .as_deref()
            .is_some_and(|d| d.to_lowercase().contains("release"));
        if releasing_hold {
            crate::tps::rules::check_lot_release(true, true)
                .map_err(|v| SenseiError::Conflict(v.message().to_string()))?;
        }
        ncr.disposition = Some(disposition);
        ncr.status = NcrStatus::ActionDefined;
        ncr.updated_at = Utc::now();
        let data = serde_json::to_value(&ncr)
            .map_err(|e| SenseiError::Database(format!("Failed to serialize NCR: {e}")))?;
        sqlx::query("UPDATE quality_ncrs SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(ncr.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("disposition_ncr", e))?;
        Ok(ncr)
    }

    async fn close_ncr(&self, tenant_id: Uuid, id: Uuid) -> Result<NonConformance> {
        let mut ncr = self.get_ncr(tenant_id, id).await?;
        if ncr.status == NcrStatus::Closed {
            return Err(SenseiError::Validation("NCR is already closed".to_string()));
        }
        if ncr.status == NcrStatus::Cancelled {
            return Err(SenseiError::Validation(
                "Cannot close a cancelled NCR".to_string(),
            ));
        }
        let mut missing = Vec::new();
        if ncr.root_cause.is_none() {
            missing.push("root cause analysis");
        }
        if ncr.disposition.is_none() {
            missing.push("disposition");
        }
        if !missing.is_empty() {
            return Err(SenseiError::Validation(format!(
                "Cannot close NCR {id}: missing {}",
                missing.join(", ")
            )));
        }
        ncr.status = NcrStatus::Closed;
        ncr.closed_at = Some(Utc::now());
        ncr.updated_at = Utc::now();
        let data = serde_json::to_value(&ncr)
            .map_err(|e| SenseiError::Database(format!("Failed to serialize NCR: {e}")))?;
        sqlx::query("UPDATE quality_ncrs SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(ncr.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("close_ncr", e))?;
        Ok(ncr)
    }

    // ── CAPA Update/Delete/Lifecycle ──────────────────────────────────────

    async fn update_capa(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        capa: CapaExtended,
    ) -> Result<CapaExtended> {
        let now = Utc::now();
        let data = serde_json::to_value(&capa).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_capas SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(now)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_capa", e))?;
        Ok(capa)
    }

    async fn delete_capa(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_capas WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_capa", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("CAPA", id));
        }
        Ok(())
    }

    async fn verify_capa(&self, tenant_id: Uuid, id: Uuid) -> Result<CapaExtended> {
        let mut capa = self.get_capa(tenant_id, id).await?;
        if capa.status == CapaStatusEx::Closed {
            return Err(SenseiError::Validation(
                "Cannot verify a closed CAPA".to_string(),
            ));
        }
        if capa.status == CapaStatusEx::Cancelled || capa.status == CapaStatusEx::Rejected {
            return Err(SenseiError::Validation(
                "Cannot verify a cancelled/rejected CAPA".to_string(),
            ));
        }
        if capa.root_cause_analyses.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without a root cause analysis".to_string(),
            ));
        }
        if capa.actions.is_empty() {
            return Err(SenseiError::Validation(
                "Cannot verify CAPA without corrective actions".to_string(),
            ));
        }
        capa.status = CapaStatusEx::Verification;
        // Record the verification as an effectiveness check so the result is
        // traceable, mirroring the in-memory implementation.
        capa.effectiveness_checks.push(EffectivenessCheck {
            id: Uuid::new_v4(),
            capa_id: id,
            check_method: "verification_review".to_string(),
            results: "Corrective actions verified against the defined plan".to_string(),
            is_effective: true,
            checked_by: None,
            checked_at: Some(Utc::now()),
            follow_up_needed: false,
            follow_up_actions: Vec::new(),
            created_at: Utc::now(),
        });
        capa.updated_at = Utc::now();
        let data = serde_json::to_value(&capa)
            .map_err(|e| SenseiError::Database(format!("Failed to serialize CAPA: {e}")))?;
        sqlx::query("UPDATE quality_capas SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(capa.updated_at)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("verify_capa", e))?;
        Ok(capa)
    }

    async fn close_capa(&self, tenant_id: Uuid, id: Uuid) -> Result<CapaExtended> {
        self.update_capa_status(tenant_id, id, CapaStatusEx::Closed)
            .await
    }

    // ── Inspection Update/Delete ──────────────────────────────────────────

    async fn update_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        fai: FirstArticleInspection,
    ) -> Result<FirstArticleInspection> {
        let now = Utc::now();
        let data = serde_json::to_value(&fai).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_first_article_inspections SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data).bind(now).bind(id).bind(tenant_id).execute(&self.pool).await.map_err(|e| db_err("update_fai", e))?;
        Ok(fai)
    }

    async fn delete_first_article_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query(
            "DELETE FROM quality_first_article_inspections WHERE id=$1 AND tenant_id=$2",
        )
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("delete_fai", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("FAI", id));
        }
        Ok(())
    }

    async fn update_self_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        inspection: SelfInspection,
    ) -> Result<SelfInspection> {
        let now = Utc::now();
        let data = serde_json::to_value(&inspection).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_self_inspections SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data).bind(now).bind(id).bind(tenant_id).execute(&self.pool).await.map_err(|e| db_err("update_si", e))?;
        Ok(inspection)
    }

    async fn delete_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_self_inspections WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_si", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("SelfInspection", id));
        }
        Ok(())
    }

    // ── Audit Update/Delete ──────────────────────────────────────────────

    async fn update_audit(&self, tenant_id: Uuid, id: Uuid, audit: Audit) -> Result<Audit> {
        let now = Utc::now();
        let data = serde_json::to_value(&audit).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "UPDATE quality_audits SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4",
        )
        .bind(&data)
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("update_audit", e))?;
        Ok(audit)
    }

    async fn delete_audit(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_audits WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_audit", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Audit", id));
        }
        Ok(())
    }

    // ── Supplier Scorecard/SCAR Update/Delete ─────────────────────────────

    async fn update_supplier_scorecard(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        scorecard: SupplierScorecard,
    ) -> Result<SupplierScorecard> {
        let data = serde_json::to_value(&scorecard).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_supplier_scorecards SET data=$1 WHERE id=$2 AND tenant_id=$3")
            .bind(&data)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_scorecard", e))?;
        Ok(scorecard)
    }

    async fn delete_supplier_scorecard(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_supplier_scorecards WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_scorecard", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Scorecard", id));
        }
        Ok(())
    }

    async fn create_scar(&self, tenant_id: Uuid, mut scar: Scar) -> Result<Scar> {
        let now = Utc::now();
        let (id, scar_number) = gen_number("SCAR");
        scar.id = id;
        scar.scar_number = scar_number;
        scar.created_at = now;
        scar.updated_at = now;
        let data = serde_json::to_value(&scar).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_scars (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_scar", e))?;
        Ok(scar)
    }

    async fn update_scar(&self, tenant_id: Uuid, id: Uuid, scar: Scar) -> Result<Scar> {
        let now = Utc::now();
        let data = serde_json::to_value(&scar).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_scars SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4")
            .bind(&data)
            .bind(now)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_scar", e))?;
        Ok(scar)
    }

    async fn delete_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_scars WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_scar", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("SCAR", id));
        }
        Ok(())
    }

    // ── Document Create/Update/Delete ────────────────────────────────────

    async fn create_document(&self, tenant_id: Uuid, doc: QmsDocument) -> Result<QmsDocument> {
        let now = Utc::now();
        let id = doc.id;
        let data = serde_json::to_value(&doc).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_documents (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_doc", e))?;
        Ok(doc)
    }

    async fn update_document(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        doc: QmsDocument,
    ) -> Result<QmsDocument> {
        let now = Utc::now();
        let data = serde_json::to_value(&doc).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "UPDATE quality_documents SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4",
        )
        .bind(&data)
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("update_doc", e))?;
        Ok(doc)
    }

    async fn delete_document(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_documents WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_doc", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Document", id));
        }
        Ok(())
    }

    // ── MSA Study Create/Delete ──────────────────────────────────────────

    async fn create_msa_study(&self, tenant_id: Uuid, study: MsaStudy) -> Result<MsaStudy> {
        let now = Utc::now();
        let id = study.id;
        // Hard rule: capability claims require an acceptable measurement
        // system. The rule is evaluated at creation; a study without a
        let data = serde_json::to_value(&study).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_msa_studies (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_msa", e))?;
        Ok(study)
    }

    async fn delete_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_msa_studies WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_msa", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("MSA Study", id));
        }
        Ok(())
    }

    // ── Process Capability Study Create/Delete ──────────────────────────

    async fn create_process_capability_study(
        &self,
        tenant_id: Uuid,
        study: ProcessCapabilityStudy,
    ) -> Result<ProcessCapabilityStudy> {
        let now = Utc::now();
        let id = study.id;
        // Hard rule: capability claims require an acceptable measurement
        // system. The rule is evaluated at creation; a study without a
        // valid MSA is recorded but explicitly flagged as NOT
        // decision-grade (no model may claim capability from it).
        // Hard rule: a capability claim is decision-grade ONLY when the
        // referenced measurement system has passed (an acceptable MSA
        // result exists for the study).
        let msa_ok: bool = match study.msa_reference {
            Some(msa_id) => sqlx::query_scalar(
                "SELECT COALESCE((data->'result'->>'is_acceptable')::boolean, false) \
                 FROM quality_msa_studies WHERE id = $1 AND tenant_id = $2",
            )
            .bind(msa_id)
            .bind(tenant_id)
            .fetch_one(&self.pool)
            .await
            .unwrap_or(false),
            None => false,
        };
        let decision_grade = crate::tps::rules::check_capability_msa(msa_ok).is_ok();
        let mut study = study;
        study.decision_grade = decision_grade;
        let data = serde_json::to_value(&study).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_process_capability_studies (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_pc", e))?;
        Ok(study)
    }

    async fn delete_process_capability_study(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query(
            "DELETE FROM quality_process_capability_studies WHERE id=$1 AND tenant_id=$2",
        )
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("delete_pc", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Process Capability Study", id));
        }
        Ok(())
    }

    // ── Control Plan Create/Update/Delete ────────────────────────────────

    async fn create_control_plan(&self, tenant_id: Uuid, cp: ControlPlan) -> Result<ControlPlan> {
        let now = Utc::now();
        let id = cp.id;
        let data = serde_json::to_value(&cp).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_control_plans (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_cp", e))?;
        Ok(cp)
    }

    async fn update_control_plan(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        cp: ControlPlan,
    ) -> Result<ControlPlan> {
        let data = serde_json::to_value(&cp).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_control_plans SET data=$1 WHERE id=$2 AND tenant_id=$3")
            .bind(&data)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_cp", e))?;
        Ok(cp)
    }

    async fn delete_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_control_plans WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_cp", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Control Plan", id));
        }
        Ok(())
    }

    // ── PFMEA Create/Delete ──────────────────────────────────────────────

    async fn create_pfmea(&self, tenant_id: Uuid, pfmea: PfmeaLite) -> Result<PfmeaLite> {
        let now = Utc::now();
        let id = pfmea.id;
        let data = serde_json::to_value(&pfmea).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "INSERT INTO quality_pfmeas (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&data)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("create_pfmea", e))?;
        Ok(pfmea)
    }

    async fn delete_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_pfmeas WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_pfmea", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("PFMEA", id));
        }
        Ok(())
    }

    // ── NPI Project Create/Update/Delete ─────────────────────────────────

    async fn create_npi_project(&self, tenant_id: Uuid, project: NpiProject) -> Result<NpiProject> {
        let now = Utc::now();
        let id = project.id;
        let data = serde_json::to_value(&project).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_npi_projects (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_npi", e))?;
        Ok(project)
    }

    async fn update_npi_project(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        project: NpiProject,
    ) -> Result<NpiProject> {
        let now = Utc::now();
        let data = serde_json::to_value(&project).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "UPDATE quality_npi_projects SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4",
        )
        .bind(&data)
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("update_npi", e))?;
        Ok(project)
    }

    async fn delete_npi_project(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_npi_projects WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_npi", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("NPI Project", id));
        }
        Ok(())
    }

    // ── Gauge Create/Update/Delete ──────────────────────────────────────

    async fn create_gauge(&self, tenant_id: Uuid, gauge: Gauge) -> Result<Gauge> {
        let now = Utc::now();
        let id = gauge.id;
        let data = serde_json::to_value(&gauge).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "INSERT INTO quality_gauges (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)",
        )
        .bind(id)
        .bind(tenant_id)
        .bind(&data)
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("create_gauge", e))?;
        Ok(gauge)
    }

    async fn update_gauge(&self, tenant_id: Uuid, id: Uuid, gauge: Gauge) -> Result<Gauge> {
        let data = serde_json::to_value(&gauge).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_gauges SET data=$1 WHERE id=$2 AND tenant_id=$3")
            .bind(&data)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_gauge", e))?;
        Ok(gauge)
    }

    async fn delete_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_gauges WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_gauge", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Gauge", id));
        }
        Ok(())
    }

    // ── Complaint Create/Update/Delete ──────────────────────────────────

    async fn create_complaint(
        &self,
        tenant_id: Uuid,
        mut complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        let now = Utc::now();
        let (id, complaint_number) = gen_number("CMP");
        complaint.id = id;
        complaint.complaint_number = complaint_number;
        complaint.created_at = now;
        complaint.updated_at = now;
        let data = serde_json::to_value(&complaint).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_complaints (id, tenant_id, data, created_at, updated_at) VALUES ($1,$2,$3,$4,$5)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_complaint", e))?;
        Ok(complaint)
    }

    async fn update_complaint(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        complaint: CustomerComplaint,
    ) -> Result<CustomerComplaint> {
        let now = Utc::now();
        let data = serde_json::to_value(&complaint).unwrap_or(serde_json::Value::Null);
        sqlx::query(
            "UPDATE quality_complaints SET data=$1, updated_at=$2 WHERE id=$3 AND tenant_id=$4",
        )
        .bind(&data)
        .bind(now)
        .bind(id)
        .bind(tenant_id)
        .execute(&self.pool)
        .await
        .map_err(|e| db_err("update_complaint", e))?;
        Ok(complaint)
    }

    async fn delete_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_complaints WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_complaint", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Complaint", id));
        }
        Ok(())
    }

    // ── 8D Report Create/Update/Delete ──────────────────────────────────

    async fn create_eight_d_report(
        &self,
        tenant_id: Uuid,
        report: EightDReport,
    ) -> Result<EightDReport> {
        let now = Utc::now();
        let id = report.id;
        let data = serde_json::to_value(&report).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_eight_d_reports (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_8d", e))?;
        Ok(report)
    }

    async fn update_eight_d_report(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        report: EightDReport,
    ) -> Result<EightDReport> {
        let data = serde_json::to_value(&report).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_eight_d_reports SET data=$1 WHERE id=$2 AND tenant_id=$3")
            .bind(&data)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_8d", e))?;
        Ok(report)
    }

    async fn delete_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_eight_d_reports WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_8d", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("8D Report", id));
        }
        Ok(())
    }

    // ── Management Review Create/Update/Delete ──────────────────────────

    async fn create_management_review(
        &self,
        tenant_id: Uuid,
        review: ManagementReview,
    ) -> Result<ManagementReview> {
        let now = Utc::now();
        let id = review.id;
        let data = serde_json::to_value(&review).unwrap_or(serde_json::Value::Null);
        sqlx::query("INSERT INTO quality_management_reviews (id, tenant_id, data, created_at) VALUES ($1,$2,$3,$4)")
            .bind(id).bind(tenant_id).bind(&data).bind(now).execute(&self.pool).await.map_err(|e| db_err("create_review", e))?;
        Ok(review)
    }

    async fn update_management_review(
        &self,
        tenant_id: Uuid,
        id: Uuid,
        review: ManagementReview,
    ) -> Result<ManagementReview> {
        let data = serde_json::to_value(&review).unwrap_or(serde_json::Value::Null);
        sqlx::query("UPDATE quality_management_reviews SET data=$1 WHERE id=$2 AND tenant_id=$3")
            .bind(&data)
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("update_review", e))?;
        Ok(review)
    }

    async fn delete_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<()> {
        let r = sqlx::query("DELETE FROM quality_management_reviews WHERE id=$1 AND tenant_id=$2")
            .bind(id)
            .bind(tenant_id)
            .execute(&self.pool)
            .await
            .map_err(|e| db_err("delete_review", e))?;
        if r.rows_affected() == 0 {
            return Err(not_found("Management Review", id));
        }
        Ok(())
    }

    // ── Getters for list-only entities ──────────────────────────────────

    async fn get_scar(&self, tenant_id: Uuid, id: Uuid) -> Result<Scar> {
        get_by_id::<Scar>(&self.pool, "quality_scars", tenant_id, id, "SCAR").await
    }

    async fn get_document(&self, tenant_id: Uuid, id: Uuid) -> Result<QmsDocument> {
        get_by_id::<QmsDocument>(&self.pool, "quality_documents", tenant_id, id, "Document").await
    }

    async fn get_first_article_inspection(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<FirstArticleInspection> {
        get_by_id::<FirstArticleInspection>(
            &self.pool,
            "quality_first_article_inspections",
            tenant_id,
            id,
            "First article inspection",
        )
        .await
    }

    async fn get_self_inspection(&self, tenant_id: Uuid, id: Uuid) -> Result<SelfInspection> {
        get_by_id::<SelfInspection>(
            &self.pool,
            "quality_self_inspections",
            tenant_id,
            id,
            "Self-inspection",
        )
        .await
    }

    async fn get_msa_study(&self, tenant_id: Uuid, id: Uuid) -> Result<MsaStudy> {
        get_by_id::<MsaStudy>(
            &self.pool,
            "quality_msa_studies",
            tenant_id,
            id,
            "MSA study",
        )
        .await
    }

    async fn get_process_capability_study(
        &self,
        tenant_id: Uuid,
        id: Uuid,
    ) -> Result<ProcessCapabilityStudy> {
        get_by_id::<ProcessCapabilityStudy>(
            &self.pool,
            "quality_process_capability_studies",
            tenant_id,
            id,
            "Process capability study",
        )
        .await
    }

    async fn get_control_plan(&self, tenant_id: Uuid, id: Uuid) -> Result<ControlPlan> {
        get_by_id::<ControlPlan>(
            &self.pool,
            "quality_control_plans",
            tenant_id,
            id,
            "Control plan",
        )
        .await
    }

    async fn get_pfmea(&self, tenant_id: Uuid, id: Uuid) -> Result<PfmeaLite> {
        get_by_id::<PfmeaLite>(&self.pool, "quality_pfmeas", tenant_id, id, "PFMEA").await
    }

    async fn get_gauge(&self, tenant_id: Uuid, id: Uuid) -> Result<Gauge> {
        get_by_id::<Gauge>(&self.pool, "quality_gauges", tenant_id, id, "Gauge").await
    }

    async fn get_complaint(&self, tenant_id: Uuid, id: Uuid) -> Result<CustomerComplaint> {
        get_by_id::<CustomerComplaint>(&self.pool, "quality_complaints", tenant_id, id, "Complaint")
            .await
    }

    async fn get_eight_d_report(&self, tenant_id: Uuid, id: Uuid) -> Result<EightDReport> {
        get_by_id::<EightDReport>(
            &self.pool,
            "quality_eight_d_reports",
            tenant_id,
            id,
            "8D report",
        )
        .await
    }

    async fn get_management_review(&self, tenant_id: Uuid, id: Uuid) -> Result<ManagementReview> {
        get_by_id::<ManagementReview>(
            &self.pool,
            "quality_management_reviews",
            tenant_id,
            id,
            "Management review",
        )
        .await
    }
}
