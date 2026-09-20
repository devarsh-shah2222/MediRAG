import re
from dataclasses import dataclass

from app.rag.retrieval import RetrievedChunk

_CITE_RE = re.compile(r"\[\[cite:\s*([a-f0-9]+)\s*\]\]")
# Real models don't agree on marker placement relative to sentence-ending
# punctuation: the mock/Anthropic prompt example shows "Sentence. [[cite:id]]"
# (marker AFTER the period), but a real Gemini response instead wrote
# "Sentence [[cite: id]]." (marker BEFORE the period) -- both grammatically
# reasonable, neither reliably followed. Rather than trust either convention,
# normalize every marker to the "before punctuation" position first, so a
# plain sentence-boundary split can never let a marker drift onto the next,
# unrelated sentence.
_CITE_AFTER_PUNCT_RE = re.compile(r"([.!?])\s*(\[\[cite:\s*[a-f0-9]+\s*\]\])")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,!?;:])")
UNSUPPORTED_ABSTAIN_RATIO = 0.5


@dataclass
class ValidatedAnswer:
    text: str
    cited_chunk_ids: list[str]
    abstained: bool


def validate_claims(raw_text: str, evidence: list[RetrievedChunk]) -> ValidatedAnswer:
    """Strips citation markers, keeps only sentences that cite an actually
    retrieved chunk, and abstains if too much of the answer is unsupported.

    This is the safety net for every provider: the mock provider emits
    citation markers by construction, and the real providers are instructed
    to -- this function is what actually enforces it, rather than trusting
    the model's compliance (including its compliance with the marker's exact
    syntax and placement).
    """
    valid_ids = {c.chunk_id for c in evidence}
    if not raw_text.strip():
        return ValidatedAnswer(text="", cited_chunk_ids=[], abstained=True)

    normalized = _CITE_AFTER_PUNCT_RE.sub(r"\2\1", raw_text.strip())

    kept: list[str] = []
    cited: list[str] = []
    unsupported_count = 0

    for sentence in _SENTENCE_SPLIT_RE.split(normalized):
        matches = _CITE_RE.findall(sentence)
        clean_sentence = _CITE_RE.sub("", sentence).strip()
        # Removing an inline "text [[cite: id]]." marker leaves a stray space
        # before the punctuation that used to follow it directly.
        clean_sentence = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", clean_sentence)
        if not clean_sentence:
            continue
        supported_ids = [m for m in matches if m in valid_ids]
        if supported_ids:
            kept.append(clean_sentence)
            for cid in supported_ids:
                if cid not in cited:
                    cited.append(cid)
        else:
            unsupported_count += 1

    total = len(kept) + unsupported_count
    if total == 0 or (unsupported_count / total) > UNSUPPORTED_ABSTAIN_RATIO or not kept:
        return ValidatedAnswer(text="", cited_chunk_ids=[], abstained=True)

    return ValidatedAnswer(text=" ".join(kept), cited_chunk_ids=cited, abstained=False)
