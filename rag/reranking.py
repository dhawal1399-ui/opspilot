from sentence_transformers import CrossEncoder


RERANKER_MODEL = (
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


class Reranker:

    def __init__(self):
        self.model = CrossEncoder(
            RERANKER_MODEL
        )

    def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:

        if not documents:
            return []

        pairs = [
            (query, document["text"])
            for document in documents
        ]

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(documents, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        results = []

        for document, score in ranked[:top_k]:

            result = document.copy()

            result["rerank_score"] = float(score)

            results.append(result)

        return results