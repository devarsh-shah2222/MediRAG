import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import RAGChunk, RAGDocument, RAGSource
from app.providers.embeddings import EmbeddingProvider
from app.rag.chunking import chunk_markdown


@dataclass
class IngestResult:
    document_id: str
    chunk_count: int
    was_updated: bool


def parse_document_text(raw_bytes: bytes, doc_type: str) -> str:
    if doc_type in ("markdown", "text"):
        return raw_bytes.decode("utf-8", errors="replace")
    if doc_type == "html":
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_bytes.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text("\n")
    if doc_type == "pdf":
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported doc_type: {doc_type}")


def ingest_document(
    db: Session,
    embedding_provider: EmbeddingProvider,
    source: RAGSource,
    title: str,
    raw_bytes: bytes,
    doc_type: str,
    medical_topic: str,
    language: str = "en",
    jurisdiction: str = "global",
    url: str | None = None,
    publication_date: datetime | None = None,
    is_demo: bool = True,
) -> IngestResult:
    text = parse_document_text(raw_bytes, doc_type)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    existing = (
        db.query(RAGDocument)
        .filter(RAGDocument.source_id == source.id, RAGDocument.title == title)
        .first()
    )

    if existing and existing.content_hash == content_hash:
        return IngestResult(document_id=existing.id, chunk_count=len(existing.chunks), was_updated=False)

    if existing:
        for chunk in list(existing.chunks):
            db.delete(chunk)
        existing.content_hash = content_hash
        existing.content_version += 1
        existing.updated_date = datetime.now(timezone.utc)
        existing.ingestion_timestamp = datetime.now(timezone.utc)
        document = existing
    else:
        document = RAGDocument(
            source_id=source.id,
            title=title,
            url=url,
            doc_type=doc_type,
            language=language,
            medical_topic=medical_topic,
            jurisdiction=jurisdiction,
            publication_date=publication_date,
            content_hash=content_hash,
            is_demo=is_demo,
        )
        db.add(document)
        db.flush()

    chunks = chunk_markdown(text)
    for chunk in chunks:
        embedding = embedding_provider.embed(chunk.content)
        db.add(
            RAGChunk(
                document_id=document.id,
                heading=chunk.heading,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                embedding=embedding,
                token_count=len(chunk.content.split()),
            )
        )

    source.last_ingested_at = datetime.now(timezone.utc)
    db.flush()

    return IngestResult(document_id=document.id, chunk_count=len(chunks), was_updated=True)
