import hashlib
import math
from abc import ABC, abstractmethod

import numpy as np

from app.providers.stopwords import tokenize_counts

EMBEDDING_DIM = 384


class EmbeddingProvider(ABC):
    dim: int = EMBEDDING_DIM

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashing bag-of-words embedding.

    ponytail: avoids a real sentence-embedding model (torch/sentence-transformers,
    or a paid embeddings API) so retrieval works offline with zero downloads/keys.
    Stable and comparable across runs, adequate for a small demo corpus. Upgrade
    trigger: eval suite shows semantic recall is too weak for real content -> swap
    in Voyage/OpenAI/Cohere embeddings behind this same interface.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float64)
        # Log-scaled term frequency, not just presence/absence: a chunk that
        # mentions its actual topic repeatedly must end up more strongly in
        # that direction than one that mentions the same word once in
        # passing (see providers/stopwords.py's tokenize_counts docstring).
        for token, count in tokenize_counts(text).items():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign * (1.0 + math.log(count))
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


def get_embedding_provider() -> EmbeddingProvider:
    return MockEmbeddingProvider()
