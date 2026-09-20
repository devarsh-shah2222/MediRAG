import math
import time
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session, joinedload

from app.models import RAGChunk, RAGDocument, RetrievalLog
from app.providers.embeddings import EmbeddingProvider
from app.providers.stopwords import tokenize, tokenize_counts

TOP_K = 5
AUTHORITATIVE_SOURCE_TYPES = {"government", "who", "regulatory"}
AUTHORITY_BOOST = 0.05
SUFFICIENCY_THRESHOLD = 0.28
# A word overlapping alone (see _lexical_score) is only trusted if its IDF is
# at least this fraction of the maximum possible IDF for the current
# candidate set (i.e. a word appearing in only one document). Expressed as a
# ratio of the achievable max, not an absolute IDF value, so it holds
# regardless of how many documents are in the candidate set -- a fixed
# absolute cutoff tuned against the ~7-document real corpus made even a
# maximally-rare word fail in a 3-document test fixture, where IDF values
# are inherently smaller.
RARE_WORD_RELATIVE_THRESHOLD = 0.65


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    heading: str | None
    content: str
    score: float
    source_name: str
    document_title: str
    source_type: str
    url: str | None
    published_date: object | None


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _compute_idf(doc_token_sets: list[set[str]]) -> dict[str, float]:
    """Inverse document frequency over the current candidate set (not the
    whole corpus): a word that appears in nearly every candidate document
    ("condition", "commonly") is uninformative and should barely move the
    score, while a word that appears in only one or two documents
    ("hypertension", "paracetamol") is a strong topic signal even if it's
    the only word the query and the source happen to share.

    ponytail: computed fresh per retrieval call over the (small) candidate
    set rather than precomputed/cached over the full corpus. Simplest thing
    that is still correct at demo-corpus scale; recompute cost is
    proportional to the same candidate set retrieval already scores.
    """
    n_docs = len(doc_token_sets)
    doc_freq: dict[str, int] = {}
    for tokens in doc_token_sets:
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    return {token: math.log((n_docs + 1) / (df + 1)) + 1 for token, df in doc_freq.items()}


def _lexical_score(query_tokens: set[str], content_counts: Counter, idf: dict[str, float], max_idf: float) -> float:
    """IDF-weighted term overlap, log-scaled by how often a term appears in
    THIS chunk (1 + log(tf): exactly 1x at one mention -- same credit a
    single match always got -- growing beyond that for repeated mentions,
    uncapped). Without the log term, a chunk that mentions "the common cold"
    once in passing (e.g. a pain reliever's indications list) scored
    identically to a chunk that's actually about the common cold and says so
    repeatedly -- caught live via a real query returning drug labels instead
    of the actual Common Cold reference document. A pure saturation curve
    (e.g. tf / (tf + 1)) fixes that but also *halves* the credit for a
    single rare-word match, which is exactly the strong, sparse signal
    (e.g. "hypertension" appearing once) IDF weighting exists to reward --
    caught by a regression test breaking when that was tried.
    """
    if not query_tokens or not content_counts:
        return 0.0
    matched_tokens = [t for t in query_tokens if content_counts.get(t, 0) > 0]
    if not matched_tokens:
        return 0.0
    # A single overlapping word is only trustworthy on its own if it's
    # genuinely rare across the candidate set. Caught live: a real query
    # about a nonexistent condition shared only the word "treatment" with a
    # real MedlinePlus article -- appearing in over half the candidate
    # documents, "treatment" isn't rare, but it appeared twice in that one
    # chunk, and the tf log-boost above let that repetition alone clear the
    # evidence-sufficiency bar. Two distinct overlapping words is still
    # trusted regardless of rarity; it's specifically the "just one word,
    # and it's a common one" case that isn't.
    if len(matched_tokens) == 1 and idf.get(matched_tokens[0], 1.0) < RARE_WORD_RELATIVE_THRESHOLD * max_idf:
        return 0.0
    matched_weight = sum(idf.get(t, 1.0) * (1.0 + math.log(content_counts[t])) for t in matched_tokens)
    total_weight = sum(idf.get(t, 1.0) for t in query_tokens)
    return matched_weight / total_weight if total_weight else 0.0


def hybrid_retrieve(
    db: Session,
    query: str,
    embedding_provider: EmbeddingProvider,
    medical_topic: str | None = None,
    language: str | None = None,
    message_id: str | None = None,
) -> list[RetrievedChunk]:
    """Hybrid retrieval: semantic (cosine over embeddings) + lexical (token
    overlap) + a small authority/freshness boost, weighted and merged.

    ponytail: similarity/scoring runs in Python over rows fetched by SQL,
    rather than Postgres full-text (`ts_rank`) + pgvector's `<=>` operator.
    This keeps retrieval logic dialect-independent and unit-testable without a
    running Postgres, at the cost of not using DB-side ANN indexing. Fine at
    demo-corpus scale (dozens–low thousands of chunks). Upgrade trigger: corpus
    size makes brute-force scoring too slow -> move scoring into SQL/pgvector.
    """
    start = time.perf_counter()

    q = db.query(RAGChunk).options(joinedload(RAGChunk.document).joinedload(RAGDocument.source))
    q = q.join(RAGDocument)
    if medical_topic:
        q = q.filter(RAGDocument.medical_topic == medical_topic)
    if language:
        q = q.filter(RAGDocument.language == language)
    candidates = q.all()

    if not candidates:
        return []

    query_embedding = embedding_provider.embed(query)
    query_tokens = tokenize(query)

    chunk_counts = {chunk.id: tokenize_counts(chunk.content) for chunk in candidates}
    doc_tokens: dict[str, set[str]] = {}
    for chunk in candidates:
        doc_tokens.setdefault(chunk.document_id, set()).update(chunk_counts[chunk.id].keys())
    idf = _compute_idf(list(doc_tokens.values()))
    max_idf = math.log((len(doc_tokens) + 1) / 2) + 1

    scored: list[RetrievedChunk] = []
    for chunk in candidates:
        doc = chunk.document
        source = doc.source
        semantic = _cosine(query_embedding, chunk.embedding)
        lexical = _lexical_score(query_tokens, chunk_counts[chunk.id], idf, max_idf)
        score = 0.65 * semantic + 0.35 * lexical
        if source.source_type in AUTHORITATIVE_SOURCE_TYPES:
            score += AUTHORITY_BOOST
        scored.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                heading=chunk.heading,
                content=chunk.content,
                score=round(score, 4),
                source_name=source.name,
                document_title=doc.title,
                source_type=source.source_type,
                url=doc.url,
                published_date=doc.publication_date,
            )
        )

    scored.sort(key=lambda c: c.score, reverse=True)
    # When the caller already identified a specific medicine by exact
    # name/alias match (medical_topic set), that's a stronger relevance
    # signal than any lexical/semantic score -- the sufficiency bar exists to
    # decide "is this document relevant at all", which is already answered.
    # Applying it anyway caused a real failure: a real OTC label's "Uses"
    # section never restates the drug's own name (a genuine, common label
    # pattern, not a data error), so it could never score high enough to
    # clear the bar on its own, even though it's exactly the content a
    # "what is <brand name> used for" question needs. Without the bar, the
    # named document's own top chunks are trusted directly.
    threshold = SUFFICIENCY_THRESHOLD if not medical_topic else 0.0
    top = [c for c in scored[:TOP_K] if c.score >= threshold]

    latency_ms = int((time.perf_counter() - start) * 1000)
    db.add(
        RetrievalLog(
            message_id=message_id,
            query=query,
            retrieved_chunk_ids=[c.chunk_id for c in top],
            retrieval_count=len(top),
            latency_ms=latency_ms,
        )
    )

    return top


def is_evidence_sufficient(chunks: list[RetrievedChunk]) -> bool:
    return len(chunks) > 0
