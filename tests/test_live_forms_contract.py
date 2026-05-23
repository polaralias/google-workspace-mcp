import unittest
import uuid

from tests.live_harness import live_google_client, live_runtime, maybe_skip_http_error, require_live_scopes


class FormsLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_forms_batch_update_on_owned_form(self):
        config = require_live_scopes(self, ["https://www.googleapis.com/auth/forms.body"])
        forms_client = live_google_client(config, "forms", "v1")

        with live_runtime(config) as runtime:
            marker = "codex-live-form-" + uuid.uuid4().hex[:8]
            form_id = None
            deleted = False

            async def cleanup():
                if form_id and not deleted:
                    await runtime.dispatch("delete_drive_file", {"file_id": form_id})

            try:
                created = forms_client.forms().create(body={"info": {"title": marker}}).execute()
            except Exception as exc:
                maybe_skip_http_error(self, exc, "Google Forms create unavailable for current credential or project")
            form_id = created["formId"]
            self.addAsyncCleanup(cleanup)

            updated = await runtime.dispatch(
                "batch_update_form",
                {
                    "form_id": form_id,
                    "requests": [
                        {
                            "createItem": {
                                "item": {
                                    "title": "Validation question",
                                    "questionItem": {
                                        "question": {
                                            "required": False,
                                            "textQuestion": {},
                                        }
                                    },
                                },
                                "location": {"index": 0},
                            }
                        }
                    ],
                    "include_form_in_response": True,
                },
            )

            form = forms_client.forms().get(formId=form_id).execute()
            deleted_result = await runtime.dispatch("delete_drive_file", {"file_id": form_id})
            deleted = True

        self.assertTrue(updated["updated"])
        self.assertEqual(form["info"]["title"], marker)
        self.assertGreaterEqual(len(form.get("items", [])), 1)
        self.assertTrue(deleted_result["deleted"])
