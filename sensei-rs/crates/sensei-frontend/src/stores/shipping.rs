//! Shipping & Pick Lists store.
//!
//! Port of [`frontend/src/stores/shipping.ts`](frontend/src/stores/shipping.ts).

use crate::api::client::{ApiClient, ApiError};
use leptos::prelude::*;
use std::collections::HashSet;

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct ShippingStats {
    pub total_shipments: i32,
    pub pending_shipments: i32,
    pub in_transit: i32,
    pub delivered: i32,
    pub total_pick_lists: i32,
    pub open_pick_lists: i32,
    pub in_progress_picks: i32,
    pub completed_picks: i32,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ShipmentLine {
    pub id: String,
    pub product_id: String,
    pub product_name: String,
    pub quantity: f64,
    pub quantity_shipped: f64,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Shipment {
    pub id: String,
    pub shipment_number: String,
    pub status: String,
    pub origin: String,
    pub destination: String,
    pub carrier: String,
    pub tracking_number: Option<String>,
    pub scheduled_date: String,
    pub shipped_date: Option<String>,
    pub estimated_arrival: Option<String>,
    pub lines: Vec<ShipmentLine>,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PickListLine {
    pub id: String,
    pub product_id: String,
    pub product_name: String,
    pub quantity_required: f64,
    pub quantity_picked: f64,
    pub location: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PickList {
    pub id: String,
    pub pick_list_number: String,
    pub status: String,
    pub shipment_id: Option<String>,
    pub warehouse_id: String,
    pub assigned_to: Option<String>,
    pub lines: Vec<PickListLine>,
    pub notes: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

// ---------------------------------------------------------------------------
// ShippingStore
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ShippingStore {
    // Data
    pub shipments: RwSignal<Vec<Shipment>>,
    pub current_shipment: RwSignal<Option<Shipment>>,
    pub pick_lists: RwSignal<Vec<PickList>>,
    pub current_pick_list: RwSignal<Option<PickList>>,
    pub stats: RwSignal<Option<ShippingStats>>,

    // Loading & error
    pub loading_ops: RwSignal<HashSet<String>>,
    pub error: RwSignal<Option<String>>,
}

impl ShippingStore {
    pub fn new() -> Self {
        Self {
            shipments: RwSignal::new(Vec::new()),
            current_shipment: RwSignal::new(None),
            pick_lists: RwSignal::new(Vec::new()),
            current_pick_list: RwSignal::new(None),
            stats: RwSignal::new(None),
            loading_ops: RwSignal::new(HashSet::new()),
            error: RwSignal::new(None),
        }
    }

    fn start_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.insert(op.to_string());
        });
        self.error.set(None);
    }

    fn end_op(&self, op: &str) {
        self.loading_ops.update(|ops| {
            ops.remove(op);
        });
    }

    pub fn is_op_loading(&self, op: &str) -> bool {
        self.loading_ops.get().contains(op)
    }

    pub fn clear_error(&self) {
        self.error.set(None);
    }

    // -----------------------------------------------------------------------
    // Shipments
    // -----------------------------------------------------------------------

    pub async fn fetch_shipments(&self, client: &ApiClient, params: Option<&str>) {
        self.start_op("fetchShipments");
        let path = match params {
            Some(q) => format!("/shipping/shipments?{q}"),
            None => "/shipping/shipments".to_string(),
        };
        match client.get::<serde_json::Value>(&path).await {
            Ok(data) => {
                if let Some(items) = data
                    .get("items")
                    .and_then(|v| serde_json::from_value(v.clone()).ok())
                {
                    self.shipments.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchShipments");
    }

    pub async fn fetch_shipment(&self, client: &ApiClient, id: &str) {
        self.start_op("fetchShipment");
        match client
            .get::<Shipment>(&format!("/shipping/shipments/{id}"))
            .await
        {
            Ok(shipment) => {
                self.current_shipment.set(Some(shipment));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchShipment");
    }

    pub async fn create_shipment(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<Shipment, ApiError> {
        self.start_op("createShipment");
        match client
            .post::<Shipment, serde_json::Value>("/shipping/shipments", &payload)
            .await
        {
            Ok(shipment) => {
                self.shipments.update(|s| s.push(shipment.clone()));
                self.end_op("createShipment");
                Ok(shipment)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createShipment");
                Err(e)
            }
        }
    }

    pub async fn update_shipment(
        &self,
        client: &ApiClient,
        id: &str,
        payload: serde_json::Value,
    ) -> Result<Shipment, ApiError> {
        self.start_op("updateShipment");
        match client
            .put::<Shipment, serde_json::Value>(&format!("/shipping/shipments/{id}"), &payload)
            .await
        {
            Ok(updated) => {
                self.shipments.update(|s| {
                    if let Some(pos) = s.iter().position(|x| x.id == id) {
                        s[pos] = updated.clone();
                    }
                });
                self.current_shipment.set(Some(updated.clone()));
                self.end_op("updateShipment");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updateShipment");
                Err(e)
            }
        }
    }

    pub async fn update_shipment_status(
        &self,
        client: &ApiClient,
        id: &str,
        status: &str,
    ) -> Result<Shipment, ApiError> {
        self.update_shipment(client, id, serde_json::json!({ "status": status }))
            .await
    }

    pub async fn add_shipment_line(
        &self,
        client: &ApiClient,
        shipment_id: &str,
        line: serde_json::Value,
    ) -> Result<ShipmentLine, ApiError> {
        self.start_op("addShipmentLine");
        match client
            .post::<ShipmentLine, serde_json::Value>(
                &format!("/shipping/shipments/{shipment_id}/lines"),
                &line,
            )
            .await
        {
            Ok(new_line) => {
                self.shipments.update(|s| {
                    if let Some(shipment) = s.iter_mut().find(|x| x.id == shipment_id) {
                        shipment.lines.push(new_line.clone());
                    }
                });
                self.end_op("addShipmentLine");
                Ok(new_line)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("addShipmentLine");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Pick Lists
    // -----------------------------------------------------------------------

    pub async fn fetch_pick_lists(&self, client: &ApiClient, params: Option<&str>) {
        self.start_op("fetchPickLists");
        let path = match params {
            Some(q) => format!("/shipping/pick-lists?{q}"),
            None => "/shipping/pick-lists".to_string(),
        };
        match client.get::<serde_json::Value>(&path).await {
            Ok(data) => {
                if let Some(items) = data
                    .get("items")
                    .and_then(|v| serde_json::from_value(v.clone()).ok())
                {
                    self.pick_lists.set(items);
                }
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchPickLists");
    }

    pub async fn fetch_pick_list(&self, client: &ApiClient, id: &str) {
        self.start_op("fetchPickList");
        match client
            .get::<PickList>(&format!("/shipping/pick-lists/{id}"))
            .await
        {
            Ok(pl) => {
                self.current_pick_list.set(Some(pl));
            }
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchPickList");
    }

    pub async fn create_pick_list(
        &self,
        client: &ApiClient,
        payload: serde_json::Value,
    ) -> Result<PickList, ApiError> {
        self.start_op("createPickList");
        match client
            .post::<PickList, serde_json::Value>("/shipping/pick-lists", &payload)
            .await
        {
            Ok(pl) => {
                self.pick_lists.update(|p| p.push(pl.clone()));
                self.end_op("createPickList");
                Ok(pl)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("createPickList");
                Err(e)
            }
        }
    }

    pub async fn update_pick_list(
        &self,
        client: &ApiClient,
        id: &str,
        payload: serde_json::Value,
    ) -> Result<PickList, ApiError> {
        self.start_op("updatePickList");
        match client
            .put::<PickList, serde_json::Value>(&format!("/shipping/pick-lists/{id}"), &payload)
            .await
        {
            Ok(updated) => {
                self.pick_lists.update(|p| {
                    if let Some(pos) = p.iter().position(|x| x.id == id) {
                        p[pos] = updated.clone();
                    }
                });
                self.current_pick_list.set(Some(updated.clone()));
                self.end_op("updatePickList");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updatePickList");
                Err(e)
            }
        }
    }

    pub async fn start_picking(&self, client: &ApiClient, id: &str) -> Result<PickList, ApiError> {
        self.update_pick_list(client, id, serde_json::json!({ "status": "in_progress" }))
            .await
    }

    pub async fn complete_picking(
        &self,
        client: &ApiClient,
        id: &str,
    ) -> Result<PickList, ApiError> {
        self.update_pick_list(client, id, serde_json::json!({ "status": "completed" }))
            .await
    }

    pub async fn update_pick_line(
        &self,
        client: &ApiClient,
        pick_list_id: &str,
        line_id: &str,
        quantity_picked: f64,
    ) -> Result<PickListLine, ApiError> {
        self.start_op("updatePickLine");
        match client
            .put::<PickListLine, serde_json::Value>(
                &format!("/shipping/pick-lists/{pick_list_id}/lines/{line_id}"),
                &serde_json::json!({ "quantity_picked": quantity_picked }),
            )
            .await
        {
            Ok(updated) => {
                self.pick_lists.update(|p| {
                    if let Some(pl) = p.iter_mut().find(|x| x.id == pick_list_id) {
                        if let Some(line) = pl.lines.iter_mut().find(|l| l.id == line_id) {
                            line.quantity_picked = quantity_picked;
                        }
                    }
                });
                self.end_op("updatePickLine");
                Ok(updated)
            }
            Err(e) => {
                self.error.set(Some(e.to_string()));
                self.end_op("updatePickLine");
                Err(e)
            }
        }
    }

    // -----------------------------------------------------------------------
    // Stats
    // -----------------------------------------------------------------------

    pub async fn fetch_stats(&self, client: &ApiClient) {
        self.start_op("fetchStats");
        match client.get::<ShippingStats>("/shipping/stats").await {
            Ok(stats) => self.stats.set(Some(stats)),
            Err(e) => self.error.set(Some(e.to_string())),
        }
        self.end_op("fetchStats");
    }
}

impl Default for ShippingStore {
    fn default() -> Self {
        Self::new()
    }
}
