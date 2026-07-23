import sys, os
os.environ['ENVIRONMENT'] = 'development'
sys.path.insert(0, '.')

print('=== 1. IMPORTS ===')
from core.config import settings, JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, decode_token,
    generate_secure_token, is_account_locked, lockout_expires_at,
    LOCKOUT_THRESHOLD, LOCKOUT_MINUTES
)
from database.db import init_db
print('OK')

print('=== 2. DB SCHEMA ===')
init_db()
import sqlite3
conn = sqlite3.connect('coldtrace.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables:', tables)
required = {'locations','risk_scores','latest_scores','alerts','access_log','users','alert_preferences'}
missing = required - set(tables)
assert not missing, f'Missing tables: {missing}'
users_cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print('users cols:', users_cols)
for c in ['id','email','password_hash','is_verified','verification_token','verification_expires',
          'reset_token','reset_expires','created_at','failed_login_attempts','locked_until']:
    assert c in users_cols, f'Missing users column: {c}'
ap_cols = [r[1] for r in conn.execute('PRAGMA table_info(alert_preferences)').fetchall()]
print('alert_preferences cols:', ap_cols)
for c in ['id','user_id','location_id','channel','created_at']:
    assert c in ap_cols, f'Missing alert_preferences column: {c}'
conn.close()
print('OK')

print('=== 3. PASSWORD HASHING ===')
h = hash_password('TestPass1')
assert verify_password('TestPass1', h)
assert not verify_password('WrongPass1', h)
print('OK')

print('=== 4. PASSWORD STRENGTH ===')
cases = [
    ('short1',      False),
    ('allletters',  False),
    ('12345678',    False),
    ('password123', False),
    ('Secure99!',   True),
    ('MyApp2024',   True),
]
for pwd, expected in cases:
    ok, msg = validate_password_strength(pwd)
    assert ok == expected, f'{pwd!r}: expected {expected}, got {ok} ({msg})'
print('OK')

print('=== 5. JWT TOKENS ===')
access = create_access_token({'sub': 'user@example.com'})
p = decode_token(access)
assert p['sub'] == 'user@example.com' and p['type'] == 'access'
refresh = create_refresh_token({'sub': 'user@example.com'})
rp = decode_token(refresh)
assert rp['type'] == 'refresh'
expired = create_access_token({'sub': 'x'}, expires_minutes=-1)
try:
    decode_token(expired)
    assert False, 'Should have raised on expired token'
except Exception as e:
    print(f'  Expired token correctly rejected: {type(e).__name__}')
print('OK')

print('=== 6. SECURE TOKENS ===')
t1, t2 = generate_secure_token(), generate_secure_token()
assert len(t1) >= 40 and t1 != t2, 'Tokens not unique or too short'
print('OK')

print('=== 7. LOCKOUT HELPERS ===')
assert not is_account_locked(None)
assert not is_account_locked('2020-01-01T00:00:00')
assert is_account_locked(lockout_expires_at())
assert LOCKOUT_THRESHOLD == 5
assert LOCKOUT_MINUTES == 15
print('OK')

print('=== 8. MAIN.PY ROUTES ===')
from main import app
routes = [r.path for r in app.routes]
print('Routes:', routes)
for expected_route in ['/refresh', '/risk-scores', '/model-metrics', '/alert-status', '/dashboard-summary']:
    assert expected_route in routes, f'Missing route: {expected_route}'
print('OK')

print()
print('=' * 40)
print('ALL CHECKS PASSED')
print('=' * 40)
