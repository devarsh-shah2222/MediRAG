from app.rag.claims import validate_claims
from app.rag.retrieval import RetrievedChunk


def _chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        heading="Uses",
        content="Some evidence content.",
        score=0.9,
        source_name="Demo Source",
        document_title="Demo Doc",
        source_type="demo_reference",
        url=None,
        published_date=None,
    )


def test_fully_cited_answer_is_kept() -> None:
    evidence = [_chunk("abc123")]
    text = "Paracetamol relieves pain. [[cite:abc123]] It also reduces fever. [[cite:abc123]]"
    result = validate_claims(text, evidence)
    assert not result.abstained
    assert result.cited_chunk_ids == ["abc123"]
    assert "[[cite" not in result.text


def test_tolerates_whitespace_after_cite_colon() -> None:
    """Regression: a real Gemini response emitted "[[cite: <id>]]" with a
    space after the colon despite the prompt showing no space -- the parser
    must not silently drop a correctly-attributed claim over formatting."""
    evidence = [_chunk("abc123")]
    text = "Paracetamol relieves pain. [[cite: abc123]]"
    result = validate_claims(text, evidence)
    assert not result.abstained
    assert result.cited_chunk_ids == ["abc123"]


def test_tolerates_marker_before_terminal_punctuation() -> None:
    """Regression: a real Gemini response placed the marker BEFORE the
    sentence's period ("Sentence [[cite: id]].") instead of after it
    ("Sentence. [[cite:id]]") as the prompt's example showed. Both
    placements must attribute the citation to the sentence it's attached
    to, and neither must let the citation drift onto the next sentence."""
    evidence = [_chunk("abc123")]
    text = (
        "Paracetamol relieves pain [[cite: abc123]]. "
        "It also reduces fever [[cite: abc123]]. "
        "This sentence has no citation at all."
    )
    result = validate_claims(text, evidence)
    assert not result.abstained
    assert result.cited_chunk_ids == ["abc123"]
    assert "Paracetamol relieves pain" in result.text
    assert "It also reduces fever" in result.text
    assert "This sentence has no citation" not in result.text


def test_strips_stray_space_left_behind_by_removed_marker() -> None:
    """Regression: "...documented [[cite: id]]." became "...documented ."
    (stray space before the period) once the marker was stripped."""
    evidence = [_chunk("abc123")]
    text = "The intended uses are not documented [[cite: abc123]]."
    result = validate_claims(text, evidence)
    assert not result.abstained
    assert result.text == "The intended uses are not documented."


def test_unknown_citation_id_is_treated_as_unsupported() -> None:
    evidence = [_chunk("abc123")]
    text = "This is a fabricated claim. [[cite:doesnotexist]]"
    result = validate_claims(text, evidence)
    assert result.abstained


def test_minority_unsupported_sentences_are_dropped_not_abstained() -> None:
    evidence = [_chunk("abc123")]
    text = (
        "Supported claim one. [[cite:abc123]] "
        "Supported claim two. [[cite:abc123]] "
        "Supported claim three. [[cite:abc123]] "
        "Unsupported extra claim."
    )
    result = validate_claims(text, evidence)
    assert not result.abstained
    assert "Unsupported extra claim" not in result.text
    assert "Supported claim one" in result.text


def test_majority_unsupported_triggers_abstention() -> None:
    evidence = [_chunk("abc123")]
    text = "Unsupported one. Unsupported two. Supported claim. [[cite:abc123]]"
    result = validate_claims(text, evidence)
    assert result.abstained


def test_empty_text_abstains() -> None:
    result = validate_claims("", [_chunk("abc123")])
    assert result.abstained
    assert result.text == ""
