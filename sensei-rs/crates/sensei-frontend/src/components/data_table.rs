//! Industrial data table component.
//!
//! Provides a [`DataTable`] for tabular data following the Rams design system
//! section 5.1. The table features a recessed chassis, monospaced header labels,
//! and zebra-striped rows for scanning clarity.

use leptos::prelude::*;

/// Describes a single column in a [`DataTable`].
#[derive(Debug, Clone)]
pub struct TableColumn {
    /// Human-readable column header label.
    pub label: &'static str,
    /// Machine-readable key (for data access).
    pub key: &'static str,
    /// Whether this column supports sorting.
    pub sortable: bool,
    /// Optional CSS width value (e.g. `"100px"`, `"15%"`).
    pub width: Option<&'static str>,
}

/// Industrial data table with header and row body.
///
/// Renders a `<table>` inside a scrollable container. Each row should contain
/// `<td>` elements matching the column definition order.
///
/// # Type Parameters
///
/// * `T` — The row type, which must implement [`IntoView`].
///
/// # Example
///
/// ```ignore
/// let columns = vec![
///     TableColumn { label: "ID", key: "id", sortable: true, width: Some("60px") },
///     TableColumn { label: "Name", key: "name", sortable: true, width: None },
/// ];
/// let rows: Vec<HtmlElement<HtmlTrElement>> = data.iter().map(|item| {
///     view! { <td>{item.id}</td><td>{item.name}</td> }
/// }).collect();
///
/// <DataTable columns=columns rows=rows />
/// ```
#[component]
pub fn DataTable<T>(
    /// Column definitions.
    columns: Vec<TableColumn>,
    /// Row content — each element becomes a `<tr>`.
    rows: Vec<T>,
    /// Additional CSS classes to append.
    #[prop(optional)]
    class: String,
) -> impl IntoView
where
    T: IntoView + 'static,
{
    view! {
        <div class=format!("rams-table-container {}", class) role="region" aria-label="Data table">
            <table class="rams-table">
                <thead>
                    <tr>
                        {columns
                            .iter()
                            .map(|col| {
                                view! {
                                    <th class="rams-table-header" scope="col" aria-sort=if col.sortable { "none" } else { "" }>
                                        {col.label}
                                    </th>
                                }
                            })
                            .collect::<Vec<_>>()}
                    </tr>
                </thead>
                <tbody>
                    {rows
                        .into_iter()
                        .map(|row| {
                            view! { <tr>{row}</tr> }
                        })
                        .collect::<Vec<_>>()}
                </tbody>
            </table>
        </div>
    }
}
