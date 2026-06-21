import os
import yaml
from pydantic import BaseModel
from typing import List, Optional

class Bounds(BaseModel):
    south: float
    west: float
    north: float
    east: float

class AppConfig(BaseModel):
    schedule_interval_hours: int
    region: str
    bounds: Bounds

class AlertsConfig(BaseModel):
    score_threshold: int
    # email_recipients removed from config.yaml — now queried from the users/alert_preferences
    # DB tables so only verified subscribers receive alerts.
    email_recipients: List[str] = []   # kept optional for backward-compat; ignored at runtime
    sms_recipients: List[str]

class ModelConfig(BaseModel):
    target_recall: float

class Config(BaseModel):
    app: AppConfig
    alerts: AlertsConfig
    model: ModelConfig

def load_config() -> Config:
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return Config(**data)

settings = load_config()

DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")
GMAIL_USER          = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD", "")
ADMIN_API_KEY       = os.getenv("ADMIN_API_KEY", "")
FRONTEND_URL        = os.getenv("FRONTEND_URL", "http://localhost:5173")

# ---------------------------------------------------------------------------
# JWT configuration
# ---------------------------------------------------------------------------
# JWT_SECRET_KEY MUST be set in the environment on Render (or any production
# host). It must be a long random string — generate with:
#   python -c "import secrets; print(secrets.token_hex(64))"
# If unset on startup, the server will refuse to start rather than silently
# running with an insecure blank/default key.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

# Unsafe fallback placeholder is strictly forbidden unless ALLOW_INSECURE_DEV_KEY=true is explicitly set.
_ALLOW_INSECURE = os.getenv("ALLOW_INSECURE_DEV_KEY", "").lower() == "true"

if not JWT_SECRET_KEY:
    if _ALLOW_INSECURE:
        JWT_SECRET_KEY = "dev-only-insecure-placeholder-change-in-production"
    else:
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: JWT_SECRET_KEY environment variable is not set. "
            "To resolve this, generate a secure random secret key with:\n"
            "  python -c \"import secrets; print(secrets.token_hex(64))\"\n"
            "and set it as the JWT_SECRET_KEY environment variable.\n"
            "For local development ONLY, you can bypass this requirement by setting "
            "the environment variable: ALLOW_INSECURE_DEV_KEY=true"
        )

JWT_ALGORITHM       = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES  = 15
REFRESH_TOKEN_EXPIRE_DAYS    = 7
