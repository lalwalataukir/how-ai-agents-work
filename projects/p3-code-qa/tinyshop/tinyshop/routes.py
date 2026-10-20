"""HTTP handlers. Each takes a request dict and returns (status, body)."""
from tinyshop import auth
from tinyshop.cart import Cart

CARTS = {}  # session token -> Cart


def require_login(handler):
    """Turn away requests without a valid session with a 401."""
    def wrapped(request):
        user_id = auth.current_user_id(request.get("session", ""))
        if user_id is None:
            return 401, {"error": "Log in first."}
        return handler(request, user_id)
    return wrapped


def handle_login(request, users):
    user = users.get(request["email"].lower())
    token = auth.login(user, request["password"]) if user else None
    if not token:
        return 401, {"error": "Wrong email or password."}  # the same message either way
    return 200, {"session": token}


@require_login
def handle_add_to_cart(request, user_id):
    """POST /cart/items: add a product to the visitor's cart."""
    cart = CARTS.setdefault(request["session"], Cart())
    cart.add(request["product"], int(request.get("quantity", 1)))
    return 200, {"items": len(cart.lines), "subtotal_cents": cart.subtotal_cents()}


@require_login
def handle_apply_coupon(request, user_id):
    """POST /cart/coupon"""
    cart = CARTS.setdefault(request["session"], Cart())
    if not cart.apply_coupon(request["code"]):
        return 400, {"error": "That code doesn't apply to this cart."}
    return 200, {"discount_cents": cart.discount_cents()}


ROUTES = {
    ("POST", "/login"): handle_login,
    ("POST", "/cart/items"): handle_add_to_cart,
    ("POST", "/cart/coupon"): handle_apply_coupon,
}
