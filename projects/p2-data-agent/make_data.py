"""Make shop.db: a year of sales for a small online shop. The data is made up, and the same
every time, so everyone's answers match the eval.

Run it with:
    uv run make_data.py
"""
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).parent / "shop.db"
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = {  # category -> (name, price in cents)
    "Books": [("Field Notes on Birds", 1899), ("The Patient Gardener", 2450), ("Cooking for One", 1599),
              ("A Short History of Maps", 2999), ("Learn Python in a Weekend", 3499), ("Night Sky Atlas", 2799),
              ("Bread Every Day", 1999), ("Small Spaces", 2199)],
    "Games": [("Harbour Masters", 4499), ("Pocket Chess", 1499), ("Tile Town", 3299), ("Word Ladder", 1999),
              ("Galaxy Traders", 5999), ("Pirate Dice", 1299), ("Forest Quest", 3899), ("Speed Sketch", 2499)],
    "Home": [("Linen Cushion", 2899), ("Oak Serving Board", 3599), ("Glass Carafe", 2299), ("Wool Throw", 6999),
             ("Ceramic Mug Set", 3199), ("Desk Lamp", 4899), ("Bamboo Tray", 1799), ("Scented Candle", 1499)],
    "Garden": [("Pruning Shears", 2599), ("Seed Starter Kit", 1999), ("Watering Can", 2799), ("Kneeling Pad", 1599),
               ("Bird Feeder", 3299), ("Herb Planter", 3999), ("Garden Gloves", 1299), ("Compost Bin", 7999)],
    "Toys": [("Wooden Train", 3499), ("Puzzle Cube", 999), ("Kite", 2199), ("Building Blocks", 4299),
             ("Plush Fox", 1899), ("Marble Run", 5499), ("Jump Rope", 799), ("Paint Set", 1699)],
}
FIRST = ["Asha", "Ben", "Chloe", "Dev", "Ella", "Farid", "Grace", "Hugo", "Isla", "Jai", "Kira", "Leo", "Maya",
         "Nikhil", "Olivia", "Priya", "Quinn", "Rohan", "Sara", "Tom", "Uma", "Vik", "Wen", "Yusuf", "Zoe"]
LAST = ["Shah", "Brown", "Okafor", "Patel", "Nguyen", "Garcia", "Kim", "Silva", "Rossi", "Khan", "Murphy", "Ito"]

SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL, joined TEXT NOT NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, price_cents INTEGER NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
                     ordered_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id),
                          quantity INTEGER NOT NULL, unit_cents INTEGER NOT NULL);
"""


def build(path=DB):
    """Write the database to path, replacing any old one. Returns the number of rows in each table."""
    rng = random.Random(2025)
    path = Path(path)
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    products = [(name, category, price) for category, items in PRODUCTS.items() for name, price in items]
    db.executemany("INSERT INTO products (name, category, price_cents) VALUES (?, ?, ?)", products)
    customers = []
    for _ in range(300):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        region = rng.choices(REGIONS, weights=[30, 25, 25, 20])[0]
        joined = date(2023, 1, 1) + timedelta(days=rng.randrange(1000))
        customers.append((name, region, joined.isoformat()))
    db.executemany("INSERT INTO customers (name, region, joined) VALUES (?, ?, ?)", customers)
    orders, items = [], []
    for order_id in range(1, 2001):
        day = date(2025, 1, 1) + timedelta(days=rng.randrange(365))
        if day.month in (11, 12) and rng.random() < 0.3:  # a holiday rush
            day = date(2025, 12, rng.randrange(1, 24))
        status = rng.choices(["completed", "refunded", "cancelled"], weights=[88, 7, 5])[0]
        orders.append((rng.randrange(1, 301), day.isoformat(), status))
        for product_id in rng.sample(range(1, len(products) + 1), rng.choices([1, 2, 3, 4], weights=[45, 30, 15, 10])[0]):
            price = products[product_id - 1][2]
            unit = price * 9 // 10 if rng.random() < 0.15 else price  # some sold at 10% off
            items.append((order_id, product_id, rng.choices([1, 2, 3], weights=[75, 20, 5])[0], unit))
    db.executemany("INSERT INTO orders (customer_id, ordered_at, status) VALUES (?, ?, ?)", orders)
    db.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_cents) VALUES (?, ?, ?, ?)", items)
    db.commit()
    counts = {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
              for table in ("customers", "products", "orders", "order_items")}
    db.close()
    return counts


if __name__ == "__main__":
    counts = build(Path(sys.argv[1]) if len(sys.argv) > 1 else DB)
    print("Wrote shop.db: " + ", ".join(f"{n} {table}" for table, n in counts.items()))
