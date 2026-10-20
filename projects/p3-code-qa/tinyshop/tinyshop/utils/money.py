"""Money, kept in whole cents so sums are exact."""


def format_cents(cents):
    """Cents as dollars for display: 123456 -> "$1,234.56", -500 -> "-$5.00"."""
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rest:02d}"
