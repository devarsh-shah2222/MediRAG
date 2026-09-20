from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Conversation, EvidenceReference, Message, SafetyEvent, User
from app.providers.embeddings import get_embedding_provider
from app.providers.llm import get_llm_provider
from app.rag.claims import validate_claims
from app.rag.medicine_topic import find_medicine_topic
from app.rag.retrieval import hybrid_retrieve
from app.rate_limit import make_rate_limiter
from app.safety import classifier
from app.safety.emergency import build_emergency_actions, build_urgent_actions, get_emergency_contacts
from app.schemas import ChatAction, ChatRequest, ChatResponse, EvidenceItem

router = APIRouter(prefix="/api/chat", tags=["chat"])
chat_rate_limit = make_rate_limiter(max_requests=30)

ABSTAIN_MESSAGE = "I couldn't verify that information from the available medical references."
GENERAL_DISCLAIMER = (
    "MediRAG provides general health information and care navigation. It is not a "
    "diagnosis and does not replace professional medical advice."
)
URGENT_INTRO = "Your description includes symptoms that may need prompt professional evaluation."
EMERGENCY_INTRO = "Your description includes symptoms that may need urgent professional evaluation."


def _get_or_create_conversation(db: Session, req: ChatRequest, user: User | None) -> Conversation:
    if req.conversation_id:
        existing = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
        if existing:
            return existing
    conversation = Conversation(
        user_id=user.id if user else None,
        client_session_id=req.client_session_id,
        language=req.language,
    )
    db.add(conversation)
    db.flush()
    return conversation


@router.post("", response_model=ChatResponse, dependencies=[Depends(chat_rate_limit)])
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> ChatResponse:
    conversation = _get_or_create_conversation(db, req, user)

    db.add(Message(conversation_id=conversation.id, role="user", content=req.message))

    assessment = classifier.classify(req.message)

    if assessment.level != classifier.LEVEL_NORMAL:
        db.add(
            SafetyEvent(
                conversation_id=conversation.id,
                level=assessment.level,
                categories=assessment.urgency_categories,
                input_excerpt=req.message[:500],
            )
        )

    if assessment.level == classifier.LEVEL_EMERGENCY:
        contacts = get_emergency_contacts(db, "US")
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=EMERGENCY_INTRO,
            mode="emergency_navigation",
            disclaimer=GENERAL_DISCLAIMER,
            actions=[a for a in build_emergency_actions("US")],
        )
        db.add(assistant_message)
        db.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=EMERGENCY_INTRO,
            mode="emergency_navigation",
            evidence=[],
            actions=[ChatAction(**a) for a in build_emergency_actions("US")],
            disclaimer=GENERAL_DISCLAIMER,
            language=req.language,
            emergency_contacts=contacts,
        )

    embedding_provider = get_embedding_provider()
    llm_provider = get_llm_provider()

    # A question naming a specific medicine (by generic or brand name, e.g.
    # "Dolo 650") gets scoped retrieval against just that medicine's
    # document, the same as the dedicated Medicine page -- otherwise its
    # chunks compete lexically against the whole corpus, and a section that
    # doesn't happen to repeat the drug name (real OTC "Uses" text often
    # doesn't) can lose to an unrelated document. Caught live with a real
    # "What is Dolo 650 used for?" query.
    medical_topic = find_medicine_topic(db, req.message)
    retrieved = hybrid_retrieve(db, req.message, embedding_provider, medical_topic=medical_topic, language=req.language)
    generated = llm_provider.generate(req.message, retrieved, req.language)
    validated = validate_claims(generated.text, retrieved)

    mode = "urgent" if assessment.level == classifier.LEVEL_URGENT else "information"

    if validated.abstained or not validated.text:
        answer_text = ABSTAIN_MESSAGE
        evidence_items: list[EvidenceItem] = []
        actions = [ChatAction(id="find_doctor", label="Find a Doctor Nearby", type="navigate", target="/doctors")]
    else:
        answer_text = validated.text
        cited = [c for c in retrieved if c.chunk_id in validated.cited_chunk_ids]
        evidence_items = [
            EvidenceItem(
                source_name=c.source_name,
                document_title=c.document_title,
                source_type=c.source_type,
                url=c.url,
                published_date=c.published_date,
                snippet=c.content[:280],
                retrieval_score=c.score,
            )
            for c in cited
        ]
        actions = [
            ChatAction(id="explain_simpler", label="Explain more simply", type="suggested_prompt"),
            ChatAction(id="show_sources", label="Show sources", type="toggle_evidence"),
        ]

    cited_chunks = cited if not (validated.abstained or not validated.text) else []

    if mode == "urgent":
        answer_text = f"{URGENT_INTRO} {answer_text}".strip()
        actions = [ChatAction(**a) for a in build_urgent_actions()] + actions

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        mode=mode,
        disclaimer=GENERAL_DISCLAIMER,
        actions=[a.model_dump() for a in actions],
    )
    db.add(assistant_message)
    db.flush()

    for rank, (chunk, item) in enumerate(zip(cited_chunks, evidence_items)):
        db.add(
            EvidenceReference(
                message_id=assistant_message.id,
                chunk_id=chunk.chunk_id,
                source_name=item.source_name,
                document_title=item.document_title,
                source_type=item.source_type,
                url=item.url,
                published_date=item.published_date,
                snippet=item.snippet,
                retrieval_score=item.retrieval_score,
                rank=rank,
            )
        )

    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        answer=answer_text,
        mode=mode,
        evidence=evidence_items,
        actions=actions,
        disclaimer=GENERAL_DISCLAIMER,
        language=req.language,
    )


@router.get("/{conversation_id}/prepare-visit")
def prepare_visit(conversation_id: str, db: Session = Depends(get_db)) -> dict:
    """Heuristic 'Doctor Visit Summary' built from the conversation so far.
    Preparation only -- never a diagnosis or a prescription.
    """
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at)
        .all()
    )
    return {
        "summary_type": "doctor_visit_preparation",
        "topics_discussed": [m.content for m in messages][-10:],
        "suggested_questions": [
            "Can you help me understand what might be causing this?",
            "Are there any tests you'd recommend?",
            "What symptoms should prompt me to come back sooner?",
        ],
        "note": "This is preparation only, not a diagnosis or a prescription.",
    }
