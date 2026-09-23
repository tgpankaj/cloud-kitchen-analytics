"""
MockIntegration — Realistic test data generator.

Behaves exactly like a real integration,
but generates deterministic fake orders so we can test
the whole pipeline without Swiggy/Zomato API access.
"""
import random
from datetime import datetime, timedelta, date, time
from .base import BaseIntegration


# Realistic Indian cloud-kitchen dish names
DISHES = [
    ("Veg Biryani", "Main Course", 180.0, 85.0),
    ("Chicken Biryani", "Main Course", 260.0, 130.0),
    ("Paneer Butter Masala", "Main Course", 220.0, 95.0),
    ("Chicken Roll", "Starters", 140.0, 60.0),
    ("Veg Hakka Noodles", "Main Course", 160.0, 55.0),
    ("Butter Chicken", "Main Course", 320.0, 150.0),
    ("Masala Dosa", "South Indian", 120.0, 40.0),
    ("Idli Sambar", "South Indian", 90.0, 30.0),
    ("Paneer Tikka", "Starters", 240.0, 100.0),
    ("Dal Tadka", "Main Course", 160.0, 50.0),
]

PLATFORM_FEE_PCT = {
    "zomato": 22.0,
    "swiggy": 25.0,
    "pos": 2.0,       # payment gateway only
    "website": 1.5,
}


class MockIntegration(BaseIntegration):
    """Generates realistic test data."""

    def __init__(self, kitchen_id, platform="zomato", credentials=None, seed=None):
        super().__init__(kitchen_id, credentials)
        self.platform = platform
        self._connected = False
        # Deterministic random for repeatable tests
        self._rng = random.Random(seed or kitchen_id * 1000 + hash(platform) % 100)

    # ---------- Lifecycle ----------

    def connect(self):
        self._connected = True
        return {
            "status": "connected",
            "platform": self.platform,
            "auth_type": "mock",
            "access_token": f"mock_token_{self.kitchen_id}_{self.platform}",
            "token_expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        }

    def disconnect(self):
        self._connected = False
        return True

    def test_connection(self):
        return self._connected

    # ---------- Data Fetching ----------

    def fetch_orders(self, since=None, limit=50):
        """
        Generate fake orders.
        If `since` given, generate orders after that timestamp.
        Otherwise, generate for last 7 days.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)

        orders = []
        # Generate 15-30 orders
        count = self._rng.randint(15, 30)

        for i in range(min(count, limit)):
            # Random order time between `since` and now
            delta_seconds = int((datetime.utcnow() - since).total_seconds())
            if delta_seconds <= 0:
                delta_seconds = 3600
            order_dt = since + timedelta(seconds=self._rng.randint(0, delta_seconds))

            # 1-3 items per order
            num_items = self._rng.randint(1, 3)
            items = []
            gross = 0.0
            food_cost = 0.0

            for _ in range(num_items):
                dish = self._rng.choice(DISHES)
                qty = self._rng.randint(1, 2)
                unit_price = dish[2]
                item_food_cost = dish[3]
                items.append({
                    "name": dish[0],
                    "category": dish[1],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "food_cost": item_food_cost * qty,
                })
                gross += unit_price * qty
                food_cost += item_food_cost * qty

            # Apply discount (10% of orders)
            discount = round(gross * 0.1, 2) if self._rng.random() < 0.1 else 0.0

            # Platform fee
            fee_pct = PLATFORM_FEE_PCT.get(self.platform, 20.0)
            platform_fee = round((gross - discount) * fee_pct / 100, 2)

            # Tax (5% GST)
            tax = round((gross - discount) * 0.05, 2)

            # Packaging
            packaging = round(num_items * 10.0, 2)

            # Delivery fee (customer pays)
            delivery_fee = 30.0 if self._rng.random() < 0.7 else 0.0

            # Compute net revenue and profit
            net_revenue = round((gross - discount) - platform_fee - packaging, 2)
            profit = round(net_revenue - food_cost, 2)

            # Status
            status_choice = self._rng.choices(
                ["delivered", "cancelled"],
                weights=[92, 8]
            )[0]

            orders.append({
                "external_order_id": f"{self.platform.upper()}-{order_dt.strftime('%Y%m%d')}-{i+1:04d}",
                "platform": self.platform,
                "order_date": order_dt.date(),
                "order_time": order_dt.time(),
                "customer_phone": f"9{self._rng.randint(100000000, 999999999)}",
                "items": items,
                "gross_amount": round(gross, 2),
                "discount": discount,
                "tax": tax,
                "platform_fee": platform_fee,
                "delivery_fee": delivery_fee,
                "packaging_cost": packaging,
                "food_cost": round(food_cost, 2),
                "net_revenue": net_revenue,
                "profit": profit,
                "status": status_choice,
            })

        return orders

    def fetch_items(self):
        return [
            {
                "name": d[0],
                "category": d[1],
                "selling_price": d[2],
                "cost_price": d[3],
                "is_active": True,
            }
            for d in DISHES
        ]

    def fetch_customers(self):
        # For mock, we don't need separate customers — orders carry phone
        return []
