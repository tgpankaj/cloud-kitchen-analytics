"""
KitchenIQ Pro — Insights Engine (Upgraded)

Uses new fields: profit, platform_fee, food_cost, packaging_cost, net_revenue.

Insight types:
- PROMOTE / success     — High margin + demand
- OPPORTUNITY / info    — Growth potential
- OPTIMIZE / warning    — Cost or margin issues
- REVIEW / danger       — Underperformers, risks

Every insight includes:
- title, category, type
- reason (human readable)
- supporting_metrics (numbers)
- suggested_action
- confidence (0.0 – 1.0)
"""
from db.connection import execute_query, execute_one


def _float(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _int(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


def _date_filter(days, alias="o"):
    if days is None:
        return "", []
    return (
        f"AND {alias}.order_date >= CURRENT_DATE - INTERVAL '%s days'",
        [int(days)],
    )


def generate_insights(kitchen_id, days=30):
    """Main entry — returns list of insight dicts."""
    insights = []
    insights += _dish_profitability(kitchen_id, days)
    insights += _platform_commission(kitchen_id, days)
    insights += _discount_analysis(kitchen_id, days)
    insights += _cancellation_analysis(kitchen_id, days)
    insights += _peak_hours(kitchen_id, days)
    insights += _repeat_customers(kitchen_id, days)

    priority = {"danger": 0, "warning": 1, "info": 2, "success": 3}
    insights.sort(key=lambda i: priority.get(i.get("type", "info"), 99))
    return insights


def _dish_profitability(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT
            mi.id, mi.name, mi.category,
            COALESCE(SUM(oi.quantity), 0) AS qty,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue,
            COALESCE(SUM(oi.quantity * COALESCE(mi.cost_price, 0)), 0) AS food_cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {df}
        GROUP BY mi.id, mi.name, mi.category
        HAVING SUM(oi.quantity) > 0
        ORDER BY revenue DESC
        """,
        [kitchen_id] + dp
    )

    if not rows:
        return []

    margins = []
    for r in rows:
        rev = _float(r["revenue"])
        cost = _float(r["food_cost"])
        margins.append(((rev - cost) / rev * 100) if rev > 0 else 0)
    avg_margin = sum(margins) / len(margins) if margins else 0

    insights = []

    # High-margin winner
    high_margin = [r for r in rows if _float(r["qty"]) >= 5]
    if high_margin:
        best = max(
            high_margin,
            key=lambda r: (_float(r["revenue"]) - _float(r["food_cost"])) / max(_float(r["revenue"]), 1)
        )
        rev = _float(best["revenue"])
        cost = _float(best["food_cost"])
        margin = ((rev - cost) / rev * 100) if rev > 0 else 0

        if margin > avg_margin + 5:
            insights.append({
                "type": "success",
                "category": "Menu",
                "title": best["name"],
                "reason": f"High profit margin ({margin:.1f}%) vs your average ({avg_margin:.1f}%). Strong performer.",
                "supporting_metrics": {
                    "revenue": round(rev, 2),
                    "food_cost": round(cost, 2),
                    "profit": round(rev - cost, 2),
                    "margin_pct": round(margin, 1),
                    "quantity_sold": _int(best["qty"]),
                },
                "suggested_action": "Increase visibility during peak hours (7–10 PM). Consider small price premium.",
                "confidence": min(0.95, 0.6 + _int(best["qty"]) / 100),
            })

    # Low-margin worrier
    low_margin = [r for r in rows if _float(r["qty"]) >= 3]
    if low_margin:
        worst = min(
            low_margin,
            key=lambda r: (_float(r["revenue"]) - _float(r["food_cost"])) / max(_float(r["revenue"]), 1)
        )
        rev = _float(worst["revenue"])
        cost = _float(worst["food_cost"])
        margin = ((rev - cost) / rev * 100) if rev > 0 else 0

        if margin < avg_margin - 5:
            insights.append({
                "type": "warning",
                "category": "Menu",
                "title": worst["name"],
                "reason": f"Low margin ({margin:.1f}%) vs your average ({avg_margin:.1f}%). Reprice or cut cost.",
                "supporting_metrics": {
                    "revenue": round(rev, 2),
                    "food_cost": round(cost, 2),
                    "profit": round(rev - cost, 2),
                    "margin_pct": round(margin, 1),
                    "quantity_sold": _int(worst["qty"]),
                },
                "suggested_action": "Review recipe costing. If costs cannot be reduced, increase price by 5–8%.",
                "confidence": 0.85,
            })

    # Critical: very low margin item with revenue
    for r in rows:
        rev = _float(r["revenue"])
        cost = _float(r["food_cost"])
        if rev > 500 and (rev - cost) / rev < 0.10:
            insights.append({
                "type": "danger",
                "category": "Menu",
                "title": f"{r['name']} — critically low margin",
                "reason": f"Only {((rev - cost) / rev * 100):.1f}% margin. Losing money after fees.",
                "supporting_metrics": {
                    "revenue": round(rev, 2),
                    "food_cost": round(cost, 2),
                    "margin_pct": round((rev - cost) / rev * 100, 1),
                },
                "suggested_action": "Remove from menu or immediately reprice +15%.",
                "confidence": 0.9,
            })
            break

    return insights


def _platform_commission(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT
            platform,
            COUNT(*) AS orders,
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(platform_fee), 0) AS fee,
            COALESCE(SUM(profit), 0) AS profit
        FROM orders o
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
        GROUP BY platform
        HAVING COUNT(*) >= 3
        ORDER BY gross DESC
        """,
        [kitchen_id] + dp
    )

    if not rows or len(rows) < 2:
        return []

    insights = []

    worst = max(rows, key=lambda r: (_float(r["fee"]) / max(_float(r["gross"]), 1)))
    gross = _float(worst["gross"])
    fee = _float(worst["fee"])
    fee_pct = (fee / gross * 100) if gross > 0 else 0

    if fee_pct > 15:
        insights.append({
            "type": "warning",
            "category": "Commission",
            "title": f"{worst['platform'].capitalize()} takes {fee_pct:.1f}% in fees",
            "reason": f"Highest fee platform. {worst['orders']} orders, ₹{fee:,.0f} paid.",
            "supporting_metrics": {
                "platform": worst["platform"],
                "gross_revenue": round(gross, 2),
                "platform_fee": round(fee, 2),
                "fee_pct": round(fee_pct, 1),
                "orders": _int(worst["orders"]),
            },
            "suggested_action": f"Shift promotions to lower-fee platforms, or negotiate with {worst['platform']}.",
            "confidence": 0.8,
        })

    best = max(rows, key=lambda r: _float(r["profit"]))
    if _float(best["profit"]) > 0:
        insights.append({
            "type": "info",
            "category": "Commission",
            "title": f"{best['platform'].capitalize()} is your most profitable channel",
            "reason": f"₹{_float(best['profit']):,.0f} net profit from {best['orders']} orders.",
            "supporting_metrics": {
                "platform": best["platform"],
                "profit": round(_float(best["profit"]), 2),
                "orders": _int(best["orders"]),
            },
            "suggested_action": f"Invest marketing spend on {best['platform']} to grow volume.",
            "confidence": 0.75,
        })

    return insights


def _discount_analysis(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    row = execute_one(
        f"""
        SELECT
            COALESCE(SUM(total_amount), 0) AS gross,
            COALESCE(SUM(discount), 0) AS discount,
            COUNT(*) FILTER (WHERE discount > 0) AS discounted_orders,
            COUNT(*) AS total_orders
        FROM orders o
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
        """,
        [kitchen_id] + dp
    )

    gross = _float(row["gross"])
    discount = _float(row["discount"])
    if gross <= 0 or discount <= 0:
        return []

    discount_pct = discount / gross * 100

    if discount_pct > 12:
        return [{
            "type": "warning",
            "category": "Revenue",
            "title": f"You are losing {discount_pct:.1f}% to discounts",
            "reason": f"₹{discount:,.0f} in discounts on ₹{gross:,.0f} revenue. {row['discounted_orders']} of {row['total_orders']} orders.",
            "supporting_metrics": {
                "discount_amount": round(discount, 2),
                "discount_pct": round(discount_pct, 1),
                "discounted_orders": _int(row["discounted_orders"]),
                "total_orders": _int(row["total_orders"]),
            },
            "suggested_action": "Cap discounts at 10%. Target them to new customers only.",
            "confidence": 0.85,
        }]
    return []


def _cancellation_analysis(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    row = execute_one(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COUNT(*) AS total
        FROM orders o
        WHERE kitchen_id = %s
          {df}
        """,
        [kitchen_id] + dp
    )

    total = _int(row["total"])
    cancelled = _int(row["cancelled"])
    if total < 10:
        return []

    rate = cancelled / total * 100
    if rate > 10:
        return [{
            "type": "danger",
            "category": "Operations",
            "title": f"Cancellation rate at {rate:.1f}%",
            "reason": f"{cancelled} of {total} orders cancelled. Healthy is under 5%.",
            "supporting_metrics": {
                "cancelled": cancelled,
                "total_orders": total,
                "rate_pct": round(rate, 1),
            },
            "suggested_action": "Check prep times vs delivery times. Late food drives cancellations.",
            "confidence": 0.9,
        }]
    return []


def _peak_hours(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT
            EXTRACT(HOUR FROM order_time)::int AS hour,
            COUNT(*) AS orders
        FROM orders o
        WHERE kitchen_id = %s
          AND order_time IS NOT NULL
          AND status != 'cancelled'
          {df}
        GROUP BY hour
        ORDER BY orders DESC
        LIMIT 1
        """,
        [kitchen_id] + dp
    )

    if not rows:
        return []

    hr = rows[0]["hour"]
    label = f"{hr}:00 – {hr + 1}:00"
    orders = _int(rows[0]["orders"])
    if orders < 3:
        return []

    return [{
        "type": "info",
        "category": "Operations",
        "title": f"Peak ordering hour: {label}",
        "reason": f"{orders} orders in this hour. Focus staffing and promotions here.",
        "supporting_metrics": {
            "peak_hour": hr,
            "orders_in_peak": orders,
        },
        "suggested_action": f"Schedule more kitchen staff around {label} and time promos to hit this window.",
        "confidence": 0.75,
    }]


def _repeat_customers(kitchen_id, days):
    df, dp = _date_filter(days, alias="o")

    row = execute_one(
        f"""
        WITH stats AS (
            SELECT customer_phone, COUNT(*) AS freq
            FROM orders o
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
              {df}
            GROUP BY customer_phone
        )
        SELECT
            COUNT(*) FILTER (WHERE freq >= 2) AS repeat_c,
            COUNT(*) AS total_c
        FROM stats
        """,
        [kitchen_id] + dp
    )

    total = _int(row["total_c"])
    repeat = _int(row["repeat_c"])
    if total < 10:
        return []

    repeat_pct = repeat / total * 100

    if repeat_pct > 30:
        return [{
            "type": "success",
            "category": "Customers",
            "title": f"Strong loyalty — {repeat_pct:.1f}% repeat customers",
            "reason": f"{repeat} of {total} customers ordered more than once. Healthy retention.",
            "supporting_metrics": {
                "repeat_customers": repeat,
                "total_customers": total,
                "repeat_pct": round(repeat_pct, 1),
            },
            "suggested_action": "Launch a loyalty program to convert the remaining base into repeat buyers.",
            "confidence": 0.8,
        }]
    elif repeat_pct < 15:
        return [{
            "type": "warning",
            "category": "Customers",
            "title": f"Low retention — only {repeat_pct:.1f}% return",
            "reason": f"{repeat} of {total} customers are repeat buyers. Most order once.",
            "supporting_metrics": {
                "repeat_customers": repeat,
                "total_customers": total,
                "repeat_pct": round(repeat_pct, 1),
            },
            "suggested_action": "Add a follow-up coupon after first order. Track why customers do not return.",
            "confidence": 0.85,
        }]
    return []