//! Industrial-style progress indicator component.
//!
//! Provides [`ProgressBar`] — a horizontal progress bar following the Rams design
//! system. Uses border-based styling (no rounded corners > 2px, no shadows).

use leptos::prelude::*;

/// Industrial-style horizontal progress bar.
///
/// Renders a track with a filled segment. The fill color transitions from
/// Rams success (green) through warning (orange) to danger (red) based on value.
///
/// # Example
///
/// ```ignore
/// <ProgressBar value=75.0 label="Completion" show_value=true />
/// ```
#[component]
pub fn ProgressBar(
    /// Progress value from 0.0 to 100.0.
    #[prop(into)]
    value: f64,
    /// Optional descriptive label (displayed uppercase above the bar).
    #[prop(optional)]
    label: Option<String>,
    /// Whether to show the numeric percentage value.
    #[prop(optional)]
    show_value: bool,
) -> impl IntoView {
    let clamped_value = value.clamp(0.0, 100.0);
    let fill_color = move || {
        if clamped_value >= 80.0 {
            "var(--rams-red)"
        } else if clamped_value >= 50.0 {
            "var(--rams-orange)"
        } else {
            "var(--rams-green)"
        }
    };
    let display_value = format!("{:.0}%", clamped_value);

    view! {
        <div class="rams-input-wrapper">
            {label.as_ref().map(|l| {
                let label_upper = l.to_uppercase();
                view! {
                    <div class="rams-flex rams-flex--between rams-flex--center">
                        <span class="rams-label">{label_upper}</span>
                        {if show_value {
                            view! {
                                <span
                                    class="rams-label"
                                    style="color: var(--rams-foreground); letter-spacing: normal; text-transform: none;"
                                >
                                    {display_value.clone()}
                                </span>
                            }.into_any()
                        } else {
                            ().into_any()
                        }}
                    </div>
                }
            })}
            <div
                role="progressbar"
                aria-valuenow=clamped_value as u32
                aria-valuemin="0"
                aria-valuemax="100"
                aria-label=label.clone().unwrap_or_default()
                style=format!(
                    "width: 100%; height: 8px; \
                     background-color: var(--rams-panel); \
                     border: 1px solid var(--rams-line); \
                     border-radius: var(--rams-radius-sm); \
                     overflow: hidden;"
                )
            >
                <div
                    style=move || format!(
                        "width: {:.1}%; height: 100%; \
                         background-color: {}; \
                         transition: width var(--rams-normal), background-color var(--rams-normal);",
                        clamped_value, fill_color()
                    )
                ></div>
            </div>
            {if label.is_none() && show_value {
                view! {
                    <span class="rams-label" style="color: var(--rams-foreground); letter-spacing: normal; text-transform: none; margin-top: 2px;">
                        {display_value}
                    </span>
                }.into_any()
            } else {
                ().into_any()
            }}
        </div>
    }
}
