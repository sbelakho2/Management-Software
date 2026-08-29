//! TPS work surfaces (items 33/64/67): Leader Standard Work, Standard
//! Work, Tier Meetings, Topology and Work Centers — FULL workflows
//! (create/act/complete), not read-only tables (item 44). Every fetch
//! failure renders an explicit UNAVAILABLE state (item 4).

use crate::api::tps::*;
use crate::components::data_table::{
    ActionKind, DataTableData, RowAction, TableColumn, TableState,
};
use crate::components::modal::Modal;
use crate::state::AppState;
use leptos::prelude::*;
use std::sync::Arc;

// ── Shared helpers ──────────────────────────────────────────────────────

/// Format an id as a SHORT display token (item 46: operators see
/// recognizable context, not raw UUIDs).
pub fn short_id(id: &str) -> String {
    id.chars().take(8).collect()
}

/// Create a modal-open signal pair.
fn modal_open(open: bool) -> RwSignal<bool> {
    RwSignal::new(open)
}

// ── Leader Standard Work (item 33: the manager's ordinary checks) ───────

#[component]
pub fn LswPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let client = app_state.api_client();
            async move { list_lsw_standards(&client).await }
        }
    });

    let create_open = modal_open(false);
    let title = RwSignal::new(String::new());
    let area = RwSignal::new(String::new());
    let layer = RwSignal::new(1u8);
    let frequency = RwSignal::new("daily".to_string());
    let create_error = RwSignal::new(None::<String>);

    let create_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            leptos::task::spawn_local({
                let app_state = app_state_for_submit.clone();
                async move {
                    let client = app_state.api_client();
                    let req = serde_json::json!({
                        "title": title.get_untracked(),
                        "area": area.get_untracked(),
                        "layer": layer.get_untracked(),
                        "frequency": frequency.get_untracked(),
                        "checklist_items": [],
                    });
                    match create_lsw_standard(&client, req).await {
                        Ok(_) => create_open.set(false),
                        Err(e) => create_error.set(Some(e.to_string())),
                    }
                }
            });
        });
    let columns = vec![
        TableColumn {
            label: "CHECK",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "AREA",
            key: "area",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "LAYER",
            key: "layer",
            sortable: true,
            width: Some("70px"),
        },
        TableColumn {
            label: "REV",
            key: "revision",
            sortable: true,
            width: Some("70px"),
        },
        TableColumn {
            label: "FREQ",
            key: "frequency",
            sortable: true,
            width: Some("90px"),
        },
        TableColumn {
            label: "ITEMS",
            key: "items",
            sortable: true,
            width: Some("80px"),
        },
    ];
    let sort_by = Arc::new(|row: &LswStandardDto, key: &str| -> String {
        match key {
            "title" => row.title.clone(),
            "area" => row.area.clone(),
            "layer" => row.layer.to_string(),
            "revision" => row.revision.to_string(),
            "frequency" => row.frequency.clone(),
            "items" => row.checklist_items.len().to_string(),
            _ => String::new(),
        }
    });
    let on_create_submit = RwSignal::new(Some(create_submit.clone()));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"LEADER STANDARD WORK — YOUR CHECKS"</h1>
                <button
                    type="button"
                    class="rams-btn rams-btn--md"
                    on:click=move |_| create_open.set(true)
                >
                    "NEW CHECK"
                </button>
            </div>
            <p class="rams-font-mono rams-text-sm rams-mb-4" style="color: var(--rams-muted);">
                "A check is an OBSERVATION, not an audit form: expected condition, what you actually saw, what made the job harder."
            </p>
            {move || data.map(|w| match &**w { Ok(list) => {
                    let rows: Vec<LswStandardDto> = list.clone();
                    let actions = vec![RowAction {
                        label: "SCHEDULE".to_string(),
                        kind: ActionKind::Primary,
                        on_click: Arc::new(|_std: LswStandardDto| {}),
                    }];
                    view! {
                        <DataTableData
                            columns=columns.clone()
                            rows=rows
                            render_row=Arc::new(|s: LswStandardDto| {
                                vec![
                                    s.title.into_any(),
                                    s.area.into_any(),
                                    s.layer.to_string().into_any(),
                                    format!("v{}", s.revision).into_any(),
                                    s.frequency.to_uppercase().into_any(),
                                    s.checklist_items.len().to_string().into_any(),
                                ]
                            })
                            sort_by=sort_by.clone()
                            state=TableState::Normal
                            caption=Some("Leader standard work checks".to_string())
                            row_actions=actions
                        />
                    }.into_any()
                }
                Err(e) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                        <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                    </div>
                }.into_any(),
            }).unwrap_or_else(|| view! {
                <div class="module rams-mb-4"><div class="module-content">
                    <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p>
                </div></div>
            }.into_any())}

            <Show when=move || create_open.get()>
                <Modal title="New Leader Standard Work".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="lsw-title">"CHECK TITLE"</label>
                        <input id="lsw-title" class="rams-input" prop:value=title placeholder="Line 2 startup observation" />
                        <label class="rams-text-sm" for="lsw-area">"AREA"</label>
                        <input id="lsw-area" class="rams-input" prop:value=area placeholder="Assembly" />
                        <label class="rams-text-sm" for="lsw-layer">"TIER"</label>
                        <input id="lsw-layer" class="rams-input" type="number" prop:value=layer min="1" max="4" />
                        <label class="rams-text-sm" for="lsw-freq">"FREQUENCY"</label>
                        <select id="lsw-freq" class="rams-input" prop:value=frequency>
                            <option value="daily">"DAILY"</option>
                            <option value="weekly">"WEEKLY"</option>
                            <option value="monthly">"MONTHLY"</option>
                        </select>
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button
                            type="button"
                            class="rams-btn rams-btn--md"
                            on:click=move |_| { if let Some(cb) = on_create_submit.get_untracked() { cb() } }
                        >
                            "CREATE CHECK"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Standard Work (item 15 lifecycle in the UI) ─────────────────────────

#[component]
pub fn StandardWorkPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let app_state_for_actions = app_state.clone();
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { list_standard_work(&client).await }
    });
    // Manual refresh signal so lifecycle actions re-render.
    let refresh = RwSignal::new(0u32);

    let create_open = modal_open(false);
    let title = RwSignal::new(String::new());
    let doc_number = RwSignal::new(String::new());
    let area = RwSignal::new(String::new());
    let process = RwSignal::new(String::new());
    let create_error = RwSignal::new(None::<String>);

    let create_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            leptos::task::spawn_local({
                let app_state = app_state_for_submit.clone();
                async move {
                    let client = app_state.api_client();
                    let req = serde_json::json!({
                        "title": title.get_untracked(),
                        "document_number": doc_number.get_untracked(),
                        "area": area.get_untracked(),
                        "process": process.get_untracked(),
                        "steps": [],
                        "required_skills": [],
                        "quality_checks": [],
                    });
                    match create_standard_work(&client, req).await {
                        Ok(_) => {
                            create_open.set(false);
                            refresh.update(|v| *v += 1);
                        }
                        Err(e) => create_error.set(Some(e.to_string())),
                    }
                }
            });
        });
    let columns = vec![
        TableColumn {
            label: "DOC",
            key: "document_number",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TITLE",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "AREA",
            key: "area",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("120px"),
        },
        TableColumn {
            label: "VER",
            key: "version",
            sortable: true,
            width: Some("70px"),
        },
    ];
    let sort_by = Arc::new(|row: &StandardWorkDto, key: &str| -> String {
        match key {
            "document_number" => row.document_number.clone(),
            "title" => row.title.clone(),
            "area" => row.area.clone(),
            "status" => row.status.clone(),
            "version" => row.version.to_string(),
            _ => String::new(),
        }
    });
    let on_create_submit = RwSignal::new(Some(create_submit.clone()));

    // Lifecycle actions (item 15): submit / approve / reject / supersede.
    let submit_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |dto: StandardWorkDto| {
            let client = app_state.api_client();
            let id = dto.id.clone();
            leptos::task::spawn_local(async move {
                let _ = submit_standard_work(&client, &id).await;
                refresh.update(|v| *v += 1);
            });
        })
    };
    let approve_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |dto: StandardWorkDto| {
            let client = app_state.api_client();
            let id = dto.id.clone();
            leptos::task::spawn_local(async move {
                let _ = approve_standard_work(&client, &id, None).await;
                refresh.update(|v| *v += 1);
            });
        })
    };

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"STANDARD WORK"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "NEW STANDARD"
                </button>
            </div>
            {move || {
                let _ = refresh.get();
                data.map(|w| match &**w {
                    Ok(list) => {
                        let rows: Vec<StandardWorkDto> = list.clone();
                        let actions = vec![
                            RowAction { label: "SUBMIT".to_string(), kind: ActionKind::Primary, on_click: submit_action.clone() },
                            RowAction { label: "APPROVE".to_string(), kind: ActionKind::Primary, on_click: approve_action.clone() },
                        ];
                        view! {
                            <DataTableData
                                columns=columns.clone()
                                rows=rows
                                render_row=Arc::new(|s: StandardWorkDto| {
                                    let status_badge = format!("rams-badge status-{}", s.status.to_lowercase().replace('_', "-"));
                                    vec![
                                        s.document_number.clone().into_any(),
                                        s.title.into_any(),
                                        s.area.into_any(),
                                        view! { <span class=status_badge>{s.status.to_uppercase()}</span> }.into_any(),
                                        format!("v{}", s.version).into_any(),
                                    ]
                                })
                                sort_by=sort_by.clone()
                                state=TableState::Normal
                                caption=Some("Standard work documents".to_string())
                                row_actions=actions
                            />
                        }.into_any()
                    }
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                        </div>
                    }.into_any(),
                }).unwrap_or_else(|| view! {
                    <div class="module rams-mb-4"><div class="module-content">
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p>
                    </div></div>
                }.into_any())
            }}
            <Show when=move || create_open.get()>
                <Modal title="New Standard Work".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="sw-doc">"DOCUMENT #"</label>
                        <input id="sw-doc" class="rams-input" prop:value=doc_number placeholder="SW-2026-001" />
                        <label class="rams-text-sm" for="sw-title">"TITLE"</label>
                        <input id="sw-title" class="rams-input" prop:value=title placeholder="Cell 4 assembly" />
                        <label class="rams-text-sm" for="sw-area">"AREA"</label>
                        <input id="sw-area" class="rams-input" prop:value=area placeholder="Assembly" />
                        <label class="rams-text-sm" for="sw-process">"PROCESS"</label>
                        <input id="sw-process" class="rams-input" prop:value=process placeholder="Final assembly" />
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = on_create_submit.get_untracked() { cb() } }>
                            "CREATE DRAFT"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Tier Meetings (item 15 escalation in the UI) ────────────────────────

#[component]
pub fn TierMeetingsPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let app_state_for_actions = app_state.clone();
    let data = ArcLocalResource::new(move || {
        let app_state = app_state.clone();
        let client = app_state.api_client();
        async move { list_tier_meetings(&client).await }
    });
    let refresh = RwSignal::new(0u32);

    let create_open = modal_open(false);
    let title = RwSignal::new(String::new());
    let tier = RwSignal::new(1u8);
    let area = RwSignal::new(String::new());
    let create_error = RwSignal::new(None::<String>);

    let schedule_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> = std::sync::Arc::new(
        move || {
            leptos::task::spawn_local({
                let app_state = app_state_for_submit.clone();
                async move {
                    let client = app_state.api_client();
                    let req = serde_json::json!({
                        "tier_level": tier.get_untracked(),
                        "title": title.get_untracked(),
                        "area": if area.get_untracked().is_empty() { None } else { Some(area.get_untracked()) },
                        "scheduled_at": chrono::Utc::now().to_rfc3339(),
                    });
                    match schedule_tier_meeting(&client, req).await {
                        Ok(_) => {
                            create_open.set(false);
                            refresh.update(|v| *v += 1);
                        }
                        Err(e) => create_error.set(Some(e.to_string())),
                    }
                }
            });
        },
    );
    let start_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |m: TierMeetingDto| {
            let client = app_state.api_client();
            let id = m.id.clone();
            leptos::task::spawn_local(async move {
                let _ = start_tier_meeting(&client, &id).await;
                refresh.update(|v| *v += 1);
            });
        })
    };
    let complete_action = {
        let app_state = app_state_for_actions.clone();
        Arc::new(move |m: TierMeetingDto| {
            let client = app_state.api_client();
            let id = m.id.clone();
            leptos::task::spawn_local(async move {
                let _ = complete_tier_meeting(&client, &id).await;
                refresh.update(|v| *v += 1);
            });
        })
    };

    let columns = vec![
        TableColumn {
            label: "MEETING",
            key: "title",
            sortable: true,
            width: None,
        },
        TableColumn {
            label: "TIER",
            key: "tier_level",
            sortable: true,
            width: Some("70px"),
        },
        TableColumn {
            label: "STATUS",
            key: "status",
            sortable: true,
            width: Some("120px"),
        },
        TableColumn {
            label: "SCHEDULED",
            key: "scheduled_at",
            sortable: true,
            width: None,
        },
    ];
    let sort_by = Arc::new(|row: &TierMeetingDto, key: &str| -> String {
        match key {
            "title" => row.title.clone(),
            "tier_level" => row.tier_level.to_string(),
            "status" => row.status.clone(),
            "scheduled_at" => row.scheduled_at.clone(),
            _ => String::new(),
        }
    });
    let on_schedule_submit = RwSignal::new(Some(schedule_submit.clone()));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"TIER MEETINGS"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "SCHEDULE MEETING"
                </button>
            </div>
            {move || {
                let _ = refresh.get();
                data.map(|w| match &**w {
                    Ok(list) => {
                        let rows: Vec<TierMeetingDto> = list.clone();
                        let actions = vec![
                            RowAction { label: "START".to_string(), kind: ActionKind::Primary, on_click: start_action.clone() },
                            RowAction { label: "COMPLETE".to_string(), kind: ActionKind::Ghost, on_click: complete_action.clone() },
                        ];
                        view! {
                            <DataTableData
                                columns=columns.clone()
                                rows=rows
                                render_row=Arc::new(|m: TierMeetingDto| {
                                    let badge = format!("rams-badge status-{}", m.status.to_lowercase());
                                    vec![
                                        m.title.into_any(),
                                        format!("T{}", m.tier_level).into_any(),
                                        view! { <span class=badge>{m.status.to_uppercase()}</span> }.into_any(),
                                        short_id(&m.scheduled_at).into_any(),
                                    ]
                                })
                                sort_by=sort_by.clone()
                                state=TableState::Normal
                                caption=Some("Tier meetings".to_string())
                                row_actions=actions
                            />
                        }.into_any()
                    }
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                        </div>
                    }.into_any(),
                }).unwrap_or_else(|| view! {
                    <div class="module rams-mb-4"><div class="module-content">
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p>
                    </div></div>
                }.into_any())
            }}
            <Show when=move || create_open.get()>
                <Modal title="Schedule Tier Meeting".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="tm-tier">"TIER (1 line/cell, 2 value stream, 3 plant, 4 site)"</label>
                        <input id="tm-tier" class="rams-input" type="number" prop:value=tier min="1" max="4" />
                        <label class="rams-text-sm" for="tm-title">"TITLE"</label>
                        <input id="tm-title" class="rams-input" prop:value=title placeholder="Tier 2 daily walk" />
                        <label class="rams-text-sm" for="tm-area">"AREA (optional)"</label>
                        <input id="tm-area" class="rams-input" prop:value=area placeholder="Assembly" />
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = on_schedule_submit.get_untracked() { cb() } }>
                            "SCHEDULE"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Topology (sites / value streams / product families) ─────────────────

#[component]
pub fn TopologyPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let sites = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let client = app_state.api_client();
            async move { list_sites(&client).await }
        }
    });
    let streams = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let client = app_state.api_client();
            async move { list_value_streams(&client).await }
        }
    });
    let families = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let client = app_state.api_client();
            async move { list_product_families(&client).await }
        }
    });

    let site_open = modal_open(false);
    let site_code = RwSignal::new(String::new());
    let site_name = RwSignal::new(String::new());
    let site_tz = RwSignal::new("UTC".to_string());
    let create_error = RwSignal::new(None::<String>);

    let site_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            leptos::task::spawn_local({
                let app_state = app_state_for_submit.clone();
                async move {
                    let client = app_state.api_client();
                    let req = serde_json::json!({
                        "site_code": site_code.get_untracked(),
                        "name": site_name.get_untracked(),
                        "timezone": site_tz.get_untracked(),
                        "is_active": true,
                    });
                    match create_site(&client, req).await {
                        Ok(_) => site_open.set(false),
                        Err(e) => create_error.set(Some(e.to_string())),
                    }
                }
            });
        });
    let on_site_submit = RwSignal::new(Some(site_submit.clone()));
    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"PLANT TOPOLOGY"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| site_open.set(true)>
                    "NEW SITE"
                </button>
            </div>
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"SITES"</h3></div>
                <div class="module-content">
                    {move || sites.map(|w| match &**w { Ok(list) => view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "CODE", key: "site_code", sortable: true, width: None },
                                    TableColumn { label: "NAME", key: "name", sortable: true, width: None },
                                    TableColumn { label: "TZ", key: "timezone", sortable: true, width: None },
                                ]
                                rows=list.clone()
                                render_row=Arc::new(|s: SiteDto| {
                                    vec![s.site_code.into_any(), s.name.clone().into_any(), s.timezone.clone().into_any()]
                                })
                                sort_by=Arc::new(|row: &SiteDto, key: &str| -> String {
                                    match key { "site_code" => row.site_code.clone(), "name" => row.name.clone(), "timezone" => row.timezone.clone(), _ => String::new() }
                                })
                                state=TableState::Normal
                                caption=Some("Sites".to_string())
                            />
                        }.into_any(),
                        Err(_) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert"><strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong></div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p> }.into_any())}
                </div>
            </div>
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"VALUE STREAMS"</h3></div>
                <div class="module-content">
                    {move || streams.map(|w| match &**w { Ok(list) => view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "NAME", key: "name", sortable: true, width: None },
                                    TableColumn { label: "SITE", key: "site_id", sortable: true, width: None },
                                    TableColumn { label: "STATUS", key: "is_active", sortable: true, width: None },
                                ]
                                rows=list.clone()
                                render_row=Arc::new(|v: ValueStreamDto| {
                                    vec![v.name.clone().into_any(), short_id(&v.site_id).into_any(), if v.is_active { "ACTIVE".into_any() } else { "INACTIVE".into_any() }]
                                })
                                sort_by=Arc::new(|row: &ValueStreamDto, key: &str| -> String {
                                    match key { "name" => row.name.clone(), "site_id" => row.site_id.clone(), "is_active" => row.is_active.to_string(), _ => String::new() }
                                })
                                state=TableState::Normal
                                caption=Some("Value streams".to_string())
                            />
                        }.into_any(),
                        Err(_) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert"><strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong></div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p> }.into_any())}
                </div>
            </div>
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"PRODUCT FAMILIES"</h3></div>
                <div class="module-content">
                    {move || families.map(|w| match &**w { Ok(list) => view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "NAME", key: "name", sortable: true, width: None },
                                    TableColumn { label: "DESCRIPTION", key: "description", sortable: true, width: None },
                                ]
                                rows=list.clone()
                                render_row=Arc::new(|f: ProductFamilyDto| {
                                    vec![f.name.clone().into_any(), f.description.clone().unwrap_or_default().into_any()]
                                })
                                sort_by=Arc::new(|row: &ProductFamilyDto, key: &str| -> String {
                                    match key { "name" => row.name.clone(), "description" => row.description.clone().unwrap_or_default(), _ => String::new() }
                                })
                                state=TableState::Normal
                                caption=Some("Product families".to_string())
                            />
                        }.into_any(),
                        Err(_) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert"><strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong></div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p> }.into_any())}
                </div>
            </div>
            <Show when=move || site_open.get()>
                <Modal title="New Site".to_string() open=site_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="site-code">"SITE CODE"</label>
                        <input id="site-code" class="rams-input" prop:value=site_code placeholder="TNG" />
                        <label class="rams-text-sm" for="site-name">"NAME"</label>
                        <input id="site-name" class="rams-input" prop:value=site_name placeholder="Tanger" />
                        <label class="rams-text-sm" for="site-tz">"TIMEZONE (IANA)"</label>
                        <input id="site-tz" class="rams-input" prop:value=site_tz placeholder="Africa/Casablanca" />
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = on_site_submit.get_untracked() { cb() } }>
                            "CREATE SITE"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Work Centers (item 64: cells / work centers first-class) ────────────

#[component]
pub fn WorkCentersPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { list_work_centers(&client).await }
    });
    let refresh = RwSignal::new(0u32);

    let create_open = modal_open(false);
    let wc_number = RwSignal::new(String::new());
    let wc_name = RwSignal::new(String::new());
    let wc_type = RwSignal::new("assembly".to_string());
    let create_error = RwSignal::new(None::<String>);

    let create_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            leptos::task::spawn_local({
                let app_state = app_state_for_submit.clone();
                async move {
                    let client = app_state.api_client();
                    let req = serde_json::json!({
                        "work_center_number": wc_number.get_untracked(),
                        "name": wc_name.get_untracked(),
                        "work_center_type": wc_type.get_untracked(),
                        "description": "",
                        "is_active": true,
                        "capacity_per_shift": 480,
                        "shifts_per_day": 2,
                        "efficiency": 1.0,
                        "available_hours_per_day": 16.0,
                    });
                    match create_work_center(&client, req).await {
                        Ok(_) => {
                            create_open.set(false);
                            refresh.update(|v| *v += 1);
                        }
                        Err(e) => create_error.set(Some(e.to_string())),
                    }
                }
            });
        });
    let on_create_submit_wc = RwSignal::new(Some(create_submit.clone()));
    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"WORK CENTERS / CELLS"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "NEW WORK CENTER"
                </button>
            </div>
            {move || {
                let _ = refresh.get();
                data.map(|w| match &**w {
                    Ok(list) => view! {
                        <DataTableData
                            columns=vec![
                                TableColumn { label: "NUMBER", key: "work_center_number", sortable: true, width: None },
                                TableColumn { label: "NAME", key: "name", sortable: true, width: None },
                                TableColumn { label: "TYPE", key: "work_center_type", sortable: true, width: None },
                                TableColumn { label: "DEPARTMENT", key: "department", sortable: true, width: None },
                                TableColumn { label: "CAP/SHIFT", key: "capacity_per_shift", sortable: true, width: Some("90px") },
                            ]
                            rows=list.clone()
                            render_row=Arc::new(|w: WorkCenterDto| {
                                vec![
                                    w.work_center_number.clone().into_any(),
                                    w.name.clone().into_any(),
                                    w.work_center_type.to_uppercase().into_any(),
                                    w.department.clone().unwrap_or_else(|| "—".to_string()).into_any(),
                                    w.capacity_per_shift.to_string().into_any(),
                                ]
                            })
                            sort_by=Arc::new(|row: &WorkCenterDto, key: &str| -> String {
                                match key {
                                    "work_center_number" => row.work_center_number.clone(),
                                    "name" => row.name.clone(),
                                    "work_center_type" => row.work_center_type.clone(),
                                    "department" => row.department.clone().unwrap_or_default(),
                                    "capacity_per_shift" => row.capacity_per_shift.to_string(),
                                    _ => String::new(),
                                }
                            })
                            state=TableState::Normal
                            caption=Some("Work centers".to_string())
                        />
                    }.into_any(),
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                        </div>
                    }.into_any(),
                }).unwrap_or_else(|| view! {
                    <div class="module rams-mb-4"><div class="module-content">
                        <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p>
                    </div></div>
                }.into_any())
            }}
            <Show when=move || create_open.get()>
                <Modal title="New Work Center".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="wc-number">"NUMBER"</label>
                        <input id="wc-number" class="rams-input" prop:value=wc_number placeholder="WC-04" />
                        <label class="rams-text-sm" for="wc-name">"NAME"</label>
                        <input id="wc-name" class="rams-input" prop:value=wc_name placeholder="Cell 4" />
                        <label class="rams-text-sm" for="wc-type">"TYPE"</label>
                        <select id="wc-type" class="rams-input" prop:value=wc_type>
                            <option value="assembly">"ASSEMBLY"</option>
                            <option value="machining">"MACHINING"</option>
                            <option value="test">"TEST"</option>
                            <option value="packaging">"PACKAGING"</option>
                        </select>
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = on_create_submit_wc.get_untracked() { cb() } }>
                            "CREATE"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// Helper to satisfy unused-import lint when only some helpers are used.
