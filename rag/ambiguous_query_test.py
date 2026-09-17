from rag.conversation import ConversationManager


conversation = ConversationManager()

conversation.add_message(
    "user",
    "Why did order 1001 fail for customer 1024?",
)

conversation.add_message(
    "assistant",
    "Order 1001 failed because the payment was rejected "
    "with INSUFFICIENT_FUNDS.",
)

queries = [
    "Why?",
    "What happened?",
    "What about the payment?",
    "What should I check?",
    "Is it still failing?",
]

for query in queries:
    rewritten = conversation.rewrite_query(query)

    print("\nOriginal:", query)
    print("Rewritten:", rewritten)