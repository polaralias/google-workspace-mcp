import unittest
import uuid

from tests.live_harness import live_runtime, require_live_google_workspace


class SlidesLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_slides_create_read_add_slide_delete_lifecycle(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            marker = "codex-live-slides-" + uuid.uuid4().hex[:8]
            presentation_id = None
            deleted = False

            async def cleanup():
                if presentation_id and not deleted:
                    await runtime.dispatch("delete_drive_file", {"file_id": presentation_id})

            created = await runtime.dispatch("create_presentation", {"title": marker})
            presentation_id = created["presentation"]["presentationId"]
            self.addAsyncCleanup(cleanup)

            read_before = await runtime.dispatch("get_presentation", {"presentation_id": presentation_id})
            initial_count = len(read_before.get("slides", []))

            await runtime.dispatch("create_slide", {"presentation_id": presentation_id})
            read_after = await runtime.dispatch("get_presentation", {"presentation_id": presentation_id})

            deleted_result = await runtime.dispatch("delete_drive_file", {"file_id": presentation_id})
            deleted = True

        self.assertGreaterEqual(initial_count, 1)
        self.assertEqual(len(read_after.get("slides", [])), initial_count + 1)
        self.assertTrue(deleted_result["deleted"])
