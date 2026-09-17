
from rag.hybrid import HybridRetriever
from rag.reranking import Reranker


class RAGRetriever:

    def __init__(self):
        self.hybrid_retriever = HybridRetriever()
        self.reranker = Reranker()

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        candidate_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve and rerank documentation.

        candidate_k:
            Number of candidates retrieved by semantic + BM25.

        top_k:
            Number of final documents returned to the LLM.
        """

        candidates = self.hybrid_retriever.search(
            query=query,
            top_k=candidate_k,
        )

        reranked = self.reranker.rerank(
            query=query,
            documents=candidates,
            top_k=top_k,
        )

        return reranked



# from pathlib import Path




# DOCS_DIR = Path("docs")


# def load_documents() -> list[dict]:
#     """Load markdown documentation files."""
#     documents = []

#     for file_path in DOCS_DIR.glob("*.md"):
#         content = file_path.read_text(encoding="utf-8")

#         documents.append(
#             {
#                 "source": file_path.name,
#                 "content": content,
#             }
#         )

#     return documents


# def search(query: str, top_k: int = 5) -> list[dict]:
#     """
#     Search documentation using simple keyword matching.

#     This provides the retrieval interface that the Documentation
#     MCP server consumes. The underlying implementation can later
#     be replaced with the full hybrid RAG pipeline.
#     """

#     documents = load_documents()

#     if not query.strip():
#         return []

#     query_terms = {
#         term.lower()
#         for term in query.split()
#         if term.strip()
#     }

#     results = []

#     for document in documents:
#         content = document["content"].lower()

#         score = sum(
#             1
#             for term in query_terms
#             if term in content
#         )

#         if score > 0:
#             results.append(
#                 {
#                     "source": document["source"],
#                     "content": document["content"],
#                     "score": score,
#                 }
#             )

#     results.sort(
#         key=lambda item: item["score"],
#         reverse=True,
#     )

#     return results[:top_k]