import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.agent import AgentDecision, ToolCall
from app.services.agent_service import AgentService
from app.services.mcp_client import MCPClient


def tool_result(*, content=None, structured_content=None, is_error=False):
    return SimpleNamespace(
        content=content or [],
        structured_content=structured_content,
        is_error=is_error,
    )


class FakeToolSession:
    def __init__(self, tool_name, result=None, exception=None):
        self.tool_name = tool_name
        self.result = result
        self.exception = exception

    async def list_tools(self):
        return SimpleNamespace(
            tools=[SimpleNamespace(name=self.tool_name)]
        )

    async def call_tool(self, tool_name, arguments):
        if self.exception:
            raise self.exception
        return self.result


class MCPToolFailureTest(unittest.IsolatedAsyncioTestCase):
    async def test_exception_is_controlled_and_other_server_remains_usable(self):
        client = MCPClient()
        client.connections = {
            "tickets": {
                "session": FakeToolSession(
                    "get_ticket",
                    exception=RuntimeError("ticket lookup failed"),
                )
            },
            "database": {
                "session": FakeToolSession(
                    "get_customer",
                    result=tool_result(
                        structured_content={"id": 1024}
                    ),
                )
            },
        }

        failed = await client.call_tool("get_ticket", {"ticket_id": 9999})
        successful = await client.call_tool("get_customer", {"customer_id": 1024})

        self.assertFalse(failed["success"])
        self.assertIn("RuntimeError", failed["error"])
        self.assertEqual(successful, {"success": True, "data": {"id": 1024}})

    async def test_is_error_is_not_successful_evidence(self):
        client = MCPClient()
        client.connections = {
            "tickets": {
                "session": FakeToolSession(
                    "get_ticket",
                    result=tool_result(
                        is_error=True,
                        content=[SimpleNamespace(text="Ticket not found")],
                    ),
                )
            }
        }

        result = await client.call_tool("get_ticket", {"ticket_id": 9999})

        self.assertFalse(result["success"])
        self.assertIn("Ticket not found", result["error"])

    async def test_malformed_response_is_controlled(self):
        client = MCPClient()
        client.connections = {
            "tickets": {
                "session": FakeToolSession(
                    "get_ticket",
                    result=tool_result(
                        content=[SimpleNamespace(text="not-json")]
                    ),
                )
            }
        }

        result = await client.call_tool("get_ticket", {"ticket_id": 9999})

        self.assertFalse(result["success"])
        self.assertIn("malformed", result["error"])

    async def test_failed_tool_does_not_create_evidence_or_loop(self):
        agent = AgentService()
        tool_names = {
            "get_customer",
            "search_orders",
            "get_error_logs",
        }

        class FakeMCP:
            async def list_tools(self):
                return [
                    {
                        "server": "fake",
                        "tool": SimpleNamespace(
                            name=name,
                            description=name,
                            input_schema={
                                "required": []
                                if name == "search_orders"
                                else ["customer_id"]
                                if name == "get_customer"
                                else ["order_id"]
                            },
                        ),
                    }
                    for name in tool_names
                ]

            async def call_tool(self, tool_name, arguments):
                if tool_name == "get_customer":
                    return {
                        "success": True,
                        "data": {"customer": {"id": 1024}},
                    }
                if tool_name == "search_orders":
                    return {
                        "success": True,
                        "data": {"orders": [{"id": 1001}]},
                    }
                return {
                    "success": False,
                    "error": "log retrieval failed",
                }

        agent.mcp = FakeMCP()
        agent.connect = AsyncMock()
        agent.disconnect = AsyncMock()
        agent.select_tools = AsyncMock(
            side_effect=[
                AgentDecision(
                    action="tool_call",
                    tools=[
                        ToolCall(
                            name="get_customer",
                            arguments={"customer_id": 1024},
                        )
                    ],
                ),
                AgentDecision(action="final", tools=[]),
            ]
        )
        final_answer = AsyncMock(return_value="Insufficient evidence")
        agent.generate_final_answer_async = final_answer

        result = await agent.investigate(
            "Why are orders failing for customer 1024?"
        )

        self.assertEqual(result, "Insufficient evidence")
        evidence = final_answer.await_args.kwargs["tool_results"]
        self.assertEqual(evidence[-1]["success"], False)
        self.assertNotIn("result", evidence[-1])
        self.assertEqual(agent.select_tools.await_count, 2)


if __name__ == "__main__":
    unittest.main()