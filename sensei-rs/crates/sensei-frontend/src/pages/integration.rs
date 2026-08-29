//! Legacy-system integration page (interoperability): shows the starzERP
//! and CRM-v2 sync state — the legacy systems KEEP RUNNING and feed Sensei
//! through the versioned import API. Every import is idempotent via the
//! entity map: re-importing the same legacy id updates, never duplicates.

use crate::api::tps::get_integration_status;
use crate::state::AppState;
use leptos::prelude::*;

#[component]
pub fn IntegrationPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { get_integration_status(&client).await }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-2">"LEGACY SYSTEM INTEGRATION"</h1>
            <p class="rams-font-mono rams-text-sm rams-mb-4" style="color: var(--rams-muted);">
                "starzERP and CRM-v2 keep running and feed Sensei through the versioned import \
                 API — every record maps idempotently (same legacy id = same Sensei entity)."
            </p>
            {move || data.map(|w| match &**w {
                Ok(s) => {
                    let systems = s.legacy_systems.clone();
                    let entities = s.supported_entities.clone();
                    let count = s.entity_map_count;
                    view! {
                        <div class="module rams-mb-4">
                            <div class="module-header"><h3 class="module-title">"SYNC STATE"</h3></div>
                            <div class="module-content">
                                <div class="rams-flex rams-flex--between">
                                    <span class="rams-text-sm">"MAPPED LEGACY RECORDS"</span>
                                    <span class="rams-font-mono rams-text-sm">{count.to_string()}</span>
                                </div>
                            </div>
                        </div>
                        <div class="module rams-mb-4">
                            <div class="module-header"><h3 class="module-title">"LEGACY SYSTEMS"</h3></div>
                            <div class="module-content">
                                {systems.iter().map(|sys| {
                                    let sys = sys.clone();
                                    let name = match sys.as_str() {
                                        "starzerp" => "starzERP — Symfony ERP (articles, customers, sales orders, stock, suppliers)".to_string(),
                                        "crm_v2" => "CRM-v2 — Symfony CRM (leads, companies, contacts, quotes, RFQs)".to_string(),
                                        other => other.to_string(),
                                    };
                                    view! {
                                        <div class="rams-flex rams-flex--between" style="padding: var(--rams-space-2); border-bottom: 1px solid var(--rams-line);">
                                            <span class="rams-font-mono rams-text-sm">{sys.to_uppercase()}</span>
                                            <span class="rams-text-sm">{name}</span>
                                        </div>
                                    }
                                }).collect::<Vec<_>>()}
                            </div>
                        </div>
                        <div class="module">
                            <div class="module-header"><h3 class="module-title">"IMPORTABLE ENTITIES"</h3></div>
                            <div class="module-content">
                                <div class="rams-flex rams-flex--wrap rams-gap-2">
                                    {entities.iter().map(|e| {
                                        let e = e.clone();
                                        view! { <span class="rams-badge status-ok">{e.to_uppercase()}</span> }
                                    }).collect::<Vec<_>>()}
                                </div>
                                <p class="rams-font-mono rams-text-2xs rams-mt-3" style="color: var(--rams-muted);">
                                    "Run `sensei-bridge --all` with STARZERP_DATABASE_URL and CRM_V2_DATABASE_URL set to sync."
                                </p>
                            </div>
                        </div>
                    }.into_any()
                }
                Err(e) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"STATUS UNKNOWN — INTEGRATION UNAVAILABLE"</strong>
                        <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                    </div>
                }.into_any(),
            }).unwrap_or_else(|| view! {
                <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING INTEGRATION…"</p>
            }.into_any())}
        </div>
    }
}
