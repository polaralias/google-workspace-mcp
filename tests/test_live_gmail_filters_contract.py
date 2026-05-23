import unittest
import uuid

from tests.live_harness import live_runtime, require_live_scopes


class GmailFiltersLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_gmail_filter_create_list_delete_lifecycle(self):
        config = require_live_scopes(self, ["https://www.googleapis.com/auth/gmail.settings.basic"])

        with live_runtime(config) as runtime:
            marker = "codex-live-filter-" + uuid.uuid4().hex[:8]
            filter_id = None
            deleted = False

            async def cleanup():
                if filter_id and not deleted:
                    await runtime.dispatch("delete_gmail_filter", {"filter_id": filter_id})

            existing = await runtime.dispatch("list_gmail_filters", {})
            self.assertIsInstance(existing.get("filters", []), list)

            created = await runtime.dispatch(
                "create_gmail_filter",
                {
                    "criteria": {"query": marker},
                    "action": {"removeLabelIds": ["INBOX"]},
                },
            )
            filter_id = created["filter"]["id"]
            self.addAsyncCleanup(cleanup)

            listed = await runtime.dispatch("list_gmail_filters", {})
            self.assertTrue(any(item["id"] == filter_id for item in listed.get("filters", [])))

            deleted_result = await runtime.dispatch("delete_gmail_filter", {"filter_id": filter_id})
            deleted = True

        self.assertTrue(deleted_result["deleted"])
        self.assertEqual(deleted_result["filterId"], filter_id)
