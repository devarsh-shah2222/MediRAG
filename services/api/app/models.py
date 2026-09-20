import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import EmbeddingVector
from app.providers.embeddings import EMBEDDING_DIM


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(Base):
    """Tracks issued JWTs so they can be revoked/audited. The JWT itself stays stateless."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_id: Mapped[str] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    client_session_id: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)  # information|urgent|emergency_navigation
    disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    evidence: Mapped[list["EvidenceReference"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class RAGSource(Base):
    __tablename__ = "rag_sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(64))  # government|who|regulatory|institution|other
    jurisdiction: Mapped[str] = mapped_column(String(64), default="global")
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    authority_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    update_policy: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    documents: Mapped[list["RAGDocument"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("rag_sources.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(32))  # pdf|html|markdown|text
    language: Mapped[str] = mapped_column(String(8), default="en")
    medical_topic: Mapped[str] = mapped_column(String(128), index=True)
    jurisdiction: Mapped[str] = mapped_column(String(64), default="global")
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    content_version: Mapped[int] = mapped_column(Integer, default=1)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    is_demo: Mapped[bool] = mapped_column(default=True)

    source: Mapped["RAGSource"] = relationship(back_populates="documents")
    chunks: Mapped[list["RAGChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id"), index=True)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector(EMBEDDING_DIM))
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["RAGDocument"] = relationship(back_populates="chunks")


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text)
    retrieved_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("rag_chunks.id"))
    source_name: Mapped[str] = mapped_column(String(255))
    document_title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snippet: Mapped[str] = mapped_column(Text)
    retrieval_score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    message: Mapped["Message"] = relationship(back_populates="evidence")


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(16))  # normal|urgent|emergency
    categories: Mapped[list] = mapped_column(JSON, default=list)
    input_excerpt: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), index=True)
    generic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    medical_topic: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))  # medicine_image | prescription
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer)
    ocr_status: Mapped[str] = mapped_column(String(32), default="pending")
    ocr_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Provider(Base):
    """A doctor/hospital/clinic/pharmacy at a single location (location merged in, ponytail)."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    provider_type: Mapped[str] = mapped_column(String(32), index=True)  # doctor|hospital|clinic|pharmacy
    specialty: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    address: Mapped[str] = mapped_column(String(512))
    city: Mapped[str] = mapped_column(String(128), index=True)
    region: Mapped[str] = mapped_column(String(64), default="US")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    opening_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    accepts_emergency: Mapped[bool] = mapped_column(default=False)
    is_demo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)  # -1, 0, 1
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApplicationSetting(Base):
    __tablename__ = "application_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
