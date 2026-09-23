"""
========================================================
KitchenIQ - Analytics Routes
========================================================
Revenue, Orders, Profit, Dish Margin, Peak Hours,
Cancellations, Top Days and Recent Orders
========================================================
"""

from flask import Blueprint, request, jsonify

from middleware.auth import token_required
from db.connection import execute_query, execute_one


analytics_bp = Blueprint("analytics", __name__)


# ========================================================
# HELPERS
# ========================================================

def get_kitchen_id(request):
    """
    Get kitchen_id from query parameter.
    If not provided, use the first kitchen belonging
    to the authenticated user.
    """

    kitchen_id = request.args.get("kitchen_id")

    if kitchen_id:
        try:
            return int(kitchen_id)
        except (ValueError, TypeError):
            pass

    kitchen = execute_one(
        """
        SELECT id
        FROM kitchens
        WHERE user_id = %s
        ORDER BY id
        LIMIT 1
        """,
        (request.user_id,)
    )

    return kitchen["id"] if kitchen else None


def get_days(request):
    """
    Get analytics period.

    Examples:
        ?days=7
        ?days=30
        ?days=90
        ?days=all

    Default = 30 days
    """

    days = request.args.get("days", "30")

    if str(days).lower() == "all":
        return None

    try:
        days = int(days)
        return max(days, 1)
    except (ValueError, TypeError):
        return 30


def date_filter(days, alias="o"):
    """
    Create reusable order_date filter.

    IMPORTANT:
    The orders table MUST use the same alias.

    Example:

        FROM orders o

        WHERE o.kitchen_id = %s
          {df}
    """

    if days is None:
        return "", []

    return (
        f"AND {alias}.order_date >= "
        f"CURRENT_DATE - INTERVAL '%s days'",
        [days]
    )


def safe_float(value):
    """
    Safely convert PostgreSQL numeric/decimal values
    into float.
    """

    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def safe_int(value):
    """
    Safely convert value into integer.
    """

    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def get_limit(request, default=10, maximum=50):
    """
    Safely read ?limit= parameter.
    """

    try:
        limit = int(request.args.get("limit", default))
        return max(1, min(limit, maximum))
    except (ValueError, TypeError):
        return default


# ========================================================
# SALES ANALYTICS
# GET /api/analytics/sales
# ========================================================

@analytics_bp.route("/sales", methods=["GET"])
@token_required
def sales():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    # ----------------------------------------------------
    # KPIs
    # ----------------------------------------------------

    kpis = execute_one(
        f"""
        SELECT

            COUNT(*) AS total_orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0) / 100.0
                    )
                ),
                0
            ) AS net_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    COALESCE(o.commission_pct, 0) / 100.0
                ),
                0
            ) AS commission_paid,

            COALESCE(
                AVG(o.total_amount),
                0
            ) AS avg_order_value,

            COUNT(DISTINCT o.customer_phone)
                FILTER (
                    WHERE o.customer_phone IS NOT NULL
                ) AS unique_customers,

            COUNT(*) FILTER (
                WHERE o.status = 'cancelled'
            ) AS cancelled_orders,

            COUNT(*) AS all_orders

        FROM orders o

        WHERE o.kitchen_id = %s
          {df}
        """,
        [kitchen_id] + dp
    )

    total_orders = safe_int(kpis["total_orders"])
    cancelled_orders = safe_int(kpis["cancelled_orders"])

    cancellation_rate = (
        round(
            cancelled_orders /
            max(total_orders, 1) *
            100,
            1
        )
    )

    # ----------------------------------------------------
    # PLATFORM PERFORMANCE
    # ----------------------------------------------------

    platforms = execute_query(
        f"""
        SELECT

            o.platform,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0) / 100.0
                    )
                ),
                0
            ) AS net_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    COALESCE(o.commission_pct, 0) / 100.0
                ),
                0
            ) AS commission_paid,

            COALESCE(
                AVG(o.commission_pct),
                0
            ) AS avg_commission_pct

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.platform

        ORDER BY gross_revenue DESC
        """,
        [kitchen_id] + dp
    )

    return jsonify({

        "period_days": days,

        "kpis": {

            "total_orders":
                safe_int(kpis["total_orders"]),

            "gross_revenue":
                round(
                    safe_float(kpis["gross_revenue"]),
                    2
                ),

            "net_revenue":
                round(
                    safe_float(kpis["net_revenue"]),
                    2
                ),

            "commission_paid":
                round(
                    safe_float(kpis["commission_paid"]),
                    2
                ),

            "avg_order_value":
                round(
                    safe_float(kpis["avg_order_value"]),
                    2
                ),

            "unique_customers":
                safe_int(kpis["unique_customers"]),

            "cancellation_rate":
                cancellation_rate
        },

        "platforms": [

            {
                "platform":
                    r["platform"] or "Unknown",

                "orders":
                    safe_int(r["orders"]),

                "gross_revenue":
                    round(
                        safe_float(
                            r["gross_revenue"]
                        ),
                        2
                    ),

                "net_revenue":
                    round(
                        safe_float(
                            r["net_revenue"]
                        ),
                        2
                    ),

                "commission_paid":
                    round(
                        safe_float(
                            r["commission_paid"]
                        ),
                        2
                    ),

                "avg_commission_pct":
                    round(
                        safe_float(
                            r["avg_commission_pct"]
                        ),
                        1
                    )
            }

            for r in platforms
        ]
    })


# ========================================================
# REVENUE TRENDS
# GET /api/analytics/trends
# ========================================================

@analytics_bp.route("/trends", methods=["GET"])
@token_required
def trends():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    # ----------------------------------------------------
    # DAILY
    # ----------------------------------------------------

    daily = execute_query(
        f"""
        SELECT

            o.order_date::text AS date,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0)
                        / 100.0
                    )
                ),
                0
            ) AS net_revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.order_date

        ORDER BY o.order_date
        """,
        [kitchen_id] + dp
    )

    # ----------------------------------------------------
    # WEEKLY
    # ----------------------------------------------------

    weekly = execute_query(
        f"""
        SELECT

            DATE_TRUNC(
                'week',
                o.order_date
            )::date::text AS week_start,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0)
                        / 100.0
                    )
                ),
                0
            ) AS net_revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY DATE_TRUNC(
            'week',
            o.order_date
        )

        ORDER BY week_start
        """,
        [kitchen_id] + dp
    )

    # ----------------------------------------------------
    # MONTHLY
    # ----------------------------------------------------

    monthly = execute_query(
        f"""
        SELECT

            DATE_TRUNC(
                'month',
                o.order_date
            )::date::text AS month_start,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0)
                        / 100.0
                    )
                ),
                0
            ) AS net_revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY DATE_TRUNC(
            'month',
            o.order_date
        )

        ORDER BY month_start
        """,
        [kitchen_id] + dp
    )

    return jsonify({

        "period_days": days,

        "daily": [
            dict(row)
            for row in daily
        ],

        "weekly": [
            dict(row)
            for row in weekly
        ],

        "monthly": [
            dict(row)
            for row in monthly
        ]
    })


# ========================================================
# ORDERS TREND
# GET /api/analytics/orders-trend
# ========================================================

@analytics_bp.route("/orders-trend", methods=["GET"])
@token_required
def orders_trend():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT

            o.order_date::text AS date,

            COUNT(*) AS orders,

            COALESCE(
                AVG(o.total_amount),
                0
            ) AS avg_value

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.order_date

        ORDER BY o.order_date
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "date":
                r["date"],

            "orders":
                safe_int(r["orders"]),

            "avg_value":
                round(
                    safe_float(r["avg_value"]),
                    2
                )
        }

        for r in rows
    ])


# ========================================================
# PROFIT TREND
# GET /api/analytics/profit-trend
# ========================================================

@analytics_bp.route("/profit-trend", methods=["GET"])
@token_required
def profit_trend():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT

            o.order_date::text AS date,

            COALESCE(
                SUM(
                    o.total_amount *
                    (
                        1 -
                        COALESCE(o.commission_pct, 0)
                        / 100.0
                    )
                ),
                0
            ) AS net_profit,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS gross_revenue,

            COALESCE(
                SUM(
                    o.total_amount *
                    COALESCE(o.commission_pct, 0)
                    / 100.0
                ),
                0
            ) AS commission

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.order_date

        ORDER BY o.order_date
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "date":
                r["date"],

            "net_profit":
                round(
                    safe_float(
                        r["net_profit"]
                    ),
                    2
                ),

            "gross_revenue":
                round(
                    safe_float(
                        r["gross_revenue"]
                    ),
                    2
                ),

            "commission":
                round(
                    safe_float(
                        r["commission"]
                    ),
                    2
                )
        }

        for r in rows
    ])


# ========================================================
# MARGIN BY DISH
# GET /api/analytics/margin-by-dish
# ========================================================

@analytics_bp.route("/margin-by-dish", methods=["GET"])
@token_required
def margin_by_dish():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    limit = get_limit(
        request,
        default=10,
        maximum=30
    )

    df, dp = date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT

            mi.id,

            mi.name,

            mi.category,

            COALESCE(
                SUM(oi.quantity),
                0
            ) AS quantity_sold,

            COALESCE(
                SUM(
                    oi.quantity *
                    oi.unit_price *
                    (
                        1 -
                        COALESCE(
                            o.commission_pct,
                            0
                        ) / 100.0
                    )
                ),
                0
            ) AS net_revenue,

            COALESCE(
                SUM(
                    oi.quantity *
                    COALESCE(
                        mi.cost_price,
                        0
                    )
                ),
                0
            ) AS total_cost

        FROM menu_items mi

        JOIN order_items oi
            ON oi.menu_item_id = mi.id

        JOIN orders o
            ON o.id = oi.order_id

        WHERE mi.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY
            mi.id,
            mi.name,
            mi.category

        HAVING SUM(oi.quantity) > 0

        ORDER BY net_revenue DESC

        LIMIT %s
        """,
        [kitchen_id] + dp + [limit]
    )

    result = []

    for r in rows:

        net_revenue = safe_float(
            r["net_revenue"]
        )

        total_cost = safe_float(
            r["total_cost"]
        )

        net_profit = (
            net_revenue -
            total_cost
        )

        margin_pct = (
            net_profit /
            net_revenue *
            100
            if net_revenue > 0
            else 0
        )

        result.append({

            "id":
                r["id"],

            "name":
                r["name"],

            "category":
                r["category"] or
                "Uncategorized",

            "quantity_sold":
                safe_int(
                    r["quantity_sold"]
                ),

            "net_revenue":
                round(
                    net_revenue,
                    2
                ),

            "total_cost":
                round(
                    total_cost,
                    2
                ),

            "net_profit":
                round(
                    net_profit,
                    2
                ),

            "margin_pct":
                round(
                    margin_pct,
                    1
                )
        })

    return jsonify(result)


# ========================================================
# PEAK HOURS
# GET /api/analytics/peak-hours
# ========================================================

@analytics_bp.route("/peak-hours", methods=["GET"])
@token_required
def peak_hours():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    rows = execute_query(
        f"""
        SELECT

            EXTRACT(
                HOUR FROM o.order_time
            )::int AS hour,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.order_time IS NOT NULL

          AND o.status != 'cancelled'

          {df}

        GROUP BY EXTRACT(
            HOUR FROM o.order_time
        )

        ORDER BY hour
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "hour":
                safe_int(r["hour"]),

            "orders":
                safe_int(r["orders"]),

            "revenue":
                round(
                    safe_float(
                        r["revenue"]
                    ),
                    2
                )
        }

        for r in rows
    ])


# ========================================================
# CANCELLATIONS
# GET /api/analytics/cancellations
# ========================================================

@analytics_bp.route("/cancellations", methods=["GET"])
@token_required
def cancellations():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    # ----------------------------------------------------
    # OVERALL CANCELLATION STATS
    # ----------------------------------------------------

    stats = execute_one(
        f"""
        SELECT

            COUNT(*) FILTER (
                WHERE o.status = 'cancelled'
            ) AS cancelled,

            COUNT(*) AS total

        FROM orders o

        WHERE o.kitchen_id = %s

          {df}
        """,
        [kitchen_id] + dp
    )

    cancelled = safe_int(
        stats["cancelled"]
    )

    total = safe_int(
        stats["total"]
    )

    cancellation_rate = (
        round(
            cancelled /
            max(total, 1) *
            100,
            1
        )
    )

    # ----------------------------------------------------
    # CANCELLATIONS BY PLATFORM
    # ----------------------------------------------------

    by_platform = execute_query(
        f"""
        SELECT

            o.platform,

            COUNT(*) FILTER (
                WHERE o.status = 'cancelled'
            ) AS cancelled,

            COUNT(*) AS total

        FROM orders o

        WHERE o.kitchen_id = %s

          {df}

        GROUP BY o.platform

        ORDER BY total DESC
        """,
        [kitchen_id] + dp
    )

    # ----------------------------------------------------
    # NOTE:
    # No real cancellation-reason column has been
    # confirmed in the current orders schema.
    #
    # Therefore these are placeholder categories.
    # Do NOT treat them as database-derived values.
    # ----------------------------------------------------

    reasons = [
        {
            "reason": "Customer Change",
            "pct": 24
        },
        {
            "reason": "Delivery Delay",
            "pct": 22
        },
        {
            "reason": "Restaurant Busy",
            "pct": 20
        },
        {
            "reason": "Payment Issue",
            "pct": 18
        },
        {
            "reason": "Other",
            "pct": 16
        }
    ]

    return jsonify({

        "cancellation_rate":
            cancellation_rate,

        "cancelled_count":
            cancelled,

        "total_orders":
            total,

        "by_platform": [

            {
                "platform":
                    r["platform"] or
                    "Unknown",

                "cancelled":
                    safe_int(
                        r["cancelled"]
                    ),

                "total":
                    safe_int(
                        r["total"]
                    ),

                "rate":
                    round(
                        safe_int(
                            r["cancelled"]
                        )
                        /
                        max(
                            safe_int(
                                r["total"]
                            ),
                            1
                        )
                        *
                        100,
                        1
                    )
            }

            for r in by_platform
        ],

        "reasons":
            reasons
    })


# ========================================================
# TOP DAYS
# GET /api/analytics/top-days
# ========================================================

@analytics_bp.route("/top-days", methods=["GET"])
@token_required
def top_days():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(days, alias="o")

    # ----------------------------------------------------
    # BEST DAYS
    # ----------------------------------------------------

    best = execute_query(
        f"""
        SELECT

            o.order_date::text AS date,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.order_date

        HAVING COUNT(*) >= 1

        ORDER BY revenue DESC

        LIMIT 5
        """,
        [kitchen_id] + dp
    )

    # ----------------------------------------------------
    # WORST DAYS
    # ----------------------------------------------------

    worst = execute_query(
        f"""
        SELECT

            o.order_date::text AS date,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS revenue

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          {df}

        GROUP BY o.order_date

        HAVING COUNT(*) >= 1

        ORDER BY revenue ASC

        LIMIT 5
        """,
        [kitchen_id] + dp
    )

    return jsonify({

        "best_days": [

            {
                "date":
                    r["date"],

                "orders":
                    safe_int(
                        r["orders"]
                    ),

                "revenue":
                    round(
                        safe_float(
                            r["revenue"]
                        ),
                        2
                    )
            }

            for r in best
        ],

        "worst_days": [

            {
                "date":
                    r["date"],

                "orders":
                    safe_int(
                        r["orders"]
                    ),

                "revenue":
                    round(
                        safe_float(
                            r["revenue"]
                        ),
                        2
                    )
            }

            for r in worst
        ]
    })


# ========================================================
# RECENT ORDERS
# GET /api/analytics/recent-orders
# ========================================================

@analytics_bp.route("/recent-orders", methods=["GET"])
@token_required
def recent_orders():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    limit = get_limit(
        request,
        default=5,
        maximum=20
    )

    rows = execute_query(
        """
        SELECT

            o.id,

            o.order_date::text AS date,

            o.order_time::text AS time,

            o.customer_phone,

            o.total_amount,

            o.status

        FROM orders o

        WHERE o.kitchen_id = %s

        ORDER BY o.id DESC

        LIMIT %s
        """,
        (kitchen_id, limit)
    )

    result = []

    for r in rows:

        order_id = safe_int(
            r["id"]
        )

        order_time = (
            str(r["time"])[:5]
            if r["time"]
            else ""
        )

        result.append({

            "id":
                f"#ORD{order_id:04d}",

            "customer":
                r["customer_phone"] or
                "Guest",

            "amount":
                round(
                    safe_float(
                        r["total_amount"]
                    ),
                    2
                ),

            "status":
                (
                    r["status"] or
                    "pending"
                ).lower(),

            "date":
                r["date"],

            "time":
                order_time
        })

    return jsonify(result)

