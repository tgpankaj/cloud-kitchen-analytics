"""
Create a demo user with sample data.
Run: python scripts/seed_demo.py
"""
import psycopg2
import pandas as pd
import os
from datetime import datetime, timedelta
import random
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Create demo user
DEMO_EMAIL = 'demo@kitchenanalytics.in'
DEMO_PASSWORD = 'demo1234'

cur.execute("SELECT id FROM users WHERE email = %s", (DEMO_EMAIL,))
existing = cur.fetchone()

if existing:
    print(f"Demo user exists (id: {existing[0]})")
    user_id = existing[0]
else:
    password_hash = generate_password_hash(DEMO_PASSWORD)
    cur.execute("""
        INSERT INTO users (email, password_hash, full_name)
        VALUES (%s, %s, 'Demo User') RETURNING id
    """, (DEMO_EMAIL, password_hash))
    user_id = cur.fetchone()[0]
    print(f"Created demo user (id: {user_id})")

# Create demo kitchen
cur.execute("SELECT id FROM kitchens WHERE user_id = %s LIMIT 1", (user_id,))
k = cur.fetchone()
if not k:
    cur.execute("""
        INSERT INTO kitchens (user_id, name, city)
        VALUES (%s, 'Demo Kitchen', 'Mumbai') RETURNING id
    """, (user_id,))
    kitchen_id = cur.fetchone()[0]
    print(f"Created kitchen (id: {kitchen_id})")
else:
    kitchen_id = k[0]

# Insert 200 orders
items = [
    ('Paneer Tikka', 300, 120), ('Chicken Biryani', 350, 140),
    ('Dal Makhani', 250, 100), ('Butter Chicken', 400, 160),
    ('Veg Biryani', 220, 88), ('Veg Sandwich', 150, 60),
    ('Cold Coffee', 120, 48), ('Masala Dosa', 180, 72),
]
platforms = [('Swiggy', 25), ('Zomato', 28), ('Direct', 0)]

base = datetime.now() - timedelta(days=60)
added = 0

for i in range(200):
    order_date = base + timedelta(days=random.randint(0, 60))
    hour = random.choice([12, 13, 14, 19, 20, 21])
    platform, comm = random.choice(platforms)
    phone = f"98765{random.randint(10000, 99999)}"
    item = random.choice(items)
    qty = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
    total = qty * item[1]

    cur.execute("""
        INSERT INTO orders (kitchen_id, order_date, order_time, platform,
            customer_phone, total_amount, commission_pct,
            prep_time_minutes, delivery_time_minutes, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'delivered')
        RETURNING id
    """, (kitchen_id, order_date.date(), f"{hour}:00", platform, phone,
          total, comm, random.randint(10, 25), random.randint(25, 55)))
    order_id = cur.fetchone()[0]

    # Menu item
    cur.execute("SELECT id FROM menu_items WHERE kitchen_id = %s AND name = %s",
                (kitchen_id, item[0]))
    mi = cur.fetchone()
    if not mi:
        cur.execute("""
            INSERT INTO menu_items (kitchen_id, name, cost_price, selling_price)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (kitchen_id, item[0], item[2], item[1]))
        mi_id = cur.fetchone()[0]
    else:
        mi_id = mi[0]

    cur.execute("""
        INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price)
        VALUES (%s, %s, %s, %s)
    """, (order_id, mi_id, qty, item[1]))

    added += 1

conn.commit()
print(f"✅ Added {added} orders to demo kitchen")
print(f"\n📧 Demo login: {DEMO_EMAIL}")
print(f"🔑 Password: {DEMO_PASSWORD}")

cur.close()
conn.close()

