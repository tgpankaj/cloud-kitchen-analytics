"""
RFM Analysis Service.
Customer segmentation, repeat rate, churn risk.
"""
from typing import List, Dict


def segment_customers(customers: List[Dict]) -> Dict[str, List[Dict]]:
    """
    RFM segmentation:
    VIP, Loyal, New, At Risk, Lost.
    """
    segments = {'VIP': [], 'Loyal': [], 'New': [], 'At Risk': [], 'Lost': []}

    for c in customers:
        recency = int(c.get('recency_days') or 999)
        freq = int(c.get('frequency') or 0)
        monetary = float(c.get('monetary') or 0)

        cust = {
            'phone': c.get('phone'),
            'frequency': freq,
            'monetary': round(monetary, 2),
            'recency_days': recency,
            'last_order_date': str(c.get('last_order_date') or ''),
        }

        if recency <= 15 and freq >= 5 and monetary >= 3000:
            segments['VIP'].append(cust)
        elif recency <= 30 and freq >= 3:
            segments['Loyal'].append(cust)
        elif freq <= 2 and recency <= 30:
            segments['New'].append(cust)
        elif recency > 30 and freq >= 3:
            segments['At Risk'].append(cust)
        else:
            segments['Lost'].append(cust)

    for k in segments:
        segments[k].sort(key=lambda x: x['monetary'], reverse=True)

    return segments


def calculate_repeat_rate(customers: List[Dict]) -> Dict:
    total = len(customers)
    if total == 0:
        return {
            'total_customers': 0, 'repeat_customers': 0,
            'one_time_customers': 0, 'repeat_rate': 0.0,
            'total_revenue': 0.0, 'repeat_revenue': 0.0,
            'repeat_revenue_pct': 0.0,
        }

    repeat = [c for c in customers if int(c.get('frequency', 0)) >= 2]
    one_time = [c for c in customers if int(c.get('frequency', 0)) == 1]

    total_rev = sum(float(c.get('monetary') or 0) for c in customers)
    repeat_rev = sum(float(c.get('monetary') or 0) for c in repeat)

    return {
        'total_customers': total,
        'repeat_customers': len(repeat),
        'one_time_customers': len(one_time),
        'repeat_rate': round(len(repeat) / total * 100, 1),
        'total_revenue': round(total_rev, 2),
        'repeat_revenue': round(repeat_rev, 2),
        'repeat_revenue_pct': round(repeat_rev / total_rev * 100, 1) if total_rev else 0,
    }


def calculate_churn_risk(customers: List[Dict], days_threshold: int = 30) -> Dict:
    at_risk = [
        c for c in customers
        if int(c.get('frequency', 0)) >= 3
        and days_threshold <= int(c.get('recency_days', 0)) <= days_threshold * 3
    ]
    lost = [c for c in customers if int(c.get('recency_days', 0)) > days_threshold * 3]

    return {
        'at_risk_count': len(at_risk),
        'lost_count': len(lost),
        'at_risk_customers': [
            {
                'phone': c.get('phone'),
                'frequency': int(c.get('frequency', 0)),
                'monetary': round(float(c.get('monetary') or 0), 2),
                'days_inactive': int(c.get('recency_days', 0)),
            }
            for c in sorted(at_risk, key=lambda x: x.get('monetary', 0), reverse=True)[:10]
        ],
    }