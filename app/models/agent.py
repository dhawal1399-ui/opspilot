from typing import Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str
    arguments: dict = Field(
        default_factory=dict
    )


class ToolSelection(BaseModel):
    tools: list[ToolCall] = Field(
        default_factory=list
    )


class AgentDecision(BaseModel):
    action: Literal[
        "tool_call",
        "final",
    ]

    tools: list[ToolCall] = Field(
        default_factory=list
    )