from rag.bm25_store import BM25Store
from rag.ingestion import ingest_all_documents
from rag.vector_store import VectorStore


documents = ingest_all_documents()

vector_store = VectorStore()
vector_store.add_documents(documents)

bm25_store = BM25Store(documents)


query = "gateway availability"


print("\n==============================")
print("SEMANTIC SEARCH")
print("==============================")

semantic_results = vector_store.search(
    query,
    top_k=3,
)

for result in semantic_results:
    print(
        result["metadata"]["source"],
        result.get("distance"),
    )


print("\n==============================")
print("BM25 SEARCH")
print("==============================")

keyword_results = bm25_store.search(
    query,
    top_k=3,
)

for result in keyword_results:
    print(
        result["metadata"]["source"],
        result["score"],
    )