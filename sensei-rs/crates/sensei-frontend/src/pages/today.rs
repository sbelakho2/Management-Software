//! Today page — the primary home screen (item 30/67).
//!
//! Not a "dashboard" of departmental counts: it renders the SERVER-side
//! Today snapshot (site-local date, caller scope, work-order/quality/
//! operations condition). Any fetch failure renders an explicit
//! UNAVAILABLE state — a failed request must never look like a healthy
//! zero (item 4).

use crate::api::today::{get_today_snapshot, TodaySnapshot};
use crate::state::AppState;
use leptos::prelude::*;

#[component]
pub fn TodayPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_data = app_state.clone();
    let snapshot = ArcLocalResource::new(move || {
        let state = app_state_for_data.clone();
        async move {
            let client = state.api_client();
            get_today_snapshot(&client).await
        }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"TODAY"</h1>
            {move || snapshot.map(|result| {
                match result.as_ref() {
                    Ok(s) => render_snapshot(s).into_any(),
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">
                                {format!("Could not obtain the Today snapshot: {e}. \
                                          Zero is a business fact — 'could not obtain the fact' \
                                          is a different state.")}
                            </p>
                        </div>
                    }.into_any(),
                }
            }).unwrap_or_else(|| view! {
                <div class="module rams-mb-4">
                    <div class="module-content">
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted)">
                            "LOADING TODAY..."
                        </p>
                    </div>
                </div>
            }.into_any())}
        </div>
    }
}

fn render_snapshot(s: &TodaySnapshot) -> impl IntoView {
    let overdue_danger = s.work_orders.overdue > 0;
    let andon_danger = s.quality.active_andons > 0;
    let scope_line = format!(
        "SITE-LOCAL TODAY: {}  ·  TZ {}  ·  Site {}  ·  Shift {}",
        s.date,
        s.timezone,
        s.scope.site_id.as_deref().unwrap_or("—"),
        s.scope.shift_id.as_deref().unwrap_or("—"),
    );
    view! {
        <>
            <div class="rams-font-mono rams-text-sm rams-mb-4" style="color: var(--rams-muted)">
                {scope_line}
            </div>

            <div class="module rams-mb-4">
                <div class="module-header">
                    <h3 class="module-title">"PRODUCTION CONDITION"</h3>
                </div>
                <div class="module-content">
                    <div class="rams-grid rams-grid--cols-4 rams-gap-4">
                        <MetricTile
                            label="ACTIVE WORK ORDERS".to_string()
                            value=s.work_orders.total_active.to_string()
                        ></MetricTile>
                        <MetricTile
                            label="IN PROGRESS".to_string()
                            value=s.work_orders.in_progress.to_string()
                        ></MetricTile>
                        <MetricTile
                            label="COMPLETED TODAY".to_string()
                            value=s.work_orders.completed_today.to_string()
                        ></MetricTile>
                        <MetricTile
                            label="OVERDUE".to_string()
                            value=s.work_orders.overdue.to_string()
                            danger=overdue_danger
                        ></MetricTile>
                    </div>
                </div>
            </div>

            <div class="module rams-mb-4">
                <div class="module-header">
                    <h3 class="module-title">"QUALITY & OPERATIONS"</h3>
                </div>
                <div class="module-content">
                    <div class="rams-grid rams-grid--cols-4 rams-gap-4">
                        <MetricTile
                            label="ACTIVE ANDONS".to_string()
                            value=s.quality.active_andons.to_string()
                            danger=andon_danger
                        ></MetricTile>
                        <MetricTile
                            label="OPEN NCRs".to_string()
                            value=s.quality.open_ncrs.to_string()
                        ></MetricTile>
                        <MetricTile
                            label="OPEN CAPAs".to_string()
                            value=s.quality.open_capas.to_string()
                        ></MetricTile>
                        <MetricTile
                            label="OPEN A3s".to_string()
                            value=s.operations.open_a3s.to_string()
                        ></MetricTile>
                    </div>
                </div>
            </div>
        </>
    }
}

#[component]
fn MetricTile(label: String, value: String, #[prop(optional)] danger: bool) -> impl IntoView {
    let class = if danger {
        "metric-display metric-display--danger"
    } else {
        "metric-display"
    };
    let aria = format!("{label}: {value}");
    let value_display = value.clone();
    view! {
        <div class=class aria-label=aria>
            <div class="metric-display-value">{value_display}</div>
            <div class="metric-display-label">{label}</div>
        </div>
    }
}
