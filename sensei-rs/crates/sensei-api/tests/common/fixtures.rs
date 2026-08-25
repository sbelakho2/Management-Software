//! Test data factories for end-to-end API tests.
//!
//! Provides factory functions that generate valid payloads for each
//! domain entity, reducing boilerplate in individual test files.

use serde_json::Value;

// ── Auth / Users ─────────────────────────────────────────────────────────────

/// Generate a valid registration payload.
pub fn register_payload(email: &str, password: &str, name: &str) -> Value {
    serde_json::json!({
        "email": email,
        "password": password,
        "name": name,
    })
}

/// Generate a valid login payload.
pub fn login_payload(email: &str, password: &str) -> Value {
    serde_json::json!({
        "email": email,
        "password": password,
    })
}

// ── Work Orders ──────────────────────────────────────────────────────────────

/// Generate a valid work order creation payload.
pub fn work_order_payload(product_name: &str, quantity: i64) -> Value {
    serde_json::json!({
        "product_name": product_name,
        "product_id": uuid::Uuid::new_v4().to_string(),
        "quantity": quantity,
        "priority": "Normal",
        "status": "Scheduled",
        "notes": "Test work order",
    })
}

// ── Work Centers ─────────────────────────────────────────────────────────────

/// Generate a valid work center creation payload.
pub fn work_center_payload(name: &str, wc_type: &str) -> Value {
    serde_json::json!({
        "work_center_number": format!("WC-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "name": name,
        "description": format!("{} work center", name),
        "work_center_type": wc_type,
        "capacity_per_shift": 8,
        "shifts_per_day": 2,
        // Efficiency is a percentage (0-100), not a fraction.
        "efficiency": 85.0,
        "available_hours_per_day": 16.0,
        "is_active": true,
    })
}

// ── Andon ────────────────────────────────────────────────────────────────────

/// Generate a valid Andon raise payload.
pub fn andon_payload(_work_center: &str, problem: &str) -> Value {
    serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "andon_number": "ANDON-001",
        "work_center_id": uuid::Uuid::new_v4().to_string(),
        "issue_type": "quality",
        "severity": "high",
        "description": problem,
        "status": "active",
        "raised_by": uuid::Uuid::new_v4().to_string(),
        "created_at": "2025-01-01T00:00:00Z",
    })
}

// ── A3 ───────────────────────────────────────────────────────────────────────

/// Generate a valid A3 creation payload.
pub fn a3_payload(title: &str, problem: &str) -> Value {
    serde_json::json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "tenant_id": uuid::Uuid::new_v4().to_string(),
        "a3_number": format!("A3-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "title": title,
        "background": problem,
        "current_state": "Current state description",
        "goal": "Reduce defects by 50%",
        "root_cause_analysis": "Root cause analysis findings",
        "countermeasures": "Implement standardized work instructions",
        "check_plan": "Weekly audits for 4 weeks",
        "follow_up": "Monthly review with team",
        "status": "draft",
        "owner_id": uuid::Uuid::new_v4().to_string(),
        "created_at": "2026-01-01T00:00:00Z",
    })
}

// ── Obeya ────────────────────────────────────────────────────────────────────

/// Generate a valid Obeya board creation payload.
pub fn obeya_board_payload(name: &str, board_type: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("{} board", name),
        "board_type": board_type,
        "department": "Production",
        "is_active": true,
    })
}

// ── Risk ─────────────────────────────────────────────────────────────────────

/// Generate a valid risk creation payload.
pub fn risk_payload(title: &str, category: &str) -> Value {
    serde_json::json!({
        "title": title,
        "description": format!("Risk: {}", title),
        "category": category,
        "probability": 3,
        "impact": 4,
        "risk_level": "Medium",
        "status": "Open",
    })
}

// ── Inventory ────────────────────────────────────────────────────────────────

/// Generate a valid inventory item payload.
pub fn inventory_item_payload(sku: &str, name: &str) -> Value {
    serde_json::json!({
        "sku": sku,
        "name": name,
        "description": format!("Item: {}", name),
        "category": "Raw Material",
        "warehouse_id": uuid::Uuid::new_v4().to_string(),
        "quantity_on_hand": 100.0,
        "quantity_reserved": 10.0,
        "quantity_available": 90.0,
        "unit_cost": 25.50,
        "total_value": 2550.0,
        "reorder_point": 20.0,
        "reorder_quantity": 50.0,
        "is_active": true,
    })
}

// ── MRP ──────────────────────────────────────────────────────────────────────

/// Generate a valid MRP demand payload.
pub fn mrp_demand_payload(product_name: &str, quantity: f64) -> Value {
    serde_json::json!({
        "product_id": uuid::Uuid::new_v4().to_string(),
        "product_name": product_name,
        "quantity": quantity,
        "due_date": "2026-07-15T00:00:00Z",
        "source_type": "SalesOrder",
        "notes": "Test demand",
    })
}

// ── Tasks ────────────────────────────────────────────────────────────────────

/// Generate a valid task creation payload.
pub fn task_payload(title: &str, priority: &str) -> Value {
    serde_json::json!({
        "title": title,
        "description": format!("Task: {}", title),
        "status": "Open",
        "priority": priority,
        "category": "General",
        "tags": ["test"],
    })
}

// ── Kanban ───────────────────────────────────────────────────────────────────

/// Generate a valid Kanban board creation payload.
pub fn kanban_board_payload(name: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("Kanban board: {}", name),
    })
}

// ── Quality ──────────────────────────────────────────────────────────────────

/// Generate a valid NCR (Non-Conformance Report) payload.
pub fn ncr_payload(title: &str) -> Value {
    serde_json::json!({
        "title": title,
        "description": format!("NCR: {}", title),
        "nc_type": "Product",
        "severity": "High",
        "source": "Inspection",
        "status": "Open",
        "is_recurrence": false,
    })
}

/// Generate a valid CAPA (Corrective Action Preventive Action) payload.
pub fn capa_payload(title: &str) -> Value {
    serde_json::json!({
        "title": title,
        "description": format!("CAPA: {}", title),
        "nc_ids": [uuid::Uuid::new_v4().to_string()],
        "capa_type": "Corrective",
        "priority": "High",
        "severity": "Critical",
        "source": "Audit",
        "status": "Open",
    })
}

// ── KPI ──────────────────────────────────────────────────────────────────────

/// Generate a valid KPI definition payload.
pub fn kpi_payload(name: &str, category: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("KPI: {}", name),
        "category": category,
        "unit": "%",
        "target": 95.0,
        "lower_limit": 80.0,
        "upper_limit": 100.0,
        "direction": "HigherIsBetter",
        "is_active": true,
    })
}

// ── Training ─────────────────────────────────────────────────────────────────

/// Generate a valid training course payload.
pub fn training_course_payload(title: &str, category: &str) -> Value {
    serde_json::json!({
        "title": title,
        "description": format!("Course: {}", title),
        "category": category,
        "duration_minutes": 120,
        "required_for_roles": [],
        "prerequisites": [],
        "is_mandatory": false,
        "is_active": true,
    })
}

// ── CTQ ──────────────────────────────────────────────────────────────────────

/// Generate a valid CTQ characteristic payload.
pub fn ctq_characteristic_payload(name: &str, category: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("CTQ: {}", name),
        "category": category,
        "specification_limit_lower": 10.0,
        "specification_limit_upper": 20.0,
        "target_value": 15.0,
        "unit": "mm",
        "measurement_method": "Caliper",
        "is_active": true,
    })
}

// ── Compliance / LSW ─────────────────────────────────────────────────────────

/// Generate a valid LSW standard payload.
pub fn lsw_standard_payload(title: &str, area: &str) -> Value {
    serde_json::json!({
        "title": title,
        "area": area,
        "layer": 1,
        "frequency": "Daily",
        "checklist_items": [
            {
                "id": uuid::Uuid::new_v4(),
                "description": "Check item 1",
                "expected_value": "OK",
                "is_critical": true,
            }
        ],
        "is_active": true,
    })
}

// ── Notification Triggers ────────────────────────────────────────────────────

/// Generate a valid notification trigger payload.
pub fn notification_trigger_payload(name: &str, event_type: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("Trigger: {}", name),
        "event_type": event_type,
        "condition": {"field": "status", "operator": "equals", "value": "completed"},
        "action": {"template": "notification_template", "payload": null},
        "channels": ["InApp"],
        "is_active": true,
    })
}

// ── State Machines ───────────────────────────────────────────────────────────

/// Generate a valid state machine definition payload.
pub fn state_machine_payload(name: &str, entity_type: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("State machine: {}", name),
        "entity_type": entity_type,
        "initial_state": "Draft",
        "states": [
            {"name": "Draft", "label": "Draft", "is_terminal": false, "allowed_roles": ["admin"]},
            {"name": "Active", "label": "Active", "is_terminal": false, "allowed_roles": ["admin"]},
            {"name": "Complete", "label": "Complete", "is_terminal": true, "allowed_roles": ["admin"]},
        ],
        "transitions": [
            {"from_state": "Draft", "to_state": "Active", "event": "activate", "conditions": null, "on_transition": null},
            {"from_state": "Active", "to_state": "Complete", "event": "complete", "conditions": null, "on_transition": null},
        ],
        "is_active": true,
    })
}

// ── Quoting Helper ───────────────────────────────────────────────────────────

/// Generate a valid saved view payload.
pub fn saved_view_payload(name: &str, entity_type: &str) -> Value {
    serde_json::json!({
        "name": name,
        "entity_type": entity_type,
        "filters": {"status": "Active"},
        "columns": ["id", "name", "status"],
        "is_default": false,
    })
}

// ── Escalation Policy ────────────────────────────────────────────────────────

/// Generate a valid escalation policy payload.
pub fn escalation_policy_payload(name: &str, event_type: &str) -> Value {
    serde_json::json!({
        "name": name,
        "description": format!("Escalation policy: {}", name),
        "event_type": event_type,
        "is_active": true,
        "rules": [
            {
                "id": uuid::Uuid::new_v4().to_string(),
                "priority": 1,
                "condition": "unacknowledged > 5min",
                "notify_user_ids": [],
                "notify_role": "supervisor",
                "escalate_after_seconds": 300,
            }
        ],
    })
}

// ── Standard Work ────────────────────────────────────────────────────────────

/// Generate a valid standard work document payload.
pub fn standard_work_payload(title: &str, area: &str, process: &str) -> Value {
    serde_json::json!({
        "title": title,
        "document_number": format!("SW-{}", uuid::Uuid::new_v4().to_string()[..8].to_string()),
        "area": area,
        "process": process,
        "status": "Draft",
        "steps": [
            {
                "id": uuid::Uuid::new_v4().to_string(),
                "step_number": 1,
                "description": "Step 1 description",
                "key_points": ["Point 1", "Point 2"],
                "duration_seconds": 60,
            }
        ],
        "required_skills": ["Assembly"],
        "quality_checks": [],
        "safety_notes": [],
        "tools_required": [],
        "materials_required": [],
        "attachments": [],
    })
}
