//! The canonical pagination envelope — one type, both sides.

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Paginated<T> {
    pub data: Vec<T>,
    pub total: i64,
    pub page: i64,
    pub per_page: i64,
    pub total_pages: i64,
}

impl<T> Paginated<T> {
    pub fn new(data: Vec<T>, total: i64, page: i64, per_page: i64) -> Self {
        let total_pages = if per_page > 0 {
            (total as f64 / per_page as f64).ceil() as i64
        } else {
            0
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
