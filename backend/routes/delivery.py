"""
Delivery Analytics Routes
Delivery times, late %, platform performance, prep vs delivery.
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

delivery_bp = Blueprint('delivery', __name__)


def get_kitchen_id(request):
    kitchen_id = request.args.get('kitchen_id')
    if kitchen_id:
        try:
            return int(kitchen_id)
        except (ValueError, TypeError):
            pass

    kitchen = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s ORDER BY id LIMIT 1",
        (request.user_id,)
    )
    return kitchen['id'] if kitchen else None


def get_date_range(request):
    days = request.args.get('days', '30')
    if days == 'all':
        return None
    try:
        return int(days)
    except ValueError:
        return 30


def build_date_filter(days):
    if days is None:
        return "", []
    return "AND order_date >= CURRENT_DATE - INTERVAL '%s days'", [days]


# ==========================================
# ENDPOINT 1: Delivery KPIs
# ==========================================
@delivery_bp.route('/stats', methods=['GET'])
@token_required
def delivery_stats():
    """Overall delivery performance."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            COUNT(*) AS total_orders,
            COALESCE(AVG(prep_time_minutes), 0) AS avg_prep_time,
            COALESCE(AVG(delivery_time_minutes), 0) AS avg_delivery_time,
            COALESCE(AVG(prep_time_minutes + delivery_time_minutes), 0) AS avg_total_time,
            COUNT(*) FILTER (WHERE delivery_time_minutes > 45) AS late_orders,
            COUNT(*) FILTER (WHERE delivery_time_minutes <= 30) AS fast_orders,
            COALESCE(AVG(total_amount), 0) AS avg_order_value
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND delivery_time_minutes IS NOT NULL
          {date_sql}
    """
    params = [kitchen_id] + date_params
    result = execute_one(sql, params)

    total = int(result['total_orders'] or 0)
    late = int(result['late_orders'] or 0)
    fast = int(result['fast_orders'] or 0)

    return jsonify({
        'total_orders': total,
        'avg_prep_time': round(float(result['avg_prep_time'] or 0), 1),
        'avg_delivery_time': round(float(result['avg_delivery_time'] or 0), 1),
        'avg_total_time': round(float(result['avg_total_time'] or 0), 1),
        'late_orders': late,
        'late_percentage': round(late / total * 100, 1) if total else 0,
        'fast_orders': fast,
        'fast_percentage': round(fast / total * 100, 1) if total else 0,
        'avg_order_value': round(float(result['avg_order_value'] or 0), 2)
    })


# ==========================================
# ENDPOINT 2: Delivery by Platform
# ==========================================
@delivery_bp.route('/by-platform', methods=['GET'])
@token_required
def delivery_by_platform():
    """Delivery performance breakdown by platform."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            platform,
            COUNT(*) AS orders,
            COALESCE(AVG(prep_time_minutes), 0) AS avg_prep,
            COALESCE(AVG(delivery_time_minutes), 0) AS avg_delivery,
            COUNT(*) FILTER (WHERE delivery_time_minutes > 45) AS late_orders,
            COALESCE(AVG(total_amount), 0) AS avg_order_value
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND delivery_time_minutes IS NOT NULL
          {date_sql}
        GROUP BY platform
        ORDER BY orders DESC
    """
    params = [kitchen_id] + date_params
    rows = execute_query(sql, params)

    result = []
    for r in rows:
        orders = int(r['orders'])
        late = int(r['late_orders'] or 0)
        result.append({
            'platform': r['platform'],
            'orders': orders,
            'avg_prep': round(float(r['avg_prep'] or 0), 1),
            'avg_delivery': round(float(r['avg_delivery'] or 0), 1),
            'late_orders': late,
            'late_pct': round(late / orders * 100, 1) if orders else 0,
            'avg_order_value': round(float(r['avg_order_value'] or 0), 2)
        })

    return jsonify(result)


# ==========================================
# ENDPOINT 3: Delivery Time Distribution
# ==========================================
@delivery_bp.route('/distribution', methods=['GET'])
@token_required
def delivery_distribution():
    """
    Buckets orders into time ranges:
    <20 min, 20-30, 30-40, 40-50, 50+ min
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        WITH bucketed_orders AS (
            SELECT
                CASE
                    WHEN delivery_time_minutes < 20 THEN '<20 min'
                    WHEN delivery_time_minutes < 30 THEN '20-30 min'
                    WHEN delivery_time_minutes < 40 THEN '30-40 min'
                    WHEN delivery_time_minutes < 50 THEN '40-50 min'
                    ELSE '50+ min'
                END AS bucket
            FROM orders
            WHERE kitchen_id = %s
              AND status != 'cancelled'
              AND delivery_time_minutes IS NOT NULL
              {date_sql}
        )
        SELECT
            bucket,
            COUNT(*) AS orders
        FROM bucketed_orders
        GROUP BY bucket
        ORDER BY
            CASE bucket
                WHEN '<20 min' THEN 1
                WHEN '20-30 min' THEN 2
                WHEN '30-40 min' THEN 3
                WHEN '40-50 min' THEN 4
                WHEN '50+ min' THEN 5
                ELSE 6
            END
    """

    params = [kitchen_id] + date_params
    rows = execute_query(sql, params)

    return jsonify([
        {
            'bucket': r['bucket'],
            'orders': int(r['orders'])
        }
        for r in rows
    ])


# ==========================================
# ENDPOINT 4: Prep vs Delivery Time (Scatter)
# ==========================================
@delivery_bp.route('/prep-vs-delivery', methods=['GET'])
@token_required
def prep_vs_delivery():
    """Scatter data: prep time vs delivery time."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            prep_time_minutes,
            delivery_time_minutes,
            total_amount,
            platform
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND prep_time_minutes IS NOT NULL
          AND delivery_time_minutes IS NOT NULL
          {date_sql}
        LIMIT 500
    """
    params = [kitchen_id] + date_params
    rows = execute_query(sql, params)

    return jsonify([{
        'prep': int(r['prep_time_minutes']),
        'delivery': int(r['delivery_time_minutes']),
        'amount': float(r['total_amount'] or 0),
        'platform': r['platform']
    } for r in rows])


# ==========================================
# ENDPOINT 5: Slowest Dishes (by prep time)
# ==========================================
@delivery_bp.route('/slow-dishes', methods=['GET'])
@token_required
def slow_dishes():
    """Items with highest prep times."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            mi.name,
            COALESCE(AVG(o.prep_time_minutes), mi.prep_time_minutes) AS avg_prep,
            COUNT(*) AS orders,
            COALESCE(AVG(o.delivery_time_minutes), 0) AS avg_delivery
        FROM order_items oi
        JOIN menu_items mi ON mi.id = oi.menu_item_id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.prep_time_minutes IS NOT NULL
          {date_sql}
        GROUP BY mi.id, mi.name, mi.prep_time_minutes
        HAVING COUNT(*) >= 2
        ORDER BY avg_prep DESC
        LIMIT 10
    """
    params = [kitchen_id] + date_params
    rows = execute_query(sql, params)

    return jsonify([{
        'name': r['name'],
        'avg_prep': round(float(r['avg_prep'] or 0), 1),
        'orders': int(r['orders']),
        'avg_delivery': round(float(r['avg_delivery'] or 0), 1)
    } for r in rows])