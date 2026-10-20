"""Stock levels. Reserving and releasing happen inside the caller's transaction."""


class OutOfStock(Exception):
    pass


def reserve(conn, product_id, quantity):
    """Take quantity out of stock, or raise OutOfStock. The WHERE clause makes the check and the
    update one step, so two shoppers can't both buy the last one."""
    changed = conn.execute(
        "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?", (quantity, product_id, quantity)
    ).rowcount
    if changed == 0:
        raise OutOfStock(f"Not enough stock for product {product_id}.")


def release(conn, product_id, quantity):
    """Put stock back, after a refund or a failed payment."""
    conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (quantity, product_id))
