//! Universal search (item 71): type or SCAN an operational id —
//! WO-30291, SN-817723, PO-9918, Supplier ABC, Line 4 — and see the
//! relevant object with context. Exact-match ids resolve deterministically
//! before semantic retrieval (backend). Every failure renders an explicit
//! UNAVAILABLE state.

use crate::api::tps::{universal_search, SearchResponseDto};
use crate::state::AppState;
use leptos::prelude::*;

#[component]
pub fn SearchPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let query = RwSignal::new(String::new());
    let result = RwSignal::new(None::<std::result::Result<SearchResponseDto, String>>);
    let running = RwSignal::new(false);

    let run_search = {
        let app_state = app_state.clone();
        std::sync::Arc::new(move || {
            let app_state = app_state.clone();
            leptos::task::spawn_local(async move {
                let client = app_state.api_client();
                running.set(true);
                let q = query.get_untracked();
                if q.trim().is_empty() {
                    result.set(None);
                    running.set(false);
                    return;
                }
                match universal_search(&client, &q).await {
                    Ok(resp) => result.set(Some(Ok(resp))),
                    Err(e) => result.set(Some(Err(e.to_string()))),
                }
                running.set(false);
            });
        })
    };
    let on_search = RwSignal::new(Some(run_search));

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"SEARCH"</h1>
            <div class="rams-flex rams-gap-2 rams-mb-4">
                <div class="rams-input-group" style="flex: 1;">
                    <label for="search-q" class="rams-label">"TYPE OR SCAN AN OPERATIONAL ID"</label>
                    <input
                        id="search-q"
                        type="text"
                        class="rams-input"
                        placeholder="WO-30291 · SN-817723 · PO-9918 · Supplier ABC · Line 4"
                        prop:value=query
                        on:input=move |ev| query.set(event_target_value(&ev))
                        on:keydown=move |ev: web_sys::KeyboardEvent| {
                            if ev.key() == "Enter" {
                                if let Some(cb) = on_search.get_untracked() { cb() }
                            }
                        }
                    />
                </div>
                <button
                    class="rams-btn rams-btn--primary rams-btn--md"
                    on:click=move |_| { if let Some(cb) = on_search.get_untracked() { cb() } }
                    disabled=move || running.get() || query.get().trim().is_empty()
                >
                    {move || if running.get() { "SEARCHING..." } else { "SEARCH" }}
                </button>
            </div>

            {move || match result.get() {
                Some(Ok(resp)) => {
                    let results = resp.results.clone();
                    let facets = resp.facets.clone();
                    let total = resp.total;
                    view! {
                        <div class="rams-font-mono rams-text-sm rams-mb-3" style="color: var(--rams-muted);">
                            {format!("{total} RESULTS FOR \"{}\"", resp.query)}
                        </div>
                        {if !facets.is_empty() {
                            view! {
                                <div class="rams-flex rams-flex--wrap rams-gap-2 rams-mb-4">
                                    {facets.iter().map(|f| {
                                        let label = f.entity_type.clone();
                                        let count = f.count;
                                        view! { <span class="rams-badge status-ok">{format!("{} · {}", label.to_uppercase(), count)}</span> }
                                    }).collect::<Vec<_>>()}
                                </div>
                            }.into_any()
                        } else {
                            ().into_any()
                        }}
                        <div class="module">
                            <div class="module-content">
                                {if results.is_empty() {
                                    view! {
                                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                                            "NO MATCHES — this is a confirmed empty result, not a failed search."
                                        </p>
                                    }.into_any()
                                } else {
                                    view! {
                                        {results.iter().map(|r| {
                                            let rtype = r.result_type.clone();
                                            let title = r.result_title.clone();
                                            let rid = r.result_id.clone();
                                            let is_exact = r.relevance > 1.0;
                                            let badge = if is_exact { "rams-badge status-open" } else { "rams-badge status-ok" };
                                            // Item 81: every result is a REAL navigable object —
                                            // the exact-match resolves deterministically and the
                                            // link goes to the object's operational page, not a
                                            // raw UUID fragment.
                                            let target = result_target(&rtype, &rid);
                                            view! {
                                                <a
                                                    href=target
                                                    class="rams-flex rams-flex--between"
                                                    style="padding: var(--rams-space-3); border-bottom: 1px solid var(--rams-line); text-decoration: none; color: inherit; display: flex;"
                                                >
                                                    <div>
                                                        <div class="rams-text-sm">{title}</div>
                                                        <div class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">
                                                            {business_identifier(&rtype, &rid)}
                                                        </div>
                                                    </div>
                                                    <span class=badge>
                                                        {if is_exact { "EXACT MATCH".to_string() } else { format!("{:.0}%", r.relevance * 100.0) }}
                                                    </span>
                                                </a>
                                            }
                                        }).collect::<Vec<_>>()}
                                    }.into_any()
                                }}
                            </div>
                        </div>
                    }.into_any()
                }
                Some(Err(e)) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"STATUS UNKNOWN — SEARCH UNAVAILABLE"</strong>
                        <p class="rams-mt-2 rams-text-sm">{e}</p>
                    </div>
                }.into_any(),
                None => view! {
                    <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">
                        "Search an operational id or name — exact matches resolve first."
                    </p>
                }.into_any(),
            }}
        </div>
    }
}

/// Item 81: map a result type to its operational page. Exact identifiers
/// (work orders, NCrs, andons, products) resolve deterministically; a
/// result is a navigable object, never a UUID fragment.
fn result_target(result_type: &str, id: &str) -> String {
    match result_type {
        "work_order" => format!("/work/{}", id),
        "product" => format!("/production/products/{}", id),
        "ncr" => format!("/quality/ncrs/{}", id),
        "andon" => format!("/abnormalities/{}", id),
        "a3" => format!("/tps/a3/{}", id),
        "sales_order" => format!("/sales/orders/{}", id),
        "supplier" => format!("/supply-chain/suppliers/{}", id),
        "standard_work" | "standard-work" => format!("/tps/standards/{}", id),
        "account" | "customer" => format!("/sales/accounts/{}", id),
        "contact" => format!("/sales/contacts/{}", id),
        "employee" => format!("/hr/employees/{}", id),
        "knowledge_pack" => format!("/knowledge/{}", id),
        _ => format!("/search?q={}", id),
    }
}

/// Item 81: emphasize BUSINESS identifiers — work-order numbers, SKUs —
/// instead of UUID fragments where the search index carries them.
fn business_identifier(result_type: &str, id: &str) -> String {
    match result_type {
        "work_order" | "product" | "sales_order" | "ncr" | "andon" | "a3" => {
            format!("{} · {}", result_type.to_uppercase(), id)
        }
        _ => {
            let short = if id.len() > 8 { &id[..8] } else { id };
            format!("{} · {}", result_type.to_uppercase(), short)
        }
    }
}
