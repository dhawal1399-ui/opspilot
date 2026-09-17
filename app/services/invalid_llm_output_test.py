import json

from app.models.llm import LLMResponse
from app.services.llm_service import LLMServiceError


def validate_response(response: str) -> LLMResponse:
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


invalid_responses = [
    "This is not JSON",
    '{"answer": "Order failed"',
    '{"answer": "Order failed", "root_cause": 123}',
]

for response in invalid_responses:
    print("\nTesting:", response)

    try:
        validate_response(response)
        print("Unexpected: response accepted")

    except LLMServiceError as exc:
        print("Handled:", exc)