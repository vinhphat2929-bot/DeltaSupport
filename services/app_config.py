import json
import os
from pathlib import Path


API_BASE_URL_ENV_VAR = "DELTA_API_BASE_URL"
APP_CONFIG_PATH_ENV_VAR = "DELTA_APP_CONFIG_PATH"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_APP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "app_config.json"


def _normalize_base_url(value):
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return normalized.rstrip("/")


def _load_json_config(path):
    try:
        with open(path, "r", encoding="utf-8") as config_file:
            payload = json.load(config_file)
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _resolve_config_path():
    configured_path = str(os.getenv(APP_CONFIG_PATH_ENV_VAR, "") or "").strip()
    if configured_path:
        return Path(configured_path)
    return DEFAULT_APP_CONFIG_PATH


def get_api_base_url():
    env_url = _normalize_base_url(os.getenv(API_BASE_URL_ENV_VAR))
    if env_url:
        return env_url

    config_payload = _load_json_config(_resolve_config_path())
    config_url = _normalize_base_url(config_payload.get("api_base_url"))
    if config_url:
        return config_url

    return _normalize_base_url(DEFAULT_API_BASE_URL)


API_BASE_URL = get_api_base_url()
