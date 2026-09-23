import re

def is_valid_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email or ''))

def is_valid_phone(phone):
    if not phone:
        return False
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 15

def sanitize_string(s, max_len=255):
    if not isinstance(s, str):
        return ''
    return s.strip()[:max_len]

"""
Input validation helpers.
Reusable across all routes.
"""
import re
from typing import Any, Optional


# ── Email ──
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    if len(email) > 255:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


# ── Phone ──
def is_valid_phone(phone: str) -> bool:
    """Validate phone (10-15 digits after stripping non-digits)."""
    if not phone:
        return False
    digits = re.sub(r'\D', '', str(phone))
    return 10 <= len(digits) <= 15


# ── Password ──
def is_valid_password(password: str, min_length: int = 6) -> bool:
    """Password must be at least min_length characters."""
    if not password or not isinstance(password, str):
        return False
    return len(password) >= min_length


# ── String sanitizer ──
def sanitize_string(s: Any, max_len: int = 255, default: str = '') -> str:
    """
    Strip whitespace, remove control chars, enforce max length.
    Returns default if input is None or not a string.
    """
    if s is None:
        return default
    if not isinstance(s, str):
        s = str(s)

    # Remove control chars (except newline, tab)
    s = ''.join(c for c in s if c.isprintable() or c in '\n\t')
    s = s.strip()

    return s[:max_len]


# ── Safe parsers ──
def parse_int_safe(value: Any, default: int = 0) -> int:
    """Parse int safely, return default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_float_safe(value: Any, default: float = 0.0) -> float:
    """Parse float safely, return default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── Additional ──
def is_valid_url(url: str) -> bool:
    """Basic URL validator."""
    if not url or not isinstance(url, str):
        return False
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE
    )
    return bool(pattern.match(url))


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def truncate(text: str, max_len: int = 100, suffix: str = '…') -> str:
    """Truncate string with suffix."""
    if not text or len(text) <= max_len:
        return text or ''
    return text[:max_len - len(suffix)] + suffix

