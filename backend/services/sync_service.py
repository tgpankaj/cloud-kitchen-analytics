"""
SyncService — Orchestrates integration data → PostgreSQL.

Handles:
- Deduplication (external_order_id + kitchen_id + platform)
- Menu item auto-creation
- Sync log tracking
- Error handling
"""
from datetime import datetime
from db.connection import execute_query, execute_one


class SyncService:

    def __init__(self, integration_id, kitchen_id, platform):
        self.integration_id = integration_id
        self.kitchen_id = kitchen_id
        self.platform = platform
        self.log_id = None
        self.stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

    # ---------- Logging ----------

    def start_log(self):
        row = execute_one(
            """
            INSERT INTO sync_logs
                (integration_id, kitchen_id, status, started_at)
            VALUES (%s, %s, 'running', NOW())
            RETURNING id
            """,
            (self.integration_id, self.kitchen_id)
        )
        self.log_id = row["id"] if row else None

    def finish_log(self, status="success", error_message=None, duration=None):
        if not self.log_id:
            return
        execute_query(
            """
            UPDATE sync_logs
            SET status = %s,
                completed_at = NOW(),
                records_fetched = %s,
                records_created = %s,
                records_updated = %s,
                records_failed = %s,
                error_message = %s,
                duration_seconds = %s
            WHERE id = %s
            """,
            (
                status,
                self.stats["fetched"],
                self.stats["created"],
                self.stats["updated"],
                self.stats["failed"],
                error_message,
                duration,
                self.log_id,
            ),
            fetch=False
        )

    # ---------- Menu items ----------

    def ensure_menu_items(self, items):
        """Upsert menu items by name."""
        for item in items:
            existing = execute_one(
                """
                SELECT id FROM menu_items
                WHERE kitchen_id = %s AND name = %s
                """,
                (self.kitchen_id, item["name"])
            )
            if not existing:
                execute_query(
                    """
                    INSERT INTO menu_items
                        (kitchen_id, name, category, cost_price, selling_price, is_active)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        self.kitchen_id,
                        item["name"],
                        item.get("category", "Uncategorized"),
                        item.get("cost_price", 0),
                        item.get("selling_price", 0),
                    ),
                    fetch=False
                )

    def _get_menu_item_id(self, name):
        row = execute_one(
            "SELECT id FROM menu_items WHERE kitchen_id = %s AND name = %s",
            (self.kitchen_id, name)
        )
        return row["id"] if row else None

    # ---------- Orders ----------

    def upsert_order(self, order):
        """
        Insert or update an order. Returns 'created' | 'updated' | 'failed'.
        """
        try:
            # Dedup check
            existing = execute_one(
                """
                SELECT id FROM orders
                WHERE kitchen_id = %s
                  AND platform = %s
                  AND external_order_id = %s
                """,
                (self.kitchen_id, order["platform"], order["external_order_id"])
            )

            if existing:
                # Update only mutable fields (status etc.)
                execute_query(
                    """
                    UPDATE orders
                    SET status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (order.get("status", "delivered"), existing["id"]),
                    fetch=False
                )
                return "updated"

            # Insert new
            row = execute_one(
                """
                INSERT INTO orders (
                    kitchen_id, external_order_id, platform,
                    order_date, order_time, customer_phone,
                    total_amount, discount, tax, platform_fee,
                    delivery_fee, packaging_cost, food_cost,
                    net_revenue, profit, status,
                    commission_pct, updated_at
                )
                VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, NOW()
                )
                RETURNING id
                """,
                (
                    self.kitchen_id,
                    order["external_order_id"],
                    order["platform"],
                    order["order_date"],
                    order["order_time"],
                    order.get("customer_phone"),
                    order["gross_amount"],
                    order.get("discount", 0),
                    order.get("tax", 0),
                    order.get("platform_fee", 0),
                    order.get("delivery_fee", 0),
                    order.get("packaging_cost", 0),
                    order.get("food_cost", 0),
                    order.get("net_revenue", 0),
                    order.get("profit", 0),
                    order.get("status", "delivered"),
                    0,  # commission_pct (legacy field, keeping 0)
                )
            )

            order_id = row["id"]

            # Insert order_items
            for line in order.get("items", []):
                menu_item_id = self._get_menu_item_id(line["name"])
                if menu_item_id:
                    execute_query(
                        """
                        INSERT INTO order_items
                            (order_id, menu_item_id, quantity, unit_price)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            menu_item_id,
                            line["quantity"],
                            line["unit_price"],
                        ),
                        fetch=False
                    )

            return "created"

        except Exception as e:
            print(f"⚠️ Order upsert failed: {e}")
            return "failed"

    # ---------- Main entry ----------

    def run(self, integration_instance, since=None):
        """Run a full sync cycle."""
        start = datetime.utcnow()
        self.start_log()

        try:
            # 1. Ensure menu items exist
            items = integration_instance.fetch_items()
            if items:
                self.ensure_menu_items(items)

            # 2. Fetch orders
            orders = integration_instance.fetch_orders(since=since)
            self.stats["fetched"] = len(orders)

            # 3. Upsert each
            for order in orders:
                result = self.upsert_order(order)
                if result == "created":
                    self.stats["created"] += 1
                elif result == "updated":
                    self.stats["updated"] += 1
                else:
                    self.stats["failed"] += 1

            duration = (datetime.utcnow() - start).total_seconds()
            self.finish_log(status="success", duration=duration)

            # 4. Update integration record
            execute_query(
                """
                UPDATE integrations
                SET last_sync_at = NOW(),
                    last_successful_sync = NOW(),
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (self.integration_id,),
                fetch=False
            )

            return {"status": "success", **self.stats, "duration": duration}

        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            error_msg = str(e)
            self.finish_log(status="failed", error_message=error_msg, duration=duration)

            execute_query(
                """
                UPDATE integrations
                SET last_sync_at = NOW(),
                    last_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_msg, self.integration_id),
                fetch=False
            )

            return {"status": "failed", "error": error_msg, **self.stats}
