import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class FakeAgentService:
    should_fail = False

    def __init__(self):
        self.last_tool_results = [
            {
                "tool": "get_customer",
                "arguments": {"customer_id": 1024},
                "success": True,
                "data": {"customer": {"id": 1024}},
            },
            {
                "tool": "search_orders",
                "arguments": {"customer_id": 1024},
                "success": True,
                "data": {"orders": [{"id": 1001}]},
            },
            {
                "tool": "get_error_logs",
                "arguments": {"order_id": 1001},
                "success": True,
                "data": {"logs": [{"error_code": "INSUFFICIENT_FUNDS"}]},
            },
            {
                "tool": "search_documentation",
                "arguments": {"query": "INSUFFICIENT_FUNDS", "top_k": 3},
                "success": True,
                "data": {"results": [{"text": "Insufficient funds"}]},
            },
        ]
        self.last_tools_used = [
            result["tool"]
            for result in self.last_tool_results
        ]

    async def investigate(self, question):
        if self.should_fail:
            raise RuntimeError("private internal failure")
        return "Root cause: INSUFFICIENT_FUNDS"


client = TestClient(app)


def test_valid_chat_request_returns_answer_evidence_and_tools():
    with patch("app.api.chat.AgentService", FakeAgentService):
        response = client.post(
            "/chat",
            json={
                "question": "Why are orders failing for customer 1024?"
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"].startswith("req-")
    assert "INSUFFICIENT_FUNDS" in body["answer"]
    assert body["tools_used"] == [
        "get_customer",
        "search_orders",
        "get_error_logs",
        "search_documentation",
    ]
    assert len(body["evidence"]) == 4


def test_empty_question_is_rejected():
    response = client.post("/chat", json={"question": ""})
    assert response.status_code == 422


def test_missing_question_is_rejected():
    response = client.post("/chat", json={})
    assert response.status_code == 422


def test_whitespace_question_is_rejected():
    response = client.post("/chat", json={"question": "   "})
    assert response.status_code == 422


def test_agent_failure_returns_safe_error_with_request_id():
    FakeAgentService.should_fail = True
    try:
        with patch("app.api.chat.AgentService", FakeAgentService):
            response = client.post(
                "/chat",
                json={"question": "Investigate order failures"},
            )
    finally:
        FakeAgentService.should_fail = False

    assert response.status_code == 500
    body = response.json()
    assert body["detail"]["request_id"].startswith("req-")
    assert body["detail"]["error"] == (
        "Unable to complete the investigation."
    )
    assert "private internal failure" not in response.text


class ChatApiTest(unittest.TestCase):
    def test_valid_request(self):
        test_valid_chat_request_returns_answer_evidence_and_tools()

    def test_empty_question(self):
        test_empty_question_is_rejected()

    def test_missing_question(self):
        test_missing_question_is_rejected()

    def test_whitespace_question(self):
        test_whitespace_question_is_rejected()

    def test_agent_failure(self):
        test_agent_failure_returns_safe_error_with_request_id()


if __name__ == "__main__":
    unittest.main()