"""
Generate a larger sample CSV for testing.
Run: python scripts/generate_sample_csv.py
"""
import pandas as pd
import random
from datetime import datetime, timedelta

# Config
NUM_ORDERS = 500
OUTPUT = 'frontend/assets/sample-data/sample-orders-large.csv'

items = [
    ('Paneer Tikka', 300, 120),
    ('Chicken Biryani', 350, 140),
    ('Dal Makhani', 250, 100),
    ('Butter Chicken', 400, 160),
    ('Veg Biryani', 220, 88),
    ('Veg Sandwich', 150, 60),
    ('Cold Coffee', 120, 48),
    ('Masala Dosa', 180, 72),
    ('Idli Sambar', 100, 40),
    ('Chole Bhature', 200, 80),
    ('Fish Curry', 420, 168),
    ('Mutton Biryani', 450, 180),
]

platforms = ['Swiggy', 'Zomato', 'Direct']
commission_map = {'Swiggy': 25, 'Zomato': 28, 'Direct': 0}

rows = []
base_date = datetime(2026, 1, 1)

for i in range(NUM_ORDERS):
    order_date = base_date + timedelta(days=random.randint(0, 30))
    hour = random.choice([12, 13, 14, 19, 20, 21, 22])
    minute = random.randint(0, 59)
    platform = random.choices(platforms, weights=[45, 40, 15])[0]
    phone = f"98765{random.randint(10000, 99999)}"
    item = random.choice(items)

    rows.append({
        'order_date': order_date.strftime('%Y-%m-%d'),
        'order_time': f"{hour:02d}:{minute:02d}",
        'platform': platform,
        'customer_phone': phone,
        'item_name': item[0],
        'quantity': random.choices([1, 2, 3], weights=[60, 30, 10])[0],
        'unit_price': item[1],
        'commission_pct': commission_map[platform],
        'prep_time': random.randint(10, 25),
        'delivery_time': random.randint(25, 55),
        'status': random.choices(['delivered', 'cancelled'],
                                 weights=[95, 5])[0]
    })

df = pd.DataFrame(rows)
df.to_csv(OUTPUT, index=False)
print(f"✅ Generated {len(df)} orders → {OUTPUT}")
print(f"   Date range: {df['order_date'].min()} to {df['order_date'].max()}")
print(f"   Platforms: {df['platform'].value_counts().to_dict()}")
print(f"   Unique items: {df['item_name'].nunique()}")
print(f"   Unique customers: {df['customer_phone'].nunique()}")