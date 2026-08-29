//! Document ingestion (item 72): scanned shop documents (standards,
//! customer requirements, work instructions) pass through a HUMAN
//! APPROVAL GATE before they can influence knowledge — OCR output is
//! never automatically authoritative. The page shows the pipeline queue
//! and the approve/reject actions with the extractor's candidate
//! authority for the person to confirm.

use crate::api::tps::{ingest_document, list_ingestions, review_document, IngestedDocumentDto};
use crate::components::data_table::{DataTableData, TableColumn, TableState};
use crate::components::modal::Modal;
use crate::state::AppState;
use leptos::prelude::*;
use std::sync::Arc;

#[component]
pub fn DocumentIngestionPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_ingest = app_state.clone();
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { list_ingestions(&client).await }
    });
    let refresh = RwSignal::new(0u32);
    let app_state_for_actions = app_state_for_ingest.clone();

    let ingest_open = modal_open(false);
    let title = RwSignal::new(String::new());
    let source = RwSignal::new(String::new());
    let raw_text = RwSignal::new(String::new());
    let ingest_error = RwSignal::new(None::<String>);

    let do_ingest = {
        std::sync::Arc::new(move || {
            let app_state = app_state_for_ingest.clone();
            let refresh = refresh;
            leptos::task::spawn_local(async move {
                let client = app_state.api_client();
                let req = serde_json::json!({
                    "title": title.get_untracked(),
                    "source_path": source.get_untracked(),
                    "raw_text": raw_text.get_untracked(),
                    "structured": [],
                });
                match ingest_document(&client, req).await {
                    Ok(_) => {
                        ingest_open.set(false);
                        title.set(String::new());
                        source.set(String::new());
                        raw_text.set(String::new());
                        refresh.update(|v| *v += 1);
                    }
                    Err(e) => ingest_error.set(Some(e.to_string())),
                }
            });
        })
    };
    let on_ingest = RwSignal::new(Some(do_ingest));

    let approve_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |dto: IngestedDocumentDto| {
            let client = app_state.api_client();
            let id = dto.id.clone();
            let refresh = refresh;
            leptos::task::spawn_local(async move {
                let _ = review_document(&client, &id, true, None).await;
                refresh.update(|v| *v += 1);
            });
        })
    };
    let reject_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |dto: IngestedDocumentDto| {
            let client = app_state.api_client();
            let id = dto.id.clone();
            let refresh = refresh;
            leptos::task::spawn_local(async move {
                let _ = review_document(&client, &id, false, None).await;
                refresh.update(|v| *v += 1);
            });
        })
    };

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"DOCUMENT INGESTION"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| ingest_open.set(true)>
                    "INGEST DOCUMENT"
                </button>
            </div>
            <crate::components::inline_coach::InlineCoach
                step="HUMAN APPROVAL REQUIRED".to_string()
                question="OCR output is never automatically authoritative — approve only what a person can confirm against the actual condition.".to_string()
            />
            {move || {
                let _ = refresh.get();
                data.map(|w| match &**w {
                    Ok(list) => {
                        let rows: Vec<IngestedDocumentDto> = list.clone();
                        let actions = vec![
                            crate::components::data_table::RowAction {
                                label: "APPROVE".to_string(),
                                kind: crate::components::data_table::ActionKind::Primary,
                                on_click: approve_action.clone(),
                            },
                            crate::components::data_table::RowAction {
                                label: "REJECT".to_string(),
                                kind: crate::components::data_table::ActionKind::Danger,
                                on_click: reject_action.clone(),
                            },
                        ];
                        view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "TITLE", key: "title", sortable: true, width: None },
                                    TableColumn { label: "STATUS", key: "status", sortable: true, width: None },
                                    TableColumn { label: "CANDIDATE AUTHORITY", key: "authority", sortable: true, width: None },
                                    TableColumn { label: "CREATED", key: "created_at", sortable: true, width: None },
                                ]
                                rows=rows
                                render_row=Arc::new(|d: IngestedDocumentDto| {
                                    let badge = format!("rams-badge status-{}", d.status.to_lowercase());
                                    vec![
                                        d.title.clone().into_any(),
                                        view! { <span class=badge>{d.status.to_uppercase()}</span> }.into_any(),
                                        d.candidate.map(|c| c.authority.replace('_', " ").to_uppercase()).unwrap_or_else(|| "—".to_string()).into_any(),
                                        d.created_at[..10].to_string().into_any(),
                                    ]
                                })
                                sort_by=Arc::new(|d: &IngestedDocumentDto, key: &str| -> String {
                                    match key {
                                        "title" => d.title.clone(),
                                        "status" => d.status.clone(),
                                        "authority" => d.candidate.clone().map(|c| c.authority).unwrap_or_default(),
                                        "created_at" => d.created_at.clone(),
                                        _ => String::new(),
                                    }
                                })
                                state=TableState::Normal
                                caption=Some("Document ingestion queue".to_string())
                                row_actions=actions
                            />
                        }.into_any()
                    }
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — INGESTION UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                        </div>
                    }.into_any(),
                }).unwrap_or_else(|| view! {
                    <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING INGESTIONS…"</p>
                }.into_any())
            }}
            <Show when=move || ingest_open.get()>
                <Modal title="Ingest Document".to_string() open=ingest_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="ing-title">"TITLE"</label>
                        <input id="ing-title" class="rams-input" prop:value=title placeholder="Cell 4 work instruction" />
                        <label class="rams-text-sm" for="ing-source">"SOURCE"</label>
                        <input id="ing-source" class="rams-input" prop:value=source placeholder="scan/wi-4.pdf" />
                        <label class="rams-text-sm" for="ing-text">"PERCEIVED TEXT (OCR output)"</label>
                        <textarea id="ing-text" class="rams-input" rows="6" prop:value=raw_text placeholder="The perceived text of the scanned document…"></textarea>
                        {move || ingest_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = on_ingest.get_untracked() { cb() } }>
                            "INGEST AS CANDIDATE"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

fn modal_open(open: bool) -> leptos::prelude::RwSignal<bool> {
    leptos::prelude::RwSignal::new(open)
}
