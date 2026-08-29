//! Production management page — Work Orders, Production Orders, BOM, MRP.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::client::ApiError;
use crate::api::production::{run_mrp_planning, MrpPlanningDto, ProductionApi};
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Production management parent page.
#[component]
pub fn ProductionPage() -> impl IntoView {
    view! {
        <Module title="PRODUCTION".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all work orders.
#[component]
pub fn WorkOrderListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let wos = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { ProductionApi::list_work_orders(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "WO #",
            key: "work_order_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PRODUCT",
            key: "product_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "QTY",
            key: "quantity",
            sortable: true,
            width: Some("60px"),
        },
        TableColumn {
            label: "COMPLETED",
            key: "quantity_completed",
            sortable: true,
            width: Some("80px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PRIORITY",
            key: "priority",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "DUE DATE",
            key: "due_date",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ASSIGNED TO",
            key: "assigned_to",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="WORK ORDERS".to_string()>
            {move || wos.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|wo| {
                        view! {
                            <td>{wo.work_order_number}</td>
                            <td>{wo.product_id}</td>
                            <td>{wo.quantity}</td>
                            <td>{wo.quantity_completed.map(|q| q.to_string()).unwrap_or_else(|| "0".into())}</td>
                            <td><span class=format!("rams-badge status-{}", wo.status.to_lowercase())>{wo.status.clone()}</span></td>
                            <td><span class=format!("rams-badge priority-{}", wo.priority.to_lowercase())>{wo.priority.clone()}</span></td>
                            <td>{wo.due_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{wo.assigned_to.unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load work orders: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all production orders.
#[component]
pub fn ProductionOrderListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let pos = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { ProductionApi::list_production_orders(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "PO #",
            key: "production_order_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PRODUCT",
            key: "product_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PLANNED QTY",
            key: "planned_quantity",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "PRODUCED",
            key: "produced_quantity",
            sortable: true,
            width: Some("80px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "START DATE",
            key: "start_date",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "END DATE",
            key: "end_date",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="PRODUCTION ORDERS".to_string()>
            {move || pos.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|po| {
                        view! {
                            <td>{po.production_order_number}</td>
                            <td>{po.product_id}</td>
                            <td>{po.planned_quantity}</td>
                            <td>{po.produced_quantity.map(|q| q.to_string()).unwrap_or_else(|| "0".into())}</td>
                            <td><span class=format!("rams-badge status-{}", po.status.to_lowercase())>{po.status.clone()}</span></td>
                            <td>{po.start_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                            <td>{po.end_date.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load production orders: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// BOM page (list items for a given product).
#[component]
pub fn BomListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let (product_id, set_product_id) = signal(String::new());
    let bom = ArcLocalResource::new(move || {
        let pid = product_id.get();
        let client = app_state.api_client();
        async move {
            if pid.is_empty() {
                return Ok(Vec::new());
            }
            ProductionApi::get_bom(&client, &pid).await
        }
    });

    let columns = vec![
        TableColumn {
            label: "COMPONENT ID",
            key: "component_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "QUANTITY",
            key: "quantity",
            sortable: true,
            width: Some("80px"),
        },
        TableColumn {
            label: "UNIT",
            key: "unit",
            sortable: true,
            width: Some("60px"),
        },
    ];

    view! {
        <Module title="BILL OF MATERIALS".to_string()>
            <div class="rams-input-group rams-mb-4">
                <label for="bom-product-id" class="rams-label">PRODUCT ID</label>
                <input
                    id="bom-product-id"
                    type="text"
                    class="rams-input"
                    placeholder="Enter Product ID to view BOM..."
                    prop:value=product_id
                    on:input=move |ev| set_product_id.set(event_target_value(&ev))
                />
            </div>
            {move || bom.map(|w| match &**w {
                Ok(list) if list.is_empty() && product_id.get().is_empty() => view! {
                    <p class="rams-text-sm">"Enter a product ID above to view its BOM."</p>
                }.into_any(),
                Ok(list) if list.is_empty() => view! {
                    <p class="rams-text-sm">"No BOM items found for this product."</p>
                }.into_any(),
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|item| {
                        view! {
                            <td>{item.component_id}</td>
                            <td>{item.quantity}</td>
                            <td>{item.unit}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load BOM: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// MRP page (run for a given product).
#[component]
pub fn MrpPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let search = RwSignal::new(String::new());
    let plan = RwSignal::new(None::<std::result::Result<MrpPlanningDto, ApiError>>);
    let running = RwSignal::new(false);

    let run_planning = {
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            leptos::task::spawn_local(async move {
                let client = app_state.api_client();
                running.set(true);
                let result = run_mrp_planning(&client, &search.get_untracked()).await;
                plan.set(Some(result));
                running.set(false);
            });
        }
    };
    let on_run = RwSignal::new(Some(std::sync::Arc::new(run_planning)));

    let columns = vec![
        TableColumn {
            label: "PERIOD",
            key: "period",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "GROSS REQ.",
            key: "gross_requirement",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SCHED. RECEIPTS",
            key: "scheduled_receipts",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ON HAND",
            key: "projected_on_hand",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "NET REQ.",
            key: "net_requirement",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "PLANNED RELEASE",
            key: "planned_order_release",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="MATERIAL REQUIREMENTS PLANNING (MRP)".to_string()>
            <p class="rams-font-mono rams-text-sm rams-mb-3" style="color: var(--rams-muted);">
                "Plan by PRODUCT, not identifier — search by number or name, then act on the exceptions."
            </p>
            <div class="rams-flex rams-gap-2 rams-mb-4">
                <div class="rams-input-group">
                    <label for="mrp-product-search" class="rams-label">PRODUCT SEARCH</label>
                    <input
                        id="mrp-product-search"
                        type="text"
                        class="rams-input"
                        placeholder="Search product number or name… (e.g. PCB-100)"
                        prop:value=search
                        on:input=move |ev| search.set(event_target_value(&ev))
                        on:keydown=move |ev: web_sys::KeyboardEvent| {
                            if ev.key() == "Enter" {
                                if let Some(cb) = on_run.get_untracked() { cb() }
                            }
                        }
                    />
                </div>
                <button
                    class="rams-btn rams-btn--primary rams-btn--md"
                    on:click=move |_| { if let Some(cb) = on_run.get_untracked() { cb() } }
                    disabled=move || running.get() || search.get().trim().is_empty()
                >
                    {move || if running.get() { "RUNNING..." } else { "RUN MRP" }}
                </button>
            </div>

            {move || match plan.get() {
                Some(Ok(resp)) => {
                    let exceptions = resp.exceptions.clone();
                    let records = resp.records.clone();
                    let product_line = format!(
                        "{} · {} — demand {}",
                        resp.product_number, resp.product_name, resp.demand
                    );
                    view! {
                        <div class="rams-font-mono rams-text-sm rams-mb-3" style="color: var(--rams-muted);">
                            {product_line}
                        </div>
                        {if exceptions.is_empty() {
                            view! {
                                <div class="rams-alert rams-alert--success" role="status">
                                    "NO SHORTAGES — supply covers demand. This is a confirmed plan, not an empty run."
                                </div>
                            }.into_any()
                        } else {
                            view! {
                                <div class="module rams-mb-4">
                                    <div class="module-header"><h3 class="module-title">"SHORTAGES — NEED ACTION"</h3></div>
                                    <div class="module-content">
                                        {exceptions.iter().map(|e| {
                                            let badge = "rams-badge status-open";
                                            view! {
                                                <div class="rams-flex rams-flex--between" style="padding: var(--rams-space-3); border-bottom: 1px solid var(--rams-line);">
                                                    <div style="flex: 1;">
                                                        <div class="rams-text-sm">
                                                            {format!("{} — {}", e.product_number, e.product_name)}
                                                        </div>
                                                        <div class="rams-font-mono rams-text-2xs rams-mt-1" style="color: var(--rams-muted);">
                                                            {format!(
                                                                "Need {} · available {} · short {} · latest release {}",
                                                                e.need_qty, e.available_qty, e.short_qty, e.latest_release_date
                                                            )}
                                                        </div>
                                                        {e.supplier_risk.clone().map(|risk| view! {
                                                            <div class="rams-font-mono rams-text-2xs rams-mt-1" style="color: var(--rams-red);">
                                                                {risk}
                                                            </div>
                                                        })}
                                                    </div>
                                                    <span class=badge>{format!("SHORT {}", e.short_qty)}</span>
                                                </div>
                                            }
                                        }).collect::<Vec<_>>()}
                                    </div>
                                </div>
                            }.into_any()
                        }}
                        <div class="module">
                            <div class="module-header"><h3 class="module-title">"PLAN — FULL RECORDS"</h3></div>
                            <div class="module-content">
                                <DataTable
                                    columns=columns.clone()
                                    rows={records.into_iter().map(|r| view! {
                                        <td>{r.period}</td>
                                        <td>{r.gross_requirement}</td>
                                        <td>{r.scheduled_receipts}</td>
                                        <td>{r.projected_on_hand}</td>
                                        <td>{r.net_requirement}</td>
                                        <td>{r.planned_order_release.map(|v| v.to_string()).unwrap_or_else(|| "—".into())}</td>
                                    }).collect::<Vec<_>>()}
                                />
                            </div>
                        </div>
                    }.into_any()
                }
                Some(Err(e)) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"MRP PLAN FAILED"</strong>
                        <p class="rams-mt-2 rams-text-sm">{e.to_string()}</p>
                    </div>
                }.into_any(),
                None => view! {
                    <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                        "Search a product and run the plan."
                    </p>
                }.into_any(),
            }}
        </Module>
    }
}
