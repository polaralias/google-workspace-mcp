import unittest
import uuid
from datetime import datetime, timedelta, timezone

from tests.live_harness import live_runtime, require_live_google_workspace


class CalendarLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_calendar_create_get_delete_lifecycle_uses_owned_artifact_cleanup(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            calendars = await runtime.dispatch("list_calendars", {})
            primary = next((item for item in calendars["calendars"] if item.get("primary")), None)
            self.assertIsNotNone(primary, "expected a primary calendar for live validation")

            marker = "codex-live-cal-" + uuid.uuid4().hex[:8]
            start = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(microsecond=0)
            end = start + timedelta(minutes=30)
            deleted = False
            event_id = None

            async def cleanup():
                if event_id and not deleted:
                    await runtime.dispatch(
                        "delete_event",
                        {"calendar_id": primary["id"], "event_id": event_id},
                    )

            created = await runtime.dispatch(
                "create_event",
                {
                    "calendar_id": primary["id"],
                    "summary": marker,
                    "start_time": start.isoformat().replace("+00:00", "Z"),
                    "end_time": end.isoformat().replace("+00:00", "Z"),
                    "description": "created during live contract validation",
                },
            )
            event_id = created["event"]["id"]
            self.addAsyncCleanup(cleanup)

            fetched = await runtime.dispatch(
                "get_events",
                {"calendar_id": primary["id"], "event_id": event_id},
            )
            self.assertEqual(fetched["event"]["summary"], marker)

            deleted_result = await runtime.dispatch(
                "delete_event",
                {"calendar_id": primary["id"], "event_id": event_id},
            )
            deleted = True

        self.assertTrue(deleted_result["deleted"])
        self.assertEqual(deleted_result["eventId"], event_id)
