"""
Reports / Export Routes
CSV exports for analytics
"""
from flask import Blueprint, request, jsonify, Response
from middleware.auth import token_required
from db.connection import execute_query, execute_one
import csv
import io

reports_bp = Blueprint('reports', __name__)


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


# ═══════════════════════════════════════════
# EXPORT ITEMS CSV (Dishes page)
# ═══════════════════════════════════════════
@reports_bp.route('/items.csv', methods=['GET'])
@token_required
def export_items():
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
        LEFT JOIN orders o ON o.id = oi.order_id AND o.status != 'cancelled' {df}
        WHERE mi.kitchen_id = %s
        GROUP BY mi.id, mi.name, mi.category, mi.cost_price, mi.selling_price
        ORDER BY net_revenue DESC
    """, dp + [kitchen_id])

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Item Name', 'Category', 'Cost Price', 'Selling Price',
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
        headers={'Content-Disposition': 'attachment; filename=items.csv'}
    )


# ═══════════════════════════════════════════
# EXPORT FINANCE CSV
# ═══════════════════════════════════════════
@reports_bp.route('/finance.csv', methods=['GET'])
@token_required
def export_finance():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    stats = execute_one(f"""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_amount * commission_pct / 100.0), 0) AS commission
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(stats['revenue'] or 0)
    commission = float(stats['commission'] or 0)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Category', 'Amount (₹)', '% of Revenue'])
    writer.writerow(['Total Revenue', round(revenue, 2), '100%'])
    writer.writerow(['Food Cost', round(revenue * 0.40, 2), '40%'])
    writer.writerow(['Platform Fees', round(commission, 2), f"{commission/revenue*100:.1f}%" if revenue else "0%"])
    writer.writerow(['Packaging', round(revenue * 0.05, 2), '5%'])
    writer.writerow(['Delivery', round(revenue * 0.03, 2), '3%'])
    writer.writerow(['Other Costs', round(revenue * 0.02, 2), '2%'])
    writer.writerow([])
    writer.writerow(['Net Profit', round(revenue - (revenue * 0.40 + commission + revenue * 0.05 + revenue * 0.03 + revenue * 0.02), 2)])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=finance.csv'}
    )

"""
Reports / CSV Exports
Powers the "Export" buttons across the app
"""
from flask import Blueprint, request, jsonify, Response
from middleware.auth import token_required
from db.connection import execute_query, execute_one
import csv
import io
from datetime import datetime

reports_bp = Blueprint('reports', __name__)


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


def csv_response(rows, headers, filename):
    """Build CSV response."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    for row in rows:
        writer.writerow(row)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    full_filename = f"{filename}_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={full_filename}'
        }
    )


# ==========================================
# EXPORT: DISHES / ITEMS
# ==========================================
@reports_bp.route('/items.csv', methods=['GET'])
@token_required
def export_items():
    """
    Export all dishes with performance metrics.
    """
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

    headers = [
        'Dish', 'Category', 'Cost Price', 'Selling Price',
        'Quantity Sold', 'Gross Revenue', 'Net Revenue',
        'Total Cost', 'Net Profit', 'Margin %'
    ]

    csv_rows = []
    for r in rows:
        net_rev = float(r['net_revenue'] or 0)
        cost = float(r['total_cost'] or 0)
        profit = net_rev - cost
        margin = (profit / net_rev * 100) if net_rev > 0 else 0

        csv_rows.append([
            r['name'],
            r['category'],
            round(float(r['cost_price'] or 0), 2),
            round(float(r['selling_price'] or 0), 2),
            int(r['quantity_sold'] or 0),
            round(float(r['gross_revenue'] or 0), 2),
            round(net_rev, 2),
            round(cost, 2),
            round(profit, 2),
            round(margin, 1)
        ])

    return csv_response(csv_rows, headers, 'dishes')


# ==========================================
# EXPORT: FINANCE
# ==========================================
@reports_bp.route('/finance.csv', methods=['GET'])
@token_required
def export_finance():
    """
    Export finance breakdown.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    stats = execute_one(f"""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_amount * commission_pct / 100.0), 0) AS commission
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(stats['revenue'] or 0)
    commission = float(stats['commission'] or 0)

    food_cost = revenue * 0.40
    packaging = revenue * 0.05
    delivery = revenue * 0.03
    other = revenue * 0.02
    total_expenses = food_cost + packaging + delivery + commission + other
    net_profit = revenue - total_expenses
    margin = (net_profit / revenue * 100) if revenue > 0 else 0

    headers = ['Category', 'Amount (INR)', '% of Revenue']
    csv_rows = [
        ['Total Revenue', round(revenue, 2), '100.0%'],
        ['Food Cost', round(food_cost, 2), f'{(food_cost/revenue*100):.1f}%' if revenue else '0%'],
        ['Platform Fees', round(commission, 2), f'{(commission/revenue*100):.1f}%' if revenue else '0%'],
        ['Packaging', round(packaging, 2), f'{(packaging/revenue*100):.1f}%' if revenue else '0%'],
        ['Delivery', round(delivery, 2), f'{(delivery/revenue*100):.1f}%' if revenue else '0%'],
        ['Other Costs', round(other, 2), f'{(other/revenue*100):.1f}%' if revenue else '0%'],
        ['', '', ''],
        ['Total Expenses', round(total_expenses, 2), f'{(total_expenses/revenue*100):.1f}%' if revenue else '0%'],
        ['Net Profit', round(net_profit, 2), f'{margin:.1f}%']
    ]

    return csv_response(csv_rows, headers, 'finance')


# ==========================================
# EXPORT: ORDERS
# ==========================================
@reports_bp.route('/orders.csv', methods=['GET'])
@token_required
def export_orders():
    """
    Export recent orders.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    limit = min(int(request.args.get('limit', 500)), 5000)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            o.id,
            o.order_date::text AS date,
            o.order_time::text AS time,
            o.platform,
            o.customer_phone,
            o.total_amount,
            o.commission_pct,
            o.total_amount * (1 - o.commission_pct/100.0) AS net_amount,
            o.status
        FROM orders o
        WHERE o.kitchen_id = %s
          {df}
        ORDER BY o.id DESC
        LIMIT %s
    """, [kitchen_id] + dp + [limit])

    headers = [
        'Order ID', 'Date', 'Time', 'Platform', 'Customer Phone',
        'Amount', 'Commission %', 'Net Amount', 'Status'
    ]

    csv_rows = []
    for r in rows:
        csv_rows.append([
            f"#ORD{r['id']:04d}",
            r['date'],
            (r['time'] or '')[:5] if r['time'] else '',
            r['platform'],
            r['customer_phone'] or 'Guest',
            round(float(r['total_amount'] or 0), 2),
            round(float(r['commission_pct'] or 0), 1),
            round(float(r['net_amount'] or 0), 2),
            r['status']
        ])

    return csv_response(csv_rows, headers, 'orders')


# ==========================================
# EXPORT: CUSTOMERS
# ==========================================
@reports_bp.route('/customers.csv', methods=['GET'])
@token_required
def export_customers():
    """
    Export customer list with stats.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            customer_phone AS phone,
            COUNT(*) AS frequency,
            COALESCE(SUM(total_amount), 0) AS monetary,
            COALESCE(AVG(total_amount), 0) AS avg_value,
            MAX(order_date)::text AS last_order_date,
            (CURRENT_DATE - MAX(order_date)) AS recency_days
        FROM orders
        WHERE kitchen_id = %s
          AND customer_phone IS NOT NULL
          AND status != 'cancelled'
          {df}
        GROUP BY customer_phone
        ORDER BY monetary DESC
    """, [kitchen_id] + dp)

    headers = [
        'Phone', 'Frequency', 'Monetary Value', 'Avg Order Value',
        'Last Order Date', 'Recency Days'
    ]

    csv_rows = [[
        r['phone'],
        int(r['frequency']),
        round(float(r['monetary'] or 0), 2),
        round(float(r['avg_value'] or 0), 2),
        r['last_order_date'],
        int(r['recency_days'] or 0)
    ] for r in rows]

    return csv_response(csv_rows, headers, 'customers')


# ==========================================
# EXPORT: ANALYTICS SUMMARY
# ==========================================
@reports_bp.route('/analytics.csv', methods=['GET'])
@token_required
def export_analytics():
    """
    Export daily analytics summary.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            order_date::text AS date,
            COUNT(*) AS orders,
            COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
            COALESCE(SUM(total_amount), 0) AS gross_revenue,
            COALESCE(SUM(total_amount * (1 - commission_pct/100.0)), 0) AS net_revenue,
            COALESCE(AVG(total_amount), 0) AS avg_order_value
        FROM orders
        WHERE kitchen_id = %s
          {df}
        GROUP BY order_date
        ORDER BY order_date DESC
    """, [kitchen_id] + dp)

    headers = [
        'Date', 'Total Orders', 'Cancelled', 'Gross Revenue',
        'Net Revenue', 'Avg Order Value'
    ]

    csv_rows = [[
        r['date'],
        int(r['orders']),
        int(r['cancelled'] or 0),
        round(float(r['gross_revenue'] or 0), 2),
        round(float(r['net_revenue'] or 0), 2),
        round(float(r['avg_order_value'] or 0), 2)
    ] for r in rows]

    return csv_response(csv_rows, headers, 'analytics')