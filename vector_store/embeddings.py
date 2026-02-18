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


import os

# Force usage of PyTorch and disable TensorFlow to prevent broken DLL imports
os.environ["USE_TORCH"] = "1"
os.environ["USE_TF"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # Suppress TF logging

from sentence_transformers import SentenceTransformer

# Load model once
_model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings using a real SentenceTransformer model.
    Returns a list of embedding vectors.
    """
    if not texts:
        return []

    # Encode texts
    embeddings = _model.encode(texts)
    
    # Convert numpy arrays to lists for JSON serialization compatibility
    return embeddings.tolist()


def embed_query(text: str) -> List[float]:
    """
    Convenience helper to embed a single query string.
    """
    if not text:
        return []

    return embed_texts([text])[0]
