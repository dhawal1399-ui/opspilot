import json
from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt"}

DOCS_DIR = Path("docs")
PROCESSED_DIR = Path("data/processed")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def parse_document(file_path: Path) -> str:
    """Read and return the text content of a supported document."""

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type: {file_path.suffix}"
        )

    return file_path.read_text(encoding="utf-8")


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping word-based chunks."""

    if not text.strip():
        return []

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size

        chunk = " ".join(words[start:end])

        if chunk.strip():
            chunks.append(chunk)

        if end >= len(words):
            break

        start = end - chunk_overlap

    return chunks


def extract_sections(text: str) -> list[dict]:
    """
    Split Markdown documentation into sections.

    Each section starts with a Markdown heading.
    """

    lines = text.splitlines()

    sections = []

    current_section = None
    current_lines = []

    for line in lines:

        stripped = line.strip()

        if stripped.startswith("# "):

            if current_section is not None:
                sections.append(
                    {
                        "section": current_section,
                        "text": "\n".join(current_lines).strip(),
                    }
                )

            current_section = stripped[2:].strip()

            current_lines = [line]

        elif stripped.startswith("## "):

            if current_section is not None:
                sections.append(
                    {
                        "section": current_section,
                        "text": "\n".join(current_lines).strip(),
                    }
                )

            current_section = stripped[3:].strip()

            current_lines = [line]

        else:
            current_lines.append(line)

    if current_section is not None:
        sections.append(
            {
                "section": current_section,
                "text": "\n".join(current_lines).strip(),
            }
        )

    return sections


def generate_chunk_metadata(
    file_path: Path,
    chunk_index: int,
    total_chunks: int,
    section: str | None = None,
) -> dict:
    """Generate metadata for a document chunk."""

    metadata = {
        "source": file_path.name,
        "file_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
    }

    if section is not None:
        metadata["section"] = section

    return metadata


def ingest_document(file_path: Path) -> list[dict]:
    """Parse, section, chunk, and generate metadata."""

    text = parse_document(file_path)

    sections = extract_sections(text)

    documents = []

    global_chunk_index = 0

    # Process section by section so each chunk knows its section.
    for section_data in sections:

        section_name = section_data["section"]
        section_text = section_data["text"]

        chunks = chunk_text(
            section_text,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        for chunk in chunks:

            metadata = generate_chunk_metadata(
                file_path=file_path,
                chunk_index=global_chunk_index,
                total_chunks=0,
                section=section_name,
            )

            documents.append(
                {
                    "id": f"{file_path.stem}_{global_chunk_index}",
                    "text": chunk,
                    "metadata": metadata,
                }
            )

            global_chunk_index += 1

    total_chunks = len(documents)

    for document in documents:
        document["metadata"]["total_chunks"] = total_chunks

    return documents


def ingest_all_documents() -> list[dict]:
    """Ingest all supported documents from the docs directory."""

    all_chunks = []

    for file_path in sorted(DOCS_DIR.iterdir()):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        chunks = ingest_document(file_path)

        all_chunks.extend(chunks)

    return all_chunks


def save_processed_documents(
    documents: list[dict],
) -> None:
    """Save processed document chunks and metadata."""

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = PROCESSED_DIR / "documents.json"

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            documents,
            file,
            indent=2,
            ensure_ascii=False,
        )


def ingest() -> list[dict]:
    """Run the complete document ingestion pipeline."""

    documents = ingest_all_documents()

    save_processed_documents(documents)

    return documents


if __name__ == "__main__":
    documents = ingest()

    print(
        f"Ingested {len(documents)} document chunks."
    )