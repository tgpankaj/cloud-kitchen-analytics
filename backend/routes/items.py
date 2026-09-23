"""
Item Performance Routes
Profitability, menu engineering, best/worst, CSV export.
"""
from flask import Blueprint, request, jsonify, Response
from middleware.auth import token_required
from db.connection import execute_query, execute_one
import csv
import io

items_bp = Blueprint('items', __name__)


def get_kitchen_id(request):
    """Helper: get kitchen_id from query params or user's default."""
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
    """Helper: extract days filter (default 30)."""
    days = request.args.get('days', '30')
    if days == 'all':
        return None
    try:
        return int(days)
    except ValueError:
        return 30


def build_date_filter(days):
    """Helper: returns SQL condition and params."""
    if days is None:
        return "", []
    return "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'", [days]


def classify_menu_item(quantity_sold, profit_margin, avg_qty, avg_margin):
    """
    Classify item into Star/Plowhorse/Puzzle/Dog.
    Based on median thresholds.
    """
    high_popularity = quantity_sold > avg_qty
    high_margin = profit_margin > avg_margin

    if high_popularity and high_margin:
        return 'Star'
    elif high_popularity and not high_margin:
        return 'Plowhorse'
    elif not high_popularity and high_margin:
        return 'Puzzle'
    else:
        return 'Dog'


# ==========================================
# ENDPOINT 1: Item Performance (main data)
# ==========================================
@items_bp.route('/performance', methods=['GET'])
@token_required
def item_performance():
    """
    Returns all items with:
    - quantity_sold, gross_revenue, net_revenue
    - cost, net_profit, profit_margin
    - avg_prep_time
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            mi.cost_price,
            mi.selling_price,
            mi.prep_time_minutes AS default_prep_time,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost,
            COALESCE(AVG(o.prep_time_minutes), mi.prep_time_minutes) AS avg_prep_time
        FROM menu_items mi
        LEFT JOIN order_items oi ON oi.menu_item_id = mi.id
        LEFT JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category,
                 mi.cost_price, mi.selling_price, mi.prep_time_minutes
        ORDER BY net_revenue DESC
    """

    params = date_params + [kitchen_id]
    rows = execute_query(sql, params)

    items = []
    for row in rows:
        r = dict(row)
        net_rev = float(r['net_revenue'] or 0)
        total_cost = float(r['total_cost'] or 0)
        qty = int(r['quantity_sold'] or 0)
        net_profit = net_rev - total_cost
        margin = (net_profit / net_rev * 100) if net_rev > 0 else 0

        r['net_revenue'] = round(net_rev, 2)
        r['total_cost'] = round(total_cost, 2)
        r['net_profit'] = round(net_profit, 2)
        r['profit_margin'] = round(margin, 1)
        r['gross_revenue'] = round(float(r['gross_revenue'] or 0), 2)
        r['avg_prep_time'] = int(r['avg_prep_time'] or 15)

        items.append(r)

    return jsonify(items)


# ==========================================
# ENDPOINT 2: Best & Worst Items
# ==========================================
@items_bp.route('/best-worst', methods=['GET'])
@token_required
def best_worst_items():
    """
    Returns top 5 (best) and bottom 5 (worst) items by net profit.
    Only considers items with quantity_sold > 0.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category
        HAVING SUM(oi.quantity) > 0
    """

    params = date_params + [kitchen_id]
    rows = execute_query(sql, params)

    items = []
    for row in rows:
        r = dict(row)
        net_rev = float(r['net_revenue'] or 0)
        total_cost = float(r['total_cost'] or 0)
        net_profit = net_rev - total_cost
        margin = (net_profit / net_rev * 100) if net_rev > 0 else 0

        r['net_revenue'] = round(net_rev, 2)
        r['net_profit'] = round(net_profit, 2)
        r['profit_margin'] = round(margin, 1)
        r['gross_revenue'] = round(float(r['gross_revenue'] or 0), 2)
        items.append(r)

    # Sort by net profit
    sorted_items = sorted(items, key=lambda x: x['net_profit'], reverse=True)

    best = sorted_items[:5]
    worst = sorted_items[-5:][::-1] if len(sorted_items) >= 5 else sorted_items[::-1]

    return jsonify({
        'best': best,
        'worst': worst,
        'total_items': len(items)
    })


# ==========================================
# ENDPOINT 3: Menu Engineering
# ==========================================
@items_bp.route('/menu-engineering', methods=['GET'])
@token_required
def menu_engineering():
    """
    Classify items into Stars / Plowhorses / Puzzles / Dogs.
    Uses median thresholds for popularity and margin.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category
        HAVING SUM(oi.quantity) > 0
    """

    params = date_params + [kitchen_id]
    rows = execute_query(sql, params)

    if not rows:
        return jsonify({
            'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': [],
            'thresholds': {'popularity': 0, 'margin': 0}
        })

    # Compute metrics for each item
    items = []
    for row in rows:
        r = dict(row)
        net_rev = float(r['net_revenue'] or 0)
        total_cost = float(r['total_cost'] or 0)
        net_profit = net_rev - total_cost
        margin = (net_profit / net_rev * 100) if net_rev > 0 else 0

        r['quantity_sold'] = int(r['quantity_sold'] or 0)
        r['gross_revenue'] = round(float(r['gross_revenue'] or 0), 2)
        r['net_revenue'] = round(net_rev, 2)
        r['net_profit'] = round(net_profit, 2)
        r['profit_margin'] = round(margin, 1)
        items.append(r)

    # Median thresholds
    quantities = sorted([i['quantity_sold'] for i in items])
    margins = sorted([i['profit_margin'] for i in items])

    def median(arr):
        n = len(arr)
        if n == 0:
            return 0
        return arr[n // 2] if n % 2 == 1 else (arr[n // 2 - 1] + arr[n // 2]) / 2

    threshold_qty = median(quantities)
    threshold_margin = median(margins)

    # Classify
    result = {'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': []}
    for item in items:
        category = classify_menu_item(
            item['quantity_sold'],
            item['profit_margin'],
            threshold_qty,
            threshold_margin
        )
        item['engineering_category'] = category
        key = category.lower() + 's'
        result[key].append(item)

    # Sort within each category
    for key in result:
        if key in ['stars', 'puzzles']:
            result[key].sort(key=lambda x: x['net_profit'], reverse=True)
        else:
            result[key].sort(key=lambda x: x['net_profit'], reverse=True)

    return jsonify({
        **result,
        'thresholds': {
            'popularity': round(threshold_qty, 1),
            'margin': round(threshold_margin, 1)
        },
        'summary': {
            'stars': len(result['stars']),
            'plowhorses': len(result['plowhorses']),
            'puzzles': len(result['puzzles']),
            'dogs': len(result['dogs'])
        }
    })


# ==========================================
# ENDPOINT 4: CSV Export
# ==========================================
@items_bp.route('/export', methods=['GET'])
@token_required
def export_items_csv():
    """Download item performance as CSV."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_date_range(request)
    date_sql, date_params = build_date_filter(days)

    sql = f"""
        SELECT
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            mi.cost_price,
            mi.selling_price,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        LEFT JOIN order_items oi ON oi.menu_item_id = mi.id
        LEFT JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {date_sql}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category, mi.cost_price, mi.selling_price
        ORDER BY net_revenue DESC
    """

    params = date_params + [kitchen_id]
    rows = execute_query(sql, params)

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Item Name', 'Category', 'Cost Price', 'Selling Price',
        'Quantity Sold', 'Gross Revenue', 'Net Revenue',
        'Total Cost', 'Net Profit', 'Profit Margin (%)'
    ])

    for row in rows:
        net_rev = float(row['net_revenue'] or 0)
        total_cost = float(row['total_cost'] or 0)
        net_profit = net_rev - total_cost
        margin = (net_profit / net_rev * 100) if net_rev > 0 else 0

        writer.writerow([
            row['name'],
            row['category'],
            float(row['cost_price'] or 0),
            float(row['selling_price'] or 0),
            int(row['quantity_sold'] or 0),
            float(row['gross_revenue'] or 0),
            round(net_rev, 2),
            round(total_cost, 2),
            round(net_profit, 2),
            round(margin, 1)
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=item-performance.csv'
        }
    )


# ═══════════════════════════════════════════
# NEW: CATEGORIES (Dishes filter dropdown)
# ═══════════════════════════════════════════
@items_bp.route('/categories', methods=['GET'])
@token_required
def list_categories():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query("""
        SELECT DISTINCT category
        FROM menu_items
        WHERE kitchen_id = %s
          AND category IS NOT NULL
          AND category != ''
          AND is_active = TRUE
        ORDER BY category
    """, (kitchen_id,))

    return jsonify([r['category'] for r in rows])



    """
Items / Dishes Routes
Updated for KitchenIQ Dishes page
"""
from flask import Blueprint, request, jsonify, Response
from middleware.auth import token_required
from db.connection import execute_query, execute_one
import csv
import io

items_bp = Blueprint('items', __name__)


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


def date_filter(days, alias='o'):
    if days is None:
        return "", []
    return f"AND {alias}.order_date >= CURRENT_DATE - INTERVAL '%s days'", [days]


def get_recommendation(margin_pct, orders):
    """
    Determine recommendation category based on margin and volume.
    Matches frontend logic.
    """
    if margin_pct >= 40 and orders >= 100:
        return 'promote'
    if margin_pct >= 40 and orders < 100:
        return 'growth'
    if margin_pct < 30 and orders >= 100:
        return 'optimize'
    return 'review'


# ==========================================
# PERFORMANCE (Main Dishes table)
# ==========================================
@items_bp.route('/performance', methods=['GET'])
@token_required
def performance():
    """
    All dishes with performance metrics.
    Used by: Dishes page main table, Dashboard top dishes
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            mi.cost_price,
            mi.selling_price,
            mi.prep_time_minutes,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        LEFT JOIN order_items oi ON oi.menu_item_id = mi.id
        LEFT JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {df}
        WHERE mi.kitchen_id = %s
          AND mi.is_active = TRUE
        GROUP BY mi.id, mi.name, mi.category, mi.cost_price,
                 mi.selling_price, mi.prep_time_minutes
        ORDER BY net_revenue DESC
    """, dp + [kitchen_id])

    result = []
    for r in rows:
        net_rev = float(r['net_revenue'] or 0)
        cost = float(r['total_cost'] or 0)
        qty = int(r['quantity_sold'] or 0)
        profit = net_rev - cost
        margin = (profit / net_rev * 100) if net_rev > 0 else 0
        food_cost_pct = (cost / net_rev * 100) if net_rev > 0 else 0

        # Simulated rating based on prep time (faster = better, cap 3.5-5.0)
        prep = int(r['prep_time_minutes'] or 15)
        rating = round(max(3.5, min(5.0, 5.0 - (prep - 10) * 0.03)), 1)

        result.append({
            'id': r['id'],
            'name': r['name'],
            'category': r['category'],
            'cost_price': round(float(r['cost_price'] or 0), 2),
            'selling_price': round(float(r['selling_price'] or 0), 2),
            'prep_time_minutes': prep,
            'quantity_sold': qty,
            'gross_revenue': round(float(r['gross_revenue'] or 0), 2),
            'net_revenue': round(net_rev, 2),
            'total_cost': round(cost, 2),
            'net_profit': round(profit, 2),
            'profit_margin': round(margin, 1),
            'food_cost_pct': round(food_cost_pct, 1),
            'rating': rating,
            'recommendation': get_recommendation(margin, qty)
        })

    return jsonify(result)


# ==========================================
# CATEGORIES (Filter dropdown)
# ==========================================
@items_bp.route('/categories', methods=['GET'])
@token_required
def categories():
    """
    Get unique categories for filter dropdown.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify([])

    rows = execute_query("""
        SELECT DISTINCT category
        FROM menu_items
        WHERE kitchen_id = %s
          AND category IS NOT NULL
          AND category != ''
          AND is_active = TRUE
        ORDER BY category
    """, (kitchen_id,))

    return jsonify([r['category'] for r in rows])


# ==========================================
# BEST & WORST
# ==========================================
@items_bp.route('/best-worst', methods=['GET'])
@token_required
def best_worst():
    """
    Top 5 + Bottom 5 dishes by profit.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {df}
        GROUP BY mi.id, mi.name, mi.category
        HAVING SUM(oi.quantity) > 0
    """, [kitchen_id] + dp)

    items = []
    for r in rows:
        net_rev = float(r['net_revenue'] or 0)
        cost = float(r['total_cost'] or 0)
        profit = net_rev - cost
        margin = (profit / net_rev * 100) if net_rev > 0 else 0
        items.append({
            'id': r['id'],
            'name': r['name'],
            'category': r['category'],
            'quantity_sold': int(r['quantity_sold'] or 0),
            'net_revenue': round(net_rev, 2),
            'net_profit': round(profit, 2),
            'profit_margin': round(margin, 1)
        })

    sorted_items = sorted(items, key=lambda x: x['net_profit'], reverse=True)
    best = sorted_items[:5]
    worst = sorted_items[-5:][::-1] if len(sorted_items) >= 5 else sorted_items[::-1]

    return jsonify({
        'best': best,
        'worst': worst,
        'total_items': len(items)
    })


# ==========================================
# MENU ENGINEERING
# ==========================================
@items_bp.route('/menu-engineering', methods=['GET'])
@token_required
def menu_engineering():
    """
    Classify dishes into Stars/Plowhorses/Puzzles/Dogs.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            mi.id,
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {df}
        GROUP BY mi.id, mi.name, mi.category
        HAVING SUM(oi.quantity) > 0
    """, [kitchen_id] + dp)

    if not rows:
        return jsonify({
            'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': [],
            'thresholds': {'popularity': 0, 'margin': 0}
        })

    items = []
    for r in rows:
        net_rev = float(r['net_revenue'] or 0)
        cost = float(r['total_cost'] or 0)
        profit = net_rev - cost
        margin = (profit / net_rev * 100) if net_rev > 0 else 0

        items.append({
            'id': r['id'],
            'name': r['name'],
            'category': r['category'],
            'quantity_sold': int(r['quantity_sold'] or 0),
            'net_revenue': round(net_rev, 2),
            'net_profit': round(profit, 2),
            'profit_margin': round(margin, 1)
        })

    # Median thresholds
    quantities = sorted([i['quantity_sold'] for i in items])
    margins = sorted([i['profit_margin'] for i in items])

    def median(arr):
        n = len(arr)
        if n == 0:
            return 0
        return arr[n // 2] if n % 2 else (arr[n // 2 - 1] + arr[n // 2]) / 2

    t_qty = median(quantities)
    t_margin = median(margins)

    buckets = {'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': []}

    for item in items:
        high_pop = item['quantity_sold'] > t_qty
        high_margin = item['profit_margin'] > t_margin

        if high_pop and high_margin:
            item['category_eng'] = 'Star'
            buckets['stars'].append(item)
        elif high_pop and not high_margin:
            item['category_eng'] = 'Plowhorse'
            buckets['plowhorses'].append(item)
        elif not high_pop and high_margin:
            item['category_eng'] = 'Puzzle'
            buckets['puzzles'].append(item)
        else:
            item['category_eng'] = 'Dog'
            buckets['dogs'].append(item)

    return jsonify({
        'stars': buckets['stars'],
        'plowhorses': buckets['plowhorses'],
        'puzzles': buckets['puzzles'],
        'dogs': buckets['dogs'],
        'thresholds': {
            'popularity': round(t_qty, 1),
            'margin': round(t_margin, 1)
        }
    })


# ==========================================
# EXPORT CSV
# ==========================================
@items_bp.route('/export', methods=['GET'])
@token_required
def export_items():
    """Export dishes as CSV."""
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            mi.name,
            COALESCE(mi.category, 'Uncategorized') AS category,
            mi.cost_price,
            mi.selling_price,
            COALESCE(SUM(oi.quantity), 0) AS quantity_sold,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS gross_revenue,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS total_cost
        FROM menu_items mi
        LEFT JOIN order_items oi ON oi.menu_item_id = mi.id
        LEFT JOIN orders o ON o.id = oi.order_id
            AND o.status != 'cancelled'
            {df}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category, mi.cost_price, mi.selling_price
        ORDER BY net_revenue DESC
    """, dp + [kitchen_id])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Dish', 'Category', 'Cost Price', 'Selling Price',
        'Quantity Sold', 'Gross Revenue', 'Net Revenue',
        'Total Cost', 'Net Profit', 'Margin %'
    ])

    for r in rows:
        net_rev = float(r['net_revenue'] or 0)
        cost = float(r['total_cost'] or 0)
        profit = net_rev - cost
        margin = (profit / net_rev * 100) if net_rev > 0 else 0

        writer.writerow([
            r['name'],
            r['category'],
            float(r['cost_price'] or 0),
            float(r['selling_price'] or 0),
            int(r['quantity_sold'] or 0),
            round(float(r['gross_revenue'] or 0), 2),
            round(net_rev, 2),
            round(cost, 2),
            round(profit, 2),
            round(margin, 1)
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=dishes.csv'}
    )