"""Stores a repo's chunks with their embeddings and finds the chunks closest to a question."""
from dataclasses import dataclass

import numpy as np

from app.services.chunker import Chunk
from app.services.embedder import embed


def chunk_to_text(chunk: Chunk) -> str:
    # Add the file and function name so they count towards the meaning too
    header = f"{chunk.language} {chunk.kind} {chunk.name} in {chunk.file}".replace("  ", " ")
    return f"{header}\n{chunk.content}"


@dataclass
class SearchResult:
    chunk: Chunk
    score: float  # similarity from -1 to 1; higher means closer in meaning


class CodeIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray | None = None):
        """Embed the chunks, or reuse `vectors` that were saved earlier (one row per chunk)."""
        self.chunks = chunks
        if vectors is not None:
            self.vectors = vectors
        else:
            self.vectors = embed([chunk_to_text(c) for c in chunks]) if chunks else np.empty((0, 384))

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not self.chunks:
            return []
        query_vector = embed([query])[0]
        scores = self.vectors @ query_vector  # one similarity score per chunk
        best = np.argsort(scores)[::-1][:top_k]  # highest scores first
        return [SearchResult(self.chunks[i], float(scores[i])) for i in best]
