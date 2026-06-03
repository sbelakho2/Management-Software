//! Metric display component.
//!
//! A read-only industrial instrument readout showing a single KPI value with
//! optional unit, label, and trend indicator. See [`styles/rams.css`](../../styles/rams.css)
//! section 3.6.

use leptos::prelude::*;

/// Industrial metric readout — displays a single KPI value.
///
/// Designed for dashboard metric grids and instrument panels. The value is
/// prominently displayed, with the unit and label below it in decreasing
/// visual weight.
///
/// # Example
///
/// ```ignore
/// <MetricDisplay value="98.2" unit="%" label="OEE" trend="+1.2%" />
/// ```
#[component]
pub fn MetricDisplay(
    /// The numeric (or text) value to display prominently.
    value: String,
    /// Short label describing the metric.
    label: String,
    /// Optional unit suffix (e.g. "%", "pcs", "hrs").
    #[prop(optional)]
    unit: String,
    /// Optional trend indicator text (e.g. "+2.1%", "▼ 0.5").
    #[prop(optional)]
    trend: Option<String>,
    /// Additional CSS classes to append.
    #[prop(optional)]
    class: String,
) -> impl IntoView {
    let aria_text = format!("{}: {}", label, value);

    view! {
        <div class=format!("metric-display {}", class) aria-label=aria_text>
            <div class="metric-display-value" data-numeric="">{value}</div>
            {if !unit.is_empty() {
                view! { <span class="metric-display-unit">{unit}</span> }.into_any()
            } else {
                ().into_any()
            }}
            <div class="metric-display-label">{label}</div>
            {trend.map(|t| {
                view! { <div class="metric-display-trend">{t}</div> }
            })}
        </div>
    }
}
