from app.models import RAGSource
from app.providers.embeddings import MockEmbeddingProvider
from app.rag.ingest import ingest_document
from app.rag.retrieval import hybrid_retrieve

PARACETAMOL_TEXT = """# Paracetamol

## Uses
Paracetamol is commonly used to relieve mild pain and reduce fever.

## Warnings
Taking more than the recommended dose can cause serious liver damage.
"""

UNRELATED_TEXT = """# Seasonal Allergies

## Uses
Antihistamines are commonly used to relieve sneezing and itchy eyes caused by pollen.
"""

# Deliberately never uses the word "managed" -- see
# test_retrieves_on_topic_paraphrase_word_not_present_in_source.
HYPERTENSION_TEXT = """# Hypertension

## What It Is
Hypertension means blood pressure in the arteries is higher than the typical healthy range.

## Self-Care
Reducing salt intake and regular activity are commonly documented approaches.
"""

# Mirrors a real OTC pain-reliever label: mentions "the common cold" exactly
# once, in passing, as one of several reasons someone might take it -- it is
# not a document about the common cold. See
# test_repeated_topic_word_outranks_incidental_single_mention.
PAIN_RELIEVER_TEXT = """# Pain Reliever Tablets

## Uses
Temporarily relieves minor aches and pains due to headache, the common cold, backache, and toothache.
"""

COMMON_COLD_TEXT = """# Common Cold

## What It Is
The common cold is a mild viral infection of the nose and throat. Cold symptoms usually include a
runny nose, sneezing, and a mild cough. Most colds get better on their own within a week or two.
Rest and fluids are the usual advice for a cold.
"""


def _seed(db_session):
    embedding_provider = MockEmbeddingProvider()
    source = RAGSource(name="Test Source", source_type="demo_reference", jurisdiction="global")
    db_session.add(source)
    db_session.flush()

    ingest_document(
        db=db_session, embedding_provider=embedding_provider, source=source,
        title="Paracetamol", raw_bytes=PARACETAMOL_TEXT.encode(), doc_type="markdown",
        medical_topic="paracetamol",
    )
    ingest_document(
        db=db_session, embedding_provider=embedding_provider, source=source,
        title="Seasonal Allergies", raw_bytes=UNRELATED_TEXT.encode(), doc_type="markdown",
        medical_topic="seasonal_allergies",
    )
    ingest_document(
        db=db_session, embedding_provider=embedding_provider, source=source,
        title="Hypertension", raw_bytes=HYPERTENSION_TEXT.encode(), doc_type="markdown",
        medical_topic="hypertension",
    )
    ingest_document(
        db=db_session, embedding_provider=embedding_provider, source=source,
        title="Pain Reliever Tablets", raw_bytes=PAIN_RELIEVER_TEXT.encode(), doc_type="markdown",
        medical_topic="pain_reliever",
    )
    ingest_document(
        db=db_session, embedding_provider=embedding_provider, source=source,
        title="Common Cold", raw_bytes=COMMON_COLD_TEXT.encode(), doc_type="markdown",
        medical_topic="common_cold",
    )
    db_session.commit()
    return embedding_provider


def test_retrieves_relevant_chunk_for_matching_query(db_session) -> None:
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(db_session, "What is paracetamol used for?", embedding_provider)
    assert len(results) > 0
    assert any("paracetamol" in r.content.lower() or "paracetamol" in (r.document_title or "").lower() for r in results)


def test_returns_empty_for_completely_unrelated_query(db_session) -> None:
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(db_session, "quantum computing stock market forecast", embedding_provider)
    assert results == []


def test_retrieves_on_topic_paraphrase_word_not_present_in_source(db_session) -> None:
    """Regression: 'What is hypertension and how is it managed?' abstained
    because the only overlapping content word ('hypertension') failed a
    blanket 'need >=2 overlapping words' guardrail meant to catch nonsense
    queries -- it can't tell a rare, specific topic word from a generic one
    without knowing how common that word is across the corpus. Fixed by
    weighting overlap by inverse document frequency instead."""
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(db_session, "What is hypertension and how is it managed?", embedding_provider)
    assert len(results) > 0
    assert all(r.document_title == "Hypertension" for r in results)


def test_still_abstains_when_only_a_common_word_overlaps(db_session) -> None:
    """The other half of the same regression: a query sharing only a
    corpus-common word (e.g. 'commonly', 'approaches') with a document must
    still not be treated as a real topic match."""
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(db_session, "What are commonly documented approaches for xyz123?", embedding_provider)
    assert results == []


def test_repeated_topic_word_outranks_incidental_single_mention(db_session) -> None:
    """Regression: a real query for 'the common cold' returned real FDA drug
    labels instead of the actual Common Cold reference document, because a
    pain reliever's indications list mentions "the common cold" once (as one
    of several reasons to take it) and, before term-frequency weighting, that
    single mention scored identically to a document that's actually about
    the common cold and says so repeatedly."""
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(db_session, "What is the common cold?", embedding_provider)
    assert len(results) > 0
    assert results[0].document_title == "Common Cold"


def test_explicit_medical_topic_bypasses_sufficiency_threshold(db_session) -> None:
    """Regression: a real query naming a specific medicine by brand name
    ("What is Dolo 650 used for?") correctly scoped retrieval to that
    medicine's own document, but still returned nothing useful, because the
    real OTC label's "Uses" section (like PAIN_RELIEVER_TEXT here) never
    restates the drug's own name -- a genuine, common label pattern, not a
    data error -- so it could never clear the sufficiency bar on lexical/
    semantic score alone. Once a specific medicine has already been
    identified by exact name/alias match, that confidence should be trusted
    directly rather than re-filtered by score."""
    embedding_provider = _seed(db_session)
    # "xyz123" shares no vocabulary at all with the pain reliever document --
    # simulates a query token (e.g. a brand name) with zero lexical/semantic
    # overlap with the actual Uses text it should still surface.
    results = hybrid_retrieve(db_session, "xyz123", embedding_provider, medical_topic="pain_reliever")
    assert len(results) > 0
    assert all(r.document_title == "Pain Reliever Tablets" for r in results)


def test_medical_topic_filter_scopes_results(db_session) -> None:
    embedding_provider = _seed(db_session)
    results = hybrid_retrieve(
        db_session, "warnings", embedding_provider, medical_topic="paracetamol"
    )
    assert all("allerg" not in r.document_title.lower() for r in results)
