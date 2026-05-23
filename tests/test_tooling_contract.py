import re
import unittest
from pathlib import Path

import tool_support
from scripts.render_tool_reference import render_tool_reference


class ToolingContractTests(unittest.TestCase):
    def test_manifest_inventory_matches_runtime_dispatch_inventory(self):
        manifest_names = tool_support.manifest_tool_names()
        runtime_names = tool_support.runtime_tool_names()

        self.assertEqual(manifest_names - runtime_names, set())

    def test_tool_support_rows_cover_manifest_inventory_with_allowed_statuses(self):
        manifest_names = tool_support.manifest_tool_names()
        rows = tool_support.tool_support_rows()
        row_names = {row["tool_name"] for row in rows}

        self.assertEqual(row_names, manifest_names)
        self.assertEqual(len(rows), len(manifest_names))
        self.assertTrue(all(row["status"] in tool_support.ALLOWED_SUPPORT_STATUSES for row in rows))
        self.assertTrue(all(row["status"] != "untested" for row in rows))

    def test_tool_reference_inventory_matches_manifest_inventory(self):
        content = Path("docs/tool-reference.md").read_text(encoding="utf-8")
        documented_names = set(re.findall(r"^### `([^`]+)`$", content, flags=re.MULTILINE))

        self.assertEqual(documented_names, tool_support.manifest_tool_names())

    def test_rendered_tool_reference_matches_generated_file(self):
        rendered = render_tool_reference()
        recorded = Path("docs/tool-reference.md").read_text(encoding="utf-8")

        self.assertEqual(recorded, rendered)

    def test_rendered_tool_support_matrix_matches_generated_file(self):
        rendered = tool_support.render_tool_support_matrix()
        recorded = Path("docs/generated/tool-support-matrix.md").read_text(encoding="utf-8")

        self.assertEqual(recorded, rendered)

    def test_public_manifest_excludes_unverified_gmail_message_mutation_tools(self):
        manifest_names = tool_support.manifest_tool_names()

        for tool_name in [
            "archive_gmail_message",
            "trash_gmail_message",
            "mark_gmail_read_unread",
            "star_unstar_gmail_message",
        ]:
            self.assertNotIn(tool_name, manifest_names)

    def test_contacts_search_contract_is_explicitly_cache_refresh_limited(self):
        rows = {row["tool_name"]: row for row in tool_support.tool_support_rows()}

        self.assertEqual(rows["search_contacts"]["status"], "verified limited")
        self.assertIn("warmup", rows["search_contacts"]["known_limitations"].lower())
