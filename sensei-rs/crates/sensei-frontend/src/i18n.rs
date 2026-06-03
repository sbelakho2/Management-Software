//! I18n system with reactive locale switching backed by generated data.
//!
//! Translations are loaded at startup from the generated
//! [`i18n_translations`](crate::generated::i18n_translations) module, which is
//! produced by the `build.rs` code generator from JSON locale files.
//!
//! Provides a reactive [`I18nContext`] that can be provided at the app root
//! and consumed anywhere via [`use_i18n`].
//!
//! # Usage
//! ```ignore
//! provide_i18n();
//! let i18n = use_i18n();
//! let label = i18n.t(I18nKey::CommonSave);
//! let greeting = i18n.t_with_args(I18nKey::LoginWelcomeBack, &[("name", "John")]);
//! ```

use crate::generated::i18n_keys::I18nKey;
use crate::generated::i18n_translations;
use leptos::prelude::*;
use once_cell::sync::Lazy;
use std::collections::HashMap;

/// Global translation data loaded once at runtime.
static TRANSLATIONS: Lazy<HashMap<String, HashMap<String, String>>> = Lazy::new(|| {
    let t = i18n_translations::load_translations();
    t.data
        .into_iter()
        .map(|(locale, map)| {
            (
                locale.to_string(),
                map.into_iter()
                    .map(|(k, v)| (k.to_string(), v.to_string()))
                    .collect(),
            )
        })
        .collect()
});

/// Reactive i18n context providing locale switching and translation lookups.
#[derive(Clone)]
pub struct I18nContext {
    /// The current locale code (e.g. `"en"`, `"fr"`, `"ar"`).
    pub locale: RwSignal<String>,
    /// The loaded message map for the current locale.
    pub messages: RwSignal<HashMap<String, String>>,
    /// Derived text direction: `"ltr"` or `"rtl"`.
    pub direction: Memo<String>,
}

impl I18nContext {
    /// Create a new `I18nContext` with the default locale (`"en"`).
    pub fn new() -> Self {
        let locale = RwSignal::new("en".to_string());
        let locale_clone = locale;
        let messages = RwSignal::new(load_locale("en"));
        let direction = Memo::new(move |_| match locale_clone.get().as_str() {
            "ar" => "rtl".to_string(),
            _ => "ltr".to_string(),
        });

        Self {
            locale,
            messages,
            direction,
        }
    }

    /// Switch the active locale and reload messages.
    pub fn set_locale(&self, locale: &str) {
        let locale_str = if TRANSLATIONS.contains_key(locale) {
            locale.to_string()
        } else {
            "en".to_string()
        };
        self.locale.set(locale_str.clone());
        self.messages.set(load_locale(&locale_str));
    }

    /// Translate an [`I18nKey`] for the current locale.
    ///
    /// Returns the key's dot-notation string as a fallback if no translation
    /// is found (fail-safe).
    pub fn t(&self, key: I18nKey) -> String {
        self.messages
            .get()
            .get(key.key())
            .cloned()
            .unwrap_or_else(|| key.to_string())
    }

    /// Translate an [`I18nKey`] with positional argument substitution.
    ///
    /// Use `{0}`, `{1}`, or named placeholders like `{name}` in the
    /// translation values.
    /// `args` is a slice of `(placeholder, value)` pairs.
    pub fn t_with_args(&self, key: I18nKey, args: &[(&str, &str)]) -> String {
        let mut msg = self.t(key);
        for (placeholder, value) in args {
            msg = msg.replace(&format!("{{{}}}", placeholder), value);
        }
        msg
    }
}

impl Default for I18nContext {
    fn default() -> Self {
        Self::new()
    }
}

/// Provide the [`I18nContext`] as a reactive context (call once at app root).
pub fn provide_i18n() -> I18nContext {
    let ctx = I18nContext::new();
    provide_context(ctx.clone());
    ctx
}

/// Access the [`I18nContext`] from anywhere in the component tree.
///
/// # Panics
/// Panics if no `I18nContext` has been provided via [`provide_i18n`].
pub fn use_i18n() -> I18nContext {
    expect_context::<I18nContext>()
}

// ---------------------------------------------------------------------------
// Locale data loader
// ---------------------------------------------------------------------------

fn load_locale(locale: &str) -> HashMap<String, String> {
    TRANSLATIONS
        .get(locale)
        .cloned()
        .unwrap_or_else(|| TRANSLATIONS.get("en").cloned().unwrap_or_default())
}

// ---------------------------------------------------------------------------
// Convenience re-exports
// ---------------------------------------------------------------------------

pub use crate::generated::i18n_keys::all_keys;
