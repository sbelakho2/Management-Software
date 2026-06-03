//! Quality management page — NCRs, CAPAs, Inspections, Audits, Suppliers.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::quality::QualityApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Quality management parent page with navigation to sub-pages.
#[component]
pub fn QualityPage() -> impl IntoView {
    let _app_state = use_context::<AppState>().expect("AppState not provided");

    view! {
        <Module title="QUALITY".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all NCRs.
#[component]
pub fn NcrListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let ncrs = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { QualityApi::list_ncrs(&client).await }
    });

    let columns = vec![
        TableColumn { label: "TITLE", key: "title", sortable: true, width: None },
        TableColumn { label: "SEVERITY", key: "severity", sortable: true, width: Some("80px") },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "SOURCE", key: "source", sortable: true, width: None },
        TableColumn { label: "ASSIGNED TO", key: "assigned_to", sortable: true, width: None },
        TableColumn { label: "CREATED", key: "created_at", sortable: true, width: None },
    ];

    view! {
        <Module title="NCRs".to_string()>
            {move || ncrs.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|ncr| {
                        view! {
                            <td>{ncr.title}</td>
                            <td><span class=format!("rams-badge severity-{}", ncr.severity.to_lowercase())>{ncr.severity.clone()}</span></td>
                            <td><span class=format!("rams-badge status-{}", ncr.status.to_lowercase())>{ncr.status.clone()}</span></td>
                            <td>{ncr.source}</td>
                            <td>{ncr.assigned_to.unwrap_or_else(|| "—".into())}</td>
                            <td>{ncr.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load NCRs: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all CAPAs.
#[component]
pub fn CapaListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let capas = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { QualityApi::list_capas(&client).await }
    });

    let columns = vec![
        TableColumn { label: "ROOT CAUSE", key: "root_cause", sortable: true, width: None },
        TableColumn { label: "ACTION PLAN", key: "action_plan", sortable: true, width: None },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "DUE DATE", key: "due_date", sortable: true, width: None },
        TableColumn { label: "ASSIGNED TO", key: "assigned_to", sortable: true, width: None },
    ];

    view! {
        <Module title="CAPAs".to_string()>
            {move || capas.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|capa| {
                        view! {
                            <td>{capa.root_cause}</td>
                            <td>{capa.action_plan}</td>
                            <td><span class=format!("rams-badge status-{}", capa.status.to_lowercase())>{capa.status.clone()}</span></td>
                            <td>{capa.due_date.unwrap_or_else(|| "—".into())}</td>
                            <td>{capa.assigned_to.unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load CAPAs: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all Inspections.
#[component]
pub fn InspectionListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let inspections = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { QualityApi::list_inspections(&client).await }
    });

    let columns = vec![
        TableColumn { label: "TITLE", key: "title", sortable: true, width: None },
        TableColumn { label: "TYPE", key: "inspection_type", sortable: true, width: None },
        TableColumn { label: "RESULT", key: "result", sortable: true, width: None },
        TableColumn { label: "INSPECTOR", key: "inspector", sortable: true, width: None },
        TableColumn { label: "DATE", key: "created_at", sortable: true, width: None },
    ];

    view! {
        <Module title="INSPECTIONS".to_string()>
            {move || inspections.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|i| {
                        view! {
                            <td>{i.title}</td>
                            <td>{i.inspection_type}</td>
                            <td><span class=format!("rams-badge result-{}", i.result.to_lowercase())>{i.result.clone()}</span></td>
                            <td>{i.inspector}</td>
                            <td>{i.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load inspections: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all Audits.
#[component]
pub fn AuditListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let audits = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { QualityApi::list_audits(&client).await }
    });

    let columns = vec![
        TableColumn { label: "TYPE", key: "audit_type", sortable: true, width: None },
        TableColumn { label: "SCOPE", key: "scope", sortable: true, width: None },
        TableColumn { label: "SCORE", key: "score", sortable: true, width: Some("60px") },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "CONDUCTED BY", key: "conducted_by", sortable: true, width: None },
        TableColumn { label: "COMPLETED", key: "completed_at", sortable: true, width: None },
    ];

    view! {
        <Module title="AUDITS".to_string()>
            {move || audits.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|a| {
                        view! {
                            <td>{a.audit_type}</td>
                            <td>{a.scope}</td>
                            <td>{a.score.map(|s| format!("{:.1}", s)).unwrap_or_else(|| "—".into())}</td>
                            <td><span class=format!("rams-badge status-{}", a.status.to_lowercase())>{a.status.clone()}</span></td>
                            <td>{a.conducted_by}</td>
                            <td>{a.completed_at.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load audits: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List supplier evaluations.
#[component]
pub fn SupplierEvalListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let evals = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { QualityApi::list_supplier_evals(&client).await }
    });

    let columns = vec![
        TableColumn { label: "SUPPLIER", key: "supplier_name", sortable: true, width: None },
        TableColumn { label: "SCORE", key: "score", sortable: true, width: Some("60px") },
        TableColumn { label: "TIER", key: "tier", sortable: true, width: Some("60px") },
        TableColumn { label: "EVALUATED BY", key: "evaluated_by", sortable: true, width: None },
        TableColumn { label: "DATE", key: "evaluated_at", sortable: true, width: None },
    ];

    view! {
        <Module title="SUPPLIER EVALUATIONS".to_string()>
            {move || evals.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|s| {
                        view! {
                            <td>{s.supplier_name}</td>
                            <td>{format!("{:.1}", s.score)}</td>
                            <td><span class=format!("rams-badge tier-{}", s.tier.to_lowercase())>{s.tier.clone()}</span></td>
                            <td>{s.evaluated_by}</td>
                            <td>{s.evaluated_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load evaluations: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
