-- ============================================================
-- KitchenIQ Pro — Migration 001
-- Foundation: Extend schema for SaaS + integrations
-- Safe: idempotent, non-breaking, preserves existing data
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 0. Migration tracking table
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(100) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
    rolled_back_at TIMESTAMP
);

-- ------------------------------------------------------------
-- 1. Extend orders table
-- ------------------------------------------------------------
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS external_order_id VARCHAR(150),
    ADD COLUMN IF NOT EXISTS discount NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tax NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS platform_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS delivery_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS packaging_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS food_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS net_revenue NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS profit NUMERIC(10,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cancelled_reason VARCHAR(255),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- ------------------------------------------------------------
-- 2. Extend menu_items table
-- ------------------------------------------------------------
ALTER TABLE menu_items
    ADD COLUMN IF NOT EXISTS packaging_cost NUMERIC(10,2) NOT NULL DEFAULT 0;

-- ------------------------------------------------------------
-- 3. Add role to users
-- ------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'owner';

-- ------------------------------------------------------------
-- 4. Extend kitchens table
-- ------------------------------------------------------------
ALTER TABLE kitchens
    ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();

-- ------------------------------------------------------------
-- 5. Deduplication unique index
-- ------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_external_dedup
    ON orders(kitchen_id, platform, external_order_id)
    WHERE external_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_updated ON orders(updated_at DESC);

-- ------------------------------------------------------------
-- 6. Table: kitchen_users (team members)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kitchen_users (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'staff',
    invited_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(kitchen_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_kitchen_users_kitchen ON kitchen_users(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_users_user ON kitchen_users(user_id);

-- ------------------------------------------------------------
-- 7. Table: integrations
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS integrations (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'disconnected',
    auth_type VARCHAR(50),
    credentials_encrypted TEXT,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    last_sync_at TIMESTAMP,
    last_successful_sync TIMESTAMP,
    last_error TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(kitchen_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_integrations_kitchen ON integrations(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_integrations_status ON integrations(status);
CREATE INDEX IF NOT EXISTS idx_integrations_platform ON integrations(platform);

-- ------------------------------------------------------------
-- 8. Table: sync_logs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_logs (
    id SERIAL PRIMARY KEY,
    integration_id INTEGER NOT NULL REFERENCES integrations(id) ON DELETE CASCADE,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    records_fetched INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_sync_logs_integration ON sync_logs(integration_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_kitchen ON sync_logs(kitchen_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);

-- ------------------------------------------------------------
-- 9. Table: audit_logs
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    resource_id VARCHAR(100),
    metadata JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_kitchen ON audit_logs(kitchen_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- ------------------------------------------------------------
-- 10. Backfill: existing orders ke new fields calculate karo
-- ------------------------------------------------------------
UPDATE orders
SET
    platform_fee = ROUND(total_amount * COALESCE(commission_pct, 0) / 100.0, 2),
    net_revenue  = ROUND(total_amount * (1 - COALESCE(commission_pct, 0) / 100.0), 2),
    profit       = ROUND(total_amount * (1 - COALESCE(commission_pct, 0) / 100.0), 2)
WHERE total_amount > 0
  AND net_revenue = 0;

-- ------------------------------------------------------------
-- 11. Backfill: existing kitchens ke owners ko kitchen_users mein daalo
-- ------------------------------------------------------------
INSERT INTO kitchen_users (kitchen_id, user_id, role, accepted_at)
SELECT id, user_id, 'owner', NOW()
FROM kitchens
WHERE user_id IS NOT NULL
ON CONFLICT (kitchen_id, user_id) DO NOTHING;

-- ------------------------------------------------------------
-- 12. Record migration
-- ------------------------------------------------------------
INSERT INTO schema_migrations (version)
VALUES ('001_kitcheniq_pro_foundation')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- ============================================================
-- DONE
-- ============================================================
