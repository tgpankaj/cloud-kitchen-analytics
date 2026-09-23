-- ============================================
-- CLOUD KITCHEN ANALYTICS - SCHEMA
-- ============================================

DROP TABLE IF EXISTS uploads CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS recipes CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS menu_items CASCADE;
DROP TABLE IF EXISTS kitchens CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- USERS
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- KITCHENS
CREATE TABLE kitchens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- MENU ITEMS
CREATE TABLE menu_items (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    cost_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    selling_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    prep_time_minutes INTEGER DEFAULT 15,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- INGREDIENTS
CREATE TABLE ingredients (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50),
    cost_per_unit NUMERIC(10, 2) DEFAULT 0,
    current_stock NUMERIC(10, 2) DEFAULT 0,
    reorder_threshold NUMERIC(10, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RECIPES
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
    ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity_required NUMERIC(10, 3) NOT NULL
);

-- ORDERS
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    order_date DATE NOT NULL,
    order_time TIME,
    platform VARCHAR(50) NOT NULL,
    customer_phone VARCHAR(15),
    total_amount NUMERIC(10, 2) DEFAULT 0,
    commission_pct NUMERIC(5, 2) DEFAULT 25,
    delivery_time_minutes INTEGER,
    prep_time_minutes INTEGER,
    status VARCHAR(50) DEFAULT 'delivered',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ORDER ITEMS
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

-- CUSTOMERS
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    phone VARCHAR(15),
    first_order_date DATE,
    last_order_date DATE,
    total_orders INTEGER DEFAULT 0,
    total_spent NUMERIC(10, 2) DEFAULT 0,
    UNIQUE(kitchen_id, phone)
);

-- UPLOADS LOG
CREATE TABLE uploads (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER REFERENCES kitchens(id) ON DELETE CASCADE,
    filename VARCHAR(255),
    rows_inserted INTEGER DEFAULT 0,
    rows_failed INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- INDEXES
CREATE INDEX idx_orders_kitchen_date ON orders(kitchen_id, order_date DESC);
CREATE INDEX idx_orders_platform ON orders(platform);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_menu ON order_items(menu_item_id);
CREATE INDEX idx_menu_items_kitchen ON menu_items(kitchen_id);
CREATE INDEX idx_customers_kitchen ON customers(kitchen_id);
CREATE INDEX idx_customers_phone ON customers(phone);

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT 'Schema created successfully!' AS status;





CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,          -- 'starter', 'pro', 'business'
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'cancelled', 'expired'
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    amount NUMERIC(10, 2),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

