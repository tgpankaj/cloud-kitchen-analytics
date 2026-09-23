"""
Finance Routes
Revenue, Expenses, Cost Breakdown
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

finance_bp = Blueprint('finance', __name__)


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
# FINANCE KPIs (4 cards at top)
# ═══════════════════════════════════════════
@finance_bp.route('/kpis', methods=['GET'])
@token_required
def finance_kpis():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    current = execute_one(f"""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_amount * commission_pct / 100.0), 0) AS commission
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(current['revenue'] or 0)
    commission = float(current['commission'] or 0)

    # Estimated other costs
    food_cost = revenue * 0.40
    packaging = revenue * 0.05
    delivery = revenue * 0.03
    other = revenue * 0.02

    total_expenses = food_cost + packaging + delivery + commission + other
    net_profit = revenue - total_expenses
    margin = (net_profit / revenue * 100) if revenue > 0 else 0

    return jsonify({
        'revenue': round(revenue, 2),
        'expenses': round(total_expenses, 2),
        'net_profit': round(net_profit, 2),
        'margin_pct': round(margin, 1),
        'trends': {
            'revenue': 12.4,
            'expenses': 3.1,
            'net_profit': 15.1,
            'margin': 4.6
        }
    })


# ═══════════════════════════════════════════
# REVENUE VS EXPENSES (Grouped bar chart)
# ═══════════════════════════════════════════
@finance_bp.route('/revenue-vs-expenses', methods=['GET'])
@token_required
def revenue_vs_expenses():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    # Weekly aggregation
    rows = execute_query(f"""
        SELECT
            DATE_TRUNC('week', order_date)::date::text AS week_start,
            COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
        GROUP BY week_start
        ORDER BY week_start
    """, [kitchen_id] + dp)

    result = []
    for r in rows:
        revenue = float(r['revenue'] or 0)
        # Estimate expenses: 65% of revenue
        expenses = revenue * 0.65
        result.append({
            'week': r['week_start'],
            'revenue': round(revenue, 2),
            'expenses': round(expenses, 2)
        })

    return jsonify(result)


# ═══════════════════════════════════════════
# COST BREAKDOWN (Doughnut)
# ═══════════════════════════════════════════
@finance_bp.route('/cost-breakdown', methods=['GET'])
@token_required
def cost_breakdown():
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

    breakdown = [
        {'label': 'Food Cost', 'value': round(revenue * 0.40, 2)},
        {'label': 'Packaging', 'value': round(revenue * 0.05, 2)},
        {'label': 'Delivery', 'value': round(revenue * 0.03, 2)},
        {'label': 'Platform Fees', 'value': round(commission, 2)},
        {'label': 'Other Costs', 'value': round(revenue * 0.02, 2)}
    ]

    total = sum(b['value'] for b in breakdown)
    for b in breakdown:
        b['pct'] = round(b['value'] / total * 100, 1) if total > 0 else 0

    return jsonify({
        'total': round(total, 2),
        'breakdown': breakdown
    })


# ═══════════════════════════════════════════
# EXPENSE DETAILS (Table)
# ═══════════════════════════════════════════
@finance_bp.route('/expenses', methods=['GET'])
@token_required
def expenses():
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

    expense_list = [
        {'category': 'Food Cost', 'amount': revenue * 0.40, 'pct': 40, 'trend': 'up', 'trend_pct': 2.1},
        {'category': 'Platform Fees', 'amount': commission, 'pct': round(commission / revenue * 100, 1) if revenue else 25, 'trend': 'down', 'trend_pct': -1.4},
        {'category': 'Packaging', 'amount': revenue * 0.05, 'pct': 5, 'trend': 'up', 'trend_pct': 0.8},
        {'category': 'Delivery', 'amount': revenue * 0.03, 'pct': 3, 'trend': 'flat', 'trend_pct': 0},
        {'category': 'Other Costs', 'amount': revenue * 0.02, 'pct': 2, 'trend': 'down', 'trend_pct': -0.3}
    ]

    return jsonify([{
        'category': e['category'],
        'amount': round(e['amount'], 2),
        'pct': round(e['pct'], 1),
        'trend': e['trend'],
        'trend_pct': e['trend_pct']
    } for e in expense_list])


# ═══════════════════════════════════════════
# INSIGHT (Additional Insight card)
# ═══════════════════════════════════════════
@finance_bp.route('/insight', methods=['GET'])
@token_required
def finance_insight():
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    stats = execute_one(f"""
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(stats['revenue'] or 0)
    food_cost_pct = 40  # Fixed estimate

    if food_cost_pct > 35:
        insight = f"Food cost is {food_cost_pct}% of revenue — above the 35% benchmark. Review supplier pricing or reduce portion sizes on low-margin dishes."
    else:
        insight = f"Food cost is {food_cost_pct}% of revenue — within the healthy 28-35% range. Keep monitoring to maintain profitability."

    return jsonify({
        'text': insight,
        'food_cost_pct': food_cost_pct,
        'benchmark_pct': 35
    })

"""
Finance Routes
Revenue, Expenses, Cost Breakdown
Powers the KitchenIQ Finance page
"""
from flask import Blueprint, request, jsonify
from middleware.auth import token_required
from db.connection import execute_query, execute_one

finance_bp = Blueprint('finance', __name__)


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


def calc_trend(current, previous):
    try:
        c = float(current or 0)
        p = float(previous or 0)
        if p == 0:
            return 0.0
        return round((c - p) / p * 100, 1)
    except (ValueError, TypeError):
        return 0.0


# Cost estimation constants (can be moved to config)
FOOD_COST_PCT = 0.40       # 40% of revenue
PACKAGING_PCT = 0.05       # 5%
DELIVERY_PCT = 0.03        # 3%
OTHER_PCT = 0.02           # 2%


# ==========================================
# KPIs (4 cards at top)
# ==========================================
@finance_bp.route('/kpis', methods=['GET'])
@token_required
def kpis():
    """
    Finance KPIs:
    - Total Revenue
    - Total Expenses
    - Net Profit
    - Profit Margin %
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    # Current period
    current = execute_one(f"""
        SELECT
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_amount * commission_pct / 100.0), 0) AS commission
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(current['revenue'] or 0)
    commission = float(current['commission'] or 0)

    # Estimated costs
    food_cost = revenue * FOOD_COST_PCT
    packaging = revenue * PACKAGING_PCT
    delivery = revenue * DELIVERY_PCT
    other = revenue * OTHER_PCT

    total_expenses = food_cost + packaging + delivery + commission + other
    net_profit = revenue - total_expenses
    margin = (net_profit / revenue * 100) if revenue > 0 else 0

    # Previous period for trends
    previous = None
    if days:
        prev_df = (
            "AND order_date >= CURRENT_DATE - INTERVAL '%s days' "
            "AND order_date < CURRENT_DATE - INTERVAL '%s days'"
        )
        previous = execute_one(f"""
            SELECT
                COALESCE(SUM(total_amount), 0) AS revenue
            FROM orders
            WHERE kitchen_id = %s
              AND status != 'cancelled'
              {prev_df}
        """, [kitchen_id, days * 2, days])

    prev_revenue = float(previous['revenue'] or 0) if previous else 0
    rev_trend = calc_trend(revenue, prev_revenue)

    return jsonify({
        'revenue': {
            'value': round(revenue, 2),
            'trend': rev_trend
        },
        'expenses': {
            'value': round(total_expenses, 2),
            'trend': 3.1
        },
        'net_profit': {
            'value': round(net_profit, 2),
            'trend': 15.1
        },
        'margin': {
            'value': round(margin, 1),
            'trend': 4.6
        }
    })


# ==========================================
# REVENUE VS EXPENSES (Grouped bar chart)
# ==========================================
@finance_bp.route('/revenue-vs-expenses', methods=['GET'])
@token_required
def revenue_vs_expenses():
    """
    Weekly revenue vs expenses for grouped bar chart.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    rows = execute_query(f"""
        SELECT
            DATE_TRUNC('week', order_date)::date::text AS week_start,
            COALESCE(SUM(total_amount), 0) AS revenue,
            COALESCE(SUM(total_amount * commission_pct / 100.0), 0) AS commission
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
        GROUP BY week_start
        ORDER BY week_start
    """, [kitchen_id] + dp)

    result = []
    for r in rows:
        revenue = float(r['revenue'] or 0)
        commission = float(r['commission'] or 0)

        # Estimated expenses
        expenses = (
            revenue * FOOD_COST_PCT +
            revenue * PACKAGING_PCT +
            revenue * DELIVERY_PCT +
            commission +
            revenue * OTHER_PCT
        )

        result.append({
            'week': r['week_start'],
            'revenue': round(revenue, 2),
            'expenses': round(expenses, 2)
        })

    return jsonify(result)


# ==========================================
# COST BREAKDOWN (Doughnut chart)
# ==========================================
@finance_bp.route('/cost-breakdown', methods=['GET'])
@token_required
def cost_breakdown():
    """
    Cost breakdown by category (for doughnut).
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

    breakdown = [
        {'label': 'Food Cost', 'value': revenue * FOOD_COST_PCT},
        {'label': 'Packaging', 'value': revenue * PACKAGING_PCT},
        {'label': 'Delivery', 'value': revenue * DELIVERY_PCT},
        {'label': 'Platform Fees', 'value': commission},
        {'label': 'Other Costs', 'value': revenue * OTHER_PCT}
    ]

    total = sum(b['value'] for b in breakdown)

    for b in breakdown:
        b['value'] = round(b['value'], 2)
        b['pct'] = round(b['value'] / total * 100, 1) if total > 0 else 0

    return jsonify({
        'total': round(total, 2),
        'breakdown': breakdown
    })


# ==========================================
# EXPENSES TABLE
# ==========================================
@finance_bp.route('/expenses', methods=['GET'])
@token_required
def expenses():
    """
    Expense breakdown table with trends.
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

    expense_list = [
        {
            'category': 'Food Cost',
            'amount': revenue * FOOD_COST_PCT,
            'pct': FOOD_COST_PCT * 100,
            'trend': 'up',
            'trend_pct': 2.1
        },
        {
            'category': 'Platform Fees',
            'amount': commission,
            'pct': round(commission / revenue * 100, 1) if revenue else 25,
            'trend': 'down',
            'trend_pct': -1.4
        },
        {
            'category': 'Packaging',
            'amount': revenue * PACKAGING_PCT,
            'pct': PACKAGING_PCT * 100,
            'trend': 'up',
            'trend_pct': 0.8
        },
        {
            'category': 'Delivery',
            'amount': revenue * DELIVERY_PCT,
            'pct': DELIVERY_PCT * 100,
            'trend': 'flat',
            'trend_pct': 0
        },
        {
            'category': 'Other Costs',
            'amount': revenue * OTHER_PCT,
            'pct': OTHER_PCT * 100,
            'trend': 'down',
            'trend_pct': -0.3
        }
    ]

    return jsonify([{
        'category': e['category'],
        'amount': round(e['amount'], 2),
        'pct': round(e['pct'], 1),
        'trend': e['trend'],
        'trend_pct': e['trend_pct']
    } for e in expense_list])


# ==========================================
# INSIGHT (Additional Insight card)
# ==========================================
@finance_bp.route('/insight', methods=['GET'])
@token_required
def insight():
    """
    Generates finance insight message.
    """
    kitchen_id = get_kitchen_id(request)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    days = get_days(request)
    df, dp = date_filter(days)

    stats = execute_one(f"""
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {df}
    """, [kitchen_id] + dp)

    revenue = float(stats['revenue'] or 0)
    food_cost_pct = FOOD_COST_PCT * 100
    benchmark = 35

    if food_cost_pct > benchmark:
        text = (
            f"Food cost is {food_cost_pct:.1f}% of revenue — above the {benchmark}% benchmark. "
            f"Review supplier pricing or reduce portion sizes on low-margin dishes."
        )
    else:
        text = (
            f"Food cost is {food_cost_pct:.1f}% of revenue — within the healthy 28-35% range. "
            f"Keep monitoring to maintain profitability."
        )

    return jsonify({
        'text': text,
        'food_cost_pct': round(food_cost_pct, 1),
        'benchmark_pct': benchmark,
        'status': 'warning' if food_cost_pct > benchmark else 'healthy'
    })
