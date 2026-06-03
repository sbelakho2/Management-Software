//! Products reactive store.
//!
//! Mirrors the Zustand [`products.ts`](frontend/src/stores/products.ts) store.

use crate::api::client::{ApiClient, ApiError};
use crate::api::products::{ProductDetailDto, ProductDto, ProductsApi};
use leptos::prelude::*;

/// Reactive store for products.
#[derive(Debug, Clone)]
pub struct ProductsStore {
    /// List of products.
    pub products: RwSignal<Vec<ProductDto>>,
    /// Total number of products (across pages).
    pub total_products: RwSignal<i32>,
    /// Currently selected product detail.
    pub current_product: RwSignal<Option<ProductDetailDto>>,
    /// Whether a fetch is in flight.
    pub loading: RwSignal<bool>,
    /// Last error, if any.
    pub error: RwSignal<Option<String>>,
}

impl ProductsStore {
    pub fn new() -> Self {
        Self {
            products: RwSignal::new(Vec::new()),
            total_products: RwSignal::new(0),
            current_product: RwSignal::new(None),
            loading: RwSignal::new(false),
            error: RwSignal::new(None),
        }
    }

    /// Fetch all products.
    pub async fn fetch_products(&self, client: &ApiClient) {
        self.loading.set(true);
        self.error.set(None);
        match ProductsApi::list_products(client, None).await {
            Ok(resp) => {
                self.products.set(resp.items);
                self.total_products.set(resp.total);
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Fetch a single product by ID.
    pub async fn fetch_product(&self, client: &ApiClient, id: &str) {
        self.loading.set(true);
        self.error.set(None);
        match ProductsApi::get_product(client, id).await {
            Ok(product) => {
                self.current_product.set(Some(product));
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
            }
        }
        self.loading.set(false);
    }

    /// Create a new product.
    pub async fn create_product(&self, client: &ApiClient, data: &serde_json::Value) -> Result<ProductDetailDto, ApiError> {
        let product = ProductsApi::create_product(client, data).await?;
        // Refetch the list
        self.fetch_products(client).await;
        Ok(product)
    }

    /// Update an existing product.
    pub async fn update_product(&self, client: &ApiClient, id: &str, data: &serde_json::Value) -> Result<ProductDetailDto, ApiError> {
        let product = ProductsApi::update_product(client, id, data).await?;
        self.current_product.set(Some(product.clone()));
        self.fetch_products(client).await;
        Ok(product)
    }

    /// Delete a product.
    pub async fn delete_product(&self, client: &ApiClient, id: &str) -> Result<(), ApiError> {
        ProductsApi::delete_product(client, id).await?;
        self.fetch_products(client).await;
        Ok(())
    }
}

impl Default for ProductsStore {
    fn default() -> Self {
        Self::new()
    }
}
