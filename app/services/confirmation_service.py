import secrets
from typing import Any


class ConfirmationService:
    def __init__(self):
        self._pending_actions: dict[str, dict[str, Any]] = {}

    def create(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        token = secrets.token_urlsafe(32)

        self._pending_actions[token] = {
            "tool_name": tool_name,
            "arguments": arguments,
        }

        return token

    def get(self, token: str) -> dict[str, Any] | None:
        return self._pending_actions.get(token)

    def consume(self, token: str) -> dict[str, Any] | None:
        return self._pending_actions.pop(token, None)

    def clear(self, token: str) -> None:
        self._pending_actions.pop(token, None)