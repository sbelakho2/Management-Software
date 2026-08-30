-- Station execution binding (thirteenth audit): the displayed step is
-- the ORDINAL position (1/3), not the routing sequence (10/30), and the
-- operation binds to the released standard's WorkStep so the operator
-- sees the key point, the WHY, the safety warning and the criticality of
-- the exact step — not a bare operation name.
ALTER TABLE work_order_operations
    ADD COLUMN IF NOT EXISTS ordinal_position INT NOT NULL DEFAULT 0;

-- Backfill ordinal positions for existing orders (1-based per order).
UPDATE work_order_operations w
SET ordinal_position = sub.pos
FROM (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY work_order_id ORDER BY sequence) AS pos
    FROM work_order_operations
) sub
WHERE w.id = sub.id;
