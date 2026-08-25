//! End-to-end tests for CTQ (Critical-To-Quality) endpoints.
//!
//! Covers: create, list, get, update characteristic; create record,
//! list records, get conformance analysis.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

// ── Characteristic CRUD ────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_characteristic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Diameter", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["id"].as_str().unwrap_or("").len() > 0);
    assert_eq!(json["name"], "Diameter");
}

#[tokio::test]
async fn test_list_characteristics() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Length", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/ctq/characteristics", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_get_characteristic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Width", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(
        &format!("/api/v1/ctq/characteristics/{}", char_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], char_id);
}

#[tokio::test]
async fn test_get_characteristic_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/ctq/characteristics/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_characteristic() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Tolerance", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated Tolerance"});
    let req = app.put_authenticated(
        &format!("/api/v1/ctq/characteristics/{}", char_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Tolerance");
}

// ── Records ────────────────────────────────────────────────────────────────

#[tokio::test]
async fn test_create_record() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Record Test", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap();

    let record = serde_json::json!({"value": 15.0});
    let req = app.post_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/records", char_id),
        &token,
        record,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["value"], 15.0);
}

#[tokio::test]
async fn test_list_records() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("List Records", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap();

    let record = serde_json::json!({"value": 12.5});
    let req = app.post_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/records", char_id),
        &token,
        record,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/records", char_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().map_or(false, |a| a.len() >= 1));
}

#[tokio::test]
async fn test_conformance_analysis() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Analysis CTQ", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap();

    let record = serde_json::json!({"value": 15.0});
    let req = app.post_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/records", char_id),
        &token,
        record,
    );
    let _ = app.send_request(req).await;

    let req = app.get_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/analysis", char_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["total_measurements"], 1);
}

#[tokio::test]
async fn test_conformance_analysis_uses_sample_variance() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Variance CTQ", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap().to_string();

    // Values 10 and 14: mean 12, population variance 4 (std 2), sample
    // variance 8 (std ≈ 2.8284). The analysis must use the sample (n-1)
    // denominator.
    for value in [10.0, 14.0] {
        let record = serde_json::json!({"value": value});
        let req = app.post_authenticated(
            &format!("/api/v1/ctq/characteristics/{}/records", char_id),
            &token,
            record,
        );
        let resp = app.send_request(req).await;
        assert_eq!(resp.status(), StatusCode::OK);
    }

    let req = app.get_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/analysis", char_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    let std_dev = json["std_dev"].as_f64().unwrap();
    assert!(
        (std_dev - 8.0_f64.sqrt()).abs() < 1e-9,
        "std_dev must use the sample (n-1) variance, got {std_dev}"
    );
}

#[tokio::test]
async fn test_list_records_invalid_date_filter_rejected() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::ctq_characteristic_payload("Date Filter CTQ", "Dimension");
    let req = app.post_authenticated("/api/v1/ctq/characteristics", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let char_id = created["id"].as_str().unwrap().to_string();

    // Invalid date parameters are a client error (400), not a silent
    // no-filter.
    let req = app.get_authenticated(
        &format!("/api/v1/ctq/characteristics/{}/records?date_from=not-a-date", char_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
}
