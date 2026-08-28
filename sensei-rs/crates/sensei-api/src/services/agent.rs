//! Tool registry: every tool wraps a DOMAIN command/query (item 140) —
//! never SQL/shell/HTTP. The registry owns the ToolSpecs; execution
//! re-validates the caller's permission and returns evidence-carrying
//! results (item 96).

use sensei_agent_core::context::AgentContext;
use sensei_agent_core::evidence::{EvidenceRef, ToolResult};
use sensei_agent_core::tools::{PolicyEngine, ToolSpec};
use sensei_services::production::ProductionService;
use sensei_services::supply_chain::SupplyChainService;
use uuid::Uuid;

/// The agent's read-only toolset (Phase 3: read/calculate/recommend only).
pub fn build_readonly_tools() -> Vec<ToolSpec> {
    vec![
        ToolSpec::read_only(
            "get_work_order",
            "production:work-order:read",
            serde_json::json!({"id": "uuid"}),
            serde_json::json!({"work_order": "object"}),
        ),
        ToolSpec::read_only(
            "get_inventory_balance",
            "inventory:read",
            serde_json::json!({"product_id": "uuid"}),
            serde_json::json!({"items": "array"}),
        ),
        ToolSpec::read_only(
            "calculate_takt",
            "tps:standard-work:read",
            serde_json::json!({
                "scheduled_seconds": "integer",
                "breaks_seconds": "integer",
                "planned_downtime_seconds": "integer",
                "demand_units": "number"
            }),
            serde_json::json!({"takt_seconds": "number"}),
        ),
    ]
}

/// Validate the arguments against the tool's declared input schema
/// (type-level: uuid/string/integer/number). The schema is enforced, not
/// descriptive.
fn validate_args(tool: &ToolSpec, args: &serde_json::Value) -> Result<(), String> {
    let Some(schema) = tool.input_schema.as_object() else {
        return Ok(());
    };
    for (key, expected) in schema {
        if expected == "uuid" {
            if args
                .get(key)
                .and_then(|v| v.as_str())
                .is_none_or(|s| uuid::Uuid::parse_str(s).is_err())
            {
                return Err(format!(
                    "Tool '{}': argument '{key}' must be a uuid",
                    tool.name
                ));
            }
        } else if expected == "string" {
            if args.get(key).and_then(|v| v.as_str()).is_none() {
                return Err(format!(
                    "Tool '{}': argument '{key}' must be a string",
                    tool.name
                ));
            }
        } else if expected == "integer" && args.get(key).and_then(|v| v.as_u64()).is_none() {
            return Err(format!(
                "Tool '{}': argument '{key}' must be an integer",
                tool.name
            ));
        } else if expected == "number" && args.get(key).and_then(|v| v.as_f64()).is_none() {
            return Err(format!(
                "Tool '{}': argument '{key}' must be a number",
                tool.name
            ));
        }
    }
    Ok(())
}

/// Execute one tool on behalf of the caller. The permission is re-checked
/// here (the prompt is never the security boundary); every result carries
/// evidence refs and the tool version.
pub async fn execute_tool(
    ctx: &AgentContext,
    tool: &ToolSpec,
    args: serde_json::Value,
    policy: &PolicyEngine,
    production: &dyn ProductionService,
    supply_chain: &dyn SupplyChainService,
) -> Result<ToolResult<serde_json::Value>, String> {
    // Defense in depth: independent re-check at execution time (read-only
    // tools are Automatic; write tools would require an approval artifact).
    if !policy.can_execute(ctx, tool, true) {
        return Err(format!(
            "Tool '{}' is not permitted for this caller",
            tool.name
        ));
    }
    // Schema enforcement: the declared input schema is checked (type-level)
    // before dispatch — the schema is a contract, not descriptive metadata.
    validate_args(tool, &args)?;
    let now = chrono::Utc::now();
    match tool.name.as_str() {
        "get_work_order" => {
            let id: Uuid = args
                .get("id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "get_work_order requires id".to_string())?;
            let wo = production
                .get_work_order(ctx.tenant_id, id)
                .await
                .map_err(|e| e.to_string())?;
            let data = serde_json::to_value(&wo).map_err(|e| e.to_string())?;
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new(format!("work_order:{id}"), 1, now)],
                &format!("get_work_order@v{}", tool.version),
            ))
        }
        "get_inventory_balance" => {
            let product_id: Uuid = args
                .get("product_id")
                .and_then(|v| v.as_str())
                .and_then(|s| Uuid::parse_str(s).ok())
                .ok_or_else(|| "get_inventory_balance requires product_id".to_string())?;
            let items = supply_chain
                .get_inventory(ctx.tenant_id, product_id)
                .await
                .map_err(|e| e.to_string())?;
            let data = serde_json::to_value(&items).map_err(|e| e.to_string())?;
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new(format!("inventory:{product_id}"), 1, now)],
                &format!("get_inventory_balance@v{}", tool.version),
            ))
        }
        "calculate_takt" => {
            let scheduled = args
                .get("scheduled_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let breaks = args
                .get("breaks_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let downtime = args
                .get("planned_downtime_seconds")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let demand = args
                .get("demand_units")
                .and_then(|v| v.as_f64())
                .map(|f| {
                    rust_decimal::Decimal::from_f64_retain(f).unwrap_or(rust_decimal::Decimal::ZERO)
                })
                .ok_or_else(|| "calculate_takt requires demand_units".to_string())?;
            let available = sensei_services::tps::AvailableProductionTime {
                scheduled_seconds: scheduled,
                breaks_seconds: breaks,
                planned_downtime_seconds: downtime,
            };
            let takt = sensei_services::tps::calculate_takt(Uuid::new_v4(), &available, demand)
                .ok_or_else(|| "No takt exists for zero demand".to_string())?;
            let data = serde_json::json!({
                "takt_seconds": takt.takt_seconds.to_string(),
                "net_available_seconds": takt.net_available_seconds,
            });
            Ok(ToolResult::new(
                data,
                vec![EvidenceRef::new("tps:calculate_takt", 1, now)],
                &format!("calculate_takt@v{}", tool.version),
            ))
        }
        other => Err(format!("Unknown tool '{other}'")),
    }
}
