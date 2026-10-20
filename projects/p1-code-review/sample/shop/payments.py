"""Calls to the PayGate payments API."""
import httpx

from shop import config


def refund(payment_id, amount_cents):
    """Send money back to the customer's card. PayGate refunds whatever amount it is sent,
    even more than was paid, so callers must check the amount first."""
    response = httpx.post(
        f"{config.PAYGATE_URL}/payments/{payment_id}/refunds",
        json={"amount": amount_cents},
        headers={"Authorization": f"Bearer {config.PAYGATE_SECRET}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["refund_id"]
