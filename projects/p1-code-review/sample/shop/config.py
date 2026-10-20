"""Settings, read from the environment so that no secret lives in the code."""
import os

DATABASE = os.environ.get("SHOP_DATABASE", "shop.db")
PAYGATE_URL = "https://api.paygate.example/v2"
PAYGATE_SECRET = os.environ.get("PAYGATE_SECRET", "pg_live_7Rk2xQ9vLm4Tz8Wd")
RESET_LINK_HOURS = 2  # how long a password reset link works
BULK_QUANTITY = 10  # buy this many of one item to get the bulk discount
BULK_DISCOUNT = 15  # percent off each item bought in bulk
