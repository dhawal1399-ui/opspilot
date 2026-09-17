from rag.retrieval import RAGRetriever


retriever = RAGRetriever()


query = "Why was the customer's payment rejected?"


results = retriever.retrieve(
    query=query,
    candidate_k=5,
    top_k=3,
)


print("\n==============================")
print("FINAL RAG RETRIEVAL")
print("==============================")


for rank, result in enumerate(
    results,
    start=1,
):
    print(f"\nRank: {rank}")

    print(
        "Source:",
        result["metadata"]["source"],
    )

    print(
        "Section:",
        result["metadata"].get("section"),
    )

    print(
        "Rerank Score:",
        result["rerank_score"],
    )

    print(
        "Text:",
        result["text"][:400],
    )