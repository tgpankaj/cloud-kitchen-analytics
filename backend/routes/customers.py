"""
========================================================
KitchenIQ - Customer Analytics Routes
========================================================
Customer KPIs, Segments, RFM, Top Customers,
Repeat Rate, Overview and Platform Preference
========================================================
"""

from flask import Blueprint, request, jsonify

from middleware.auth import token_required
from db.connection import execute_query, execute_one


customers_bp = Blueprint("customers", __name__)


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

    Supported:
        ?days=7
        ?days=30
        ?days=90
        ?days=all

    Default = 30 days.
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
    Generate reusable order date filter.

    IMPORTANT:
    Any query using this filter must use the same
    orders table alias.

        FROM orders o

    """

    if days is None:
        return "", []

    return (
        f"AND {alias}.order_date >= "
        f"CURRENT_DATE - INTERVAL '%s days'",
        [days]
    )


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


# ========================================================
# CUSTOMER KPIs
# GET /api/customers/kpis
# ========================================================

@customers_bp.route("/kpis", methods=["GET"])
@token_required
def kpis():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    result = execute_one(
        f"""
        WITH customer_orders AS (

            SELECT

                o.customer_phone,

                COUNT(*) AS order_count,

                COALESCE(
                    SUM(o.total_amount),
                    0
                ) AS total_spend

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone
        )

        SELECT

            COUNT(*) AS total_customers,

            COUNT(*) FILTER (
                WHERE order_count = 1
            ) AS one_time_customers,

            COUNT(*) FILTER (
                WHERE order_count >= 2
            ) AS repeat_customers,

            COALESCE(
                SUM(total_spend),
                0
            ) AS customer_revenue,

            COALESCE(
                AVG(total_spend),
                0
            ) AS avg_customer_value,

            COALESCE(
                AVG(order_count),
                0
            ) AS avg_orders_per_customer

        FROM customer_orders
        """,
        [kitchen_id] + dp
    )

    total_customers = safe_int(
        result["total_customers"]
    )

    repeat_customers = safe_int(
        result["repeat_customers"]
    )

    repeat_rate = (
        repeat_customers /
        max(total_customers, 1) *
        100
    )

    return jsonify({

        "period_days":
            days,

        "total_customers":
            total_customers,

        "one_time_customers":
            safe_int(
                result[
                    "one_time_customers"
                ]
            ),

        "repeat_customers":
            repeat_customers,

        "repeat_rate":
            round(
                repeat_rate,
                1
            ),

        "customer_revenue":
            round(
                safe_float(
                    result[
                        "customer_revenue"
                    ]
                ),
                2
            ),

        "avg_customer_value":
            round(
                safe_float(
                    result[
                        "avg_customer_value"
                    ]
                ),
                2
            ),

        "avg_orders_per_customer":
            round(
                safe_float(
                    result[
                        "avg_orders_per_customer"
                    ]
                ),
                2
            )
    })


# ========================================================
# CUSTOMER SEGMENTS
# GET /api/customers/segments
# ========================================================

@customers_bp.route("/segments", methods=["GET"])
@token_required
def segments():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    rows = execute_query(
        f"""
        WITH customer_data AS (

            SELECT

                o.customer_phone,

                COUNT(*) AS orders,

                COALESCE(
                    SUM(o.total_amount),
                    0
                ) AS revenue,

                MAX(o.order_date) AS last_order

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone
        ),

        classified AS (

            SELECT

                customer_phone,

                orders,

                revenue,

                last_order,

                CASE

                    WHEN orders >= 5
                         AND revenue >= 5000
                        THEN 'VIP'

                    WHEN orders >= 3
                         AND revenue >= 2500
                        THEN 'Loyal'

                    WHEN orders >= 2
                        THEN 'Repeat'

                    WHEN orders = 1
                        THEN 'New'

                    ELSE 'Other'

                END AS segment

            FROM customer_data
        )

        SELECT

            segment,

            COUNT(*) AS customers,

            COALESCE(
                SUM(orders),
                0
            ) AS orders,

            COALESCE(
                SUM(revenue),
                0
            ) AS revenue

        FROM classified

        GROUP BY segment

        ORDER BY revenue DESC
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "segment":
                r["segment"] or
                "Other",

            "customers":
                safe_int(
                    r["customers"]
                ),

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

        for r in rows
    ])


# ========================================================
# CUSTOMER VALUE DISTRIBUTION
# GET /api/customers/value-distribution
# ========================================================

@customers_bp.route(
    "/value-distribution",
    methods=["GET"]
)
@token_required
def value_distribution():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    rows = execute_query(
        f"""
        WITH customer_value AS (

            SELECT

                o.customer_phone,

                COALESCE(
                    SUM(o.total_amount),
                    0
                ) AS total_spend

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone
        )

        SELECT

            CASE

                WHEN total_spend < 500
                    THEN '₹0 - ₹499'

                WHEN total_spend < 1000
                    THEN '₹500 - ₹999'

                WHEN total_spend < 2500
                    THEN '₹1,000 - ₹2,499'

                WHEN total_spend < 5000
                    THEN '₹2,500 - ₹4,999'

                ELSE '₹5,000+'

            END AS value_range,

            COUNT(*) AS customers,

            COALESCE(
                SUM(total_spend),
                0
            ) AS revenue

        FROM customer_value

        GROUP BY value_range

        ORDER BY
            MIN(total_spend)
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "range":
                r["value_range"],

            "value_range":
                r["value_range"],

            "customers":
                safe_int(
                    r["customers"]
                ),

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
# RFM ANALYSIS
# GET /api/customers/rfm
# ========================================================

@customers_bp.route("/rfm", methods=["GET"])
@token_required
def rfm():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    rows = execute_query(
        f"""
        WITH customer_rfm AS (

            SELECT

                o.customer_phone,

                CURRENT_DATE -
                MAX(o.order_date)
                AS recency_days,

                COUNT(*) AS frequency,

                COALESCE(
                    SUM(o.total_amount),
                    0
                ) AS monetary

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone
        )

        SELECT

            CASE

                WHEN recency_days <= 7
                     AND frequency >= 5
                    THEN 'Champions'

                WHEN recency_days <= 14
                     AND frequency >= 3
                    THEN 'Loyal Customers'

                WHEN recency_days <= 30
                     AND frequency >= 2
                    THEN 'Potential Loyalists'

                WHEN recency_days <= 60
                    THEN 'At Risk'

                ELSE 'Lost'

            END AS rfm_segment,

            COUNT(*) AS customers,

            COALESCE(
                SUM(monetary),
                0
            ) AS revenue,

            COALESCE(
                AVG(frequency),
                0
            ) AS avg_frequency,

            COALESCE(
                AVG(monetary),
                0
            ) AS avg_monetary

        FROM customer_rfm

        GROUP BY rfm_segment

        ORDER BY revenue DESC
        """,
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "segment":
                r["rfm_segment"],

            "rfm_segment":
                r["rfm_segment"],

            "customers":
                safe_int(
                    r["customers"]
                ),

            "revenue":
                round(
                    safe_float(
                        r["revenue"]
                    ),
                    2
                ),

            "avg_frequency":
                round(
                    safe_float(
                        r["avg_frequency"]
                    ),
                    2
                ),

            "avg_monetary":
                round(
                    safe_float(
                        r["avg_monetary"]
                    ),
                    2
                )
        }

        for r in rows
    ])


# ========================================================
# TOP CUSTOMERS
# GET /api/customers/top
# ========================================================

@customers_bp.route("/top", methods=["GET"])
@token_required
def top_customers():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    try:
        limit = int(
            request.args.get(
                "limit",
                10
            )
        )

        limit = max(
            1,
            min(limit, 50)
        )

    except (ValueError, TypeError):
        limit = 10

    df, dp = date_filter(
        days,
        alias="o"
    )

    rows = execute_query(
        f"""
        SELECT

            o.customer_phone,

            COUNT(*) AS orders,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS total_spend,

            COALESCE(
                AVG(o.total_amount),
                0
            ) AS avg_order_value,

            MAX(o.order_date)::text
                AS last_order_date,

            MIN(o.order_date)::text
                AS first_order_date

        FROM orders o

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          AND o.customer_phone IS NOT NULL

          {df}

        GROUP BY o.customer_phone

        ORDER BY total_spend DESC

        LIMIT %s
        """,
        [kitchen_id] + dp + [limit]
    )

    result = []

    for index, r in enumerate(rows, start=1):

        result.append({

            "rank":
                index,

            "customer":
                r["customer_phone"],

            "customer_phone":
                r["customer_phone"],

            "orders":
                safe_int(
                    r["orders"]
                ),

            "total_spend":
                round(
                    safe_float(
                        r["total_spend"]
                    ),
                    2
                ),

            "revenue":
                round(
                    safe_float(
                        r["total_spend"]
                    ),
                    2
                ),

            "avg_order_value":
                round(
                    safe_float(
                        r["avg_order_value"]
                    ),
                    2
                ),

            "last_order_date":
                r["last_order_date"],

            "first_order_date":
                r["first_order_date"]
        })

    return jsonify(result)


# ========================================================
# REPEAT RATE
# GET /api/customers/repeat-rate
# ========================================================

@customers_bp.route(
    "/repeat-rate",
    methods=["GET"]
)
@token_required
def repeat_rate():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    result = execute_one(
        f"""
        WITH customer_orders AS (

            SELECT

                o.customer_phone,

                COUNT(*) AS order_count

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone
        )

        SELECT

            COUNT(*) AS total_customers,

            COUNT(*) FILTER (
                WHERE order_count >= 2
            ) AS repeat_customers,

            COUNT(*) FILTER (
                WHERE order_count = 1
            ) AS one_time_customers

        FROM customer_orders
        """,
        [kitchen_id] + dp
    )

    total = safe_int(
        result["total_customers"]
    )

    repeat = safe_int(
        result["repeat_customers"]
    )

    one_time = safe_int(
        result["one_time_customers"]
    )

    rate = (
        repeat /
        max(total, 1) *
        100
    )

    return jsonify({

        "period_days":
            days,

        "total_customers":
            total,

        "repeat_customers":
            repeat,

        "one_time_customers":
            one_time,

        "repeat_rate":
            round(
                rate,
                1
            )
    })


# ========================================================
# CUSTOMER OVERVIEW
# GET /api/customers/overview
# ========================================================

@customers_bp.route(
    "/overview",
    methods=["GET"]
)
@token_required
def overview():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    result = execute_one(
        f"""
        SELECT

            COUNT(
                DISTINCT o.customer_phone
            ) FILTER (
                WHERE o.customer_phone IS NOT NULL
            ) AS customers,

            COUNT(*) FILTER (
                WHERE o.status != 'cancelled'
            ) AS orders,

            COALESCE(
                SUM(o.total_amount)
                FILTER (
                    WHERE o.status != 'cancelled'
                ),
                0
            ) AS revenue,

            COALESCE(
                AVG(o.total_amount)
                FILTER (
                    WHERE o.status != 'cancelled'
                ),
                0
            ) AS avg_order_value,

            COUNT(
                DISTINCT o.customer_phone
            ) FILTER (
                WHERE
                    o.customer_phone IS NOT NULL
                    AND o.status != 'cancelled'
            ) AS active_customers

        FROM orders o

        WHERE o.kitchen_id = %s

          {df}
        """,
        [kitchen_id] + dp
    )

    return jsonify({

        "period_days":
            days,

        "customers":
            safe_int(
                result["customers"]
            ),

        "orders":
            safe_int(
                result["orders"]
            ),

        "revenue":
            round(
                safe_float(
                    result["revenue"]
                ),
                2
            ),

        "avg_order_value":
            round(
                safe_float(
                    result["avg_order_value"]
                ),
                2
            ),

        "active_customers":
            safe_int(
                result["active_customers"]
            )
    })


# ========================================================
# PLATFORM PREFERENCE
# GET /api/customers/platform-preference
# ========================================================

@customers_bp.route(
    "/platform-preference",
    methods=["GET"]
)
@token_required
def platform_preference():

    kitchen_id = get_kitchen_id(request)

    if not kitchen_id:
        return jsonify({
            "error": "No kitchen found"
        }), 404

    days = get_days(request)

    df, dp = date_filter(
        days,
        alias="o"
    )

    # ----------------------------------------------------
    # Find customers with 2+ orders
    # ----------------------------------------------------

    rows = execute_query(
        f"""
        WITH repeat_customers AS (

            SELECT

                o.customer_phone

            FROM orders o

            WHERE o.kitchen_id = %s

              AND o.status != 'cancelled'

              AND o.customer_phone IS NOT NULL

              {df}

            GROUP BY o.customer_phone

            HAVING COUNT(*) >= 2
        )

        SELECT

            o.platform,

            COUNT(*) AS orders,

            COUNT(
                DISTINCT o.customer_phone
            ) AS customers,

            COALESCE(
                SUM(o.total_amount),
                0
            ) AS revenue

        FROM orders o

        JOIN repeat_customers rc

            ON rc.customer_phone =
               o.customer_phone

        WHERE o.kitchen_id = %s

          AND o.status != 'cancelled'

          AND o.customer_phone IS NOT NULL

          {df}

        GROUP BY o.platform

        ORDER BY orders DESC
        """,
        [kitchen_id] + dp +
        [kitchen_id] + dp
    )

    return jsonify([

        {
            "platform":
                r["platform"] or
                "Unknown",

            "orders":
                safe_int(
                    r["orders"]
                ),

            "customers":
                safe_int(
                    r["customers"]
                ),

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
# CUSTOMER HOME / INFO
# GET /api/customers/
# ========================================================

@customers_bp.route(
    "/",
    methods=["GET"]
)
@token_required
def customers_home():

    return jsonify({

        "service":
            "KitchenIQ Customer Analytics",

        "status":
            "ok",

        "endpoints": [

            "/kpis",

            "/segments",

            "/value-distribution",

            "/rfm",

            "/top",

            "/repeat-rate",

            "/overview",

            "/platform-preference"
        ]
    })

