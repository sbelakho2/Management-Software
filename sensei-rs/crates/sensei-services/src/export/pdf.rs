//! PDF report generation using `printpdf`.
//!
//! The [`PdfExportService`] generates printable PDF documents for quality,
//! maintenance, and production reports using the low-level `Op`-based
//! printpdf 0.8 API (built-in fonts, A4 layout).

use printpdf::*;
use sensei_core::error::Result;

// ---------------------------------------------------------------------------
// Report input data structs
// ---------------------------------------------------------------------------

/// Input data for a Non-Conformance Report (NCR) PDF.
#[derive(Debug, Clone, Default)]
pub struct NcrData {
    pub id: String,
    pub title: String,
    pub description: String,
    pub status: String,
    pub severity: String,
    pub created_by: String,
    pub created_at: String,
    pub department: String,
    pub corrective_actions: Vec<String>,
}

/// Input data for a CAPA form PDF.
#[derive(Debug, Clone, Default)]
pub struct CapaData {
    pub id: String,
    pub title: String,
    pub description: String,
    pub root_cause: String,
    pub action_plan: String,
    pub status: String,
    pub deadline: String,
    pub assigned_to: String,
}

/// Input data for an Audit Report PDF.
#[derive(Debug, Clone, Default)]
pub struct AuditData {
    pub id: String,
    pub title: String,
    pub auditor: String,
    pub auditee: String,
    pub date: String,
    pub scope: String,
    pub findings: Vec<(String, String, String)>, // (clause, description, status)
    pub score: f64,
    pub status: String,
}

/// Input data for a Work Order PDF.
#[derive(Debug, Clone, Default)]
pub struct WorkOrderData {
    pub id: String,
    pub title: String,
    pub description: String,
    pub status: String,
    pub priority: String,
    pub assigned_to: String,
    pub due_date: String,
    pub work_center: String,
    pub estimated_hours: f64,
}

/// Input data for an Inspection Report PDF.
#[derive(Debug, Clone, Default)]
pub struct InspectionData {
    pub id: String,
    pub part_name: String,
    pub part_number: String,
    pub inspector: String,
    pub date: String,
    /// (characteristic, nominal, actual, status)
    pub measurements: Vec<(String, f64, f64, String)>,
    pub result: String,
}

/// Input data for an A3 problem-solving report PDF.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct A3Data {
    pub id: String,
    pub title: String,
    pub problem_statement: String,
    pub current_state: String,
    pub goal: String,
    pub root_cause_analysis: String,
    pub countermeasures: String,
    pub check_plan: String,
    pub follow_up: String,
    pub owner: String,
    pub status: String,
    pub created_at: String,
}

/// A single line item in a quote PDF.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct QuoteLineData {
    pub description: String,
    pub quantity: String,
    pub unit_price: String,
    pub total: String,
}

/// Input data for a Quote PDF.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct QuoteData {
    pub id: String,
    pub quote_number: String,
    pub customer_name: String,
    pub date: String,
    pub valid_until: String,
    pub currency: String,
    pub line_items: Vec<QuoteLineData>,
    pub subtotal: String,
    pub tax: String,
    pub total: String,
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Service for generating PDF reports using the low-level printpdf Op API.
#[derive(Clone)]
pub struct PdfExportService;

impl PdfExportService {
    /// Create a new [`PdfExportService`].
    pub fn new() -> Self {
        Self
    }

    // ── High-level report generators ────────────────────────────────────

    /// Generate a PDF for a Non-Conformance Report.
    pub fn generate_ncr_report(&self, ncr: &NcrData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "NON-CONFORMANCE REPORT");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "NCR ID", &ncr.id);
        y = Self::draw_field(&mut ops, y, "Title", &ncr.title);
        y = Self::draw_field(&mut ops, y, "Description", &ncr.description);
        y = Self::draw_field(&mut ops, y, "Status", &ncr.status);
        y = Self::draw_field(&mut ops, y, "Severity", &ncr.severity);
        y = Self::draw_field(&mut ops, y, "Created By", &ncr.created_by);
        y = Self::draw_field(&mut ops, y, "Created At", &ncr.created_at);
        y = Self::draw_field(&mut ops, y, "Department", &ncr.department);
        y -= Pt(8.0);

        // Corrective actions table
        y = Self::draw_table_header(&mut ops, y, &["#", "Corrective Action"]);
        for (i, action) in ncr.corrective_actions.iter().enumerate() {
            if y < Pt(40.0) {
                break;
            }
            y = Self::draw_table_row(&mut ops, y, &[&(i + 1).to_string(), action]);
        }

        Self::build_pdf("NCR Report", ops)
    }

    /// Generate a PDF for a CAPA form.
    pub fn generate_capa_report(&self, capa: &CapaData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "CORRECTIVE & PREVENTIVE ACTION (CAPA)");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "CAPA ID", &capa.id);
        y = Self::draw_field(&mut ops, y, "Title", &capa.title);
        y = Self::draw_field(&mut ops, y, "Description", &capa.description);
        y = Self::draw_field(&mut ops, y, "Root Cause", &capa.root_cause);
        y = Self::draw_field(&mut ops, y, "Action Plan", &capa.action_plan);
        y = Self::draw_field(&mut ops, y, "Status", &capa.status);
        y = Self::draw_field(&mut ops, y, "Deadline", &capa.deadline);
        let _ = Self::draw_field(&mut ops, y, "Assigned To", &capa.assigned_to);

        Self::build_pdf("CAPA Report", ops)
    }

    /// Generate a PDF for an Audit Report.
    pub fn generate_audit_report(&self, audit: &AuditData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "AUDIT REPORT");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "Audit ID", &audit.id);
        y = Self::draw_field(&mut ops, y, "Title", &audit.title);
        y = Self::draw_field(&mut ops, y, "Auditor", &audit.auditor);
        y = Self::draw_field(&mut ops, y, "Auditee", &audit.auditee);
        y = Self::draw_field(&mut ops, y, "Date", &audit.date);
        y = Self::draw_field(&mut ops, y, "Scope", &audit.scope);
        y = Self::draw_field(&mut ops, y, "Status", &audit.status);
        y = Self::draw_field(&mut ops, y, "Score", &format!("{:.1}", audit.score));
        y -= Pt(8.0);

        // Findings table
        y = Self::draw_table_header(&mut ops, y, &["#", "Clause", "Finding", "Status"]);
        for (i, (clause, desc, status)) in audit.findings.iter().enumerate() {
            if y < Pt(40.0) {
                break;
            }
            y = Self::draw_table_row(&mut ops, y, &[&(i + 1).to_string(), clause, desc, status]);
        }

        Self::build_pdf("Audit Report", ops)
    }

    /// Generate a PDF for a Work Order.
    pub fn generate_work_order(&self, wo: &WorkOrderData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "WORK ORDER");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "Work Order ID", &wo.id);
        y = Self::draw_field(&mut ops, y, "Title", &wo.title);
        y = Self::draw_field(&mut ops, y, "Description", &wo.description);
        y = Self::draw_field(&mut ops, y, "Status", &wo.status);
        y = Self::draw_field(&mut ops, y, "Priority", &wo.priority);
        y = Self::draw_field(&mut ops, y, "Assigned To", &wo.assigned_to);
        y = Self::draw_field(&mut ops, y, "Due Date", &wo.due_date);
        y = Self::draw_field(&mut ops, y, "Work Center", &wo.work_center);
        let _ = Self::draw_field(&mut ops, y, "Estimated Hours", &format!("{:.1}", wo.estimated_hours));

        Self::build_pdf("Work Order", ops)
    }

    /// Generate a PDF for an A3 problem-solving report.
    pub fn generate_a3_report(&self, a3: &A3Data) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "A3 PROBLEM-SOLVING REPORT");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "A3 ID", &a3.id);
        y = Self::draw_field(&mut ops, y, "Title", &a3.title);
        y = Self::draw_field(&mut ops, y, "Owner", &a3.owner);
        y = Self::draw_field(&mut ops, y, "Status", &a3.status);
        y = Self::draw_field(&mut ops, y, "Created At", &a3.created_at);
        y -= Pt(8.0);

        y = Self::draw_field(&mut ops, y, "1. Problem Statement", &a3.problem_statement);
        y = Self::draw_field(&mut ops, y, "2. Current State", &a3.current_state);
        y = Self::draw_field(&mut ops, y, "3. Goal", &a3.goal);
        y = Self::draw_field(&mut ops, y, "4. Root Cause Analysis", &a3.root_cause_analysis);
        y = Self::draw_field(&mut ops, y, "5. Countermeasures", &a3.countermeasures);
        y = Self::draw_field(&mut ops, y, "6. Check Plan", &a3.check_plan);
        let _ = Self::draw_field(&mut ops, y, "7. Follow Up", &a3.follow_up);

        Self::build_pdf("A3 Report", ops)
    }

    /// Generate a PDF for a customer quotation.
    pub fn generate_quote(&self, quote: &QuoteData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "QUOTATION");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "Quote ID", &quote.id);
        y = Self::draw_field(&mut ops, y, "Quote Number", &quote.quote_number);
        y = Self::draw_field(&mut ops, y, "Customer", &quote.customer_name);
        y = Self::draw_field(&mut ops, y, "Date", &quote.date);
        y = Self::draw_field(&mut ops, y, "Valid Until", &quote.valid_until);
        y -= Pt(8.0);

        // Line items table
        y = Self::draw_table_header(&mut ops, y, &["#", "Description", "Qty", "Unit Price", "Total"]);
        for (i, line) in quote.line_items.iter().enumerate() {
            if y < Pt(60.0) {
                break;
            }
            y = Self::draw_table_row(
                &mut ops,
                y,
                &[
                    &(i + 1).to_string(),
                    &line.description,
                    &line.quantity,
                    &line.unit_price,
                    &line.total,
                ],
            );
        }
        y -= Pt(8.0);
        draw_hline(&mut ops, mm_pt(20.0), mm_pt(170.0), y + Pt(3.0));
        y -= Pt(4.0);

        y = Self::draw_field(&mut ops, y, "Subtotal", &quote.subtotal);
        y = Self::draw_field(&mut ops, y, "Tax", &quote.tax);
        let _ = Self::draw_field(&mut ops, y, "TOTAL", &quote.total);

        Self::build_pdf("Quotation", ops)
    }

    /// Generate a PDF for an Inspection Report.
    pub fn generate_inspection_report(&self, inspection: &InspectionData) -> Result<Vec<u8>> {
        let mut ops: Vec<Op> = Vec::new();

        Self::draw_report_header(&mut ops, "INSPECTION REPORT");

        let mut y = mm_pt(260.0);
        y = Self::draw_field(&mut ops, y, "Inspection ID", &inspection.id);
        y = Self::draw_field(&mut ops, y, "Part Name", &inspection.part_name);
        y = Self::draw_field(&mut ops, y, "Part Number", &inspection.part_number);
        y = Self::draw_field(&mut ops, y, "Inspector", &inspection.inspector);
        y = Self::draw_field(&mut ops, y, "Date", &inspection.date);
        y = Self::draw_field(&mut ops, y, "Result", &inspection.result);
        y -= Pt(8.0);

        // Measurements table
        y = Self::draw_table_header(&mut ops, y, &["#", "Characteristic", "Nominal", "Actual", "Status"]);
        for (i, (char_name, nominal, actual, status)) in inspection.measurements.iter().enumerate() {
            if y < Pt(40.0) {
                break;
            }
            y = Self::draw_table_row(
                &mut ops,
                y,
                &[
                    &(i + 1).to_string(),
                    char_name,
                    &format!("{:.3}", nominal),
                    &format!("{:.3}", actual),
                    status,
                ],
            );
        }

        Self::build_pdf("Inspection Report", ops)
    }

    // ── Private helpers ─────────────────────────────────────────────────

    /// Build the final PDF document from a vector of operations.
    fn build_pdf(title: &str, ops: Vec<Op>) -> Result<Vec<u8>> {
        let mut doc = PdfDocument::new(title);

        let page = PdfPage::new(Mm(210.0), Mm(297.0), ops);
        doc.with_pages(vec![page]);

        let bytes = doc.save(&PdfSaveOptions::default(), &mut vec![]);
        Ok(bytes)
    }

    /// Draw the report title header at the top of the page.
    fn draw_report_header(ops: &mut Vec<Op>, title: &str) {
        // Company / title bar
        write_text(ops, Pt(18.0), mm_pt(20.0), mm_pt(282.0), "SENSEI ERP", BuiltinFont::HelveticaBold);
        write_text(ops, Pt(14.0), mm_pt(20.0), mm_pt(275.0), title, BuiltinFont::HelveticaBold);

        // Horizontal rule
        draw_hline(ops, mm_pt(20.0), mm_pt(190.0), mm_pt(270.0));
    }

    /// Draw a label: value field at the given y-position (in points).
    /// Returns the new y position after the field.
    fn draw_field(ops: &mut Vec<Op>, y: Pt, label: &str, value: &str) -> Pt {
        write_text(ops, Pt(10.0), mm_pt(20.0), y, label, BuiltinFont::HelveticaBold);
        write_text(ops, Pt(10.0), mm_pt(65.0), y, value, BuiltinFont::Helvetica);
        y - Pt(14.0)
    }

    /// Draw a table header row at the given y-position.
    /// Returns the new y position.
    fn draw_table_header(ops: &mut Vec<Op>, y: Pt, columns: &[&str]) -> Pt {
        let col_width = 150.0 / columns.len() as f32;

        // Draw header background line
        draw_hline(ops, mm_pt(20.0), mm_pt(170.0), y + Pt(3.0));

        let mut x = mm_pt(20.0);
        for col in columns {
            write_text(ops, Pt(9.0), x, y, col, BuiltinFont::HelveticaBold);
            x += Pt(col_width);
        }

        draw_hline(ops, mm_pt(20.0), mm_pt(170.0), y - Pt(1.0));
        y - Pt(16.0)
    }

    /// Draw a table data row.
    fn draw_table_row(ops: &mut Vec<Op>, y: Pt, columns: &[&str]) -> Pt {
        let col_width = 150.0 / columns.len() as f32;

        let mut x = mm_pt(20.0);
        for col in columns {
            // Truncate long text for table cells
            let text = if col.len() > 30 {
                format!("{}…", &col[..29])
            } else {
                col.to_string()
            };
            write_text(ops, Pt(8.0), x, y, &text, BuiltinFont::Helvetica);
            x += Pt(col_width);
        }

        y - Pt(12.0)
    }
}

impl Default for PdfExportService {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Low-level operation helpers
// ---------------------------------------------------------------------------

/// Write a single line of text using a built-in font.
fn write_text(ops: &mut Vec<Op>, size: Pt, x: Pt, y: Pt, text: &str, font: BuiltinFont) {
    // Save graphics state, set up text cursor, font size, then write text.
    ops.push(Op::SaveGraphicsState);
    ops.push(Op::SetTextCursor {
        pos: Point { x, y },
    });
    ops.push(Op::SetFontSizeBuiltinFont { size, font: font.clone() });
    ops.push(Op::StartTextSection);
    ops.push(Op::WriteTextBuiltinFont {
        items: vec![TextItem::Text(text.to_string())],
        font,
    });
    ops.push(Op::EndTextSection);
    ops.push(Op::RestoreGraphicsState);
}

/// Draw a horizontal line at the given y-position (from x1 to x2).
fn draw_hline(ops: &mut Vec<Op>, x1: Pt, x2: Pt, y: Pt) {
    let line = Line {
        points: vec![
            LinePoint {
                p: Point { x: x1, y },
                bezier: false,
            },
            LinePoint {
                p: Point { x: x2, y },
                bezier: false,
            },
        ],
        is_closed: false,
    };
    ops.push(Op::SetOutlineColor {
        col: Color::Rgb(Rgb::new(0.3, 0.3, 0.3, None)),
    });
    ops.push(Op::DrawLine { line });
    // Reset to black
    ops.push(Op::SetOutlineColor {
        col: Color::Rgb(Rgb::new(0.0, 0.0, 0.0, None)),
    });
}

/// Convert millimetres to points.
fn mm_pt(mm: f32) -> Pt {
    Pt(mm * 72.0 / 25.4)
}
