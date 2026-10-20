"""Discount codes."""
from datetime import date

COUPONS = {  # code -> (percent off, minimum spend in cents, last day it works)
    "WELCOME10": (10, 0, date(2026, 12, 31)),
    "SPRING25": (25, 8000, date(2026, 5, 31)),
    "FREESHIP": (0, 3000, date(2026, 12, 31)),
}


def discount_for(code, subtotal_cents, today=None):
    """The discount in cents for a coupon code, or 0. Unknown, expired and under-minimum codes give nothing."""
    today = today or date.today()
    percent, minimum, last_day = COUPONS.get(code.strip().upper(), (0, 0, date.min))
    if today > last_day or subtotal_cents < minimum:
        return 0
    return subtotal_cents * percent // 100
