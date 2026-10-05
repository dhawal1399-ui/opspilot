from rag.conversation import ConversationManager


conversation = ConversationManager()

# Initial investigation
conversation.add_message(
    "user",
    "Why did order 1001 fail for customer 1024?",
)

conversation.add_message(
    "assistant",
    "Order 1001 failed because the payment was rejected "
    "with INSUFFICIENT_FUNDS.",
)

# Follow-up questions
questions = [
    "What about the payment?",
    "Why did it fail?",
    "What does that error mean?",
]

for question in questions:
    rewritten = conversation.rewrite_query(question)

    print("\nOriginal:", question)
    print("Rewritten:", rewritten)

    conversation.add_message(
        "user",
        question,
    )

    conversation.add_message(
        "assistant",
        f"Processed question: {rewritten}",
    )