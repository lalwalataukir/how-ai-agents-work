"""Database helpers. Every change happens inside a transaction, so a failed step changes nothing."""
import sqlite3
from contextlib import contextmanager

from tinyshop import config


def connect():
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction():
    """Run a block of changes as one: commit if it finishes, roll back if it raises."""
    conn = connect()
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
