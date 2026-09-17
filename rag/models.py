from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    intent: str
    sections: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)