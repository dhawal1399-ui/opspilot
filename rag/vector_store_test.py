from rag.ingestion import ingest_all_documents
from rag.vector_store import VectorStore


documents = ingest_all_documents()

store = VectorStore()

store.add_documents(documents)

results = store.search(
    "Why did the payment fail?",
    top_k=3,
)

print("\nSEMANTIC SEARCH RESULTS:")

for result in results:
    print("\nID:", result["id"])
    print("Source:", result["metadata"]["source"])
    print("Distance:", result["distance"])
    print("Text:", result["text"][:300])