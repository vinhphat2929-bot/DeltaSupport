import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse


router = APIRouter()

APP_UPDATE_CONFIG_ENV_VAR = "DELTA_APP_UPDATE_CONFIG_PATH"
DEFAULT_APP_UPDATE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "app_update_config.json"


def normalize_text(value):
    return str(value or "").strip()


def _resolve_app_update_config_path():
    configured_path = normalize_text(os.getenv(APP_UPDATE_CONFIG_ENV_VAR))
    if configured_path:
        return Path(configured_path)
    return DEFAULT_APP_UPDATE_CONFIG_PATH


def _load_app_update_config():
    config_path = _resolve_app_update_config_path()
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            payload = json.load(config_file)
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _parse_version_parts(value):
    text = normalize_text(value)
    if not text:
        return ()

    parts = []
    for part in re.split(r"[^\d]+", text):
        if not part:
            continue
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)

    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer_version(latest_version, current_version):
    latest_parts = _parse_version_parts(latest_version)
    current_parts = _parse_version_parts(current_version)
    max_length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (max_length - len(latest_parts))
    current_parts += (0,) * (max_length - len(current_parts))
    return latest_parts > current_parts


def _resolve_release_file_path(config_payload):
    configured_path = normalize_text(config_payload.get("windows_exe_path"))
    if not configured_path:
        return None

    release_path = Path(configured_path)
    if not release_path.is_absolute():
        release_path = (_resolve_app_update_config_path().parent / release_path).resolve()

    if not release_path.exists() or not release_path.is_file():
        return None
    return release_path


def _build_download_url(request, endpoint_path):
    return str(request.base_url).rstrip("/") + endpoint_path


def _build_update_payload(config_payload, request, current_version=""):
    latest_version = normalize_text(config_payload.get("version"))
    release_file_path = _resolve_release_file_path(config_payload)
    release_notes = normalize_text(config_payload.get("release_notes"))
    minimum_supported_version = normalize_text(config_payload.get("minimum_supported_version"))
    published_at = normalize_text(config_payload.get("published_at"))
    mandatory = bool(config_payload.get("mandatory"))

    if not latest_version or release_file_path is None:
        return {
            "success": True,
            "update_available": False,
            "version": latest_version,
            "current_version": normalize_text(current_version),
            "release_notes": release_notes,
            "minimum_supported_version": minimum_supported_version,
            "published_at": published_at,
            "mandatory": mandatory,
            "download_url": "",
            "file_name": "",
            "file_size": 0,
            "message": "No app update is configured.",
        }

    current_text = normalize_text(current_version)
    minimum_required = False
    if minimum_supported_version and current_text:
        minimum_required = is_newer_version(minimum_supported_version, current_text)

    update_available = is_newer_version(latest_version, current_text)
    return {
        "success": True,
        "update_available": update_available,
        "version": latest_version,
        "current_version": current_text,
        "release_notes": release_notes,
        "minimum_supported_version": minimum_supported_version,
        "published_at": published_at,
        "mandatory": bool(mandatory or minimum_required),
        "download_url": _build_download_url(request, "/app-update/download"),
        "file_name": release_file_path.name,
        "file_size": int(release_file_path.stat().st_size),
        "message": "Update available." if update_available else "App is up to date.",
    }


@router.get("/app-update")
def get_app_update(request: Request, current_version: str = ""):
    config_payload = _load_app_update_config()
    return _build_update_payload(config_payload, request, current_version=current_version)


@router.get("/app-update/download")
def download_app_update():
    config_payload = _load_app_update_config()
    release_file_path = _resolve_release_file_path(config_payload)
    if release_file_path is None:
        raise HTTPException(status_code=404, detail="App update package not found.")

    return FileResponse(
        path=release_file_path,
        filename=release_file_path.name,
        media_type="application/octet-stream",
    )
