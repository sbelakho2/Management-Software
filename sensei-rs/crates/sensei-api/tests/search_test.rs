//! End-to-end tests for the unified search endpoint.
//!
//! Covers:
//! - GET /api/v1/search?q=...
//! - Empty query handling
//! - Unauthenticated access

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Search ────────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_search_basic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=test", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert!(json["total"].is_number());
    assert_eq!(json["query"], "test");
}

#[tokio::test]
async fn test_search_empty_query() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert_eq!(json["total"], 0);
}

#[tokio::test]
async fn test_search_with_limit() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=admin&limit=5", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["results"].is_array());
    assert_eq!(json["query"], "admin");
}

#[tokio::test]
async fn test_search_facets_grouped_by_entity_type() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    // Seed searchable entities: a task and a work center sharing a keyword.
    let task = common::fixtures::task_payload("Turbo widget task", "high");
    let req = app.post_authenticated("/api/v1/tasks", &token, task);
    let _ = app.send_request(req).await;

    let wc = common::fixtures::work_center_payload("Turbo Assembly Line", "Assembly");
    let req = app.post_authenticated("/api/v1/work-centers", &token, wc);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/search?q=Turbo", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    let facets = json["facets"].as_array().unwrap();
    assert!(!facets.is_empty(), "facets must be computed from results");
    let total_facet_count: usize = facets
        .iter()
        .map(|f| f["count"].as_u64().unwrap() as usize)
        .sum();
    assert_eq!(total_facet_count, json["total"].as_u64().unwrap() as usize);
    // At least one "task" facet for the seeded task.
    assert!(facets.iter().any(|f| f["entity_type"] == "task"));
    for facet in facets {
        assert!(
            facet["count"].as_u64().unwrap() >= 1,
            "facet counts must be positive"
        );
    }
}

#[tokio::test]
async fn test_search_entity_type_filter() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let task = common::fixtures::task_payload("Filtered task", "medium");
    let req = app.post_authenticated("/api/v1/tasks", &token, task);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/search?q=Filtered&entity_type=task", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["total"].as_u64().unwrap_or(0) >= 1);
    for result in json["results"].as_array().unwrap() {
        assert_eq!(result["result_type"], "task");
    }
}

#[tokio::test]
async fn test_search_empty_facets() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let req = app.get_authenticated("/api/v1/search?q=", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total"], 0);
    assert_eq!(json["facets"].as_array().unwrap().len(), 0);
}

#[tokio::test]
async fn test_search_unauthenticated() {
    let app = common::TestApp::new().await;

    let req = app.get("/api/v1/search?q=test");
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::UNAUTHORIZED);
}
