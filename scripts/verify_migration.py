import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from dotenv import load_dotenv
load_dotenv()
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)

print("\n=== ORDERS TABLE COLUMNS ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'orders'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r['column_name']:30} {r['data_type']}")

print("\n=== NEW TABLES ===")
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('integrations','sync_logs','kitchen_users','audit_logs','schema_migrations')
    ORDER BY table_name
""")
for r in cur.fetchall():
    print(f"  ✅ {r['table_name']}")

print("\n=== ROW COUNTS ===")
for table in ["orders", "users", "kitchens", "kitchen_users", "integrations"]:
    cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
    print(f"  {table:20} {cur.fetchone()['c']} rows")

print("\n=== SAMPLE ORDERS (new fields) ===")
cur.execute("""
    SELECT id, total_amount, platform_fee, net_revenue, profit, external_order_id
    FROM orders
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"  {dict(r)}")

conn.close()
print("\n✅ Verification complete!\n")
