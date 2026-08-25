//! Operations / Continuous Improvement page — Andon, Projects, A3, Risks.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::ops::OpsApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Operations parent page.
#[component]
pub fn OpsPage() -> impl IntoView {
    view! {
        <Module title="OPERATIONS".to_string()>
            <Outlet />
        </Module>
    }
}

/// List Andon events.
#[component]
pub fn AndonListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { OpsApi::list_andons(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "ANDON #",
            key: "andon_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TITLE",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SEVERITY",
            key: "severity",
            sortable: true,
            width: Some("80px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "LOCATION",
            key: "location",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "RAISED BY",
            key: "raised_by",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "RESPONSE (S)",
            key: "response_time_seconds",
            sortable: true,
            width: Some("100px"),
        },
        TableColumn {
            label: "RESOLUTION (S)",
            key: "resolution_time_seconds",
            sortable: true,
            width: Some("100px"),
        },
        TableColumn {
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="ANDON BOARD".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|a| {
                        view! {
                            <td>{a.andon_number}</td>
                            <td>{a.title}</td>
                            <td><span class=format!("rams-badge severity-{}", a.severity.to_lowercase())>{a.severity.clone()}</span></td>
                            <td><span class=format!("rams-badge status-{}", a.status.to_lowercase())>{a.status.clone()}</span></td>
                            <td>{a.location.unwrap_or_else(|| "—".into())}</td>
                            <td>{a.raised_by}</td>
                            <td>{a.response_time_seconds.map(|s| s.to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{a.resolution_time_seconds.map(|s| s.to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{a.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load andon events: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List projects.
#[component]
pub fn ProjectListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { OpsApi::list_projects(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "PROJECT #",
            key: "project_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "NAME",
            key: "name",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PRIORITY",
            key: "priority",
            sortable: true,
            width: Some("80px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "OWNER",
            key: "owner",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "START",
            key: "start_date",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "END",
            key: "end_date",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="PROJECTS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|p| {
                        view! {
                            <td>{p.project_number}</td>
                            <td>{p.name}</td>
                            <td><span class=format!("rams-badge priority-{}", p.priority.to_lowercase())>{p.priority.clone()}</span></td>
                            <td><span class=format!("rams-badge status-{}", p.status.to_lowercase())>{p.status.clone()}</span></td>
                            <td>{p.owner}</td>
                            <td>{p.start_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{p.end_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load projects: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List A3 reports.
#[component]
pub fn A3ListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { OpsApi::list_a3s(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "A3 #",
            key: "a3_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TITLE",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ROOT CAUSE",
            key: "root_cause",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "OWNER",
            key: "owner",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CLOSED",
            key: "closed_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="A3 REPORTS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|a3| {
                        view! {
                            <td>{a3.a3_number}</td>
                            <td>{a3.title}</td>
                            <td>{a3.root_cause.unwrap_or_else(|| "—".into())}</td>
                            <td><span class=format!("rams-badge status-{}", a3.status.to_lowercase())>{a3.status.clone()}</span></td>
                            <td>{a3.owner}</td>
                            <td>{a3.created_at[..10].to_string()}</td>
                            <td>{a3.closed_at.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load A3 reports: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List risks.
#[component]
pub fn RiskListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { OpsApi::list_risks(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "RISK #",
            key: "risk_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TITLE",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "LIKELIHOOD",
            key: "likelihood",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "IMPACT",
            key: "impact",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SCORE",
            key: "risk_score",
            sortable: true,
            width: Some("60px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "OWNER",
            key: "owner",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="RISKS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|r| {
                        view! {
                            <td>{r.risk_number}</td>
                            <td>{r.title}</td>
                            <td>{r.likelihood}</td>
                            <td>{r.impact}</td>
                            <td><strong>{r.risk_score}</strong></td>
                            <td><span class=format!("rams-badge status-{}", r.status.to_lowercase())>{r.status.clone()}</span></td>
                            <td>{r.owner}</td>
                            <td>{r.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load risks: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
