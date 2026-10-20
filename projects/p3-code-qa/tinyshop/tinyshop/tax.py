"""Sales tax."""
from decimal import ROUND_HALF_UP, Decimal

from tinyshop import config


def tax_for(region, taxable_cents):
    """Sales tax in cents for a region. Rounded half up to the cent, as the tax office does,
    not to the nearest even cent as Python's round() would."""
    rate = Decimal(str(config.TAX_RATES[region]))
    return int((Decimal(taxable_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
