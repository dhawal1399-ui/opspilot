from rag.bm25_store import BM25Store
from rag.ingestion import ingest_all_documents
from rag.vector_store import VectorStore


def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """Combine ranked result lists using Reciprocal Rank Fusion."""

    scores = {}
    documents = {}

    for results in result_lists:

        for rank, document in enumerate(
            results,
            start=1,
        ):
            document_id = document["id"]

            scores[document_id] = (
                scores.get(document_id, 0)
                + 1 / (k + rank)
            )

            documents[document_id] = document

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True,
    )

    output = []

    for document_id in ranked_ids:

        document = documents[document_id].copy()

        document["rrf_score"] = scores[document_id]

        output.append(document)

    return output


class HybridRetriever:

    def __init__(self):
        self.documents = ingest_all_documents()

        self.vector_store = VectorStore()

        self.vector_store.add_documents(
            self.documents
        )

        self.bm25_store = BM25Store(
            self.documents
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filters: dict | None = None,
    ) -> list[dict]:

        semantic_results = self.vector_store.search(
            query=query,
            top_k=top_k,
        )

        keyword_results = self.bm25_store.search(
            query=query,
            top_k=top_k,
        )

        hybrid_results = reciprocal_rank_fusion(
            [
                semantic_results,
                keyword_results,
            ]
        )

        hybrid_results = filter_by_metadata(
            hybrid_results,
            metadata_filters,
        )

        return hybrid_results[:top_k]



def filter_by_metadata(
    documents: list[dict],
    filters: dict | None = None,
) -> list[dict]:
    """Filter documents using metadata values."""

    if not filters:
        return documents

    filtered = []

    for document in documents:

        metadata = document.get(
            "metadata",
            {},
        )

        matches = all(
            metadata.get(key) == value
            for key, value in filters.items()
        )

        if matches:
            filtered.append(document)

    return filtered

# def reciprocal_rank_fusion(
#     result_lists: list[list[dict]],
#     k: int = 60,
# ) -> list[dict]:
#     """
#     Combine multiple ranked result lists using
#     Reciprocal Rank Fusion.
#     """

#     scores = {}
#     documents = {}

#     for results in result_lists:

#         for rank, document in enumerate(
#             results,
#             start=1,
#         ):
#             document_id = document["id"]

#             scores[document_id] = (
#                 scores.get(document_id, 0)
#                 + 1 / (k + rank)
#             )

#             documents[document_id] = document

#     ranked_ids = sorted(
#         scores,
#         key=scores.get,
#         reverse=True,
#     )

#     output = []

#     for document_id in ranked_ids:

#         document = documents[document_id].copy()

#         document["rrf_score"] = scores[
#             document_id
#         ]

#         output.append(document)

#     return output

