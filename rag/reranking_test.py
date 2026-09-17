from rag.hybrid import HybridRetriever
from rag.reranking import Reranker


query = "Why was the customer's payment rejected?"


retriever = HybridRetriever()

hybrid_results = retriever.search(
    query=query,
    top_k=5,
)


print("\n==============================")
print("BEFORE RERANKING")
print("==============================")


for rank, result in enumerate(
    hybrid_results,
    start=1,
):
    print(
        f"{rank}. "
        f"{result['metadata']['source']} "
        f"(RRF: {result['rrf_score']})"
    )


reranker = Reranker()

reranked_results = reranker.rerank(
    query=query,
    documents=hybrid_results,
    top_k=3,
)


print("\n==============================")
print("AFTER CROSSENCODER RERANKING")
print("==============================")


for rank, result in enumerate(
    reranked_results,
    start=1,
):
    print(
        f"\nRank: {rank}"
    )

    print(
        "Source:",
        result["metadata"]["source"],
    )

    print(
        "Rerank Score:",
        result["rerank_score"],
    )

    print(
        "Text:",
        result["text"][:300],
    )