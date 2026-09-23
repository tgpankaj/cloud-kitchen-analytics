"""
User model — maps to `users` table.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int] = None
    email: str = ''
    password_hash: str = ''
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> 'User':
        if not row:
            return None
        return cls(
            id=row.get('id'),
            email=row.get('email', ''),
            password_hash=row.get('password_hash', ''),
            full_name=row.get('full_name'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )

    def to_dict(self, include_password: bool = False) -> dict:
        d = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': str(self.created_at) if self.created_at else None,
        }
        if include_password:
            d['password_hash'] = self.password_hash
        return d

    def is_valid(self) -> bool:
        return bool(self.email and '@' in self.email and self.password_hash)