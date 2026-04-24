import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.responses import FileResponse

from backend_server.routers import app_update


class FakeRequest:
    def __init__(self, base_url="http://testserver/"):
        self.base_url = base_url


class AppUpdateRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "app_update_config.json"
        self.release_path = Path(self.temp_dir.name) / "delta-one.exe"
        self.release_path.write_bytes(b"delta-one-update")

        self.original_config_env = os.environ.get(app_update.APP_UPDATE_CONFIG_ENV_VAR)
        os.environ[app_update.APP_UPDATE_CONFIG_ENV_VAR] = str(self.config_path)

    def tearDown(self):
        if self.original_config_env is None:
            os.environ.pop(app_update.APP_UPDATE_CONFIG_ENV_VAR, None)
        else:
            os.environ[app_update.APP_UPDATE_CONFIG_ENV_VAR] = self.original_config_env
        self.temp_dir.cleanup()

    def write_config(self, **overrides):
        payload = {
            "version": "2026.4.25.2",
            "release_notes": "Bug fixes",
            "minimum_supported_version": "",
            "published_at": "2026-04-25 03:00:00",
            "mandatory": False,
            "windows_exe_path": str(self.release_path),
        }
        payload.update(overrides)
        self.config_path.write_text(json.dumps(payload), encoding="utf-8")

    def test_manifest_reports_update_available(self):
        self.write_config()
        config_payload = app_update._load_app_update_config()

        payload = app_update._build_update_payload(
            config_payload,
            FakeRequest(),
            current_version="2026.4.25.1",
        )
        self.assertTrue(payload["success"])
        self.assertTrue(payload["update_available"])
        self.assertEqual("2026.4.25.2", payload["version"])
        self.assertTrue(payload["download_url"].endswith("/app-update/download"))
        self.assertEqual(self.release_path.name, payload["file_name"])

    def test_manifest_reports_no_update_when_not_configured(self):
        self.write_config(windows_exe_path="")
        config_payload = app_update._load_app_update_config()

        payload = app_update._build_update_payload(
            config_payload,
            FakeRequest(),
            current_version="2026.4.25.1",
        )
        self.assertTrue(payload["success"])
        self.assertFalse(payload["update_available"])
        self.assertEqual("", payload["download_url"])

    def test_download_endpoint_returns_release_file(self):
        self.write_config()

        response = app_update.download_app_update()
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(str(self.release_path), str(response.path))


if __name__ == "__main__":
    unittest.main()
