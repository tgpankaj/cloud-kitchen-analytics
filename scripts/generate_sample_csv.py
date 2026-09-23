"""
Generate a realistic sample CSV for testing.
Run: python scripts/generate_sample_csv.py
"""
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

NUM_ORDERS = 500
OUTPUT = 'frontend/assets/sample-data/sample-orders-large.csv'

ITEMS = [
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
    ('Paneer Butter Masala', 320, 128),
    ('Chicken Tikka', 340, 136),
    ('Veg Pulao', 200, 80),
]

PLATFORMS = [('Swiggy', 25), ('Zomato', 28), ('Direct', 0)]
PLATFORM_WEIGHTS = [0.45, 0.40, 0.15]


def generate_orders():
    rows = []
    base_date = datetime(2026, 1, 1)
    customers = [f"98765{random.randint(10000, 99999)}" for _ in range(150)]

    for i in range(NUM_ORDERS):
        order_date = base_date + timedelta(days=random.randint(0, 60))
        hour = random.choice([12, 13, 14, 19, 20, 21, 22])
        minute = random.randint(0, 59)

        platform, commission = random.choices(PLATFORMS, weights=PLATFORM_WEIGHTS)[0]
        phone = random.choice(customers)
        item = random.choice(ITEMS)
        qty = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]

        rows.append({
            'order_date': order_date.strftime('%Y-%m-%d'),
            'order_time': f'{hour:02d}:{minute:02d}',
            'platform': platform,
            'customer_phone': phone,
            'item_name': item[0],
            'quantity': qty,
            'unit_price': item[1],
            'commission_pct': commission,
            'prep_time': random.randint(10, 25),
            'delivery_time': random.randint(25, 55),
            'status': random.choices(['delivered', 'cancelled'], weights=[0.95, 0.05])[0],
        })

    return pd.DataFrame(rows)


def main():
    Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)

    print(f'🎲 Generating {NUM_ORDERS} orders...')
    df = generate_orders()
    df.to_csv(OUTPUT, index=False)

    print(f'✅ Saved: {OUTPUT}')
    print(f'   Rows: {len(df)}')
    print(f'   Date range: {df.order_date.min()} to {df.order_date.max()}')
    print(f'   Unique customers: {df.customer_phone.nunique()}')
    print(f'   Unique items: {df.item_name.nunique()}')
    print(f'   Platform split:')
    for p, c in df.platform.value_counts().items():
        print(f'      {p}: {c} orders')


if __name__ == '__main__':
    main()