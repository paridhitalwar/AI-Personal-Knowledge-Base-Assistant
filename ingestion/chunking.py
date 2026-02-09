from typing import Iterable, List

from models.document import Chunk, Document


def simple_text_chunker(
    doc: Document,
    chunk_size_chars: int = 3500,
    chunk_overlap_chars: int = 400,
) -> List[Chunk]:
    """Naive character-based chunker with overlap.

    This keeps implementation simple and does not rely on external NLP libs.
    """
    text = doc.text or ""
    chunks: List[Chunk] = []
    if not text:
        return chunks

    start = 0
    index = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size_chars, text_len)
        content = text[start:end]

        chunk_id = f"{doc.id}::chunk_{index}"
        metadata = {
            "chunk_id": chunk_id,
            "document_id": doc.id,
            "source": doc.source,
            "source_id": doc.source_id,
            "title": doc.title,
            "url": doc.url,
            "path": doc.path,
            "chunk_index": index,
        }

        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=doc.id,
                content=content,
                metadata=metadata,
            )
        )

        if end == text_len:
            break

        start = max(0, end - chunk_overlap_chars)
        index += 1

    return chunks


def chunk_documents(docs: Iterable[Document]) -> List[Chunk]:
    """Chunk a list of documents into Chunk objects."""
    all_chunks: List[Chunk] = []
    for doc in docs:
        all_chunks.extend(simple_text_chunker(doc))
    return all_chunks

