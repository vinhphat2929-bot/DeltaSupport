import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin

import requests

from app_version import APP_NAME, APP_VERSION
from services.app_config import API_BASE_URL


APP_UPDATE_TIMEOUT_SECONDS = 15
APP_UPDATE_DOWNLOAD_TIMEOUT_SECONDS = 120


def normalize_text(value):
    return str(value or "").strip()


def _safe_json_response(response, fallback_message="Server returned an invalid response."):
    content_type = str(response.headers.get("Content-Type", "")).lower()
    status = getattr(response, "status_code", None)
    body_text = ""
    try:
        body_text = response.text or ""
    except Exception:
        body_text = ""

    if "application/json" in content_type:
        try:
            return response.json()
        except Exception:
            pass

    preview = body_text.strip()
    if len(preview) > 250:
        preview = preview[:250] + "..."
    if not preview:
        preview = "<empty response body>"
    return {
        "success": False,
        "message": f"{fallback_message} (HTTP {status}) {preview}",
    }


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


def is_frozen_app():
    return bool(getattr(sys, "frozen", False))


def get_current_app_version():
    return APP_VERSION


def get_current_executable_path():
    if not is_frozen_app():
        return None
    try:
        return Path(sys.executable).resolve()
    except Exception:
        return None


def _resolve_download_url(value):
    text = normalize_text(value)
    if not text:
        return ""
    if text.lower().startswith(("http://", "https://")):
        return text
    return urljoin(API_BASE_URL.rstrip("/") + "/", text.lstrip("/"))


def check_for_app_update():
    try:
        response = requests.get(
            f"{API_BASE_URL}/app-update",
            params={"current_version": APP_VERSION},
            timeout=APP_UPDATE_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {"success": False, "message": str(exc), "update_available": False}

    payload = _safe_json_response(response, fallback_message="Unable to check for app updates.")
    if not payload.get("success", True):
        payload.setdefault("update_available", False)
        return payload

    latest_version = normalize_text(payload.get("version"))
    minimum_supported_version = normalize_text(payload.get("minimum_supported_version"))
    update_available = bool(payload.get("update_available"))
    if latest_version and is_newer_version(latest_version, APP_VERSION):
        update_available = True

    mandatory = bool(payload.get("mandatory"))
    if minimum_supported_version and is_newer_version(minimum_supported_version, APP_VERSION):
        mandatory = True
        update_available = True

    return {
        "success": True,
        "update_available": update_available,
        "current_version": APP_VERSION,
        "version": latest_version,
        "release_notes": normalize_text(payload.get("release_notes")),
        "published_at": normalize_text(payload.get("published_at")),
        "minimum_supported_version": minimum_supported_version,
        "mandatory": mandatory,
        "download_url": _resolve_download_url(payload.get("download_url")),
        "file_name": normalize_text(payload.get("file_name")),
        "file_size": int(payload.get("file_size") or 0),
        "message": normalize_text(payload.get("message")),
    }


def ensure_update_can_start():
    if not is_frozen_app():
        return {
            "success": False,
            "message": "Auto update chi hoat dong tren ban .exe da build.",
        }

    executable_path = get_current_executable_path()
    if executable_path is None or not executable_path.exists():
        return {"success": False, "message": "Khong tim thay file .exe hien tai de update."}

    parent_dir = executable_path.parent
    try:
        parent_dir.mkdir(parents=True, exist_ok=True)
        probe_path = parent_dir / f".update_probe_{os.getpid()}.tmp"
        with open(probe_path, "w", encoding="utf-8") as probe_file:
            probe_file.write("ok")
        probe_path.unlink(missing_ok=True)
    except Exception:
        return {
            "success": False,
            "message": "Khong co quyen ghi de cap nhat app tai thu muc hien tai.",
        }

    return {"success": True, "executable_path": str(executable_path)}


def download_update_package(update_info, progress_callback=None):
    download_url = normalize_text((update_info or {}).get("download_url"))
    latest_version = normalize_text((update_info or {}).get("version"))
    if not download_url:
        return {"success": False, "message": "Khong co link tai ban cap nhat."}

    temp_dir = Path(tempfile.gettempdir()) / "DeltaOneUpdate"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_name = normalize_text((update_info or {}).get("file_name"))
    if not file_name.lower().endswith(".exe"):
        file_name = f"delta-one-{latest_version or 'latest'}.exe"

    download_path = temp_dir / file_name

    try:
        with requests.get(
            download_url,
            stream=True,
            timeout=(APP_UPDATE_TIMEOUT_SECONDS, APP_UPDATE_DOWNLOAD_TIMEOUT_SECONDS),
        ) as response:
            response.raise_for_status()
            total_bytes = int(response.headers.get("Content-Length") or 0)
            downloaded_bytes = 0
            with open(download_path, "wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    output_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded_bytes, total_bytes)
    except requests.RequestException as exc:
        return {"success": False, "message": f"Khong tai duoc ban cap nhat: {exc}"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}

    if not download_path.exists() or download_path.stat().st_size <= 0:
        return {"success": False, "message": "File update tai ve khong hop le."}

    return {
        "success": True,
        "download_path": str(download_path),
        "file_size": int(download_path.stat().st_size),
    }


def launch_self_update(download_path):
    precheck = ensure_update_can_start()
    if not precheck.get("success"):
        return precheck

    executable_path = Path(precheck["executable_path"])
    source_path = Path(download_path)
    if not source_path.exists():
        return {"success": False, "message": "Khong tim thay file update da tai ve."}

    helper_dir = Path(tempfile.gettempdir()) / "DeltaOneUpdate"
    helper_dir.mkdir(parents=True, exist_ok=True)
    script_path = helper_dir / "apply_update.ps1"

    script_content = r"""
param(
    [int]$AppPid,
    [string]$SourcePath,
    [string]$TargetPath
)

$ErrorActionPreference = "Stop"
$targetDir = [System.IO.Path]::GetDirectoryName($TargetPath)
$backupPath = "$TargetPath.old"
$deadline = (Get-Date).AddMinutes(3)

while (Get-Process -Id $AppPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Milliseconds 500
    if ((Get-Date) -gt $deadline) {
        exit 1
    }
}

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        if (Test-Path -LiteralPath $backupPath) {
            Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
        }

        if (Test-Path -LiteralPath $TargetPath) {
            Move-Item -LiteralPath $TargetPath -Destination $backupPath -Force
        }

        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Remove-Item -LiteralPath $SourcePath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue

        Start-Process -FilePath $TargetPath -WorkingDirectory $targetDir
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
}

exit 1
"""

    try:
        with open(script_path, "w", encoding="utf-8") as script_file:
            script_file.write(script_content.strip() + "\n")
    except Exception as exc:
        return {"success": False, "message": f"Khong tao duoc script update: {exc}"}

    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(script_path),
        "-AppPid",
        str(os.getpid()),
        "-SourcePath",
        str(source_path),
        "-TargetPath",
        str(executable_path),
    ]

    creationflags = 0
    for flag_name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
        creationflags |= int(getattr(subprocess, flag_name, 0) or 0)

    try:
        subprocess.Popen(
            command,
            close_fds=True,
            creationflags=creationflags,
        )
    except Exception as exc:
        return {"success": False, "message": f"Khong the khoi dong trinh update: {exc}"}

    return {
        "success": True,
        "message": f"{APP_NAME} dang cap nhat va se mo lai ngay sau khi xong.",
    }
