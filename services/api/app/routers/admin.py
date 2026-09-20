from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models import AuditEvent, RAGChunk, RAGDocument, RAGSource, User
from app.providers.embeddings import get_embedding_provider
from app.rag.ingest import ingest_document
from app.schemas import RAGDocumentResponse, RAGSourceResponse

router = APIRouter(prefix="/api/rag", tags=["admin", "rag"])


@router.get("/sources", response_model=list[RAGSourceResponse])
def list_sources(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[RAGSourceResponse]:
    return [RAGSourceResponse(**s.__dict__) for s in db.query(RAGSource).all()]


@router.get("/documents", response_model=list[RAGDocumentResponse])
def list_documents(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[RAGDocumentResponse]:
    docs = db.query(RAGDocument).all()
    return [
        RAGDocumentResponse(
            id=d.id,
            title=d.title,
            medical_topic=d.medical_topic,
            content_version=d.content_version,
            is_demo=d.is_demo,
            ingestion_timestamp=d.ingestion_timestamp,
            chunk_count=len(d.chunks),
        )
        for d in docs
    ]


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest(
    source_id: str = Form(...),
    title: str = Form(...),
    doc_type: str = Form(...),
    medical_topic: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> dict:
    source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")

    raw_bytes = await file.read()
    result = ingest_document(
        db=db,
        embedding_provider=get_embedding_provider(),
        source=source,
        title=title,
        raw_bytes=raw_bytes,
        doc_type=doc_type,
        medical_topic=medical_topic,
        is_demo=False,
    )
    db.add(
        AuditEvent(
            actor_user_id=admin_user.id,
            action="rag.ingest",
            entity_type="rag_document",
            entity_id=result.document_id,
            event_metadata={"chunk_count": result.chunk_count, "updated": result.was_updated},
        )
    )
    db.commit()
    return {"document_id": result.document_id, "chunk_count": result.chunk_count, "updated": result.was_updated}


@router.post("/reindex")
def reindex(db: Session = Depends(get_db), admin_user: User = Depends(require_admin)) -> dict:
    embedding_provider = get_embedding_provider()
    chunks = db.query(RAGChunk).all()
    for chunk in chunks:
        chunk.embedding = embedding_provider.embed(chunk.content)
    db.add(
        AuditEvent(
            actor_user_id=admin_user.id,
            action="rag.reindex",
            entity_type="rag_chunk",
            event_metadata={"reindexed_chunks": len(chunks)},
        )
    )
    db.commit()
    return {"reindexed_chunks": len(chunks)}
