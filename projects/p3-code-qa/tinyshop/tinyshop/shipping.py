"""Shipping costs."""
import math

from tinyshop import config


def shipping_cost(weight_grams, region, subtotal_cents, coupon=None):
    """Shipping in cents: free over FREE_SHIPPING_OVER_CENTS or with the FREESHIP coupon,
    otherwise a rate per started kilogram for the region."""
    if subtotal_cents >= config.FREE_SHIPPING_OVER_CENTS or coupon == "FREESHIP":
        return 0
    kilograms = max(1, math.ceil(weight_grams / 1000))
    return kilograms * config.SHIPPING_CENTS_PER_KG[region]
