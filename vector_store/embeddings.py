from functools import lru_cache
from typing import List
import hashlib
import numpy as np


@lru_cache(maxsize=1)
def _get_embedder():
    """
    Simple hash-based embedding for testing.
    This creates deterministic embeddings for testing purposes.
    """
    return None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Create simple hash-based embeddings for testing.
    Returns a list of embedding vectors.
    """
    if not texts:
        return []

    embeddings = []
    for text in texts:
        # Create a simple 384-dimensional embedding (same as MiniLM)
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # Convert hash to float values
        embedding = []
        for i in range(0, len(hash_hex), 2):
            hex_pair = hash_hex[i:i+2]
            val = int(hex_pair, 16) / 255.0  # Normalize to 0-1
            embedding.append(val)
        
        # Pad or truncate to 384 dimensions
        while len(embedding) < 384:
            embedding.append(0.0)
        embedding = embedding[:384]
        
        embeddings.append(embedding)

    return embeddings


def embed_query(text: str) -> List[float]:
    """
    Convenience helper to embed a single query string.
    """
    if not text:
        return []

    return embed_texts([text])[0]
