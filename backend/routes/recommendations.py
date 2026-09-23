"""
Recommendations Routes
Updated for KitchenIQ Insights page
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one
from services.insights_engine import generate_insights

recommendations_bp = Blueprint('recommendations', __name__)


# ==========================================
# HELPERS
# ==========================================
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


def get_days(request):
    days = request.args.get('days', '30')
    if days == 'all':
        return None
    try:
        return int(days)
    except ValueError:
        return 30


def get_type_filter(request):
    """Map frontend filter to backend type."""
    f = request.args.get('filter', 'all')
    reverse_map = {
        'promote': 'success',
        'opportunity': 'info',
        'optimize': 'warning',
        'review': 'danger'
    }
    return reverse_map.get(f)  # None if 'all'


# ==========================================
# ALL INSIGHTS
# ==========================================
@recommendations_bp.route('/insights', methods=['GET'])
@token_required
def insights():
    """
    All insights, sorted by impact score.
    Optional filter: ?filter=promote|opportunity|optimize|review
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    type_filter = get_type_filter(request)

    all_insights = generate_insights(kitchen_id, days)

    if type_filter:
        all_insights = [i for i in all_insights if i.get('type') == type_filter]

    return jsonify(all_insights)


# ==========================================
# SUMMARY (Counts by type)
# ==========================================
@recommendations_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    """
    Counts by type and category.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    all_insights = generate_insights(kitchen_id, days)

    by_type = {'success': 0, 'info': 0, 'warning': 0, 'danger': 0}
    by_category = {}

    for i in all_insights:
        by_type[i.get('type', 'info')] = by_type.get(i.get('type', 'info'), 0) + 1
        cat = i.get('category', 'Other')
        by_category[cat] = by_category.get(cat, 0) + 1

    return jsonify({
        'total': len(all_insights),
        'by_type': by_type,
        'by_category': by_category
    })


# ==========================================
# TOP N (For dashboard widget)
# ==========================================
@recommendations_bp.route('/top', methods=['GET'])
@token_required
def top():
    """
    Top N insights for dashboard widget.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    limit = min(int(request.args.get('limit', 4)), 20)

    all_insights = generate_insights(kitchen_id, days)
    return jsonify(all_insights[:limit])


# ==========================================
# ADDITIONAL INSIGHTS (Insights page bottom)
# ==========================================
@recommendations_bp.route('/additional', methods=['GET'])
@token_required
def additional():
    """
    Additional observations — smaller insights for the bottom section.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    result = []

    # ─── 1. Best hour to promote ───
    hours = execute_query("""
        SELECT
            EXTRACT(HOUR FROM order_time)::int AS hour,
            COUNT(*) AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND order_time IS NOT NULL
          AND status != 'cancelled'
        GROUP BY hour
        ORDER BY orders DESC
        LIMIT 1
    """, (kitchen_id,))

    if hours:
        hr = hours[0]['hour']
        if hr == 0:
            label = '12 AM'
        elif hr < 12:
            label = f'{hr} AM'
        elif hr == 12:
            label = '12 PM'
        else:
            label = f'{hr - 12} PM'

        result.append({
            'icon': '⏰',
            'text': f'Best time to promote: {label}',
            'sub': f'Peak ordering hour ({hours[0]["orders"]} orders)'
        })

    # ─── 2. Top performing dish ───
    top_dish = execute_one("""
        SELECT
            mi.name,
            SUM(oi.quantity * oi.unit_price) AS revenue
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
        GROUP BY mi.id, mi.name
        ORDER BY revenue DESC
        LIMIT 1
    """, (kitchen_id,))

    if top_dish:
        result.append({
            'icon': '🍛',
            'text': f'Top performing: {top_dish["name"]}',
            'sub': f'Highest revenue: ₹{float(top_dish["revenue"]):,.0f}'
        })

    # ─── 3. Lowest margin dish ───
    low_margin = execute_one("""
        SELECT
            mi.name,
            SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)) AS net_rev,
            SUM(oi.quantity * mi.cost_price) AS cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
        GROUP BY mi.id, mi.name
        HAVING SUM(oi.quantity) > 0
        ORDER BY (
            SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0))
            - SUM(oi.quantity * mi.cost_price)
        ) / NULLIF(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0)
        ASC
        LIMIT 1
    """, (kitchen_id,))

    if low_margin:
        net_rev = float(low_margin['net_rev'] or 0)
        cost = float(low_margin['cost'] or 0)
        margin = ((net_rev - cost) / net_rev * 100) if net_rev > 0 else 0
        result.append({
            'icon': '📉',
            'text': f'Lowest margin: {low_margin["name"]}',
            'sub': f'Only {margin:.1f}% — consider repricing'
        })

    # ─── 4. Repeat rate ───
    repeat = execute_one("""
        WITH stats AS (
            SELECT customer_phone, COUNT(*) AS freq
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
            GROUP BY customer_phone
        )
        SELECT
            COUNT(*) FILTER (WHERE freq >= 2)::float
                / NULLIF(COUNT(*), 0) * 100 AS repeat_pct
        FROM stats
    """, (kitchen_id,))

    if repeat and repeat['repeat_pct']:
        result.append({
            'icon': '👥',
            'text': f'Loyal customers are {float(repeat["repeat_pct"]):.1f}% of your base',
            'sub': 'Focus on retention campaigns'
        })

    # ─── 5. Missing recipes ───
    missing = execute_one("""
        SELECT COUNT(*) AS c
        FROM menu_items mi
        WHERE mi.kitchen_id = %s
          AND mi.is_active = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM recipes r WHERE r.menu_item_id = mi.id
          )
    """, (kitchen_id,))

    if missing and missing['c'] > 0:
        result.append({
            'icon': '⚠️',
            'text': f'{missing["c"]} dishes need recipe costing',
            'sub': 'Add recipes to see true profitability'
        })

    # ─── 6. Best day of week ───
    best_day = execute_one("""
        SELECT
            TO_CHAR(order_date, 'Day') AS day_name,
            COUNT(*) AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
        GROUP BY TO_CHAR(order_date, 'Day'), EXTRACT(DOW FROM order_date)
        ORDER BY orders DESC
        LIMIT 1
    """, (kitchen_id,))

    if best_day:
        result.append({
            'icon': '📅',
            'text': f'Best day: {best_day["day_name"].strip()}',
            'sub': f'{best_day["orders"]} orders on this day'
        })

    return jsonify(result)


# ==========================================
# CATEGORIES (For filter dropdown)
# ==========================================
@recommendations_bp.route('/categories', methods=['GET'])
@token_required
def categories():
    """
    Available insight categories.
    """
    return jsonify([
        'Menu', 'Commission', 'Delivery', 'Operations',
        'Customers', 'Inventory', 'Revenue'
    ])

