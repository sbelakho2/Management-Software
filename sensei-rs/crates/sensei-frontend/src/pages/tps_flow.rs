//! TPS flow surfaces (items 64/67): Kanban, Training Matrix (item 39:
//! pull-driven skill coverage), CTQ (item 34: quality at source), Obeya
//! (item 40: aggregation of the same issue ids) and the Agent tool
//! surface (item 68: inline, evidence-first) — full workflows, explicit
//! error states (item 4).

use crate::api::tps::*;
use crate::components::data_table::{DataTableData, TableColumn, TableState};
use crate::components::modal::Modal;
use crate::state::AppState;
use leptos::prelude::*;
use std::sync::Arc;

// ── Kanban (item 64: boards + cards, pull-based visual control) ─────────

#[component]
pub fn KanbanPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_kanban_boards(&client).await }
        }
    });
    let create_open = modal_open(false);
    let board_name = RwSignal::new(String::new());
    let board_desc = RwSignal::new(String::new());
    let create_error = RwSignal::new(None::<String>);

    let create_submit_arc: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            let app_state = app_state_for_submit.clone();
            {
                leptos::task::spawn_local({
                    let app_state = app_state.clone();
                    async move {
                        let client = app_state.api_client();
                        let req = serde_json::json!({
                            "name": board_name.get_untracked(),
                            "description": board_desc.get_untracked(),
                        });
                        match create_kanban_board(&client, req).await {
                            Ok(_) => create_open.set(false),
                            Err(e) => create_error.set(Some(e.to_string())),
                        }
                    }
                });
            }
        });
    let create_submit = RwSignal::new(Some(create_submit_arc));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"KANBAN"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "NEW BOARD"
                </button>
            </div>
            {move || data.map(|w| match &**w { Ok(boards) => view! {
                    <div class="rams-grid rams-grid--cols-2 rams-gap-4">
                        {boards.iter().map(|b| {
                            let name = b.name.clone();
                            let desc = b.description.clone();
                            let cols = b.columns.clone();
                            view! {
                                <div class="module">
                                    <div class="module-header"><h3 class="module-title">{name}</h3></div>
                                    <div class="module-content">
                                        <p class="rams-font-mono rams-text-sm rams-mb-3" style="color: var(--rams-muted);">{desc}</p>
                                        <div class="rams-flex rams-flex--wrap rams-gap-2">
                                            {cols.iter().map(|c| {
                                                let col_name = c.name.clone();
                                                let cards = c.cards.clone();
                                                let count = cards.len();
                                                view! {
                                                    <div class="module" style="flex: 1; min-width: 180px;">
                                                        <div class="module-header">
                                                            <h4 class="module-title">{col_name.clone()}</h4>
                                                            <span class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">{count.to_string()}</span>
                                                        </div>
                                                        <div class="module-content">
                                                            {if cards.is_empty() {
                                                                view! { <p class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">"EMPTY"</p> }.into_any()
                                                            } else {
                                                                view! {
                                                                    {cards.iter().map(|card| {
                                                                        let title = card.title.clone();
                                                                        let prio = card.priority.clone();
                                                                        let assignee = card.assigned_to.clone();
                                                                        view! {
                                                                            <div class="rams-card rams-mb-2" style="padding: var(--rams-space-2); border: 1px solid var(--rams-line);">
                                                                                <p class="rams-text-sm">{title}</p>
                                                                                <p class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">
                                                                                    {format!("{} · {}", prio.to_uppercase(), assignee.unwrap_or_else(|| "unassigned".to_string()))}
                                                                                </p>
                                                                            </div>
                                                                        }
                                                                    }).collect::<Vec<_>>()}
                                                                }.into_any()
                                                            }}
                                                        </div>
                                                    </div>
                                                }
                                            }).collect::<Vec<_>>()}
                                        </div>
                                    </div>
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
            }).unwrap_or_else(|| view! { <div class="module rams-mb-4"><div class="module-content"><p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p></div></div> }.into_any())}
            <Show when=move || create_open.get()>
                <Modal title="New Kanban Board".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="kb-name">"NAME"</label>
                        <input id="kb-name" class="rams-input" prop:value=board_name placeholder="Cell 4 pull board" />
                        <label class="rams-text-sm" for="kb-desc">"DESCRIPTION"</label>
                        <input id="kb-desc" class="rams-input" prop:value=board_desc placeholder="Replenishment of component kits" />
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = create_submit.get_untracked() { cb() } }>
                            "CREATE BOARD"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Training Matrix (item 39: can the current team run today's flow?) ───

#[component]
pub fn TrainingPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_training_matrix(&client).await }
        }
    });
    let gaps = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_skill_gaps(&client).await }
        }
    });
    let create_open = modal_open(false);
    let emp_name = RwSignal::new(String::new());
    let skill = RwSignal::new(String::new());
    let category = RwSignal::new(String::new());
    let level = RwSignal::new("trained".to_string());
    let create_error = RwSignal::new(None::<String>);

    let create_submit_arc: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            let app_state = app_state_for_submit.clone();
            {
                leptos::task::spawn_local({
                    let app_state = app_state.clone();
                    async move {
                        let client = app_state.api_client();
                        let req = serde_json::json!({
                            "employee_name": emp_name.get_untracked(),
                            "skill_name": skill.get_untracked(),
                            "skill_category": category.get_untracked(),
                            "proficiency_level": level.get_untracked(),
                            "notes": "",
                        });
                        match create_training_entry(&client, req).await {
                            Ok(_) => create_open.set(false),
                            Err(e) => create_error.set(Some(e.to_string())),
                        }
                    }
                });
            }
        });
    let create_submit = RwSignal::new(Some(create_submit_arc));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"TRAINING MATRIX"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "RECORD SKILL"
                </button>
            </div>
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"SKILL GAPS — CAN TODAY'S FLOW BE COVERED?"</h3></div>
                <div class="module-content">
                    {move || gaps.map(|w| match &**w { Ok(g) => view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "SKILL", key: "skill_name", sortable: true, width: None },
                                    TableColumn { label: "CATEGORY", key: "skill_category", sortable: true, width: None },
                                    TableColumn { label: "AVAILABLE", key: "available_count", sortable: true, width: Some("90px") },
                                    TableColumn { label: "REQUIRED", key: "required_count", sortable: true, width: Some("90px") },
                                    TableColumn { label: "GAP", key: "gap", sortable: true, width: Some("70px") },
                                ]
                                rows=g.clone()
                                render_row=Arc::new(|s: SkillGapDto| {
                                    let badge = if s.gap > 0 { "rams-badge status-open" } else { "rams-badge status-ok" };
                                    vec![
                                        s.skill_name.clone().into_any(),
                                        s.skill_category.into_any(),
                                        s.available_count.to_string().into_any(),
                                        s.required_count.to_string().into_any(),
                                        view! { <span class=badge>{s.gap.to_string()}</span> }.into_any(),
                                    ]
                                })
                                sort_by=Arc::new(|row: &SkillGapDto, key: &str| -> String {
                                    match key {
                                        "skill_name" => row.skill_name.clone(),
                                        "skill_category" => row.skill_category.clone(),
                                        "available_count" => row.available_count.to_string(),
                                        "required_count" => row.required_count.to_string(),
                                        "gap" => row.gap.to_string(),
                                        _ => String::new(),
                                    }
                                })
                                state=TableState::Normal
                                caption=Some("Skill gaps".to_string())
                            />
                        }.into_any(),
                        Err(e) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert"><strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong><p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p></div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p> }.into_any())}
                </div>
            </div>
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"MATRIX"</h3></div>
                <div class="module-content">
                    {move || data.map(|w| match &**w { Ok(list) => view! {
                            <DataTableData
                                columns=vec![
                                    TableColumn { label: "EMPLOYEE", key: "employee_name", sortable: true, width: None },
                                    TableColumn { label: "SKILL", key: "skill_name", sortable: true, width: None },
                                    TableColumn { label: "LEVEL", key: "proficiency_level", sortable: true, width: None },
                                    TableColumn { label: "VALID UNTIL", key: "valid_until", sortable: true, width: None },
                                ]
                                rows=list.clone()
                                render_row=Arc::new(|t: TrainingMatrixDto| {
                                    vec![
                                        t.employee_name.clone().into_any(),
                                        t.skill_name.clone().into_any(),
                                        t.proficiency_level.to_uppercase().into_any(),
                                        t.valid_until.clone().unwrap_or_else(|| "—".to_string()).into_any(),
                                    ]
                                })
                                sort_by=Arc::new(|row: &TrainingMatrixDto, key: &str| -> String {
                                    match key {
                                        "employee_name" => row.employee_name.clone(),
                                        "skill_name" => row.skill_name.clone(),
                                        "proficiency_level" => row.proficiency_level.clone(),
                                        "valid_until" => row.valid_until.clone().unwrap_or_default(),
                                        _ => String::new(),
                                    }
                                })
                                state=TableState::Normal
                                caption=Some("Training matrix".to_string())
                            />
                        }.into_any(),
                        Err(e) => view! {
                            <div class="rams-alert rams-alert--danger" role="alert"><strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong><p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p></div>
                        }.into_any(),
                    }).unwrap_or_else(|| view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p> }.into_any())}
                </div>
            </div>
            <Show when=move || create_open.get()>
                <Modal title="Record Skill".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="tr-emp">"EMPLOYEE"</label>
                        <input id="tr-emp" class="rams-input" prop:value=emp_name placeholder="Amine B." />
                        <label class="rams-text-sm" for="tr-skill">"SKILL"</label>
                        <input id="tr-skill" class="rams-input" prop:value=skill placeholder="Test-2 operation" />
                        <label class="rams-text-sm" for="tr-cat">"CATEGORY"</label>
                        <input id="tr-cat" class="rams-input" prop:value=category placeholder="Final test" />
                        <label class="rams-text-sm" for="tr-level">"PROFICIENCY"</label>
                        <select id="tr-level" class="rams-input" prop:value=level>
                            <option value="aware">"AWARE"</option>
                            <option value="trained">"TRAINED"</option>
                            <option value="qualified">"QUALIFIED"</option>
                            <option value="certified">"CERTIFIED"</option>
                        </select>
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = create_submit.get_untracked() { cb() } }>
                            "RECORD"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── CTQ (item 34: quality at source — CTQs bound to the standard) ───────

#[component]
pub fn CtqPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_ctq_characteristics(&client).await }
        }
    });
    let create_open = modal_open(false);
    let ctq_name = RwSignal::new(String::new());
    let ctq_cat = RwSignal::new(String::new());
    let ctq_unit = RwSignal::new(String::new());
    let ctq_lower = RwSignal::new(String::new());
    let ctq_upper = RwSignal::new(String::new());
    let create_error = RwSignal::new(None::<String>);

    let create_submit_arc: std::sync::Arc<dyn Fn() + Send + Sync + 'static> = std::sync::Arc::new(
        move || {
            let app_state = app_state_for_submit.clone();
            {
                leptos::task::spawn_local({
                    let app_state = app_state.clone();
                    async move {
                        let client = app_state.api_client();
                        let req = serde_json::json!({
                            "name": ctq_name.get_untracked(),
                            "category": ctq_cat.get_untracked(),
                            "unit": if ctq_unit.get_untracked().is_empty() { None } else { Some(ctq_unit.get_untracked()) },
                            "specification_limit_lower": ctq_lower.get_untracked().parse::<f64>().ok(),
                            "specification_limit_upper": ctq_upper.get_untracked().parse::<f64>().ok(),
                            "description": "",
                            "measurement_method": "manual",
                        });
                        match create_ctq(&client, req).await {
                            Ok(_) => create_open.set(false),
                            Err(e) => create_error.set(Some(e.to_string())),
                        }
                    }
                });
            }
        },
    );
    let create_submit = RwSignal::new(Some(create_submit_arc));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"CTQ CHARACTERISTICS"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "NEW CTQ"
                </button>
            </div>
            {move || data.map(|w| match &**w { Ok(list) => view! {
                    <DataTableData
                        columns=vec![
                            TableColumn { label: "CTQ", key: "name", sortable: true, width: None },
                            TableColumn { label: "CATEGORY", key: "category", sortable: true, width: None },
                            TableColumn { label: "SPEC LIMITS", key: "limits", sortable: true, width: None },
                            TableColumn { label: "TARGET", key: "target_value", sortable: true, width: None },
                            TableColumn { label: "UNIT", key: "unit", sortable: true, width: None },
                        ]
                        rows=list.clone()
                        render_row=Arc::new(|c: CtqDto| {
                            let limits = match (c.specification_limit_lower, c.specification_limit_upper) {
                                (Some(l), Some(u)) => format!("{l} .. {u}"),
                                (Some(l), None) => format!("≥ {l}"),
                                (None, Some(u)) => format!("≤ {u}"),
                                (None, None) => "—".to_string(),
                            };
                            vec![
                                c.name.clone().into_any(),
                                c.category.into_any(),
                                limits.into_any(),
                                c.target_value.map(|t| t.to_string()).unwrap_or_else(|| "—".to_string()).into_any(),
                                c.unit.clone().unwrap_or_else(|| "—".to_string()).into_any(),
                            ]
                        })
                        sort_by=Arc::new(|row: &CtqDto, key: &str| -> String {
                            match key {
                                "name" => row.name.clone(),
                                "category" => row.category.clone(),
                                "limits" => format!("{:?}{:?}", row.specification_limit_lower, row.specification_limit_upper),
                                "target_value" => row.target_value.map(|t| t.to_string()).unwrap_or_default(),
                                "unit" => row.unit.clone().unwrap_or_default(),
                                _ => String::new(),
                            }
                        })
                        state=TableState::Normal
                        caption=Some("CTQ characteristics".to_string())
                    />
                }.into_any(),
                Err(e) => view! {
                    <div class="rams-alert rams-alert--danger" role="alert">
                        <strong>"STATUS UNKNOWN — LIVE DATA UNAVAILABLE"</strong>
                        <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                    </div>
                }.into_any(),
            }).unwrap_or_else(|| view! { <div class="module rams-mb-4"><div class="module-content"><p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p></div></div> }.into_any())}
            <Show when=move || create_open.get()>
                <Modal title="New CTQ".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="ctq-name">"NAME"</label>
                        <input id="ctq-name" class="rams-input" prop:value=ctq_name placeholder="Pin depth" />
                        <label class="rams-text-sm" for="ctq-cat">"CATEGORY"</label>
                        <input id="ctq-cat" class="rams-input" prop:value=ctq_cat placeholder="Geometry" />
                        <label class="rams-text-sm" for="ctq-unit">"UNIT"</label>
                        <input id="ctq-unit" class="rams-input" prop:value=ctq_unit placeholder="mm" />
                        <label class="rams-text-sm" for="ctq-lower">"LOWER SPEC"</label>
                        <input id="ctq-lower" class="rams-input" prop:value=ctq_lower placeholder="7.8" />
                        <label class="rams-text-sm" for="ctq-upper">"UPPER SPEC"</label>
                        <input id="ctq-upper" class="rams-input" prop:value=ctq_upper placeholder="8.2" />
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = create_submit.get_untracked() { cb() } }>
                            "CREATE CTQ"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Obeya (item 40: aggregation of the SAME issue ids) ──────────────────

#[component]
pub fn ObeyaPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let data = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_obeya_boards(&client).await }
        }
    });
    let create_open = modal_open(false);
    let board_name = RwSignal::new(String::new());
    let board_type = RwSignal::new("tier".to_string());
    let create_error = RwSignal::new(None::<String>);

    let create_submit_arc: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            let app_state = app_state_for_submit.clone();
            {
                leptos::task::spawn_local({
                    let app_state = app_state.clone();
                    async move {
                        let client = app_state.api_client();
                        let req = serde_json::json!({
                            "name": board_name.get_untracked(),
                            "board_type": board_type.get_untracked(),
                            "description": "",
                        });
                        match create_obeya_board(&client, req).await {
                            Ok(_) => create_open.set(false),
                            Err(e) => create_error.set(Some(e.to_string())),
                        }
                    }
                });
            }
        });
    let create_submit = RwSignal::new(Some(create_submit_arc));

    view! {
        <div class="rams-p-4">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"OBEYA"</h1>
                <button type="button" class="rams-btn rams-btn--md" on:click=move |_| create_open.set(true)>
                    "NEW BOARD"
                </button>
            </div>
            {move || data.map(|w| match &**w { Ok(boards) => view! {
                    <div class="rams-grid rams-grid--cols-2 rams-gap-4">
                        {boards.iter().map(|b| {
                            let name = b.name.clone();
                            let btype = b.board_type.clone();
                            let items = b.items.clone();
                            let open_count = items.iter().filter(|i| i.status.to_lowercase() != "closed").count();
                            view! {
                                <div class="module">
                                    <div class="module-header">
                                        <h3 class="module-title">{name}</h3>
                                        <span class=format!("rams-badge {}", if open_count > 0 { "status-open" } else { "status-ok" })>
                                            {format!("{open_count} OPEN")}
                                        </span>
                                    </div>
                                    <div class="module-content">
                                        <p class="rams-font-mono rams-text-2xs rams-mb-2" style="color: var(--rams-muted);">
                                            {btype.to_uppercase()}
                                        </p>
                                        {items.iter().take(8).map(|i| {
                                            let title = i.title.clone();
                                            let prio = i.priority.clone();
                                            let status = i.status.clone();
                                            view! {
                                                <div class="rams-flex rams-flex--between" style="padding: 2px 0; border-bottom: 1px solid var(--rams-line);">
                                                    <span class="rams-text-sm">{title}</span>
                                                    <span class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">
                                                        {format!("{} · {}", prio.to_uppercase(), status.to_uppercase())}
                                                    </span>
                                                </div>
                                            }
                                        }).collect::<Vec<_>>()}
                                    </div>
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
            }).unwrap_or_else(|| view! { <div class="module rams-mb-4"><div class="module-content"><p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p></div></div> }.into_any())}
            <Show when=move || create_open.get()>
                <Modal title="New Obeya Board".to_string() open=create_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <label class="rams-text-sm" for="ob-name">"NAME"</label>
                        <input id="ob-name" class="rams-input" prop:value=board_name placeholder="Plant daily" />
                        <label class="rams-text-sm" for="ob-type">"TYPE"</label>
                        <select id="ob-type" class="rams-input" prop:value=board_type>
                            <option value="tier">"TIER"</option>
                            <option value="project">"PROJECT"</option>
                            <option value="site">"SITE"</option>
                        </select>
                        {move || create_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = create_submit.get_untracked() { cb() } }>
                            "CREATE BOARD"
                        </button>
                    </div>
                </Modal>
            </Show>
        </div>
    }
}

// ── Agent tool surface (item 68: evidence-first, inline) ────────────────

#[component]
pub fn AgentPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_submit = app_state.clone();
    let tools = ArcLocalResource::new({
        let app_state = app_state.clone();
        move || {
            let app_state = app_state.clone();
            let client = app_state.api_client();
            async move { list_agent_tools(&client).await }
        }
    });
    let selected_tool = RwSignal::new(String::new());
    let tool_args = RwSignal::new(String::new());
    let result_text = RwSignal::new(None::<String>);
    let result_error = RwSignal::new(None::<String>);
    let running = RwSignal::new(false);

    let run_tool_arc: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            let app_state = app_state_for_submit.clone();
            leptos::task::spawn_local({
                let app_state = app_state.clone();
                async move {
                    let client = app_state.api_client();
                    running.set(true);
                    result_error.set(None);
                    result_text.set(None);
                    let args: serde_json::Value = tool_args
                        .get_untracked()
                        .parse()
                        .unwrap_or(serde_json::Value::Null);
                    match execute_agent_tool(&client, &selected_tool.get_untracked(), args).await {
                        Ok(resp) => {
                            let verification = resp
                                .verification
                                .map(|v| serde_json::to_string_pretty(&v).unwrap_or_default())
                                .unwrap_or_else(|| "not reported".to_string());
                            result_text.set(Some(format!(
                                "RESULT:\n{}\n\nVERIFICATION:\n{}",
                                serde_json::to_string_pretty(&resp.result).unwrap_or_default(),
                                verification
                            )));
                        }
                        Err(e) => result_error.set(Some(e.to_string())),
                    }
                    running.set(false);
                }
            });
        });
    let run_tool = RwSignal::new(Some(run_tool_arc));

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"STARZ FORGE AGENT — EVIDENCE-FIRST"</h1>
            {move || tools.map(|w| match &**w { Ok(list) => {
                    let list_owned: Vec<AgentToolDto> = list.clone();
                    view! {
                    <div class="module rams-mb-4">
                        <div class="module-header"><h3 class="module-title">"AVAILABLE TOOLS"</h3></div>
                        <div class="module-content">
                            <div class="rams-grid rams-grid--cols-2 rams-gap-2">
                                {list_owned.iter().map(|t| {
                                    let name = t.name.clone();
                                    let _desc = t.description.clone();
                                    let risk = t.risk.clone();
                                    let is_sel = selected_tool.get() == name;
                                    let sel = selected_tool;
                                    view! {
                                        <button
                                            type="button"
                                            class=format!("rams-btn {} rams-btn--sm", if is_sel { "" } else { "rams-btn--ghost" })
                                            on:click=move |_| sel.set(name.clone())
                                        >
                                            {name.to_uppercase()}
                                            <span class="rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">
                                                {format!(" · {risk}")}
                                            </span>
                                        </button>
                                    }
                                }).collect::<Vec<_>>()}
                            </div>
                            <p class="rams-font-mono rams-text-2xs rams-mt-2" style="color: var(--rams-muted);">
                                {move || list_owned.iter().find(|t| t.name.clone() == selected_tool.get()).map(|t| t.description.clone()).unwrap_or_default()}
                            </p>
                        </div>
                    </div>
                    <div class="module rams-mb-4">
                        <div class="module-header"><h3 class="module-title">"ARGUMENTS (JSON)"</h3></div>
                        <div class="module-content">
                            <textarea
                                class="rams-input"
                                rows="4"
                                prop:value=tool_args
                                placeholder=r#"{"id": "..."}"#
                            ></textarea>
                            <div class="rams-flex rams-gap-2 rams-mt-2">
                                <button type="button" class="rams-btn rams-btn--md" disabled=running on:click=move |_| { if let Some(cb) = run_tool.get_untracked() { cb() } }>
                                    {move || if running.get() { "RUNNING…" } else { "EXECUTE" }}
                                </button>
                            </div>
                            {move || result_error.get().map(|e| view! {
                                <div class="rams-alert rams-alert--danger rams-mt-2" role="alert">{e}</div>
                            })}
                            {move || result_text.get().map(|t| view! {
                                <pre class="rams-mt-2" style="white-space: pre-wrap; font-family: var(--rams-font-mono); font-size: 12px; color: var(--rams-foreground);">{t}</pre>
                            })}
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
            }).unwrap_or_else(|| view! { <div class="module rams-mb-4"><div class="module-content"><p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING…"</p></div></div> }.into_any())}
        </div>
    }
}

fn modal_open(open: bool) -> leptos::prelude::RwSignal<bool> {
    leptos::prelude::RwSignal::new(open)
}
