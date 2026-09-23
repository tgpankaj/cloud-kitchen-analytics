"""
Standalone data cleaning script.
Run: python analytics/scripts/cleaning.py
Input:  raw CSV file
Output: cleaned CSV file
"""
import pandas as pd
import sys
from pathlib import Path


REQUIRED_COLUMNS = ['order_date', 'platform', 'item_name', 'quantity', 'unit_price']


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Full cleaning pipeline."""
    df = df.copy()

    # Standardize column names
    df.columns = (
        df.columns.str.lower()
        .str.strip()
        .str.replace(' ', '_')
        .str.replace('-', '_')
    )

    # Validate required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')

    # Date parsing
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    df = df.dropna(subset=['order_date'])

    # Numeric coercion
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1).astype(int)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0).astype(float)

    if 'commission_pct' in df.columns:
        df['commission_pct'] = (
            pd.to_numeric(df['commission_pct'], errors='coerce')
            .fillna(25)
            .clip(0, 50)
        )
    else:
        df['commission_pct'] = 25.0

    # Text cleanup
    df['item_name'] = df['item_name'].astype(str).str.strip().str.title()
    df['platform'] = df['platform'].astype(str).str.strip().str.title()

    # Platform standardization
    platform_map = {
        'Swiggy': 'Swiggy',
        'Zomato': 'Zomato',
        'Direct': 'Direct',
        'Own': 'Direct',
        'Whatsapp': 'Direct'
    }
    df['platform'] = df['platform'].map(platform_map).fillna(df['platform'])

    # Filter invalid
    df = df[df['quantity'] > 0]
    df = df[df['unit_price'] >= 0]
    df = df[df['item_name'].str.len() > 0]

    # Remove duplicates
    dup_cols = ['order_date', 'item_name', 'platform']
    if 'customer_phone' in df.columns:
        dup_cols.append('customer_phone')
    df = df.drop_duplicates(subset=dup_cols)

    # Add computed columns
    df['gross_revenue'] = df['quantity'] * df['unit_price']
    df['net_revenue'] = df['gross_revenue'] * (1 - df['commission_pct'] / 100)

    # Sort
    df = df.sort_values('order_date').reset_index(drop=True)

    return df


def main():
    if len(sys.argv) < 2:
        print('Usage: python cleaning.py <input_csv> [output_csv]')
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_name(
        f'{input_path.stem}_cleaned{input_path.suffix}'
    )

    if not input_path.exists():
        print(f'❌ File not found: {input_path}')
        sys.exit(1)

    print(f'📂 Reading: {input_path}')
    df = pd.read_csv(input_path)
    print(f'   Rows: {len(df)}, Columns: {len(df.columns)}')

    print('🧹 Cleaning...')
    cleaned = clean_orders(df)
    print(f'   Cleaned rows: {len(cleaned)}')

    cleaned.to_csv(output_path, index=False)
    print(f'✅ Saved: {output_path}')

    # Summary
    print('\\n📊 Summary:')
    print(f'   Total gross revenue: ₹{cleaned.gross_revenue.sum():,.0f}')
    print(f'   Total net revenue:   ₹{cleaned.net_revenue.sum():,.0f}')
    print(f'   Unique items:        {cleaned.item_name.nunique()}')
    print(f'   Unique platforms:    {cleaned.platform.nunique()}')
    print(f'   Date range:          {cleaned.order_date.min().date()} to {cleaned.order_date.max().date()}')


if __name__ == '__main__':
    main()