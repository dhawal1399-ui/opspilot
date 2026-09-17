from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    answer: str
    root_cause: str
    evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)