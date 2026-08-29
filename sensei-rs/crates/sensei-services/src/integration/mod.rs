//! Legacy-system interoperability (full interoperability, not a fork):
//! Sensei is the system of record; the legacy PHP systems (starzERP:
//! Symfony ERP — articles, customers, sales orders, stock movements,
//! suppliers; CRM-v2: Symfony CRM — leads, companies, contacts, quotes,
//! RFQs) KEEP RUNNING and feed Sensei through a versioned import API.
//!
//! Every imported record maps deterministically and IDEMPOTENTLY through
//! `integration_entity_map` (migration 095): the same legacy id can never
//! create a duplicate Sensei entity. The mappers are pure functions over
//! the legacy payload shapes (their Doctrine JSON), so they are fully
//! testable without the legacy databases.

use rust_decimal::Decimal;
use serde_json::Value;

/// One legacy record to import, in the legacy system's OWN JSON shape.
#[derive(Debug, Clone)]
pub struct LegacyRecord {
    /// 'starzerp' | 'crm_v2'
    pub system: String,
    /// 'article', 'customer', 'sales_order', 'stock_movement', 'supplier',
    /// 'lead', 'company', 'contact', 'quote', 'rfq'
    pub entity: String,
    /// The legacy row's id (string — legacy systems use int ids).
    pub legacy_id: String,
    /// The legacy payload (its Doctrine/JSON shape).
    pub payload: Value,
}

/// A canonical Sensei entity produced by a mapper.
#[derive(Debug, Clone)]
pub enum CanonicalEntity {
    Product(CanonicalProduct),
    Account(CanonicalAccount),
    Contact(CanonicalContact),
    SalesOrder(CanonicalSalesOrder),
    StockMove(CanonicalStockMove),
    Supplier(CanonicalSupplier),
    Lead(CanonicalLead),
    Quote(CanonicalQuote),
    Rfq(CanonicalRfq),
}

#[derive(Debug, Clone)]
pub struct CanonicalProduct {
    pub sku: String,
    pub name: String,
    pub description: Option<String>,
    pub unit_of_measure: String,
    pub standard_cost: Option<Decimal>,
    pub selling_price: Option<Decimal>,
}

#[derive(Debug, Clone)]
pub struct CanonicalAccount {
    pub name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
    pub country: Option<String>,
    pub legacy_reference: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalContact {
    pub account_id: Option<String>,
    pub first_name: String,
    pub last_name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalSalesOrder {
    pub order_number: String,
    pub customer_name: String,
    pub status: String,
    pub currency: String,
    pub line_items: Vec<CanonicalSalesOrderItem>,
    pub total_amount: Decimal,
    pub delivery_date: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalSalesOrderItem {
    pub product_sku: String,
    pub quantity: i64,
    pub unit_price: Decimal,
}

#[derive(Debug, Clone)]
pub struct CanonicalStockMove {
    pub product_sku: String,
    pub quantity: i64,
    pub move_type: String, // in | out | transfer
    pub reference: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalSupplier {
    pub name: String,
    pub email: Option<String>,
    pub phone: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalLead {
    pub company_name: String,
    pub website: Option<String>,
    pub sector_tags: Vec<String>,
    pub fit_signals: Vec<String>,
    pub quality_stack: Vec<String>,
    pub lead_score: Option<i64>,
    pub review_status: Option<String>,
}

#[derive(Debug, Clone)]
pub struct CanonicalQuote {
    pub quote_number: String,
    pub company_name: String,
    pub status: String,
    pub currency: String,
    pub total_cost: Decimal,
    pub lines: Vec<CanonicalQuoteLine>,
}

#[derive(Debug, Clone)]
pub struct CanonicalQuoteLine {
    pub part_number: String,
    pub quantity: i64,
    pub unit_price: Decimal,
}

#[derive(Debug, Clone)]
pub struct CanonicalRfq {
    pub rfq_number: String,
    pub company_name: String,
    pub status: String,
    pub lines: Vec<CanonicalRfqLine>,
}

#[derive(Debug, Clone)]
pub struct CanonicalRfqLine {
    pub part_number: String,
    pub quantity: i64,
}

/// Field helpers over the legacy payload (their JSON shapes are
/// snake_case or camelCase depending on the serializer).
fn get_str(payload: &Value, keys: &[&str]) -> Option<String> {
    for k in keys {
        if let Some(v) = payload.get(k) {
            if let Some(s) = v.as_str() {
                if !s.is_empty() {
                    return Some(s.to_string());
                }
            }
        }
    }
    None
}

fn get_i64(payload: &Value, keys: &[&str]) -> Option<i64> {
    for k in keys {
        if let Some(v) = payload.get(k) {
            if let Some(i) = v.as_i64() {
                return Some(i);
            }
            if let Some(s) = v.as_str() {
                if let Ok(i) = s.parse::<i64>() {
                    return Some(i);
                }
            }
        }
    }
    None
}

fn get_decimal(payload: &Value, keys: &[&str]) -> Option<Decimal> {
    for k in keys {
        if let Some(v) = payload.get(k) {
            if let Some(n) = v.as_f64() {
                return Decimal::from_f64_retain(n);
            }
            if let Some(s) = v.as_str() {
                if let Ok(d) = s.parse::<Decimal>() {
                    return Some(d);
                }
            }
        }
    }
    None
}

fn get_string_array(payload: &Value, keys: &[&str]) -> Vec<String> {
    for k in keys {
        if let Some(arr) = payload.get(k).and_then(|v| v.as_array()) {
            return arr
                .iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect();
        }
    }
    Vec::new()
}

/// Map an erpStarz Article payload onto a canonical Product.
pub fn map_starz_article(payload: &Value) -> Result<CanonicalProduct, String> {
    let sku = get_str(payload, &["codeReference", "code_reference", "sku"])
        .ok_or_else(|| "starzERP article missing codeReference".to_string())?;
    let name =
        get_str(payload, &["description", "name", "designation"]).unwrap_or_else(|| sku.clone());
    Ok(CanonicalProduct {
        sku,
        name: name.clone(),
        description: get_str(payload, &["longDescription", "long_description"]),
        unit_of_measure: get_str(payload, &["unit", "unitOfMeasure", "unite"])
            .unwrap_or_else(|| "pcs".to_string()),
        standard_cost: get_decimal(payload, &["costPrice", "cost_price"]),
        selling_price: get_decimal(payload, &["price", "sellingPrice", "prix"]),
    })
}

/// Map an erpStarz Customer payload onto a canonical Account + Contact.
pub fn map_starz_customer(
    payload: &Value,
) -> Result<(CanonicalAccount, Option<CanonicalContact>), String> {
    let name = get_str(payload, &["name", "companyName", "raisonSociale"])
        .ok_or_else(|| "starzERP customer missing name".to_string())?;
    let account = CanonicalAccount {
        name: name.clone(),
        email: get_str(payload, &["legacyEmail", "email"]),
        phone: get_str(payload, &["legacyPhone", "phone"]),
        country: get_str(payload, &["country", "pays"]),
        legacy_reference: get_str(payload, &["vendorId", "clientId"]),
    };
    let contact = get_str(payload, &["legacyContactName", "contactName"]).map(|cn| {
        let parts: Vec<&str> = cn.splitn(2, ' ').collect();
        CanonicalContact {
            account_id: None,
            first_name: parts.first().copied().unwrap_or("").to_string(),
            last_name: parts.get(1).copied().unwrap_or("").to_string(),
            email: account.email.clone(),
            phone: account.phone.clone(),
        }
    });
    Ok((account, contact))
}

/// Map a CRM-v2 Lead payload onto a canonical Lead (which becomes an
/// Account + Opportunity in Sensei).
pub fn map_crm_lead(payload: &Value) -> Result<CanonicalLead, String> {
    let company = get_str(
        payload,
        &["companyName", "company_name", "legalName", "legal_name"],
    )
    .ok_or_else(|| "CRM-v2 lead missing companyName".to_string())?;
    Ok(CanonicalLead {
        company_name: company,
        website: get_str(
            payload,
            &["websiteRoot", "website_root", "leadUrl", "lead_url"],
        ),
        sector_tags: get_string_array(payload, &["sectorTags", "sector_tags"]),
        fit_signals: get_string_array(payload, &["fitSignals", "fit_signals"])
            .into_iter()
            .filter(|s| s == "true")
            .collect(),
        quality_stack: get_string_array(payload, &["qualityStack", "quality_stack"]),
        lead_score: get_i64(payload, &["leadScore", "lead_score"]),
        review_status: get_str(payload, &["reviewStatus", "review_status"]),
    })
}

/// Map a CRM-v2 Quote payload onto a canonical Quote.
pub fn map_crm_quote(payload: &Value) -> Result<CanonicalQuote, String> {
    let quote_number = get_str(payload, &["quoteNumber", "quote_number"])
        .ok_or_else(|| "CRM-v2 quote missing quoteNumber".to_string())?;
    let company = get_str(payload, &["issuingCompany", "issuing_company"])
        .unwrap_or_else(|| "unknown".to_string());
    let lines = payload
        .get("partBreakdowns")
        .or_else(|| payload.get("part_breakdowns"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|line| {
                    let part = get_str(line, &["partNumber", "part_number", "mpn"])?;
                    let qty = get_i64(line, &["quantity", "qty"]).unwrap_or(0);
                    let price =
                        get_decimal(line, &["unitPrice", "unit_price"]).unwrap_or(Decimal::ZERO);
                    Some(CanonicalQuoteLine {
                        part_number: part,
                        quantity: qty,
                        unit_price: price,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    Ok(CanonicalQuote {
        quote_number,
        company_name: company,
        status: get_str(payload, &["status"]).unwrap_or_else(|| "draft".to_string()),
        currency: get_str(payload, &["currency"]).unwrap_or_else(|| "USD".to_string()),
        total_cost: get_decimal(payload, &["totalCost", "total_cost"]).unwrap_or(Decimal::ZERO),
        lines,
    })
}

/// Map a CRM-v2 RFQ payload onto a canonical RFQ.
pub fn map_crm_rfq(payload: &Value) -> Result<CanonicalRfq, String> {
    let rfq_number = get_str(payload, &["rfqNumber", "rfq_number", "number", "reference"])
        .ok_or_else(|| "CRM-v2 RFQ missing number".to_string())?;
    let lines = payload
        .get("lineItems")
        .or_else(|| payload.get("line_items"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|line| {
                    let part = get_str(line, &["partNumber", "part_number", "mpn"])?;
                    let qty = get_i64(line, &["quantity", "qty"]).unwrap_or(0);
                    Some(CanonicalRfqLine {
                        part_number: part,
                        quantity: qty,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    Ok(CanonicalRfq {
        rfq_number,
        company_name: get_str(payload, &["companyName", "company_name"]).unwrap_or_default(),
        status: get_str(payload, &["status"]).unwrap_or_else(|| "open".to_string()),
        lines,
    })
}

/// Map an erpStarz SalesOrder payload onto a canonical SalesOrder.
pub fn map_starz_sales_order(payload: &Value) -> Result<CanonicalSalesOrder, String> {
    let order_number = get_str(
        payload,
        &["orderNumber", "order_number", "number", "numBon"],
    )
    .ok_or_else(|| "starzERP sales order missing number".to_string())?;
    let items = payload
        .get("orderItems")
        .or_else(|| payload.get("order_items"))
        .or_else(|| payload.get("items"))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|line| {
                    let sku = get_str(line, &["article", "articleCode", "codeReference", "sku"])?;
                    let qty = get_i64(line, &["quantity", "qty", "quantite"]).unwrap_or(0);
                    let price = get_decimal(line, &["unitPrice", "unit_price", "price"])
                        .unwrap_or(Decimal::ZERO);
                    Some(CanonicalSalesOrderItem {
                        product_sku: sku,
                        quantity: qty,
                        unit_price: price,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    let total = get_decimal(
        payload,
        &["totalAmount", "total_amount", "total", "montant"],
    )
    .unwrap_or_else(|| {
        items
            .iter()
            .map(|i| i.unit_price * Decimal::from(i.quantity))
            .sum()
    });
    Ok(CanonicalSalesOrder {
        order_number,
        customer_name: get_str(payload, &["customer", "customerName", "client"])
            .unwrap_or_default(),
        status: get_str(payload, &["status", "etat"]).unwrap_or_else(|| "pending".to_string()),
        currency: get_str(payload, &["currency", "devise"]).unwrap_or_else(|| "MAD".to_string()),
        line_items: items,
        total_amount: total,
        delivery_date: get_str(payload, &["deliveryDate", "delivery_date"]),
    })
}

/// Map an erpStarz StockMovement payload onto a canonical StockMove.
pub fn map_starz_stock_move(payload: &Value) -> Result<CanonicalStockMove, String> {
    let sku = get_str(payload, &["article", "articleCode", "codeReference", "sku"])
        .ok_or_else(|| "starzERP stock movement missing article".to_string())?;
    let quantity = get_i64(payload, &["quantity", "qty", "quantite"]).unwrap_or(0);
    let move_type = match get_str(payload, &["type", "mouvement", "direction"])
        .unwrap_or_default()
        .to_lowercase()
        .as_str()
    {
        "in" | "entree" | "reception" | "receive" => "in",
        "out" | "sortie" | "expedition" | "ship" => "out",
        "transfer" | "transfert" => "transfer",
        _ => "in",
    }
    .to_string();
    Ok(CanonicalStockMove {
        product_sku: sku,
        quantity,
        move_type,
        reference: get_str(payload, &["reference", "referenceNumber", "numBon"]),
    })
}

/// Map an erpStarz Supplier payload onto a canonical Supplier.
pub fn map_starz_supplier(payload: &Value) -> Result<CanonicalSupplier, String> {
    let name = get_str(payload, &["name", "companyName", "raisonSociale", "nom"])
        .ok_or_else(|| "starzERP supplier missing name".to_string())?;
    Ok(CanonicalSupplier {
        name,
        email: get_str(payload, &["email", "legacyEmail"]),
        phone: get_str(payload, &["phone", "legacyPhone", "telephone"]),
    })
}

/// Dispatch a legacy record to the right mapper.
pub fn map_record(record: &LegacyRecord) -> Result<CanonicalEntity, String> {
    match (record.system.as_str(), record.entity.as_str()) {
        ("starzerp", "article") => map_starz_article(&record.payload).map(CanonicalEntity::Product),
        ("starzerp", "customer") => {
            map_starz_customer(&record.payload).map(|(a, _c)| CanonicalEntity::Account(a))
        }
        ("starzerp", "sales_order") => {
            map_starz_sales_order(&record.payload).map(CanonicalEntity::SalesOrder)
        }
        ("starzerp", "stock_movement") => {
            map_starz_stock_move(&record.payload).map(CanonicalEntity::StockMove)
        }
        ("starzerp", "supplier") => {
            map_starz_supplier(&record.payload).map(CanonicalEntity::Supplier)
        }
        ("crm_v2", "lead") => map_crm_lead(&record.payload).map(CanonicalEntity::Lead),
        ("crm_v2", "quote") => map_crm_quote(&record.payload).map(CanonicalEntity::Quote),
        ("crm_v2", "rfq") => map_crm_rfq(&record.payload).map(CanonicalEntity::Rfq),
        ("crm_v2", "company") => {
            map_starz_customer(&record.payload).map(|(a, _c)| CanonicalEntity::Account(a))
        }
        ("crm_v2", "contact") => {
            let first = get_str(&record.payload, &["firstName", "first_name"]).unwrap_or_default();
            let last = get_str(&record.payload, &["lastName", "last_name"]).unwrap_or_default();
            if first.is_empty() && last.is_empty() {
                return Err("CRM-v2 contact missing name".to_string());
            }
            Ok(CanonicalEntity::Contact(CanonicalContact {
                account_id: get_str(&record.payload, &["company", "companyId"]),
                first_name: first,
                last_name: last,
                email: get_str(&record.payload, &["email"]),
                phone: get_str(&record.payload, &["phone"]),
            }))
        }
        other => Err(format!("Unsupported legacy record {other:?}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn starz_article_maps_to_product() {
        let payload = json!({
            "id": 42,
            "codeReference": "PCB-100",
            "description": "Controller PCB",
            "costPrice": "12.50",
            "price": "19.99",
            "unit": "pcs"
        });
        let rec = LegacyRecord {
            system: "starzerp".to_string(),
            entity: "article".to_string(),
            legacy_id: "42".to_string(),
            payload,
        };
        let CanonicalEntity::Product(p) = map_record(&rec).unwrap() else {
            panic!("expected product");
        };
        assert_eq!(p.sku, "PCB-100");
        assert_eq!(p.standard_cost.unwrap().to_string(), "12.50");
        assert_eq!(p.selling_price.unwrap().to_string(), "19.99");
    }

    #[test]
    fn starz_sales_order_maps_with_lines() {
        let payload = json!({
            "orderNumber": "BC-2026-0150",
            "customer": "Starz Automotive",
            "status": "confirmed",
            "currency": "MAD",
            "orderItems": [
                {"article": "PCB-100", "quantity": 50, "unitPrice": "18.00"},
                {"article": "CBL-07", "quantity": 25, "unitPrice": "3.50"}
            ]
        });
        let rec = LegacyRecord {
            system: "starzerp".to_string(),
            entity: "sales_order".to_string(),
            legacy_id: "150".to_string(),
            payload,
        };
        let CanonicalEntity::SalesOrder(so) = map_record(&rec).unwrap() else {
            panic!("expected sales order");
        };
        assert_eq!(so.line_items.len(), 2);
        assert_eq!(so.total_amount.to_string(), "987.50");
    }

    #[test]
    fn crm_lead_maps_sector_and_quality() {
        let payload = json!({
            "id": 7,
            "companyName": "Acme Aerospace",
            "websiteRoot": "acme.example",
            "sectorTags": ["aerospace", "defense"],
            "fitSignals": {"pcba": true, "smt": true},
            "qualityStack": ["AS9100", "IATF 16949"],
            "leadScore": 87,
            "reviewStatus": "approved"
        });
        let rec = LegacyRecord {
            system: "crm_v2".to_string(),
            entity: "lead".to_string(),
            legacy_id: "7".to_string(),
            payload,
        };
        let CanonicalEntity::Lead(l) = map_record(&rec).unwrap() else {
            panic!("expected lead");
        };
        assert_eq!(l.company_name, "Acme Aerospace");
        assert_eq!(l.sector_tags, vec!["aerospace", "defense"]);
        assert_eq!(l.quality_stack, vec!["AS9100", "IATF 16949"]);
        assert_eq!(l.lead_score, Some(87));
    }

    #[test]
    fn crm_quote_maps_breakdown_lines() {
        let payload = json!({
            "quoteNumber": "QTE-2026-001",
            "status": "approved",
            "currency": "USD",
            "totalCost": "1250.00",
            "partBreakdowns": [
                {"partNumber": "MPN-1", "quantity": 100, "unitPrice": "8.00"},
                {"partNumber": "MPN-2", "quantity": 50, "unitPrice": "9.00"}
            ]
        });
        let rec = LegacyRecord {
            system: "crm_v2".to_string(),
            entity: "quote".to_string(),
            legacy_id: "1".to_string(),
            payload,
        };
        let CanonicalEntity::Quote(q) = map_record(&rec).unwrap() else {
            panic!("expected quote");
        };
        assert_eq!(q.lines.len(), 2);
        assert_eq!(q.total_cost.to_string(), "1250.00");
    }

    #[test]
    fn unknown_system_rejected() {
        let rec = LegacyRecord {
            system: "nope".to_string(),
            entity: "article".to_string(),
            legacy_id: "1".to_string(),
            payload: json!({}),
        };
        assert!(map_record(&rec).is_err());
    }
}
