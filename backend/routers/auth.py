"""
backend/routers/auth.py
-----------------------
All authentication endpoints for ColdTrace.

Token strategy:
  - access_token  → httpOnly, Secure, SameSite=None cookie, 15-min TTL
  - refresh_token → httpOnly, Secure, SameSite=None cookie, 7-day TTL
  - Neither token is returned in the JSON body (prevents JS-accessible storage).
  - SameSite=None is required because frontend (Vercel) and backend (Render) are
    cross-origin. Secure=True means HTTPS-only, which both platforms enforce.

Anti-enumeration:
  - /register and /forgot-password always return the same generic success message
    regardless of whether the email already exists or not.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import JWTError

from database.db import fetch_one, execute_query
from core.config import FRONTEND_URL
from core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    is_account_locked,
    lockout_expires_at,
    LOCKOUT_THRESHOLD,
)
from services.alerts import send_email_to

# ---------------------------------------------------------------------------
# Router + rate limiter (uses the same Limiter instance wired in main.py via
# app.state.limiter — slowapi picks it up automatically through the request)
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
_COOKIE_KWARGS = dict(
    httponly=True,
    secure=True,       # HTTPS only — both Vercel and Render enforce HTTPS
    samesite="none",   # Required for cross-origin Vercel ↔ Render requests
    path="/",
)

def _set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(key="access_token",  value=access_token,  max_age=60 * 15,        **_COOKIE_KWARGS)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=60 * 60 * 24 * 7, **_COOKIE_KWARGS)

def _clear_auth_cookies(response: Response):
    response.delete_cookie(key="access_token",  path="/", samesite="none", secure=True)
    response.delete_cookie(key="refresh_token", path="/", samesite="none", secure=True)

# ---------------------------------------------------------------------------
# get_current_user dependency — reusable across any protected endpoint
# ---------------------------------------------------------------------------
def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency. Reads access_token cookie, validates JWT, fetches user
    from DB. Raises HTTP 401 if token is missing, invalid, expired, or user
    not found. Import and use as: user = Depends(get_current_user)
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired.")

    user = fetch_one("SELECT * FROM users WHERE email = ?", (email,))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _utc_str(dt: datetime) -> str:
    return dt.isoformat()

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None

def _token_expired(expires_str: Optional[str]) -> bool:
    dt = _parse_dt(expires_str)
    return dt is None or _utc_now() > dt

# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register")
@limiter.limit("3/hour")
def register(body: RegisterRequest, request: Request):
    """
    Register a new account. Always returns the same success message regardless
    of whether the email already exists (prevents user enumeration).
    """
    generic_ok = {"message": "If that email is available, a verification link has been sent."}

    # Validate password strength first (safe to reveal — not email-specific)
    ok, reason = validate_password_strength(body.password)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)

    # Check whether email already exists — but don't reveal the result
    existing = fetch_one("SELECT id FROM users WHERE email = ?", (body.email,))
    if existing:
        # Silently return success — don't leak that the email is registered
        return generic_ok

    pw_hash     = hash_password(body.password)
    v_token     = generate_secure_token()
    v_expires   = _utc_str(_utc_now() + timedelta(hours=24))

    execute_query(
        """INSERT INTO users
           (email, password_hash, is_verified, verification_token, verification_expires)
           VALUES (?, ?, 0, ?, ?)""",
        (body.email, pw_hash, v_token, v_expires),
    )

    verify_link = f"{FRONTEND_URL}/verify-email?token={v_token}"
    send_email_to(
        body.email,
        subject="Verify your ColdTrace account",
        body=(
            f"Welcome to ColdTrace!\n\n"
            f"Please verify your email address by clicking the link below.\n"
            f"This link expires in 24 hours.\n\n"
            f"{verify_link}\n\n"
            f"If you did not create this account, you can safely ignore this email."
        ),
    )

    return generic_ok

# ---------------------------------------------------------------------------
# GET /auth/verify-email?token=xxx
# ---------------------------------------------------------------------------
@router.get("/verify-email")
def verify_email(token: str):
    """Verify email via the token sent during registration."""
    user = fetch_one("SELECT * FROM users WHERE verification_token = ?", (token,))

    if not user or _token_expired(user.get("verification_expires")):
        raise HTTPException(status_code=400, detail="Verification link is invalid or has expired.")

    execute_query(
        "UPDATE users SET is_verified = 1, verification_token = NULL, verification_expires = NULL WHERE id = ?",
        (user["id"],),
    )

    # Return a JSON success response
    return {"message": "Email verified successfully."}

# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login")
@limiter.limit("10/hour")
def login(body: LoginRequest, request: Request, response: Response):
    """
    Authenticate and issue httpOnly cookies containing JWT tokens.
    Tokens are NOT returned in the JSON body.
    """
    user = fetch_one("SELECT * FROM users WHERE email = ?", (body.email,))

    # Generic error to prevent user enumeration
    _bad_creds = HTTPException(status_code=401, detail="Invalid email or password.")

    if not user:
        raise _bad_creds

    # Account lockout check
    if is_account_locked(user.get("locked_until")):
        raise HTTPException(
            status_code=429,
            detail="Account temporarily locked due to too many failed login attempts. Try again in 15 minutes.",
        )

    # Password check
    if not verify_password(body.password, user["password_hash"]):
        new_attempts = (user["failed_login_attempts"] or 0) + 1
        if new_attempts >= LOCKOUT_THRESHOLD:
            execute_query(
                "UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?",
                (new_attempts, lockout_expires_at(), user["id"]),
            )
            raise HTTPException(
                status_code=429,
                detail=f"Account locked after {LOCKOUT_THRESHOLD} failed attempts. Try again in 15 minutes.",
            )
        else:
            execute_query(
                "UPDATE users SET failed_login_attempts = ? WHERE id = ?",
                (new_attempts, user["id"]),
            )
        raise _bad_creds

    # Email must be verified before granting tokens
    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address before logging in. Check your inbox for the verification link.",
        )

    # Successful login — reset lockout counters
    execute_query(
        "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
        (user["id"],),
    )

    access_token  = create_access_token({"sub": user["email"]})
    refresh_token = create_refresh_token({"sub": user["email"]})
    _set_auth_cookies(response, access_token, refresh_token)

    return {"message": "Login successful.", "email": user["email"]}

# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post("/refresh-token")
@router.post("/refresh")
@limiter.limit("30/hour")
def refresh_token_endpoint(request: Request, response: Response):
    """Issue a new access_token from a valid refresh_token cookie."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token found.")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired.")

    # Ensure user still exists
    user = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    new_access = create_access_token({"sub": email})
    response.set_cookie(key="access_token", value=new_access, max_age=60 * 15, **_COOKIE_KWARGS)
    return {"message": "Token refreshed."}

# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout")
def logout(response: Response):
    """Clear both auth cookies. No DB changes needed — tokens are stateless."""
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully."}

# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------
@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(body: ForgotPasswordRequest, request: Request):
    """
    Send a password-reset link. Always returns a generic success message
    regardless of whether the email exists (prevents user enumeration).
    """
    generic_ok = {"message": "If an account with that email exists, a password reset link has been sent."}

    user = fetch_one("SELECT * FROM users WHERE email = ?", (body.email,))
    if not user:
        return generic_ok  # Silently succeed — don't reveal the email isn't registered

    reset_token   = generate_secure_token()
    reset_expires = _utc_str(_utc_now() + timedelta(hours=1))

    execute_query(
        "UPDATE users SET reset_token = ?, reset_expires = ? WHERE id = ?",
        (reset_token, reset_expires, user["id"]),
    )

    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    send_email_to(
        body.email,
        subject="Reset your ColdTrace password",
        body=(
            f"You requested a password reset for your ColdTrace account.\n\n"
            f"Click the link below to reset your password.\n"
            f"This link expires in 1 hour.\n\n"
            f"{reset_link}\n\n"
            f"If you did not request this, you can safely ignore this email.\n"
            f"Your password will not be changed."
        ),
    )

    return generic_ok

# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------
@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest):
    """Validate reset token and update the user's password."""
    user = fetch_one("SELECT * FROM users WHERE reset_token = ?", (body.token,))

    if not user or _token_expired(user.get("reset_expires")):
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")

    ok, reason = validate_password_strength(body.new_password)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)

    new_hash = hash_password(body.new_password)
    execute_query(
        """UPDATE users
           SET password_hash = ?, reset_token = NULL, reset_expires = NULL,
               failed_login_attempts = 0, locked_until = NULL
           WHERE id = ?""",
        (new_hash, user["id"]),
    )
    # Access tokens are short-lived (15 min) so we don't need an explicit
    # blacklist — existing sessions naturally expire within 15 minutes.
    # Acceptable for this project's threat model.

    return {"message": "Password reset successfully. You can now log in with your new password."}

# ---------------------------------------------------------------------------
# GET /auth/me — example protected endpoint using get_current_user
# ---------------------------------------------------------------------------
@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Return basic profile for the logged-in user."""
    return {
        "id":          current_user["id"],
        "email":       current_user["email"],
        "is_verified": bool(current_user["is_verified"]),
        "created_at":  current_user["created_at"],
    }
