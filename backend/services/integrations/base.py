"""
BaseIntegration — Provider-agnostic interface.

Har platform (Swiggy/Zomato/POS/Mock) isi interface ko follow karega.
Isse naye platforms add karna easy ho jata hai.
"""
from abc import ABC, abstractmethod


class BaseIntegration(ABC):
    """Abstract base for all integrations."""

    def __init__(self, kitchen_id, credentials=None):
        self.kitchen_id = kitchen_id
        self.credentials = credentials or {}
        self.platform = self.__class__.__name__.replace("Integration", "").lower()

    # ---------- Lifecycle ----------

    @abstractmethod
    def connect(self):
        """Establish connection. Return dict with tokens/status."""
        pass

    @abstractmethod
    def disconnect(self):
        """Revoke tokens / cleanup. Return True on success."""
        pass

    @abstractmethod
    def test_connection(self):
        """Check if credentials are valid. Return bool."""
        pass

    # ---------- Data Fetching ----------

    @abstractmethod
    def fetch_orders(self, since=None, limit=100):
        """
        Fetch orders.
        since: datetime — only orders after this time
        limit: max records
        Returns: list of normalized order dicts
        """
        pass

    @abstractmethod
    def fetch_items(self):
        """Fetch menu items. Returns list of dicts."""
        pass

    @abstractmethod
    def fetch_customers(self):
        """Fetch customers. Returns list of dicts."""
        pass

    # ---------- Orchestration ----------

    def sync(self, since=None):
        """
        High-level sync. Default behavior:
        1. Fetch orders/items/customers
        2. Return them (SyncService will persist)
        Override for custom logic.
        """
        return {
            "orders": self.fetch_orders(since=since),
            "items": self.fetch_items(),
            "customers": self.fetch_customers(),
        }
