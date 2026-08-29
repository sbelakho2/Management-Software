//! Industrial DataTable components (item 45): REAL sorting — the old
//! component only advertised `aria-sort` with no behavior. Two components:
//!
//! - [`DataTable`] — legacy-compatible: `rows` are already-rendered views
//!   (each containing `<td>`s). Now with caption, explicit states,
//!   pagination and REAL sorting via `sort_by`.
//! - [`DataTableData`] — data mode: typed rows + `render_row` + `sort_by`
//!   extractor; the header click REALLY re-orders the rows.
//!
//! A failed request renders an explicit ERROR state — never a healthy
//! empty table (item 4).

use leptos::prelude::*;
use std::sync::Arc;

/// Column definition.
#[derive(Debug, Clone)]
pub struct TableColumn {
    pub label: &'static str,
    /// Stable key used for sorting.
    pub key: &'static str,
    pub sortable: bool,
    pub width: Option<&'static str>,
}

/// Operational table state (item 45): Loading / Normal / Stale / Error are
/// explicit — a failed request renders an error banner, never a healthy
/// empty table.
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub enum TableState {
    Loading,
    #[default]
    Normal,
    Stale,
    Error,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SortDirection {
    Asc,
    Desc,
}

/// Data-mode row renderer: maps one item to its `<td>` cells.
pub type RowRenderer<T> = Arc<dyn Fn(T) -> Vec<leptos::prelude::AnyView> + Send + Sync>;
/// Sort-value extractor: maps an item + column key to a comparable string.
pub type SortExtractor<T> = Arc<dyn Fn(&T, &str) -> String + Send + Sync>;
/// Pagination callback.
pub type PageCallback = Arc<dyn Fn(u32) + Send + Sync + 'static>;

/// Numeric-aware string comparison: "10" > "9".
fn compare_values(a: &str, b: &str) -> std::cmp::Ordering {
    let a_num = a.trim().parse::<f64>();
    let b_num = b.trim().parse::<f64>();
    match (a_num, b_num) {
        (Ok(x), Ok(y)) => x.partial_cmp(&y).unwrap_or(std::cmp::Ordering::Equal),
        _ => a.to_lowercase().cmp(&b.to_lowercase()),
    }
}

/// The shared table chrome: caption, state chrome, pagination, and the
/// real sort state. Returns the reactive sort signal so both components
/// can wire the header clicks.
fn sort_state_signal() -> RwSignal<Option<(String, SortDirection)>> {
    RwSignal::new(None)
}

/// Legacy-compatible operational table: `rows` are already-rendered views
/// (each containing the `<td>`s). `sort_by` (optional) extracts the sort
/// value for a column key — when present, header clicks REALLY re-order.
#[component]
pub fn DataTable<T>(
    columns: Vec<TableColumn>,
    /// Pre-rendered row views (each containing `<td>` elements).
    rows: Vec<T>,
    /// Extracts the sort value for a column key (enables REAL sorting).
    #[prop(optional)]
    sort_by: Option<SortExtractor<T>>,
    /// Table state: Loading / Normal / Stale / Error.
    #[prop(optional)]
    state: TableState,
    /// Contextual accessible name (item 45); falls back to a generic label.
    #[prop(optional)]
    caption: Option<String>,
    /// Server-style pagination.
    #[prop(optional)]
    page: u32,
    #[prop(optional)] total_pages: u32,
    #[prop(optional)] on_page: Option<Arc<dyn Fn(u32) + Send + Sync + 'static>>,
    /// Additional CSS classes.
    #[prop(optional)]
    class: String,
) -> impl IntoView
where
    T: Clone + IntoView + 'static,
{
    let sort_state = sort_state_signal();
    let caption_for_table = caption.clone().unwrap_or_else(|| "Data table".to_string());

    let sorted_rows = {
        let rows = rows;
        let sort_by = sort_by.clone();
        move || {
            let Some((key, dir)) = sort_state.get() else {
                return rows.clone();
            };
            let Some(extract) = sort_by.as_ref() else {
                return rows.clone();
            };
            let mut sorted = rows.clone();
            sorted.sort_by(|a, b| {
                let va = extract(a, &key);
                let vb = extract(b, &key);
                match dir {
                    SortDirection::Asc => compare_values(&va, &vb),
                    SortDirection::Desc => compare_values(&vb, &va),
                }
            });
            sorted
        }
    };

    view! {
        <div class=format!("rams-table-container {}", class) role="region" aria-label=caption_for_table.clone()>
            <table class="rams-table">
                <caption class="rams-sr-only">{caption_for_table.clone()}</caption>
                <thead>
                    <tr>
                        {columns
                            .iter()
                            .map(|col| {
                                let col_key = col.key;
                                let sortable = col.sortable;
                                let on_sort = sort_state;
                                let dir = move || {
                                    on_sort
                                        .get()
                                        .and_then(|(k, d)| if k.as_str() == col_key { Some(d) } else { None })
                                };
                                let aria_sort = move || match dir() {
                                    Some(SortDirection::Asc) => "ascending",
                                    Some(SortDirection::Desc) => "descending",
                                    None => "none",
                                };
                                let label = col.label;
                                view! {
                                    <th
                                        class="rams-table-header"
                                        scope="col"
                                        aria-sort=aria_sort
                                        style=col.width.map(|w| format!("width: {w};")).unwrap_or_default()
                                    >
                                        {if sortable {
                                            view! {
                                                <button
                                                    type="button"
                                                    class="rams-table-sort"
                                                    aria-label=format!("Sort by {label}")
                                                    on:click=move |_| {
                                                        let current = on_sort.get();
                                                        let next = match current {
                                                            None => Some((col_key.to_string(), SortDirection::Asc)),
                                                            Some((k, SortDirection::Asc)) if k == col_key => {
                                                                Some((col_key.to_string(), SortDirection::Desc))
                                                            }
                                                            Some((k, SortDirection::Desc)) if k == col_key => None,
                                                            Some(_) => Some((col_key.to_string(), SortDirection::Asc)),
                                                        };
                                                        on_sort.set(next);
                                                    }
                                                >
                                                    {label}
                                                    {move || match dir() {
                                                        Some(SortDirection::Asc) => " ▲",
                                                        Some(SortDirection::Desc) => " ▼",
                                                        None => "",
                                                    }}
                                                </button>
                                            }.into_any()
                                        } else {
                                            view! { <span>{label}</span> }.into_any()
                                        }}
                                    </th>
                                }
                            })
                            .collect::<Vec<_>>()}
                    </tr>
                </thead>
                <tbody>
                    {move || match state {
                        TableState::Loading => view! {
                            <tr><td colspan=columns.len()>
                                <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted); padding: var(--rams-space-4);">
                                    "LOADING…"
                                </p>
                            </td></tr>
                        }.into_any(),
                        TableState::Error => view! {
                            <tr><td colspan=columns.len()>
                                <div class="rams-alert rams-alert--danger" role="alert">
                                    <strong>"STATUS UNKNOWN — DATA UNAVAILABLE"</strong>
                                    <span>" "</span>
                                    "The request failed; zero rows would be a LIE about the condition."
                                </div>
                            </td></tr>
                        }.into_any(),
                        TableState::Stale => view! {
                            <tr><td colspan=columns.len()>
                                <div class="rams-alert rams-alert--warning" role="status">
                                    <strong>"STALE"</strong>
                                    <span>" "</span>
                                    "The data shown may be out of date (realtime disconnected or refresh failed)."
                                </div>
                            </td></tr>
                        }.into_any(),
                        _ => {
                            let items = sorted_rows();
                            if items.is_empty() {
                                view! {
                                    <tr><td colspan=columns.len()>
                                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted); padding: var(--rams-space-4);">
                                            "NO RECORDS — a confirmed empty state, not a failed request."
                                        </p>
                                    </td></tr>
                                }.into_any()
                            } else {
                                view! {
                                    {items.into_iter().map(|row| {
                                        view! { <tr>{row}</tr> }
                                    }).collect::<Vec<_>>()}
                                }.into_any()
                            }
                        }
                    }}
                </tbody>
            </table>
            <PaginationBar page=page total_pages=total_pages on_page=on_page />
        </div>
    }
}

/// Data-mode operational table: typed rows + `render_row` (produces the
/// `<td>` cells) + a `sort_by` extractor — the header click REALLY
/// re-orders the rows. Row actions render in a trailing column.
#[component]
pub fn DataTableData<T>(
    columns: Vec<TableColumn>,
    rows: Vec<T>,
    /// Renders one data row into its `<td>` cells.
    render_row: RowRenderer<T>,
    /// Extracts the sort value for a column key (enables REAL sorting).
    #[prop(optional)]
    sort_by: Option<SortExtractor<T>>,
    /// Table state: Loading / Normal / Stale / Error.
    #[prop(optional)]
    state: TableState,
    /// Contextual accessible name (item 45).
    caption: Option<String>,
    /// Row actions rendered in the trailing column.
    #[prop(optional)]
    row_actions: Vec<RowAction<T>>,
    /// Server-style pagination.
    #[prop(optional)]
    page: u32,
    #[prop(optional)] total_pages: u32,
    #[prop(optional)] on_page: Option<Arc<dyn Fn(u32) + Send + Sync + 'static>>,
    /// Additional CSS classes.
    #[prop(optional)]
    class: String,
) -> impl IntoView
where
    T: Clone + Send + Sync + 'static,
{
    let sort_state = sort_state_signal();
    let caption_for_table = caption.clone().unwrap_or_else(|| "Data table".to_string());
    let has_actions = !row_actions.is_empty();

    let sorted_rows = {
        let rows = rows;
        let sort_by = sort_by.clone();
        move || {
            let Some((key, dir)) = sort_state.get() else {
                return rows.clone();
            };
            let Some(extract) = sort_by.as_ref() else {
                return rows.clone();
            };
            let mut sorted = rows.clone();
            sorted.sort_by(|a, b| {
                let va = extract(a, &key);
                let vb = extract(b, &key);
                match dir {
                    SortDirection::Asc => compare_values(&va, &vb),
                    SortDirection::Desc => compare_values(&vb, &va),
                }
            });
            sorted
        }
    };

    let render = render_row.clone();

    view! {
        <div class=format!("rams-table-container {}", class) role="region" aria-label=caption_for_table.clone()>
            <table class="rams-table">
                <caption class="rams-sr-only">{caption_for_table.clone()}</caption>
                <thead>
                    <tr>
                        {columns
                            .iter()
                            .map(|col| {
                                let col_key = col.key;
                                let sortable = col.sortable;
                                let on_sort = sort_state;
                                let dir = move || {
                                    on_sort
                                        .get()
                                        .and_then(|(k, d)| if k.as_str() == col_key { Some(d) } else { None })
                                };
                                let aria_sort = move || match dir() {
                                    Some(SortDirection::Asc) => "ascending",
                                    Some(SortDirection::Desc) => "descending",
                                    None => "none",
                                };
                                let label = col.label;
                                view! {
                                    <th
                                        class="rams-table-header"
                                        scope="col"
                                        aria-sort=aria_sort
                                        style=col.width.map(|w| format!("width: {w};")).unwrap_or_default()
                                    >
                                        {if sortable {
                                            view! {
                                                <button
                                                    type="button"
                                                    class="rams-table-sort"
                                                    aria-label=format!("Sort by {label}")
                                                    on:click=move |_| {
                                                        let current = on_sort.get();
                                                        let next = match current {
                                                            None => Some((col_key.to_string(), SortDirection::Asc)),
                                                            Some((k, SortDirection::Asc)) if k == col_key => {
                                                                Some((col_key.to_string(), SortDirection::Desc))
                                                            }
                                                            Some((k, SortDirection::Desc)) if k == col_key => None,
                                                            Some(_) => Some((col_key.to_string(), SortDirection::Asc)),
                                                        };
                                                        on_sort.set(next);
                                                    }
                                                >
                                                    {label}
                                                    {move || match dir() {
                                                        Some(SortDirection::Asc) => " ▲",
                                                        Some(SortDirection::Desc) => " ▼",
                                                        None => "",
                                                    }}
                                                </button>
                                            }.into_any()
                                        } else {
                                            view! { <span>{label}</span> }.into_any()
                                        }}
                                    </th>
                                }
                            })
                            .collect::<Vec<_>>()}
                        {if has_actions {
                            view! { <th class="rams-table-header" scope="col" aria-label="Row actions"></th> }.into_any()
                        } else {
                            ().into_any()
                        }}
                    </tr>
                </thead>
                <tbody>
                    {move || match state {
                        TableState::Loading => view! {
                            <tr><td colspan=columns.len() + if has_actions { 1 } else { 0 }>
                                <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted); padding: var(--rams-space-4);">
                                    "LOADING…"
                                </p>
                            </td></tr>
                        }.into_any(),
                        TableState::Error => view! {
                            <tr><td colspan=columns.len() + if has_actions { 1 } else { 0 }>
                                <div class="rams-alert rams-alert--danger" role="alert">
                                    <strong>"STATUS UNKNOWN — DATA UNAVAILABLE"</strong>
                                    <span>" "</span>
                                    "The request failed; zero rows would be a LIE about the condition."
                                </div>
                            </td></tr>
                        }.into_any(),
                        TableState::Stale => view! {
                            <tr><td colspan=columns.len() + if has_actions { 1 } else { 0 }>
                                <div class="rams-alert rams-alert--warning" role="status">
                                    <strong>"STALE"</strong>
                                    <span>" "</span>
                                    "The data shown may be out of date (realtime disconnected or refresh failed)."
                                </div>
                            </td></tr>
                        }.into_any(),
                        _ => {
                            let items = sorted_rows();
                            if items.is_empty() {
                                view! {
                                    <tr><td colspan=columns.len() + if has_actions { 1 } else { 0 }>
                                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted); padding: var(--rams-space-4);">
                                            "NO RECORDS — a confirmed empty state, not a failed request."
                                        </p>
                                    </td></tr>
                                }.into_any()
                            } else {
                                let actions = row_actions.clone();
                                view! {
                                    {items
                                        .into_iter()
                                        .map(|row| {
                                            let row_for_actions = row.clone();
                                            let cells = render(row.clone());
                                            let row_actions = actions.clone();
                                            view! {
                                                <tr>
                                                    {cells.into_iter().map(|c| view! { <td>{c}</td> }).collect::<Vec<_>>()}
                                                    {if has_actions {
                                                        view! {
                                                            <td class="rams-table-actions">
                                                                {row_actions.iter().map(|a| {
                                                                    let kind_class = match a.kind {
                                                                        ActionKind::Primary => "rams-btn--ghost",
                                                                        ActionKind::Ghost => "rams-btn--ghost",
                                                                        ActionKind::Danger => "rams-btn--danger",
                                                                    };
                                                                    let label = a.label.clone();
                                                                    let row = row_for_actions.clone();
                                                                    let cb = a.on_click.clone();
                                                                    view! {
                                                                        <button
                                                                            type="button"
                                                                            class=format!("rams-btn {kind_class} rams-btn--sm")
                                                                            on:click=move |_| { cb(row.clone()); }
                                                                        >
                                                                            {label}
                                                                        </button>
                                                                    }
                                                                }).collect::<Vec<_>>()}
                                                            </td>
                                                        }.into_any()
                                                    } else {
                                                        ().into_any()
                                                    }}
                                                </tr>
                                            }
                                        })
                                        .collect::<Vec<_>>()}
                                }.into_any()
                            }
                        }
                    }}
                </tbody>
            </table>
            <PaginationBar page=page total_pages=total_pages on_page=on_page />
        </div>
    }
}

/// Server-style pagination controls.
#[component]
fn PaginationBar(
    #[prop(optional)] page: u32,
    #[prop(optional)] total_pages: u32,
    on_page: Option<PageCallback>,
) -> impl IntoView {
    move || {
        if total_pages <= 1 {
            return ().into_any();
        }
        let prev_click = on_page.clone();
        let next_click = on_page.clone();
        let current = page;
        let total = total_pages;
        view! {
            <div class="rams-flex rams-flex--between rams-mt-2" style="align-items: center;">
                <span class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                    {format!("PAGE {} / {}", current, total)}
                </span>
                <div class="rams-flex rams-gap-2">
                    <button
                        type="button"
                        class="rams-btn rams-btn--ghost rams-btn--sm"
                        disabled=current <= 1
                        on:click=move |_| {
                            if let Some(ref cb) = prev_click { cb(current.saturating_sub(1).max(1)); }
                        }
                    >
                        "PREV"
                    </button>
                    <button
                        type="button"
                        class="rams-btn rams-btn--ghost rams-btn--sm"
                        disabled=current >= total
                        on:click=move |_| {
                            if let Some(ref cb) = next_click { cb(current.saturating_add(1).min(total)); }
                        }
                    >
                        "NEXT"
                    </button>
                </div>
            </div>
        }
        .into_any()
    }
}

/// A row action (button in the row-actions column).
#[derive(Clone)]
pub struct RowAction<T> {
    pub label: String,
    pub kind: ActionKind,
    pub on_click: RowActionCallback<T>,
}

/// Row-action callback.
pub type RowActionCallback<T> = Arc<dyn Fn(T) + Send + Sync + 'static>;

impl<T> std::fmt::Debug for RowAction<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RowAction")
            .field("label", &self.label)
            .finish()
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ActionKind {
    Primary,
    Ghost,
    Danger,
}
