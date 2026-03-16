"""Embedding engine — generates and manages vector embeddings for memory entries."""

import struct
from pathlib import Path
from typing import Optional

import numpy as np

# Lazy-load the model to avoid slow import at module level
_model = None
_model_name = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_model_name)
    return _model


def embed_text(text: str) -> bytes:
    """Generate an embedding for a single text string. Returns bytes for SQLite BLOB storage."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.astype(np.float32).tobytes()


def embed_texts(texts: list[str]) -> list[bytes]:
    """Batch-embed multiple texts. More efficient than calling embed_text in a loop."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.astype(np.float32).tobytes() for v in vectors]


def cosine_similarity(embedding_a: bytes, embedding_b: bytes) -> float:
    """Compute cosine similarity between two embeddings stored as bytes."""
    a = np.frombuffer(embedding_a, dtype=np.float32)
    b = np.frombuffer(embedding_b, dtype=np.float32)
    return float(np.dot(a, b))  # Already normalized, so dot = cosine


def bytes_to_vector(embedding: bytes) -> np.ndarray:
    """Convert stored bytes back to numpy array."""
    return np.frombuffer(embedding, dtype=np.float32)
