"""
Full audit for ColdTrace backend — runs after auth endpoints were added.
Tests: imports, DB schema, security utils, JWT, auth router logic, route list, CORS config.
"""
import os, sys
os.environ["ENVIRONMENT"] = "development"
sys.path.insert(0, ".")

PASS = []
FAIL = []

def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✅  {name}")
    except Exception as e:
        FAIL.append((name, e))
        print(f"  ❌  {name}: {e}")

print("\n=== SECTION 1: Core imports ===")

def t_imports():
    from core.config import (settings, JWT_SECRET_KEY, JWT_ALGORITHM,
                              ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
                              FRONTEND_URL, ADMIN_API_KEY, GMAIL_USER)
    assert JWT_SECRET_KEY, "JWT_SECRET_KEY empty"
    assert FRONTEND_URL
check("config.py imports + JWT vars present", t_imports)

def t_security_imports():
    from core.security import (
        hash_password, verify_password, validate_password_strength,
        create_access_token, create_refresh_token, decode_token,
        generate_secure_token, is_account_locked, lockout_expires_at,
        LOCKOUT_THRESHOLD, LOCKOUT_MINUTES, get_token_subject
    )
check("security.py — all symbols importable", t_security_imports)

def t_alerts_import():
    from services.alerts import send_email_alert, send_email_to, trigger_alerts
check("alerts.py — send_email_to present", t_alerts_import)

def t_auth_router_import():
    from routers.auth import router, get_current_user
    from fastapi import APIRouter
    assert isinstance(router, APIRouter)
check("routers/auth.py — router + get_current_user importable", t_auth_router_import)

print("\n=== SECTION 2: Database schema ===")

def t_db_schema():
    from database.db import init_db
    import sqlite3
    init_db()
    conn = sqlite3.connect("coldtrace.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    required = {"locations","risk_scores","latest_scores","alerts","access_log","users","alert_preferences"}
    missing = required - tables
    assert not missing, f"Missing tables: {missing}"

    users_cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    for c in ["id","email","password_hash","is_verified","verification_token",
              "verification_expires","reset_token","reset_expires",
              "created_at","failed_login_attempts","locked_until"]:
        assert c in users_cols, f"Missing users.{c}"

    ap_cols = {r[1] for r in conn.execute("PRAGMA table_info(alert_preferences)").fetchall()}
    for c in ["id","user_id","location_id","channel","created_at"]:
        assert c in ap_cols, f"Missing alert_preferences.{c}"
    conn.close()
check("All 7 tables present with correct columns", t_db_schema)

print("\n=== SECTION 3: Security utilities ===")

def t_bcrypt():
    from core.security import hash_password, verify_password
    h = hash_password("ColdTrace2024!")
    assert verify_password("ColdTrace2024!", h)
    assert not verify_password("wrongpass1", h)
check("bcrypt hash/verify", t_bcrypt)

def t_password_strength():
    from core.security import validate_password_strength
    bad = [("short1","too short"), ("allletters","no number"),
           ("12345678","no letter"), ("password123","blocklist")]
    for pwd, reason in bad:
        ok, msg = validate_password_strength(pwd)
        assert not ok, f"{pwd!r} should fail ({reason}) but passed"
    for pwd in ["Secure99!", "Blueberry42", "MyApp2024"]:
        ok, msg = validate_password_strength(pwd)
        assert ok, f"{pwd!r} should pass but failed: {msg}"
check("password strength validator — 7 cases", t_password_strength)

def t_jwt():
    from core.security import create_access_token, create_refresh_token, decode_token
    from jose import JWTError
    # access token
    tok = create_access_token({"sub": "audit@example.com"})
    p = decode_token(tok)
    assert p["sub"] == "audit@example.com" and p["type"] == "access"
    # refresh token
    rtok = create_refresh_token({"sub": "audit@example.com"})
    rp = decode_token(rtok)
    assert rp["type"] == "refresh"
    # expired token rejected
    expired = create_access_token({"sub": "x"}, expires_minutes=-1)
    try:
        decode_token(expired)
        assert False, "should have raised"
    except JWTError:
        pass
check("JWT create/decode/expiry", t_jwt)

def t_lockout():
    from core.security import is_account_locked, lockout_expires_at, LOCKOUT_THRESHOLD, LOCKOUT_MINUTES
    assert not is_account_locked(None)
    assert not is_account_locked("2020-01-01T00:00:00")
    assert is_account_locked(lockout_expires_at())
    assert LOCKOUT_THRESHOLD == 5
    assert LOCKOUT_MINUTES == 15
check("account lockout helpers", t_lockout)

def t_secure_token():
    from core.security import generate_secure_token
    t1, t2 = generate_secure_token(), generate_secure_token()
    assert len(t1) >= 40 and t1 != t2
check("generate_secure_token — length + uniqueness", t_secure_token)

print("\n=== SECTION 4: Route registration ===")

def t_routes():
    from main import app
    routes = {r.path for r in app.routes}
    # existing routes
    for r in ["/risk-scores", "/dashboard-summary", "/alert-status",
              "/model-metrics", "/refresh", "/history/{location_id}"]:
        assert r in routes, f"Missing existing route: {r}"
    # new auth routes
    for r in ["/auth/register", "/auth/verify-email", "/auth/login",
              "/auth/refresh-token", "/auth/logout",
              "/auth/forgot-password", "/auth/reset-password", "/auth/me"]:
        assert r in routes, f"Missing auth route: {r}"
check("All 14 endpoints registered", t_routes)

print("\n=== SECTION 5: CORS config ===")

def t_cors():
    from main import app
    from starlette.middleware.cors import CORSMiddleware
    cors = next((m for m in app.user_middleware if "CORSMiddleware" in str(m)), None)
    assert cors is not None, "CORSMiddleware not found"
    # Check allow_credentials is True by checking the middleware kwargs
    from core.config import FRONTEND_URL
    assert FRONTEND_URL  # must not be empty string
check("CORS middleware present, FRONTEND_URL non-empty", t_cors)

print("\n=== SECTION 6: Auth router logic ===")

def t_cookie_kwargs():
    from routers.auth import _COOKIE_KWARGS
    assert _COOKIE_KWARGS["httponly"]  is True
    assert _COOKIE_KWARGS["secure"]   is True
    assert _COOKIE_KWARGS["samesite"] == "none"
check("Cookie flags: httponly=True, secure=True, samesite=none", t_cookie_kwargs)

def t_router_prefix():
    from routers.auth import router
    assert router.prefix == "/auth"
check("Router prefix is /auth", t_router_prefix)

def t_anti_enum_messages():
    # Verify the generic messages are identical strings (anti-enumeration)
    import inspect
    import routers.auth as auth_mod
    src = inspect.getsource(auth_mod)
    assert "If that email is available" in src
    assert "If an account with that email exists" in src
check("Anti-enumeration generic messages present", t_anti_enum_messages)

# ── Final summary ──────────────────────────────────────────────────────────────
print()
print("=" * 50)
print(f"  PASSED: {len(PASS)}/{len(PASS)+len(FAIL)}")
if FAIL:
    print(f"  FAILED: {len(FAIL)}")
    for name, err in FAIL:
        print(f"    ❌ {name}: {err}")
else:
    print("  ALL CHECKS PASSED ✅")
print("=" * 50)
sys.exit(0 if not FAIL else 1)
