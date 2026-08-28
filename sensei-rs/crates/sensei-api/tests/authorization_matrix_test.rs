//! Executable route-authorization matrix (structural invariant).
//!
//! Every business handler in the route modules must carry a declared
//! authorization requirement: a `require_permission(...)` call, a custom
//! role/self-service guard, or an explicit entry in the allowlists below.
//! Authentication is not authorization — this test makes it impossible to
//! register a protected business route without an authorization policy.
//!
//! The scan is AST-based (syn): each `pub async fn` is parsed INDIVIDUALLY
//! and only statements INSIDE that function's body count as its guard. A
//! short unprotected function can no longer inherit the next function's
//! permission call (the previous 900-byte substring window was unsound).

use std::collections::HashSet;

use quote::ToTokens;
use syn::visit::Visit;

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

/// AST visitor: does THIS function's own body call any authorization guard?
struct GuardVisitor {
    found: bool,
}

impl<'ast> Visit<'ast> for GuardVisitor {
    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if let syn::Expr::Path(path) = node.func.as_ref() {
            if let Some(last) = path.path.segments.last() {
                let name = last.ident.to_string();
                if matches!(
                    name.as_str(),
                    "require_permission"
                        | "require_permissions"
                        | "has_any_role"
                        | "has_role"
                        | "require_admin"
                        | "require_platform_superadmin"
                        | "is_self"
                        | "ensure_self"
                ) {
                    self.found = true;
                }
            }
        }
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        // `user.require_permission(...)` — the overwhelmingly common guard.
        let method = node.method.to_string();
        if matches!(
            method.as_str(),
            "require_permission"
                | "require_permissions"
                | "has_any_role"
                | "has_role"
                | "require_admin"
                | "require_platform_superadmin"
                | "is_self"
                | "ensure_self"
        ) {
            self.found = true;
        }
        syn::visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_binary(&mut self, node: &'ast syn::ExprBinary) {
        // Direct user-id comparisons (self-service guards) count only when
        // they reference the authenticated principal: `user.user_id == x`.
        if matches!(node.op, syn::BinOp::Eq(_) | syn::BinOp::Ne(_)) {
            let left = quote_expr(&node.left);
            let right = quote_expr(&node.right);
            if left.contains("user.user_id") || right.contains("user.user_id") {
                self.found = true;
            }
        }
        syn::visit::visit_expr_binary(self, node);
    }
}

fn quote_expr(e: &syn::Expr) -> String {
    e.to_token_stream().to_string()
}

/// Whether the function signature carries an Axum extractor that implies a
/// business handler (State or HeaderMap). Pure helpers (no extractors) are
/// not routes and are skipped.
fn is_business_handler(f: &syn::ItemFn) -> bool {
    if f.sig.asyncness.is_none() {
        return false;
    }
    if !matches!(f.vis, syn::Visibility::Public(_)) {
        return false;
    }
    // A business handler has an Axum extractor argument: a parameter whose
    // TYPE is `State<...>` or `HeaderMap`. `build_context(&user, &state)`
    // helpers reference the AppState type but never extract it.
    let has_state = f.sig.inputs.iter().any(|arg| {
        let syn::FnArg::Typed(pat) = arg else {
            return false;
        };
        let ty_text = pat.ty.to_token_stream().to_string();
        ty_text.starts_with("State <") || ty_text.starts_with("State<")
    });
    let has_headers = f.sig.inputs.iter().any(|arg| {
        let syn::FnArg::Typed(pat) = arg else {
            return false;
        };
        let ty_text = pat.ty.to_token_stream().to_string();
        ty_text.starts_with("HeaderMap")
    });
    if !has_state && !has_headers {
        return false;
    }
    // Internal helpers (not registered as routes) that happen to take State
    // are rare; only functions whose name is not underscore-prefixed count.
    !f.sig.ident.to_string().starts_with('_')
}

/// The per-function AST check: every statement inside THIS function body is
/// visited; nothing outside it can count as its authorization.
fn function_has_guard(f: &syn::ItemFn) -> bool {
    let mut visitor = GuardVisitor { found: false };
    visitor.visit_block(&f.block);
    visitor.found
}

#[test]
fn every_business_handler_declares_authorization() {
    let public: HashSet<&str> = PUBLIC_HANDLERS.iter().copied().collect();
    let self_service: HashSet<&str> = SELF_SERVICE_HANDLERS.iter().copied().collect();

    let routes_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/routes");
    let mut uncovered: Vec<String> = Vec::new();
    let mut handlers_seen = 0usize;

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
        let Ok(file) = syn::parse_file(&src) else {
            continue;
        };
        for item in &file.items {
            let syn::Item::Fn(f) = item else { continue };
            if !is_business_handler(f) {
                continue;
            }
            handlers_seen += 1;
            let name = f.sig.ident.to_string();
            if public.contains(name.as_str()) || self_service.contains(name.as_str()) {
                continue;
            }
            if !function_has_guard(f) {
                uncovered.push(format!("{fname}: {name}"));
            }
        }
    }

    assert!(
        handlers_seen > 0,
        "the AST scan must find at least one business handler"
    );
    assert!(
        uncovered.is_empty(),
        "Handlers without declared authorization in their OWN body ({}):\n{}",
        uncovered.len(),
        uncovered.join("\n")
    );
}
