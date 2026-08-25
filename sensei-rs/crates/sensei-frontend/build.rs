//! # I18n Code Generator
//!
//! This build script reads JSON locale files from `locales/` and generates
//! Rust source code with:
//!
//! - `src/generated/i18n_keys.rs` — An `I18nKey` enum with one variant per
//!   translation key, along with helpers to convert to/from dot-notation
//!   strings, display, and iterate all keys.
//!
//! - `src/generated/i18n_translations.rs` — A `Translations` struct and a
//!   `load_translations()` function that returns all locale data as a
//!   `HashMap<&'static str, HashMap<&'static str, &'static str>>`
//!   (locale → key → translated value).
//!
//! Nested JSON keys are flattened to dot notation (e.g. `common.save`).
//! The generator verifies that all locale files contain the same set of keys
//! and emits `cargo:warning` messages for any discrepancies.
//!
//! If two different keys would produce the same PascalCase variant name
//! (e.g. `pages.sales.status.new` and `pages.sales.statusNew` both map to
//! `PagesSalesStatusNew`), the second and subsequent duplicates get a
//! numeric suffix like `_2`, `_3`, etc.

use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::io;
use std::path::Path;

/// Directory containing locale JSON files (relative to crate root).
const LOCALES_DIR: &str = "locales";

/// Output directory for generated code (relative to crate root).
const OUT_DIR: &str = "src/generated";

/// A flattened key–value pair for a single locale.
type FlatLocale = BTreeMap<String, String>;

/// All parsed locales, keyed by locale code.
type AllLocales = BTreeMap<String, FlatLocale>;

fn main() -> io::Result<()> {
    println!("cargo:rerun-if-changed={LOCALES_DIR}/");

    let crate_dir = std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR not set");
    let locales_dir = Path::new(&crate_dir).join(LOCALES_DIR);
    let out_dir = Path::new(&crate_dir).join(OUT_DIR);

    // Ensure output directory exists
    fs::create_dir_all(&out_dir)?;

    // ── 1. Read and flatten all locale files ──────────────────────────
    let mut all_locales: AllLocales = BTreeMap::new();
    let mut all_keys: BTreeSet<String> = BTreeSet::new();

    let entries = fs::read_dir(&locales_dir)?;
    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "json") {
            continue;
        }
        let locale_code = path
            .file_stem()
            .and_then(|s| s.to_str())
            .expect("valid locale filename")
            .to_string();

        let content = fs::read_to_string(&path)?;
        let json: Value = serde_json::from_str(&content)
            .unwrap_or_else(|e| panic!("Failed to parse {}: {e}", path.display()));

        let flat = flatten_json(&json, "");
        let keys: BTreeSet<String> = flat.keys().cloned().collect();
        all_keys.extend(keys.clone());
        all_locales.insert(locale_code, flat);
    }

    if all_locales.is_empty() {
        panic!("No locale JSON files found in {LOCALES_DIR}/");
    }

    // ── 2. Validate all locales have the same keys ────────────────────
    let locale_codes: Vec<&str> = all_locales.keys().map(|s| s.as_str()).collect();
    let reference = &locale_codes[0];

    for code in &locale_codes[1..] {
        let ref_keys: BTreeSet<String> = all_locales[*reference].keys().cloned().collect();
        let loc_keys: BTreeSet<String> = all_locales[*code].keys().cloned().collect();

        let missing: Vec<&str> = ref_keys.difference(&loc_keys).map(|s| s.as_str()).collect();
        let extra: Vec<&str> = loc_keys.difference(&ref_keys).map(|s| s.as_str()).collect();

        if !missing.is_empty() {
            println!(
                "cargo:warning=Locale '{code}' is missing {} keys (vs '{reference}'): {:?}",
                missing.len(),
                &missing[..missing.len().min(10)]
            );
        }
        if !extra.is_empty() {
            println!(
                "cargo:warning=Locale '{code}' has {} extra keys (vs '{reference}'): {:?}",
                extra.len(),
                &extra[..extra.len().min(10)]
            );
        }
    }

    // ── 3. Sort keys deterministically ────────────────────────────────
    let sorted_keys: Vec<&str> = all_keys.iter().map(|s| s.as_str()).collect();

    // ── 4. Build variant name mapping with disambiguation ─────────────
    let variant_map = build_variant_map(&sorted_keys);

    // ── 5. Generate i18n_keys.rs ──────────────────────────────────────
    let keys_rs = generate_keys_module(&sorted_keys, &variant_map);
    fs::write(out_dir.join("i18n_keys.rs"), &keys_rs)?;

    // ── 6. Generate i18n_translations.rs ──────────────────────────────
    let locale_codes_sorted: Vec<&str> = all_locales.keys().map(|s| s.as_str()).collect();
    let trans_rs = generate_translations_module(
        &sorted_keys,
        &variant_map,
        &all_locales,
        &locale_codes_sorted,
    );
    fs::write(out_dir.join("i18n_translations.rs"), &trans_rs)?;

    // ── 7. Generate mod.rs ────────────────────────────────────────────
    let mod_rs = "pub mod i18n_keys;\npub mod i18n_translations;\n";
    fs::write(out_dir.join("mod.rs"), mod_rs)?;

    Ok(())
}

/// Recursively flatten a JSON value into dot-notation key–value pairs.
///
/// Only string leaf values are included. Nested objects produce dotted keys.
fn flatten_json(value: &Value, prefix: &str) -> FlatLocale {
    let mut result = FlatLocale::new();
    match value {
        Value::Object(map) => {
            for (k, v) in map {
                let key = if prefix.is_empty() {
                    k.clone()
                } else {
                    format!("{prefix}.{k}")
                };
                result.extend(flatten_json(v, &key));
            }
        }
        Value::String(s) => {
            result.insert(prefix.to_string(), s.clone());
        }
        // Skip numbers, booleans, null, arrays — only string values are
        // translatable.
        _ => {}
    }
    result
}

/// Convert a dot-notation i18n key into a valid PascalCase Rust identifier.
///
/// Each dot-separated segment is further split on underscores, and each
/// sub-segment is capitalized. Leading underscores in segments are stripped.
/// Digits are preserved as-is (valid after the first character).
///
/// Examples:
/// - `"meta.locale"` → `"MetaLocale"`
/// - `"common.save"` → `"CommonSave"`
/// - `"common.actions._value"` → `"CommonActionsValue"`
/// - `"a3.stats.emailDrafting.status.approved"` → `"A3StatsEmailDraftingStatusApproved"`
/// - `"maintenance.workOrders.title_field"` → `"MaintenanceWorkOrdersTitleField"`
/// - `"pages.analytics.periods._24h"` → `"PagesAnalyticsPeriods24h"`
fn key_to_variant(key: &str) -> String {
    let mut result = String::with_capacity(key.len());
    for segment in key.split('.') {
        // Split segment on underscores to get proper PascalCase sub-segments
        for sub_segment in segment.split('_') {
            let trimmed = sub_segment.trim_start_matches('_');
            if trimmed.is_empty() {
                continue;
            }
            // Capitalize first char, preserving digits
            for (i, ch) in trimmed.chars().enumerate() {
                if i == 0 {
                    if ch.is_ascii_digit() {
                        // Digits are fine mid-name in Rust identifiers
                        result.push(ch);
                    } else {
                        result.extend(ch.to_uppercase());
                    }
                } else {
                    result.push(ch);
                }
            }
        }
    }
    // If the variant would start with a digit (edge case), prefix with '_'
    if result.starts_with(|c: char| c.is_ascii_digit()) {
        result.insert(0, '_');
    }
    // If the variant would be a Rust reserved word, add trailing underscore
    let reserved = ["Self", "Super", "Crate", "True", "False"];
    if reserved.contains(&result.as_str()) {
        result.push('_');
    }
    result
}

/// Build a mapping from key → (variant_name, is_unique).
///
/// If multiple keys produce the same variant name, the second and subsequent
/// ones get a `_2`, `_3`, … suffix (deterministic, based on sort order).
fn build_variant_map(sorted_keys: &[&str]) -> Vec<(String, bool /* is_duplicate */)> {
    // First pass: count occurrences of each variant name
    let mut counts: HashMap<&str, u32> = HashMap::new();
    // We need to store the variant strings
    let variants: Vec<String> = sorted_keys.iter().map(|k| key_to_variant(k)).collect();

    for v in &variants {
        *counts.entry(v.as_str()).or_insert(0) += 1u32;
    }

    // Second pass: assign disambiguated names
    let mut seen: HashMap<&str, u32> = HashMap::new();
    let mut result: Vec<(String, bool)> = Vec::with_capacity(sorted_keys.len());

    for (i, _key) in sorted_keys.iter().enumerate() {
        let base = &variants[i];
        let total = counts[base.as_str()];

        if total == 1 {
            // Unique — use as-is
            result.push((base.clone(), false));
        } else {
            let counter = seen.entry(base.as_str()).or_insert(0u32);
            *counter += 1;
            let is_first = *counter == 1;
            if is_first {
                // First occurrence keeps the base name
                result.push((base.clone(), true));
            } else {
                // Subsequent occurrences get a numeric suffix that keeps the
                // identifier camel-cased (e.g. `...High2` — never `...High_2`).
                let disambiguated = format!("{}{}", base, counter);
                result.push((disambiguated, true));
            }
        }
    }

    result
}

/// Generate the `i18n_keys.rs` module source code.
fn generate_keys_module(sorted_keys: &[&str], variant_map: &[(String, bool)]) -> String {
    let mut out = String::new();

    out.push_str(
        "//! Auto-generated i18n key enum.\n\
         //! Run `cargo build` in the sensei-frontend crate to regenerate.\n\n\
         use std::fmt;\n\n",
    );

    // ── I18nKey enum ──────────────────────────────────────────────
    out.push_str("/// Typed i18n translation key.\n");
    out.push_str("///\n");
    out.push_str("/// Each variant corresponds to exactly one dot-notation key\n");
    out.push_str("/// from the locale JSON files.\n");
    out.push_str("#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]\n");
    out.push_str("pub enum I18nKey {\n");

    for (i, key) in sorted_keys.iter().enumerate() {
        let variant = &variant_map[i].0;
        out.push_str(&format!("    /// `{key}`\n"));
        out.push_str(&format!("    {variant},\n"));
    }

    out.push_str("}\n\n");

    // ── impl I18nKey ──────────────────────────────────────────────
    out.push_str("impl I18nKey {\n");
    out.push_str("    /// Return the dot-notation key string.\n");
    out.push_str("    pub fn key(&self) -> &'static str {\n");
    out.push_str("        match self {\n");

    for (i, key) in sorted_keys.iter().enumerate() {
        let variant = &variant_map[i].0;
        out.push_str(&format!("            I18nKey::{variant} => \"{key}\",\n"));
    }

    out.push_str("        }\n");
    out.push_str("    }\n");
    out.push_str("}\n\n");

    // ── Display ───────────────────────────────────────────────────
    out.push_str("impl fmt::Display for I18nKey {\n");
    out.push_str("    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {\n");
    out.push_str("        write!(f, \"{}\", self.key())\n");
    out.push_str("    }\n");
    out.push_str("}\n\n");

    // ── all_keys ──────────────────────────────────────────────────
    out.push_str("/// Return a slice of every known [`I18nKey`].\n");
    out.push_str("pub fn all_keys() -> &'static [I18nKey] {\n");
    out.push_str("    &[\n");

    for (i, _key) in sorted_keys.iter().enumerate() {
        let variant = &variant_map[i].0;
        out.push_str(&format!("        I18nKey::{variant},\n"));
    }

    out.push_str("    ]\n");
    out.push_str("}\n");

    out
}

/// Escape a Rust string literal, handling quotes, backslashes, and
/// non-ASCII characters.
fn escape_rust_string(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 8);
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_ascii_graphic() || c == ' ' => out.push(c),
            // For non-ASCII (Unicode), emit them directly — Rust supports
            // UTF-8 source files and string literals.
            c => out.push(c),
        }
    }
    out
}

/// Generate the `i18n_translations.rs` module source code.
fn generate_translations_module(
    sorted_keys: &[&str],
    _variant_map: &[(String, bool)],
    all_locales: &AllLocales,
    locale_codes: &[&str],
) -> String {
    let mut out = String::new();

    out.push_str(
        "//! Auto-generated translation data.\n\
         //! Run `cargo build` in the sensei-frontend crate to regenerate.\n\n\
         use std::collections::HashMap;\n\n",
    );

    // ── Translations struct ───────────────────────────────────────
    out.push_str(
        "/// Holds all translations for all locales.\n\
         ///\n\
         /// The inner map is keyed by dot-notation key; the outer map is\n\
         /// keyed by locale code (e.g. `\"en\"`, `\"fr\"`).\n",
    );
    out.push_str("#[derive(Debug, Clone)]\n");
    out.push_str("pub struct Translations {\n");
    out.push_str("    pub data: HashMap<&'static str, HashMap<&'static str, &'static str>>,\n");
    out.push_str("}\n\n");

    // ── load_translations ─────────────────────────────────────────
    out.push_str(
        "/// Load all translations into a [`Translations`] instance.\n\
         ///\n\
         /// This function is called once at application startup and the\n\
         /// result is cached for the lifetime of the app.\n",
    );
    out.push_str("pub fn load_translations() -> Translations {\n");
    out.push_str("    let mut data: HashMap<&'static str, HashMap<&'static str, &'static str>> = HashMap::new();\n\n");

    // Generate a static map per locale
    for locale in locale_codes {
        let locale_data = &all_locales[*locale];
        let map_name = format!("{}_MAP", locale.to_uppercase());

        // Build a static array of (key, value) pairs for this locale
        out.push_str(&format!(
            "    // ── {} translations ──────────────────────────────────\n",
            locale
        ));
        out.push_str(&format!("    static {}: &[(&str, &str)] = &[\n", map_name));

        for key in sorted_keys {
            let value = locale_data.get(*key).map(|s| s.as_str()).unwrap_or("");
            let escaped = escape_rust_string(value);
            out.push_str(&format!("        (\"{key}\", \"{escaped}\"),\n"));
        }

        out.push_str("    ];\n\n");

        // Insert into the HashMap
        out.push_str(&format!(
            "    data.insert(\"{locale}\", {}.iter().map(|&(k, v)| (k, v)).collect());\n\n",
            map_name
        ));
    }

    out.push_str("    Translations { data }\n");
    out.push_str("}\n");

    out
}
