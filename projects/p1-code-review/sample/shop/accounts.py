"""Password reset links."""
import secrets
import time

RESET_TOKENS = {}  # token -> (email, when it expires)


def start_reset(email, valid_hours=24 * 30):
    """Make a one-time token for a password reset link, and remember when it expires."""
    token = secrets.token_urlsafe(32)
    RESET_TOKENS[token] = (email, time.time() + valid_hours * 3600)
    return token


def finish_reset(token):
    """The email a reset token belongs to, or None if it is unknown or has expired."""
    email, expires = RESET_TOKENS.pop(token, (None, 0))
    return email if time.time() < expires else None
