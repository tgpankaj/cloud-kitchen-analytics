"""
Rule-Based Insights Engine
Analyzes data and generates actionable business recommendations.
"""
from db.connection import execute_query, execute_one


# ==========================================
# INSIGHT RULES
# ==========================================

def rule_loss_making_items(kitchen_id, days):
    """Items that lose money after commission + cost."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    rows = execute_query(f"""
        SELECT
            mi.name,
            COALESCE(SUM(oi.quantity), 0) AS qty,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_rev,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {date_sql}
        GROUP BY mi.id, mi.name
        HAVING COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0)
             - COALESCE(SUM(oi.quantity * mi.cost_price), 0) < 0
    """, [kitchen_id] + params)

    insights = []
    for r in rows:
        loss = float(r['net_rev']) - float(r['cost'])
        insights.append({
            'type': 'danger',
            'category': 'Menu',
            'title': f"Remove or reprice: {r['name']}",
            'description': f"This item is losing ₹{abs(loss):.0f} after commission and cost. Sold {r['qty']} units.",
            'action': 'Increase price by 20% or remove from menu',
            'impact_score': min(abs(loss) / 100, 10),
            'metrics': {'loss': round(abs(loss), 2), 'qty_sold': int(r['qty'])}
        })
    return insights


def rule_low_margin_items(kitchen_id, days):
    """Items with margin < 30%."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    rows = execute_query(f"""
        SELECT
            mi.name,
            COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) AS net_rev,
            COALESCE(SUM(oi.quantity * mi.cost_price), 0) AS cost
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {date_sql}
        GROUP BY mi.id, mi.name
        HAVING COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0) > 0
           AND (COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0)
                - COALESCE(SUM(oi.quantity * mi.cost_price), 0))
               / COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 1) < 0.30
           AND COALESCE(SUM(oi.quantity * oi.unit_price * (1 - o.commission_pct/100.0)), 0)
                - COALESCE(SUM(oi.quantity * mi.cost_price), 0) >= 0
        ORDER BY net_rev DESC
        LIMIT 5
    """, [kitchen_id] + params)

    insights = []
    for r in rows:
        net_rev = float(r['net_rev'])
        cost = float(r['cost'])
        margin = ((net_rev - cost) / net_rev * 100) if net_rev else 0
        insights.append({
            'type': 'warning',
            'category': 'Menu',
            'title': f"Low margin: {r['name']}",
            'description': f"Profit margin is only {margin:.1f}%. Industry benchmark: 40-60%.",
            'action': 'Reduce portion size, renegotiate supplier, or increase price',
            'impact_score': 6,
            'metrics': {'margin_pct': round(margin, 1), 'net_revenue': round(net_rev, 2)}
        })
    return insights


def rule_high_commission(kitchen_id, days):
    """Platforms charging high commissions."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    rows = execute_query(f"""
        SELECT
            platform,
            AVG(commission_pct) AS avg_comm,
            SUM(total_amount) AS gross_rev,
            SUM(total_amount * commission_pct/100.0) AS commission_paid,
            COUNT(*) AS orders
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {date_sql}
        GROUP BY platform
        HAVING AVG(commission_pct) > 20
        ORDER BY SUM(total_amount * commission_pct/100.0) DESC
    """, [kitchen_id] + params)

    insights = []
    for r in rows:
        platform = r['platform']
        if platform.lower() == 'direct':
            continue

        comm_paid = float(r['commission_paid'])
        insights.append({
            'type': 'warning',
            'category': 'Commission',
            'title': f"{platform} is costing you ₹{comm_paid:,.0f}",
            'description': f"{r['orders']} orders on {platform} at {float(r['avg_comm']):.1f}% commission. You paid ₹{comm_paid:,.0f} in fees.",
            'action': f"Shift some {platform} customers to direct ordering (WhatsApp/Instagram) to save 15-20%",
            'impact_score': min(comm_paid / 500, 10),
            'metrics': {'commission_paid': round(comm_paid, 2), 'avg_pct': round(float(r['avg_comm']), 1)}
        })
    return insights


def rule_high_direct_share(kitchen_id, days):
    """Positive: High direct-order share."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        SELECT
            COUNT(*) FILTER (WHERE LOWER(platform) = 'direct') AS direct_orders,
            COUNT(*) AS total
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {date_sql}
    """, [kitchen_id] + params)

    if not result or not result['total']:
        return []

    direct_pct = (result['direct_orders'] / result['total'] * 100) if result['total'] else 0

    if direct_pct >= 20:
        return [{
            'type': 'success',
            'category': 'Commission',
            'title': f"Great direct-order share: {direct_pct:.1f}%",
            'description': f"{result['direct_orders']} of {result['total']} orders came through direct channels. You're saving significant commission.",
            'action': 'Keep promoting direct ordering — target 40%+',
            'impact_score': 5,
            'metrics': {'direct_pct': round(direct_pct, 1)}
        }]
    return []


def rule_late_deliveries(kitchen_id, days):
    """High late delivery rate."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        SELECT
            COUNT(*) FILTER (WHERE delivery_time_minutes > 45) AS late_orders,
            COUNT(*) AS total,
            AVG(prep_time_minutes) AS avg_prep
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          AND delivery_time_minutes IS NOT NULL
          {date_sql}
    """, [kitchen_id] + params)

    if not result or not result['total']:
        return []

    late_pct = (result['late_orders'] / result['total'] * 100) if result['total'] else 0

    if late_pct > 15:
        return [{
            'type': 'danger' if late_pct > 25 else 'warning',
            'category': 'Delivery',
            'title': f"High late delivery rate: {late_pct:.1f}%",
            'description': f"{result['late_orders']} of {result['total']} orders took >45 minutes. Average prep time: {float(result['avg_prep'] or 0):.0f} min.",
            'action': 'Optimize prep workflow, add staff during peak hours, or update delivery ETAs',
            'impact_score': min(late_pct / 3, 10),
            'metrics': {'late_pct': round(late_pct, 1), 'late_orders': int(result['late_orders'])}
        }]
    return []


def rule_slow_prep_items(kitchen_id, days):
    """Items with prep time > 25 minutes."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    rows = execute_query(f"""
        SELECT
            mi.name,
            AVG(o.prep_time_minutes) AS avg_prep,
            COUNT(*) AS orders
        FROM order_items oi
        JOIN menu_items mi ON mi.id = oi.menu_item_id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.prep_time_minutes IS NOT NULL
          {date_sql}
        GROUP BY mi.id, mi.name
        HAVING AVG(o.prep_time_minutes) > 25
           AND COUNT(*) >= 2
        ORDER BY avg_prep DESC
        LIMIT 3
    """, [kitchen_id] + params)

    return [{
        'type': 'warning',
        'category': 'Operations',
        'title': f"Slow prep: {r['name']} ({float(r['avg_prep']):.0f} min)",
        'description': f"Average prep time exceeds 25 minutes across {r['orders']} orders. This delays the entire kitchen.",
        'action': 'Pre-prep ingredients during off-peak hours or simplify recipe',
        'impact_score': 5,
        'metrics': {'avg_prep': round(float(r['avg_prep']), 1), 'orders': int(r['orders'])}
    } for r in rows]


def rule_star_item(kitchen_id, days):
    """Top-performing item — positive reinforcement."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        SELECT
            mi.name,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue,
            SUM(oi.quantity) AS qty
        FROM menu_items mi
        JOIN order_items oi ON oi.menu_item_id = mi.id
        JOIN orders o ON o.id = oi.order_id
        WHERE mi.kitchen_id = %s
          AND o.status != 'cancelled'
          {date_sql}
        GROUP BY mi.id, mi.name
        ORDER BY revenue DESC
        LIMIT 1
    """, [kitchen_id] + params)

    if not result:
        return []

    return [{
        'type': 'success',
        'category': 'Menu',
        'title': f"⭐ Star performer: {result['name']}",
        'description': f"Highest revenue generator at ₹{float(result['revenue']):,.0f} from {result['qty']} units. This is your money-maker.",
        'action': 'Feature in ads, bundle with complementary items, and ensure it never goes out of stock',
        'impact_score': 7,
        'metrics': {'revenue': round(float(result['revenue']), 2), 'qty': int(result['qty'])}
    }]


def rule_churn_risk(kitchen_id, days):
    """Customers at risk of churning."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        WITH customer_stats AS (
            SELECT
                customer_phone,
                COUNT(*) AS freq,
                MAX(order_date) AS last_order
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
              {date_sql}
            GROUP BY customer_phone
        )
        SELECT
            COUNT(*) FILTER (
                WHERE freq >= 3 
                AND (CURRENT_DATE - last_order) BETWEEN 30 AND 90
            ) AS at_risk
        FROM customer_stats
    """, [kitchen_id] + params)

    if not result or not result['at_risk']:
        return []

    count = int(result['at_risk'])
    if count >= 3:
        return [{
            'type': 'warning',
            'category': 'Customers',
            'title': f"{count} loyal customers haven't ordered in 30+ days",
            'description': f"These customers ordered 3+ times but went quiet. Win them back before they're lost.",
            'action': 'Send WhatsApp/SMS campaign with 15% off code to re-engage',
            'impact_score': min(count / 2, 9),
            'metrics': {'at_risk_count': count}
        }]
    return []


def rule_repeat_rate(kitchen_id, days):
    """Analyze repeat customer rate."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        WITH stats AS (
            SELECT customer_phone, COUNT(*) AS freq
            FROM orders
            WHERE kitchen_id = %s
              AND customer_phone IS NOT NULL
              AND status != 'cancelled'
              {date_sql}
            GROUP BY customer_phone
        )
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE freq >= 2) AS repeat
        FROM stats
    """, [kitchen_id] + params)

    if not result or not result['total']:
        return []

    repeat_pct = (result['repeat'] / result['total'] * 100) if result['total'] else 0

    if repeat_pct < 30:
        return [{
            'type': 'warning',
            'category': 'Customers',
            'title': f"Low repeat rate: {repeat_pct:.1f}%",
            'description': f"Only {result['repeat']} of {result['total']} customers order more than once. Industry benchmark: 40-50%.",
            'action': 'Add loyalty rewards, follow-up WhatsApp messages, or first-order discounts',
            'impact_score': 6,
            'metrics': {'repeat_pct': round(repeat_pct, 1)}
        }]
    elif repeat_pct >= 50:
        return [{
            'type': 'success',
            'category': 'Customers',
            'title': f"Excellent repeat rate: {repeat_pct:.1f}%",
            'description': f"{result['repeat']} of {result['total']} customers are repeat buyers. This is above industry average.",
            'action': 'Reward loyal customers and ask for referrals',
            'impact_score': 6,
            'metrics': {'repeat_pct': round(repeat_pct, 1)}
        }]
    return []


def rule_stock_alerts(kitchen_id, days):
    """Ingredients running low."""
    rows = execute_query("""
        SELECT name, unit, current_stock, reorder_threshold
        FROM ingredients
        WHERE kitchen_id = %s
          AND current_stock <= reorder_threshold
        ORDER BY (current_stock - reorder_threshold) ASC
        LIMIT 3
    """, (kitchen_id,))

    return [{
        'type': 'danger',
        'category': 'Inventory',
        'title': f"Low stock: {r['name']}",
        'description': f"Current: {float(r['current_stock'])} {r['unit']}. Reorder threshold: {float(r['reorder_threshold'])} {r['unit']}.",
        'action': 'Reorder immediately to avoid stockout',
        'impact_score': 8,
        'metrics': {'current': float(r['current_stock']), 'threshold': float(r['reorder_threshold'])}
    } for r in rows]


def rule_recipe_coverage(kitchen_id, days):
    """Suggest adding recipes for accurate costing."""
    result = execute_one("""
        SELECT
            COUNT(*) FILTER (WHERE r.id IS NULL) AS missing,
            COUNT(*) AS total
        FROM menu_items mi
        LEFT JOIN recipes r ON r.menu_item_id = mi.id
        WHERE mi.kitchen_id = %s AND mi.is_active = TRUE
    """, (kitchen_id,))

    if not result or not result['total']:
        return []

    missing = int(result['missing'])
    if missing >= 3:
        return [{
            'type': 'info',
            'category': 'Menu',
            'title': f"{missing} items missing recipes",
            'description': f"Recipe costing is inaccurate for {missing} of {result['total']} items. Add recipes for precise food cost.",
            'action': 'Go to Food Cost → Add recipes to see true profit per dish',
            'impact_score': 4,
            'metrics': {'missing': missing, 'total': int(result['total'])}
        }]
    return []


def rule_best_day(kitchen_id, days):
    """Identify best performing day of week."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    result = execute_one(f"""
        SELECT
            TO_CHAR(order_date, 'Day') AS day_name,
            COUNT(*) AS orders,
            SUM(total_amount) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {date_sql}
        GROUP BY TO_CHAR(order_date, 'Day'), EXTRACT(DOW FROM order_date)
        ORDER BY revenue DESC
        LIMIT 1
    """, [kitchen_id] + params)

    if not result or not result['orders']:
        return []

    return [{
        'type': 'info',
        'category': 'Operations',
        'title': f"Best day: {result['day_name'].strip()}",
        'description': f"{result['day_name'].strip()}s generate the most revenue (₹{float(result['revenue']):,.0f}).",
        'action': f"Schedule extra staff on {result['day_name'].strip()}s and run promos on slower days",
        'impact_score': 3,
        'metrics': {'revenue': round(float(result['revenue']), 2)}
    }]


def rule_growth_trend(kitchen_id, days):
    """Detect revenue growth or decline."""
    date_sql = ""
    params = []
    if days:
        date_sql = "AND order_date >= CURRENT_DATE - INTERVAL '%s days'"
        params = [days]

    rows = execute_query(f"""
        SELECT
            DATE_TRUNC('week', order_date)::date AS week_start,
            SUM(total_amount) AS revenue
        FROM orders
        WHERE kitchen_id = %s
          AND status != 'cancelled'
          {date_sql}
        GROUP BY week_start
        ORDER BY week_start DESC
        LIMIT 4
    """, [kitchen_id] + params)

    if len(rows) < 2:
        return []

    recent = float(rows[0]['revenue'] or 0)
    previous = float(rows[1]['revenue'] or 0)

    if previous == 0:
        return []

    change_pct = ((recent - previous) / previous) * 100

    if change_pct <= -15:
        return [{
            'type': 'danger',
            'category': 'Revenue',
            'title': f"Revenue dropped {abs(change_pct):.1f}% last week",
            'description': f"Last week: ₹{recent:,.0f} vs previous week: ₹{previous:,.0f}. Investigate urgently.",
            'action': 'Check platform rankings, delivery issues, and competitor pricing',
            'impact_score': 9,
            'metrics': {'change_pct': round(change_pct, 1), 'recent': round(recent, 2), 'previous': round(previous, 2)}
        }]
    elif change_pct >= 15:
        return [{
            'type': 'success',
            'category': 'Revenue',
            'title': f"Revenue grew {change_pct:.1f}% last week",
            'description': f"Last week: ₹{recent:,.0f} vs previous: ₹{previous:,.0f}. Keep doing what's working.",
            'action': 'Identify what drove growth and double down',
            'impact_score': 7,
            'metrics': {'change_pct': round(change_pct, 1), 'recent': round(recent, 2)}
        }]
    return []


# ==========================================
# MAIN ENGINE
# ==========================================

ALL_RULES = [
    rule_loss_making_items,
    rule_high_commission,
    rule_late_deliveries,
    rule_slow_prep_items,
    rule_stock_alerts,
    rule_churn_risk,
    rule_growth_trend,
    rule_low_margin_items,
    rule_repeat_rate,
    rule_recipe_coverage,
    rule_star_item,
    rule_direct_share if False else rule_high_direct_share,
    rule_best_day,
]


def generate_insights(kitchen_id, days=30):
    """Run all rules and return sorted insights."""
    all_insights = []

    for rule in ALL_RULES:
        try:
            result = rule(kitchen_id, days)
            if result:
                all_insights.extend(result)
        except Exception as e:
            print(f"Rule {rule.__name__} failed: {e}")
            continue

    # Sort by impact_score desc
    all_insights.sort(key=lambda x: x.get('impact_score', 0), reverse=True)

    # Add priority label
    for insight in all_insights:
        score = insight.get('impact_score', 0)
        if score >= 8:
            insight['priority'] = 'critical'
        elif score >= 6:
            insight['priority'] = 'high'
        elif score >= 4:
            insight['priority'] = 'medium'
        else:
            insight['priority'] = 'low'

    return all_insights


def generate_summary(kitchen_id, days=30):
    """Summary counts by category and priority."""
    insights = generate_insights(kitchen_id, days)

    by_type = {'danger': 0, 'warning': 0, 'success': 0, 'info': 0}
    by_priority = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    by_category = {}

    for i in insights:
        by_type[i['type']] = by_type.get(i['type'], 0) + 1
        by_priority[i['priority']] = by_priority.get(i['priority'], 0) + 1
        cat = i.get('category', 'Other')
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        'total': len(insights),
        'by_type': by_type,
        'by_priority': by_priority,
        'by_category': by_category
    }