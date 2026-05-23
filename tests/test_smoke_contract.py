import unittest
from pathlib import Path
from unittest.mock import patch

import server


class _FakeServer:
    def __init__(self):
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)


class _FailingRuntime:
    async def dispatch(self, name, args):
        raise RuntimeError(f"boom: {name} {args['example']}")


class SmokeContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_manifest_prefers_last_duplicate_tool_definition(self):
        manifest_a = Path("C:/tmp/tool_manifest_google_a.json")
        manifest_b = Path("C:/tmp/tool_manifest_google_b.json")

        def _fake_read_text(self, encoding="utf-8"):
            if self == manifest_a:
                return '{"tools":[{"name":"duplicate_tool","description":"first","parameters":{"type":"object"}}]}'
            if self == manifest_b:
                return '{"tools":[{"name":"duplicate_tool","description":"second","parameters":{"type":"object"}}]}'
            raise AssertionError(f"unexpected manifest read: {self}")

        with patch.object(server, "_repo_root", return_value=Path("C:/tmp")), patch.object(
            Path,
            "glob",
            return_value=[manifest_a, manifest_b],
        ), patch.object(Path, "exists", return_value=True), patch.object(Path, "read_text", _fake_read_text):
            manifest = server._load_manifest()

        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["description"], "second")

    async def test_manifest_unique_tool_count_matches_documented_inventory(self):
        self.assertEqual(len(server.manifest), 53)

    async def test_register_tools_registers_every_manifest_entry(self):
        fake_server = _FakeServer()
        runtime = _FailingRuntime()

        server._register_tools(fake_server, runtime, server.manifest)

        self.assertEqual(len(fake_server.tools), len(server.manifest))

    async def test_registered_tool_returns_structured_error_payload(self):
        fake_server = _FakeServer()
        runtime = _FailingRuntime()
        manifest = [
            {
                "name": "example_tool",
                "description": "desc",
                "parameters": {"type": "object", "properties": {"example": {"type": "string"}}},
            }
        ]

        server._register_tools(fake_server, runtime, manifest)

        result = await fake_server.tools[0].fn(example="value")

        self.assertEqual(
            result,
            {"isError": True, "error": "boom: example_tool value"},
        )
