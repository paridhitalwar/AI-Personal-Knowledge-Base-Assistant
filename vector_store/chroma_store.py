from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import numpy as np

from app.config import settings
from models.document import Chunk, RetrievedChunk
from vector_store.embeddings import embed_texts

# NOTE: Switched to a simple JSON-based vector store to resolve stability issues with ChromaDB on Windows.
# This implementation provides the same interface but uses a local JSON file for storage.

class ChromaStore:
    """Simple file-based vector store replacing ChromaDB for stability."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.persist_dir / f"{self.collection_name}.json"
        
        self.data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load vector store: {e}. Starting fresh.")
                self.data = {}

    def _save(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f)

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        """Upsert a batch of chunks into the collection."""
        chunk_list = list(chunks)
        if not chunk_list:
            return

        texts = [c.content for c in chunk_list]
        embeddings = embed_texts(texts)

        for chunk, embedding in zip(chunk_list, embeddings):
            self.data[chunk.id] = {
                "chunk_id": chunk.id, # store ID explicitly in value too
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": embedding
            }
        self._save()

    def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks belonging to a given document."""
        keys_to_delete = [
            k for k, v in self.data.items() 
            if v["metadata"].get("document_id") == document_id
        ]
        if keys_to_delete:
            for k in keys_to_delete:
                del self.data[k]
            self._save()

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """Query the collection with a natural-language text."""
        if not query_text or not self.data:
            return []

        q_vec = np.array(embed_texts([query_text])[0])
        q_norm = np.linalg.norm(q_vec)
        
        results = []
        
        for cid, item in self.data.items():
            # Check 'where' filter
            if where:
                match = True
                for k, v in where.items():
                    # Support simple equality
                    if item["metadata"].get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            d_vec = np.array(item["embedding"])
            d_norm = np.linalg.norm(d_vec)
            
            if q_norm == 0 or d_norm == 0:
                dist = 1.0 # Max distance
            else:
                cosine_sim = np.dot(q_vec, d_vec) / (q_norm * d_norm)
                dist = 1.0 - cosine_sim # Convert similarity (1=good) to distance (0=good)
            
            if score_threshold is not None and dist > score_threshold:
                continue
                
            results.append((dist, cid, item))

        # Sort by distance (ascending)
        results.sort(key=lambda x: x[0])
        results = results[:top_k]

        retrieved: List[RetrievedChunk] = []
        for dist, cid, item in results:
            retrieved.append(
                RetrievedChunk(
                    id=cid,
                    content=item["content"],
                    metadata=item["metadata"],
                    score=float(dist),
                )
            )

        return retrieved
