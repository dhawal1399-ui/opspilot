from pathlib import Path

from rag.ingestion import (
    chunk_text,
    ingest_document,
)


# file_path = Path("docs/payment_service.md")

# documents = ingest_document(file_path)

# print("Number of chunks:", len(documents))

# for document in documents:
#     print("\nID:", document["id"])
#     print("Metadata:", document["metadata"])
#     print("Text:", document["text"][:200])


text = " ".join(
    f"word{i}"
    for i in range(1200)
)

chunks = chunk_text(
    text,
    chunk_size=500,
    chunk_overlap=100,
)

print("Number of chunks:", len(chunks))

print("\nFirst chunk starts with:")
print(chunks[0][:100])

print("\nSecond chunk starts with:")
print(chunks[1][:100])