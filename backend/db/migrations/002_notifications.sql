-- ============================================================
-- KitchenIQ Pro — Migration 002
-- Notifications system
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    title VARCHAR(255) NOT NULL,
    message TEXT,
    link VARCHAR(500),
    metadata JSONB,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications(user_id, is_read, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_kitchen
    ON notifications(kitchen_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_type
    ON notifications(type);

INSERT INTO schema_migrations (version)
VALUES ('002_notifications')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 002 applied!' AS status;
