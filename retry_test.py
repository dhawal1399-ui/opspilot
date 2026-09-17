import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.llm_service import LLMService, LLMServiceError
from app.services.mcp_client import MCPClient
from mcp_servers.documentation import server as documentation_server


def result(data=None, is_error=False, text=None):
    return SimpleNamespace(
        structured_content=data,
        is_error=is_error,
        content=(
            [SimpleNamespace(text=text)]
            if text is not None
            else []
        ),
    )


class RetrySession:
    def __init__(self, tool_name, outcomes):
        self.tool_name = tool_name
        self.outcomes = list(outcomes)
        self.calls = 0

    async def list_tools(self):
        return SimpleNamespace(
            tools=[SimpleNamespace(name=self.tool_name)]
        )

    async def call_tool(self, tool_name, arguments):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class RetryTest(unittest.IsolatedAsyncioTestCase):
    def client_for(self, session):
        client = MCPClient()
        client.connections = {"database": {"session": session}}
        return client

    async def test_transient_mcp_succeeds_on_second_attempt(self):
        session = RetrySession(
            "get_customer",
            [ConnectionError("temporary network failure"), result({"id": 1})],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 2), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "get_customer",
                {"customer_id": 1},
            )
        self.assertTrue(response["success"])
        self.assertEqual(session.calls, 2)
        sleep.assert_awaited_once_with(0.5)

    async def test_transient_mcp_succeeds_on_final_allowed_attempt(self):
        session = RetrySession(
            "get_customer",
            [
                ConnectionError("temporary network failure"),
                TimeoutError("temporary timeout"),
                result({"id": 1}),
            ],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 2), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "get_customer",
                {"customer_id": 1},
            )
        self.assertTrue(response["success"])
        self.assertEqual(session.calls, 3)
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [0.5, 1.0],
        )

    async def test_transient_mcp_exhaustion_is_controlled(self):
        session = RetrySession(
            "get_customer",
            [
                ConnectionError("temporary failure"),
                ConnectionError("temporary failure"),
                ConnectionError("temporary failure"),
            ],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 2), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "get_customer",
                {"customer_id": 1},
            )
        self.assertFalse(response["success"])
        self.assertEqual(session.calls, 3)
        self.assertEqual(sleep.await_count, 2)

    async def test_permanent_mcp_failure_is_not_retried(self):
        session = RetrySession(
            "get_ticket",
            [
                result(
                    is_error=True,
                    text="Ticket not found",
                )
            ],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 2), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "get_ticket",
                {"ticket_id": 9999},
            )
        self.assertFalse(response["success"])
        self.assertEqual(session.calls, 1)
        sleep.assert_not_awaited()

    async def test_write_mcp_tool_is_not_retried(self):
        session = RetrySession(
            "create_ticket",
            [ConnectionError("temporary network failure")],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 2), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "create_ticket",
                {"customer_id": 1},
            )
        self.assertFalse(response["success"])
        self.assertEqual(session.calls, 1)
        sleep.assert_not_awaited()

    async def test_transient_llm_failure_retries(self):
        service = LLMService()
        service.timeout = 0.1
        outcomes = [
            LLMServiceError("temporary provider failure", transient=True),
            "answer",
        ]

        def generate(prompt, system_prompt=None):
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        service.generate = generate

        with patch("app.services.llm_service.MAX_RETRIES", 2), patch(
            "app.services.llm_service.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await service.generate_async("question")
        self.assertEqual(response, "answer")
        sleep.assert_awaited_once_with(0.5)

    async def test_permanent_llm_failure_is_not_retried(self):
        service = LLMService()
        service.timeout = 0.1
        calls = 0

        def fail(prompt, system_prompt=None):
            nonlocal calls
            calls += 1
            raise LLMServiceError("invalid structured output")

        service.generate = fail
        with patch("app.services.llm_service.MAX_RETRIES", 2), patch(
            "app.services.llm_service.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            with self.assertRaises(LLMServiceError):
                await service.generate_async("question")
        self.assertEqual(calls, 1)
        sleep.assert_not_awaited()

    async def test_rag_retry_reuses_same_retriever(self):
        class FakeRetriever:
            def __init__(self):
                self.calls = 0

            def retrieve(self, query, top_k):
                self.calls += 1
                if self.calls == 1:
                    raise ConnectionError("temporary vector store failure")
                return [{"id": "doc-1"}]

        retriever = FakeRetriever()
        with patch.object(documentation_server, "RAG_TIMEOUT", 0.1), patch.object(
            documentation_server,
            "MAX_RETRIES",
            2,
        ), patch(
            "asyncio.sleep",
            new_callable=AsyncMock,
        ), patch.object(
            documentation_server,
            "get_retriever",
            return_value=retriever,
        ):
            response = await documentation_server.search_documentation(
                "query",
                top_k=1,
            )
        self.assertEqual(response["count"], 1)
        self.assertEqual(retriever.calls, 2)

    async def test_rag_retry_exhaustion_is_controlled(self):
        def fail(query, top_k):
            raise ConnectionError("temporary vector store failure")

        with patch.object(documentation_server, "RAG_TIMEOUT", 0.1), patch.object(
            documentation_server,
            "MAX_RETRIES",
            2,
        ), patch(
            "asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep, patch.object(
            documentation_server,
            "retrieve_documentation",
            side_effect=fail,
        ):
            response = await documentation_server.search_documentation(
                "query",
                top_k=1,
            )
        self.assertFalse("results" not in response)
        self.assertEqual(response["error"], "Documentation retrieval error")
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [0.5, 1.0],
        )

    async def test_backoff_is_capped(self):
        session = RetrySession(
            "get_customer",
            [
                ConnectionError("temporary failure"),
                ConnectionError("temporary failure"),
                ConnectionError("temporary failure"),
                ConnectionError("temporary failure"),
            ],
        )
        with patch("app.services.mcp_client.MAX_RETRIES", 3), patch(
            "app.services.mcp_client.RETRY_BACKOFF_BASE",
            2.0,
        ), patch(
            "app.services.mcp_client.RETRY_BACKOFF_MAX",
            3.0,
        ), patch(
            "app.services.mcp_client.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep:
            response = await self.client_for(session).call_tool(
                "get_customer",
                {"customer_id": 1},
            )
        self.assertFalse(response["success"])
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [2.0, 3.0, 3.0],
        )


if __name__ == "__main__":
    unittest.main()