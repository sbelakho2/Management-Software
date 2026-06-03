//! Pagination types shared across all domain services.
//!
//! Provides [`PaginatedResponse<T>`] for wrapping list results and
//! [`PaginationParams`] for deserializing query parameters from API requests.

use serde::{Deserialize, Serialize};

/// Generic paginated response wrapper returned by all list endpoints.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaginatedResponse<T> {
    /// The items on the current page.
    pub data: Vec<T>,
    /// Total number of items across all pages.
    pub total: usize,
    /// Current page number (1-based).
    pub page: usize,
    /// Number of items per page.
    pub per_page: usize,
    /// Total number of pages.
    pub total_pages: usize,
}

impl<T> PaginatedResponse<T> {
    /// Create a new paginated response from a full item list.
    ///
    /// * `items`  – the complete (already-filtered) item collection.
    /// * `page`    – 1-based page number; defaults to `1` if `None`.
    /// * `per_page` – items per page; defaults to `20`, clamped to `[1, 100]`.
    pub fn new(items: Vec<T>, page: Option<usize>, per_page: Option<usize>) -> Self {
        let total = items.len();
        let page = page.unwrap_or(1).max(1);
        let per_page = per_page.unwrap_or(20).clamp(1, 100);
        let total_pages = total.div_ceil(per_page).max(1);

        let start = (page - 1) * per_page;
        let data = if start >= total {
            Vec::new()
        } else {
            items.into_iter().skip(start).take(per_page).collect()
        };

        Self {
            data,
            total,
            page,
            per_page,
            total_pages,
        }
    }
}

/// Query-string parameters accepted by all paginated list endpoints.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct PaginationParams {
    /// Page number (1-based; defaults to 1).
    pub page: Option<usize>,
    /// Items per page (defaults to 20; clamped to [1, 100]).
    pub per_page: Option<usize>,
}
