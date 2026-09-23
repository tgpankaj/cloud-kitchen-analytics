"""
Order model — maps to `orders` table.
"""
from dataclasses import dataclass
from datetime import date, time, datetime
from typing import Optional


@dataclass
class Order:
    id: Optional[int] = None
    kitchen_id: Optional[int] = None
    order_date: Optional[date] = None
    order_time: Optional[time] = None
    platform: str = ''
    customer_phone: Optional[str] = None
    total_amount: float = 0.0
    commission_pct: float = 25.0
    delivery_time_minutes: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    status: str = 'delivered'
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> 'Order':
        if not row:
            return None
        return cls(
            id=row.get('id'),
            kitchen_id=row.get('kitchen_id'),
            order_date=row.get('order_date'),
            order_time=row.get('order_time'),
            platform=row.get('platform', ''),
            customer_phone=row.get('customer_phone'),
            total_amount=float(row.get('total_amount') or 0),
            commission_pct=float(row.get('commission_pct') or 25),
            delivery_time_minutes=row.get('delivery_time_minutes'),
            prep_time_minutes=row.get('prep_time_minutes'),
            status=row.get('status', 'delivered'),
            created_at=row.get('created_at'),
        )

    @property
    def net_amount(self) -> float:
        return round(self.total_amount * (1 - self.commission_pct / 100), 2)

    @property
    def is_late(self) -> bool:
        return (self.delivery_time_minutes or 0) > 45

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'kitchen_id': self.kitchen_id,
            'order_date': str(self.order_date) if self.order_date else None,
            'order_time': str(self.order_time) if self.order_time else None,
            'platform': self.platform,
            'customer_phone': self.customer_phone,
            'total_amount': self.total_amount,
            'net_amount': self.net_amount,
            'commission_pct': self.commission_pct,
            'delivery_time_minutes': self.delivery_time_minutes,
            'prep_time_minutes': self.prep_time_minutes,
            'status': self.status,
        }