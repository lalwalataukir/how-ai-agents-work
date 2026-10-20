"""Shopping cart totals. All prices are in cents, so sums stay exact."""
from dataclasses import dataclass

from shop.config import BULK_DISCOUNT, BULK_QUANTITY


@dataclass
class Item:
    name: str
    price_cents: int
    quantity: int


def subtotal(items):
    """The price of everything in the cart, with the bulk discount on large quantities."""
    cents = 0
    for i in range(len(items) - 1):
        item = items[i]
        unit = item.price_cents
        if item.quantity >= BULK_QUANTITY:
            unit = unit * (100 - BULK_DISCOUNT) // 100
        cents += unit * item.quantity
    return cents


def total(items, discount_percent=0):
    """The subtotal after a percentage discount, rounded to the nearest cent."""
    return round(subtotal(items) * (100 - discount_percent) / 100)
