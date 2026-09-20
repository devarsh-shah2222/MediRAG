from sqlalchemy.types import JSON as SA_JSON
from sqlalchemy.types import TypeDecorator


class EmbeddingVector(TypeDecorator):
    """Stores a fixed-dimension embedding vector.

    ponytail: uses pgvector's native column on Postgres (ready for a future
    ivfflat/HNSW index if corpus size ever needs ANN search) and falls back to
    a plain JSON array on any other dialect, so tests run against SQLite with
    zero infra. Similarity is always computed in Python over the fetched rows
    (see app/rag/retrieval.py) rather than via SQL vector operators, so the
    fallback has no behavioral difference at MVP demo-corpus scale (dozens to
    low thousands of chunks). Upgrade trigger: corpus size makes brute-force
    Python cosine similarity too slow, then switch to pgvector's `<=>` operator
    with an ivfflat index.
    """

    impl = SA_JSON
    cache_ok = True

    def __init__(self, dim: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(SA_JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return list(value)
