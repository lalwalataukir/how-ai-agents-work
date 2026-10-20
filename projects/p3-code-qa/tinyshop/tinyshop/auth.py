"""Passwords, logins and sessions."""
import hashlib
import hmac
import secrets
import time

from tinyshop import config

ITERATIONS = 600_000  # PBKDF2 rounds: slow on purpose, so stolen hashes are hard to crack
SESSIONS = {}  # token -> (user id, when it expires)


def hash_password(password):
    """A salted PBKDF2 hash, stored as salt$hash. The same password gives a different hash each time."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    """Check a password against a stored hash, in constant time so timing gives nothing away."""
    salt, expected = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected)


def login(user, password):
    """Log a user in and return a session token, or None. Too many wrong passwords lock the account."""
    now = time.time()
    if user.locked_until > now:
        return None
    if not verify_password(password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= config.MAX_LOGIN_ATTEMPTS:
            user.locked_until = now + config.LOCKOUT_MINUTES * 60
            user.failed_logins = 0
        return None
    user.failed_logins = 0
    return create_session(user)


def create_session(user):
    """A random session token that expires after SESSION_HOURS."""
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = (user.id, time.time() + config.SESSION_HOURS * 3600)
    return token


def current_user_id(token):
    """The user a session token belongs to, or None if it's unknown or has expired."""
    user_id, expires = SESSIONS.get(token, (None, 0))
    if time.time() >= expires:
        SESSIONS.pop(token, None)
        return None
    return user_id
