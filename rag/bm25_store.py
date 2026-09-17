from rank_bm25 import BM25Okapi


class BM25Store:

    def __init__(self, documents: list[dict]):
        self.documents = documents

        self.tokenized_documents = [
            document["text"].lower().split()
            for document in documents
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_documents
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search documents using BM25."""

        if not query.strip():
            return []

        query_tokens = query.lower().split()

        scores = self.bm25.get_scores(
            query_tokens
        )

        ranked_indexes = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )

        results = []

        # for index in ranked_indexes[:top_k]:

        #     if scores[index] <= 0:
        #         continue

        #     document = self.documents[index]

        #     results.append(
        #         {
        #             "id": document["id"],
        #             "text": document["text"],
        #             "metadata": document["metadata"],
        #             "score": float(scores[index]),
        #         }
        #     )

        for index in ranked_indexes[:top_k]:

            document = self.documents[index]

            results.append(
                {
                    "id": document["id"],
                    "text": document["text"],
                    "metadata": document["metadata"],
                    "score": float(scores[index]),
                }
            )

        return results