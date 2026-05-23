import unittest
import uuid

from tests.live_harness import live_runtime, require_live_google_workspace


class DocsLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_docs_create_read_update_delete_lifecycle_uses_owned_artifact_cleanup(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            marker = "codex-live-doc-" + uuid.uuid4().hex[:8]
            document_id = None
            deleted = False

            async def cleanup():
                if document_id and not deleted:
                    await runtime.dispatch("delete_drive_file", {"file_id": document_id})

            created = await runtime.dispatch("create_doc", {"title": marker, "content": "hello"})
            document_id = created["document"]["documentId"]
            self.addAsyncCleanup(cleanup)

            read_before = await runtime.dispatch("get_doc_content", {"document_id": document_id})
            self.assertEqual(read_before["text"].strip(), "hello")

            await runtime.dispatch("modify_doc_text", {"document_id": document_id, "text": " world", "index": 6})

            read_after = await runtime.dispatch("get_doc_content", {"document_id": document_id})
            self.assertEqual(read_after["text"].strip(), "hello world")

            deleted_result = await runtime.dispatch("delete_drive_file", {"file_id": document_id})
            deleted = True

        self.assertTrue(deleted_result["deleted"])
        self.assertEqual(deleted_result["fileId"], document_id)
