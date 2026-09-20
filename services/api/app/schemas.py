from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool
    preferred_language: str


# --- Evidence / Chat contract ---
class EvidenceItem(BaseModel):
    source_name: str
    document_title: str
    source_type: str
    url: str | None
    published_date: datetime | None
    snippet: str
    retrieval_score: float


class ChatAction(BaseModel):
    id: str
    label: str
    type: str
    target: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    client_session_id: str = Field(min_length=1, max_length=64)
    language: str = "en"


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    mode: str  # information | urgent | emergency_navigation
    evidence: list[EvidenceItem]
    actions: list[ChatAction]
    disclaimer: str
    language: str
    emergency_contacts: dict | None = None


# --- Medicine ---
class MedicineAnalyzeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    language: str = "en"


# --- Providers ---
class ProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    specialty: str | None
    address: str
    city: str
    phone: str | None
    website: str | None
    opening_hours: dict | None
    distance_km: float | None
    accepts_emergency: bool
    is_demo: bool


# --- Feedback ---
class FeedbackRequest(BaseModel):
    conversation_id: str | None = None
    message_id: str | None = None
    rating: int = Field(ge=-1, le=1)
    comment: str | None = Field(default=None, max_length=1000)


# --- Admin / RAG ---
class RAGSourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    jurisdiction: str
    url: str | None
    last_ingested_at: datetime | None


class RAGDocumentResponse(BaseModel):
    id: str
    title: str
    medical_topic: str
    content_version: int
    is_demo: bool
    ingestion_timestamp: datetime
    chunk_count: int
