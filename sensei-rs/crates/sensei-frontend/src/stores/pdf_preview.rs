//! PDF preview store — document viewer with zoom, rotation, page navigation,
//! version selection, and fit modes.
//!
//! Port of [`frontend/src/stores/pdf-preview-store.ts`](frontend/src/stores/pdf-preview-store.ts).

use leptos::prelude::*;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

pub type PdfDocumentType = String; // "quote" | "rfq" | "invoice" | "report" | "po" | "other"
pub type FitMode = String; // "width" | "height" | "page" | "actual"

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PdfVersion {
    pub id: String,
    pub version_number: i32,
    pub label: String,
    pub created_at: String,
    pub created_by: String,
    pub file_size: u64,
    pub url: String,
    pub is_current: bool,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PdfDocument {
    pub id: String,
    pub document_type: PdfDocumentType,
    pub title: String,
    pub description: Option<String>,
    pub versions: Vec<PdfVersion>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone)]
pub struct PdfPreviewState {
    pub is_open: bool,
    pub document: Option<PdfDocument>,
    pub selected_version_id: Option<String>,
    pub current_page: u32,
    pub total_pages: u32,
    pub zoom: f64,
    pub rotation: i32, // degrees: 0, 90, 180, 270
    pub fit_mode: FitMode,
    pub loading: bool,
    pub error: Option<String>,
}

impl Default for PdfPreviewState {
    fn default() -> Self {
        Self {
            is_open: false,
            document: None,
            selected_version_id: None,
            current_page: 1,
            total_pages: 1,
            zoom: 1.0,
            rotation: 0,
            fit_mode: "width".to_string(),
            loading: false,
            error: None,
        }
    }
}

// ---------------------------------------------------------------------------
// PDFPreviewStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct PdfPreviewStore {
    pub is_open: RwSignal<bool>,
    pub document: RwSignal<Option<PdfDocument>>,
    pub selected_version_id: RwSignal<Option<String>>,
    pub current_page: RwSignal<u32>,
    pub total_pages: RwSignal<u32>,
    pub zoom: RwSignal<f64>,
    pub rotation: RwSignal<i32>,
    pub fit_mode: RwSignal<FitMode>,
    pub loading: RwSignal<bool>,
    pub error: RwSignal<Option<String>>,
}

impl PdfPreviewStore {
    pub fn new() -> Self {
        Self {
            is_open: RwSignal::new(false),
            document: RwSignal::new(None),
            selected_version_id: RwSignal::new(None),
            current_page: RwSignal::new(1),
            total_pages: RwSignal::new(1),
            zoom: RwSignal::new(1.0),
            rotation: RwSignal::new(0),
            fit_mode: RwSignal::new("width".to_string()),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    // -----------------------------------------------------------------------
    // Open / Close
    // -----------------------------------------------------------------------

    pub fn open(&self, doc: PdfDocument, version_id: Option<&str>) {
        let vid = version_id
            .map(|v| v.to_string())
            .or_else(|| {
                doc.versions.iter().find(|v| v.is_current).map(|v| v.id.clone())
            })
            .or_else(|| doc.versions.first().map(|v| v.id.clone()));

        self.document.set(Some(doc));
        self.selected_version_id.set(vid);
        self.current_page.set(1);
        self.zoom.set(1.0);
        self.rotation.set(0);
        self.fit_mode.set("width".to_string());
        self.loading.set(false);
        self.error.set(None);
        self.is_open.set(true);
    }

    pub fn close(&self) {
        self.is_open.set(false);
        self.document.set(None);
        self.selected_version_id.set(None);
        self.current_page.set(1);
        self.total_pages.set(1);
        self.zoom.set(1.0);
        self.rotation.set(0);
        self.loading.set(false);
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Version selection
    // -----------------------------------------------------------------------

    pub fn select_version(&self, version_id: &str) {
        self.selected_version_id.set(Some(version_id.to_string()));
        self.current_page.set(1);
        self.loading.set(true);

        // In a real implementation, this would fetch the new version's PDF data
        // For now, just mark loading as complete
        self.loading.set(false);
    }

    // -----------------------------------------------------------------------
    // Page navigation
    // -----------------------------------------------------------------------

    pub fn set_current_page(&self, page: u32) {
        let total = self.total_pages.get();
        self.current_page.set(page.clamp(1, total.max(1)));
    }

    pub fn next_page(&self) {
        let page = self.current_page.get();
        let total = self.total_pages.get();
        if page < total {
            self.current_page.set(page + 1);
        }
    }

    pub fn previous_page(&self) {
        let page = self.current_page.get();
        if page > 1 {
            self.current_page.set(page - 1);
        }
    }

    pub fn go_to_page(&self, page: u32) {
        self.set_current_page(page);
    }

    // -----------------------------------------------------------------------
    // Zoom
    // -----------------------------------------------------------------------

    pub fn set_zoom(&self, zoom: f64) {
        self.zoom.set(zoom.max(0.25).min(5.0));
    }

    pub fn zoom_in(&self) {
        let zoom = self.zoom.get();
        self.zoom.set((zoom * 1.25).min(5.0));
    }

    pub fn zoom_out(&self) {
        let zoom = self.zoom.get();
        self.zoom.set((zoom / 1.25).max(0.25));
    }

    // -----------------------------------------------------------------------
    // Rotation
    // -----------------------------------------------------------------------

    pub fn rotate_clockwise(&self) {
        let rot = self.rotation.get();
        self.rotation.set((rot + 90) % 360);
    }

    pub fn rotate_counter_clockwise(&self) {
        let rot = self.rotation.get();
        self.rotation.set((rot - 90 + 360) % 360);
    }

    // -----------------------------------------------------------------------
    // Fit mode
    // -----------------------------------------------------------------------

    pub fn set_fit_mode(&self, mode: &str) {
        self.fit_mode.set(mode.to_string());
    }

    // -----------------------------------------------------------------------
    // Derived selectors
    // -----------------------------------------------------------------------

    pub fn selected_version(&self) -> Option<PdfVersion> {
        let doc = self.document.get()?;
        let vid = self.selected_version_id.get()?;
        doc.versions.into_iter().find(|v| v.id == vid)
    }

    pub fn pdf_url(&self) -> Option<String> {
        self.selected_version().map(|v| v.url)
    }
}

impl Default for PdfPreviewStore {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

pub fn format_file_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{bytes} B")
    }
}

pub fn format_version_label(version: &PdfVersion) -> String {
    if version.is_current {
        format!("v{} (Current)", version.version_number)
    } else {
        format!("v{}", version.version_number)
    }
}

pub fn get_document_type_label(doc_type: &str) -> &str {
    match doc_type {
        "quote" => "Quote",
        "rfq" => "RFQ",
        "invoice" => "Invoice",
        "report" => "Report",
        "po" => "Purchase Order",
        "other" => "Document",
        _ => "Document",
    }
}

pub fn get_document_type_icon(doc_type: &str) -> &str {
    match doc_type {
        "quote" => "file-text",
        "rfq" => "file-search",
        "invoice" => "file-invoice",
        "report" => "file-bar-chart",
        "po" => "file-plus",
        _ => "file",
    }
}
