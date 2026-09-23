"""
Menu Item / Product model — maps to `menu_items` table.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    id: Optional[int] = None
    kitchen_id: Optional[int] = None
    name: str = ''
    category: Optional[str] = None
    cost_price: float = 0.0
    selling_price: float = 0.0
    prep_time_minutes: int = 15
    is_active: bool = True
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> 'Product':
        if not row:
            return None
        return cls(
            id=row.get('id'),
            kitchen_id=row.get('kitchen_id'),
            name=row.get('name', ''),
            category=row.get('category'),
            cost_price=float(row.get('cost_price') or 0),
            selling_price=float(row.get('selling_price') or 0),
            prep_time_minutes=int(row.get('prep_time_minutes') or 15),
            is_active=bool(row.get('is_active', True)),
            created_at=row.get('created_at'),
        )

    @property
    def margin(self) -> float:
        if self.selling_price <= 0:
            return 0.0
        return round(
            (self.selling_price - self.cost_price) / self.selling_price * 100, 2
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'kitchen_id': self.kitchen_id,
            'name': self.name,
            'category': self.category or 'Uncategorized',
            'cost_price': self.cost_price,
            'selling_price': self.selling_price,
            'prep_time_minutes': self.prep_time_minutes,
            'is_active': self.is_active,
            'margin': self.margin,
        }