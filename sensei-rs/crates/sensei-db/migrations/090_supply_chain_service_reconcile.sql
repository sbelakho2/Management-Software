-- Supply-chain service schema reconciliation (audit gate discovery): the
-- DatabaseSupplyChainService and the MRP engine read sales_orders /
-- purchase_orders with a JSONB line_items + delivery_date shape and a
-- NUMERIC total_amount, but the base migrations created normalized
-- line-item tables and FLOAT8 money. The service contract is the API
-- source of truth — reconcile additively and idempotently.
ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS order_number VARCHAR(50),
    ADD COLUMN IF NOT EXISTS customer_name VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS line_items JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS delivery_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_by UUID;

UPDATE sales_orders SET order_number = so_number WHERE order_number IS NULL;

ALTER TABLE sales_orders
    ALTER COLUMN total_amount TYPE NUMERIC(19,4) USING ROUND(total_amount::numeric, 4);

-- Purchase orders: the service reads line_items, supplier_name,
-- expected_delivery and a NUMERIC total.
ALTER TABLE purchase_orders
    ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS line_items JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS expected_delivery TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_by UUID;

ALTER TABLE purchase_orders
    ALTER COLUMN total_amount TYPE NUMERIC(19,4) USING ROUND(total_amount::numeric, 4);
