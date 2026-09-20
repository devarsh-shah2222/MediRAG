"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("preferred_language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_id", sa.String(32), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("client_session_id", sa.String(64), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_client_session_id", "conversations", ["client_session_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("conversation_id", sa.String(32), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("mode", sa.String(32), nullable=True),
        sa.Column("disclaimer", sa.Text, nullable=True),
        sa.Column("actions", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "rag_sources",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("jurisdiction", sa.String(64), nullable=False, server_default="global"),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("authority_notes", sa.Text, nullable=True),
        sa.Column("update_policy", sa.String(255), nullable=True),
        sa.Column("license_notes", sa.String(255), nullable=True),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rag_documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("source_id", sa.String(32), sa.ForeignKey("rag_sources.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("doc_type", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("medical_topic", sa.String(128), nullable=False),
        sa.Column("jurisdiction", sa.String(64), nullable=False, server_default="global"),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_rag_documents_source_id", "rag_documents", ["source_id"])
    op.create_index("ix_rag_documents_medical_topic", "rag_documents", ["medical_topic"])

    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("rag_documents.id"), nullable=False),
        sa.Column("heading", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])

    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("message_id", sa.String(32), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("retrieved_chunk_ids", sa.JSON, nullable=False),
        sa.Column("retrieval_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_logs_message_id", "retrieval_logs", ["message_id"])

    op.create_table(
        "evidence_references",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("message_id", sa.String(32), sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("chunk_id", sa.String(32), sa.ForeignKey("rag_chunks.id"), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("document_title", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snippet", sa.Text, nullable=False),
        sa.Column("retrieval_score", sa.Float, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
    )
    op.create_index("ix_evidence_references_message_id", "evidence_references", ["message_id"])

    op.create_table(
        "safety_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("conversation_id", sa.String(32), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("message_id", sa.String(32), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("categories", sa.JSON, nullable=False),
        sa.Column("input_excerpt", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_safety_events_conversation_id", "safety_events", ["conversation_id"])

    op.create_table(
        "medicines",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("generic_name", sa.String(255), nullable=True),
        sa.Column("aliases", sa.JSON, nullable=False),
        sa.Column("medical_topic", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_medicines_name", "medicines", ["name"])

    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("ocr_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("ocr_result", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "providers",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("specialty", sa.String(128), nullable=True),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("city", sa.String(128), nullable=False),
        sa.Column("region", sa.String(64), nullable=False, server_default="US"),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lng", sa.Float, nullable=False),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("opening_hours", sa.JSON, nullable=True),
        sa.Column("accepts_emergency", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_providers_provider_type", "providers", ["provider_type"])
    op.create_index("ix_providers_specialty", "providers", ["specialty"])
    op.create_index("ix_providers_city", "providers", ["city"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("actor_user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("event_metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("conversation_id", sa.String(32), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("message_id", sa.String(32), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "application_settings",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("key", sa.String(128), unique=True, nullable=False),
        sa.Column("value", sa.JSON, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_settings_key", "application_settings", ["key"])


def downgrade() -> None:
    op.drop_table("application_settings")
    op.drop_table("feedback")
    op.drop_table("audit_events")
    op.drop_table("providers")
    op.drop_table("uploaded_documents")
    op.drop_table("medicines")
    op.drop_table("safety_events")
    op.drop_table("evidence_references")
    op.drop_table("retrieval_logs")
    op.drop_table("rag_chunks")
    op.drop_table("rag_documents")
    op.drop_table("rag_sources")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("auth_sessions")
    op.drop_table("users")
