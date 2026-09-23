"""
Demand forecasting using Random Forest.
Predicts order volume for next 7 days per item.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from pathlib import Path
import sys
import json


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature engineering for time series."""
    df = df.copy()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['day_of_week'] = df['order_date'].dt.dayofweek
    df['day_of_month'] = df['order_date'].dt.day
    df['month'] = df['order_date'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    return df


def forecast_item(group: pd.DataFrame, days_ahead: int = 7) -> dict:
    """Forecast for one item."""
    if len(group) < 14:
        return None

    group = group.sort_values('order_date')
    X = group[['day_of_week', 'day_of_month', 'month', 'is_weekend']]
    y = group['quantity']

    # Train/test split
    split = int(len(group) * 0.8)
    if split < 10:
        return None

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X[:split], y[:split])
    mae = mean_absolute_error(y[split:], model.predict(X[split:]))

    # Predict next 7 days
    last_date = group['order_date'].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days_ahead)
    future_X = pd.DataFrame({
        'day_of_week': future_dates.dayofweek,
        'day_of_month': future_dates.day,
        'month': future_dates.month,
        'is_weekend': future_dates.dayofweek.isin([5, 6]).astype(int)
    })

    preds = model.predict(future_X)

    return {
        'item_name': group.iloc[0]['item_name'],
        'predicted_weekly': int(round(preds.sum())),
        'daily': [
            {'date': str(d.date()), 'predicted': max(0, int(round(p)))}
            for d, p in zip(future_dates, preds)
        ],
        'mae': round(float(mae), 2),
    }


def forecast_all(df: pd.DataFrame, top_n: int = 10) -> list:
    """Forecast top N items."""
    df = prepare_features(df)

    # Aggregate per item per day
    daily = df.groupby(['item_name', 'order_date', 'day_of_week',
                        'day_of_month', 'month', 'is_weekend']).agg({
        'quantity': 'sum'
    }).reset_index()

    # Top N by total quantity
    top_items = (
        daily.groupby('item_name')['quantity'].sum()
        .nlargest(top_n).index.tolist()
    )

    results = []
    for item in top_items:
        group = daily[daily.item_name == item]
        forecast = forecast_item(group)
        if forecast:
            results.append(forecast)

    return sorted(results, key=lambda x: x['predicted_weekly'], reverse=True)


def main():
    if len(sys.argv) < 2:
        path = '../../frontend/assets/sample-data/sample-orders.csv'
    else:
        path = sys.argv[1]

    print(f'📂 Loading: {path}')
    df = pd.read_csv(path)

    print('🤖 Training models...')
    forecasts = forecast_all(df, top_n=10)

    print(f'\\n📊 Forecasts for next 7 days (Top {len(forecasts)} items):\\n')
    for f in forecasts:
        print(f"  {f['item_name']:.<30} {f['predicted_weekly']:>4} units "
              f"(MAE: {f['mae']})")

    # Save
    output = Path('forecast_output.json')
    output.write_text(json.dumps(forecasts, indent=2))
    print(f'\\n✅ Saved: {output}')


if __name__ == '__main__':
    main()