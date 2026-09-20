from app.rag.chunking import MAX_CHUNK_CHARS, chunk_markdown


def test_splits_on_headings_and_keeps_heading_text() -> None:
    text = """# Medicine

## Uses
Used for pain relief.

## Warnings
Do not exceed the recommended dose.
"""
    chunks = chunk_markdown(text)
    headings = [c.heading for c in chunks]
    assert "Uses" in headings
    assert "Warnings" in headings
    uses_chunk = next(c for c in chunks if c.heading == "Uses")
    assert "pain relief" in uses_chunk.content


def test_long_section_is_split_but_keeps_heading_context() -> None:
    long_body = "This sentence repeats important warning text. " * 60
    text = f"# Medicine\n\n## Warnings\n\n{long_body}"
    chunks = chunk_markdown(text)
    warning_chunks = [c for c in chunks if c.heading == "Warnings"]
    assert len(warning_chunks) > 1
    for c in warning_chunks:
        assert len(c.content) <= MAX_CHUNK_CHARS + len("Warnings: ")
        assert c.content.startswith("Warnings:")


def test_plain_text_without_headings_is_chunked_by_paragraph() -> None:
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = chunk_markdown(text)
    assert len(chunks) >= 1
    assert all(c.heading is None for c in chunks)


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n  ") == []
