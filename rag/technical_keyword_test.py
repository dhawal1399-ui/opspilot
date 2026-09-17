from rag.conversation import ConversationManager
from rag.intent_classifier import QueryIntentClassifier


conversation = ConversationManager()
classifier = QueryIntentClassifier()

queries = [
    "Why did the payment gateway decline the request?",
    "Why did the API request timeout?",
    "Is the payment service healthy?",
    "Why is the WebSocket connection failing?",
    "What caused the database connection error?",
]

for query in queries:
    print("\n" + "=" * 60)
    print("Original:", query)

    rewritten = conversation.rewrite_query(query)

    print("Rewritten:", rewritten)

    intent = classifier.classify(rewritten)

    print("Intent:", intent.intent)
    print("Sections:", intent.sections)
    print("Keywords:", intent.keywords)