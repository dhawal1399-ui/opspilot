import ollama


class QueryRewriter:
    def __init__(self, model: str = "llama3.2"):
        self.model = model

    def rewrite(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> str:

        conversation_history = conversation_history or []

        history_text = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in conversation_history
        )

        prompt = f"""
You rewrite user questions for a documentation search system.

IMPORTANT:
Your output MUST be a normal English question or search query.

NEVER output:
- SQL
- Python
- code
- commands
- database queries
- JSON
- markdown
- explanations

Use the conversation history only to resolve references such as:
"it", "that order", "the payment", "this error", etc.

Preserve important identifiers such as:
- customer IDs
- order IDs
- payment IDs
- request IDs
- error codes
- service names

IMPORTANT:
- Never invent an identifier that is not present in the conversation
  or provided context.
- If payment_id is unknown, do NOT mention a payment ID.
- If order_id is known, use the order_id to identify the payment context.
- Preserve known identifiers exactly.

Do not invent information.

If the latest query is already clear and standalone,
return it unchanged.

Return ONLY the rewritten natural-language query.

Conversation history:
{history_text}

Latest user query:
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

        rewritten_query = response["message"]["content"].strip()

        if self._looks_like_code(rewritten_query):
            return query

        return rewritten_query

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        lowered = text.lower()

        suspicious_patterns = [
            "select ",
            "insert ",
            "update ",
            "delete ",
            " from ",
            " where ",
            "```",
            "import ",
            "def ",
            "execute(",
        ]

        return any(
            pattern in lowered
            for pattern in suspicious_patterns
        )