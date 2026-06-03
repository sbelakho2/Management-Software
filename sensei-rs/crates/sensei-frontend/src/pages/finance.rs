//! Finance management page — Invoices, Payments, Budgets, Journal Entries, Cost Rollups.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::finance::FinanceApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Finance management parent page.
#[component]
pub fn FinancePage() -> impl IntoView {
    view! {
        <Module title="FINANCE".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all invoices.
#[component]
pub fn InvoiceListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { FinanceApi::list_invoices(&client).await }
    });

    let columns = vec![
        TableColumn { label: "INVOICE #", key: "invoice_number", sortable: true, width: None },
        TableColumn { label: "CUSTOMER", key: "customer_id", sortable: true, width: None },
        TableColumn { label: "SUBTOTAL", key: "subtotal", sortable: true, width: None },
        TableColumn { label: "TAX", key: "tax", sortable: true, width: None },
        TableColumn { label: "TOTAL", key: "total", sortable: true, width: None },
        TableColumn { label: "CURRENCY", key: "currency", sortable: true, width: Some("80px") },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "DUE DATE", key: "due_date", sortable: true, width: None },
    ];

    view! {
        <Module title="INVOICES".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|inv| {
                        view! {
                            <td>{inv.invoice_number}</td>
                            <td>{inv.customer_id}</td>
                            <td>{format!("{:.2}", inv.subtotal)}</td>
                            <td>{format!("{:.2}", inv.tax)}</td>
                            <td><strong>{format!("{:.2}", inv.total)}</strong></td>
                            <td>{inv.currency}</td>
                            <td><span class=format!("rams-badge status-{}", inv.status.to_lowercase())>{inv.status.clone()}</span></td>
                            <td>{inv.due_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load invoices: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all payments.
#[component]
pub fn PaymentListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { FinanceApi::list_payments(&client).await }
    });

    let columns = vec![
        TableColumn { label: "PAYMENT #", key: "payment_number", sortable: true, width: None },
        TableColumn { label: "INVOICE", key: "invoice_id", sortable: true, width: None },
        TableColumn { label: "AMOUNT", key: "amount", sortable: true, width: None },
        TableColumn { label: "CURRENCY", key: "currency", sortable: true, width: Some("80px") },
        TableColumn { label: "METHOD", key: "method", sortable: true, width: None },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "PAID AT", key: "paid_at", sortable: true, width: None },
    ];

    view! {
        <Module title="PAYMENTS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|p| {
                        view! {
                            <td>{p.payment_number}</td>
                            <td>{p.invoice_id}</td>
                            <td>{format!("{:.2}", p.amount)}</td>
                            <td>{p.currency}</td>
                            <td>{p.method}</td>
                            <td><span class=format!("rams-badge status-{}", p.status.to_lowercase())>{p.status.clone()}</span></td>
                            <td>{p.paid_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load payments: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all budgets.
#[component]
pub fn BudgetListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { FinanceApi::list_budgets(&client).await }
    });

    let columns = vec![
        TableColumn { label: "DEPARTMENT", key: "department", sortable: true, width: None },
        TableColumn { label: "FISCAL YEAR", key: "fiscal_year", sortable: true, width: None },
        TableColumn { label: "ALLOCATED", key: "allocated", sortable: true, width: None },
        TableColumn { label: "SPENT", key: "spent", sortable: true, width: None },
        TableColumn { label: "REMAINING", key: "remaining", sortable: true, width: None },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
    ];

    view! {
        <Module title="BUDGETS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|b| {
                        view! {
                            <td>{b.department}</td>
                            <td>{b.fiscal_year}</td>
                            <td>{format!("{:.2}", b.allocated)}</td>
                            <td>{format!("{:.2}", b.spent)}</td>
                            <td>{format!("{:.2}", b.remaining)}</td>
                            <td><span class=format!("rams-badge status-{}", b.status.to_lowercase())>{b.status.clone()}</span></td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load budgets: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all journal entries.
#[component]
pub fn JournalEntryListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { FinanceApi::list_journal_entries(&client).await }
    });

    let columns = vec![
        TableColumn { label: "ENTRY #", key: "entry_number", sortable: true, width: None },
        TableColumn { label: "DESCRIPTION", key: "description", sortable: true, width: None },
        TableColumn { label: "DEBIT", key: "debit", sortable: true, width: None },
        TableColumn { label: "CREDIT", key: "credit", sortable: true, width: None },
        TableColumn { label: "ACCOUNT", key: "account", sortable: true, width: None },
        TableColumn { label: "POSTED AT", key: "posted_at", sortable: true, width: None },
    ];

    view! {
        <Module title="JOURNAL ENTRIES".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|je| {
                        view! {
                            <td>{je.entry_number}</td>
                            <td>{je.description}</td>
                            <td>{format!("{:.2}", je.debit)}</td>
                            <td>{format!("{:.2}", je.credit)}</td>
                            <td>{je.account}</td>
                            <td>{je.posted_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load journal entries: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all cost rollups.
#[component]
pub fn CostRollupListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { FinanceApi::list_cost_rollups(&client).await }
    });

    let columns = vec![
        TableColumn { label: "PRODUCT", key: "product_id", sortable: true, width: None },
        TableColumn { label: "MATERIAL", key: "material_cost", sortable: true, width: None },
        TableColumn { label: "LABOR", key: "labor_cost", sortable: true, width: None },
        TableColumn { label: "OVERHEAD", key: "overhead_cost", sortable: true, width: None },
        TableColumn { label: "TOTAL", key: "total_cost", sortable: true, width: None },
        TableColumn { label: "CURRENCY", key: "currency", sortable: true, width: Some("80px") },
        TableColumn { label: "CALCULATED AT", key: "calculated_at", sortable: true, width: None },
    ];

    view! {
        <Module title="COST ROLLUPS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|cr| {
                        view! {
                            <td>{cr.product_id}</td>
                            <td>{format!("{:.2}", cr.material_cost)}</td>
                            <td>{format!("{:.2}", cr.labor_cost)}</td>
                            <td>{format!("{:.2}", cr.overhead_cost)}</td>
                            <td><strong>{format!("{:.2}", cr.total_cost)}</strong></td>
                            <td>{cr.currency}</td>
                            <td>{cr.calculated_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load cost rollups: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
