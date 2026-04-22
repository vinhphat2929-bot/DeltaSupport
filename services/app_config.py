import json
import os
from pathlib import Path

import requests


API_BASE_URL_ENV_VAR = "DELTA_API_BASE_URL"
APP_CONFIG_PATH_ENV_VAR = "DELTA_APP_CONFIG_PATH"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_OFFICE_API_BASE_URL = "http://192.168.80.110:8000"
DEFAULT_TAILSCALE_API_BASE_URL = "http://100.111.27.65:8000"
DEFAULT_API_PROBE_TIMEOUT_SECONDS = 1.2
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


def _is_auto_mode(value):
    return _normalize_base_url(value).lower() == "auto"


def _dedupe_urls(values):
    seen = set()
    resolved = []
    for value in values:
        normalized = _normalize_base_url(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        resolved.append(normalized)
    return resolved


def _read_candidate_urls(config_payload):
    raw_candidates = config_payload.get("api_base_url_candidates", [])
    if isinstance(raw_candidates, str):
        raw_candidates = [item.strip() for item in raw_candidates.split(",")]
    if not isinstance(raw_candidates, list):
        raw_candidates = []

    candidates = _dedupe_urls(raw_candidates)
    if candidates:
        return candidates

    return _dedupe_urls(
        [
            DEFAULT_OFFICE_API_BASE_URL,
            DEFAULT_TAILSCALE_API_BASE_URL,
            DEFAULT_API_BASE_URL,
        ]
    )


def _is_healthy_api_url(base_url, timeout_seconds=DEFAULT_API_PROBE_TIMEOUT_SECONDS):
    try:
        response = requests.get(base_url, timeout=timeout_seconds)
    except requests.RequestException:
        return False

    content_type = str(response.headers.get("Content-Type", "")).lower()
    if response.status_code >= 400:
        return False
    if "application/json" not in content_type:
        return False

    try:
        payload = response.json()
    except Exception:
        return False

    return isinstance(payload, dict) and str(payload.get("status", "")).strip().upper() == "API OK"


def get_api_base_url():
    env_url = _normalize_base_url(os.getenv(API_BASE_URL_ENV_VAR))
    if env_url and not _is_auto_mode(env_url):
        return env_url

    config_payload = _load_json_config(_resolve_config_path())
    config_url = _normalize_base_url(config_payload.get("api_base_url"))
    if config_url and not _is_auto_mode(config_url):
        return config_url

    for candidate_url in _read_candidate_urls(config_payload):
        if _is_healthy_api_url(candidate_url):
            return candidate_url

    fallback_candidates = _read_candidate_urls(config_payload)
    if fallback_candidates:
        return fallback_candidates[0]
    return _normalize_base_url(DEFAULT_API_BASE_URL)


API_BASE_URL = get_api_base_url()
