import unittest
from unittest.mock import patch

import server


class _FakeStore:
    def get(self, _email):
        return object()


class _FakeDriveFiles:
    def get_media(self, **kwargs):
        class _Execute:
            def execute(self_inner):
                return b"portable"

        return _Execute()


class _FakeDriveService:
    def files(self):
        return _FakeDriveFiles()


class KeepPortabilityContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_keep_dispatch_does_not_require_gkeepapi_import(self):
        runtime = server.GoogleRuntime(_FakeStore())

        with patch.object(server, "_load_gkeepapi", side_effect=ModuleNotFoundError("gkeepapi")):
            with patch.object(runtime, "_svc", return_value=_FakeDriveService()), patch.object(
                runtime,
                "_resolve_drive_item",
                return_value=("file-123", {"id": "file-123", "mimeType": "text/plain", "name": "notes.txt"}),
            ):
                result = await runtime.dispatch(
                    "get_drive_file_content",
                    {"user_google_email": "user@example.com", "file_id": "file-123"},
                )

        self.assertEqual(result["content"], "portable")

    async def test_keep_tools_fail_with_clear_error_when_gkeepapi_is_unavailable(self):
        runtime = server.GoogleRuntime(_FakeStore())
        runtime._keep_master_token._master_token = "token"
        runtime._keep_master_token._email = "user@example.com"

        with patch.object(server.importlib, "import_module", side_effect=ModuleNotFoundError("gkeepapi")):
            server._GKEEPAPI_MODULE = None
            with self.assertRaises(RuntimeError) as exc:
                await runtime.dispatch(
                    "list_keep_labels",
                    {"user_google_email": "user@example.com"},
                )

        self.assertIn("gkeepapi", str(exc.exception))
