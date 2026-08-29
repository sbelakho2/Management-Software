//! Flow economics (items 36/38): make waste financially visible WITHOUT
//! lecturing. Purchasing sees the total flow impact of a decision; finance
//! sees WIP cash, aging inventory, scrap and rework — overproduction that
//! "looks efficient" must visibly look economically bad.
//!
//! All computations are pure functions over observable inputs — the DB
//! aggregation is a thin reader that feeds these.

use rust_decimal::Decimal;
use serde::Serialize;

/// The flow-cost view of a sourcing decision (item 36).
#[derive(Debug, Clone, Serialize)]
pub struct SourcingFlowCost {
    pub option_label: String,
    pub unit_price: Decimal,
    pub moq: Decimal,
    pub lead_time_days: i64,
    pub on_time_delivery: Decimal,
    /// Average stock held because of MOQ + lead time, in days of demand.
    pub inventory_days: Decimal,
    /// Cash trapped in stock for this option.
    pub trapped_cash: Decimal,
    /// Shortage-risk score 0..1 driven by OTD variability.
    pub shortage_risk: Decimal,
    /// Plain-language guidance (never a lecture about waste).
    pub guidance: String,
}

/// Compute the flow economics of one sourcing option.
/// `unit_price`, `moq` and `annual_demand` are money/quantity facts;
/// `demand_per_day` drives inventory days; `otd_stddev` (0..1) is the
/// delivery variability that drives shortage risk.
pub fn sourcing_flow_cost(
    label: &str,
    unit_price: Decimal,
    moq: Decimal,
    lead_time_days: i64,
    otd: Decimal,
    demand_per_day: Decimal,
    otd_variability: Decimal,
) -> SourcingFlowCost {
    // Inventory held because of MOQ + lead-time coverage (days of demand).
    let moq_days = if demand_per_day > Decimal::ZERO {
        moq / demand_per_day
    } else {
        Decimal::ZERO
    };
    let lead_days = Decimal::from(lead_time_days);
    let inventory_days = moq_days + lead_days;
    // Cash trapped: the MOQ at unit price (the minimum committed).
    let trapped_cash = moq * unit_price;
    // Shortage risk: variability dominates — a supplier with 98% OTD but
    // wild swings is riskier than a stable 90%.
    let shortage_risk = (otd_variability * Decimal::from(2))
        .max(Decimal::ZERO)
        .min(Decimal::ONE);
    let guidance = if inventory_days >= Decimal::from(30) {
        format!(
            "This option holds ~{inventory_days:.0} days of demand in stock \
             (≈ {trapped_cash:.2} cash committed). The 'cheapest' part can \
             create excess WIP, trapped cash and shortages when demand moves."
        )
    } else if shortage_risk > Decimal::from_f64_retain(0.5).unwrap() {
        format!(
            "Delivery VARIABILITY (risk {shortage_risk:.2}), not mean lead \
             time, drives your shortage exposure here."
        )
    } else {
        format!(
            "This option keeps {inventory_days:.0} days of stock and \
                 variability low — a flow-compatible choice."
        )
    };
    SourcingFlowCost {
        option_label: label.to_string(),
        unit_price,
        moq,
        lead_time_days,
        on_time_delivery: otd,
        inventory_days,
        trapped_cash,
        shortage_risk,
        guidance,
    }
}

/// One waste line in the finance view (item 38).
#[derive(Debug, Clone, Serialize)]
pub struct WasteLine {
    pub key: &'static str,
    pub label: &'static str,
    pub value: Decimal,
    /// The flow condition it reveals (plain language).
    pub guidance: String,
}

/// The finance waste snapshot.
#[derive(Debug, Clone, Serialize)]
pub struct FinanceWasteSnapshot {
    pub lines: Vec<WasteLine>,
    /// Total annual waste exposure in money.
    pub total_waste_annual: Decimal,
}

/// Compute the finance waste view from observable inputs — all monetary
/// amounts are measured by the caller (the DB aggregates money directly):
/// `wip_cash`, `aging_stock_value`, `scrap_cost`, `rework_cost`,
/// `premium_freight`, `expediting`; `batch_excess_days` × `daily_demand` ×
/// `unit_cost` is the working capital caused by batch policy.
/// Batch-policy inputs (item 38): `excess_days` × `daily_demand` ×
/// `unit_cost` is the working capital caused by the batch size.
#[derive(Debug, Clone, Copy)]
pub struct BatchPolicyInput {
    pub excess_days: Decimal,
    pub daily_demand: Decimal,
    pub unit_cost: Decimal,
}

pub fn finance_waste(
    wip_cash: Decimal,
    aging_stock_value: Decimal,
    scrap_cost: Decimal,
    rework_cost: Decimal,
    premium_freight: Decimal,
    expediting: Decimal,
    batch: BatchPolicyInput,
) -> FinanceWasteSnapshot {
    let batch_cash = batch.excess_days * batch.daily_demand * batch.unit_cost;
    let total = wip_cash
        + aging_stock_value
        + scrap_cost
        + rework_cost
        + premium_freight
        + expediting
        + batch_cash;
    let lines = vec![
        WasteLine {
            key: "wip_cash",
            label: "Cash in work-in-process",
            value: wip_cash,
            guidance: "WIP is cash sitting between operations. High WIP hides \
                       flow problems and delays defect discovery."
                .to_string(),
        },
        WasteLine {
            key: "aging_inventory",
            label: "Aging inventory",
            value: aging_stock_value,
            guidance: "Stock older than the target is a demand/mismatch signal, \
                       not an asset."
                .to_string(),
        },
        WasteLine {
            key: "scrap",
            label: "Scrap",
            value: scrap_cost,
            guidance: "Scrap is the measurable part of 'quality is not built \
                       in' — the invisible part is the lost capacity."
                .to_string(),
        },
        WasteLine {
            key: "rework",
            label: "Rework",
            value: rework_cost,
            guidance: "Rework doubles the work without doubling the value — it \
                       is the classic sign of inspect-in quality."
                .to_string(),
        },
        WasteLine {
            key: "premium_freight",
            label: "Premium freight",
            value: premium_freight,
            guidance: "Premium freight is the price of plan instability.".to_string(),
        },
        WasteLine {
            key: "expediting",
            label: "Expediting",
            value: expediting,
            guidance: "Expediting effort is the system compensating for a \
                       broken plan with people's time."
                .to_string(),
        },
        WasteLine {
            key: "batch_policy_cash",
            label: "Working capital caused by batch policy",
            value: batch_cash,
            guidance: "The batch size holds THIS much cash above near-term \
                       pull — a local 'efficiency' gain that looks economically \
                       bad at the system level."
                .to_string(),
        },
    ];
    FinanceWasteSnapshot {
        lines,
        total_waste_annual: total,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cheap_part_with_big_moq_traps_cash() {
        // €1.92/part, MOQ 10k, 9-week lead → ~63+ days of stock at 160/day.
        let a = sourcing_flow_cost(
            "Supplier A",
            Decimal::from_f64_retain(1.92).unwrap(),
            Decimal::from(10000),
            63,
            Decimal::from_f64_retain(0.84).unwrap(),
            Decimal::from(160),
            Decimal::from_f64_retain(0.4).unwrap(),
        );
        assert!(a.inventory_days >= Decimal::from(60));
        assert!(a.trapped_cash >= Decimal::from(19000));
        assert!(a.guidance.contains("days of demand"));
        let b = sourcing_flow_cost(
            "Supplier B",
            Decimal::from_f64_retain(2.03).unwrap(),
            Decimal::from(2000),
            21,
            Decimal::from_f64_retain(0.98).unwrap(),
            Decimal::from(160),
            Decimal::from_f64_retain(0.1).unwrap(),
        );
        // The "cheaper" option traps far more cash.
        assert!(a.trapped_cash > b.trapped_cash * Decimal::from(4));
        assert!(a.inventory_days > b.inventory_days * Decimal::from(2));
    }

    #[test]
    fn variability_drives_shortage_risk() {
        let stable = sourcing_flow_cost(
            "Stable",
            Decimal::from(2),
            Decimal::from(1000),
            14,
            Decimal::from_f64_retain(0.9).unwrap(),
            Decimal::from(100),
            Decimal::from_f64_retain(0.1).unwrap(),
        );
        let wild = sourcing_flow_cost(
            "Wild",
            Decimal::from(2),
            Decimal::from(1000),
            14,
            Decimal::from_f64_retain(0.98).unwrap(),
            Decimal::from(100),
            Decimal::from_f64_retain(0.6).unwrap(),
        );
        assert!(wild.shortage_risk > stable.shortage_risk);
        assert!(wild.guidance.contains("VARIABILITY"));
    }

    #[test]
    fn finance_waste_totals() {
        let s = finance_waste(
            Decimal::from(5000), // WIP cash
            Decimal::from(3000), // aging
            Decimal::from(500),  // scrap
            Decimal::from(400),  // rework
            Decimal::from(900),  // premium freight
            Decimal::from(600),  // expediting
            BatchPolicyInput {
                excess_days: Decimal::from(5),
                daily_demand: Decimal::from(100),
                unit_cost: Decimal::from(10),
            }, // batch: 5000
        );
        assert_eq!(s.lines.len(), 7);
        assert_eq!(s.total_waste_annual, Decimal::from(15400));
        let wip = s.lines.iter().find(|l| l.key == "wip_cash").unwrap();
        assert_eq!(wip.value, Decimal::from(5000));
    }
}
