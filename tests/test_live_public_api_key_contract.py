import unittest
import uuid

from tests.live_harness import api_key_runtime, live_google_clients, live_runtime, require_live_api_key, require_live_google_workspace


class PublicApiKeyLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_key_public_read_slice_on_owned_public_artifacts(self):
        oauth_config = require_live_google_workspace(self)
        api_key_config = require_live_api_key(self)

        clients = live_google_clients(oauth_config)
        drive_client = clients["drive"]
        sheets_client = clients["sheets"]

        with live_runtime(oauth_config) as oauth_runtime:
            marker = "codex-live-public-" + uuid.uuid4().hex[:8]
            text_file_id = None
            spreadsheet_id = None
            presentation_id = None

            async def cleanup():
                for file_id in (text_file_id, spreadsheet_id, presentation_id):
                    if file_id:
                        await oauth_runtime.dispatch("delete_drive_file", {"file_id": file_id})

            self.addAsyncCleanup(cleanup)

            created_file = await oauth_runtime.dispatch(
                "create_drive_file",
                {
                    "file_name": marker + ".txt",
                    "content": "hello from public api key",
                    "mime_type": "text/plain",
                },
            )
            text_file_id = created_file["file"]["id"]
            drive_client.permissions().create(fileId=text_file_id, body={"type": "anyone", "role": "reader"}).execute()

            spreadsheet = sheets_client.spreadsheets().create(
                body={"properties": {"title": marker + "-sheet"}, "sheets": [{"properties": {"title": "Sheet1"}}]}
            ).execute()
            spreadsheet_id = spreadsheet["spreadsheetId"]
            sheets_client.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1:B2",
                valueInputOption="RAW",
                body={"values": [["Name", "Value"], ["alpha", "42"]]},
            ).execute()
            drive_client.permissions().create(fileId=spreadsheet_id, body={"type": "anyone", "role": "reader"}).execute()

            created_presentation = await oauth_runtime.dispatch("create_presentation", {"title": marker + "-slides"})
            presentation_id = created_presentation["presentation"]["presentationId"]
            drive_client.permissions().create(fileId=presentation_id, body={"type": "anyone", "role": "reader"}).execute()

        with api_key_runtime(api_key_config) as api_runtime:
            public_file = await api_runtime.dispatch("get_drive_file_content", {"file_id": text_file_id})
            public_permissions = await api_runtime.dispatch("get_drive_file_permissions", {"file_id": text_file_id})
            sheet_info = await api_runtime.dispatch("get_spreadsheet_info", {"spreadsheet_id": spreadsheet_id})
            sheet_values = await api_runtime.dispatch(
                "read_sheet_values", {"spreadsheet_id": spreadsheet_id, "range_name": "Sheet1!A1:B5"}
            )
            presentation_pdf = await api_runtime.dispatch(
                "export_presentation_pdf", {"presentation_id": presentation_id}
            )

        self.assertEqual(public_file["content"], "hello from public api key")
        self.assertEqual(public_permissions["file"]["id"], text_file_id)
        self.assertEqual(sheet_info["spreadsheet"]["spreadsheetId"], spreadsheet_id)
        self.assertEqual(sheet_values["values"][1], ["alpha", "42"])
        self.assertEqual(presentation_pdf["presentationId"], presentation_id)
        self.assertEqual(presentation_pdf["contentEncoding"], "base64")
