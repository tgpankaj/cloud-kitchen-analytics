"""
CSV Processor Service
Handles cleaning, validation, and insertion of order data.
"""
import pandas as pd
import numpy as np
from db.connection import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor


REQUIRED_COLUMNS = [
    'order_date', 'platform', 'item_name',
    'quantity', 'unit_price'
]

OPTIONAL_COLUMNS = [
    'order_time', 'customer_phone', 'commission_pct',
    'prep_time', 'delivery_time', 'status'
]


class CSVValidationError(Exception):
    """Raised when CSV validation fails."""
    pass


def validate_csv(df):
    """Validate CSV structure and columns."""
    # Standardize column names
    df.columns = (df.columns
                  .str.lower()
                  .str.strip()
                  .str.replace(' ', '_')
                  .str.replace('-', '_'))

    # Check required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CSVValidationError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Required: {', '.join(REQUIRED_COLUMNS)}"
        )

    # Check for empty file
    if len(df) == 0:
        raise CSVValidationError("CSV file is empty")

    # Check for excessive rows (safety limit)
    if len(df) > 50000:
        raise CSVValidationError(
            f"CSV has {len(df)} rows. Maximum 50,000 rows per upload."
        )

    return df


def clean_csv(df):
    """Clean and standardize CSV data."""
    df = validate_csv(df.copy())

    # ─── Dates ───
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    invalid_dates = df['order_date'].isna().sum()
    df = df.dropna(subset=['order_date'])

    # ─── Numeric columns ───
    df['quantity'] = (pd.to_numeric(df['quantity'], errors='coerce')
                      .fillna(1).astype(int))
    df['unit_price'] = (pd.to_numeric(df['unit_price'], errors='coerce')
                        .fillna(0).astype(float))

    if 'commission_pct' in df.columns:
        df['commission_pct'] = (pd.to_numeric(df['commission_pct'], errors='coerce')
                                .fillna(25).clip(0, 50))
    else:
        df['commission_pct'] = 25.0

    if 'prep_time' in df.columns:
        df['prep_time'] = (pd.to_numeric(df['prep_time'], errors='coerce')
                           .fillna(15).clip(1, 120).astype(int))
    else:
        df['prep_time'] = 15

    if 'delivery_time' in df.columns:
        df['delivery_time'] = (pd.to_numeric(df['delivery_time'], errors='coerce')
                               .fillna(30).clip(1, 180).astype(int))
    else:
        df['delivery_time'] = 30

    # ─── Text columns ───
    df['item_name'] = df['item_name'].astype(str).str.strip().str.title()
    df['platform'] = df['platform'].astype(str).str.strip().str.title()

    # Platform standardization
    platform_map = {
        'Swiggy': 'Swiggy', 'Zomato': 'Zomato',
        'Direct': 'Direct', 'Own': 'Direct',
        'Whatsapp': 'Direct', 'Phone': 'Direct'
    }
    df['platform'] = df['platform'].map(platform_map).fillna(df['platform'])

    if 'customer_phone' in df.columns:
        df['customer_phone'] = (df['customer_phone']
                                .astype(str)
                                .str.strip()
                                .str.replace(r'\D', '', regex=True))
        df.loc[df['customer_phone'].isin(['', 'nan', 'None']), 'customer_phone'] = None
    else:
        df['customer_phone'] = None

    if 'order_time' not in df.columns:
        df['order_time'] = None

    if 'status' not in df.columns:
        df['status'] = 'delivered'
    df['status'] = df['status'].astype(str).str.strip().str.lower()

    # ─── Filter invalid ───
    df = df[df['quantity'] > 0]
    df = df[df['unit_price'] >= 0]
    df = df[df['item_name'].str.len() > 0]

    # ─── Remove duplicates ───
    df = df.drop_duplicates(
        subset=['order_date', 'item_name', 'customer_phone', 'platform'],
        keep='first'
    )

    return df, invalid_dates


def process_orders_csv(df, kitchen_id):
    """
    Main processor: clean CSV → insert into database.
    Returns dict with statistics.
    """
    df, invalid_dates = clean_csv(df)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    stats = {
        'total_rows': len(df),
        'inserted': 0,
        'failed': 0,
        'new_items': 0,
        'new_customers': 0,
        'invalid_dates': int(invalid_dates),
        'errors': []
    }

    try:
        # Build order key (unique per order)
        df['order_key'] = (
            df['order_date'].astype(str) + '_' +
            df['customer_phone'].fillna('guest').astype(str) + '_' +
            df['platform'].astype(str) + '_' +
            df['order_time'].fillna('00:00').astype(str)
        )

        # ─── Process each order ───
        for order_key, group in df.groupby('order_key'):
            try:
                first = group.iloc[0]
                total_amount = float(
                    (group['quantity'] * group['unit_price']).sum()
                )

                # Insert order
                order_time_val = first['order_time']
                if pd.isna(order_time_val) or order_time_val == 'None':
                    order_time_val = None

                cur.execute("""
                    INSERT INTO orders (
                        kitchen_id, order_date, order_time, platform,
                        customer_phone, total_amount, commission_pct,
                        prep_time_minutes, delivery_time_minutes, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    kitchen_id,
                    first['order_date'].date(),
                    order_time_val,
                    first['platform'],
                    first['customer_phone'],
                    total_amount,
                    float(first['commission_pct']),
                    int(first['prep_time']),
                    int(first['delivery_time']),
                    first['status']
                ))
                order_id = cur.fetchone()['id']

                # ─── Insert order items ───
                for _, item in group.iterrows():
                    # Find or create menu item
                    cur.execute("""
                        SELECT id FROM menu_items
                        WHERE kitchen_id = %s AND name = %s
                    """, (kitchen_id, item['item_name']))
                    mi = cur.fetchone()

                    if not mi:
                        # Auto-create with 40% estimated cost
                        est_cost = float(item['unit_price']) * 0.4
                        cur.execute("""
                            INSERT INTO menu_items (
                                kitchen_id, name, cost_price,
                                selling_price, prep_time_minutes
                            ) VALUES (%s, %s, %s, %s, %s)
                            RETURNING id
                        """, (
                            kitchen_id,
                            item['item_name'],
                            est_cost,
                            float(item['unit_price']),
                            int(item['prep_time'])
                        ))
                        mi_id = cur.fetchone()['id']
                        stats['new_items'] += 1
                    else:
                        mi_id = mi['id']

                    cur.execute("""
                        INSERT INTO order_items (
                            order_id, menu_item_id, quantity, unit_price
                        ) VALUES (%s, %s, %s, %s)
                    """, (
                        order_id, mi_id,
                        int(item['quantity']),
                        float(item['unit_price'])
                    ))

                # ─── Update customer aggregate ───
                if first['customer_phone']:
                    cur.execute("""
                        INSERT INTO customers (
                            kitchen_id, phone, first_order_date,
                            last_order_date, total_orders, total_spent
                        ) VALUES (%s, %s, %s, %s, 1, %s)
                        ON CONFLICT (kitchen_id, phone) DO UPDATE SET
                            last_order_date = GREATEST(customers.last_order_date,
                                                       EXCLUDED.last_order_date),
                            total_orders = customers.total_orders + 1,
                            total_spent = customers.total_spent + EXCLUDED.total_spent
                        RETURNING id
                    """, (
                        kitchen_id,
                        first['customer_phone'],
                        first['order_date'].date(),
                        first['order_date'].date(),
                        total_amount
                    ))
                    result = cur.fetchone()
                    if result and cur.rowcount == 1:
                        stats['new_customers'] += 1

                stats['inserted'] += 1

            except Exception as e:
                stats['failed'] += 1
                if len(stats['errors']) < 10:
                    stats['errors'].append(f"Row {order_key}: {str(e)[:100]}")
                continue

        # ─── Log upload ───
        cur.execute("""
            INSERT INTO uploads (
                kitchen_id, filename, rows_inserted, rows_failed
            ) VALUES (%s, %s, %s, %s)
        """, (
            kitchen_id,
            'uploaded.csv',
            stats['inserted'],
            stats['failed']
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        release_db_connection(conn)

    return stats

