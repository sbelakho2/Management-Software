//! Maintenance management page — Work Requests, PM Schedules, Equipment.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::maintenance::MaintenanceApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Maintenance management parent page.
#[component]
pub fn MaintenancePage() -> impl IntoView {
    view! {
        <Module title="MAINTENANCE".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all maintenance work requests.
#[component]
pub fn WorkRequestListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let wrs = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { MaintenanceApi::list_work_requests(&client).await }
    });

    let columns = vec![
        TableColumn { label: "REQUEST #", key: "request_number", sortable: true, width: None },
        TableColumn { label: "TITLE", key: "title", sortable: true, width: None },
        TableColumn { label: "PRIORITY", key: "priority", sortable: true, width: Some("80px") },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "ASSET", key: "asset_id", sortable: true, width: None },
        TableColumn { label: "ASSIGNED TO", key: "assigned_to", sortable: true, width: None },
        TableColumn { label: "CREATED", key: "created_at", sortable: true, width: None },
    ];

    view! {
        <Module title="WORK REQUESTS".to_string()>
            {move || wrs.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|wr| {
                        view! {
                            <td>{wr.request_number}</td>
                            <td>{wr.title}</td>
                            <td><span class=format!("rams-badge priority-{}", wr.priority.to_lowercase())>{wr.priority.clone()}</span></td>
                            <td><span class=format!("rams-badge status-{}", wr.status.to_lowercase())>{wr.status.clone()}</span></td>
                            <td>{wr.asset_id.unwrap_or_else(|| "—".into())}</td>
                            <td>{wr.assigned_to.unwrap_or_else(|| "—".into())}</td>
                            <td>{wr.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load work requests: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all PM schedules.
#[component]
pub fn PmScheduleListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let pms = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { MaintenanceApi::list_pm_schedules(&client).await }
    });

    let columns = vec![
        TableColumn { label: "SCHEDULE #", key: "schedule_number", sortable: true, width: None },
        TableColumn { label: "TITLE", key: "title", sortable: true, width: None },
        TableColumn { label: "ASSET", key: "asset_id", sortable: true, width: None },
        TableColumn { label: "FREQUENCY (DAYS)", key: "frequency_days", sortable: true, width: Some("120px") },
        TableColumn { label: "LAST DONE", key: "last_performed", sortable: true, width: None },
        TableColumn { label: "NEXT DUE", key: "next_due", sortable: true, width: None },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
    ];

    view! {
        <Module title="PM SCHEDULES".to_string()>
            {move || pms.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|pm| {
                        view! {
                            <td>{pm.schedule_number}</td>
                            <td>{pm.title}</td>
                            <td>{pm.asset_id}</td>
                            <td>{pm.frequency_days}</td>
                            <td>{pm.last_performed.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{pm.next_due[..10].to_string()}</td>
                            <td><span class=format!("rams-badge status-{}", pm.status.to_lowercase())>{pm.status.clone()}</span></td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load PM schedules: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all equipment.
#[component]
pub fn EquipmentListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let equip = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { MaintenanceApi::list_equipment(&client).await }
    });

    let columns = vec![
        TableColumn { label: "CODE", key: "equipment_code", sortable: true, width: None },
        TableColumn { label: "NAME", key: "name", sortable: true, width: None },
        TableColumn { label: "TYPE", key: "equipment_type", sortable: true, width: None },
        TableColumn { label: "LOCATION", key: "location", sortable: true, width: None },
        TableColumn { label: "STATUS", key: "status", sortable: true, width: Some("90px") },
        TableColumn { label: "SERIAL #", key: "serial_number", sortable: true, width: None },
    ];

    view! {
        <Module title="EQUIPMENT".to_string()>
            {move || equip.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|e| {
                        view! {
                            <td>{e.equipment_code}</td>
                            <td>{e.name}</td>
                            <td>{e.equipment_type}</td>
                            <td>{e.location.unwrap_or_else(|| "—".into())}</td>
                            <td><span class=format!("rams-badge status-{}", e.status.to_lowercase())>{e.status.clone()}</span></td>
                            <td>{e.serial_number.unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load equipment: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
