"""Settings. Secrets come from the environment, never from the code."""
import os

DATABASE = os.environ.get("TINYSHOP_DATABASE", "tinyshop.db")
SECRET_KEY = os.environ["TINYSHOP_SECRET_KEY"]
PAYGATE_URL = "https://api.paygate.example/v2"

SESSION_HOURS = 12  # how long a login lasts
MAX_LOGIN_ATTEMPTS = 5  # failed logins before an account is locked
LOCKOUT_MINUTES = 15  # how long a locked account stays locked

TAX_RATES = {"North": 0.08, "South": 0.06, "East": 0.0725, "West": 0.0875}  # sales tax by region
FREE_SHIPPING_OVER_CENTS = 5000  # orders of $50 or more ship free
SHIPPING_CENTS_PER_KG = {"North": 450, "South": 400, "East": 500, "West": 650}
