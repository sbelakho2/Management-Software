//! Supply Chain page — RFQs, Quotes, Sales Orders, POs, Inventory, Stock Moves.
//!
//! Rams design system — parent page uses Module, child list pages use
//! Module + DataTable components.

use crate::api::supply_chain::SupplyChainApi;
use crate::components::data_table::{DataTable, TableColumn};
use crate::components::module::Module;
use crate::state::AppState;
use leptos::prelude::*;
use leptos_router::components::Outlet;

/// Supply chain parent page.
#[component]
pub fn SupplyChainPage() -> impl IntoView {
    view! {
        <Module title="SUPPLY CHAIN".to_string()>
            <Outlet />
        </Module>
    }
}

/// List all RFQs.
#[component]
pub fn RfqListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_rfqs(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "RFQ #",
            key: "rfq_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SUPPLIER",
            key: "supplier_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ITEMS",
            key: "items",
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
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="RFQS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|rfq| {
                        view! {
                            <td>{rfq.rfq_number}</td>
                            <td>{rfq.supplier_id}</td>
                            <td>{rfq.items.len()}</td>
                            <td><span class=format!("rams-badge status-{}", rfq.status.to_lowercase())>{rfq.status.clone()}</span></td>
                            <td>{rfq.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load RFQs: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all quotes.
#[component]
pub fn QuoteListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_quotes(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "QUOTE #",
            key: "quote_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SUPPLIER",
            key: "supplier_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TOTAL",
            key: "total",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CURRENCY",
            key: "currency",
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
            label: "VALID UNTIL",
            key: "valid_until",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="QUOTES".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|q| {
                        view! {
                            <td>{q.quote_number}</td>
                            <td>{q.supplier_id}</td>
                            <td>{format!("{:.2}", q.total)}</td>
                            <td>{q.currency}</td>
                            <td><span class=format!("rams-badge status-{}", q.status.to_lowercase())>{q.status.clone()}</span></td>
                            <td>{q.valid_until.as_ref().map(|d| d[..10].to_string()).unwrap_or_else(|| "—".into())}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load quotes: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all sales orders.
#[component]
pub fn SalesOrderListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_sales_orders(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "SO #",
            key: "sales_order_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CUSTOMER",
            key: "customer_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ITEMS",
            key: "items",
            sortable: true,
            width: Some("60px"),
        },
        TableColumn {
            label: "TOTAL",
            key: "total",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CURRENCY",
            key: "currency",
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
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="SALES ORDERS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|so| {
                        view! {
                            <td>{so.sales_order_number}</td>
                            <td>{so.customer_id}</td>
                            <td>{so.items.len()}</td>
                            <td>{format!("{:.2}", so.total)}</td>
                            <td>{so.currency}</td>
                            <td><span class=format!("rams-badge status-{}", so.status.to_lowercase())>{so.status.clone()}</span></td>
                            <td>{so.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load sales orders: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List all purchase orders.
#[component]
pub fn PurchaseOrderListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_purchase_orders(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "PO #",
            key: "po_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "SUPPLIER",
            key: "supplier_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ITEMS",
            key: "items",
            sortable: true,
            width: Some("60px"),
        },
        TableColumn {
            label: "TOTAL",
            key: "total",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "CURRENCY",
            key: "currency",
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
            label: "CREATED",
            key: "created_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="PURCHASE ORDERS".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|po| {
                        view! {
                            <td>{po.po_number}</td>
                            <td>{po.supplier_id}</td>
                            <td>{po.items.len()}</td>
                            <td>{format!("{:.2}", po.total)}</td>
                            <td>{po.currency}</td>
                            <td><span class=format!("rams-badge status-{}", po.status.to_lowercase())>{po.status.clone()}</span></td>
                            <td>{po.created_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load purchase orders: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List inventory items.
#[component]
pub fn InventoryListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_inventory(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "PRODUCT",
            key: "product_name",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "ON HAND",
            key: "quantity_on_hand",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "RESERVED",
            key: "quantity_reserved",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "AVAILABLE",
            key: "quantity_available",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "LOCATION",
            key: "location",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "UNIT",
            key: "unit",
            sortable: true,
            width: Some("60px"),
        },
    ];

    view! {
        <Module title="INVENTORY".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|item| {
                        view! {
                            <td>{item.product_name}</td>
                            <td>{item.quantity_on_hand}</td>
                            <td>{item.quantity_reserved}</td>
                            <td><strong>{item.quantity_available}</strong></td>
                            <td>{item.location.unwrap_or_else(|| "—".into())}</td>
                            <td>{item.unit}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load inventory: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}

/// List stock moves.
#[component]
pub fn StockMoveListPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { SupplyChainApi::list_stock_moves(&client).await }
    });

    let columns = vec![
        TableColumn {
            label: "PRODUCT",
            key: "product_id",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "QUANTITY",
            key: "quantity",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TYPE",
            key: "move_type",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "FROM",
            key: "from_location",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TO",
            key: "to_location",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "REFERENCE",
            key: "reference",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "MOVED AT",
            key: "moved_at",
            sortable: true,
            width: None,
        },
    ];

    view! {
        <Module title="STOCK MOVES".to_string()>
            {move || data.map(|w| match &**w {
                Ok(list) => {
                    let rows: Vec<_> = list.clone().into_iter().map(|sm| {
                        view! {
                            <td>{sm.product_id}</td>
                            <td>{sm.quantity}</td>
                            <td><span class=format!("rams-badge move-type-{}", sm.move_type.to_lowercase())>{sm.move_type.clone()}</span></td>
                            <td>{sm.from_location.unwrap_or_else(|| "—".into())}</td>
                            <td>{sm.to_location.unwrap_or_else(|| "—".into())}</td>
                            <td>{sm.reference.unwrap_or_else(|| "—".into())}</td>
                            <td>{sm.moved_at[..10].to_string()}</td>
                        }
                    }).collect();
                    view! { <DataTable columns=columns.clone() rows=rows /> }.into_any()
                },
                Err(e) => view! { <p class="rams-text-sm">"Failed to load stock moves: " {e.to_string()}</p> }.into_any(),
            }).unwrap_or_else(|| view! { <p class="rams-text-sm">"Loading..."</p> }.into_any())}
        </Module>
    }
}
