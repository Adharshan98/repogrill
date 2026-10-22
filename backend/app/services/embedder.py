"""Turns text into embeddings: lists of numbers that capture meaning.

Texts with similar meaning get similar numbers, which lets us search code by
meaning ("login logic") instead of exact words ("verify_user").

We use a small free model that runs locally, so no API key or cost is needed.
"""
import os
from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 numbers per text, ~70 MB download


@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    # Loading the model is slow, so do it once and reuse it.
    # FASTEMBED_CACHE_DIR lets Docker keep the downloaded model inside the image.
    return TextEmbedding(MODEL_NAME, cache_dir=os.getenv("FASTEMBED_CACHE_DIR"))


def embed(texts: list[str]) -> np.ndarray:
    """Return one row of numbers per text, scaled to length 1 so a dot product = similarity."""
    vectors = np.array(list(get_model().embed(texts)), dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
