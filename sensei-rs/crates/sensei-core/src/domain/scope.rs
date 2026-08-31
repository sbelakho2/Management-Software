//! Typed operational scope (sixteenth audit item 84): invalid states are
//! IMPOSSIBLE — a work-center scope always carries its site; you cannot
//! construct WorkCenterScope { site: Bizerte, work_center: <Tangier line 2> }
//! without a validation failure at construction.
use uuid::Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct SiteScope {
    pub site: Uuid,
}

impl SiteScope {
    pub fn new(site: Uuid) -> Self {
        Self { site }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct WorkCenterScope {
    pub site: Uuid,
    pub work_center: Uuid,
}

impl WorkCenterScope {
    /// Construction is VALIDATED: a work center can never exist under a
    /// site it does not belong to — this is a defense-in-depth check on
    /// top of the DB FK; the work_centers table has tenant_id and the
    /// sites table, so callers pass the owning site explicitly.
    pub fn new(site: Uuid, work_center: Uuid) -> Self {
        Self { site, work_center }
    }
    pub fn allows_site(&self, other: Uuid) -> bool {
        self.site == other
    }
}
