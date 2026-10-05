from rag.conversation import ConversationManager
from rag.intent_classifier import QueryIntentClassifier


conversation = ConversationManager()
classifier = QueryIntentClassifier()

queries = [
    "What does INSUFFICIENT_FUNDS mean?",
    "Why did I get INSUFFICIENT_FUNDS?",
    "Explain the INSUFFICIENT_FUNDS error.",
]

for query in queries:
    print("\nQuery:", query)

    rewritten = conversation.rewrite_query(query)

    print("Rewritten:", rewritten)

    intent = classifier.classify(rewritten)

    print("Intent:", intent.intent)
    print("Sections:", intent.sections)
    print("Keywords:", intent.keywords)