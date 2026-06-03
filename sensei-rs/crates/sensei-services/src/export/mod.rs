//! Export services for generating PDF and Excel/CSV reports.
//!
//! Provides:
//! - [`pdf::PdfExportService`] — generates PDF documents for NCR, CAPA, audit,
//!   work order, and inspection reports using `printpdf`.
//! - [`excel::ExcelExportService`] — generates XLSX workbooks and CSV files
//!   from structured data using `rust_xlsxwriter`.

pub mod excel;
pub mod pdf;

pub use excel::ExcelExportService;
pub use pdf::{AuditData, CapaData, InspectionData, NcrData, PdfExportService, WorkOrderData};
