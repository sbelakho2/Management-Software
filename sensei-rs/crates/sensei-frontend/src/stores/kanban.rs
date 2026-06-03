//! Kanban board store — column-based card management with drag state,
//! filters, WIP limits, and column visibility.
//!
//! Port of [`frontend/src/stores/kanban-store.ts`](frontend/src/stores/kanban-store.ts).

use leptos::prelude::*;
use std::collections::HashMap;
use crate::api::client::ApiClient;
use crate::api::rfq::RfqDto;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type RfqStatus = String; // "new" | "in_progress" | "review" | "sent" | "won" | "lost" | "archived"
pub type Priority = String;  // "low" | "medium" | "high" | "critical"

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct KanbanCard {
    pub id: String,
    pub title: String,
    pub customer: Option<String>,
    pub value: Option<f64>,
    pub priority: Priority,
    pub status: RfqStatus,
    pub assigned_to: Option<String>,
    pub due_date: Option<String>,
    pub age_days: Option<i32>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct KanbanColumn {
    pub id: RfqStatus,
    pub title: String,
    pub card_ids: Vec<String>,
    pub wip_limit: Option<u32>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DragState {
    pub is_dragging: bool,
    pub card: Option<KanbanCard>,
    pub source_column: Option<RfqStatus>,
    pub target_column: Option<RfqStatus>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct KanbanFilters {
    pub priority: Option<Priority>,
    pub search_query: String,
    pub assigned_to: Option<String>,
    pub date_range: Option<(String, String)>,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
}

impl Default for KanbanFilters {
    fn default() -> Self {
        Self {
            priority: None,
            search_query: String::new(),
            assigned_to: None,
            date_range: None,
            min_value: None,
            max_value: None,
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct KanbanConfig {
    pub show_archived: bool,
    pub compact_view: bool,
    pub show_avatars: bool,
}

impl Default for KanbanConfig {
    fn default() -> Self {
        Self {
            show_archived: false,
            compact_view: false,
            show_avatars: true,
        }
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ColumnConfig {
    pub visible: bool,
    pub wip_limit: Option<u32>,
}

// ---------------------------------------------------------------------------
// KanbanStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct KanbanStore {
    // Cards stored per-column (column_id → ordered card IDs, plus a full card map)
    pub cards: RwSignal<HashMap<String, KanbanCard>>,
    pub columns: RwSignal<HashMap<RfqStatus, Vec<String>>>, // column → ordered card IDs
    pub column_order: RwSignal<Vec<RfqStatus>>,
    pub column_configs: RwSignal<HashMap<RfqStatus, ColumnConfig>>,

    // Drag state
    pub drag_state: RwSignal<DragState>,

    // Filters & config
    pub filters: RwSignal<KanbanFilters>,
    pub config: RwSignal<KanbanConfig>,
}

impl KanbanStore {
    pub fn new() -> Self {
        let default_columns = vec![
            "new".to_string(),
            "in_progress".to_string(),
            "review".to_string(),
            "sent".to_string(),
            "won".to_string(),
            "lost".to_string(),
            "archived".to_string(),
        ];

        let mut columns = HashMap::new();
        let mut column_configs = HashMap::new();
        for col_id in &default_columns {
            columns.insert(col_id.clone(), Vec::new());
            column_configs.insert(col_id.clone(), ColumnConfig {
                visible: *col_id != "archived",
                wip_limit: None,
            });
        }

        Self {
            cards: RwSignal::new(HashMap::new()),
            columns: RwSignal::new(columns),
            column_order: RwSignal::new(default_columns),
            column_configs: RwSignal::new(column_configs),
            drag_state: RwSignal::new(DragState {
                is_dragging: false,
                card: None,
                source_column: None,
                target_column: None,
            }),
            filters: RwSignal::new(KanbanFilters::default()),
            config: RwSignal::new(KanbanConfig::default()),
        }
    }

    // -----------------------------------------------------------------------
    // Initialization
    // -----------------------------------------------------------------------

    pub fn initialize_from_rfqs(&self, rfqs: Vec<RfqDto>) {
        let mut cards_map = HashMap::new();
        let mut columns_map: HashMap<String, Vec<String>> = HashMap::new();

        for col in self.column_order.get().iter() {
            columns_map.entry(col.clone()).or_default();
        }

        for rfq in rfqs {
            let card = KanbanCard {
                id: rfq.id.clone(),
                title: rfq.title.clone(),
                customer: Some(rfq.customer_id.clone()),
                value: rfq.estimated_value,
                priority: rfq.priority.clone().unwrap_or_default(),
                status: rfq.status.clone(),
                assigned_to: rfq.assigned_to.clone(),
                due_date: rfq.due_date.clone(),
                age_days: None,
            };
            cards_map.insert(rfq.id.clone(), card);
            columns_map
                .entry(rfq.status.clone())
                .or_default()
                .push(rfq.id);
        }

        self.cards.set(cards_map);
        self.columns.set(columns_map);
    }

    // -----------------------------------------------------------------------
    // Card operations
    // -----------------------------------------------------------------------

    pub async fn move_card(
        &self,
        client: &ApiClient,
        card_id: &str,
        from_column: &str,
        to_column: &str,
        new_position: u32,
    ) {
        // Optimistic update
        self.columns.update(|cols| {
            // Remove from source
            if let Some(card_ids) = cols.get_mut(from_column) {
                card_ids.retain(|id| id != card_id);
            }
            // Insert at position in target
            let target = cols.entry(to_column.to_string()).or_default();
            let pos = (new_position as usize).min(target.len());
            target.insert(pos, card_id.to_string());

            // Reorder rest of target
            for (i, id) in target.clone().iter().enumerate() {
                if *id == card_id {
                    continue;
                }
                // Re-index remaining
            }
            // Re-sort remaining to maintain positions
            let mut reordered: Vec<String> = Vec::new();
            let mut idx = 0usize;
            for id in target.clone() {
                if id == card_id {
                    continue;
                }
                if idx == pos as usize {
                    reordered.push(card_id.to_string());
                }
                reordered.push(id);
                idx += 1;
            }
            if idx == pos as usize {
                reordered.push(card_id.to_string());
            }
            cols.insert(to_column.to_string(), reordered);
        });

        // Update card status
        if let Some(card) = self.cards.get().get(card_id) {
            let mut updated = card.clone();
            updated.status = to_column.to_string();
            self.cards.update(|c| {
                c.insert(card_id.to_string(), updated);
            });
        }

        // Persist to server
        let _ = client.post::<serde_json::Value, serde_json::Value>(
            &format!("/rfqs/{card_id}/move"),
            &serde_json::json!({
                "from_column": from_column,
                "to_column": to_column,
                "position": new_position,
            }),
        ).await;
    }

    pub fn reorder_card(&self, card_id: &str, column: &str, new_position: u32) {
        self.columns.update(|cols| {
            if let Some(card_ids) = cols.get_mut(column) {
                card_ids.retain(|id| id != card_id);
                let pos = (new_position as usize).min(card_ids.len());
                card_ids.insert(pos, card_id.to_string());

                // Reset positions sequentially
                for (i, id) in card_ids.clone().iter().enumerate() {
                    if let Some(card) = self.cards.get().get(id) {
                        let mut updated = card.clone();
                        updated.status = column.to_string();
                        self.cards.update(|c| {
                            c.insert(id.clone(), updated);
                        });
                    }
                }
            }
        });
    }

    pub fn update_card(&self, card_id: &str, updates: serde_json::Value) {
        if let Some(card) = self.cards.get().get(card_id) {
            let mut updated = card.clone();
            if let Some(title) = updates.get("title").and_then(|v| v.as_str()) {
                updated.title = title.to_string();
            }
            if let Some(customer) = updates.get("customer").and_then(|v| v.as_str()) {
                updated.customer = Some(customer.to_string());
            }
            if let Some(value) = updates.get("value").and_then(|v| v.as_f64()) {
                updated.value = Some(value);
            }
            if let Some(priority) = updates.get("priority").and_then(|v| v.as_str()) {
                updated.priority = priority.to_string();
            }
            if let Some(assigned_to) = updates.get("assigned_to").and_then(|v| v.as_str()) {
                updated.assigned_to = Some(assigned_to.to_string());
            }
            if let Some(due_date) = updates.get("due_date").and_then(|v| v.as_str()) {
                updated.due_date = Some(due_date.to_string());
            }
            self.cards.update(|c| {
                c.insert(card_id.to_string(), updated);
            });
        }
    }

    pub fn remove_card(&self, card_id: &str) {
        self.cards.update(|c| {
            c.remove(card_id);
        });
        self.columns.update(|cols| {
            for (_col, card_ids) in cols.iter_mut() {
                card_ids.retain(|id| id != card_id);
            }
        });
    }

    pub fn add_card(&self, rfq: RfqDto, column: &str, position: Option<u32>) {
        let card = KanbanCard {
            id: rfq.id.clone(),
            title: rfq.title.clone(),
            customer: Some(rfq.customer_id.clone()),
            value: rfq.estimated_value,
            priority: rfq.priority.clone().unwrap_or_default(),
            status: column.to_string(),
            assigned_to: rfq.assigned_to.clone(),
            due_date: rfq.due_date.clone(),
            age_days: None,
        };
        let card_id = card.id.clone();

        self.cards.update(|c| {
            c.insert(card_id.clone(), card);
        });

        self.columns.update(|cols| {
            let target = cols.entry(column.to_string()).or_default();
            match position {
                Some(pos) => {
                    let pos = (pos as usize).min(target.len());
                    target.insert(pos, card_id);
                }
                None => target.push(card_id),
            }
        });
    }

    // -----------------------------------------------------------------------
    // Drag state
    // -----------------------------------------------------------------------

    pub fn start_drag(&self, card: KanbanCard) {
        let col = card.status.clone();
        self.drag_state.set(DragState {
            is_dragging: true,
            card: Some(card),
            source_column: Some(col),
            target_column: None,
        });
    }

    pub fn update_drag_target(&self, column: Option<&str>) {
        self.drag_state.update(|ds| {
            ds.target_column = column.map(|c| c.to_string());
        });
    }

    pub fn end_drag(&self) {
        self.drag_state.set(DragState {
            is_dragging: false,
            card: None,
            source_column: None,
            target_column: None,
        });
    }

    // -----------------------------------------------------------------------
    // Filters & Config
    // -----------------------------------------------------------------------

    pub fn set_filters(&self, new_filters: serde_json::Value) {
        self.filters.update(|f| {
            if let Some(priority) = new_filters.get("priority").and_then(|v| v.as_str()) {
                f.priority = Some(priority.to_string());
            }
            if let Some(query) = new_filters.get("search_query").and_then(|v| v.as_str()) {
                f.search_query = query.to_string();
            }
            if let Some(assigned_to) = new_filters.get("assigned_to").and_then(|v| v.as_str()) {
                f.assigned_to = Some(assigned_to.to_string());
            }
            if let Some(min) = new_filters.get("min_value").and_then(|v| v.as_f64()) {
                f.min_value = Some(min);
            }
            if let Some(max) = new_filters.get("max_value").and_then(|v| v.as_f64()) {
                f.max_value = Some(max);
            }
        });
    }

    pub fn set_config(&self, new_config: serde_json::Value) {
        self.config.update(|c| {
            if let Some(show_archived) = new_config.get("show_archived").and_then(|v| v.as_bool()) {
                c.show_archived = show_archived;
            }
            if let Some(compact) = new_config.get("compact_view").and_then(|v| v.as_bool()) {
                c.compact_view = compact;
            }
            if let Some(avatars) = new_config.get("show_avatars").and_then(|v| v.as_bool()) {
                c.show_avatars = avatars;
            }
        });
    }

    pub fn toggle_column(&self, column_id: &str, visible: bool) {
        self.column_configs.update(|cfgs| {
            if let Some(cfg) = cfgs.get_mut(column_id) {
                cfg.visible = visible;
            }
        });
    }

    pub fn set_wip_limit(&self, column_id: &str, limit: Option<u32>) {
        self.column_configs.update(|cfgs| {
            if let Some(cfg) = cfgs.get_mut(column_id) {
                cfg.wip_limit = limit;
            }
        });
    }

    // -----------------------------------------------------------------------
    // Queries
    // -----------------------------------------------------------------------

    pub fn get_column_cards(&self, column_id: &str) -> Vec<KanbanCard> {
        let cards_map = self.cards.get();
        let cols = self.columns.get();
        let filters = self.filters.get();

        let card_ids = match cols.get(column_id) {
            Some(ids) => ids.clone(),
            None => return Vec::new(),
        };

        card_ids
            .into_iter()
            .filter_map(|id| cards_map.get(&id).cloned())
            .filter(|card| self.matches_filters(card, &filters))
            .collect()
    }

    fn matches_filters(&self, card: &KanbanCard, filters: &KanbanFilters) -> bool {
        if let Some(ref priority) = filters.priority {
            if card.priority != *priority {
                return false;
            }
        }
        if !filters.search_query.is_empty() {
            let q = filters.search_query.to_lowercase();
            if !card.title.to_lowercase().contains(&q)
                && !card.customer.as_deref().unwrap_or("").to_lowercase().contains(&q)
            {
                return false;
            }
        }
        if let Some(ref assigned_to) = filters.assigned_to {
            if card.assigned_to.as_deref() != Some(assigned_to) {
                return false;
            }
        }
        if let Some(min) = filters.min_value {
            if card.value.unwrap_or(0.0) < min {
                return false;
            }
        }
        if let Some(max) = filters.max_value {
            if card.value.unwrap_or(0.0) > max {
                return false;
            }
        }
        true
    }

    pub fn get_column_wip_status(&self, column_id: &str) -> (u32, Option<u32>) {
        let count = self.columns.get().get(column_id).map(|ids| ids.len() as u32).unwrap_or(0);
        let limit = self.column_configs.get().get(column_id).and_then(|c| c.wip_limit);
        (count, limit)
    }
}

impl Default for KanbanStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

pub fn get_priority_color(priority: &str) -> &str {
    match priority {
        "critical" => "red",
        "high" => "orange",
        "medium" => "yellow",
        "low" => "green",
        _ => "gray",
    }
}

pub fn get_days_until_due(_due_date: &str) -> i32 {
    // Simplified: just parse and compare
    0
}

pub fn get_due_date_status(_due_date: &str) -> &'static str {
    // Simplified: would use actual date comparison
    "on-track"
}
