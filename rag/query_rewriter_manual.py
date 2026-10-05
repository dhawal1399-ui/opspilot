from rag.query_rewriter import QueryRewriter


rewriter = QueryRewriter()

history = [
    {
        "role": "user",
        "content": "Why did order 1001 fail?",
    },
    {
        "role": "assistant",
        "content": (
            "Order 1001 failed because the payment was rejected "
            "with INSUFFICIENT_FUNDS."
        ),
    },
]

queries = [
    "What about the payment?",
    "Why did it fail?",
    "What does INSUFFICIENT_FUNDS mean?",
    "Is the payment gateway healthy?",
]

for query in queries:
    rewritten = rewriter.rewrite(
        query=query,
        conversation_history=history,
    )

    print("\nOriginal:", query)
    print("Rewritten:", rewritten)