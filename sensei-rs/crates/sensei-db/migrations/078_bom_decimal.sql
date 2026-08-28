-- BOM canonical contract (P0-4): bom_items uses quantity / scrap_percent
-- (the MRP engine already queries these); the API/service layer now agrees.
-- Quantities become NUMERIC(20,6) + Decimal: binary floats are the wrong
-- representation for contractual quantities and unit conversions.
ALTER TABLE bom_items
    ALTER COLUMN quantity TYPE NUMERIC(20,6),
    ALTER COLUMN scrap_percent TYPE NUMERIC(20,6);
