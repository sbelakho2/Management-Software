//! Quoting Helper route handlers.
//!
//! Manages the Stage-Gate workflow for Request for Quotations (RFQs),
//! including workpacket generation, cost building, NPI conversion,
//! and AI-powered clarifications and quote memory retrieval.

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    Json,
};
use chrono::{DateTime, Utc};
use sensei_auth::middleware::AuthenticatedUser;
use sensei_core::error::{Result, SenseiError};
use sensei_core::pagination::{PaginatedResponse, PaginationParams};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::state::AppState;
use crate::stores;

// ── Request DTOs ────────────────────────────────────────────────────────────

/// Request body for generating work packets.
#[derive(Debug, Deserialize)]
pub struct GenerateWorkPacketsRequest {
    /// Line item IDs to include in the work packets.
    pub line_items: Vec<Uuid>,
    /// Optional template ID for the work packets.
    pub template_id: Option<Uuid>,
}

/// Request body for updating a work packet.
#[derive(Debug, Deserialize)]
pub struct UpdateWorkPacketRequest {
    /// New status for the work packet.
    pub status: Option<String>,
    /// Updated estimated hours.
    pub estimated_hours: Option<f64>,
    /// Notes or comments for the update.
    pub notes: Option<String>,
}

/// A single document to ingest for an RFQ.
#[derive(Debug, Deserialize)]
pub struct DocumentInput {
    /// Document type (e.g., "pdf", "xlsx", "dxf").
    #[serde(rename = "type")]
    pub doc_type: String,
    /// Base64-encoded content.
    pub content: String,
    /// Original filename.
    pub filename: String,
}

/// Request body for ingesting RFQ documents.
#[derive(Debug, Deserialize)]
pub struct IngestRfqRequest {
    /// Documents to ingest.
    pub documents: Vec<DocumentInput>,
}

/// Request body for building quote cost.
#[derive(Debug, Deserialize)]
pub struct BuildCostRequest {
    /// Material costs as a map (e.g., {"steel": 150.0, "fasteners": 25.0}).
    pub material_costs: serde_json::Value,
    /// Labor costs as a map (e.g., {"machining": 300.0, "assembly": 200.0}).
    pub labor_costs: serde_json::Value,
    /// Overhead percentage to apply.
    pub overhead_percentage: f64,
    /// Margin percentage to apply.
    pub margin_percentage: f64,
}

// ── Response DTOs ──────────────────────────────────────────────────────────

/// A work packet operation within an RFQ work packet.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkPacketOperationDto {
    /// Name of the operation.
    pub operation: String,
    /// Estimated hours for this operation.
    pub estimated_hours: f64,
}

/// Response body for a work packet.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkPacketResponse {
    /// Work packet ID.
    pub id: Uuid,
    /// RFQ ID this packet belongs to.
    pub rfq_id: Uuid,
    /// Line items included in the packet.
    pub line_items: Vec<Uuid>,
    /// Template ID used (if any).
    pub template_id: Option<Uuid>,
    /// Current status of the work packet.
    pub status: String,
    /// Operations in this work packet.
    pub workpackets: Vec<WorkPacketOperationDto>,
    /// Estimated hours (overall).
    pub estimated_hours: Option<f64>,
    /// Notes on the work packet.
    pub notes: Option<String>,
    /// When the packet was created.
    pub created_at: DateTime<Utc>,
    /// When the packet was last updated.
    pub updated_at: DateTime<Utc>,
}

/// Response body for an RFQ ingestion.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IngestionResponse {
    /// Ingestion job ID.
    pub id: Uuid,
    /// RFQ ID the documents were ingested for.
    pub rfq_id: Uuid,
    /// Current status of the ingestion.
    pub status: String,
    /// Number of documents ingested.
    pub documents_ingested: usize,
    /// When the ingestion job was created.
    pub created_at: DateTime<Utc>,
}

/// Response body for a cost build.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostBuildResponse {
    /// Cost build ID.
    pub id: Uuid,
    /// Quote ID this cost build belongs to.
    pub quote_id: Uuid,
    /// Total calculated cost.
    pub total_cost: f64,
    /// Selling price (cost + margin).
    pub selling_price: f64,
    /// Profit margin amount.
    pub margin: f64,
    /// Detailed cost breakdown.
    pub breakdown: serde_json::Value,
    /// When the cost build was created.
    pub created_at: DateTime<Utc>,
}

/// Response body for an NPI conversion.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NpiConversionResponse {
    /// The generated NPI project ID.
    pub npi_project_id: Uuid,
    /// The source quote ID.
    pub quote_id: Uuid,
    /// Current conversion status.
    pub status: String,
    /// When the conversion occurred.
    pub converted_at: DateTime<Utc>,
}

/// A single clarification suggestion from AI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClarificationItem {
    /// The clarification question.
    pub question: String,
    /// The context/section reference.
    pub context: String,
}

/// Response body for AI-suggested clarifications.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClarificationResponse {
    /// RFQ ID the clarifications are for.
    pub rfq_id: Uuid,
    /// List of suggested clarifications.
    pub clarifications: Vec<ClarificationItem>,
}

/// A similar quote from AI quote memory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimilarQuote {
    /// The similar quote's ID.
    pub quote_id: Uuid,
    /// Semantic similarity score (0.0 – 1.0).
    pub similarity_score: f64,
}

/// Historical pricing data from AI quote memory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoricalPricing {
    /// Average margin percentage from similar quotes.
    pub avg_margin: f64,
    /// Margin range [min, max].
    pub range: Vec<f64>,
}

/// Response body for AI quote memory retrieval.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuoteMemoryResponse {
    /// RFQ ID the memory was retrieved for.
    pub rfq_id: Uuid,
    /// List of similar quotes found.
    pub similar_quotes: Vec<SimilarQuote>,
    /// Historical pricing data.
    pub historical_pricing: HistoricalPricing,
    /// Notes from similar past quotes.
    pub notes: String,
}

// ── Mapping helpers ────────────────────────────────────────────────────────

impl From<stores::WorkPacket> for WorkPacketResponse {
    fn from(wp: stores::WorkPacket) -> Self {
        Self {
            id: wp.id,
            rfq_id: wp.rfq_id,
            line_items: wp.line_items,
            template_id: wp.template_id,
            status: wp.status,
            workpackets: wp
                .workpackets
                .into_iter()
                .map(|op| WorkPacketOperationDto {
                    operation: op.operation,
                    estimated_hours: op.estimated_hours,
                })
                .collect(),
            estimated_hours: wp.estimated_hours,
            notes: wp.notes,
            created_at: wp.created_at,
            updated_at: wp.updated_at,
        }
    }
}

impl From<stores::CostBuild> for CostBuildResponse {
    fn from(cb: stores::CostBuild) -> Self {
        Self {
            id: cb.id,
            quote_id: cb.quote_id,
            total_cost: cb.total_cost,
            selling_price: cb.selling_price,
            margin: cb.margin,
            breakdown: cb.breakdown,
            created_at: cb.created_at,
        }
    }
}

impl From<stores::NpiConversion> for NpiConversionResponse {
    fn from(nc: stores::NpiConversion) -> Self {
        Self {
            npi_project_id: nc.npi_project_id,
            quote_id: nc.quote_id,
            status: nc.status,
            converted_at: nc.converted_at,
        }
    }
}

// ── Handlers ───────────────────────────────────────────────────────────────

/// Deterministic discipline-based hour estimation table.
///
/// Each engineering discipline that must review a quoted line item gets a
/// standard estimate in hours. The values are documented planning standards
/// used for quoting work packets:
///
/// | Discipline            | Hours |
/// |-----------------------|-------|
/// | Engineering Review    | 4.5   |
/// | Mechanical            | 6.0   |
/// | Electrical            | 5.0   |
/// | Embedded              | 7.0   |
/// | Quality               | 3.0   |
/// | Purchasing            | 2.0   |
const DISCIPLINE_HOURS: &[(&str, f64)] = &[
    ("Engineering Review", 4.5),
    ("Mechanical", 6.0),
    ("Electrical", 5.0),
    ("Embedded", 7.0),
    ("Quality", 3.0),
    ("Purchasing", 2.0),
];

/// Generate work packets for an RFQ.
///
/// Creates one work packet containing the full discipline-based operation
/// set for every requested line item. The RFQ must exist and every requested
/// line item must belong to it.
pub async fn generate_work_packets(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
    Json(req): Json<GenerateWorkPacketsRequest>,
) -> Result<(StatusCode, Json<WorkPacketResponse>)> {
    let tenant_id = user.tenant_id;

    // The RFQ must exist and own the requested line items.
    let rfq = state
        .supply_chain_service
        .get_rfq(tenant_id, rfq_id)
        .await?;
    let known_item_ids: Vec<Uuid> = rfq.items.iter().filter_map(|i| i.line_item_id).collect();
    for item_id in &req.line_items {
        if !known_item_ids.contains(item_id) {
            return Err(SenseiError::Validation(format!(
                "Line item {item_id} does not belong to RFQ {rfq_id}"
            )));
        }
    }

    // Build the discipline operations once, then repeat them per line item
    // so every quoted position is covered by the full review set.
    let now = Utc::now();
    let mut workpackets: Vec<stores::WorkPacketOperation> = Vec::new();
    let mut estimated_hours = 0.0;
    for _line_item in &req.line_items {
        for (discipline, hours) in DISCIPLINE_HOURS {
            workpackets.push(stores::WorkPacketOperation {
                operation: discipline.to_string(),
                estimated_hours: *hours,
            });
            estimated_hours += hours;
        }
    }

    let packet = stores::WorkPacket {
        id: Uuid::new_v4(),
        rfq_id,
        tenant_id,
        line_items: req.line_items,
        template_id: req.template_id,
        status: "generated".to_string(),
        workpackets,
        notes: None,
        estimated_hours: Some(estimated_hours),
        created_by: user.user_id,
        created_at: now,
        updated_at: now,
    };

    state
        .work_packets
        .write()
        .await
        .insert(packet.id, packet.clone());

    Ok((StatusCode::CREATED, Json(WorkPacketResponse::from(packet))))
}

/// List work packets for an RFQ.
///
/// Returns a paginated list of work packets associated with the given RFQ.
pub async fn list_work_packets(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
    Query(params): Query<PaginationParams>,
) -> Result<Json<PaginatedResponse<WorkPacketResponse>>> {
    let packets: Vec<WorkPacketResponse> = state
        .work_packets
        .read()
        .await
        .values()
        .filter(|wp| wp.rfq_id == rfq_id && wp.tenant_id == user.tenant_id)
        .cloned()
        .map(WorkPacketResponse::from)
        .collect();

    Ok(Json(PaginatedResponse::new(
        packets,
        params.page,
        params.per_page,
    )))
}

/// Update a work packet.
///
/// Updates the status, estimated hours, and/or notes of a work packet.
/// Returns 404 if the packet does not exist.
pub async fn update_work_packet(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(packet_id): Path<Uuid>,
    Json(req): Json<UpdateWorkPacketRequest>,
) -> Result<Json<WorkPacketResponse>> {
    let mut store = state.work_packets.write().await;
    let packet = store
        .get_mut(&packet_id)
        .ok_or_else(|| SenseiError::NotFound(format!("Work packet {packet_id} not found")))?;

    if packet.tenant_id != user.tenant_id {
        return Err(SenseiError::Forbidden(
            "Access denied to this work packet".to_string(),
        ));
    }

    if let Some(status) = req.status {
        packet.status = status;
    }
    if let Some(hours) = req.estimated_hours {
        packet.estimated_hours = Some(hours);
    }
    if let Some(notes) = req.notes {
        packet.notes = Some(notes);
    }
    packet.updated_at = Utc::now();

    Ok(Json(WorkPacketResponse::from(packet.clone())))
}

/// Minimal standard-base64 decoder (RFC 4648, with `=` padding).
///
/// Kept local because the API crate does not depend on a base64 crate.
fn base64_decode(input: &str) -> std::result::Result<Vec<u8>, String> {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = Vec::with_capacity(input.len() / 4 * 3 + 3);
    let bytes = input.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let mut vals = [0u32; 4];
        let mut pad = 0;
        for k in 0..4 {
            if i + k >= bytes.len() || bytes[i + k] == b'=' {
                pad += 1;
            } else {
                vals[k] = TABLE
                    .iter()
                    .position(|&c| c == bytes[i + k])
                    .ok_or_else(|| "invalid base64 character in input".to_string())?
                    as u32;
            }
        }
        let n = (vals[0] << 18) | (vals[1] << 12) | (vals[2] << 6) | vals[3];
        out.push((n >> 16) as u8);
        if pad < 2 {
            out.push((n >> 8) as u8);
        }
        if pad < 1 {
            out.push(n as u8);
        }
        i += 4;
    }
    Ok(out)
}

/// Ingest RFQ documents.
///
/// Decodes each base64 document, persists the raw bytes in the ingestion
/// data store keyed by job id, and completes each job immediately with real
/// metadata (size, sha256, extracted text statistics).
pub async fn ingest_rfq_documents(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
    Json(req): Json<IngestRfqRequest>,
) -> Result<(StatusCode, Json<IngestionResponse>)> {
    use sha2::{Digest, Sha256};

    let tenant_id = user.tenant_id;
    // The RFQ must exist before documents can be ingested against it.
    let _ = state
        .supply_chain_service
        .get_rfq(tenant_id, rfq_id)
        .await?;

    let now = Utc::now();
    let documents_ingested = req.documents.len();
    let mut job_ids: Vec<Uuid> = Vec::with_capacity(documents_ingested);

    for doc in &req.documents {
        let raw = base64_decode(&doc.content).map_err(|e| {
            SenseiError::Validation(format!(
                "Invalid base64 content for '{}': {e}",
                doc.filename
            ))
        })?;

        let job_id = Uuid::new_v4();
        let file_size = raw.len() as i64;
        let sha256 = format!("{:x}", Sha256::digest(&raw));

        // Text statistics for the two directly text-readable formats.
        let text_char_count = match doc.doc_type.to_ascii_lowercase().as_str() {
            "txt" | "csv" | "text" => Some(String::from_utf8_lossy(&raw).chars().count() as u64),
            _ => None,
        };

        let job = stores::IngestionJob {
            id: job_id,
            tenant_id,
            file_name: doc.filename.clone(),
            content_type: doc.doc_type.clone(),
            file_size,
            status: stores::IngestionStatus::Completed,
            extracted_text: None,
            extracted_data: Some(serde_json::json!({
                "sha256": sha256,
                "file_size_bytes": file_size,
                "text_char_count": text_char_count,
                "rfq_id": rfq_id,
                "ingested_via": "quoting_helper",
            })),
            error_message: None,
            created_by: user.user_id,
            created_at: now,
            completed_at: Some(now),
        };
        state.ingestion_jobs.write().await.insert(job_id, job);
        state.ingestion_data.write().await.insert(job_id, raw);
        job_ids.push(job_id);
    }

    let response = IngestionResponse {
        id: job_ids[0],
        rfq_id,
        status: "completed".to_string(),
        documents_ingested,
        created_at: now,
    };

    Ok((StatusCode::CREATED, Json(response)))
}

/// Build cost for a quote.
///
/// Performs a deterministic cost rollup using material costs, labor costs,
/// overhead, and margin to produce a total cost and selling price.
pub async fn build_quote_cost(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(quote_id): Path<Uuid>,
    Json(req): Json<BuildCostRequest>,
) -> Result<(StatusCode, Json<CostBuildResponse>)> {
    let now = Utc::now();

    // Calculate costs from the provided input.
    let material_total: f64 = req
        .material_costs
        .as_object()
        .map(|obj| obj.values().filter_map(|v| v.as_f64()).sum())
        .unwrap_or(0.0);

    let labor_total: f64 = req
        .labor_costs
        .as_object()
        .map(|obj| obj.values().filter_map(|v| v.as_f64()).sum())
        .unwrap_or(0.0);

    let base_cost = material_total + labor_total;
    let overhead = base_cost * (req.overhead_percentage / 100.0);
    let total_cost = base_cost + overhead;
    let margin = total_cost * (req.margin_percentage / 100.0);
    let selling_price = total_cost + margin;

    let breakdown = serde_json::json!({
        "material_subtotal": material_total,
        "labor_subtotal": labor_total,
        "base_cost": base_cost,
        "overhead": {
            "percentage": req.overhead_percentage,
            "amount": overhead,
        },
        "margin": {
            "percentage": req.margin_percentage,
            "amount": margin,
        },
        "total_cost": total_cost,
        "selling_price": selling_price,
    });

    let cost_build = stores::CostBuild {
        id: Uuid::new_v4(),
        quote_id,
        tenant_id: user.tenant_id,
        material_costs: req.material_costs,
        labor_costs: req.labor_costs,
        overhead_percentage: req.overhead_percentage,
        margin_percentage: req.margin_percentage,
        total_cost,
        selling_price,
        margin,
        breakdown,
        created_by: user.user_id,
        created_at: now,
    };

    state
        .cost_builds
        .write()
        .await
        .insert(cost_build.id, cost_build.clone());

    Ok((
        StatusCode::CREATED,
        Json(CostBuildResponse::from(cost_build)),
    ))
}

/// Convert a quote to an NPI (New Product Introduction) project.
///
/// Creates a real [`NpiProject`] through the quality service, populated from
/// the quote's data, and records the conversion link.
pub async fn convert_quote_to_npi(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(quote_id): Path<Uuid>,
) -> Result<(StatusCode, Json<NpiConversionResponse>)> {
    use sensei_services::quality::{NpiProject, NpiStage};

    let tenant_id = user.tenant_id;
    let quote = state
        .supply_chain_service
        .get_quote(tenant_id, quote_id)
        .await?;

    let now = Utc::now();
    let npi_project = NpiProject {
        id: Uuid::new_v4(),
        name: format!("NPI from quote {}", quote.quote_number),
        description: format!(
            "New Product Introduction generated from quote {} for customer {}",
            quote.quote_number, quote.customer_name
        ),
        product_id: quote.line_items.first().map(|li| li.product_id),
        customer_id: Some(quote.customer_id),
        rfq_id: quote.rfq_id,
        quote_id: Some(quote.id),
        current_stage: NpiStage::Intake,
        stage_entered_at: now,
        target_sop_date: None,
        actual_sop_date: None,
        project_manager_id: Some(user.user_id),
        engineering_lead_id: None,
        quality_lead_id: None,
        manufacturing_lead_id: None,
        estimated_annual_volume: quote
            .line_items
            .iter()
            .map(|li| li.quantity.max(0) as u64)
            .sum(),
        estimated_unit_cost: 0.0,
        estimated_investment: 0.0,
        is_active: true,
        priority: 0,
        health_status: "OnTrack".to_string(),
        health_notes: String::new(),
        created_at: now,
        updated_at: now,
        created_by: user.user_id,
    };

    let created = state
        .quality_service
        .create_npi_project(tenant_id, npi_project)
        .await?;

    let conversion = stores::NpiConversion {
        id: Uuid::new_v4(),
        npi_project_id: created.id,
        quote_id,
        tenant_id,
        status: "converted".to_string(),
        converted_at: now,
        created_by: user.user_id,
    };

    state
        .npi_conversions
        .write()
        .await
        .insert(conversion.id, conversion.clone());

    Ok((
        StatusCode::CREATED,
        Json(NpiConversionResponse::from(conversion)),
    ))
}

/// Get AI-suggested clarifications for an RFQ.
///
/// Only questions for data that is actually missing from the RFQ are
/// suggested: missing target prices per line item, and RFQ-level details
/// (packaging/lead time/compliance) when the notes are empty. Questions are
/// never fabricated for fields the RFQ already carries.
pub async fn suggest_clarifications(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
) -> Result<Json<ClarificationResponse>> {
    let tenant_id = user.tenant_id;
    let rfq = state
        .supply_chain_service
        .get_rfq(tenant_id, rfq_id)
        .await?;

    let mut clarifications = Vec::new();

    // No line items → ask for the product list and its specifications.
    if rfq.items.is_empty() {
        clarifications.push(ClarificationItem {
            question: "No line items are listed. Which products/quantities should this RFQ cover?"
                .to_string(),
            context: "Line Items".to_string(),
        });
    }

    // Missing target price per line item.
    for (idx, item) in rfq.items.iter().enumerate() {
        let line_label = if rfq.items.len() > 1 {
            format!("Line Item {} – {}", idx + 1, item.product_name)
        } else {
            format!("{} – Product Details", item.product_name)
        };

        if item.target_price.is_none() {
            clarifications.push(ClarificationItem {
                question: format!(
                    "What is the target unit price for {} (qty {})?",
                    item.product_name, item.quantity
                ),
                context: line_label.clone(),
            });
        }
        if item.unit_of_measure.trim().is_empty() {
            clarifications.push(ClarificationItem {
                question: format!("What unit of measure applies to {}?", item.product_name),
                context: line_label.clone(),
            });
        }
    }

    // RFQ-level requirements are only in the notes; when absent, ask.
    if rfq.notes.trim().is_empty() {
        clarifications.push(ClarificationItem {
            question: "Are there any special packaging, labeling, or delivery requirements?"
                .to_string(),
            context: "RFQ General Requirements".to_string(),
        });
        clarifications.push(ClarificationItem {
            question: "What is the required lead time for first article samples and production quantities?".to_string(),
            context: "Delivery Schedule".to_string(),
        });
        clarifications.push(ClarificationItem {
            question: "Are there any regulatory or compliance certifications required (e.g., ISO, AS9100, IATF 16949)?".to_string(),
            context: "Compliance & Certifications".to_string(),
        });
    }

    Ok(Json(ClarificationResponse {
        rfq_id,
        clarifications,
    }))
}

/// Retrieve AI quote memory for an RFQ.
///
/// Queries historical quotes from the supply chain service to find
/// similar quotes based on product overlap, then computes aggregate
/// pricing statistics from the quotes' own pricing fields.
pub async fn retrieve_quote_memory(
    user: AuthenticatedUser,
    State(state): State<AppState>,
    Path(rfq_id): Path<Uuid>,
) -> Result<Json<QuoteMemoryResponse>> {
    let tenant_id = user.tenant_id;

    // The RFQ must exist; its products define the similarity target.
    let rfq = state
        .supply_chain_service
        .get_rfq(tenant_id, rfq_id)
        .await?;

    let rfq_product_ids: Vec<Uuid> = rfq.items.iter().map(|i| i.product_id).collect();
    let has_product_basis = !rfq_product_ids.is_empty();

    // Fetch historical quotes for this tenant (page through everything).
    let mut similar_quotes: Vec<SimilarQuote> = Vec::new();
    let mut margins: Vec<f64> = Vec::new();
    let mut notes_parts: Vec<String> = Vec::new();

    let mut page = 1usize;
    loop {
        let quotes_page = state
            .supply_chain_service
            .list_quotes(tenant_id, None, Some(page), Some(100))
            .await?;
        let fetched = quotes_page.data.len();

        for quote in &quotes_page.data {
            // Skip the quote if it's for the same RFQ (avoid self-reference).
            if quote.rfq_id == Some(rfq_id) {
                continue;
            }

            // Similarity is the fraction of the RFQ's products present in the
            // quote's line items. Without any RFQ products there is no
            // product-overlap basis, so the quote scores zero (no fabricated
            // fallback scores).
            let overlap = if has_product_basis {
                quote
                    .line_items
                    .iter()
                    .filter(|li| rfq_product_ids.contains(&li.product_id))
                    .count()
            } else {
                0
            };
            let similarity_score = if has_product_basis {
                overlap as f64 / rfq_product_ids.len() as f64
            } else {
                0.0
            };

            if similarity_score <= 0.0 {
                continue;
            }

            similar_quotes.push(SimilarQuote {
                quote_id: quote.id,
                similarity_score: (similarity_score * 100.0).round() / 100.0,
            });

            // Margin is computed from the quote's own pricing fields
            // (list price vs. net price), not from the discount field.
            for li in &quote.line_items {
                if li.unit_price > 0.0 {
                    let margin_pct = ((li.unit_price - li.net_price) / li.unit_price) * 100.0;
                    margins.push(margin_pct);
                }
            }

            if notes_parts.len() < 3 {
                notes_parts.push(format!(
                    "Quote {} ({}) – {} line items, total ${:.2}",
                    quote.quote_number,
                    quote.status,
                    quote.line_items.len(),
                    quote.total_amount,
                ));
            }
        }

        if fetched < 100 {
            break;
        }
        page += 1;
    }

    // Sort by similarity descending and take top results.
    similar_quotes.sort_by(|a, b| {
        b.similarity_score
            .partial_cmp(&a.similarity_score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    similar_quotes.truncate(10);

    // Compute historical pricing statistics from the real margins.
    let (avg_margin, range) = if margins.is_empty() {
        (0.0, vec![0.0, 0.0])
    } else {
        let avg = margins.iter().sum::<f64>() / margins.len() as f64;
        let min = margins.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = margins.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        (
            (avg * 100.0).round() / 100.0,
            vec![(min * 100.0).round() / 100.0, (max * 100.0).round() / 100.0],
        )
    };

    let notes = if notes_parts.is_empty() {
        "No similar historical quotes found for this RFQ.".to_string()
    } else {
        notes_parts.join("; ")
    };

    Ok(Json(QuoteMemoryResponse {
        rfq_id,
        similar_quotes,
        historical_pricing: HistoricalPricing { avg_margin, range },
        notes,
    }))
}
