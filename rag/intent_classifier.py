import json
import ollama
from rag.models import QueryIntent


class QueryIntentClassifier:
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def classify(self, query: str) -> dict:
        prompt = f"""
You are a query intent classifier for an operations troubleshooting
assistant.

Analyze the user's query and identify which documentation sections
are relevant.

Available sections:
- Payment Service
- Payment Failure
- INSUFFICIENT_FUNDS
- Gateway Declined
- Order Service
- Order Lifecycle
- Failed Orders
- Order Investigation
- Service Health
- Payment API
- Troubleshooting Guide
- Payment Failure Investigation
- Recommended Investigation Flow

Return ONLY valid JSON in this format:

{{
    "intent": "short_intent_name",
    "sections": ["section1", "section2"],
    "keywords": ["keyword1", "keyword2"]
}}

Rules:
- Select only relevant sections.
- Keep the intent short and descriptive.
- Extract important technical keywords.
- Do not add explanations outside the JSON.

User query:
{query}
"""

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        content = response["message"]["content"]

        try:
            data = json.loads(content)
            return QueryIntent.model_validate(data)

        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"Invalid intent response: {content}"
            ) from exc