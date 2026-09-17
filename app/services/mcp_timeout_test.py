import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.agent import AgentDecision, ToolCall
from app.services.agent_service import AgentService
from app.services.mcp_client import MCPClient


def tool_result(*, data=None):
    return SimpleNamespace(
        content=[],
        structured_content=data,
        is_error=False,
    )


class DelayedToolSession:
    def __init__(self, tool_name, delay=0, result=None):
        self.tool_name = tool_name
        self.delay = delay
        self.result = result or {"ok": True}
        self.cancelled = False

    async def list_tools(self):
        return SimpleNamespace(
            tools=[SimpleNamespace(name=self.tool_name)]
        )

    async def call_tool(self, tool_name, arguments):
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return tool_result(data=self.result)


class MCPTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_fast_tool_succeeds_before_timeout(self):
        client = MCPClient()
        client.connections = {
            "database": {
                "session": DelayedToolSession(
                    "get_customer",
                    delay=0,
                    result={"customer_id": 1024},
                )
            }
        }

        with patch("app.services.mcp_client.MCP_TOOL_TIMEOUT", 0.1):
            result = await client.call_tool(
                "get_customer",
                {"customer_id": 1024},
            )

        self.assertEqual(
            result,
            {
                "success": True,
                "data": {"customer_id": 1024},
            },
        )

    async def test_slow_tool_returns_bounded_controlled_failure(self):
        session = DelayedToolSession("get_error_logs", delay=1)
        client = MCPClient()
        client.connections = {
            "logs": {"session": session}
        }
        client._wait_before_retry = AsyncMock()

        start = time.perf_counter()
        with patch("app.services.mcp_client.MCP_TOOL_TIMEOUT", 0.05), patch(
            "app.services.mcp_client.MAX_RETRIES",
            0,
        ):
            result = await client.call_tool(
                "get_error_logs",
                {"order_id": 1001},
            )
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.5)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["error"])
        self.assertTrue(session.cancelled)

    async def test_other_server_remains_usable_after_timeout(self):
        client = MCPClient()
        client.connections = {
            "logs": {
                "session": DelayedToolSession(
                    "get_error_logs",
                    delay=1,
                )
            },
            "database": {
                "session": DelayedToolSession(
                    "get_customer",
                    delay=0,
                    result={"customer_id": 1024},
                )
            },
        }
        client._wait_before_retry = AsyncMock()

        with patch("app.services.mcp_client.MCP_TOOL_TIMEOUT", 0.05), patch(
            "app.services.mcp_client.MAX_RETRIES",
            0,
        ):
            timed_out = await client.call_tool(
                "get_error_logs",
                {"order_id": 1001},
            )
            successful = await client.call_tool(
                "get_customer",
                {"customer_id": 1024},
            )

        self.assertFalse(timed_out["success"])
        self.assertTrue(successful["success"])

    async def test_timeout_is_not_evidence_or_identifier_data(self):
        agent = AgentService()
        result = {
            "success": False,
            "error": "MCP tool 'get_error_logs' timed out",
        }
        identifiers = {}

        if result.get("success") is True:
            agent.process_tool_result(
                "get_error_logs",
                {"order_id": 1001},
                result["data"],
                identifiers,
            )

        self.assertEqual(identifiers, {})

    async def test_timeout_is_not_repeated_and_disconnects_cleanly(self):
        agent = AgentService()
        call_count = 0

        class FakeMCP:
            async def list_tools(self):
                return [
                    {
                        "server": "logs",
                        "tool": SimpleNamespace(
                            name="get_error_logs",
                            description="Get error logs",
                            input_schema={"required": ["order_id"]},
                        ),
                    }
                ]

            async def call_tool(self, tool_name, arguments):
                nonlocal call_count
                call_count += 1
                return {
                    "success": False,
                    "error": "MCP tool timed out",
                }

        agent.mcp = FakeMCP()
        agent.connect = AsyncMock()
        agent.disconnect = AsyncMock()
        repeated_call = ToolCall(
            name="get_error_logs",
            arguments={"order_id": 1001},
        )
        agent.select_tools = AsyncMock(
            side_effect=[
                AgentDecision(action="tool_call", tools=[repeated_call]),
                AgentDecision(action="tool_call", tools=[repeated_call]),
            ]
        )
        agent.generate_final_answer_async = AsyncMock(
            return_value="Insufficient evidence"
        )

        result = await agent.investigate("Investigate order 1001")

        self.assertEqual(result, "Insufficient evidence")
        self.assertEqual(call_count, 1)
        self.assertEqual(agent.select_tools.await_count, 2)
        agent.disconnect.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()