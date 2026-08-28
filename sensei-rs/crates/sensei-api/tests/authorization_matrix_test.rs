//! Executable route-authorization matrix (structural invariant).
//!
//! Every business handler in the route modules must carry a declared
//! authorization requirement: a `require_permission(...)` call, a custom
//! role/self-service guard, or an explicit entry in the allowlists below.
//! Authentication is not authorization — this test makes it impossible to
//! register a protected business route without an authorization policy.

use std::collections::HashSet;

/// Routes that are PUBLIC by design (no authentication required).
const PUBLIC_HANDLERS: &[&str] = &[
    "login",
    "refresh",
    "register",
    "liveness",
    "readiness",
    "detailed",
    "metrics_handler",
    "ws_handler",
    "sse_handler",
    "realtime_ticket_handler",
];

/// Authenticated user self-service / read-only surfaces where authentication
/// plus tenant scope IS the intended authorization (the user acting on
/// their own account/data).
const SELF_SERVICE_HANDLERS: &[&str] = &[
    "logout",
    "get_me",
    "update_me",
    "change_password",
    "request_password_reset",
    "confirm_password_reset",
    "request_email_verification",
    "confirm_email_verification",
    "list_notifications",
    "unread_count",
    "mark_notification_read",
    "mark_all_read",
    "get_preferences",
    "update_preferences",
    "list_saved_views",
    "create_saved_view",
    "get_saved_view",
    "update_saved_view",
    "delete_saved_view",
    "share_saved_view",
    "search",
    "get_today_snapshot",
];

fn handler_has_guard(body: &str) -> bool {
    body.contains("require_permission")
        || body.contains("has_any_role")
        || body.contains("has_role(")
        || body.contains("require_admin")
        || body.contains("is_self(")
        || body.contains("if user.user_id == ")
        || body.contains("user.user_id != ")
        || body.contains("== user.user_id")
}

#[test]
fn every_business_handler_declares_authorization() {
    let public: HashSet<&str> = PUBLIC_HANDLERS.iter().copied().collect();
    let self_service: HashSet<&str> = SELF_SERVICE_HANDLERS.iter().copied().collect();

    let routes_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/routes");
    let handler_re = regex::Regex::new(r"pub async fn (\w+)\(").unwrap();
    let mut uncovered: Vec<String> = Vec::new();

    let mut entries: Vec<_> = std::fs::read_dir(&routes_dir)
        .expect("routes dir")
        .filter_map(|e| e.ok())
        .collect();
    entries.sort_by_key(|e| e.file_name());

    for entry in entries {
        let fname = entry.file_name().to_string_lossy().to_string();
        if !fname.ends_with(".rs") {
            continue;
        }
        let src = std::fs::read_to_string(entry.path()).unwrap_or_default();
        for m in handler_re.find_iter(&src) {
            let name = m
                .as_str()
                .trim_start_matches("pub async fn ")
                .trim_end_matches('(')
                .to_string();
            let start = m.start();
            let end = (start + 900).min(src.len());
            // Trim to a char boundary so slicing never panics on multi-byte
            // characters (route files contain box-drawing comments).
            let mut end = end;
            while end > start && !src.is_char_boundary(end) {
                end -= 1;
            }
            let body = &src[start..end];
            // Only real handlers (have a State or HeaderMap extractor).
            if !body.contains("State(") && !body.contains("HeaderMap") {
                continue;
            }
            if public.contains(name.as_str()) || self_service.contains(name.as_str()) {
                continue;
            }
            if !handler_has_guard(body) {
                uncovered.push(format!("{fname}: {name}"));
            }
        }
    }

    assert!(
        uncovered.is_empty(),
        "Handlers without declared authorization ({}):\n{}",
        uncovered.len(),
        uncovered.join("\n")
    );
}
