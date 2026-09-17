from typing import Any

from pydantic import BaseModel


class PendingAction(BaseModel):
    token: str
    tool_name: str
    arguments: dict[str, Any]