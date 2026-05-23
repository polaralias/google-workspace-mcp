import unittest

from tests.live_harness import live_runtime, maybe_skip_http_error, require_live_scopes


class MeetLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_meet_conference_record_list_and_optional_get(self):
        config = require_live_scopes(self, ["https://www.googleapis.com/auth/meetings.space.readonly"])

        with live_runtime(config) as runtime:
            try:
                listed = await runtime.dispatch("list_conference_records", {})
            except Exception as exc:
                maybe_skip_http_error(self, exc, "Google Meet conference-record access unavailable")

            self.assertIsInstance(listed.get("conferenceRecords", []), list)

            if listed.get("conferenceRecords"):
                first_name = listed["conferenceRecords"][0]["name"]
                fetched = await runtime.dispatch("get_conference_record", {"name": first_name})
                self.assertEqual(fetched["conferenceRecord"]["name"], first_name)
