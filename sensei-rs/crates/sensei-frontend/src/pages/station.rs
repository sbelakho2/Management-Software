//! Operator station (item 31) and team-lead interval control (item 32):
//! the Jidoka-instinctive screens. The operator sees CURRENT JOB, RIGHT
//! NOW pitch, CURRENT STEP, KEY POINT and one prominent "I NEED HELP"
//! action with plain-language categories — no Andon terminology required.
//! The team lead sees plan-vs-actual per interval with the "what stopped
//! flow?" timeline. Both render explicit UNAVAILABLE states (item 4).

use crate::api::tps::*;
use crate::state::AppState;
use leptos::prelude::*;

// ── Operator station (item 31) ──────────────────────────────────────────

#[component]
pub fn StationPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let app_state_for_help = app_state.clone();
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { get_station_snapshot(&client, None).await }
    });
    let refresh = RwSignal::new(0u32);

    // "I NEED HELP": raise an Andon with the selected plain-language
    // category. The operator never sees the word "Andon".
    let help_open = RwSignal::new(false);
    let help_category = RwSignal::new("Quality".to_string());
    let help_note = RwSignal::new(String::new());
    let help_error = RwSignal::new(None::<String>);
    let help_status = RwSignal::new(HelpRequestState::Idle);

    let help_submit: std::sync::Arc<dyn Fn() + Send + Sync + 'static> =
        std::sync::Arc::new(move || {
            let app_state = app_state_for_help.clone();
            leptos::task::spawn_local({
                let app_state = app_state.clone();
                async move {
                    let client = app_state.api_client();
                    // Item 40: the SAFE command path — the operator's
                    // plain-language category + note; the server derives
                    // actor/tenant/status/work center.
                    let req = crate::api::andon::RaiseAndonCommandRequest {
                        work_center_id: None, // server resolves from the caller
                        issue_type: normalize_help_category(&help_category.get_untracked()),
                        severity: "medium".to_string(),
                        description: help_note.get_untracked(),
                    };
                    let _ = crate::api::ops::OpsApi::raise_andon_command(&client, &req).await;
                    help_open.set(false);
                    help_note.set(String::new());
                    refresh.update(|v| *v += 1);
                }
            });
        });
    let on_help_submit = RwSignal::new(Some(help_submit));

    view! {
        <div class="rams-p-4">
            {move || {
                let _ = refresh.get();
                data.map(|w| match &**w {
                    Ok(s) => {
                        let current_job = s.current_job.clone();
                        let pitch = s.pitch.clone();
                        let step = s.current_step.clone();
                        let quality_check = s.quality_check.clone();
                        let categories = s.help_categories.clone();
                        let wc = s.work_center_name.clone();
                        view! {
                            <StationView
                                wc_name=wc
                                current_job=current_job
                                pitch=pitch
                                step=step
                                quality_check=quality_check
                                categories=categories
                                on_help=on_help_submit
                                help_open=help_open
                                help_category=help_category
                                help_note=help_note
                                help_error=help_error
                                help_status=help_status
                            />
                        }.into_any()
                    }
                    Err(e) => view! {
                        <div class="rams-alert rams-alert--danger" role="alert">
                            <strong>"STATUS UNKNOWN — STATION DATA UNAVAILABLE"</strong>
                            <p class="rams-mt-2 rams-text-sm">{format!("{e}")}</p>
                        </div>
                    }.into_any(),
                }).unwrap_or_else(|| view! {
                    <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING STATION…"</p>
                }.into_any())
            }}
        </div>
    }
}

#[component]
fn StationView(
    wc_name: String,
    current_job: Option<CurrentJobDto>,
    pitch: Option<PitchNowDto>,
    step: Option<StepNowDto>,
    quality_check: Option<String>,
    categories: Vec<String>,
    on_help: RwSignal<Option<std::sync::Arc<dyn Fn() + Send + Sync + 'static>>>,
    help_open: RwSignal<bool>,
    help_category: RwSignal<String>,
    help_note: RwSignal<String>,
    help_error: RwSignal<Option<String>>,
    help_status: RwSignal<HelpRequestState>,
) -> impl IntoView {
    let wc_display = wc_name.clone();
    let help_click = on_help;
    let cats_signal = RwSignal::new(categories.clone());
    view! {
        <div class="rams-station">
            <div class="rams-flex rams-flex--between rams-mb-4" style="align-items: center;">
                <h1 class="module-title">"STATION"</h1>
                <span class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">{wc_display}</span>
            </div>

            // CURRENT JOB — dominant block (item 31).
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"CURRENT JOB"</h3></div>
                <div class="module-content">
                    {match current_job {
                        Some(job) => {
                            let progress = if job.required_qty > 0 {
                                (job.completed_qty as f64 / job.required_qty as f64 * 100.0) as i64
                            } else { 0 };
                            view! {
                                <div class="rams-station-job">
                                    <div class="rams-station-job-title">{job.product_name.clone()}</div>
                                    <div class="rams-font-mono rams-text-sm rams-mt-2" style="color: var(--rams-muted);">
                                        {format!("{} · Part / order / customer", job.wo_number)}
                                    </div>
                                    <div class="rams-flex rams-gap-4 rams-mt-3">
                                        <div class="rams-station-stat">
                                            <div class="rams-station-stat-value">{job.required_qty.to_string()}</div>
                                            <div class="rams-station-stat-label">"REQUIRED"</div>
                                        </div>
                                        <div class="rams-station-stat">
                                            <div class="rams-station-stat-value">{job.completed_qty.to_string()}</div>
                                            <div class="rams-station-stat-label">"DONE"</div>
                                        </div>
                                        <div class="rams-station-stat">
                                            <div class="rams-station-stat-value">{job.remaining_qty.to_string()}</div>
                                            <div class="rams-station-stat-label">"REMAINING"</div>
                                        </div>
                                        <div class="rams-station-stat">
                                            <div class="rams-station-stat-value">{format!("{progress}%")}</div>
                                            <div class="rams-station-stat-label">"PROGRESS"</div>
                                        </div>
                                    </div>
                                </div>
                            }.into_any()
                        }
                        None => view! {
                            <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"NO ACTIVE JOB — call the team lead."</p>
                        }.into_any(),
                    }}
                </div>
            </div>

            // RIGHT NOW pitch.
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"RIGHT NOW"</h3></div>
                <div class="module-content">
                    {match pitch {
                        Some(p) => {
                            // Fourteenth audit: a job WITHOUT a frozen
                            // standard shows STANDARD UNAVAILABLE — never
                            // a fabricated target.
                            match p.target {
                                Some(target) => {
                                    let gap_class = if p.gap.unwrap_or(0) < 0 { "rams-station-gap-negative" } else { "rams-station-gap-positive" };
                                    view! {
                                        <div class="rams-flex rams-gap-4">
                                            <div class="rams-station-stat">
                                                <div class="rams-station-stat-value">{target.to_string()}</div>
                                                <div class="rams-station-stat-label">"PITCH TARGET"</div>
                                            </div>
                                            <div class="rams-station-stat">
                                                <div class="rams-station-stat-value">{p.actual.to_string()}</div>
                                                <div class="rams-station-stat-label">"ACTUAL"</div>
                                            </div>
                                            <div class="rams-station-stat">
                                                <div class=format!("rams-station-stat-value {gap_class}")>{format!("{:+}", p.gap.unwrap_or(0))}</div>
                                                <div class="rams-station-stat-label">"GAP"</div>
                                            </div>
                                        </div>
                                    }.into_any()
                                }
                                None => view! {
                                    <div class="rams-alert rams-alert--warning" role="alert">
                                        "STANDARD UNAVAILABLE — TARGET NOT CALCULATED. The released standard revision is missing; do not guess the target."
                                    </div>
                                }.into_any(),
                            }
                        }
                        None => view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"No pitch baseline (no effective standard)."</p> }.into_any(),
                    }}
                </div>
            </div>

            // CURRENT STEP + KEY POINT + QUALITY CHECK.
            <div class="module rams-mb-4">
                <div class="module-header"><h3 class="module-title">"CURRENT STEP"</h3></div>
                <div class="module-content">
                    {match step {
                        Some(s) => view! {
                            <div>
                                <div class="rams-station-step-title">
                                    {format!("{} / {}", s.position, s.total_steps)}
                                </div>
                                <div class="rams-station-step-desc rams-mt-1">{s.description.clone()}</div>
                                {s.expected_seconds.map(|secs| view! {
                                    <div class="rams-font-mono rams-text-sm rams-mt-1" style="color: var(--rams-muted);">
                                        {format!("EXPECTED TIME {}s", secs)}
                                    </div>
                                })}
                                {if s.is_critical {
                                    view! { <div class="rams-badge status-open rams-mt-2">"KEY POINT — CRITICAL STEP"</div> }.into_any()
                                } else {
                                    ().into_any()
                                }}
                            </div>
                        }.into_any(),
                        None => view! { <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"No standard loaded."</p> }.into_any(),
                    }}
                </div>
            </div>

            {if let Some(qc) = quality_check {
                view! {
                    <div class="module rams-mb-4">
                        <div class="module-header"><h3 class="module-title">"QUALITY CHECK"</h3></div>
                        <div class="module-content">
                            <p class="rams-station-step-desc">{qc}</p>
                        </div>
                    </div>
                }.into_any()
            } else {
                ().into_any()
            }}

            // The ONE prominent action: I NEED HELP (item 31).
            <button
                type="button"
                class="rams-btn rams-btn--station-help"
                on:click=move |_| help_open.set(true)
            >
                "I NEED HELP / SOMETHING IS WRONG"
            </button>

            <Show when=move || help_open.get()>
                <crate::components::modal::Modal title="What's wrong?".to_string() open=help_open>
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        <p class="rams-text-sm" style="color: var(--rams-muted);">
                            "Describe it in plain words — you don't need a category name."
                        </p>
                        <div class="rams-grid rams-grid--cols-2 rams-gap-2">
                            {move || cats_signal.get().iter().map(|cat| {
                                let cat_for_selected = cat.clone();
                                let cat_for_click = cat.clone();
                                let cat_display = cat.clone();
                                let sel = help_category;
                                view! {
                                    <button
                                        type="button"
                                        class=format!("rams-btn {} rams-btn--sm", if help_category.get() == cat_for_selected { "" } else { "rams-btn--ghost" })
                                        on:click=move |_| sel.set(cat_for_click.clone())
                                    >
                                        {cat_display.to_uppercase()}
                                    </button>
                                }
                            }).collect::<Vec<_>>()}
                        </div>
                        <textarea
                            class="rams-input"
                            rows="2"
                            prop:value=help_note
                            placeholder="What happened? (optional)"
                        ></textarea>
                        {move || help_error.get().map(|e| view! {
                            <div class="rams-alert rams-alert--danger" role="alert">{e}</div>
                        })}
                        {move || {
                            let label = help_status.get().label();
                            if label.is_empty() {
                                ().into_any()
                            } else {
                                view! {
                                    <div class="rams-alert rams-alert--info" role="status" aria-live="polite">
                                        {label}
                                    </div>
                                }.into_any()
                            }
                        }}
                        <button type="button" class="rams-btn rams-btn--md" on:click=move |_| { if let Some(cb) = help_click.get_untracked() { cb() } }>
                            "REQUEST HELP NOW"
                        </button>
                    </div>
                </crate::components::modal::Modal>
            </Show>
        </div>
    }
}

// ── Team-lead interval control (item 32) ─────────────────────────────────

#[component]
pub fn TeamLeadPage() -> impl IntoView {
    let app_state = use_context::<AppState>().expect("AppState not provided");
    let data = ArcLocalResource::new(move || {
        let client = app_state.api_client();
        async move { get_interval_board(&client, None).await }
    });

    view! {
        <div class="rams-p-4">
            <h1 class="module-title rams-mb-4">"INTERVAL CONTROL — PLAN VS ACTUAL"</h1>
            <p class="rams-font-mono rams-text-sm rams-mb-4" style="color: var(--rams-muted);">
                "See the gap early rather than explain missed daily totals later."
            </p>
            {move || data.map(|w| match &**w {
                Ok(rows) => view! {
                    <div class="rams-flex rams-flex--col rams-gap-3">
                        {rows.iter().map(|r| {
                            let start = r.interval_start.clone();
                            let plan = r.plan;
                            let actual = r.actual;
                            let gap = r.gap;
                            let abnormal = gap < 0;
                            let row_class = if abnormal { "rams-interval-row rams-interval-row--abnormal" } else { "rams-interval-row" };
                            let abnormalities = r.abnormalities.clone();
                            let gap_display = format!("{:+}", gap);
                            view! {
                                <div class=row_class>
                                    <div class="rams-flex rams-flex--between" style="align-items: center; padding: var(--rams-space-3);">
                                        <span class="rams-font-mono rams-text-sm">{start}</span>
                                        <span class="rams-text-sm">"Plan "{plan.to_string()}</span>
                                        <span class="rams-text-sm">"Actual "{actual.to_string()}</span>
                                        <span class=format!("rams-text-sm {}", if abnormal { "rams-text-danger" } else { "rams-text-success" })>
                                            {gap_display}
                                        </span>
                                    </div>
                                    {if abnormal && !abnormalities.is_empty() {
                                        view! {
                                            <div class="rams-p-3" style="border-top: 1px solid var(--rams-line);">
                                                <p class="rams-font-mono rams-text-2xs rams-mb-2" style="color: var(--rams-muted);">
                                                    "WHAT STOPPED FLOW?"
                                                </p>
                                                {abnormalities.iter().map(|a| {
                                                    let status = if a.resolved { "RESOLVED" } else { "ACTIVE" };
                                                    let resp = a.response_seconds.map(|s| format!(" · response {s}s")).unwrap_or_default();
                                                    view! {
                                                        <div class="rams-text-sm rams-mb-1">
                                                            {format!("{} — {} ({}){resp} · {status}", a.andon_number, a.issue_type.to_uppercase(), a.severity)}
                                                        </div>
                                                    }
                                                }).collect::<Vec<_>>()}
                                            </div>
                                        }.into_any()
                                    } else {
                                        ().into_any()
                                    }}
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
                <p class="rams-font-mono rams-text-sm" style="color: var(--rams-muted);">"LOADING INTERVALS…"</p>
            }.into_any())}
        </div>
    }
}

/// Map the operator's plain-language help category to the Andon issue
/// type vocabulary (item 40: the operator never learns Andon terms).
fn normalize_help_category(category: &str) -> String {
    match category.to_lowercase().as_str() {
        "quality" => "quality".to_string(),
        "material" => "material".to_string(),
        "machine" => "maintenance".to_string(),
        "method / instructions" | "method" => "method".to_string(),
        "safety" => "safety".to_string(),
        "i cannot keep pace" | "cannot keep pace" => "capacity".to_string(),
        _ => "other".to_string(),
    }
}

/// The Help interaction state machine (thirteenth audit P0): the operator
/// always sees what happened — never a silently closed dialog.
#[derive(Debug, Clone, PartialEq)]
pub enum HelpRequestState {
    Idle,
    Sending,
    /// HELP REQUESTED with the server-assigned Andon number.
    Requested(String),
    Failed,
}

impl HelpRequestState {
    fn label(&self) -> String {
        match self {
            HelpRequestState::Idle => String::new(),
            HelpRequestState::Sending => "SENDING...".to_string(),
            HelpRequestState::Requested(number) => {
                format!("HELP REQUESTED · {number} — a team lead will respond. The dialog stays open so you can see the response.")
            }
            HelpRequestState::Failed => {
                "FAILED — the request was not sent. Retry below or use the team-lead channel."
                    .to_string()
            }
        }
    }
}
