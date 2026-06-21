"""
backend/core/security.py
------------------------
Auth utility functions for ColdTrace.

No endpoints live here — this module is imported by auth router (to be added).
Nothing in this file makes DB calls; all DB interactions stay in the router layer.
"""

import secrets
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

# ---------------------------------------------------------------------------
# Password hashing  (using bcrypt directly — passlib is unmaintained and
# incompatible with bcrypt >= 4.0)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Password strength validation
# ---------------------------------------------------------------------------
# A minimal blocklist of the most-abused passwords. Not a full breach-database
# check — just a basic sanity gate so obviously terrible passwords are rejected
# at registration time.
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "password1234",
    "qwerty123", "qwerty1234", "abc12345", "abc123456",
    "123456789", "12345678", "letmein1", "welcome1",
    "monkey123", "dragon123", "iloveyou1", "admin1234",
    "coldtrace", "coldtrace1", "coldtrace123",
}

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Returns:
        (True, "") on success.
        (False, reason_string) on failure.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if password.lower() in _COMMON_PASSWORDS:
        return False, "Password is too common. Please choose a stronger password."
    return True, ""


# ---------------------------------------------------------------------------
# JWT token creation and decoding
# ---------------------------------------------------------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    data: dict,
    token_version: int,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        data: Payload claims dict. Typically {"sub": user_email}.
        token_version: The user's current token version.
        expires_minutes: Token lifetime in minutes (default 15).

    Returns:
        Signed JWT string.
    """
    payload = data.copy()
    payload.update({
        "type": "access",
        "tv": token_version,
        "exp": _utc_now() + timedelta(minutes=expires_minutes),
        "iat": _utc_now(),
    })
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    data: dict,
    token_version: int,
    expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS,
) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        data: Payload claims dict. Typically {"sub": user_email}.
        token_version: The user's current token version.
        expires_days: Token lifetime in days (default 7).

    Returns:
        Signed JWT string.
    """
    payload = data.copy()
    payload.update({
        "type": "refresh",
        "tv": token_version,
        "exp": _utc_now() + timedelta(days=expires_days),
        "iat": _utc_now(),
    })
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Validate and decode a JWT token.

    Raises:
        jose.JWTError: if the signature is invalid, token is expired,
                       or any other JWT validation error occurs.
    Returns:
        The decoded payload dict.
    """
    # jwt.decode() automatically validates signature AND expiry.
    # options={"verify_exp": True} is the default — stated here for clarity.
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"verify_exp": True},
    )


def get_token_subject(token: str) -> Optional[str]:
    """
    Convenience wrapper: decode token and return the 'sub' claim.
    Returns None if the token is invalid/expired instead of raising.
    Useful for optional-auth endpoints.
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Secure random token generation (email verification / password reset)
# ---------------------------------------------------------------------------
def generate_secure_token() -> str:
    """
    Generate a cryptographically secure URL-safe token.
    Used for email verification links and password-reset links.
    32 bytes → 43 base64url characters → ~256 bits of entropy.
    """
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Account lockout helpers
# ---------------------------------------------------------------------------
LOCKOUT_THRESHOLD   = 5          # failed attempts before lockout
LOCKOUT_MINUTES     = 15         # how long the lockout lasts


def is_account_locked(locked_until_str: Optional[str]) -> bool:
    """
    Return True if the account is currently locked.

    Args:
        locked_until_str: ISO-format datetime string from the DB, or None.
    """
    if not locked_until_str:
        return False
    try:
        locked_until = datetime.fromisoformat(locked_until_str)
        # If the stored value has no timezone, treat it as UTC
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return _utc_now() < locked_until
    except (ValueError, TypeError):
        return False


def lockout_expires_at() -> str:
    """Return an ISO-format UTC datetime string for now + LOCKOUT_MINUTES."""
    return (_utc_now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
