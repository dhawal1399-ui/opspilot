import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.mcp_client import MCPClient


class FakeStdioContext:
    def __init__(self, server_name):
        self.server_name = server_name
        self.closed = False

    async def __aenter__(self):
        if self.server_name == "tickets":
            raise RuntimeError("simulated tickets startup failure")
        return (self.server_name, self.server_name)

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True


class FakeSession:
    def __init__(self, read_stream, write_stream):
        self.server_name = read_stream
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True

    async def initialize(self):
        return None

    async def list_tools(self):
        return SimpleNamespace(
            tools=[SimpleNamespace(name=f"{self.server_name}_tool")]
        )


class MCPConnectionFailureTest(unittest.IsolatedAsyncioTestCase):
    async def test_one_server_failure_preserves_other_connections(self):
        client = MCPClient()

        def fake_stdio_client(server_params):
            server_name = server_params.args[-1].split(".")[-2]
            return FakeStdioContext(server_name)

        with patch(
            "app.services.mcp_client.stdio_client",
            side_effect=fake_stdio_client,
        ), patch(
            "app.services.mcp_client.ClientSession",
            FakeSession,
        ):
            await client.connect()

            self.assertEqual(
                set(client.connections),
                {"database", "logs", "documentation", "health"},
            )
            self.assertIn("tickets", client.unavailable_servers)

            tools = await client.list_tools()
            self.assertEqual(len(tools), 4)
            self.assertNotIn(
                "tickets_tool",
                {item["tool"].name for item in tools},
            )

            with self.assertRaisesRegex(RuntimeError, "tickets"):
                await client.call_tool("tickets_tool", {})

            await client.disconnect()
            self.assertEqual(client.connections, {})


if __name__ == "__main__":
    unittest.main()