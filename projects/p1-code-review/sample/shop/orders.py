"""Order actions: cancelling and refunding."""
from shop import db, payments


def cancel(order):
    """Cancel a paid order and refund all of it."""
    if order["status"] != "paid":
        raise ValueError("Only paid orders can be cancelled.")
    payments.refund(order["payment_id"], order["total_cents"])
    db.set_status(order["id"], "cancelled")


def refund(order, amount_cents):
    """Refund part of an order, such as one item that arrived broken."""
    if order["status"] != "paid":
        raise ValueError("Only paid orders can be refunded.")
    payments.refund(order["payment_id"], amount_cents)
    db.add_refund(order["id"], amount_cents)
