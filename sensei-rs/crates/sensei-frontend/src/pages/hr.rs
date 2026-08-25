//! Human Resources page — Employees, Training, Leave, Reviews, Timecards.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::hr::HrApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// HR management parent page.
#[component]
pub fn HrPage() -> impl IntoView {
    view! {
        <Module title="HUMAN RESOURCES".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all employees.
#[component]
pub fn EmployeeListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { HrApi::list_employees(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "CODE",
            key: "employee_code",
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
            label: "EMAIL",
            key: "email",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "DEPARTMENT",
            key: "department",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "POSITION",
            key: "position",
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
            label: "HIRE DATE",
            key: "hire_date",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="EMPLOYEES".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|e| {
                        view! {
                            <td>{e.employee_code}</td>
                            <td>{e.name}</td>
                            <td>{e.email}</td>
                            <td>{e.department}</td>
                            <td>{e.position}</td>
                            <td><span class=format!("rams-badge status-{}", e.status.to_lowercase())>{e.status.clone()}</span></td>
                            <td>{e.hire_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load employees: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all training records.
#[component]
pub fn TrainingListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { HrApi::list_training_records(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "EMPLOYEE",
            key: "employee_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "COURSE",
            key: "course_name",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "COMPLETED",
            key: "completed_at",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "EXPIRES",
            key: "expires_at",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SCORE",
            key: "score",
            sortable: true,
            width: Some("60px"),
        },
    ];

    view! {
        <Module title="TRAINING".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|t| {
                        view! {
                            <td>{t.employee_id}</td>
                            <td>{t.course_name}</td>
                            <td>{t.completed_at[..10].to_string()}</td>
                            <td>{t.expires_at.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{t.score.map(|s| format!("{:.1}", s)).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load training records: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all leave requests.
#[component]
pub fn LeaveListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { HrApi::list_leave_requests(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "EMPLOYEE",
            key: "employee_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TYPE",
            key: "leave_type",
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
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "APPROVED BY",
            key: "approved_by",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="LEAVE REQUESTS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|l| {
                        view! {
                            <td>{l.employee_id}</td>
                            <td>{l.leave_type}</td>
                            <td>{l.start_date[..10].to_string()}</td>
                            <td>{l.end_date[..10].to_string()}</td>
                            <td><span class=format!("rams-badge status-{}", l.status.to_lowercase())>{l.status.clone()}</span></td>
                            <td>{l.approved_by.unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load leave requests: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all performance reviews.
#[component]
pub fn ReviewListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { HrApi::list_reviews(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "EMPLOYEE",
            key: "employee_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "REVIEWER",
            key: "reviewer_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "RATING",
            key: "rating",
            sortable: true,
            width: Some("60px"),
        },
        TableColumn {
            label: "COMMENTS",
            key: "comments",
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
            label: "REVIEW DATE",
            key: "review_date",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="REVIEWS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|r| {
                        view! {
                            <td>{r.employee_id}</td>
                            <td>{r.reviewer_id}</td>
                            <td>{r.rating}</td>
                            <td>{r.comments.unwrap_or_else(|| "—".into())}</td>
                            <td><span class=format!("rams-badge status-{}", r.status.to_lowercase())>{r.status.clone()}</span></td>
                            <td>{r.review_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load reviews: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all timecards.
#[component]
pub fn TimecardListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { HrApi::list_timecards(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "EMPLOYEE",
            key: "employee_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CLOCK IN",
            key: "clock_in",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CLOCK OUT",
            key: "clock_out",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TOTAL HOURS",
            key: "total_hours",
            sortable: true,
            width: Some("90px"),
        },
    ];

    view! {
        <Module title="TIMECARDS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|t| {
                        view! {
                            <td>{t.employee_id}</td>
                            <td>{t.clock_in[..19].to_string()}</td>
                            <td>{t.clock_out.as_ref().map(|d| d[..19].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{t.total_hours.map(|h| format!("{:.1}", h)).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load timecards: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
