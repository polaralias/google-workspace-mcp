import unittest
import uuid

from tests.live_harness import live_runtime, require_live_google_workspace


class DriveLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_drive_folder_and_file_lifecycle_with_owned_artifact_cleanup(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            marker = "codex-live-drive-" + uuid.uuid4().hex[:8]
            folder_id = None
            file_id = None
            deleted_file = False
            deleted_folder = False

            async def cleanup():
                if file_id and not deleted_file:
                    await runtime.dispatch("delete_drive_file", {"file_id": file_id})
                if folder_id and not deleted_folder:
                    await runtime.dispatch("delete_drive_file", {"file_id": folder_id})

            root_items = await runtime.dispatch("list_drive_items", {})
            self.assertIsInstance(root_items.get("files", []), list)

            created_folder = await runtime.dispatch("create_drive_folder", {"folder_name": marker})
            folder_id = created_folder["folder"]["id"]
            self.addAsyncCleanup(cleanup)

            folder_items = await runtime.dispatch("list_drive_items", {"folder_id": folder_id})
            self.assertEqual(folder_items.get("files", []), [])

            created_file = await runtime.dispatch(
                "create_drive_file",
                {
                    "folder_id": folder_id,
                    "file_name": marker + ".txt",
                    "content": "hello from live drive",
                    "mime_type": "text/plain",
                },
            )
            file_id = created_file["file"]["id"]

            file_content = await runtime.dispatch("get_drive_file_content", {"file_id": file_id})
            self.assertEqual(file_content["content"], "hello from live drive")

            search_result = await runtime.dispatch("search_drive_files", {"query": marker})
            self.assertTrue(any(item["id"] == file_id for item in search_result.get("files", [])))

            deleted_file_result = await runtime.dispatch("delete_drive_file", {"file_id": file_id})
            deleted_file = True
            deleted_folder_result = await runtime.dispatch("delete_drive_file", {"file_id": folder_id})
            deleted_folder = True

        self.assertTrue(deleted_file_result["deleted"])
        self.assertTrue(deleted_folder_result["deleted"])
