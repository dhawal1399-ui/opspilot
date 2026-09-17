from rag.hybrid import HybridRetriever


retriever = HybridRetriever()


query = "Why was the customer's payment rejected?"


# results = retriever.search(
#     query="payment failure",
#     top_k=5,
#     metadata_filters={
#         "source": "payment_service.md"
#     },
# )
results = retriever.search(
    query="payment failure",
    top_k=5,
    metadata_filters={
        "source": "payment_service.md"
    },
)

print("\n==============================")
print("HYBRID SEARCH")
print("==============================")


for rank, result in enumerate(
    results,
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
        "RRF Score:",
        result["rrf_score"],
    )

    print(
        "Text:",
        result["text"][:300],
    )