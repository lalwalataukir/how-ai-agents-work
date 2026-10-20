"""The shopping cart."""
from tinyshop.coupons import discount_for
from tinyshop.models import CartLine


class Cart:
    """Products a customer means to buy, with at most one coupon."""

    MAX_QUANTITY = 10  # of any one product

    def __init__(self):
        self.lines = {}  # product id -> CartLine
        self.coupon = None

    def add(self, product, quantity=1):
        """Add a product, or more of one already in the cart, up to MAX_QUANTITY."""
        line = self.lines.get(product.id) or CartLine(product, 0)
        line.quantity = min(line.quantity + quantity, self.MAX_QUANTITY)
        self.lines[product.id] = line

    def remove(self, product_id):
        self.lines.pop(product_id, None)

    def subtotal_cents(self):
        return sum(line.product.price_cents * line.quantity for line in self.lines.values())

    def weight_grams(self):
        return sum(line.product.weight_grams * line.quantity for line in self.lines.values())

    def apply_coupon(self, code):
        """Use a coupon if it gives a discount now. Only one coupon per cart: a new one replaces the old."""
        if discount_for(code, self.subtotal_cents()) == 0 and code.upper() != "FREESHIP":
            return False
        self.coupon = code.upper()
        return True

    def discount_cents(self):
        return discount_for(self.coupon, self.subtotal_cents()) if self.coupon else 0
