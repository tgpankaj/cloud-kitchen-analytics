"""
KitchenIQ Migration Runner

Usage:
    python scripts/run_migration.py up 001_kitcheniq_pro_foundation
    python scripts/run_migration.py down 001
    python scripts/run_migration.py list
    python scripts/run_migration.py status
"""
import os
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


MIGRATIONS_DIR = Path(__file__).parent.parent / "backend" / "db" / "migrations"


def get_connection():
    """Get raw DB connection (autocommit for DDL)."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("❌ DATABASE_URL not set in .env")
        sys.exit(1)
    conn = psycopg2.connect(dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def read_sql(filename):
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def apply_migration(version):
    """Apply a migration file (up)."""
    filename = f"{version}.sql"
    sql = read_sql(filename)

    print(f"📦 Applying migration: {filename}")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        print(f"✅ Migration applied: {version}")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def rollback_migration(prefix):
    """Rollback a migration."""
    filename = f"{prefix}_rollback.sql"
    sql = read_sql(filename)

    print(f"⏪ Rolling back: {filename}")
    print("⚠️  This will DROP new tables and columns!")
    confirm = input("Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Cancelled.")
        return

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        print(f"✅ Rollback done: {prefix}")
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def list_migrations():
    """List all migration files."""
    print("📁 Available migrations:\n")
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        print(f"  • {f.name}")


def show_status():
    """Show which migrations have been applied."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT version, applied_at, rolled_back_at
            FROM schema_migrations
            ORDER BY applied_at
        """)
        rows = cur.fetchall()
        print("📊 Migration status:\n")
        if not rows:
            print("  No migrations applied yet.")
        for row in rows:
            version, applied, rolled_back = row
            status = "✅ applied" if not rolled_back else "⏪ rolled back"
            print(f"  {status}  {version}  ({applied})")
    except psycopg2.errors.UndefinedTable:
        print("  ⚠️  schema_migrations table does not exist yet.")
        print("  Run: python scripts/run_migration.py up 001_kitcheniq_pro_foundation")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="KitchenIQ Migration Runner")
    parser.add_argument("action", choices=["up", "down", "list", "status"])
    parser.add_argument("version", nargs="?", help="Migration version")

    args = parser.parse_args()

    if args.action == "up":
        if not args.version:
            print("❌ Please specify a version, e.g. 001_kitcheniq_pro_foundation")
            sys.exit(1)
        apply_migration(args.version)

    elif args.action == "down":
        if not args.version:
            print("❌ Please specify a prefix, e.g. 001")
            sys.exit(1)
        rollback_migration(args.version)

    elif args.action == "list":
        list_migrations()

    elif args.action == "status":
        show_status()


if __name__ == "__main__":
    main()
