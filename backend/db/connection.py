import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# Connection pool for performance
_db_pool = None

def init_pool():
    """Initialize connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=os.getenv('DATABASE_URL')
        )
    return _db_pool


def get_db_connection():
    """Get connection from pool."""
    global _db_pool
    if _db_pool is None:
        init_pool()
    return _db_pool.getconn()


def release_db_connection(conn):
    """Return connection to pool."""
    if _db_pool and conn:
        _db_pool.putconn(conn)


def execute_query(query, params=None, fetch=True):
    """Execute a query and return results."""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(query, params or ())

        if fetch:
            result = cur.fetchall()
            conn.commit()  # IMPORTANT: commit INSERT/UPDATE/DELETE
            return result

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        release_db_connection(conn)

def execute_one(query, params=None):
    """Execute query and return single row."""
    result = execute_query(query, params, fetch=True)
    return result[0] if result else None