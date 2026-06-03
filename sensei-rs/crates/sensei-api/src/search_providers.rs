//! [`SearchableEntityProvider`] implementations for in-memory PM entity stores.
//!
//! Each provider wraps an [`EntityStore<T>`] and implements the
//! [`SearchableEntityProvider`] trait by iterating over all entities and
//! scoring their text fields against the search query.
//!
//! These are used by [`InMemorySearchService`] to extend search coverage
//! beyond the four domain-service-backed types (accounts, contacts, products,
//! users) to all PM entity types (tasks, kanban boards, obeya boards, etc.).

use async_trait::async_trait;
use serde::de::DeserializeOwned;
use serde::Serialize;
use sensei_core::error::Result;
use sensei_core::types::EntityId;
use sensei_services::ops::search::{SearchResult, SearchableEntityProvider};
use std::sync::Arc;
use uuid::Uuid;

use crate::db_stores::EntityStore;
use crate::stores::*;

// ---------------------------------------------------------------------------
// Helper: scoring helpers (mirror InMemorySearchService)
// ---------------------------------------------------------------------------

fn score_match(query: &str, target: &str) -> f32 {
    let lower_q = query.to_lowercase();
    let lower_t = target.to_lowercase();

    if lower_t == lower_q {
        1.0
    } else if lower_t.starts_with(&lower_q) {
        0.8
    } else if lower_t.contains(&lower_q) {
        0.5
    } else {
        let q_words: Vec<&str> = lower_q.split_whitespace().collect();
        let t_words: Vec<&str> = lower_t.split_whitespace().collect();
        let matches = q_words.iter().filter(|w| t_words.contains(w)).count();
        if matches > 0 {
            matches as f32 / q_words.len() as f32 * 0.4
        } else {
            0.0
        }
    }
}

fn best_score(query: &str, fields: &[&str]) -> f32 {
    fields
        .iter()
        .map(|f| score_match(query, f))
        .fold(0.0_f32, f32::max)
}

// ---------------------------------------------------------------------------
// Provider that wraps an EntityStore<T> and a closure to extract search fields
// ---------------------------------------------------------------------------

/// Generic provider that wraps an [`EntityStore<T>`] with a field extractor.
struct EntityStoreProvider<T> {
    entity_type: &'static str,
    store: EntityStore<T>,
    /// Given a reference to the entity, returns (title, [searchable_text_fields]).
    extractor: Box<dyn Fn(&T) -> (String, Vec<String>) + Send + Sync>,
    /// Extracts the tenant_id from an entity for cross-tenant filtering.
    tenant_id_extractor: Box<dyn Fn(&T) -> Uuid + Send + Sync>,
}

#[async_trait]
impl<T: Serialize + DeserializeOwned + Clone + Send + Sync + 'static> SearchableEntityProvider
    for EntityStoreProvider<T>
{
    async fn search_entities(
        &self,
        tenant_id: EntityId,
        query: &str,
    ) -> Result<Vec<SearchResult>> {
        let store = self.store.read().await;
        let mut results = Vec::new();

        for (entity_id, entity) in store.iter() {
            // Filter by tenant_id to prevent cross-tenant data leaks
            if (self.tenant_id_extractor)(entity) != tenant_id {
                continue;
            }

            let (title, fields) = (self.extractor)(entity);

            let field_refs: Vec<&str> = fields.iter().map(|s| s.as_str()).collect();
            let score = best_score(query, &field_refs);
            if score > 0.0 {
                results.push(SearchResult {
                    result_type: self.entity_type.to_string(),
                    result_id: *entity_id,
                    result_title: title,
                    relevance: score,
                });
            }
        }

        Ok(results)
    }

    fn entity_type_name(&self) -> &str {
        self.entity_type
    }
}

// ---------------------------------------------------------------------------
// Concrete providers — one per PM entity type
// ---------------------------------------------------------------------------

/// Create a [`SearchableEntityProvider`] for tasks.
pub fn task_search_provider(store: TaskStore) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "task",
        store: store.clone(),
        extractor: Box::new(|t: &Task| {
            let fields = vec![
                t.title.clone(),
                t.description.clone(),
                t.status.to_string(),
                t.priority.to_string(),
                t.category.clone(),
                t.tags.join(" "),
            ];
            (t.title.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|t: &Task| t.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for kanban boards.
pub fn kanban_board_search_provider(store: KanbanBoardStore) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "kanban_board",
        store: store.clone(),
        extractor: Box::new(|b: &KanbanBoard| {
            let mut fields = vec![b.name.clone(), b.description.clone()];
            for col in &b.columns {
                fields.push(col.name.clone());
                for card in &col.cards {
                    fields.push(card.title.clone());
                    fields.push(card.description.clone());
                    fields.extend(card.labels.clone());
                }
            }
            (b.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|b: &KanbanBoard| b.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for obeya boards.
pub fn obeya_board_search_provider(store: ObeyaBoardStore) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "obeya_board",
        store: store.clone(),
        extractor: Box::new(|b: &ObeyaBoard| {
            let mut fields = vec![b.name.clone(), b.description.clone()];
            for item in &b.items {
                fields.push(item.title.clone());
                fields.push(item.description.clone());
                fields.push(item.item_type.clone());
                fields.push(item.status.clone());
                fields.push(item.notes.clone());
            }
            (b.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|b: &ObeyaBoard| b.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for knowledge packs.
pub fn knowledge_pack_search_provider(
    store: KnowledgePackStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "knowledge_pack",
        store: store.clone(),
        extractor: Box::new(|kp: &KnowledgePack| {
            let fields = vec![
                kp.title.clone(),
                kp.description.clone(),
                kp.category.clone(),
                kp.content.clone(),
                kp.tags.join(" "),
            ];
            (kp.title.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|kp: &KnowledgePack| kp.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for training courses.
pub fn training_course_search_provider(
    store: TrainingCourseStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "training_course",
        store: store.clone(),
        extractor: Box::new(|c: &TrainingCourse| {
            let desc = c.description.clone().unwrap_or_default();
            let fields = vec![
                c.title.clone(),
                desc,
                format!("{:?}", c.category),
                c.required_for_roles.join(" "),
            ];
            (c.title.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|c: &TrainingCourse| c.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for work centers.
pub fn work_center_search_provider(store: WorkCenterStore) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "work_center",
        store: store.clone(),
        extractor: Box::new(|wc: &WorkCenter| {
            let fields = vec![
                wc.name.clone(),
                wc.description.clone(),
                wc.work_center_number.clone(),
                wc.work_center_type.clone(),
                wc.notes.clone(),
            ];
            (wc.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|wc: &WorkCenter| wc.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for state machine instances.
pub fn state_machine_instance_search_provider(
    store: StateMachineInstanceStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "state_machine_instance",
        store: store.clone(),
        extractor: Box::new(|smi: &StateMachineInstance| {
            let fields = vec![
                smi.current_state.clone(),
                format!("{:?}", smi.definition_id),
            ];
            (smi.current_state.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|smi: &StateMachineInstance| smi.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for production cells.
pub fn production_cell_search_provider(
    store: ProductionCellStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "production_cell",
        store: store.clone(),
        extractor: Box::new(|pc: &ProductionCell| {
            let fields = vec![
                pc.name.clone(),
                pc.code.clone(),
                pc.description.clone(),
                pc.cell_type.clone(),
                pc.location.clone().unwrap_or_default(),
            ];
            (pc.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|pc: &ProductionCell| pc.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for standard work documents.
pub fn standard_work_search_provider(
    store: StandardWorkStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "standard_work",
        store: store.clone(),
        extractor: Box::new(|sw: &StandardWorkDocument| {
            let mut fields = vec![
                sw.title.clone(),
                sw.document_number.clone(),
                sw.area.clone(),
                sw.process.clone(),
                sw.required_skills.join(" "),
                sw.safety_notes.join(" "),
                sw.tools_required.join(" "),
                sw.materials_required.join(" "),
            ];
            for step in &sw.steps {
                fields.push(step.description.clone());
                fields.extend(step.key_points.clone());
            }
            for qc in &sw.quality_checks {
                fields.push(qc.description.clone());
                fields.push(qc.standard.clone());
            }
            (sw.title.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|sw: &StandardWorkDocument| sw.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for LSW standards.
pub fn lsw_standard_search_provider(
    store: LswStandardStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "lsw_standard",
        store: store.clone(),
        extractor: Box::new(|lsw: &LswStandard| {
            let mut fields = vec![lsw.title.clone(), lsw.area.clone()];
            for item in &lsw.checklist_items {
                fields.push(item.description.clone());
            }
            (lsw.title.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|lsw: &LswStandard| lsw.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for KPI definitions.
pub fn kpi_definition_search_provider(
    store: KpiDefinitionStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "kpi_definition",
        store: store.clone(),
        extractor: Box::new(|kpi: &KpiDefinition| {
            let desc = kpi.description.clone().unwrap_or_default();
            let fields = vec![
                kpi.name.clone(),
                desc,
                format!("{:?}", kpi.category),
                kpi.unit.clone(),
                kpi.formula.clone().unwrap_or_default(),
            ];
            (kpi.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|kpi: &KpiDefinition| kpi.tenant_id),
    })
}

/// Create a [`SearchableEntityProvider`] for notification triggers.
pub fn notification_trigger_search_provider(
    store: NotificationTriggerStore,
) -> Arc<dyn SearchableEntityProvider> {
    Arc::new(EntityStoreProvider {
        entity_type: "notification_trigger",
        store: store.clone(),
        extractor: Box::new(|nt: &NotificationTrigger| {
            let desc = nt.description.clone().unwrap_or_default();
            let fields = vec![nt.name.clone(), desc, nt.event_type.clone()];
            (nt.name.clone(), fields)
        }),
        tenant_id_extractor: Box::new(|nt: &NotificationTrigger| nt.tenant_id),
    })
}

