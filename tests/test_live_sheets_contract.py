import unittest
import uuid

from tests.live_harness import live_google_client, live_runtime, require_live_scopes


class SheetsLiveContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_sheets_write_and_read_lifecycle_on_owned_spreadsheet(self):
        config = require_live_scopes(self, ["https://www.googleapis.com/auth/spreadsheets"])
        sheets_client = live_google_client(config, "sheets", "v4")

        with live_runtime(config) as runtime:
            marker = "codex-live-sheet-" + uuid.uuid4().hex[:8]
            spreadsheet_id = None
            deleted = False

            async def cleanup():
                if spreadsheet_id and not deleted:
                    await runtime.dispatch("delete_drive_file", {"file_id": spreadsheet_id})

            spreadsheet = sheets_client.spreadsheets().create(
                body={"properties": {"title": marker}, "sheets": [{"properties": {"title": "Sheet1"}}]}
            ).execute()
            spreadsheet_id = spreadsheet["spreadsheetId"]
            self.addAsyncCleanup(cleanup)

            updated = await runtime.dispatch(
                "modify_sheet_values",
                {
                    "spreadsheet_id": spreadsheet_id,
                    "range_name": "Sheet1!A1:B2",
                    "values": [["Name", "Value"], ["alpha", "1"]],
                },
            )
            self.assertTrue(updated["updated"])

            appended = await runtime.dispatch(
                "append_sheet_rows",
                {
                    "spreadsheet_id": spreadsheet_id,
                    "range_name": "Sheet1!A1:B10",
                    "values": [["beta", "2"]],
                },
            )
            self.assertTrue(appended["appended"])

            batch_updated = await runtime.dispatch(
                "batch_update_sheet_values",
                {
                    "spreadsheet_id": spreadsheet_id,
                    "data": [
                        {"range": "Sheet1!D1:E2", "values": [["Flag", "State"], ["gamma", "3"]]},
                    ],
                    "include_values_in_response": True,
                },
            )
            self.assertTrue(batch_updated["updated"])

            read_back = await runtime.dispatch(
                "read_sheet_values",
                {"spreadsheet_id": spreadsheet_id, "range_name": "Sheet1!A1:B5"},
            )
            batch_read = await runtime.dispatch(
                "batch_get_sheet_values",
                {"spreadsheet_id": spreadsheet_id, "ranges": ["Sheet1!A1:B5", "Sheet1!D1:E2"]},
            )

            deleted_result = await runtime.dispatch("delete_drive_file", {"file_id": spreadsheet_id})
            deleted = True

        self.assertEqual(read_back["values"][1], ["alpha", "1"])
        self.assertEqual(read_back["values"][2], ["beta", "2"])
        self.assertEqual(batch_read["valueRanges"][1]["values"][1], ["gamma", "3"])
        self.assertTrue(deleted_result["deleted"])
