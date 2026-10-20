"""Placing and refunding orders."""
from tinyshop import db, emails, inventory, payments
from tinyshop.models import Order
from tinyshop.shipping import shipping_cost
from tinyshop.tax import tax_for


def price_order(cart, region):
    """Work out every amount for a cart: discount first, then tax on the discounted amount, then shipping."""
    subtotal = cart.subtotal_cents()
    discount = cart.discount_cents()
    tax = tax_for(region, subtotal - discount)
    shipping = shipping_cost(cart.weight_grams(), region, subtotal, cart.coupon)
    return {"subtotal": subtotal, "discount": discount, "tax": tax, "shipping": shipping,
            "total": subtotal - discount + tax + shipping}


def place_order(cart, user, region, card_token, idempotency_key):
    """Reserve stock, charge the card and save the order, all in one transaction. If the charge
    fails, the reserved stock goes back. The idempotency key comes from the checkout page, so a
    double-click sends the same key twice and the customer pays once."""
    amounts = price_order(cart, region)
    with db.transaction() as conn:
        for line in cart.lines.values():
            inventory.reserve(conn, line.product.id, line.quantity)
        payment_id = payments.charge(amounts["total"], card_token, idempotency_key)
        order_id = conn.execute(
            "INSERT INTO orders (user_id, total_cents, payment_id, status) VALUES (?, ?, ?, 'paid')",
            (user.id, amounts["total"], payment_id),
        ).lastrowid
    order = Order(order_id, user.id, list(cart.lines.values()), amounts["subtotal"], amounts["discount"],
                  amounts["tax"], amounts["shipping"], amounts["total"], payment_id, "paid")
    emails.send_receipt(user.email, order)
    return order


def refund_order(order):
    """Refund a whole paid order and put its stock back."""
    if order.status != "paid":
        raise ValueError("Only paid orders can be refunded.")
    payments.refund(order.payment_id, order.total_cents)
    with db.transaction() as conn:
        for line in order.lines:
            inventory.release(conn, line.product.id, line.quantity)
        conn.execute("UPDATE orders SET status = 'refunded' WHERE id = ?", (order.id,))
    order.status = "refunded"
