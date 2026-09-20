"""Shared text-processing helpers for the mock embedding and lexical
retrieval scorers: a stopword list so generic words ("is", "used", "the")
don't drown out the topic words ("paracetamol", "hypertension") that
actually distinguish documents, and light suffix normalization so
"allergy"/"allergies" or "symptom"/"symptoms" count as the same token.
ponytail: a fixed ~60-word list and a ~5-line suffix rule instead of a
stemmer/stopword-list dependency (e.g. NLTK); English-only, adequate for the
demo corpus, imperfect on irregular plurals. Upgrade trigger: real
multilingual content needs per-language stopword handling, or retrieval
quality evals show real stemming is needed.
"""
import re
from collections import Counter

STOPWORDS = frozenset(
    """
    a an and are as at be by for from has have he in is it its of on
    that the to was were will with this these those what which who
    whom do does did doing can could should would i you your my me
    we our their his her they them about into than then there here
    but or not no so if when where why how also may might must shall
    such very just more most other some any all each other than
    used commonly documented approach approaches condition
    """.split()
)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")

# A handful of medical name synonyms mapped to one canonical token, so a
# query using either name matches content using the other. Caught live: the
# real FDA label for acetaminophen never says "paracetamol" (the name used
# almost everywhere outside the US) even once, so a document-level synonym
# note was enough to make the document findable at all, but its actual Uses/
# Warnings chunks -- which only ever say "acetaminophen" -- still couldn't
# match a "paracetamol" query and lost to that one short preamble chunk.
# ponytail: a fixed dict, not a medical thesaurus/UMLS lookup; add an entry
# only when a real query is confirmed to need it, the same way this one was.
#
# The brand-name entries are common Indian brand names for medicines this
# corpus covers (verified real, not invented -- see DECISIONS.md), so a user
# asking about "Crocin" or "Dolo" gets matched to the real ingested
# acetaminophen label content by generic name, same mechanism as the
# paracetamol/acetaminophen case above.
_SYNONYM_CANONICAL = {
    "paracetamol": "acetaminophen",
    "crocin": "acetaminophen",
    "dolo": "acetaminophen",
    "calpol": "acetaminophen",
    "brufen": "ibuprofen",
    "novamox": "amoxicillin",
    "glycomet": "metformin",
    "amlong": "amlodipine",
    "amlopres": "amlodipine",
    "azithral": "azithromycin",
    "alerid": "cetirizine",
}


def normalize_token(token: str) -> str:
    token = _SYNONYM_CANONICAL.get(token, token)
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es") and not token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> set[str]:
    """Lowercases, splits on non-alphanumeric characters, drops stopwords,
    and normalizes plurals -- the single tokenization path shared by the
    embedding provider and the lexical retrieval scorer, so a word is never
    treated as two different tokens depending on which one looks at it.
    Returns a set: for a query, whether a word is asked about once or twice
    doesn't add information, only which distinct words were used."""
    return {normalize_token(t) for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS}


def tokenize_counts(text: str) -> Counter:
    """Same tokenization as `tokenize`, but keeps term frequency. A document
    that only mentions "the common cold" once in passing (e.g. a pain
    reliever's indications list) must not score the same as a document
    that's actually about the common cold and says so repeatedly -- caught
    live: both the embedding and the lexical scorer originally deduplicated
    tokens into a set, so a chunk's own internal repetition of its real
    topic word carried no extra weight at all."""
    return Counter(normalize_token(t) for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS)
