from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: str = Field(max_length=500)
    confirmation: bool = False
    confirmation_token: str | None = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question must not be empty")
        return question


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    evidence: list[dict[str, Any]]
    tools_used: list[str]
    confirmation_required: bool = False
    confirmation_token: str | None = None