"""
Seed sample ingredients and recipes for testing.
Run: python scripts/seed_ingredients.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL')

# Sample ingredients (per kitchen)
SAMPLE_INGREDIENTS = [
    ('Paneer', 'kg', 320.00, 5.0, 2.0),
    ('Chicken', 'kg', 240.00, 8.0, 3.0),
    ('Rice', 'kg', 60.00, 25.0, 10.0),
    ('Wheat Flour', 'kg', 45.00, 15.0, 5.0),
    ('Onion', 'kg', 35.00, 10.0, 4.0),
    ('Tomato', 'kg', 40.00, 8.0, 3.0),
    ('Butter', 'kg', 480.00, 3.0, 1.0),
    ('Cream', 'l', 220.00, 5.0, 2.0),
    ('Cooking Oil', 'l', 130.00, 10.0, 3.0),
    ('Spices Mix', 'kg', 600.00, 2.0, 0.5),
    ('Yogurt', 'kg', 80.00, 4.0, 2.0),
    ('Ginger Garlic Paste', 'kg', 150.00, 2.0, 0.5),
]

# Sample recipes (item_name → list of (ingredient_name, qty))
SAMPLE_RECIPES = {
    'Paneer Tikka': [('Paneer', 0.2), ('Yogurt', 0.05), ('Spices Mix', 0.02)],
    'Chicken Biryani': [('Chicken', 0.25), ('Rice', 0.15), ('Onion', 0.1), ('Spices Mix', 0.03)],
    'Dal Makhani': [('Butter', 0.05), ('Cream', 0.05), ('Onion', 0.05), ('Tomato', 0.05)],
    'Butter Chicken': [('Chicken', 0.3), ('Butter', 0.06), ('Cream', 0.08), ('Tomato', 0.1)],
    'Veg Biryani': [('Rice', 0.15), ('Onion', 0.08), ('Tomato', 0.05), ('Spices Mix', 0.02)],
}


def seed():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        # Get all kitchens
        cur.execute("SELECT id FROM kitchens WHERE is_active = TRUE")
        kitchens = cur.fetchall()

        if not kitchens:
            print("❌ No kitchens found. Create a user first via signup.")
            return

        print(f"Found {len(kitchens)} kitchen(s)")

        for (kitchen_id,) in kitchens:
            print(f"\n→ Kitchen {kitchen_id}")

            # Insert ingredients (skip if exists)
            ing_map = {}
            for name, unit, cost, stock, reorder in SAMPLE_INGREDIENTS:
                cur.execute("""
                    SELECT id FROM ingredients
                    WHERE kitchen_id = %s AND LOWER(name) = LOWER(%s)
                """, (kitchen_id, name))
                existing = cur.fetchone()

                if existing:
                    ing_map[name] = existing[0]
                    continue

                cur.execute("""
                    INSERT INTO ingredients
                    (kitchen_id, name, unit, cost_per_unit, current_stock, reorder_threshold)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (kitchen_id, name, unit, cost, stock, reorder))
                ing_map[name] = cur.fetchone()[0]

            print(f"  ✅ {len(ing_map)} ingredients ready")

            # Insert recipes
            recipes_added = 0
            for item_name, ingredients in SAMPLE_RECIPES.items():
                # Find menu item
                cur.execute("""
                    SELECT id FROM menu_items
                    WHERE kitchen_id = %s AND LOWER(name) = LOWER(%s)
                """, (kitchen_id, item_name))
                item = cur.fetchone()

                if not item:
                    continue
                item_id = item[0]

                for ing_name, qty in ingredients:
                    ing_id = ing_map.get(ing_name)
                    if not ing_id:
                        continue

                    # Check duplicate
                    cur.execute("""
                        SELECT id FROM recipes
                        WHERE menu_item_id = %s AND ingredient_id = %s
                    """, (item_id, ing_id))
                    if cur.fetchone():
                        continue

                    cur.execute("""
                        INSERT INTO recipes (menu_item_id, ingredient_id, quantity_required)
                        VALUES (%s, %s, %s)
                    """, (item_id, ing_id, qty))
                    recipes_added += 1

            print(f"  ✅ {recipes_added} recipe entries added")

        conn.commit()
        print("\n🎉 Seeding complete!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    seed()