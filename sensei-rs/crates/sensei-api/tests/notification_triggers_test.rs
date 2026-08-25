//! End-to-end tests for Notification Trigger endpoints.
//!
//! Covers: CRUD, toggle, test, list event types.

use axum::http::StatusCode;
use serde_json::Value;

mod common;

#[tokio::test]
async fn test_create_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Andon Raised Alert", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(!json["id"].as_str().unwrap_or("").is_empty());
    assert_eq!(json["name"], "Andon Raised Alert");
}

#[tokio::test]
async fn test_list_notification_triggers() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Trigger A", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let _ = app.send_request(req).await;

    let req = app.get_authenticated("/api/v1/notification-triggers", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json["data"].as_array().is_some_and(|a| !a.is_empty()));
}

#[tokio::test]
async fn test_get_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Get Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.get_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["id"], trigger_id);
}

#[tokio::test]
async fn test_get_notification_trigger_not_found() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated(
        "/api/v1/notification-triggers/00000000-0000-0000-0000-000000000000",
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_update_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Update Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let update = serde_json::json!({"name": "Updated Trigger"});
    let req = app.put_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
        update,
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["name"], "Updated Trigger");
}

#[tokio::test]
async fn test_delete_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Delete Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.delete_authenticated(
        &format!("/api/v1/notification-triggers/{}", trigger_id),
        &token,
    );
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_toggle_notification_trigger() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let body = common::fixtures::notification_trigger_payload("Toggle Trigger", "andon.raised");
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, body);
    let mut resp = app.send_request(req).await;
    let created: Value = app.json_body(&mut resp).await;
    let trigger_id = created["id"].as_str().unwrap();

    let req = app.patch_authenticated(
        &format!("/api/v1/notification-triggers/{}/toggle", trigger_id),
        &token,
        serde_json::json!({}),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert!(json.as_object().unwrap().contains_key("is_active"));
}

#[tokio::test]
async fn test_list_event_types() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;
    let req = app.get_authenticated("/api/v1/notification-triggers/event-types", &token);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    // The catalog must contain the REAL event_type() strings from
    // sensei-core, e.g. the NCR creation event.
    let json: Value = app.json_body(&mut resp).await;
    let event_types = json.as_array().expect("catalog should be an array");
    assert!(
        event_types
            .iter()
            .any(|e| e["event_type"] == "quality.ncr.created"),
        "catalog is missing real event type quality.ncr.created"
    );
    assert!(
        event_types
            .iter()
            .any(|e| e["event_type"] == "operations.kanban.deleted"),
        "catalog is missing real event type operations.kanban.deleted"
    );
    // Deprecated fake event types must be gone.
    assert!(
        !event_types
            .iter()
            .any(|e| e["event_type"] == "andon.raised"),
        "fake event type andon.raised must not be in the catalog"
    );
}

/// Create a trigger with a real event type and target roles.
async fn create_real_trigger(
    app: &common::TestApp,
    token: &str,
    name: &str,
    event_type: &str,
    condition: serde_json::Value,
) -> Value {
    let body = serde_json::json!({
        "name": name,
        "description": format!("Trigger: {}", name),
        "event_type": event_type,
        "condition": condition,
        "action": {"template": "notification_template", "payload": null},
        "channels": ["InApp"],
        "cooldown_minutes": 60,
        "target_roles": ["admin"],
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/notification-triggers", token, body);
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK, "trigger creation failed");
    app.json_body(&mut resp).await
}

#[tokio::test]
async fn test_test_trigger_condition_matches_and_reports_rules() {
    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    let trigger = create_real_trigger(
        &app,
        &token,
        "NCR Severity Alert",
        "quality.ncr.created",
        serde_json::json!({"severity": "high"}),
    )
    .await;
    let trigger_id = trigger["id"].as_str().unwrap().to_string();

    // Matching payload: condition_matched + the rule name reported.
    let payload = serde_json::json!({
        "ncr_id": uuid::Uuid::new_v4().to_string(),
        "ncr_number": "NCR-100",
        "title": "Broken part",
        "severity": "high",
        "reported_by": uuid::Uuid::new_v4().to_string(),
    });
    let req = app.post_authenticated(
        &format!("/api/v1/notification-triggers/{}/test", trigger_id),
        &token,
        serde_json::json!({ "event_payload": payload }),
    );
    let mut resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["condition_matched"], true);
    assert_eq!(json["matched_rules"][0], "NCR Severity Alert");
    assert!(!json["actions_executed"]
        .as_array()
        .unwrap_or(&vec![])
        .is_empty());

    // Non-matching payload: no rule matched, no actions.
    let other_payload = serde_json::json!({ "severity": "low" });
    let req = app.post_authenticated(
        &format!("/api/v1/notification-triggers/{}/test", trigger_id),
        &token,
        serde_json::json!({ "event_payload": other_payload }),
    );
    let mut resp = app.send_request(req).await;
    let json: Value = app.json_body(&mut resp).await;
    assert_eq!(json["condition_matched"], false);
    assert!(json["matched_rules"]
        .as_array()
        .unwrap_or(&vec![])
        .is_empty());
}

#[tokio::test]
async fn test_worker_creates_notifications_for_matching_events() {
    use sensei_core::domain::events::NcrCreatedEvent;

    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    create_real_trigger(
        &app,
        &token,
        "High NCR Alert",
        "quality.ncr.created",
        serde_json::json!({"severity": "high"}),
    )
    .await;

    // Start the worker on the in-memory bus and wait until the subscription
    // is active: the in-memory bus does not replay events published before
    // the worker subscribed.
    let subscribed = sensei_api::services::notification_trigger_worker::spawn(app.state.clone());
    let subscribe_deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !subscribed.load(std::sync::atomic::Ordering::SeqCst) {
        assert!(
            std::time::Instant::now() < subscribe_deadline,
            "worker never subscribed to the event bus"
        );
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    // Publish a matching event.
    let event = NcrCreatedEvent::new(
        app.admin_tenant_id,
        uuid::Uuid::new_v4(),
        "NCR-900".to_string(),
        "High severity defect".to_string(),
        "high".to_string(),
        app.admin_user_id,
    );
    app.state
        .event_bus
        .publish(&event)
        .await
        .expect("publish should succeed");

    // The worker runs on a spawned task: poll until the notification lands.
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    let mut found = false;
    while std::time::Instant::now() < deadline {
        let notifications = app.state.notifications.read(app.admin_tenant_id).await;
        let matching: Vec<_> = notifications
            .values()
            .filter(|n| {
                n.tenant_id == app.admin_tenant_id
                    && n.user_id == app.admin_user_id
                    && n.reference_type.as_deref() == Some("quality.ncr.created")
            })
            .collect();
        if !matching.is_empty() {
            found = true;
            break;
        }
        drop(notifications);
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    }
    assert!(found, "worker did not create a notification for the event");
}

#[tokio::test]
async fn test_worker_respects_cooldown_and_empty_target_roles() {
    use sensei_core::domain::events::NcrCreatedEvent;

    let app = common::TestApp::new().await;
    let token = app.login_as_admin().await;

    create_real_trigger(
        &app,
        &token,
        "Cooldown Alert",
        "quality.ncr.created",
        serde_json::json!(null),
    )
    .await;

    // A trigger with no target roles must never notify.
    let no_roles = serde_json::json!({
        "name": "No Roles Trigger",
        "description": "No target roles",
        "event_type": "quality.ncr.created",
        "condition": null,
        "action": {"template": "t", "payload": null},
        "channels": ["InApp"],
        "target_roles": [],
        "is_active": true,
    });
    let req = app.post_authenticated("/api/v1/notification-triggers", &token, no_roles);
    let resp = app.send_request(req).await;
    assert_eq!(resp.status(), StatusCode::OK);

    let subscribed = sensei_api::services::notification_trigger_worker::spawn(app.state.clone());
    let subscribe_deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    while !subscribed.load(std::sync::atomic::Ordering::SeqCst) {
        assert!(
            std::time::Instant::now() < subscribe_deadline,
            "worker never subscribed to the event bus"
        );
        tokio::time::sleep(std::time::Duration::from_millis(10)).await;
    }

    let event = NcrCreatedEvent::new(
        app.admin_tenant_id,
        uuid::Uuid::new_v4(),
        "NCR-901".to_string(),
        "Cooldown test".to_string(),
        "low".to_string(),
        app.admin_user_id,
    );

    // First publication fires the cooldown-enabled trigger once. Wait
    // until the worker has processed it (poll) so the second event is
    // guaranteed to arrive after last_triggered_at was stamped.
    app.state
        .event_bus
        .publish(&event)
        .await
        .expect("publish ok");
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
    loop {
        let count = count_trigger_notifications(&app).await;
        if count >= 1 {
            break;
        }
        assert!(
            std::time::Instant::now() < deadline,
            "worker did not process the first event"
        );
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;
    }

    // A second event within the 60-minute cooldown must be suppressed, and
    // the no-roles trigger never fires.
    app.state
        .event_bus
        .publish(&event)
        .await
        .expect("publish ok");
    tokio::time::sleep(std::time::Duration::from_millis(300)).await;
    let count_after_second = count_trigger_notifications(&app).await;
    assert_eq!(
        count_after_second, 1,
        "cooldown or empty target_roles must suppress the second event"
    );
}

/// Count in-app notifications created by triggers for the admin user.
async fn count_trigger_notifications(app: &common::TestApp) -> usize {
    let notifications = app.state.notifications.read(app.admin_tenant_id).await;
    notifications
        .values()
        .filter(|n| {
            n.tenant_id == app.admin_tenant_id
                && n.user_id == app.admin_user_id
                && n.notification_type == "notification_trigger"
        })
        .count()
}
