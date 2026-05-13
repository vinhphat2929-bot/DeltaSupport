import os
import re
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from app_version import APP_NAME, APP_VERSION
from services.app_config import API_BASE_URL


APP_UPDATE_TIMEOUT_SECONDS = 15
APP_UPDATE_DOWNLOAD_TIMEOUT_SECONDS = 120
DEFAULT_UPDATE_EXE_NAME = "DELTA_ONE.exe"
GOOGLE_DRIVE_DIRECT_DOWNLOAD_TEMPLATE = "https://drive.google.com/uc?export=download&id={file_id}"
WINDOWS_EXE_MAGIC = b"MZ"
PYINSTALLER_ENV_PREFIX = "_PYI_"
PYINSTALLER_ENV_KEYS = {"_MEIPASS2", "PYINSTALLER_RESET_ENVIRONMENT"}


def normalize_text(value):
    return str(value or "").strip()


def _build_clean_update_environment():
    clean_env = dict(os.environ)
    for key in list(clean_env.keys()):
        key_upper = key.upper()
        if key_upper.startswith(PYINSTALLER_ENV_PREFIX) or key_upper in PYINSTALLER_ENV_KEYS:
            clean_env.pop(key, None)
    clean_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return clean_env


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


def _extract_google_drive_file_id(value):
    text = normalize_text(value)
    if not text:
        return ""

    patterns = [
        r"drive\.google\.com/file/d/([A-Za-z0-9_-]+)",
        r"drive\.google\.com/open\?id=([A-Za-z0-9_-]+)",
        r"drive\.google\.com/uc\?(?:[^#]*&)?id=([A-Za-z0-9_-]+)",
        r"drive\.usercontent\.google\.com/download\?(?:[^#]*&)?id=([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_text(match.group(1))

    try:
        parsed = urlparse(text)
        query = parse_qs(parsed.query)
        file_id = normalize_text((query.get("id") or [""])[0])
        if file_id:
            return file_id
    except Exception:
        return ""
    return ""


def _normalize_download_candidate_url(value):
    resolved_url = _resolve_download_url(value)
    file_id = _extract_google_drive_file_id(resolved_url)
    if file_id:
        return GOOGLE_DRIVE_DIRECT_DOWNLOAD_TEMPLATE.format(file_id=file_id)
    return resolved_url


def _is_html_response(response):
    content_type = str((response.headers or {}).get("Content-Type", "")).lower()
    return "text/html" in content_type or "application/xhtml" in content_type


def _build_response_preview(response, limit=250):
    preview = ""
    try:
        preview = response.text or ""
    except Exception:
        preview = ""

    preview = " ".join(preview.split())
    if len(preview) > limit:
        preview = preview[:limit] + "..."
    return preview or "<empty response body>"


def _extract_google_drive_confirm_request(response):
    if response is None or not _is_html_response(response):
        return "", {}

    page_text = ""
    try:
        page_text = response.text or ""
    except Exception:
        page_text = ""

    if not page_text:
        return "", {}

    form_match = re.search(
        r'<form[^>]+id="download-form"[^>]+action="([^"]+)"[^>]*>(.*?)</form>',
        page_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not form_match:
        return "", {}

    action_url = unescape(normalize_text(form_match.group(1)))
    form_html = form_match.group(2) or ""
    params = {}
    for input_tag in re.findall(r"<input\b[^>]*>", form_html, flags=re.IGNORECASE):
        tag_lower = input_tag.lower()
        if 'type="hidden"' not in tag_lower and "type='hidden'" not in tag_lower:
            continue
        name_match = re.search(r'\bname="([^"]+)"|\bname=\'([^\']+)\'', input_tag, flags=re.IGNORECASE)
        if not name_match:
            continue
        value_match = re.search(r'\bvalue="([^"]*)"|\bvalue=\'([^\']*)\'', input_tag, flags=re.IGNORECASE)
        field_name = unescape(normalize_text(name_match.group(1) or name_match.group(2)))
        field_value = unescape(normalize_text((value_match.group(1) or value_match.group(2)) if value_match else ""))
        if field_name:
            params[field_name] = field_value

    if not action_url or not params:
        return "", {}

    return action_url, params


def _looks_like_windows_executable(leading_bytes):
    return bytes(leading_bytes or b"").startswith(WINDOWS_EXE_MAGIC)


def _stream_response_to_file(response, download_path, progress_callback=None):
    total_bytes = int(response.headers.get("Content-Length") or 0)
    downloaded_bytes = 0
    leading_bytes = b""

    with open(download_path, "wb") as output_file:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            if len(leading_bytes) < len(WINDOWS_EXE_MAGIC):
                remaining = len(WINDOWS_EXE_MAGIC) - len(leading_bytes)
                leading_bytes += chunk[:remaining]
            output_file.write(chunk)
            downloaded_bytes += len(chunk)
            if progress_callback:
                progress_callback(downloaded_bytes, total_bytes)

    return {
        "file_size": downloaded_bytes,
        "leading_bytes": leading_bytes,
    }


def _download_from_candidate_url(session, download_url, download_path, progress_callback=None):
    normalized_url = _normalize_download_candidate_url(download_url)
    if not normalized_url:
        return {"success": False, "message": "No valid update download link is available."}

    try:
        response = session.get(
            normalized_url,
            stream=True,
            allow_redirects=True,
            timeout=(APP_UPDATE_TIMEOUT_SECONDS, APP_UPDATE_DOWNLOAD_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return {"success": False, "message": f"Unable to download the update package: {exc}"}

    if _is_html_response(response):
        action_url, action_params = _extract_google_drive_confirm_request(response)
        if action_url and action_params:
            response.close()
            try:
                response = session.get(
                    action_url,
                    params=action_params,
                    stream=True,
                    allow_redirects=True,
                    timeout=(APP_UPDATE_TIMEOUT_SECONDS, APP_UPDATE_DOWNLOAD_TIMEOUT_SECONDS),
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                return {"success": False, "message": f"Unable to download the update package from Google Drive: {exc}"}

    if _is_html_response(response):
        preview = _build_response_preview(response)
        response.close()
        return {
            "success": False,
            "message": (
                "The update link did not return a valid .exe file. "
                f"The server returned HTML instead: {preview}"
            ),
        }

    try:
        stream_result = _stream_response_to_file(
            response,
            download_path,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        try:
            response.close()
        except Exception:
            pass
        return {"success": False, "message": str(exc)}
    finally:
        try:
            response.close()
        except Exception:
            pass

    if not download_path.exists() or download_path.stat().st_size <= 0:
        return {"success": False, "message": "The downloaded update package is invalid."}

    if not _looks_like_windows_executable(stream_result.get("leading_bytes")):
        try:
            preview = download_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            preview = ""
        try:
            download_path.unlink(missing_ok=True)
        except Exception:
            pass
        preview = " ".join(preview.split())
        if len(preview) > 180:
            preview = preview[:180] + "..."
        return {
            "success": False,
            "message": (
                "The downloaded file is not a valid Windows .exe update package."
                + (f" Preview: {preview}" if preview else "")
            ),
        }

    return {
        "success": True,
        "download_path": str(download_path),
        "file_size": int(stream_result.get("file_size") or download_path.stat().st_size),
    }


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
        "preferred_download_url": _resolve_download_url(payload.get("preferred_download_url")),
        "file_name": normalize_text(payload.get("file_name")),
        "file_size": int(payload.get("file_size") or 0),
        "message": normalize_text(payload.get("message")),
    }


def ensure_update_can_start():
    if not is_frozen_app():
        return {
            "success": False,
            "message": "Auto-update only works in the packaged .exe build.",
        }

    executable_path = get_current_executable_path()
    if executable_path is None or not executable_path.exists():
        return {"success": False, "message": "The current .exe could not be found for update."}

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
            "message": "This folder is not writable, so the app cannot update here.",
        }

    return {"success": True, "executable_path": str(executable_path)}


def download_update_package(update_info, progress_callback=None):
    download_url = normalize_text((update_info or {}).get("download_url"))
    preferred_download_url = normalize_text((update_info or {}).get("preferred_download_url"))
    latest_version = normalize_text((update_info or {}).get("version"))
    candidate_urls = []
    for candidate in (preferred_download_url, download_url):
        normalized_candidate = normalize_text(candidate)
        if normalized_candidate and normalized_candidate not in candidate_urls:
            candidate_urls.append(normalized_candidate)

    if not candidate_urls:
        return {"success": False, "message": "No update download link is available."}

    temp_dir = Path(tempfile.gettempdir()) / "DeltaOneUpdate"
    temp_dir.mkdir(parents=True, exist_ok=True)

    file_name = normalize_text((update_info or {}).get("file_name"))
    if not file_name.lower().endswith(".exe"):
        file_name = f"{Path(DEFAULT_UPDATE_EXE_NAME).stem}-{latest_version or 'latest'}.exe"

    download_path = temp_dir / file_name

    if download_path.exists():
        try:
            download_path.unlink()
        except Exception:
            pass

    errors = []
    with requests.Session() as session:
        for candidate_url in candidate_urls:
            result = _download_from_candidate_url(
                session,
                candidate_url,
                download_path,
                progress_callback=progress_callback,
            )
            if result.get("success"):
                return result
            errors.append(normalize_text(result.get("message")))

    combined_error = " | ".join(message for message in errors if message)
    return {
        "success": False,
        "message": combined_error or "Unable to download the update package.",
    }


def launch_self_update(download_path):
    precheck = ensure_update_can_start()
    if not precheck.get("success"):
        return precheck

    executable_path = Path(precheck["executable_path"])
    source_path = Path(download_path)
    if not source_path.exists():
        return {"success": False, "message": "The downloaded update package could not be found."}

    helper_dir = Path(tempfile.gettempdir()) / "DeltaOneUpdate"
    helper_dir.mkdir(parents=True, exist_ok=True)
    script_path = helper_dir / "apply_update.ps1"
    log_path = helper_dir / "apply_update.log"

    script_content = r"""
param(
    [int]$AppPid,
    [string]$SourcePath,
    [string]$TargetPath,
    [string]$LogPath
)

$ErrorActionPreference = "Stop"
$targetDir = [System.IO.Path]::GetDirectoryName($TargetPath)
$backupPath = "$TargetPath.old"
$deadline = (Get-Date).AddMinutes(3)

function Write-UpdateLog {
    param([string]$Message)
    try {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        Add-Content -LiteralPath $LogPath -Value "$timestamp $Message"
    } catch {
    }
}

function Reset-PyInstallerLaunchEnvironment {
    try {
        Get-ChildItem Env: | Where-Object {
            $_.Name -eq "_MEIPASS2" -or
            $_.Name -like "_PYI_*" -or
            $_.Name -eq "PYINSTALLER_RESET_ENVIRONMENT"
        } | ForEach-Object {
            Remove-Item -LiteralPath "Env:$($_.Name)" -ErrorAction SilentlyContinue
        }
        $env:PYINSTALLER_RESET_ENVIRONMENT = "1"
        Write-UpdateLog "PyInstaller launch environment reset."
    } catch {
        Write-UpdateLog "Unable to reset PyInstaller launch environment: $($_.Exception.Message)"
    }
}

Write-UpdateLog "START pid=$AppPid"
Write-UpdateLog "SOURCE=$SourcePath"
Write-UpdateLog "TARGET=$TargetPath"
Write-UpdateLog "BACKUP=$backupPath"
Write-UpdateLog "TARGET_DIR=$targetDir"

function Start-UpdatedApp {
    param(
        [string]$LaunchPath,
        [string]$LaunchDir
    )

    try {
        Unblock-File -LiteralPath $LaunchPath -ErrorAction SilentlyContinue
    } catch {
    }

    try {
        Reset-PyInstallerLaunchEnvironment
        $launcherPath = Join-Path ([System.IO.Path]::GetDirectoryName($LogPath)) "restart_delta_one.cmd"
        $cmdContent = @"
@echo off
set "_MEIPASS2="
for /f "tokens=1 delims==" %%A in ('set _PYI_ 2^>nul') do set "%%A="
set "PYINSTALLER_RESET_ENVIRONMENT=1"
cd /d "$LaunchDir"
start "" "$LaunchPath"
"@
        Set-Content -LiteralPath $launcherPath -Value $cmdContent -Encoding ASCII
        $launchStartedAt = (Get-Date).AddSeconds(-2)
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/d", "/c", "`"$launcherPath`"") -WindowStyle Hidden -ErrorAction Stop
        Write-UpdateLog "Clean launcher issued: $launcherPath"
        Start-Sleep -Seconds 4
        $processName = [System.IO.Path]::GetFileNameWithoutExtension($LaunchPath)
        $candidate = Get-Process -Name $processName -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $LaunchPath -and $_.StartTime -ge $launchStartedAt } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if ($candidate) {
            Write-UpdateLog "Clean launcher detected pid=$($candidate.Id)."
            return $true
        }
        Write-UpdateLog "Clean launcher did not detect the updated app."
    } catch {
        Write-UpdateLog "Clean launcher failed: $($_.Exception.Message)"
    }

    try {
        Reset-PyInstallerLaunchEnvironment
        $cmdArgs = "/c start `"`" /d `"$LaunchDir`" `"$LaunchPath`""
        $launchStartedAt = (Get-Date).AddSeconds(-2)
        Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WindowStyle Hidden -ErrorAction Stop
        Write-UpdateLog "Fallback cmd launch issued."
        Start-Sleep -Seconds 2
        $processName = [System.IO.Path]::GetFileNameWithoutExtension($LaunchPath)
        $candidate = Get-Process -Name $processName -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $LaunchPath -and $_.StartTime -ge $launchStartedAt } |
            Sort-Object StartTime -Descending |
            Select-Object -First 1
        if ($candidate) {
            Write-UpdateLog "Fallback cmd launch detected pid=$($candidate.Id)."
            return $true
        }
        Write-UpdateLog "Fallback cmd launch not detected as running."
    } catch {
        Write-UpdateLog "Fallback cmd launch failed: $($_.Exception.Message)"
    }

    try {
        Reset-PyInstallerLaunchEnvironment
        Start-Process -FilePath "explorer.exe" -ArgumentList @($LaunchPath) -ErrorAction Stop
        Write-UpdateLog "Explorer launch fallback issued."
        return $true
    } catch {
        Write-UpdateLog "Explorer launch fallback failed: $($_.Exception.Message)"
    }

    return $false
}

while (Get-Process -Id $AppPid -ErrorAction SilentlyContinue) {
    Start-Sleep -Milliseconds 500
    if ((Get-Date) -gt $deadline) {
        Write-UpdateLog "TIMEOUT waiting for app process to exit. Trying force stop."
        try {
            Stop-Process -Id $AppPid -Force -ErrorAction Stop
            Start-Sleep -Seconds 1
            Write-UpdateLog "Force stop succeeded."
            break
        } catch {
            Write-UpdateLog "Force stop failed: $($_.Exception.Message)"
            exit 1
        }
    }
}

Write-UpdateLog "App process exited. Starting replace loop."
Start-Sleep -Seconds 2

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        Write-UpdateLog "Attempt $($attempt + 1): replace begin"

        if (Test-Path -LiteralPath $backupPath) {
            Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
            Write-UpdateLog "Removed stale backup."
        }

        if (Test-Path -LiteralPath $TargetPath) {
            Move-Item -LiteralPath $TargetPath -Destination $backupPath -Force
            Write-UpdateLog "Moved current app to backup."
        }

        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Write-UpdateLog "Copied new file to target."
        Remove-Item -LiteralPath $SourcePath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
        Write-UpdateLog "Cleaned temp source and backup."
        Start-Sleep -Milliseconds 700

        if (Start-UpdatedApp -LaunchPath $TargetPath -LaunchDir $targetDir) {
            Write-UpdateLog "Restarted app successfully."
            exit 0
        }

        Write-UpdateLog "All launch methods failed on this attempt."
    } catch {
        Write-UpdateLog "Attempt $($attempt + 1) failed: $($_.Exception.Message)"
        Start-Sleep -Seconds 1
    }
}

Write-UpdateLog "FAILED after max retries."
exit 1
"""

    try:
        with open(script_path, "w", encoding="utf-8") as script_file:
            script_file.write(script_content.strip() + "\n")
    except Exception as exc:
        return {"success": False, "message": f"Unable to create the update helper script: {exc}"}

    command = [
        "powershell.exe",
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
        "-LogPath",
        str(log_path),
    ]

    creationflags = 0
    for flag_name in (
        "CREATE_NEW_PROCESS_GROUP",
        "CREATE_NO_WINDOW",
        "CREATE_BREAKAWAY_FROM_JOB",
    ):
        creationflags |= int(getattr(subprocess, flag_name, 0) or 0)

    try:
        subprocess.Popen(
            command,
            close_fds=True,
            creationflags=creationflags,
            cwd=str(helper_dir),
            env=_build_clean_update_environment(),
        )
    except Exception as exc:
        return {"success": False, "message": f"Unable to start the update helper: {exc}"}

    return {
        "success": True,
        "message": (
            f"{APP_NAME} is updating and will reopen automatically when it finishes. "
            f"Log: {log_path}"
        ),
    }
