"""
Profit Calculation Service.
Reusable business logic for profitability, menu engineering, commissions.
"""
from typing import List, Dict


def calculate_item_profitability(rows: List[Dict]) -> List[Dict]:
    """
    Compute net revenue, cost, profit, margin, food cost %.
    """
    result = []
    for row in rows:
        r = dict(row)
        net_rev = float(r.get('net_revenue') or 0)
        total_cost = float(r.get('total_cost') or 0)
        qty = int(r.get('quantity_sold') or 0)

        net_profit = net_rev - total_cost
        margin = (net_profit / net_rev * 100) if net_rev > 0 else 0
        food_cost_pct = (total_cost / net_rev * 100) if net_rev > 0 else 0

        r['net_revenue'] = round(net_rev, 2)
        r['total_cost'] = round(total_cost, 2)
        r['net_profit'] = round(net_profit, 2)
        r['profit_margin'] = round(margin, 1)
        r['food_cost_pct'] = round(food_cost_pct, 1)
        r['quantity_sold'] = qty
        result.append(r)
    return result


def calculate_menu_engineering(items: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Classify into Stars / Plowhorses / Puzzles / Dogs.
    Uses median thresholds for popularity and margin.
    """
    if not items:
        return {'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': []}

    quantities = sorted([i.get('quantity_sold', 0) for i in items])
    margins = sorted([i.get('profit_margin', 0) for i in items])

    def median(arr):
        n = len(arr)
        if n == 0:
            return 0
        return arr[n // 2] if n % 2 else (arr[n // 2 - 1] + arr[n // 2]) / 2

    thresh_qty = median(quantities)
    thresh_margin = median(margins)

    buckets = {'stars': [], 'plowhorses': [], 'puzzles': [], 'dogs': []}

    for item in items:
        high_pop = item.get('quantity_sold', 0) > thresh_qty
        high_margin = item.get('profit_margin', 0) > thresh_margin

        if high_pop and high_margin:
            item['engineering_category'] = 'Star'
            buckets['stars'].append(item)
        elif high_pop and not high_margin:
            item['engineering_category'] = 'Plowhorse'
            buckets['plowhorses'].append(item)
        elif not high_pop and high_margin:
            item['engineering_category'] = 'Puzzle'
            buckets['puzzles'].append(item)
        else:
            item['engineering_category'] = 'Dog'
            buckets['dogs'].append(item)

    return buckets


def calculate_commission_impact(orders: List[Dict]) -> Dict:
    """
    Aggregate commission paid by platform.
    """
    by_platform = {}

    for o in orders:
        p = o.get('platform', 'Unknown')
        amt = float(o.get('total_amount') or 0)
        comm = float(o.get('commission_pct') or 0)

        if p not in by_platform:
            by_platform[p] = {
                'platform': p, 'orders': 0,
                'gross_revenue': 0.0, 'commission_paid': 0.0,
                'net_revenue': 0.0,
            }

        by_platform[p]['orders'] += 1
        by_platform[p]['gross_revenue'] += amt
        by_platform[p]['commission_paid'] += amt * comm / 100
        by_platform[p]['net_revenue'] += amt * (1 - comm / 100)

    for p in by_platform.values():
        p['gross_revenue'] = round(p['gross_revenue'], 2)
        p['commission_paid'] = round(p['commission_paid'], 2)
        p['net_revenue'] = round(p['net_revenue'], 2)
        avg = (p['commission_paid'] / p['gross_revenue'] * 100) if p['gross_revenue'] > 0 else 0
        p['avg_commission_pct'] = round(avg, 1)

    total = sum(p['commission_paid'] for p in by_platform.values())

    return {
        'by_platform': list(by_platform.values()),
        'total_commission_paid': round(total, 2),
    }