//! Inspection services: AQL sampling, First Article Inspection (AS9102),
//! and Self-Inspection (operator-level quality checks).
//!
//! Ported from Python's `aql_sampling_service.py`, `first_article_service.py`,
//! and `self_inspection_service.py`.

use async_trait::async_trait;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::{new_id, now, EntityId, TenantId};

use super::models::{
    AqlLotInspection, AqlSamplingPlan, FirstArticleCharacteristic, FirstArticleInspection,
    SelfInspection, SelfInspectionCheck,
};

/// AQL sampling service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait AqlSamplingService: Send + Sync {
    /// Create a new AQL sampling plan.
    async fn create_plan(
        &self,
        tenant_id: TenantId,
        plan_number: String,
        aql_percent: f64,
        inspection_level: String,
        lot_size_from: u64,
        lot_size_to: u64,
        sample_size: u64,
        accept_number: u64,
        reject_number: u64,
    ) -> Result<AqlSamplingPlan>;

    /// List AQL lot inspections for a plan.
    async fn list_inspections(&self, plan_id: Option<EntityId>) -> Result<Vec<AqlLotInspection>>;

    /// Create a lot inspection against a plan.
    async fn create_inspection(
        &self,
        plan_id: EntityId,
        lot_number: String,
        lot_size: u64,
        defects_found: u64,
        inspector_id: Option<EntityId>,
    ) -> Result<AqlLotInspection>;
}

/// First Article Inspection (AS9102) service trait.
#[async_trait]
#[allow(clippy::too_many_arguments)]
pub trait FaiService: Send + Sync {
    /// Create a new FAI.
    async fn create_inspection(
        &self,
        tenant_id: TenantId,
        part_number: String,
        part_name: String,
        revision: String,
        customer: Option<String>,
        inspector_id: Option<EntityId>,
    ) -> Result<FirstArticleInspection>;

    /// Get an FAI by ID.
    async fn get_inspection(&self, inspection_id: EntityId) -> Result<FirstArticleInspection>;

    /// List all FAIs.
    async fn list_inspections(&self, tenant_id: TenantId) -> Result<Vec<FirstArticleInspection>>;

    /// Add a characteristic to an FAI.
    async fn add_characteristic(
        &self,
        inspection_id: EntityId,
        characteristic_number: String,
        requirement: String,
        specification: String,
        result: String,
        is_conforming: Option<bool>,
        notes: Option<String>,
    ) -> Result<FirstArticleCharacteristic>;

    /// Close an FAI.
    async fn close_inspection(&self, inspection_id: EntityId) -> Result<FirstArticleInspection>;

    /// Update an FAI.
    async fn update_inspection(
        &self,
        inspection_id: EntityId,
        part_number: Option<String>,
        part_name: Option<String>,
        revision: Option<String>,
        customer: Option<String>,
        status: Option<String>,
    ) -> Result<FirstArticleInspection>;
}

/// Self-inspection service trait.
#[async_trait]
pub trait SelfInspectionService: Send + Sync {
    /// Create a self-inspection.
    async fn create_inspection(
        &self,
        tenant_id: TenantId,
        product_id: Option<EntityId>,
        work_order_id: Option<EntityId>,
        station_id: Option<EntityId>,
        operator_id: Option<EntityId>,
    ) -> Result<SelfInspection>;

    /// Get a self-inspection by ID.
    async fn get_inspection(&self, inspection_id: EntityId) -> Result<SelfInspection>;

    /// List all self-inspections.
    async fn list_inspections(&self, tenant_id: TenantId) -> Result<Vec<SelfInspection>>;

    /// Add a check to a self-inspection.
    async fn add_check(
        &self,
        inspection_id: EntityId,
        characteristic: String,
        specification: Option<String>,
        actual_value: Option<String>,
        result: String,
        notes: Option<String>,
    ) -> Result<SelfInspectionCheck>;

    /// Close a self-inspection.
    async fn close_inspection(
        &self,
        inspection_id: EntityId,
        result: String,
    ) -> Result<SelfInspection>;
}

// ---------------------------------------------------------------------------
// In-Memory Implementation
// ---------------------------------------------------------------------------

/// Combined in-memory inspection service.
#[allow(dead_code)]
pub struct InMemoryInspectionService {
    aql_plans: tokio::sync::RwLock<Vec<AqlSamplingPlan>>,
    aql_inspections: tokio::sync::RwLock<Vec<AqlLotInspection>>,
    fai_inspections: tokio::sync::RwLock<Vec<FirstArticleInspection>>,
    fai_chars: tokio::sync::RwLock<Vec<FirstArticleCharacteristic>>,
    self_inspections: tokio::sync::RwLock<Vec<SelfInspection>>,
    self_checks: tokio::sync::RwLock<Vec<SelfInspectionCheck>>,
    plan_counter: tokio::sync::RwLock<u64>,
    fai_counter: tokio::sync::RwLock<u64>,
    si_counter: tokio::sync::RwLock<u64>,
}

impl InMemoryInspectionService {
    /// Create a new empty service.
    pub fn new() -> Self {
        Self {
            aql_plans: tokio::sync::RwLock::new(Vec::new()),
            aql_inspections: tokio::sync::RwLock::new(Vec::new()),
            fai_inspections: tokio::sync::RwLock::new(Vec::new()),
            fai_chars: tokio::sync::RwLock::new(Vec::new()),
            self_inspections: tokio::sync::RwLock::new(Vec::new()),
            self_checks: tokio::sync::RwLock::new(Vec::new()),
            plan_counter: tokio::sync::RwLock::new(0),
            fai_counter: tokio::sync::RwLock::new(0),
            si_counter: tokio::sync::RwLock::new(0),
        }
    }
}

impl Default for InMemoryInspectionService {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl AqlSamplingService for InMemoryInspectionService {
    async fn create_plan(
        &self,
        _tenant_id: TenantId,
        plan_number: String,
        aql_percent: f64,
        inspection_level: String,
        lot_size_from: u64,
        lot_size_to: u64,
        sample_size: u64,
        accept_number: u64,
        reject_number: u64,
    ) -> Result<AqlSamplingPlan> {
        if aql_percent <= 0.0 || aql_percent > 100.0 {
            return Err(SenseiError::Validation(format!(
                "Invalid AQL percentage: {aql_percent}. Must be between 0 and 100."
            )));
        }
        if sample_size == 0 {
            return Err(SenseiError::Validation(
                "Sample size must be > 0".to_string(),
            ));
        }
        if lot_size_from >= lot_size_to {
            return Err(SenseiError::Validation(format!(
                "Invalid lot size range: {lot_size_from} >= {lot_size_to}"
            )));
        }

        let plan = AqlSamplingPlan {
            id: new_id(),
            plan_number,
            aql_percent,
            inspection_level,
            lot_size_from,
            lot_size_to,
            sample_size,
            accept_number,
            reject_number,
            created_at: now(),
        };

        self.aql_plans.write().await.push(plan.clone());
        Ok(plan)
    }

    async fn list_inspections(&self, plan_id: Option<EntityId>) -> Result<Vec<AqlLotInspection>> {
        let inspections = self.aql_inspections.read().await;
        Ok(match plan_id {
            Some(pid) => inspections
                .iter()
                .filter(|i| i.plan_id == pid)
                .cloned()
                .collect(),
            None => inspections.clone(),
        })
    }

    async fn create_inspection(
        &self,
        plan_id: EntityId,
        lot_number: String,
        lot_size: u64,
        defects_found: u64,
        inspector_id: Option<EntityId>,
    ) -> Result<AqlLotInspection> {
        // Verify plan exists
        let plans = self.aql_plans.read().await;
        let plan = plans
            .iter()
            .find(|p| p.id == plan_id)
            .ok_or_else(|| SenseiError::NotFound(format!("AQL plan {plan_id} not found")))?;

        // Validate lot size against plan range
        if lot_size < plan.lot_size_from || lot_size > plan.lot_size_to {
            return Err(SenseiError::Validation(format!(
                "Lot size {lot_size} outside plan range [{}, {}]",
                plan.lot_size_from, plan.lot_size_to
            )));
        }

        // Determine result based on accept/reject numbers
        let result = if defects_found <= plan.accept_number {
            "accepted".to_string()
        } else if defects_found >= plan.reject_number {
            "rejected".to_string()
        } else {
            // Between accept and reject numbers - ambiguous zone
            // Per ANSI/ASQ Z1.4, if defects >= reject_number, reject
            // Since we're between accept and reject, use the triangular definition
            // In practice this means the lot is still accepted but needs tighter scrutiny
            "accepted_conditional".to_string()
        };

        let inspection = AqlLotInspection {
            id: new_id(),
            plan_id,
            lot_number,
            lot_size,
            sample_size: plan.sample_size,
            defects_found,
            accept_number: plan.accept_number,
            reject_number: plan.reject_number,
            result,
            inspector_id,
            inspected_at: Some(now()),
            created_at: now(),
        };

        self.aql_inspections.write().await.push(inspection.clone());
        Ok(inspection)
    }
}

#[async_trait]
impl FaiService for InMemoryInspectionService {
    async fn create_inspection(
        &self,
        _tenant_id: TenantId,
        part_number: String,
        part_name: String,
        revision: String,
        customer: Option<String>,
        inspector_id: Option<EntityId>,
    ) -> Result<FirstArticleInspection> {
        let mut counter = self.fai_counter.write().await;
        *counter += 1;
        let fai_number = format!("FAI-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter);

        let inspection = FirstArticleInspection {
            id: new_id(),
            fai_number,
            part_number,
            part_name,
            revision,
            customer,
            status: "open".to_string(),
            characteristics: Vec::new(),
            inspector_id,
            created_at: now(),
            updated_at: now(),
        };

        self.fai_inspections.write().await.push(inspection.clone());
        Ok(inspection)
    }

    async fn get_inspection(&self, inspection_id: EntityId) -> Result<FirstArticleInspection> {
        self.fai_inspections
            .read()
            .await
            .iter()
            .find(|i| i.id == inspection_id)
            .cloned()
            .ok_or_else(|| SenseiError::NotFound(format!("FAI {inspection_id} not found")))
    }

    async fn list_inspections(&self, _tenant_id: TenantId) -> Result<Vec<FirstArticleInspection>> {
        Ok(self.fai_inspections.read().await.clone())
    }

    async fn add_characteristic(
        &self,
        inspection_id: EntityId,
        characteristic_number: String,
        requirement: String,
        specification: String,
        result: String,
        is_conforming: Option<bool>,
        notes: Option<String>,
    ) -> Result<FirstArticleCharacteristic> {
        // Verify inspection exists
        FaiService::get_inspection(self, inspection_id).await?;

        let characteristic = FirstArticleCharacteristic {
            id: new_id(),
            inspection_id,
            characteristic_number,
            requirement,
            specification,
            result,
            is_conforming,
            notes,
            created_at: now(),
        };

        self.fai_chars.write().await.push(characteristic.clone());

        // Update inspection's characteristics list
        let mut inspections = self.fai_inspections.write().await;
        if let Some(inspection) = inspections.iter_mut().find(|i| i.id == inspection_id) {
            inspection.characteristics.push(characteristic.clone());
            inspection.updated_at = now();
        }

        Ok(characteristic)
    }

    async fn close_inspection(&self, inspection_id: EntityId) -> Result<FirstArticleInspection> {
        let mut inspections = self.fai_inspections.write().await;
        let inspection = inspections
            .iter_mut()
            .find(|i| i.id == inspection_id)
            .ok_or_else(|| SenseiError::NotFound(format!("FAI {inspection_id} not found")))?;

        if inspection.status == "closed" {
            return Err(SenseiError::Validation("FAI is already closed".to_string()));
        }

        inspection.status = "closed".to_string();
        inspection.updated_at = now();

        Ok(inspection.clone())
    }

    async fn update_inspection(
        &self,
        inspection_id: EntityId,
        part_number: Option<String>,
        part_name: Option<String>,
        revision: Option<String>,
        customer: Option<String>,
        status: Option<String>,
    ) -> Result<FirstArticleInspection> {
        let mut inspections = self.fai_inspections.write().await;
        let inspection = inspections
            .iter_mut()
            .find(|i| i.id == inspection_id)
            .ok_or_else(|| SenseiError::NotFound(format!("FAI {inspection_id} not found")))?;

        if let Some(pn) = part_number {
            inspection.part_number = pn;
        }
        if let Some(pname) = part_name {
            inspection.part_name = pname;
        }
        if let Some(rev) = revision {
            inspection.revision = rev;
        }
        if let Some(cust) = customer {
            inspection.customer = Some(cust);
        }
        if let Some(st) = status {
            inspection.status = st;
        }

        inspection.updated_at = now();
        Ok(inspection.clone())
    }
}

#[async_trait]
impl SelfInspectionService for InMemoryInspectionService {
    async fn create_inspection(
        &self,
        _tenant_id: TenantId,
        product_id: Option<EntityId>,
        work_order_id: Option<EntityId>,
        station_id: Option<EntityId>,
        operator_id: Option<EntityId>,
    ) -> Result<SelfInspection> {
        let mut counter = self.si_counter.write().await;
        *counter += 1;
        let inspection_number =
            format!("SI-{}-{:04}", chrono::Utc::now().format("%Y%m%d"), counter);

        let inspection = SelfInspection {
            id: new_id(),
            inspection_number,
            product_id,
            work_order_id,
            station_id,
            operator_id,
            status: "open".to_string(),
            result: None,
            checks: Vec::new(),
            created_at: now(),
            completed_at: None,
        };

        self.self_inspections.write().await.push(inspection.clone());
        Ok(inspection)
    }

    async fn get_inspection(&self, inspection_id: EntityId) -> Result<SelfInspection> {
        self.self_inspections
            .read()
            .await
            .iter()
            .find(|i| i.id == inspection_id)
            .cloned()
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Self-inspection {inspection_id} not found"))
            })
    }

    async fn list_inspections(&self, _tenant_id: TenantId) -> Result<Vec<SelfInspection>> {
        Ok(self.self_inspections.read().await.clone())
    }

    async fn add_check(
        &self,
        inspection_id: EntityId,
        characteristic: String,
        specification: Option<String>,
        actual_value: Option<String>,
        result: String,
        notes: Option<String>,
    ) -> Result<SelfInspectionCheck> {
        // Verify inspection exists
        SelfInspectionService::get_inspection(self, inspection_id).await?;

        let check = SelfInspectionCheck {
            id: new_id(),
            inspection_id,
            characteristic,
            specification,
            actual_value,
            result,
            notes,
            created_at: now(),
        };

        self.self_checks.write().await.push(check.clone());

        // Update inspection's checks
        let mut inspections = self.self_inspections.write().await;
        if let Some(inspection) = inspections.iter_mut().find(|i| i.id == inspection_id) {
            inspection.checks.push(check.clone());
        }

        Ok(check)
    }

    async fn close_inspection(
        &self,
        inspection_id: EntityId,
        result: String,
    ) -> Result<SelfInspection> {
        let mut inspections = self.self_inspections.write().await;
        let inspection = inspections
            .iter_mut()
            .find(|i| i.id == inspection_id)
            .ok_or_else(|| {
                SenseiError::NotFound(format!("Self-inspection {inspection_id} not found"))
            })?;

        if inspection.status == "completed" {
            return Err(SenseiError::Validation(
                "Self-inspection is already completed".to_string(),
            ));
        }

        inspection.status = "completed".to_string();
        inspection.result = Some(result);
        inspection.completed_at = Some(now());

        Ok(inspection.clone())
    }
}
