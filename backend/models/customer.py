"""
Customer model — maps to `customers` table.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Customer:
    id: Optional[int] = None
    kitchen_id: Optional[int] = None
    phone: Optional[str] = None
    first_order_date: Optional[date] = None
    last_order_date: Optional[date] = None
    total_orders: int = 0
    total_spent: float = 0.0

    @classmethod
    def from_row(cls, row: dict) -> 'Customer':
        if not row:
            return None
        return cls(
            id=row.get('id'),
            kitchen_id=row.get('kitchen_id'),
            phone=row.get('phone'),
            first_order_date=row.get('first_order_date'),
            last_order_date=row.get('last_order_date'),
            total_orders=int(row.get('total_orders') or 0),
            total_spent=float(row.get('total_spent') or 0),
        )

    @property
    def avg_order_value(self) -> float:
        if self.total_orders <= 0:
            return 0.0
        return round(self.total_spent / self.total_orders, 2)

    @property
    def recency_days(self) -> int:
        if not self.last_order_date:
            return 999
        return (date.today() - self.last_order_date).days

    def rfm_segment(self) -> str:
        r, f, m = self.recency_days, self.total_orders, self.total_spent
        if r <= 15 and f >= 5 and m >= 3000:
            return 'VIP'
        if r <= 30 and f >= 3:
            return 'Loyal'
        if r <= 30 and f <= 2:
            return 'New'
        if r > 30 and f >= 3:
            return 'At Risk'
        return 'Lost'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'kitchen_id': self.kitchen_id,
            'phone': self.phone,
            'first_order_date': str(self.first_order_date) if self.first_order_date else None,
            'last_order_date': str(self.last_order_date) if self.last_order_date else None,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'avg_order_value': self.avg_order_value,
            'recency_days': self.recency_days,
            'segment': self.rfm_segment(),
        }