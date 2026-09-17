import asyncio
import json
import logging

import ollama

from app.config import (
    LLM_MODEL,
    MAX_RETRIES,
    OLLAMA_HOST,
    LLM_TIMEOUT,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
)
from app.models.llm import LLMResponse


logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service failures."""

    def __init__(self, message, transient=False):
        super().__init__(message)
        self.transient = transient


class LLMService:
    def __init__(self):
        self.model = LLM_MODEL
        self.timeout = LLM_TIMEOUT
        self.client = ollama.Client(host=OLLAMA_HOST, timeout=self.timeout)

    def _is_transient_exception(self, exc):
        transient_types = {
            "ConnectError",
            "ReadTimeout",
            "WriteTimeout",
            "PoolTimeout",
            "NetworkError",
            "TransportError",
            "ServiceUnavailable",
        }
        message = str(exc).lower()
        return (
            isinstance(exc, (ConnectionError, TimeoutError, OSError))
            or type(exc).__name__ in transient_types
            or any(
                marker in message
                for marker in (
                    "connection",
                    "network",
                    "transport",
                    "temporarily unavailable",
                    "service unavailable",
                    "timed out",
                    "timeout",
                )
            )
        )

    async def _wait_before_retry(self, attempt, category):
        delay = min(
            RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
            RETRY_BACKOFF_MAX,
        )
        logger.warning(
            "LLM retry backoff: provider=ollama attempt=%s delay=%ss "
            "category=%s",
            attempt,
            delay,
            category,
        )
        await asyncio.sleep(delay)

    async def generate_async(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        total_attempts = 1 + MAX_RETRIES

        for attempt in range(1, total_attempts + 1):
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(
                        self.generate,
                        prompt,
                        system_prompt,
                    ),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError as exc:
                if attempt < total_attempts:
                    logger.warning(
                        "LLM retry: provider=ollama attempt=%s/%s "
                        "category=timeout",
                        attempt,
                        total_attempts,
                    )
                    await self._wait_before_retry(attempt, "timeout")
                    continue
                logger.warning(
                    "LLM request timeout: timeout=%ss",
                    self.timeout,
                )
                raise LLMServiceError(
                    f"LLM request timed out after {self.timeout} seconds",
                    transient=True,
                ) from exc
            except LLMServiceError as exc:
                if exc.transient and attempt < total_attempts:
                    logger.warning(
                        "LLM retry: provider=ollama attempt=%s/%s "
                        "category=transient_error",
                        attempt,
                        total_attempts,
                    )
                    await self._wait_before_retry(
                        attempt,
                        "transient_error",
                    )
                    continue
                raise
            except Exception as exc:
                logger.exception("LLM request failed")
                if attempt < total_attempts:
                    if not self._is_transient_exception(exc):
                        raise LLMServiceError(
                            "LLM request failed"
                        ) from exc
                    logger.warning(
                        "LLM retry: provider=ollama attempt=%s/%s "
                        "category=transient_error",
                        attempt,
                        total_attempts,
                    )
                    await self._wait_before_retry(
                        attempt,
                        "transient_error",
                    )
                    continue
                raise LLMServiceError(
                    "LLM request failed",
                    transient=True,
                ) from exc

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:

        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        try:
            data = json.loads(response)

        except json.JSONDecodeError as exc:
            raise LLMServiceError(
                "LLM returned invalid JSON"
            ) from exc

        try:
            return LLMResponse.model_validate(data)

        except ValueError as exc:
            raise LLMServiceError(
                "LLM returned invalid structured output"
            ) from exc

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:

        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
            )

            content =  response["message"]["content"].strip()

            if not content:
                raise LLMServiceError(
                    "LLM returned an empty response"
                )

            return content.strip()
        except LLMServiceError:
            raise

        except Exception as exc:
            logger.exception("LLM request failed")
            raise LLMServiceError(
                "LLM request failed",
                transient=self._is_transient_exception(exc),
            ) from exc
