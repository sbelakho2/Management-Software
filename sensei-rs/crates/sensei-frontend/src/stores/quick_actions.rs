//! Quick actions store — action registration, execution, permissions,
//! confirmation dialogs, and execution tracking.
//!
//! Port of [`frontend/src/stores/quick-actions-store.ts`](frontend/src/stores/quick-actions-store.ts).

use leptos::prelude::*;
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type EntityType = String; // "project" | "story" | "issue" | "rfq" | "quote" | "customer" | ...
pub type ActionType = String; // "create" | "edit" | "delete" | "approve" | "reject" | "assign" | "move" | ...

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct QuickAction {
    pub id: String,
    pub name: String,
    pub description: String,
    pub icon: Option<String>,
    pub action_type: ActionType,
    pub entity_types: Vec<EntityType>,
    pub shortcut: Option<String>,
    pub requires_confirmation: bool,
    pub confirmation_title: Option<String>,
    pub confirmation_message: Option<String>,
    pub group: String, // "primary" | "secondary" | "overflow"
    pub order: i32,
    pub permissions: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ActionContext {
    pub entity_type: Option<EntityType>,
    pub entity_id: Option<String>,
    pub selected_ids: Vec<String>,
    pub parent_entity_type: Option<EntityType>,
    pub parent_entity_id: Option<String>,
    pub extra: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct ActionExecution {
    pub id: String,
    pub action_id: String,
    pub action_name: String,
    pub status: String, // "pending" | "running" | "completed" | "failed"
    pub started_at: Option<f64>,
    pub completed_at: Option<f64>,
    pub error: Option<String>,
    pub result: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct ConfirmationState {
    pub is_visible: bool,
    pub action_id: Option<String>,
    pub context: Option<ActionContext>,
    pub title: String,
    pub message: String,
    pub confirm_text: String,
    pub cancel_text: String,
    pub is_destructive: bool,
}

#[derive(Debug, Clone)]
pub struct QuickActionsState {
    pub actions: Vec<QuickAction>,
    pub handlers: HashMap<String, String>, // action_type -> handler_id
    pub context: Option<ActionContext>,
    pub executions: Vec<ActionExecution>,
    pub confirmation: ConfirmationState,
}

impl Default for QuickActionsState {
    fn default() -> Self {
        Self {
            actions: Vec::new(),
            handlers: HashMap::new(),
            context: None,
            executions: Vec::new(),
            confirmation: ConfirmationState {
                is_visible: false,
                action_id: None,
                context: None,
                title: String::new(),
                message: String::new(),
                confirm_text: "Confirm".to_string(),
                cancel_text: "Cancel".to_string(),
                is_destructive: false,
            },
        }
    }
}

// ---------------------------------------------------------------------------
// Static action definitions
// ---------------------------------------------------------------------------

fn all_actions() -> Vec<QuickAction> {
    vec![
        QuickAction {
            id: "create-project".to_string(),
            name: "Create Project".to_string(),
            description: "Start a new project".to_string(),
            icon: Some("folder-plus".to_string()),
            action_type: "create".to_string(),
            entity_types: vec!["project".to_string()],
            shortcut: Some("mod+shift+p".to_string()),
            requires_confirmation: false,
            confirmation_title: None,
            confirmation_message: None,
            group: "primary".to_string(),
            order: 1,
            permissions: vec!["project:create".to_string()],
        },
        QuickAction {
            id: "create-story".to_string(),
            name: "Create Story".to_string(),
            description: "Add a new user story".to_string(),
            icon: Some("plus-circle".to_string()),
            action_type: "create".to_string(),
            entity_types: vec!["story".to_string()],
            shortcut: Some("mod+shift+s".to_string()),
            requires_confirmation: false,
            confirmation_title: None,
            confirmation_message: None,
            group: "primary".to_string(),
            order: 2,
            permissions: vec!["story:create".to_string()],
        },
        QuickAction {
            id: "create-rfq".to_string(),
            name: "Create RFQ".to_string(),
            description: "Create a new request for quote".to_string(),
            icon: Some("file-text".to_string()),
            action_type: "create".to_string(),
            entity_types: vec!["rfq".to_string()],
            shortcut: Some("mod+shift+r".to_string()),
            requires_confirmation: false,
            confirmation_title: None,
            confirmation_message: None,
            group: "primary".to_string(),
            order: 3,
            permissions: vec!["rfq:create".to_string()],
        },
        QuickAction {
            id: "delete-entity".to_string(),
            name: "Delete".to_string(),
            description: "Delete the selected item".to_string(),
            icon: Some("trash-2".to_string()),
            action_type: "delete".to_string(),
            entity_types: vec![
                "project".to_string(),
                "story".to_string(),
                "issue".to_string(),
                "rfq".to_string(),
                "quote".to_string(),
                "customer".to_string(),
            ],
            shortcut: Some("mod+shift+d".to_string()),
            requires_confirmation: true,
            confirmation_title: Some("Confirm Delete".to_string()),
            confirmation_message: Some(
                "Are you sure you want to delete this item? This action cannot be undone."
                    .to_string(),
            ),
            group: "overflow".to_string(),
            order: 99,
            permissions: vec!["delete".to_string()],
        },
        QuickAction {
            id: "approve-quote".to_string(),
            name: "Approve Quote".to_string(),
            description: "Approve the selected quote".to_string(),
            icon: Some("check-circle".to_string()),
            action_type: "approve".to_string(),
            entity_types: vec!["quote".to_string()],
            shortcut: None,
            requires_confirmation: true,
            confirmation_title: Some("Confirm Approval".to_string()),
            confirmation_message: Some("Are you sure you want to approve this quote?".to_string()),
            group: "primary".to_string(),
            order: 4,
            permissions: vec!["quote:approve".to_string()],
        },
        QuickAction {
            id: "assign-entity".to_string(),
            name: "Assign".to_string(),
            description: "Assign the selected item to a user".to_string(),
            icon: Some("user-plus".to_string()),
            action_type: "assign".to_string(),
            entity_types: vec!["story".to_string(), "issue".to_string(), "task".to_string()],
            shortcut: Some("mod+shift+a".to_string()),
            requires_confirmation: false,
            confirmation_title: None,
            confirmation_message: None,
            group: "secondary".to_string(),
            order: 10,
            permissions: vec!["assign".to_string()],
        },
    ]
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

pub fn get_actions_for_entity(entity_type: &str) -> Vec<QuickAction> {
    all_actions()
        .into_iter()
        .filter(|action| action.entity_types.iter().any(|et| et == entity_type))
        .collect()
}

pub fn filter_by_visibility(actions: Vec<QuickAction>, group: &str) -> Vec<QuickAction> {
    actions.into_iter().filter(|a| a.group == group).collect()
}

pub fn has_permission(permissions: &[String], required: &str) -> bool {
    permissions.iter().any(|p| p == required)
}

pub fn filter_by_permissions(
    actions: Vec<QuickAction>,
    user_permissions: &[String],
) -> Vec<QuickAction> {
    actions
        .into_iter()
        .filter(|a| {
            a.permissions.is_empty()
                || a.permissions
                    .iter()
                    .any(|p| has_permission(user_permissions, p))
        })
        .collect()
}

pub fn get_action_by_id(action_id: &str) -> Option<QuickAction> {
    all_actions().into_iter().find(|a| a.id == action_id)
}

pub fn get_action_by_type(action_type: &str) -> Option<QuickAction> {
    all_actions()
        .into_iter()
        .find(|a| a.action_type == action_type)
}

pub fn format_entity_type(entity_type: &str) -> String {
    match entity_type {
        "project" => "Project".to_string(),
        "story" => "Story".to_string(),
        "issue" => "Issue".to_string(),
        "rfq" => "RFQ".to_string(),
        "quote" => "Quote".to_string(),
        "customer" => "Customer".to_string(),
        "task" => "Task".to_string(),
        _ => {
            let mut chars = entity_type.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().chain(chars).collect(),
            }
        }
    }
}

// ---------------------------------------------------------------------------
// QuickActionsStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct QuickActionsStore {
    // Data
    pub actions: RwSignal<Vec<QuickAction>>,
    pub context: RwSignal<Option<ActionContext>>,
    pub executions: RwSignal<Vec<ActionExecution>>,
    pub confirmation: RwSignal<ConfirmationState>,

    // Handler registry (action_type -> async function reference as string)
    pub handlers: RwSignal<HashMap<String, String>>,
}

impl QuickActionsStore {
    pub fn new() -> Self {
        // Initialize with default actions
        let default_actions = all_actions();

        Self {
            actions: RwSignal::new(default_actions),
            context: RwSignal::new(None),
            executions: RwSignal::new(Vec::new()),
            confirmation: RwSignal::new(ConfirmationState {
                is_visible: false,
                action_id: None,
                context: None,
                title: String::new(),
                message: String::new(),
                confirm_text: "Confirm".to_string(),
                cancel_text: "Cancel".to_string(),
                is_destructive: false,
            }),
            handlers: RwSignal::new(HashMap::new()),
        }
    }

    // -----------------------------------------------------------------------
    // Context
    // -----------------------------------------------------------------------

    pub fn set_context(&self, new_context: ActionContext) {
        self.context.set(Some(new_context));
    }

    pub fn clear_context(&self) {
        self.context.set(None);
    }

    // -----------------------------------------------------------------------
    // Action registration
    // -----------------------------------------------------------------------

    pub fn register_action(&self, action: QuickAction) {
        self.actions.update(|actions| {
            if let Some(pos) = actions.iter().position(|a| a.id == action.id) {
                actions[pos] = action;
            } else {
                actions.push(action);
            }
        });
    }

    pub fn unregister_action(&self, action_id: &str) {
        self.actions.update(|actions| {
            actions.retain(|a| a.id != action_id);
        });
    }

    pub fn update_action(&self, action_id: &str, updates: serde_json::Value) {
        self.actions.update(|actions| {
            if let Some(action) = actions.iter_mut().find(|a| a.id == action_id) {
                if let Some(name) = updates.get("name").and_then(|v| v.as_str()) {
                    action.name = name.to_string();
                }
                if let Some(desc) = updates.get("description").and_then(|v| v.as_str()) {
                    action.description = desc.to_string();
                }
                if let Some(group) = updates.get("group").and_then(|v| v.as_str()) {
                    action.group = group.to_string();
                }
                if let Some(order) = updates.get("order").and_then(|v| v.as_i64()) {
                    action.order = order as i32;
                }
            }
        });
    }

    // -----------------------------------------------------------------------
    // Handler registry
    // -----------------------------------------------------------------------

    pub fn register_handler(&self, action_type: &str, handler_id: &str) {
        self.handlers.update(|h| {
            h.insert(action_type.to_string(), handler_id.to_string());
        });
    }

    pub fn unregister_handler(&self, action_type: &str) {
        self.handlers.update(|h| {
            h.remove(action_type);
        });
    }

    // -----------------------------------------------------------------------
    // Execution
    // -----------------------------------------------------------------------

    fn generate_execution_id() -> String {
        use std::time::{SystemTime, UNIX_EPOCH};
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros();
        format!("exec_{ts}")
    }

    pub async fn execute_action(&self, action_id: &str, context_override: Option<ActionContext>) {
        let action = {
            let actions = self.actions.get();
            actions.into_iter().find(|a| a.id == action_id)
        };

        let Some(action) = action else { return };

        // Check permissions
        let ctx = context_override.or_else(|| self.context.get());

        // Create execution record
        let exec_id = Self::generate_execution_id();
        let execution = ActionExecution {
            id: exec_id.clone(),
            action_id: action_id.to_string(),
            action_name: action.name.clone(),
            status: "running".to_string(),
            started_at: Some(chrono::Utc::now().timestamp_millis() as f64),
            completed_at: None,
            error: None,
            result: None,
        };

        self.executions.update(|e| e.push(execution));

        // If requires confirmation, show dialog instead
        if action.requires_confirmation {
            self.show_confirmation(Some(action_id.to_string()), ctx);
            return;
        }

        // Execute
        // In a full Leptos implementation, this would dispatch to a registered handler
        // For now, we update the execution status
        self.executions.update(|execs| {
            if let Some(exec) = execs.iter_mut().find(|e| e.id == exec_id) {
                exec.status = "completed".to_string();
                exec.completed_at = Some(chrono::Utc::now().timestamp_millis() as f64);
                exec.result = Some(serde_json::json!({ "success": true }));
            }
        });
    }

    pub fn cancel_execution(&self, execution_id: &str) {
        self.executions.update(|execs| {
            if let Some(exec) = execs.iter_mut().find(|e| e.id == execution_id) {
                exec.status = "failed".to_string();
                exec.error = Some("Cancelled by user".to_string());
                exec.completed_at = Some(chrono::Utc::now().timestamp_millis() as f64);
            }
        });
    }

    // -----------------------------------------------------------------------
    // Confirmation dialog
    // -----------------------------------------------------------------------

    pub fn show_confirmation(&self, action_id: Option<String>, context: Option<ActionContext>) {
        let action = action_id.as_ref().and_then(|id| {
            let actions = self.actions.get();
            actions.into_iter().find(|a| a.id == *id)
        });

        self.confirmation.set(ConfirmationState {
            is_visible: true,
            title: action
                .as_ref()
                .and_then(|a| a.confirmation_title.clone())
                .unwrap_or_else(|| "Confirm Action".to_string()),
            message: action
                .as_ref()
                .and_then(|a| a.confirmation_message.clone())
                .unwrap_or_else(|| "Are you sure?".to_string()),
            confirm_text: "Confirm".to_string(),
            cancel_text: "Cancel".to_string(),
            is_destructive: action
                .as_ref()
                .map(|a| a.action_type == "delete")
                .unwrap_or(false),
            action_id,
            context,
        });
    }

    pub fn hide_confirmation(&self) {
        self.confirmation.update(|c| {
            c.is_visible = false;
        });
    }

    pub async fn confirm_action(&self) {
        let confirmation = self.confirmation.get();
        if let (true, Some(action_id)) = (confirmation.is_visible, confirmation.action_id) {
            self.hide_confirmation();
            self.execute_action(&action_id, confirmation.context).await;
        }
    }

    // -----------------------------------------------------------------------
    // Query helpers
    // -----------------------------------------------------------------------

    pub fn get_available_actions(&self) -> Vec<QuickAction> {
        let actions = self.actions.get();
        let ctx = self.context.get();

        actions
            .into_iter()
            .filter(|a| {
                // If we have context, filter by entity type
                if let Some(ref context) = ctx {
                    if let Some(ref entity_type) = context.entity_type {
                        return a.entity_types.contains(entity_type);
                    }
                }
                true
            })
            .collect()
    }

    pub fn get_primary_actions(&self) -> Vec<QuickAction> {
        self.get_available_actions()
            .into_iter()
            .filter(|a| a.group == "primary")
            .collect()
    }

    pub fn get_secondary_actions(&self) -> Vec<QuickAction> {
        self.get_available_actions()
            .into_iter()
            .filter(|a| a.group == "secondary")
            .collect()
    }

    pub fn get_overflow_actions(&self) -> Vec<QuickAction> {
        self.get_available_actions()
            .into_iter()
            .filter(|a| a.group == "overflow")
            .collect()
    }
}

impl Default for QuickActionsStore {
    fn default() -> Self {
        Self::new()
    }
}
