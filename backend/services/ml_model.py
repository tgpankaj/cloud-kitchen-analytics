import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from typing import Optional


def prepare_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features from order_date."""
    df = df.copy()
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['day_of_week'] = df['order_date'].dt.dayofweek
    df['day_of_month'] = df['order_date'].dt.day
    df['month'] = df['order_date'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    return df


def forecast_item_demand(
    item_df: pd.DataFrame,
    days_ahead: int = 7,
    min_history: int = 14
) -> Optional[dict]:
    """
    Forecast demand for a single item.
    Returns None if insufficient data.
    """
    if len(item_df) < min_history:
        return None

    df = prepare_time_features(item_df)
    df = df.sort_values('order_date')

    features = ['day_of_week', 'day_of_month', 'month', 'is_weekend']
    X = df[features]
    y = df['quantity']

    # Train/test split
    split = max(int(len(df) * 0.8), min_history - 4)
    if split < 10:
        return None

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X[:split], y[:split])
    mae = mean_absolute_error(y[split:], model.predict(X[split:]))

    # Predict next N days
    last_date = df['order_date'].max()
    future_dates = pd.date_range(
        last_date + pd.Timedelta(days=1),
        periods=days_ahead
    )
    future_X = pd.DataFrame({
        'day_of_week': future_dates.dayofweek,
        'day_of_month': future_dates.day,
        'month': future_dates.month,
        'is_weekend': future_dates.dayofweek.isin([5, 6]).astype(int)
    })

    preds = np.maximum(0, model.predict(future_X))

    return {
        'item_name': df.iloc[0].get('item_name', 'Unknown'),
        'predicted_weekly': int(round(preds.sum())),
        'daily_predictions': [
            {'date': str(d.date()), 'predicted': int(round(p))}
            for d, p in zip(future_dates, preds)
        ],
        'confidence_mae': round(float(mae), 2),
    }


def forecast_top_items(
    sales_df: pd.DataFrame,
    top_n: int = 10,
    days_ahead: int = 7
) -> list:
    """
    Forecast top N items by historical volume.
    Returns sorted list by predicted weekly demand.
    """
    if sales_df.empty:
        return []

    df = prepare_time_features(sales_df)

    # Aggregate per item per day
    daily = df.groupby([
        'item_name', 'order_date', 'day_of_week',
        'day_of_month', 'month', 'is_weekend'
    ]).agg({'quantity': 'sum'}).reset_index()

    # Top N items
    top_items = (
        daily.groupby('item_name')['quantity'].sum()
        .nlargest(top_n).index.tolist()
    )

    results = []
    for item in top_items:
        item_df = daily[daily.item_name == item]
        forecast = forecast_item_demand(item_df, days_ahead)
        if forecast:
            results.append(forecast)

    return sorted(results, key=lambda x: x['predicted_weekly'], reverse=True)


def predict_churn_probability(customers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Simple churn risk scoring.
    Uses recency, frequency, monetary.
    """
    if customers_df.empty:
        return customers_df

    df = customers_df.copy()

    # Normalize
    def norm(series):
        mn, mx = series.min(), series.max()
        if mx == mn:
            return pd.Series([0.5] * len(series), index=series.index)
        return (series - mn) / (mx - mn)

    # Churn score: high recency + low frequency + low monetary = high risk
    df['recency_score'] = norm(df['recency_days'])
    df['frequency_score'] = 1 - norm(df['frequency'])
    df['monetary_score'] = 1 - norm(df['monetary'])

    df['churn_probability'] = (
        df['recency_score'] * 0.5 +
        df['frequency_score'] * 0.3 +
        df['monetary_score'] * 0.2
    ).round(3)

    df['risk_level'] = pd.cut(
        df['churn_probability'],
        bins=[0, 0.4, 0.7, 1.0],
        labels=['Low', 'Medium', 'High']
    )

    return df