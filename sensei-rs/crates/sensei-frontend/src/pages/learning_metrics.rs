//! System learning metrics (item 43): whether the SYSTEM learns — never a
//! person ranking. Every metric carries target/gap/guidance, and the page
//! is explicit that MORE Andons can mean MORE health.

use crate::api::tps::get_learning_metrics;
use crate::state::AppState;
use leptos::prelude::*;

#[component]
pub fn LearningMetricsPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { get_learning_metrics(&client).await }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-2">"SYSTEM LEARNING"</h1>
            <p class="rams-font-mono rams-text-sm rams-mb-4" style="color: var(--rams-muted);">
                "These metrics measure whether the SYSTEM learns — never rank people by fewest \
                 Andons or NCRs. More reported abnormalities can be a sign of health."
            </p>
            {move || data.map(|w| match &**w {
                Ok(s) => {
                    let index = s.learning_index;
                    let index_pct = (index * 100.0) as i64;
                    let metrics = s.metrics.clone();
                    view! {
                        <div class="module rams-mb-4">
                            <div class="module-header">
                                <h3 class="module-title">"LEARNING INDEX"</h3>
                                <span class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                                    {format!("{index_pct}%")}
                                </span>
                            </div>
                            <div class="module-content">
                                <div class="rams-progress" role="progressbar" aria-valuenow=index_pct aria-valuemin="0" aria-valuemax="100">
                                    <div class="rams-progress-fill" style=format!("width: {index_pct}%;")></div>
                                </div>
                            </div>
                        </div>
                        <div class="module">
                            <div class="module-header"><h3 class="module-title">"METRICS"</h3></div>
                            <div class="module-content">
                                {metrics.iter().map(|m| {
                                    let value = match m.unit.as_str() {
                                        "%" => format!("{:.0}%", m.value * 100.0),
                                        _ => format!("{:.0} {}", m.value, m.unit),
                                    };
                                    let gap_line = m.gap.map(|g| {
                                        match m.unit.as_str() {
                                            "%" => format!("gap to target: {:.0}%", g * 100.0),
                                            _ => format!("gap to target: {:.0} {}", g, m.unit),
                                        }
                                    }).unwrap_or_default();
                                    let better_label = if m.better == "lower" { "lower is better" } else { "higher is better" };
                                    view! {
                                        <div class="rams-flex rams-flex--between" style="padding: var(--rams-space-3); border-bottom: 1px solid var(--rams-line);">
                                            <div style="flex: 1;">
                                                <div class="rams-text-sm">{m.label.clone()}</div>
                                                <div class="rams-font-mono rams-text-2xs rams-mt-1" style="color: var(--rams-muted);">
                                                    {m.guidance.clone()}
                                                </div>
                                            </div>
                                            <div class="rams-flex rams-flex--col" style="align-items: flex-end; min-width: 140px;">
                                                <span class="rams-text-sm">{value}</span>
                                                <span class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">{better_label}</span>
                                                {if !gap_line.is_empty() {
                                                    view! { <span class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">{gap_line}</span> }.into_any()
                                                } else {
                                                    ().into_any()
                                                }}
                                            </div>
                                        </div>
                                    }
                                }).collect::<Vec<_>>()}
                            </div>
                        </div>
                    }.into_any()
                }
                Err(e) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                        <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                    </div>
                }.into_any(),
            }).unwrap_or_else(|| view! {
                <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING METRICS…"</p>
            }.into_any())}
        </div>
    }
}
