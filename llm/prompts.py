from typing import List

from models.document import RetrievedChunk


def build_system_prompt() -> str:
    return (
        "You are an AI assistant that answers questions based only on the provided context. "
        "Use the context to produce clear, concise answers. "
        "If the answer is not contained in the context, say you do not know. "
        "Cite sources as [Source 1], [Source 2], etc. where appropriate."
    )


def format_context(chunks: List[RetrievedChunk]) -> str:
    formatted_parts: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.metadata or {}
        title = meta.get("title") or "Untitled"
        source = meta.get("source") or "unknown"
        url = meta.get("url") or ""
        header = f"[Source {i}] {title} (from {source}{', ' + url if url else ''})"
        formatted_parts.append(f"{header}\n{chunk.content}\n")
    return "\n\n".join(formatted_parts)


def build_user_prompt(question: str, chunks: List[RetrievedChunk]) -> str:
    context_str = format_context(chunks)
    return (
        "Context:\n"
        "--------\n"
        f"{context_str}\n\n"
        "--------\n"
        f"Question: {question}\n\n"
        "Instructions:\n"
        "- Answer based only on the context above.\n"
        "- If the answer is not in the context, say that you do not know.\n"
        "- When using information from a source, reference it like [Source 1], [Source 2], etc.\n"
    )

