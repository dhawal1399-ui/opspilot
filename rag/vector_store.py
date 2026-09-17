from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_DIR = Path("data/chroma")

COLLECTION_NAME = "opspilot_documents"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class VectorStore:

    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    def add_documents(self, documents: list[dict]) -> None:
        """Generate embeddings and store documents in ChromaDB."""

        if not documents:
            return

        ids = [
            document["id"]
            for document in documents
        ]

        texts = [
            document["text"]
            for document in documents
        ]

        metadatas = [
            document["metadata"]
            for document in documents
        ]

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
        ).tolist()

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Perform semantic vector search."""

        query_embedding = self.model.encode(
            query,
            convert_to_numpy=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        output = []

        for index in range(len(documents)):
            output.append(
                {
                    "id": ids[index],
                    "text": documents[index],
                    "metadata": metadatas[index],
                    "distance": distances[index],
                }
            )

        return output