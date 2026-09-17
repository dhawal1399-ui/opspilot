import asyncio
import unittest

from app.services.agent_service import AgentService


class AgentConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_independent_read_calls_overlap(self):
        agent = AgentService()
        active_calls = 0
        maximum_active_calls = 0

        async def fake_execute(tool_name, arguments):
            nonlocal active_calls, maximum_active_calls
            active_calls += 1
            maximum_active_calls = max(
                maximum_active_calls,
                active_calls,
            )
            await asyncio.sleep(0.05)
            active_calls -= 1
            return {"success": True, "data": {"tool": tool_name}}

        agent.execute_tool = fake_execute

        results = await agent.execute_tools_concurrently(
            [
                {
                    "name": "get_error_logs",
                    "arguments": {"order_id": 1001},
                },
                {
                    "name": "get_customer_tickets",
                    "arguments": {"customer_id": 1024},
                },
            ]
        )

        self.assertEqual(maximum_active_calls, 2)
        self.assertEqual(
            {result["tool"] for result in results},
            {"get_error_logs", "get_customer_tickets"},
        )
        self.assertTrue(all(result["success"] for result in results))

    async def test_one_concurrent_failure_preserves_success(self):
        agent = AgentService()

        async def fake_execute(tool_name, arguments):
            if tool_name == "get_customer_tickets":
                return {
                    "success": False,
                    "error": "ticket lookup failed",
                }
            return {
                "success": True,
                "data": {"logs": ["evidence"]},
            }

        agent.execute_tool = fake_execute

        results = await agent.execute_tools_concurrently(
            [
                {
                    "name": "get_error_logs",
                    "arguments": {"order_id": 1001},
                },
                {
                    "name": "get_customer_tickets",
                    "arguments": {"customer_id": 1024},
                },
            ]
        )

        by_tool = {result["tool"]: result for result in results}
        self.assertTrue(by_tool["get_error_logs"]["success"])
        self.assertEqual(
            by_tool["get_error_logs"]["data"],
            {"logs": ["evidence"]},
        )
        self.assertFalse(by_tool["get_customer_tickets"]["success"])
        self.assertNotIn("data", by_tool["get_customer_tickets"])

    def test_dependent_policy_steps_remain_sequential(self):
        agent = AgentService()
        available_tools = [
            {"name": "search_orders"},
            {"name": "get_error_logs"},
        ]

        next_call = agent.get_next_policy_tool(
            query="investigate",
            identifiers={"customer_id": 1024},
            executed_calls=set(),
            available_tools=available_tools,
        )
        self.assertEqual(next_call["name"], "search_orders")
        self.assertEqual(next_call["arguments"], {"customer_id": 1024})

        next_call = agent.get_next_policy_tool(
            query="investigate",
            identifiers={"customer_id": 1024, "order_id": 1001},
            executed_calls=set(),
            available_tools=available_tools,
        )
        self.assertEqual(next_call["name"], "get_error_logs")
        self.assertEqual(next_call["arguments"], {"order_id": 1001})

    async def test_writes_are_not_included_and_duplicates_are_rejected(self):
        agent = AgentService()
        executed = []

        async def fake_execute(tool_name, arguments):
            executed.append(tool_name)
            return {"success": True, "data": {}}

        agent.execute_tool = fake_execute
        executed_calls = set()

        results = await agent.execute_tools_concurrently(
            [
                {
                    "name": "create_ticket",
                    "arguments": {"customer_id": 1024},
                },
                {
                    "name": "get_error_logs",
                    "arguments": {"order_id": 1001},
                },
                {
                    "name": "get_error_logs",
                    "arguments": {"order_id": 1001},
                },
            ],
            executed_calls=executed_calls,
        )

        self.assertEqual(executed, ["get_error_logs"])
        self.assertEqual(
            sum(result["success"] for result in results),
            1,
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(len(executed_calls), 1)


if __name__ == "__main__":
    unittest.main()