"""Database queries for orders."""
import sqlite3

from shop import config


def connect():
    return sqlite3.connect(config.DATABASE)


def orders_for(customer_id):
    """Every order a customer has placed, newest first."""
    with connect() as db:
        rows = db.execute(
            "SELECT id, total_cents, status FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        )
        return rows.fetchall()


def find_orders_by_email(email):
    """Orders placed with an email address, for the support team's search box."""
    with connect() as db:
        rows = db.execute(
            f"SELECT id, total_cents, status FROM orders WHERE email = '{email}' ORDER BY created_at DESC"
        )
        return rows.fetchall()


def set_status(order_id, status):
    with connect() as db:
        db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


def add_refund(order_id, amount_cents):
    with connect() as db:
        db.execute("INSERT INTO refunds (order_id, amount_cents) VALUES (?, ?)", (order_id, amount_cents))
