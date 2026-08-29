//! Industrial button component following the Rams design system.
//!
//! Provides [`IndustrialButton`] with semantic variants (Default, Primary, Danger, Ghost)
//! and three sizes (Sm, Md, Lg). All visual styling is driven by CSS classes defined
//! in [`styles/rams.css`](../../styles/rams.css).

use leptos::prelude::*;

/// Semantic variant for an [`IndustrialButton`].
#[derive(Debug, Clone, Default)]
pub enum ButtonVariant {
    /// Neutral chassis — no special emphasis (default).
    #[default]
    Default,
    /// Orange action — primary call-to-action.
    Primary,
    /// Red destructive — irreversible actions.
    Danger,
    /// Transparent — minimal visual weight.
    Ghost,
}

/// Size preset for an [`IndustrialButton`].
#[derive(Debug, Clone, Default)]
pub enum ButtonSize {
    /// Small — 28px height.
    Sm,
    /// Medium — 36px height (default).
    #[default]
    Md,
    /// Large — 44px height.
    Lg,
}

/// Reusable industrial-styled button.
///
/// Maps to `rams-btn` CSS classes. Use [`ButtonVariant`] for semantics and
/// [`ButtonSize`] for sizing.
///
/// # Example
///
/// ```ignore
/// <IndustrialButton variant=ButtonVariant::Primary on_click=Some(Box::new(|| log::info!("Clicked"))))>
///     "SUBMIT"
/// </IndustrialButton>
/// ```
#[component]
pub fn IndustrialButton(
    /// Semantic variant (default: [`ButtonVariant::Default`]).
    #[prop(optional)]
    variant: ButtonVariant,
    /// Size preset (default: [`ButtonSize::Md`]).
    #[prop(optional)]
    size: ButtonSize,
    /// Whether the button is disabled.
    #[prop(optional)]
    disabled: bool,
    /// Additional CSS classes to append.
    #[prop(optional)]
    class: String,
    /// Accessible label for screen readers (overrides children text).
    #[prop(optional)]
    aria_label: Option<String>,
    /// Button label content.
    children: Children,
    /// Optional click handler.
    #[prop(optional)]
    on_click: Option<Box<dyn Fn() + 'static>>,
) -> impl IntoView {
    let variant_class = match variant {
        ButtonVariant::Default => "rams-btn--default",
        ButtonVariant::Primary => "rams-btn--primary",
        ButtonVariant::Danger => "rams-btn--danger",
        ButtonVariant::Ghost => "rams-btn--ghost",
    };
    let size_class = match size {
        ButtonSize::Sm => "rams-btn--sm",
        ButtonSize::Md => "rams-btn--md",
        ButtonSize::Lg => "rams-btn--lg",
    };

    // Item 53: an empty explicit aria-label can ERASE the visible child
    // text as the accessible name — when no override is provided the
    // attribute is NOT rendered at all (None), so the visible text remains
    // the accessible name.
    let aria = aria_label.clone();
    view! {
        <button
            type="button"
            class=format!("rams-btn {} {} {}", variant_class, size_class, class)
            disabled=disabled
            attr:aria-label=aria
            on:click=move |_| { if let Some(ref cb) = on_click { cb() } }
        >
            {children()}
        </button>
    }
}
