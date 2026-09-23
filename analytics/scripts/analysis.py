"""
Standalone analytics script.
Computes all key metrics from cleaned order data.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['order_date'] = pd.to_datetime(df['order_date'])
    if 'gross_revenue' not in df.columns:
        df['gross_revenue'] = df['quantity'] * df['unit_price']
    if 'net_revenue' not in df.columns:
        df['net_revenue'] = df['gross_revenue'] * (1 - df['commission_pct'] / 100)
    return df


def kpis(df: pd.DataFrame) -> dict:
    return {
        'total_orders': len(df),
        'gross_revenue': round(df.gross_revenue.sum(), 2),
        'net_revenue': round(df.net_revenue.sum(), 2),
        'commission_paid': round(df.gross_revenue.sum() - df.net_revenue.sum(), 2),
        'avg_order_value': round(df.gross_revenue.mean(), 2),
        'unique_customers': df['customer_phone'].nunique() if 'customer_phone' in df else 0,
    }


def platform_analysis(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby('platform').agg({
        'gross_revenue': 'sum',
        'net_revenue': 'sum',
        'quantity': 'sum',
        'commission_pct': 'mean'
    }).round(2).sort_values('net_revenue', ascending=False)


def item_analysis(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby('item_name').agg({
        'quantity': 'sum',
        'gross_revenue': 'sum',
        'net_revenue': 'sum'
    }).round(2).sort_values('net_revenue', ascending=False)


def menu_engineering(items: pd.DataFrame) -> pd.DataFrame:
    """Classify items into Stars/Plowhorses/Puzzles/Dogs."""
    items = items.copy()
    items['popularity'] = items['quantity']
    items['avg_price'] = items['gross_revenue'] / items['quantity']

    med_qty = items.popularity.median()
    med_rev = items.net_revenue.median()

    def classify(row):
        high_pop = row.popularity > med_qty
        high_rev = row.net_revenue > med_rev
        if high_pop and high_rev:
            return 'Star'
        if high_pop and not high_rev:
            return 'Plowhorse'
        if not high_pop and high_rev:
            return 'Puzzle'
        return 'Dog'

    items['category'] = items.apply(classify, axis=1)
    return items


def customer_analysis(df: pd.DataFrame) -> dict:
    if 'customer_phone' not in df.columns:
        return {}

    cust = df.groupby('customer_phone').agg({
        'gross_revenue': 'sum',
        'order_date': ['min', 'max', 'count']
    })
    cust.columns = ['total_spent', 'first_order', 'last_order', 'frequency']

    # RFM
    today = pd.Timestamp.now().normalize()
    cust['recency_days'] = (today - cust.last_order).dt.days
    cust['monetary'] = cust.total_spent

    return {
        'total_customers': len(cust),
        'repeat_customers': int((cust.frequency >= 2).sum()),
        'repeat_rate': round((cust.frequency >= 2).mean() * 100, 1),
        'avg_customer_value': round(cust.total_spent.mean(), 2),
        'top_10': cust.nlargest(10, 'total_spent').to_dict('index'),
    }


def delivery_analysis(df: pd.DataFrame) -> dict:
    result = {}
    if 'delivery_time' in df.columns:
        result['avg_delivery_time'] = round(df.delivery_time.mean(), 1)
        result['late_orders'] = int((df.delivery_time > 45).sum())
        result['late_pct'] = round((df.delivery_time > 45).mean() * 100, 1)
    if 'prep_time' in df.columns:
        result['avg_prep_time'] = round(df.prep_time.mean(), 1)
    return result


def print_section(title: str):
    print(f'\\n{"=" * 60}')
    print(f'  {title}')
    print(f'{"=" * 60}')


def main():
    if len(sys.argv) < 2:
        path = '../../frontend/assets/sample-data/sample-orders.csv'
    else:
        path = sys.argv[1]

    print(f'📂 Loading: {path}')
    df = load_data(path)

    print_section('KEY METRICS')
    k = kpis(df)
    for key, val in k.items():
        if 'revenue' in key or 'paid' in key or 'value' in key:
            print(f'  {key:.<30} ₹{val:,.2f}')
        else:
            print(f'  {key:.<30} {val:,}')

    print_section('PLATFORM ANALYSIS')
    print(platform_analysis(df).to_string())

    print_section('TOP 10 ITEMS')
    print(item_analysis(df).head(10).to_string())

    print_section('MENU ENGINEERING')
    items = item_analysis(df)
    eng = menu_engineering(items)
    print(eng[['category', 'quantity', 'net_revenue']].to_string())
    print('\\nCategory counts:')
    print(eng.category.value_counts().to_string())

    print_section('CUSTOMER ANALYSIS')
    cust = customer_analysis(df)
    if cust:
        print(f'  Total customers:  {cust["total_customers"]}')
        print(f'  Repeat customers: {cust["repeat_customers"]}')
        print(f'  Repeat rate:      {cust["repeat_rate"]}%')
        print(f'  Avg value:        ₹{cust["avg_customer_value"]:,.2f}')

    print_section('DELIVERY ANALYSIS')
    deliv = delivery_analysis(df)
    for key, val in deliv.items():
        print(f'  {key:.<30} {val}')

    print('\\n✅ Analysis complete')


if __name__ == '__main__':
    main()