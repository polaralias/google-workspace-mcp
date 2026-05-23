import unittest

from tests.live_harness import live_runtime, require_live_google_workspace


class GmailLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_gmail_search_executes_in_oauth_mode(self):
        config = require_live_google_workspace(self)

        with live_runtime(config) as runtime:
            result = await runtime.dispatch("search_gmail_messages", {"query": "in:anywhere newer_than:30d"})

        self.assertIn("messages", result)
        self.assertIsInstance(result["messages"], list)
