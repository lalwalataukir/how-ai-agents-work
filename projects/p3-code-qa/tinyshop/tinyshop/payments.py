"""Charges and refunds through the PayGate API."""
import httpx

from tinyshop import config
from tinyshop.utils.retry import retry


class PaymentFailed(Exception):
    pass


@retry(times=3, on=(httpx.TimeoutException, httpx.ConnectError))
def charge(amount_cents, card_token, idempotency_key):
    """Charge a card. PayGate treats repeats with the same idempotency key as one charge, so a
    retry after a timeout can never charge the customer twice."""
    response = httpx.post(
        f"{config.PAYGATE_URL}/charges",
        json={"amount": amount_cents, "card": card_token},
        headers={"Authorization": f"Bearer {config.SECRET_KEY}", "Idempotency-Key": idempotency_key},
        timeout=10,
    )
    if response.status_code == 402:
        raise PaymentFailed(response.json().get("reason", "The card was declined."))
    response.raise_for_status()
    return response.json()["id"]


def refund(payment_id, amount_cents):
    response = httpx.post(f"{config.PAYGATE_URL}/charges/{payment_id}/refunds", json={"amount": amount_cents},
                          headers={"Authorization": f"Bearer {config.SECRET_KEY}"}, timeout=10)
    response.raise_for_status()
    return response.json()["id"]
