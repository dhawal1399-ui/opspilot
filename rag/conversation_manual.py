from rag.conversation import ConversationManager


conversation = ConversationManager()

conversation.add_message(
    "user",
    "Why did order 1001 fail?",
)

conversation.add_message(
    "assistant",
    "Order 1001 failed because the payment was rejected "
    "with INSUFFICIENT_FUNDS.",
)

follow_up_questions = [
    "What about the payment?",
    "Why did it fail?",
    "What does that error mean?",
]

for question in follow_up_questions:
    rewritten = conversation.rewrite_query(question)

    print("\nOriginal:", question)
    print("Rewritten:", rewritten)

    conversation.add_message("user", question)