import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, patch

from app.services.agent_service import AgentService
from app.services.llm_service import LLMService, LLMServiceError


class LLMTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_fast_llm_call_succeeds(self):
        service = LLMService()
        service.timeout = 0.1
        service.generate = lambda prompt, system_prompt=None: "answer"

        result = await service.generate_async("question")

        self.assertEqual(result, "answer")

    async def test_slow_llm_call_returns_controlled_timeout(self):
        service = LLMService()
        service.timeout = 0.05
        release = threading.Event()

        def slow_generate(prompt, system_prompt=None):
            release.wait(1)
            return "late answer"

        service.generate = slow_generate
        service._wait_before_retry = AsyncMock()

        try:
            with self.assertRaisesRegex(
                LLMServiceError,
                "timed out after 0.05 seconds",
            ):
                await service.generate_async("question")
        finally:
            release.set()

    async def test_unavailable_llm_is_controlled(self):
        service = LLMService()
        service.timeout = 0.1

        def unavailable_generate(prompt, system_prompt=None):
            raise RuntimeError("private connection detail")

        service.generate = unavailable_generate

        with self.assertRaises(LLMServiceError) as context:
            await service.generate_async("question")

        self.assertIn("LLM request failed", str(context.exception))

    async def test_sync_llm_work_does_not_block_event_loop(self):
        service = LLMService()
        service.timeout = 0.2
        started = threading.Event()
        release = threading.Event()
        marker = asyncio.Event()

        def blocked_generate(prompt, system_prompt=None):
            started.set()
            release.wait(1)
            return "answer"

        service.generate = blocked_generate

        async def mark_event_loop():
            while not started.is_set():
                await asyncio.sleep(0)
            marker.set()

        marker_task = asyncio.create_task(mark_event_loop())
        generation_task = asyncio.create_task(
            service.generate_async("question")
        )
        try:
            await asyncio.wait_for(marker.wait(), timeout=0.1)
            self.assertTrue(marker.is_set())
        finally:
            release.set()
            await asyncio.gather(
                generation_task,
                marker_task,
                return_exceptions=True,
            )

    async def test_agent_final_answer_failure_is_not_fabricated(self):
        agent = AgentService()
        agent.generate_final_answer = lambda *args, **kwargs: (
            (_ for _ in ()).throw(LLMServiceError("LLM unavailable"))
        )

        with self.assertRaises(LLMServiceError):
            await agent.generate_final_answer_async(
                "question",
                {},
                [],
            )


if __name__ == "__main__":
    unittest.main()