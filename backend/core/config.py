import os
import yaml
from pydantic import BaseModel
from typing import List

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
    email_recipients: List[str]
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
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
