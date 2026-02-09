from dataclasses import dataclass
from typing import List, Optional

from models.document import RetrievedChunk
from vector_store.chroma_store import ChromaStore


@dataclass
class RetrievalConfig:
    top_k: int = 5
    score_threshold: Optional[float] = None


class Retriever:
    """High-level retrieval interface over the vector store."""

    def __init__(self, store: ChromaStore, config: Optional[RetrievalConfig] = None) -> None:
        self.store = store
        self.config = config or RetrievalConfig()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        if not query:
            return []

        k = top_k or self.config.top_k
        threshold = score_threshold if score_threshold is not None else self.config.score_threshold
        return self.store.query(query_text=query, top_k=k, score_threshold=threshold)

