//! Inline TPS coaching (item 68): the AI appears BESIDE the problem, not
//! as a chatbot destination. A small prompt next to a form asks the
//! observation-first question (expected vs actual) — the person learns the
//! reasoning sequence by doing, never by reading a lecture.
//!
//! The prompts are deterministic and contextual — they are the
//! Expected → Actual → Gap → Response sequence made visible at the
//! decision point.

use leptos::prelude::*;

/// A contextual coaching prompt attached to a form.
#[component]
pub fn InlineCoach(
    /// The question to ask (observation-first, never prescriptive).
    question: String,
    /// The reasoning step this prompt belongs to.
    #[prop(optional)]
    step: String,
) -> impl IntoView {
    view! {
        <div class="rams-coach" role="note">
            <div class="rams-coach-step rams-font-mono rams-text-2xs" style="color: var(--rams-muted);">
                {step}
            </div>
            <p class="rams-text-sm" style="color: var(--rams-foreground);">
                {question}
            </p>
        </div>
    }
}
