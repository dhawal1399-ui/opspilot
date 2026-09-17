from rag.conversation import ConversationManager


conversation = ConversationManager(
    max_messages=10,
    max_context_chars=200,
)

for index in range(10):
    conversation.add_message(
        "user",
        f"This is conversation message number {index}. "
        "This message contains some additional information "
        "to make the conversation reasonably large.",
    )


history = conversation.get_history()

total_chars = sum(
    len(message["content"])
    for message in history
)

print("Messages retained:", len(history))
print("Characters retained:", total_chars)

print("\nHistory:")
for message in history:
    print(message["content"])