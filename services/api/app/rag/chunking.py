import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MAX_CHUNK_CHARS = 900


@dataclass
class Chunk:
    heading: str | None
    content: str
    chunk_index: int


def chunk_markdown(text: str) -> list[Chunk]:
    """Splits on headings first (never mid-warning/mid-section), then splits any
    section still over budget on paragraph boundaries, keeping the heading as
    context on every resulting piece so a chunk read on its own still makes sense.
    """
    text = text.strip()
    if not text:
        return []

    headings = list(_HEADING_RE.finditer(text))
    if not headings:
        return _chunk_plain(text)

    sections: list[tuple[str | None, str]] = []
    first_start = headings[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            sections.append((None, preamble))

    for i, match in enumerate(headings):
        heading_text = match.group(2).strip()
        body_start = match.end()
        body_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((heading_text, body))

    chunks: list[Chunk] = []
    for heading, body in sections:
        if not body:
            continue
        if len(body) <= MAX_CHUNK_CHARS:
            chunks.append(Chunk(heading=heading, content=body, chunk_index=len(chunks)))
            continue
        for piece in _split_paragraphs(body, MAX_CHUNK_CHARS):
            prefixed = f"{heading}: {piece}" if heading else piece
            chunks.append(Chunk(heading=heading, content=prefixed, chunk_index=len(chunks)))
    return chunks


def _chunk_plain(text: str) -> list[Chunk]:
    return [
        Chunk(heading=None, content=piece, chunk_index=i)
        for i, piece in enumerate(_split_paragraphs(text, MAX_CHUNK_CHARS))
    ]


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """A single paragraph (no blank lines) that alone exceeds the budget is
    split on sentence boundaries instead, so one giant block of prose still
    yields multiple retrievable chunks."""
    sentences = _SENTENCE_SPLIT_RE.split(paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [paragraph[:max_chars]]


def _split_paragraphs(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            units.append(para)
        else:
            units.extend(_split_long_paragraph(para, max_chars))

    pieces: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) > max_chars and current:
            pieces.append(current)
            current = unit
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [text[:max_chars]]
