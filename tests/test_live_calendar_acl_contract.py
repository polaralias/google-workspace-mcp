import unittest
import uuid
from datetime import datetime, timedelta, timezone

from tests.live_harness import live_google_client, live_runtime, require_live_scopes


class CalendarAclLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendar_acl_and_free_busy_on_owned_calendar(self):
        config = require_live_scopes(self, ["https://www.googleapis.com/auth/calendar"])
        calendar_client = live_google_client(config, "calendar", "v3")

        with live_runtime(config) as runtime:
            marker = "codex-live-acl-" + uuid.uuid4().hex[:8]
            calendar_id = None
            rule_id = None
            deleted_rule = False

            async def cleanup():
                if rule_id and calendar_id and not deleted_rule:
                    await runtime.dispatch("delete_calendar_acl_rule", {"calendar_id": calendar_id, "rule_id": rule_id})
                if calendar_id:
                    calendar_client.calendars().delete(calendarId=calendar_id).execute()

            created_calendar = calendar_client.calendars().insert(body={"summary": marker}).execute()
            calendar_id = created_calendar["id"]
            self.addAsyncCleanup(cleanup)

            rules_before = await runtime.dispatch("list_calendar_acl", {"calendar_id": calendar_id})
            self.assertIsInstance(rules_before.get("rules", []), list)

            created_rule = await runtime.dispatch(
                "create_calendar_acl_rule",
                {
                    "calendar_id": calendar_id,
                    "role": "freeBusyReader",
                    "scope_type": "default",
                    "scope_value": "default",
                },
            )
            rule_id = created_rule["rule"]["id"]

            rules_after = await runtime.dispatch("list_calendar_acl", {"calendar_id": calendar_id})
            self.assertTrue(any(item["id"] == rule_id for item in rules_after.get("rules", [])))

            start = datetime.now(timezone.utc).replace(microsecond=0)
            end = start + timedelta(hours=1)
            free_busy = await runtime.dispatch(
                "get_free_busy",
                {
                    "time_min": start.isoformat().replace("+00:00", "Z"),
                    "time_max": end.isoformat().replace("+00:00", "Z"),
                    "items": [calendar_id],
                },
            )

            deleted_rule_result = await runtime.dispatch(
                "delete_calendar_acl_rule",
                {"calendar_id": calendar_id, "rule_id": rule_id},
            )
            deleted_rule = True

        self.assertIn(calendar_id, free_busy["freeBusy"].get("calendars", {}))
        self.assertTrue(deleted_rule_result["deleted"])
        self.assertEqual(deleted_rule_result["ruleId"], rule_id)
