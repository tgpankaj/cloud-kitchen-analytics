-- ============================================
-- SEED DATA — Demo content for development
-- Run in psql: \i backend/db/seed.sql
-- WARNING: This will insert demo data. Skip in production.
-- ============================================

-- Demo user (password: demo1234)
INSERT INTO users (email, password_hash, full_name)
VALUES (
    'demo@kitchenanalytics.in',
    'pbkdf2:sha256:600000$demo$0000000000000000000000000000000000000000000000000000000000000000',
    'Demo User'
)
ON CONFLICT (email) DO NOTHING;

-- Demo kitchen
INSERT INTO kitchens (user_id, name, city, address)
SELECT id, 'Demo Kitchen — Mumbai', 'Mumbai', 'Bandra West, Mumbai'
FROM users WHERE email = 'demo@kitchenanalytics.in'
ON CONFLICT DO NOTHING;

-- Sample ingredients
INSERT INTO ingredients (kitchen_id, name, unit, cost_per_unit, current_stock, reorder_threshold)
SELECT k.id, i.name, i.unit, i.cost, i.stock, i.reorder
FROM kitchens k
CROSS JOIN (VALUES
    ('Paneer', 'kg', 320.00, 5.0, 2.0),
    ('Chicken', 'kg', 240.00, 8.0, 3.0),
    ('Rice', 'kg', 60.00, 25.0, 10.0),
    ('Wheat Flour', 'kg', 45.00, 15.0, 5.0),
    ('Onion', 'kg', 35.00, 10.0, 4.0),
    ('Tomato', 'kg', 40.00, 8.0, 3.0),
    ('Butter', 'kg', 480.00, 3.0, 1.0),
    ('Cream', 'l', 220.00, 5.0, 2.0),
    ('Cooking Oil', 'l', 130.00, 10.0, 3.0),
    ('Spices Mix', 'kg', 600.00, 2.0, 0.5)
) AS i(name, unit, cost, stock, reorder)
WHERE k.name = 'Demo Kitchen — Mumbai'
  AND NOT EXISTS (
      SELECT 1 FROM ingredients WHERE kitchen_id = k.id AND name = i.name
  );

-- Sample menu items
INSERT INTO menu_items (kitchen_id, name, category, cost_price, selling_price, prep_time_minutes)
SELECT k.id, m.name, m.cat, m.cost, m.price, m.prep
FROM kitchens k
CROSS JOIN (VALUES
    ('Paneer Tikka', 'Starters', 120, 300, 15),
    ('Chicken Biryani', 'Main Course', 140, 350, 20),
    ('Dal Makhani', 'Main Course', 100, 250, 12),
    ('Butter Chicken', 'Main Course', 160, 400, 18),
    ('Veg Biryani', 'Main Course', 88, 220, 15),
    ('Veg Sandwich', 'Snacks', 60, 150, 8),
    ('Cold Coffee', 'Beverages', 48, 120, 5),
    ('Masala Dosa', 'South Indian', 72, 180, 12)
) AS m(name, cat, cost, price, prep)
WHERE k.name = 'Demo Kitchen — Mumbai'
  AND NOT EXISTS (
      SELECT 1 FROM menu_items WHERE kitchen_id = k.id AND name = m.name
  );

-- Note: Orders are NOT seeded here.
-- Upload a CSV via the app, or run scripts/seed_demo.py for full demo data.

-- Verification
DO $$
DECLARE
    user_count INT;
    kitchen_count INT;
    ingredient_count INT;
    item_count INT;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO kitchen_count FROM kitchens;
    SELECT COUNT(*) INTO ingredient_count FROM ingredients;
    SELECT COUNT(*) INTO item_count FROM menu_items;

    RAISE NOTICE '======================================';
    RAISE NOTICE '  Seed data summary:';
    RAISE NOTICE '  Users:       %', user_count;
    RAISE NOTICE '  Kitchens:    %', kitchen_count;
    RAISE NOTICE '  Ingredients: %', ingredient_count;
    RAISE NOTICE '  Menu Items:  %', item_count;
    RAISE NOTICE '======================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Demo login: demo@kitchenanalytics.in';
    RAISE NOTICE 'Password:   demo1234';
    RAISE NOTICE '(Note: password only works if seeded via seed_demo.py)';
END $$;