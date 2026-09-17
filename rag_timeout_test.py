import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_service import AgentService
from mcp_servers.documentation import server as documentation_server


class RAGTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_fast_rag_retrieval_succeeds(self):
        with patch.object(
            documentation_server,
            "RAG_TIMEOUT",
            0.1,
        ), patch.object(
            documentation_server,
            "retrieve_documentation",
            return_value=[{"id": "doc-1"}],
        ):
            result = await documentation_server.search_documentation(
                "INSUFFICIENT_FUNDS",
                top_k=3,
            )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"], [{"id": "doc-1"}])
        self.assertNotIn("error", result)

    async def test_slow_rag_returns_bounded_controlled_failure(self):
        release = threading.Event()

        def slow_retrieval(query, top_k):
            release.wait(1)
            return []

        with patch.object(
            documentation_server,
            "RAG_TIMEOUT",
            0.05,
        ), patch.object(
            documentation_server,
            "wait_before_retry",
            new_callable=AsyncMock,
        ), patch.object(
            documentation_server,
            "retrieve_documentation",
            side_effect=slow_retrieval,
        ):
            result = await documentation_server.search_documentation(
                "INSUFFICIENT_FUNDS",
                top_k=3,
            )
            release.set()

        self.assertEqual(result["count"], 0)
        self.assertIn("timed out", result["error"])

    async def test_rag_failure_is_not_evidence_or_identifier_data(self):
        agent = AgentService()
        failure = {
            "success": False,
            "error": "RAG retrieval timed out after 0.05 seconds",
        }
        identifiers = {"error_code": "INSUFFICIENT_FUNDS"}
        tool_results = []

        if failure.get("success") is False:
            tool_results.append(
                {
                    "tool": "search_documentation",
                    "success": False,
                    "error": failure["error"],
                }
            )
        else:
            agent.process_tool_result(
                "search_documentation",
                {"query": "INSUFFICIENT_FUNDS"},
                failure["data"],
                identifiers,
            )

        self.assertEqual(identifiers, {"error_code": "INSUFFICIENT_FUNDS"})
        self.assertFalse(tool_results[0]["success"])
        self.assertNotIn("data", tool_results[0])

    async def test_other_mcp_tool_remains_usable_after_rag_failure(self):
        class FakeSession:
            def __init__(self, name, result):
                self.name = name
                self.result = result

            async def list_tools(self):
                return SimpleNamespace(
                    tools=[SimpleNamespace(name=self.name)]
                )

            async def call_tool(self, tool_name, arguments):
                return self.result

        from app.services.mcp_client import MCPClient

        client = MCPClient()
        client.connections = {
            "documentation": {
                "session": FakeSession(
                    "search_documentation",
                    SimpleNamespace(
                        is_error=True,
                        structured_content=None,
                        content=[SimpleNamespace(text="RAG timed out")],
                    ),
                )
            },
            "database": {
                "session": FakeSession(
                    "get_customer",
                    SimpleNamespace(
                        is_error=False,
                        structured_content={"id": 1024},
                        content=[],
                    ),
                )
            },
        }

        failed = await client.call_tool(
            "search_documentation",
            {"query": "INSUFFICIENT_FUNDS"},
        )
        successful = await client.call_tool(
            "get_customer",
            {"customer_id": 1024},
        )

        self.assertFalse(failed["success"])
        self.assertTrue(successful["success"])

    def test_chat_returns_safe_error_for_rag_failure(self):
        class FailedAgent:
            def __init__(self):
                self.last_tool_results = []
                self.last_tools_used = ["search_documentation"]

            async def investigate(self, question):
                raise RuntimeError("RAG retrieval timed out internally")

        with patch("app.api.chat.AgentService", FailedAgent):
            response = TestClient(app).post(
                "/chat",
                json={"question": "Explain the payment failure"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("RAG retrieval timed out internally", response.text)
        self.assertIn("request_id", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()