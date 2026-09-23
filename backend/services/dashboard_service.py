"""
Dashboard Analytics Service
---------------------------
Reusable business logic for dashboard summary.
Follows existing patterns from routes/dashboard.py and routes/analytics.py.
"""
from db.connection import execute_query, execute_one


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def safe_int(value):
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


# ============================================================
# KPI CALCULATIONS
# ============================================================

def get_kpi_summary(kitchen_id, days=7):
    """
    Returns KPIs for the dashboard top cards:
    - total_revenue (gross)
    - total_orders
    - net_profit
    - avg_order_value
    - avg_rating (placeholder; ratings not in orders yet)
    - cancellation_rate
    - revenue_growth_pct (vs previous period)
    - orders_growth_pct
    """
    # Current period
    current = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue,
            COALESCE(SUM(net_revenue) FILTER (WHERE status != 'cancelled'), 0) AS net_revenue,
            COALESCE(SUM(profit) FILTER (WHERE status != 'cancelled'), 0) AS profit,
            COALESCE(AVG(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS aov,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total_orders
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days)
    )

    # Previous period (for growth %)
    previous = execute_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE status != 'cancelled') AS orders,
            COALESCE(SUM(total_amount) FILTER (WHERE status != 'cancelled'), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
          AND order_date <  CURRENT_DATE - INTERVAL '%s days'
        """,
        (kitchen_id, days * 2, days)
    )

    orders = safe_int(current["orders"])
    revenue = safe_float(current["revenue"])
    prev_orders = safe_int(previous["orders"]) if previous else 0
    prev_revenue = safe_float(previous["revenue"]) if previous else 0

    def growth_pct(curr, prev):
        if prev <= 0:
            return 0.0
        return round((curr - prev) / prev * 100, 1)

    total = safe_int(current["total_orders"])
    cancelled = safe_int(current["cancelled"])
    cancellation_rate = round(cancelled / max(total, 1) * 100, 1)

    return {
        "total_revenue": round(revenue, 2),
        "total_orders": orders,
        "net_profit": round(safe_float(current["profit"]), 2),
        "net_revenue": round(safe_float(current["net_revenue"]), 2),
        "avg_order_value": round(safe_float(current["aov"]), 2),
        "cancellation_rate": cancellation_rate,
        "avg_rating": 4.4,  # placeholder — ratings API integrate hoga baad mein
        "revenue_growth_pct": growth_pct(revenue, prev_revenue),
        "orders_growth_pct": growth_pct(orders, prev_orders),
    }


# ============================================================
# TREND CALCULATIONS
# ============================================================

def get_trend(kitchen_id, days=7):
    """
    Returns daily revenue & profit for the line chart.
    Output:
        {
            "labels": ["Apr 21", ...],
            "revenue": [...],
            "profit": [...]
        }
    """
    rows = execute_query(
        """
        SELECT
            order_date::text AS date,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY order_date
        ORDER BY order_date
        """,
        (kitchen_id, days)
    )

    labels = []
    revenue = []
    profit = []

    for r in rows:
        labels.append(r["date"])
        revenue.append(round(safe_float(r["revenue"]), 2))
        profit.append(round(safe_float(r["profit"]), 2))

    return {
        "labels": labels,
        "revenue": revenue,
        "profit": profit,
    }


# ============================================================
# PLATFORM BREAKDOWN
# ============================================================

def get_platform_breakdown(kitchen_id, days=7):
    """
    Returns platform-wise gross revenue & commission for bar chart.
    """
    rows = execute_query(
        """
        SELECT
            COALESCE(platform, 'Unknown') AS platform,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS gross_revenue,
            COALESCE(SUM(platform_fee), 0) AS commission,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY platform
        ORDER BY gross_revenue DESC
        """,
        (kitchen_id, days)
    )

    labels = []
    gross = []
    commission = []
    profit = []
    detail = []

    for r in rows:
        p = r["platform"]
        labels.append(p)
        gross.append(round(safe_float(r["gross_revenue"]), 2))
        commission.append(round(safe_float(r["commission"]), 2))
        profit.append(round(safe_float(r["profit"]), 2))
        detail.append({
            "platform": p,
            "orders": safe_int(r["orders"]),
            "gross_revenue": round(safe_float(r["gross_revenue"]), 2),
            "commission": round(safe_float(r["commission"]), 2),
            "profit": round(safe_float(r["profit"]), 2),
        })

    return {
        "labels": labels,
        "gross_revenue": gross,
        "commission": commission,
        "profit": profit,
        "detail": detail,
    }


# ============================================================
# INTEGRATION STATUS
# ============================================================

def get_integration_status(kitchen_id):
    """
    Returns list of integrations for the kitchen.
    Safe to call even if `integrations` table is empty.
    """
    rows = execute_query(
        """
        SELECT
            platform,
            status,
            last_sync_at,
            last_successful_sync,
            last_error
        FROM integrations
        WHERE kitchen_id = %s
        ORDER BY platform
        """,
        (kitchen_id,)
    )

    return [
        {
            "platform": r["platform"],
            "status": r["status"] or "disconnected",
            "last_sync_at": str(r["last_sync_at"]) if r["last_sync_at"] else None,
            "last_successful_sync": str(r["last_successful_sync"]) if r["last_successful_sync"] else None,
            "last_error": r["last_error"],
        }
        for r in rows
    ]
