"""Optional real stdio protocol check, using the pinned official MCP SDK."""
import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("mcp"), "Install requirements-growth.txt for the MCP wire check")
class MCPBridgeTest(unittest.TestCase):
    def test_stdio_discovery_and_durable_idempotent_queue(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def exercise(root):
            parameters = StdioServerParameters(
                command=sys.executable, args=[str(ROOT / "scripts" / "growthops_mcp.py")],
                env={**os.environ, "CONTENTOPS_PROJECT_ROOT": str(root)},
            )
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    names = {item.name for item in (await session.list_tools()).tools}
                    self.assertEqual(len(names), 11)
                    self.assertIn("growth_status", names)
                    self.assertIn("check_presenter", names)
                    arguments = {"lane": "campaign", "kind": "draft", "idempotency_key": "wire-check",
                                 "payload": {"brief": "Test an isolated local queue"}}
                    first = await session.call_tool("queue_growth_task", arguments)
                    second = await session.call_tool("queue_growth_task", arguments)
                    self.assertFalse(first.is_error)
                    self.assertFalse(second.is_error)
                    first_data = json.loads(next(item.text for item in first.content if item.type == "text"))
                    second_data = json.loads(next(item.text for item in second.content if item.type == "text"))
                    self.assertEqual(first_data["id"], second_data["id"])
                    status = await session.call_tool("growth_status", {})
                    self.assertFalse(status.is_error)
                    self.assertTrue((root / "data" / "growthops" / "state.sqlite3").exists())

        with tempfile.TemporaryDirectory() as temporary:
            asyncio.run(asyncio.wait_for(exercise(Path(temporary)), timeout=20))


if __name__ == "__main__":
    unittest.main()
