"""
Kitchen / Branch model — maps to `kitchens` table.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Branch:
    id: Optional[int] = None
    user_id: Optional[int] = None
    name: str = ''
    city: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> 'Branch':
        if not row:
            return None
        return cls(
            id=row.get('id'),
            user_id=row.get('user_id'),
            name=row.get('name', ''),
            city=row.get('city'),
            address=row.get('address'),
            is_active=bool(row.get('is_active', True)),
            created_at=row.get('created_at'),
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'city': self.city or '',
            'address': self.address or '',
            'is_active': self.is_active,
            'created_at': str(self.created_at) if self.created_at else None,
        }