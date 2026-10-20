"""The shop's records."""
from dataclasses import dataclass, field


@dataclass
class User:
    id: int
    email: str
    password_hash: str
    failed_logins: int = 0
    locked_until: float = 0.0


@dataclass
class Product:
    id: int
    name: str
    price_cents: int
    weight_grams: int
    stock: int


@dataclass
class CartLine:
    product: Product
    quantity: int


@dataclass
class Order:
    id: int
    user_id: int
    lines: list = field(default_factory=list)
    subtotal_cents: int = 0
    discount_cents: int = 0
    tax_cents: int = 0
    shipping_cents: int = 0
    total_cents: int = 0
    payment_id: str = ""
    status: str = "new"  # new, paid, refunded
