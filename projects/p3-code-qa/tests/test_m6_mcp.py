"""Milestone 6: an MCP server"""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp import Client  # noqa: E402

import mcp_server  # noqa: E402
import qa  # noqa: E402
from fakes import fake_collection, repo  # noqa: E402

HINT = ("search_code returns [{\"path\", \"start\", \"end\", \"name\", \"code\"}] for each chunk from index().search(query). "
        "read_lines returns the text from qa.read_lines(qa.ROOT, path, start, end), so the milestone 4 guards apply, "
        "and raises ToolError(str(error)) for a ValueError.")


class ServerTest(unittest.TestCase):
    def setUp(self):
        root = repo()
        with mock.patch.object(qa, "collection", fake_collection):
            index = qa.Index(root)
        for patch in (mock.patch.object(mcp_server, "index", lambda: index), mock.patch.object(qa, "ROOT", root)):
            patch.start()
            self.addCleanup(patch.stop)

    def call(self, name, args):
        async def go():
            async with Client(mcp_server.mcp) as client:
                return (await client.list_tools()).tools, await client.call_tool(name, args)
        return asyncio.run(go())

    def test_two_tools_with_their_schemas(self):
        tools, _ = self.call("search_code", {"query": "tax"})
        self.assertEqual(sorted(t.name for t in tools), ["read_lines", "search_code"])
        read = next(t for t in tools if t.name == "read_lines")
        self.assertEqual(sorted(read.input_schema["required"]), ["end", "path", "start"])

    def test_search_returns_chunks_with_their_lines(self):
        _, result = self.call("search_code", {"query": "sales tax rounding"})
        chunks = result.structured_content["result"]
        self.assertEqual(len(chunks), qa.TOP_K)
        self.assertEqual(set(chunks[0]), {"path", "start", "end", "name", "code"})
        self.assertIn("tinyshop/tax.py", [c["path"] for c in chunks])

    def test_read_lines_works_and_keeps_the_guards(self):
        _, result = self.call("read_lines", {"path": "tinyshop/tax.py", "start": 7, "end": 7})
        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["result"], "   7 | def tax_for(region, taxable_cents):")
        _, refused = self.call("read_lines", {"path": ".env", "start": 1, "end": 5})
        self.assertTrue(refused.is_error)
        self.assertIn("may hold secrets", refused.content[0].text)
        self.assertNotIn("test-secret", str(refused.content))


if __name__ == "__main__":
    unittest.main()
