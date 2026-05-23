import asyncio
import unittest
import uuid

from tests.live_harness import live_runtime, require_live_google_workspace


class ContactsLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_contacts_create_update_delete_and_search_contract(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            marker = "codex-live-contact-" + uuid.uuid4().hex[:8]
            resource_name = None
            deleted = False

            async def cleanup():
                if resource_name and not deleted:
                    await runtime.dispatch("delete_contact", {"resource_name": resource_name})

            contacts = await runtime.dispatch("list_contacts", {"page_size": 10})
            self.assertIsInstance(contacts.get("contacts", []), list)

            created = await runtime.dispatch(
                "create_contact",
                {
                    "person": {
                        "names": [{"givenName": marker, "familyName": "Validation"}],
                        "emailAddresses": [{"value": marker + "@example.com"}],
                    }
                },
            )
            resource_name = created["person"]["resourceName"]
            self.addAsyncCleanup(cleanup)

            updated = await runtime.dispatch(
                "update_contact",
                {
                    "resource_name": resource_name,
                    "person": {
                        "names": [{"givenName": marker + "-updated", "familyName": "Validation"}],
                        "emailAddresses": [{"value": marker + "@example.com"}],
                    },
                    "update_person_fields": "names,emailAddresses",
                },
            )
            self.assertIn(marker + "-updated", (updated["person"].get("names") or [{}])[0].get("displayName", ""))

            search_results = []
            for _ in range(5):
                searched = await runtime.dispatch("search_contacts", {"query": marker})
                search_results = searched.get("results", [])
                if any((item.get("person") or {}).get("resourceName") == resource_name for item in search_results):
                    break
                await asyncio.sleep(2)

            deleted_result = await runtime.dispatch("delete_contact", {"resource_name": resource_name})
            deleted = True

        self.assertTrue(deleted_result["deleted"])
        self.assertEqual(deleted_result["resourceName"], resource_name)
        self.assertTrue(
            any((item.get("person") or {}).get("resourceName") == resource_name for item in search_results),
            "expected search_contacts to find the owned contact after cache warmup and bounded retries",
        )
