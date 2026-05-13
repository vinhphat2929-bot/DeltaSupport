import unittest

from services import update_service


class FakeResponse:
    def __init__(self, text="", content_type="text/html; charset=utf-8"):
        self.text = text
        self.headers = {"Content-Type": content_type}


class UpdateServiceTests(unittest.TestCase):
    def test_extract_google_drive_file_id_from_share_link(self):
        file_id = update_service._extract_google_drive_file_id(
            "https://drive.google.com/file/d/1mz74VbVrrKHFKP2Cy9dFnbmTUaREzLyU/view?usp=drive_link"
        )
        self.assertEqual("1mz74VbVrrKHFKP2Cy9dFnbmTUaREzLyU", file_id)

    def test_normalize_download_candidate_url_converts_drive_share_link(self):
        normalized_url = update_service._normalize_download_candidate_url(
            "https://drive.google.com/file/d/1mz74VbVrrKHFKP2Cy9dFnbmTUaREzLyU/view?usp=drive_link"
        )
        self.assertEqual(
            "https://drive.google.com/uc?export=download&id=1mz74VbVrrKHFKP2Cy9dFnbmTUaREzLyU",
            normalized_url,
        )

    def test_extract_google_drive_confirm_request(self):
        response = FakeResponse(
            text=(
                '<html><body><form id="download-form" '
                'action="https://drive.usercontent.google.com/download" method="get">'
                '<input type="hidden" name="id" value="abc123">'
                '<input type="hidden" name="export" value="download">'
                '<input type="hidden" name="confirm" value="t">'
                '<input type="hidden" name="uuid" value="uuid-123">'
                "</form></body></html>"
            )
        )

        action_url, params = update_service._extract_google_drive_confirm_request(response)
        self.assertEqual("https://drive.usercontent.google.com/download", action_url)
        self.assertEqual(
            {
                "id": "abc123",
                "export": "download",
                "confirm": "t",
                "uuid": "uuid-123",
            },
            params,
        )

    def test_looks_like_windows_executable(self):
        self.assertTrue(update_service._looks_like_windows_executable(b"MZ\x90\x00"))
        self.assertFalse(update_service._looks_like_windows_executable(b"<!DO"))


if __name__ == "__main__":
    unittest.main()
