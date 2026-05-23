import unittest
from unittest.mock import patch

import httplib2
from googleapiclient.errors import HttpError

import server


class _FakeStore:
    def get(self, _email):
        return object()


class _FakeExecute:
    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class _FakeDriveFiles:
    def __init__(self):
        self.create_kwargs = None
        self.list_kwargs = None
        self.create_calls = 0

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        self.create_calls += 1
        return _FakeExecute({"id": "file-123", "name": kwargs["body"]["name"]})

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        return _FakeExecute({"files": [{"id": "file-123", "name": "notes.txt"}]})

    def get_media(self, **kwargs):
        return _FakeExecute(b"hello from drive")

    def get(self, **kwargs):
        if kwargs.get("alt") == "media":
            return _FakeExecute({"unexpected": "metadata"})
        return _FakeExecute({"id": kwargs["fileId"], "mimeType": "text/plain", "name": "notes.txt"})


class _FakeDriveService:
    def __init__(self):
        self._files = _FakeDriveFiles()

    def files(self):
        return self._files


class _RetryExecute:
    def __init__(self):
        self.calls = 0

    def execute(self):
        self.calls += 1
        if self.calls == 1:
            raise HttpError(httplib2.Response({"status": "500"}), b'[{"message":"Unknown Error."}]')
        return {"id": "folder-123", "name": "folder", "mimeType": "application/vnd.google-apps.folder", "parents": ["root"]}


class _RetryDriveFiles(_FakeDriveFiles):
    def __init__(self):
        super().__init__()
        self.request = _RetryExecute()

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        self.create_calls += 1
        return self.request


class _RetryDriveService:
    def __init__(self):
        self._files = _RetryDriveFiles()

    def files(self):
        return self._files


class DriveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_drive_files_normalizes_plain_text_queries_for_full_text_search(self):
        runtime = server.GoogleRuntime(_FakeStore())
        drive = _FakeDriveService()

        with patch.object(runtime, "_svc", return_value=drive):
            result = await runtime.dispatch(
                "search_drive_files",
                {
                    "user_google_email": "user@example.com",
                    "query": "O'Hare notes",
                },
            )

        self.assertEqual(result["files"][0]["id"], "file-123")
        self.assertEqual(
            drive.files().list_kwargs["q"],
            "fullText contains 'O\\'Hare notes'",
        )

    async def test_create_drive_file_uploads_text_content_instead_of_passing_raw_string(self):
        runtime = server.GoogleRuntime(_FakeStore())
        drive = _FakeDriveService()

        with patch.object(runtime, "_svc", return_value=drive), patch.object(
            runtime, "_resolve_folder", return_value="folder-123"
        ):
            result = await runtime.dispatch(
                "create_drive_file",
                {
                    "user_google_email": "user@example.com",
                    "file_name": "notes.txt",
                    "folder_id": "root",
                    "content": "hello from drive",
                    "mime_type": "text/plain",
                },
            )

        self.assertTrue(result["created"])
        self.assertIsNotNone(drive.files().create_kwargs)
        self.assertNotIsInstance(drive.files().create_kwargs["media_body"], str)

    async def test_get_drive_file_content_reads_media_bytes_for_plain_files(self):
        runtime = server.GoogleRuntime(_FakeStore())
        drive = _FakeDriveService()

        with patch.object(runtime, "_svc", return_value=drive), patch.object(
            runtime,
            "_resolve_drive_item",
            return_value=("file-123", {"id": "file-123", "mimeType": "text/plain", "name": "notes.txt"}),
        ):
            result = await runtime.dispatch(
                "get_drive_file_content",
                {
                    "user_google_email": "user@example.com",
                    "file_id": "file-123",
                },
            )

        self.assertEqual(result["content"], "hello from drive")
        self.assertEqual(result["resolvedId"], "file-123")

    async def test_create_drive_folder_retries_transient_drive_500s(self):
        runtime = server.GoogleRuntime(_FakeStore())
        drive = _RetryDriveService()

        with patch.object(runtime, "_svc", return_value=drive), patch.object(
            runtime, "_resolve_folder", return_value="root"
        ):
            result = await runtime.dispatch(
                "create_drive_folder",
                {
                    "user_google_email": "user@example.com",
                    "folder_name": "folder",
                },
            )

        self.assertTrue(result["created"])
        self.assertEqual(result["folder"]["id"], "folder-123")
        self.assertEqual(drive.files().request.calls, 2)
