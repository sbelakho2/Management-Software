//! Router-level tests for the static + SPA frontend resolver
//! (thirtieth-first audit, item 10).
//!
//! The hand-rolled `fs::read` fallback in `router.rs` was replaced by
//! tower-http services (`ServeDir` + `ServeFile`). These tests pin a real
//! static directory (`SENSEI_STATIC_DIR`) with an `index.html` entry
//! point, an asset and a secret file, then prove:
//!
//! - SPA deep links (GET /login, /today) resolve to `index.html` with
//!   200 + `text/html` (tower-http 0.6's `not_found_service` forces 404,
//!   so the resolver fixes the status back to the entry file's 200);
//! - real bundle assets are served with their own content type;
//! - an unknown `/api/*` path NEVER receives `index.html`: the
//!   `/api/{*rest}` JSON 404 route is registered before the fallback
//!   service, so the fallback only ever sees non-API paths;
//! - a path-traversal attempt (`..` / percent-encoded `..`) never
//!   escapes the static directory;
//! - non-GET methods on frontend paths stay 405 (ServeDir's method
//!   guard), never HTML.
//!
//! All tests share ONE static world: the environment variable is pinned
//! exactly once per process (`OnceLock`) before the first router build,
//! so parallel test threads can never race on `std::env`.

use axum::body::Body;
use axum::http::{Request, StatusCode};
use std::sync::OnceLock;

mod common;

/// The static frontend world: a temp directory that plays the role of
/// the deployed `/app/static` bundle.
struct StaticWorld {
    dir: std::path::PathBuf,
}

impl StaticWorld {
    fn marker() -> &'static str {
        "SENSEI-SPA-INDEX-MARKER-7f3d"
    }

    fn secret() -> &'static str {
        "SENSEI-TOP-SECRET-DO-NOT-LEAK"
    }

    /// Create the static dir (index.html + an asset + a secret probe
    /// file) and pin `SENSEI_STATIC_DIR` to it EXACTLY ONCE per test
    /// process. Returns the shared world.
    fn setup() -> &'static StaticWorld {
        static WORLD: OnceLock<StaticWorld> = OnceLock::new();
        WORLD.get_or_init(|| {
            let dir = std::env::temp_dir()
                .join(format!("sensei-static-resolver-{}", uuid::Uuid::new_v4()));
            std::fs::create_dir_all(dir.join("assets")).expect("static dirs");
            std::fs::write(
                dir.join("index.html"),
                format!(
                    "<!DOCTYPE html><html><body>{}</body></html>",
                    Self::marker()
                ),
            )
            .expect("index.html");
            std::fs::write(
                dir.join("assets").join("app.wasm"),
                [0x00, 0x61, 0x73, 0x6d],
            )
            .expect("wasm asset");
            std::fs::write(dir.join("secret.txt"), Self::secret()).expect("secret probe");
            // Pinned before any router build; never mutated again.
            std::env::set_var("SENSEI_STATIC_DIR", &dir);
            StaticWorld { dir }
        })
    }

    async fn index_body(resp: axum::response::Response<Body>) -> String {
        let bytes = axum::body::to_bytes(resp.into_body(), 1024 * 1024)
            .await
            .expect("read body");
        String::from_utf8(bytes.to_vec()).expect("utf8 body")
    }
}

/// GET /login and /today (client-side SPA routes — no such files exist)
/// deep-link to index.html with 200 text/html, and real assets keep
/// their own bytes + content type. GET / is the registered entry route.
#[tokio::test]
async fn spa_deep_links_and_assets_resolve_through_the_servedir_fallback() {
    let world = StaticWorld::setup();
    let app = common::TestApp::new().await;

    for path in ["/", "/login", "/today", "/station/42", "/some/client/route"] {
        let req = Request::builder()
            .uri(path)
            .body(Body::empty())
            .expect("request builds");
        let resp = app.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK, "GET {path} must be 200");
        let content_type = resp
            .headers()
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or_default()
            .to_string();
        assert!(
            content_type.starts_with("text/html"),
            "GET {path} must be text/html, got {content_type}"
        );
        let body = StaticWorld::index_body(resp).await;
        assert!(
            body.contains(StaticWorld::marker()),
            "GET {path} must serve the SPA entry point"
        );
    }

    // Real bundle asset: served from disk with its own content type.
    let req = Request::builder()
        .uri("/assets/app.wasm")
        .body(Body::empty())
        .expect("request builds");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let content_type = resp
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or_default()
        .to_string();
    assert!(
        content_type.contains("wasm"),
        "assets keep their mime type, got {content_type}"
    );

    // Positive control: an existing file IS served directly.
    let req = Request::builder()
        .uri("/secret.txt")
        .body(Body::empty())
        .expect("request builds");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let body = StaticWorld::index_body(resp).await;
    assert!(body.contains(StaticWorld::secret()));

    // The static dir exists on disk (sanity for the traversal probe).
    assert!(world.dir.join("index.html").is_file());
}

/// Unknown /api/* paths answer with the structured JSON 404 — they must
/// NEVER fall through to the SPA entry point (the api_not_found route is
/// registered before the fallback service).
#[tokio::test]
async fn unknown_api_paths_never_receive_index_html() {
    let _world = StaticWorld::setup();
    let app = common::TestApp::new().await;

    for path in ["/api/v1/does-not-exist", "/api/v1/andon/nope/nope"] {
        let req = Request::builder()
            .uri(path)
            .body(Body::empty())
            .expect("request builds");
        let resp = app.send_request(req).await;
        assert_eq!(
            resp.status(),
            StatusCode::NOT_FOUND,
            "GET {path} is a JSON 404"
        );
        let content_type = resp
            .headers()
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or_default()
            .to_string();
        assert!(
            content_type.starts_with("application/json"),
            "GET {path} must be JSON, got {content_type}"
        );
        let body = StaticWorld::index_body(resp).await;
        assert!(
            !body.contains(StaticWorld::marker()),
            "GET {path} must never serve the SPA entry point"
        );
        assert!(body.contains("not_found"), "JSON 404 body, got {body}");
    }

    // A non-GET on an unknown API path: the /api/{*rest} route matches
    // the path but not the method → 405, never HTML.
    let req = Request::builder()
        .uri("/api/v1/does-not-exist")
        .method("POST")
        .body(Body::empty())
        .expect("request builds");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::METHOD_NOT_ALLOWED);
}

/// A path-traversal attempt never escapes the static directory: the
/// secret probe file is only reachable through its real path, never via
/// `..` segments (plain or percent-encoded) — ServeDir percent-decodes
/// and refuses ParentDir components.
#[tokio::test]
async fn path_traversal_never_escapes_the_static_dir() {
    let _world = StaticWorld::setup();
    let app = common::TestApp::new().await;

    let secret_marker = StaticWorld::secret().to_string();
    for path in [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/%2e%2e%2fsecret.txt",
        "/assets/../../secret.txt",
        "/assets/%2e%2e/%2e%2e/secret.txt",
    ] {
        let req = Request::builder()
            .uri(path)
            .body(Body::empty())
            .expect("request builds");
        let resp = app.send_request(req).await;
        let status = resp.status();
        assert!(
            status == StatusCode::OK || status == StatusCode::NOT_FOUND,
            "GET {path} resolves without error, got {status}"
        );
        let body = StaticWorld::index_body(resp).await;
        assert!(
            !body.contains(&secret_marker),
            "GET {path} must never leak the secret file"
        );
    }
}

/// Non-GET methods on frontend paths are answered by ServeDir's method
/// guard with 405 — the SPA HTML is never served for a POST.
#[tokio::test]
async fn non_get_methods_on_frontend_paths_stay_405() {
    let _world = StaticWorld::setup();
    let app = common::TestApp::new().await;

    let req = Request::builder()
        .uri("/login")
        .method("POST")
        .body(Body::empty())
        .expect("request builds");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::METHOD_NOT_ALLOWED);
    let body = StaticWorld::index_body(resp).await;
    assert!(
        !body.contains(StaticWorld::marker()),
        "a POST must never receive the SPA entry point"
    );
}
