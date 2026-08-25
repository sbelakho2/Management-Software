//! Command palette store — fuzzy search, command registration, execution.
//!
//! Port of [`frontend/src/stores/command-palette-store.ts`](frontend/src/stores/command-palette-store.ts).

use leptos::prelude::*;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type CommandCategory = String; // "navigation" | "action" | "create" | "settings" | "reports"
pub type CommandActionType = String; // "navigate" | "execute" | "create" | "toggle"

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Command {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: CommandCategory,
    pub action_type: CommandActionType,
    pub action_data: serde_json::Value,
    pub shortcut: Option<String>,
    pub keywords: Vec<String>,
    pub icon: Option<String>,
    pub requires_confirmation: bool,
    pub group_id: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct CommandGroup {
    pub id: String,
    pub name: String,
    pub commands: Vec<String>, // command IDs
}

#[derive(Debug, Clone)]
pub struct CommandSearchResult {
    pub command: Command,
    pub score: f64,
    pub matched_indices: Vec<(usize, usize)>,
}

#[derive(Debug, Clone)]
pub struct CommandPaletteState {
    pub is_open: bool,
    pub mode: String, // "commands" | "search" | "settings"
    pub query: String,
    pub selected_index: i32,
    pub commands: Vec<Command>,
    pub filtered_results: Vec<CommandSearchResult>,
    pub recent_commands: Vec<String>, // command IDs
    pub groups: Vec<CommandGroup>,
}

impl Default for CommandPaletteState {
    fn default() -> Self {
        Self {
            is_open: false,
            mode: "commands".to_string(),
            query: String::new(),
            selected_index: 0,
            commands: Vec::new(),
            filtered_results: Vec::new(),
            recent_commands: Vec::new(),
            groups: Vec::new(),
        }
    }
}

// ---------------------------------------------------------------------------
// Fuzzy matching
// ---------------------------------------------------------------------------

fn fuzzy_match(query: &str, text: &str) -> Option<(f64, Vec<(usize, usize)>)> {
    if query.is_empty() {
        return Some((1.0, Vec::new()));
    }

    let query_lower = query.to_lowercase();
    let text_lower = text.to_lowercase();

    // Exact prefix match gets highest score
    if text_lower.starts_with(&query_lower) {
        let score = 1.0 - (query.len() as f64 * 0.01);
        let indices = vec![(0, query.len())];
        return Some((score, indices));
    }

    // Contains substring
    if let Some(pos) = text_lower.find(&query_lower) {
        let score = 0.9 - (pos as f64 * 0.01) - (query.len() as f64 * 0.01);
        let indices = vec![(pos, pos + query.len())];
        return Some((score, indices));
    }

    // Fuzzy contiguous character matching
    let chars = query_lower.chars().peekable();
    let mut text_chars = text_lower.char_indices();
    let mut matched_indices: Vec<(usize, usize)> = Vec::new();
    let mut score = 0.5;

    for qc in chars {
        let mut found = false;
        for (ti, tc) in text_chars.by_ref() {
            if tc == qc {
                // Bonus for matching after word boundary
                if ti == 0 || text_lower.as_bytes().get(ti - 1).copied() == Some(b' ') {
                    score += 0.1;
                }
                matched_indices.push((ti, ti + qc.len_utf8()));
                found = true;
                break;
            }
        }
        if !found {
            return None;
        }
    }

    // Penalize for extra characters
    score -= (text.len().saturating_sub(query.len())) as f64 * 0.01;
    score = score.max(0.0);

    Some((score, matched_indices))
}

fn search_commands(commands: &[Command], query: &str) -> Vec<CommandSearchResult> {
    if query.is_empty() {
        return commands
            .iter()
            .enumerate()
            .map(|(i, cmd)| CommandSearchResult {
                command: cmd.clone(),
                score: 1.0 - (i as f64 * 0.001),
                matched_indices: Vec::new(),
            })
            .collect();
    }

    let mut results: Vec<CommandSearchResult> = Vec::new();

    for command in commands {
        // Search in name
        if let Some((score, indices)) = fuzzy_match(query, &command.name) {
            results.push(CommandSearchResult {
                command: command.clone(),
                score,
                matched_indices: indices,
            });
            continue;
        }

        // Search in description
        if let Some((score, indices)) = fuzzy_match(query, &command.description) {
            results.push(CommandSearchResult {
                command: command.clone(),
                score: score * 0.8,
                matched_indices: indices,
            });
            continue;
        }

        // Search in keywords
        for keyword in &command.keywords {
            if let Some((score, indices)) = fuzzy_match(query, keyword) {
                results.push(CommandSearchResult {
                    command: command.clone(),
                    score: score * 0.6,
                    matched_indices: indices,
                });
                break;
            }
        }
    }

    // Sort by score descending
    results.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    results
}

// ---------------------------------------------------------------------------
// CommandPaletteStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct CommandPaletteStore {
    pub is_open: RwSignal<bool>,
    pub mode: RwSignal<String>,
    pub query: RwSignal<String>,
    pub selected_index: RwSignal<i32>,
    pub commands: RwSignal<Vec<Command>>,
    pub filtered_results: RwSignal<Vec<CommandSearchResult>>,
    pub recent_commands: RwSignal<Vec<String>>,
    pub groups: RwSignal<Vec<CommandGroup>>,
}

impl CommandPaletteStore {
    pub fn new() -> Self {
        Self {
            is_open: RwSignal::new(false),
            mode: RwSignal::new("commands".to_string()),
            query: RwSignal::new(String::new()),
            selected_index: RwSignal::new(0),
            commands: RwSignal::new(Vec::new()),
            filtered_results: RwSignal::new(Vec::new()),
            recent_commands: RwSignal::new(Vec::new()),
            groups: RwSignal::new(Vec::new()),
        }
    }

    // -----------------------------------------------------------------------
    // Open / Close
    // -----------------------------------------------------------------------

    pub fn open(&self, new_mode: Option<&str>) {
        self.is_open.set(true);
        if let Some(m) = new_mode {
            self.mode.set(m.to_string());
        } else {
            self.mode.set("commands".to_string());
        }
        self.query.set(String::new());
        self.selected_index.set(0);
        self.run_search();
    }

    pub fn close(&self) {
        self.is_open.set(false);
        self.query.set(String::new());
        self.selected_index.set(0);
    }

    pub fn toggle(&self) {
        if self.is_open.get() {
            self.close();
        } else {
            self.open(None);
        }
    }

    // -----------------------------------------------------------------------
    // Query
    // -----------------------------------------------------------------------

    pub fn set_query(&self, new_query: &str) {
        self.query.set(new_query.to_string());
        self.selected_index.set(0);
        self.run_search();
    }

    pub fn clear_query(&self) {
        self.query.set(String::new());
        self.run_search();
    }

    // -----------------------------------------------------------------------
    // Navigation
    // -----------------------------------------------------------------------

    pub fn select_next(&self) {
        let count = self.filtered_results.get().len() as i32;
        if count > 0 {
            self.selected_index.update(|i| *i = (*i + 1) % count);
        }
    }

    pub fn select_previous(&self) {
        let count = self.filtered_results.get().len() as i32;
        if count > 0 {
            self.selected_index
                .update(|i| *i = (*i - 1 + count) % count);
        }
    }

    pub fn select_index(&self, index: i32) {
        self.selected_index.set(index);
    }

    fn run_search(&self) {
        let query = self.query.get();
        let commands = self.commands.get();

        // Boost recent commands
        let recent = self.recent_commands.get();
        let mut results = search_commands(&commands, &query);

        // Boost results matching recent commands
        for result in &mut results {
            if recent.contains(&result.command.id) {
                result.score += 0.15;
            }
        }

        results.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        self.filtered_results.set(results);
    }

    // -----------------------------------------------------------------------
    // Command execution
    // -----------------------------------------------------------------------

    pub async fn execute_selected(&self) {
        let results = self.filtered_results.get();
        let idx = self.selected_index.get() as usize;
        if idx < results.len() {
            let cmd = results[idx].command.clone();
            self.add_to_recent(&cmd.id);
            self.execute_command_internal(&cmd).await;
        }
    }

    pub async fn execute_command(&self, command_id: &str) {
        let commands = self.commands.get();
        if let Some(cmd) = commands.into_iter().find(|c| c.id == command_id) {
            self.add_to_recent(&cmd.id);
            self.execute_command_internal(&cmd).await;
        }
    }

    async fn execute_command_internal(&self, command: &Command) {
        // For WASM context, execute the action
        match command.action_type.as_str() {
            "navigate" => {
                // Navigation would use the router
                // In a full implementation, this would call the Leptos router
                // self.close();
            }
            "create" => {
                // Create entity — would open a modal
                // self.close();
            }
            "execute" => {
                // Execute an action
            }
            "toggle" => {
                // Toggle a setting
            }
            _ => {}
        }
    }

    // -----------------------------------------------------------------------
    // Command registration
    // -----------------------------------------------------------------------

    pub fn register_command(&self, command: Command) {
        self.commands.update(|cmds| {
            if !cmds.iter().any(|c| c.id == command.id) {
                cmds.push(command);
            }
        });
        self.run_search();
    }

    pub fn register_commands(&self, new_commands: Vec<Command>) {
        self.commands.update(|cmds| {
            for cmd in new_commands {
                if !cmds.iter().any(|c| c.id == cmd.id) {
                    cmds.push(cmd);
                }
            }
        });
        self.run_search();
    }

    pub fn unregister_command(&self, command_id: &str) {
        self.commands.update(|cmds| {
            cmds.retain(|c| c.id != command_id);
        });
        self.run_search();
    }

    // -----------------------------------------------------------------------
    // Recent commands
    // -----------------------------------------------------------------------

    fn add_to_recent(&self, command_id: &str) {
        self.recent_commands.update(|recent| {
            recent.retain(|id| id != command_id);
            recent.insert(0, command_id.to_string());
            if recent.len() > 20 {
                recent.pop();
            }
        });
    }
}

impl Default for CommandPaletteStore {
    fn default() -> Self {
        Self::new()
    }
}
