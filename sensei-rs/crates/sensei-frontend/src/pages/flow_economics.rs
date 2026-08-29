//! Flow economics (items 36/38): purchasing sees the TOTAL flow impact of
//! a sourcing option (trapped cash, inventory days, variability risk) —
//! the "cheapest" part is not the cheapest; finance sees the waste
//! snapshot (WIP cash, aging stock, scrap, rework). No lectures about
//! waste — the numbers make the flow condition visible.

use crate::api::tps::{get_finance_waste, sourcing_flow_cost, SourcingFlowCostDto};
use crate::state::AppState;
use leptos::prelude::*;

#[component]
pub fn FlowEconomicsPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");

    // ── Sourcing comparison (item 36) ──
    let option_a_label = RwSignal::new("Supplier A".to_string());
    let a_price = RwSignal::new("1.92".to_string());
    let a_moq = RwSignal::new("10000".to_string());
    let a_lead = RwSignal::new("63".to_string());
    let a_otd = RwSignal::new("0.84".to_string());
    let a_var = RwSignal::new("0.4".to_string());

    let option_b_label = RwSignal::new("Supplier B".to_string());
    let b_price = RwSignal::new("2.03".to_string());
    let b_moq = RwSignal::new("2000".to_string());
    let b_lead = RwSignal::new("21".to_string());
    let b_otd = RwSignal::new("0.98".to_string());
    let b_var = RwSignal::new("0.1".to_string());

    let demand_per_day = RwSignal::new("160".to_string());
    let sourcing_result_a = RwSignal::new(None::<SourcingFlowCostDto>);
    let sourcing_result_b = RwSignal::new(None::<SourcingFlowCostDto>);
    let sourcing_error = RwSignal::new(None::<String>);

    let compare = {
        let app_state = app_state.clone();
        move || {
            leptos::task::spawn_local({
                let app_state = app_state.clone();
                async move {
                    let client = app_state.api_client();
                    sourcing_error.set(None);
                    let req_a = serde_json::json!({
                        "label": option_a_label.get_untracked(),
                        "unit_price": a_price.get_untracked(),
                        "moq": a_moq.get_untracked(),
                        "lead_time_days": a_lead.get_untracked().parse::<i64>().unwrap_or(0),
                        "otd": a_otd.get_untracked(),
                        "demand_per_day": demand_per_day.get_untracked(),
                        "otd_variability": a_var.get_untracked(),
                    });
                    let req_b = serde_json::json!({
                        "label": option_b_label.get_untracked(),
                        "unit_price": b_price.get_untracked(),
                        "moq": b_moq.get_untracked(),
                        "lead_time_days": b_lead.get_untracked().parse::<i64>().unwrap_or(0),
                        "otd": b_otd.get_untracked(),
                        "demand_per_day": demand_per_day.get_untracked(),
                        "otd_variability": b_var.get_untracked(),
                    });
                    match (
                        sourcing_flow_cost(&client, req_a).await,
                        sourcing_flow_cost(&client, req_b).await,
                    ) {
                        (Ok(a), Ok(b)) => {
                            sourcing_result_a.set(Some(a));
                            sourcing_result_b.set(Some(b));
                        }
                        (Err(e), _) | (_, Err(e)) => sourcing_error.set(Some(e.to_string())),
                    }
                }
            });
        }
    };
    let on_compare = RwSignal::new(Some(std::sync::Arc::new(compare)));

    // ── Finance waste (item 38) ──
    let waste = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { get_finance_waste(&client).await }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"FLOW ECONOMICS"</h1>

            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"SOURCING — TOTAL FLOW IMPACT"</h3></div>
                <div class="module-content">
                    <p class="rams-font-mono rams-text-sm rams-mb-3" style="color: var(--rams-muted);">
                        "Unit price is not the cost. Compare two options and see the cash, stock and \
                         variability each one commits."
                    </p>
                    <div class="rams-grid rams-grid--cols-3 rams-gap-3">
                        <div class="rams-flex rams-flex--col rams-gap-1">
                            <label class="rams-text-sm" for="a-label">"OPTION A NAME"</label>
                            <input id="a-label" class="rams-input" prop:value=option_a_label />
                            <label class="rams-text-sm" for="a-price">"UNIT PRICE"</label>
                            <input id="a-price" class="rams-input" prop:value=a_price />
                            <label class="rams-text-sm" for="a-moq">"MOQ"</label>
                            <input id="a-moq" class="rams-input" prop:value=a_moq />
                            <label class="rams-text-sm" for="a-lead">"LEAD TIME (days)"</label>
                            <input id="a-lead" class="rams-input" prop:value=a_lead />
                            <label class="rams-text-sm" for="a-otd">"OTD (0..1)"</label>
                            <input id="a-otd" class="rams-input" prop:value=a_otd />
                            <label class="rams-text-sm" for="a-var">"DELIVERY VARIABILITY (0..1)"</label>
                            <input id="a-var" class="rams-input" prop:value=a_var />
                        </div>
                        <div class="rams-flex rams-flex--col rams-gap-1">
                            <label class="rams-text-sm" for="b-label">"OPTION B NAME"</label>
                            <input id="b-label" class="rams-input" prop:value=option_b_label />
                            <label class="rams-text-sm" for="b-price">"UNIT PRICE"</label>
                            <input id="b-price" class="rams-input" prop:value=b_price />
                            <label class="rams-text-sm" for="b-moq">"MOQ"</label>
                            <input id="b-moq" class="rams-input" prop:value=b_moq />
                            <label class="rams-text-sm" for="b-lead">"LEAD TIME (days)"</label>
                            <input id="b-lead" class="rams-input" prop:value=b_lead />
                            <label class="rams-text-sm" for="b-otd">"OTD (0..1)"</label>
                            <input id="b-otd" class="rams-input" prop:value=b_otd />
                            <label class="rams-text-sm" for="b-var">"DELIVERY VARIABILITY (0..1)"</label>
                            <input id="b-var" class="rams-input" prop:value=b_var />
                        </div>
                        <div class="rams-flex rams-flex--col rams-gap-1">
                            <label class="rams-text-sm" for="demand">"DEMAND PER DAY"</label>
                            <input id="demand" class="rams-input" prop:value=demand_per_day />
                            <button
                                type="button"
                                class="rams-btn rams-btn--md rams-mt-3"
                                on:click=move |_| { if let Some(cb) = on_compare.get_untracked() { cb() } }
                            >
                                "COMPARE"
                            </button>
                            {move || sourcing_error.get().map(|e| view! {
                                <div class="rams-alert rams-alert--danger rams-mt-2" role="alert">{e}</div>
                            })}
                        </div>
                    </div>

                    {move || {
                        let a = sourcing_result_a.get();
                        let b = sourcing_result_b.get();
                        match (a, b) {
                            (Some(a), Some(b)) => view! {
                                <div class="rams-grid rams-grid--cols-2 rams-gap-3 rams-mt-4">
                                    <SourcingCard dto=a />
                                    <SourcingCard dto=b />
                                </div>
                            }.into_any(),
                            _ => ().into_any(),
                        }
                    }}
                </div>
            </div>

            <div class="module">
                <div class="module-header"><h3 class="module-title">"WASTE SNAPSHOT"</h3></div>
                <div class="module-content">
                    {move || waste.map(|w| match &**w {
                        Ok(s) => view! {
                            <div>
                                <div class="rams-flex rams-flex--between rams-mb-3">
                                    <span class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                                        "ANNUAL WASTE EXPOSURE"
                                    </span>
                                    <span class="rams-text-sm">{s.total_waste_annual.clone()}</span>
                                </div>
                                {s.lines.iter().map(|l| {
                                    let label = l.label.clone();
                                    let value = l.value.clone();
                                    let guidance = l.guidance.clone();
                                    view! {
                                        <div class="rams-flex rams-flex--between" style="padding: var(--rams-space-2); border-bottom: 1px solid var(--rams-line);">
                                            <div>
                                                <div class="rams-text-sm">{label}</div>
                                                <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">{guidance}</div>
                                            </div>
                                            <span class="rams-text-sm">{value}</span>
                                        </div>
                                    }
                                }).collect::<Vec<_>>()}
                            </div>
                        }.into_any(),
                        Err(e) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert">
                                <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                                <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                            </div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! {
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING WASTE…"</p>
                    }.into_any())}
                </div>
            </div>
        </div>
    }
}

#[component]
fn SourcingCard(dto: SourcingFlowCostDto) -> impl IntoView {
    let label = dto.option_label.clone();
    let unit_price = dto.unit_price.clone();
    let moq = dto.moq.clone();
    let lead = dto.lead_time_days.to_string();
    let otd = dto.on_time_delivery.clone();
    let inv_days = dto.inventory_days.clone();
    let trapped = dto.trapped_cash.clone();
    let risk = dto.shortage_risk.clone();
    let guidance = dto.guidance.clone();
    view! {
        <div class="module">
            <div class="module-header"><h3 class="module-title">{label}</h3></div>
            <div class="module-content">
                <div class="rams-grid rams-grid--cols-2 rams-gap-2">
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"UNIT PRICE"</div>
                        <div class="rams-text-sm">{unit_price}</div>
                    </div>
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"MOQ"</div>
                        <div class="rams-text-sm">{moq}</div>
                    </div>
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"LEAD"</div>
                        <div class="rams-text-sm">{format!("{lead}d")}</div>
                    </div>
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"OTD"</div>
                        <div class="rams-text-sm">{otd}</div>
                    </div>
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"INVENTORY EFFECT"</div>
                        <div class="rams-text-sm">{format!("{inv_days}d of demand")}</div>
                    </div>
                    <div>
                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"CASH COMMITTED"</div>
                        <div class="rams-text-sm">{trapped}</div>
                    </div>
                </div>
                <div class="rams-mt-2">
                    <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"SHORTAGE RISK"</div>
                    <div class="rams-progress" role="progressbar" aria-valuenow=(risk.parse::<f64>().unwrap_or(0.0) * 100.0) as i64 aria-valuemin="0" aria-valuemax="100">
                        <div class="rams-progress-fill" style=format!("width: {}%;", (risk.parse::<f64>().unwrap_or(0.0) * 100.0) as i64)></div>
                    </div>
                </div>
                <p class="rams-font-mono rams-text-2xs rams-mt-2" style="color: var(--rams-muted);">{guidance}</p>
            </div>
        </div>
    }
}
