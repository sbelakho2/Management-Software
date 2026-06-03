//! Excel (XLSX) and CSV export services.
//!
//! The [`ExcelExportService`] generates:
//! - Single-sheet XLSX workbooks from any `Serialize`-able data.
//! - Multi-sheet XLSX workbooks from a vec of [`SheetData`].
//! - CSV strings from any `Serialize`-able data with proper escaping.

use sensei_core::error::{Result, SenseiError};
use serde::Serialize;
use rust_xlsxwriter::*;

// ---------------------------------------------------------------------------
// Re-exported types
// ---------------------------------------------------------------------------

/// Describes a single worksheet for multi-sheet XLSX export.
#[derive(Debug, Clone)]
pub struct SheetData {
    pub name: String,
    pub headers: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

/// Service for generating Excel (XLSX) and CSV exports.
///
/// Stateless — all methods are pure functions of their inputs.
#[derive(Clone)]
pub struct ExcelExportService;

impl ExcelExportService {
    /// Create a new [`ExcelExportService`].
    pub fn new() -> Self {
        Self
    }

    /// Generate an XLSX workbook from a slice of serializable items.
    ///
    /// The first row contains bold column headers derived from the struct
    /// field names (via serde reflection). Data rows are written as strings.
    ///
    /// For full control over headers and cell types, use
    /// [`generate_multi_sheet_xlsx`](Self::generate_multi_sheet_xlsx) with a
    /// single sheet.
    pub fn generate_xlsx<T: Serialize>(&self, data: &[T], sheet_name: &str) -> Result<Vec<u8>> {
        let mut workbook = Workbook::new();

        // Add a worksheet
        let sheet = workbook.add_worksheet();
        sheet.set_name(sheet_name).map_err(map_xlsx_error)?;

        // Bold header format
        let header_fmt = Format::new().set_bold();

        // Serialize first item to discover field names
        if let Some(first) = data.first() {
            let json_value = serde_json::to_value(first)?;
            let headers = match &json_value {
                serde_json::Value::Object(map) => map.keys().cloned().collect::<Vec<_>>(),
                _ => {
                    return Err(SenseiError::Validation(
                        "Expected a struct/object for XLSX export".into(),
                    ))
                }
            };

            // Write header row with bold format
            for (col, header) in headers.iter().enumerate() {
                sheet.write_string_with_format(0, col as u16, header, &header_fmt).map_err(map_xlsx_error)?;
            }

            // Write data rows
            for (row_idx, item) in data.iter().enumerate() {
                let val = serde_json::to_value(item)?;
                if let serde_json::Value::Object(map) = val {
                    for (col_idx, header) in headers.iter().enumerate() {
                        let cell_value = map.get(header).map(|v| match v {
                            serde_json::Value::Null => String::new(),
                            serde_json::Value::String(s) => s.clone(),
                            other => other.to_string(),
                        }).unwrap_or_default();
                        sheet.write_string((row_idx + 1) as u32, col_idx as u16, &cell_value).map_err(map_xlsx_error)?;
                    }
                }
            }

            // Auto-fit columns (approximate width based on header + data)
            for (col_idx, header) in headers.iter().enumerate() {
                let max_width = data
                    .iter()
                    .map(|item| {
                        let val = serde_json::to_value(item).ok();
                        val.and_then(|v| {
                            v.get(header)
                                .map(|v| match v {
                                    serde_json::Value::Null => 0,
                                    serde_json::Value::String(s) => s.len(),
                                    other => other.to_string().len(),
                                })
                        }).unwrap_or(0)
                    })
                    .chain(std::iter::once(header.len()))
                    .max()
                    .unwrap_or(10)
                    .min(50) as f64; // Cap at 50 chars wide

                sheet.set_column_width(col_idx as u16, max_width + 2.0).map_err(map_xlsx_error)?;
            }
        }

        let data = workbook.save_to_buffer().map_err(map_xlsx_error)?;
        Ok(data)
    }

    /// Generate a multi-sheet XLSX workbook from a slice of [`SheetData`].
    ///
    /// Each sheet has bold headers and auto-fitted column widths.
    pub fn generate_multi_sheet_xlsx(&self, sheets: &[SheetData]) -> Result<Vec<u8>> {
        let mut workbook = Workbook::new();

        let header_fmt = Format::new().set_bold();

        for sheet_data in sheets {
            let sheet = workbook.add_worksheet();
            sheet.set_name(&sheet_data.name).map_err(map_xlsx_error)?;

            // Write headers with bold format
            for (col, header) in sheet_data.headers.iter().enumerate() {
                sheet.write_string_with_format(0, col as u16, header, &header_fmt).map_err(map_xlsx_error)?;
            }

            // Write data rows
            for (row_idx, row) in sheet_data.rows.iter().enumerate() {
                for (col_idx, value) in row.iter().enumerate() {
                    sheet.write_string((row_idx + 1) as u32, col_idx as u16, value).map_err(map_xlsx_error)?;
                }
            }

            // Auto-fit columns
            for (col_idx, header) in sheet_data.headers.iter().enumerate() {
                let max_width = sheet_data
                    .rows
                    .iter()
                    .map(|row| {
                        row.get(col_idx)
                            .map(|s| s.len())
                            .unwrap_or(0)
                    })
                    .chain(std::iter::once(header.len()))
                    .max()
                    .unwrap_or(10)
                    .min(50) as f64;

                sheet.set_column_width(col_idx as u16, max_width + 2.0).map_err(map_xlsx_error)?;
            }
        }

        let data = workbook.save_to_buffer().map_err(map_xlsx_error)?;
        Ok(data)
    }

    /// Generate a CSV string from a slice of serializable items.
    ///
    /// Properly escapes fields containing commas, double quotes, or newlines
    /// by wrapping them in double quotes and doubling internal quotes.
    pub fn generate_csv<T: Serialize>(&self, data: &[T]) -> Result<String> {
        let mut output = String::new();

        if let Some(first) = data.first() {
            let json_value = serde_json::to_value(first)?;
            let headers = match &json_value {
                serde_json::Value::Object(map) => map.keys().cloned().collect::<Vec<_>>(),
                _ => {
                    return Err(SenseiError::Validation(
                        "Expected a struct/object for CSV export".into(),
                    ))
                }
            };

            // Write header row
            for (i, header) in headers.iter().enumerate() {
                if i > 0 {
                    output.push(',');
                }
                output.push_str(&escape_csv(header));
            }
            output.push('\n');

            // Write data rows
            for item in data {
                let val = serde_json::to_value(item)?;
                if let serde_json::Value::Object(map) = val {
                    for (i, header) in headers.iter().enumerate() {
                        if i > 0 {
                            output.push(',');
                        }
                        let cell_value = map.get(header).map(|v| match v {
                            serde_json::Value::Null => String::new(),
                            serde_json::Value::String(s) => s.clone(),
                            other => other.to_string(),
                        }).unwrap_or_default();
                        output.push_str(&escape_csv(&cell_value));
                    }
                    output.push('\n');
                }
            }
        }

        Ok(output)
    }
}

impl Default for ExcelExportService {
    fn default() -> Self {
        Self::new()
    }
}

/// Convert an `XlsxError` into a `SenseiError`.
fn map_xlsx_error(e: XlsxError) -> SenseiError {
    SenseiError::Internal(format!("XLSX error: {e}"))
}

/// Escape a value for CSV: wrap in double quotes if it contains commas,
/// double quotes, or newlines; double any internal double quotes.
fn escape_csv(value: &str) -> String {
    if value.contains(',') || value.contains('"') || value.contains('\n') || value.contains('\r') {
        let escaped = value.replace('"', "\"\"");
        format!("\"{}\"", escaped)
    } else {
        value.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Serialize;

    #[derive(Serialize)]
    struct TestRow {
        name: String,
        value: i32,
    }

    #[test]
    fn test_escape_csv_no_quoting() {
        assert_eq!(escape_csv("hello"), "hello");
        assert_eq!(escape_csv("simple text"), "simple text");
    }

    #[test]
    fn test_escape_csv_with_quotes() {
        assert_eq!(escape_csv("he\"llo"), "\"he\"\"llo\"");
    }

    #[test]
    fn test_escape_csv_with_commas() {
        assert_eq!(escape_csv("hello, world"), "\"hello, world\"");
    }

    #[test]
    fn test_generate_csv_basic() {
        let svc = ExcelExportService::new();
        let data = vec![
            TestRow {
                name: "Alice".into(),
                value: 42,
            },
            TestRow {
                name: "Bob".into(),
                value: 99,
            },
        ];
        let csv = svc.generate_csv(&data).unwrap();
        assert!(csv.starts_with("name,value\n"));
        assert!(csv.contains("Alice,42"));
        assert!(csv.contains("Bob,99"));
    }

    #[test]
    fn test_generate_csv_empty() {
        let svc = ExcelExportService::new();
        let data: Vec<TestRow> = vec![];
        let csv = svc.generate_csv(&data).unwrap();
        assert_eq!(csv, "");
    }
}
