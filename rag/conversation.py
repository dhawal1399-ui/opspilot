from rag.query_rewriter import QueryRewriter


class ConversationManager:
    # def __init__(self, max_messages: int = 10):
    #     self.history: list[dict] = []
    #     self.max_messages = max_messages
    #     self.context: dict = {}
    #     self.rewriter = QueryRewriter()
    def __init__(
        self,
        max_messages: int = 10,
        max_context_chars: int = 4000,
    ):
        self.history: list[dict] = []
        self.max_messages = max_messages
        self.max_context_chars = max_context_chars
        self.context: dict = {}
        self.rewriter = QueryRewriter()

    def add_message(self, role: str, content: str) -> None:
        self.history.append(
            {
                "role": role,
                "content": content,
            }
        )

        self._update_context(content)
        self._trim_history()

    def get_history(self) -> list[dict]:
        return self.history.copy()

    def get_context(self) -> dict:
        return self.context.copy()

    def rewrite_query(self, query: str) -> str:
        history = self.history.copy()

        if self.context:
            context_text = "\n".join(
                f"{key} = {value}"
                for key, value in self.context.items()
            )

            history.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "Important conversation context:\n"
                        f"{context_text}"
                    ),
                },
            )

        return self.rewriter.rewrite(
            query=query,
            conversation_history=history,
        )

    def _update_context(self, content: str) -> None:
        self._extract_id(content, "customer_id")
        self._extract_id(content, "order_id")
        self._extract_id(content, "payment_id")
        self._extract_request_id(content)
        self._extract_error_code(content)

    def _extract_id(self, text: str, field: str) -> None:
        import re

        # Explicit forms:
        # order_id=1001
        # order_id: 1001
        explicit_pattern = rf"\b{re.escape(field)}\s*[=:]\s*(\d+)\b"

        match = re.search(
            explicit_pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            self.context[field] = int(match.group(1))
            return

        # Natural language forms:
        # order 1001
        # customer 1024
        natural_name = field.replace("_id", "")

        natural_pattern = (
            rf"\b{re.escape(natural_name)}\s+(\d+)\b"
        )

        match = re.search(
            natural_pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            self.context[field] = int(match.group(1))

    def _extract_request_id(self, text: str) -> None:
        import re

        match = re.search(
            r"\b(req-[a-zA-Z0-9-]+)\b",
            text,
        )

        if match:
            self.context["request_id"] = match.group(1)

    def _extract_error_code(self, text: str) -> None:
        import re

        known_error_codes = [
            "INSUFFICIENT_FUNDS",
            "PAYMENT_FAILED",
        ]

        for error_code in known_error_codes:
            if re.search(
                rf"\b{re.escape(error_code)}\b",
                text,
                re.IGNORECASE,
            ):
                self.context["error_code"] = error_code

    def _trim_history(self) -> None:
        # First limit the number of messages.
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages:]

        # Then limit total conversation size.
        while (
            self._history_size() > self.max_context_chars
            and len(self.history) > 1
        ):
            self.history.pop(0)

    def _history_size(self) -> int:
        return sum(
            len(message["content"])
            for message in self.history
        )
