from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from models.document import Chunk, RetrievedChunk
from vector_store.embeddings import embed_texts


class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Adapter to let Chroma call our local embedding model."""

    def __call__(self, texts: Sequence[str]) -> List[List[float]]:  # type: ignore[override]
        return embed_texts(list(texts))


class ChromaStore:
    """Wrapper around a ChromaDB collection for the personal knowledge base."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name

        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=LocalEmbeddingFunction(),
        )

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        """Upsert a batch of chunks into the collection."""
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in chunks:
            ids.append(chunk.id)
            documents.append(chunk.content)
            metadatas.append(chunk.metadata)

        if not ids:
            return

        # Embeddings are computed via the collection's embedding function.
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks belonging to a given document."""
        self.collection.delete(where={"document_id": document_id})

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Query the collection with a natural-language text."""
        if not query_text:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where if where else None,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved: List[RetrievedChunk] = []
        for doc, meta, dist in zip(docs, metas, distances):
            if score_threshold is not None and dist is not None and dist > score_threshold:
                # Chroma uses distance; smaller is better. Threshold is optional.
                continue

            chunk_id = meta.get("chunk_id") or meta.get("id") or ""
            score = float(dist) if dist is not None else 0.0
            retrieved.append(
                RetrievedChunk(
                    id=chunk_id,
                    content=doc,
                    metadata=meta,
                    score=score,
                )
            )

        return retrieved

