from rag.intent_classifier import QueryIntentClassifier


classifier = QueryIntentClassifier()

queries = [
    "Why did the payment fail?",
    "What does INSUFFICIENT_FUNDS mean?",
    "Why is order 1001 failing?",
    "Is the payment gateway healthy?",
]

for query in queries:
    print("\nQuery:", query)

    result = classifier.classify(query)

    print("Intent:", result.intent)
    print("Sections:", result.sections)
    print("Keywords:", result.keywords)