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
    ///
    /// Clamping semantics:
    /// - `page` values of `0` (or `None`) are clamped up to `1`. There is no
    ///   page `0` in a 1-based pagination scheme, so callers passing `0` are
    ///   treated as if they asked for the first page.
    /// - `per_page` is clamped to `[1, 100]` (an out-of-range value is
    ///   silently corrected, never rejected).
    /// - Pages beyond the last page (`page > total_pages`) intentionally
    ///   return an empty `data` list with `total_pages` left untouched; this
    ///   lets clients detect that they have walked off the end of the result
    ///   set instead of being silently redirected to the last page.
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
    /// Page number (1-based; defaults to 1, page 0 is clamped to 1).
    pub page: Option<usize>,
    /// Items per page (defaults to 20; clamped to [1, 100]).
    pub per_page: Option<usize>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn items() -> Vec<usize> {
        (0..25).collect()
    }

    #[test]
    fn page_zero_is_clamped_to_one() {
        let resp = PaginatedResponse::new(items(), Some(0), Some(10));
        assert_eq!(resp.page, 1);
        assert_eq!(resp.data.len(), 10);
        assert_eq!(resp.data[0], 0);
    }

    #[test]
    fn missing_page_defaults_to_one() {
        let resp = PaginatedResponse::new(items(), None, Some(10));
        assert_eq!(resp.page, 1);
        assert_eq!(resp.data.len(), 10);
    }

    #[test]
    fn per_page_is_clamped_to_bounds() {
        let resp = PaginatedResponse::new(items(), Some(1), Some(0));
        assert_eq!(resp.per_page, 1);
        let resp = PaginatedResponse::new(items(), Some(1), Some(1000));
        assert_eq!(resp.per_page, 100);
        let resp = PaginatedResponse::new(items(), Some(1), None);
        assert_eq!(resp.per_page, 20);
    }

    #[test]
    fn out_of_range_page_returns_empty_data() {
        let resp = PaginatedResponse::new(items(), Some(99), Some(10));
        assert_eq!(resp.total_pages, 3);
        assert!(resp.data.is_empty());
    }

    #[test]
    fn last_page_returns_remaining_items() {
        let resp = PaginatedResponse::new(items(), Some(3), Some(10));
        assert_eq!(resp.data.len(), 5);
        assert_eq!(resp.total_pages, 3);
    }
}
