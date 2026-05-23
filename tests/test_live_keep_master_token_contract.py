import warnings
import unittest
import uuid

from tests.live_harness import live_runtime, require_live_keep_master_token


warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"ssl\.SSLContext\(\) without protocol argument is deprecated\.")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"ssl\.PROTOCOL_TLS is deprecated")


class KeepMasterTokenLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_keep_master_token_create_read_update_delete_lifecycle(self):
        config = require_live_keep_master_token(self)

        with live_runtime(
            config,
            extra_env={
                "GOOGLE_KEEP_EMAIL": config["keep_email"],
                "GOOGLE_KEEP_MASTER_TOKEN": config["keep_token"],
            },
        ) as runtime:
            marker = "codex-live-keep-" + uuid.uuid4().hex[:8]
            note_name = None
            deleted = False

            async def cleanup():
                if note_name and not deleted:
                    await runtime.dispatch("delete_keep_note", {"note_name": note_name})

            labels = await runtime.dispatch("list_keep_labels", {})
            self.assertIsInstance(labels.get("labels", []), list)

            created = await runtime.dispatch("create_keep_note", {"title": marker, "text": "hello keep"})
            note_name = created["note"]["name"]
            self.addAsyncCleanup(cleanup)

            read_before = await runtime.dispatch("get_keep_note", {"note_name": note_name})
            self.assertEqual(read_before["note"]["title"], marker)

            updated = await runtime.dispatch(
                "update_keep_note",
                {"note_name": note_name, "title": marker + "-updated", "text": "updated keep"},
            )
            self.assertEqual(updated["note"]["title"], marker + "-updated")

            deleted_result = await runtime.dispatch("delete_keep_note", {"note_name": note_name})
            deleted = True

        self.assertTrue(deleted_result["deleted"])
        self.assertEqual(deleted_result["noteName"], note_name)
