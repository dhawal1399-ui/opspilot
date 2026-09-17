from rag.conversation import ConversationManager


conversation = ConversationManager(max_messages=4)

conversation.add_message(
    "user",
    "Why did order 1001 fail for customer 1024?",
)

conversation.add_message(
    "assistant",
    "Order 1001 failed because payment was rejected "
    "with INSUFFICIENT_FUNDS.",
)

print("Context after investigation:")
print(conversation.get_context())

# Add unrelated messages to force history trimming.
conversation.add_message(
    "user",
    "Tell me about service health."
)

conversation.add_message(
    "assistant",
    "The payment service is healthy."
)

conversation.add_message(
    "user",
    "What about that payment?"
)

print("\nCurrent history:")
for message in conversation.get_history():
    print(message)

print("\nPreserved context:")
print(conversation.get_context())

print("\nRewritten follow-up:")
print(
    conversation.rewrite_query(
        "What about that payment?"
    )
)