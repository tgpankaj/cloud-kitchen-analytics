-- ============================================================
-- KitchenIQ Pro — Rollback Migration 001
-- Restores original schema (drops all new tables and columns)
-- WARNING: Run only if you need to revert
-- ============================================================

BEGIN;

-- Drop new tables (order matters due to FKs)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS sync_logs CASCADE;
DROP TABLE IF EXISTS integrations CASCADE;
DROP TABLE IF EXISTS kitchen_users CASCADE;

-- Drop new indexes on orders
DROP INDEX IF EXISTS idx_orders_external_dedup;
DROP INDEX IF EXISTS idx_orders_status;
DROP INDEX IF EXISTS idx_orders_updated;

-- Revert orders table
ALTER TABLE orders
    DROP COLUMN IF EXISTS external_order_id,
    DROP COLUMN IF EXISTS discount,
    DROP COLUMN IF EXISTS tax,
    DROP COLUMN IF EXISTS platform_fee,
    DROP COLUMN IF EXISTS delivery_fee,
    DROP COLUMN IF EXISTS packaging_cost,
    DROP COLUMN IF EXISTS food_cost,
    DROP COLUMN IF EXISTS net_revenue,
    DROP COLUMN IF EXISTS profit,
    DROP COLUMN IF EXISTS cancelled_reason,
    DROP COLUMN IF EXISTS updated_at;

-- Revert menu_items
ALTER TABLE menu_items DROP COLUMN IF EXISTS packaging_cost;

-- Revert users
ALTER TABLE users DROP COLUMN IF EXISTS role;

-- Revert kitchens
ALTER TABLE kitchens
    DROP COLUMN IF EXISTS phone,
    DROP COLUMN IF EXISTS timezone,
    DROP COLUMN IF EXISTS currency,
    DROP COLUMN IF EXISTS updated_at;

-- Mark migration as rolled back
UPDATE schema_migrations
SET rolled_back_at = NOW()
WHERE version = '001_kitcheniq_pro_foundation';

COMMIT;

SELECT 'Rollback complete!' AS status;
