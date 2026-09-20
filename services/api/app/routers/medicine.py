from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import UploadedDocument, User
from app.providers.embeddings import get_embedding_provider
from app.providers.ocr import get_ocr_provider
from app.providers.storage import get_file_storage
from app.rag.medicine_topic import find_medicine_topic
from app.rag.retrieval import hybrid_retrieve
from app.safety import classifier
from app.schemas import MedicineAnalyzeRequest
from app.uploads import IMAGE_MIME_TYPES, UploadValidationError, read_validated_upload

router = APIRouter(prefix="/api/medicine", tags=["medicine"])

ABSTAIN_MESSAGE = "I couldn't verify that information from the available medical references."
STATIC_QUESTIONS = [
    "What is this medicine generally used for?",
    "Are there other medicines or conditions I should mention before taking this?",
    "What side effects should prompt me to call my doctor or pharmacist?",
]

_SECTION_KEYWORDS: dict[str, list[str]] = {
    "active_ingredient": ["active ingredient", "generic name"],
    "medicine_class": ["medicine class", "drug class"],
    "uses": ["use", "indication"],
    "side_effects": ["side effect"],
    "warnings": ["warning", "contraindication"],
    "interactions": ["interaction"],
    "storage": ["storage"],
    "precautions": ["precaution", "special population"],
}


def _section_for_heading(heading: str | None) -> str:
    if not heading:
        return "general"
    lowered = heading.lower()
    for key, needles in _SECTION_KEYWORDS.items():
        if any(n in lowered for n in needles):
            return key
    return "general"


@router.post("/analyze")
def analyze(req: MedicineAnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    assessment = classifier.classify(req.query)
    topic = find_medicine_topic(db, req.query)

    retrieved = hybrid_retrieve(db, req.query, get_embedding_provider(), medical_topic=topic, language=req.language)

    if not retrieved:
        return {
            "abstained": True,
            "answer": ABSTAIN_MESSAGE,
            "sections": {},
            "policy_flags": assessment.policy_flags,
            "disclaimer": "This information does not replace advice from a doctor or pharmacist.",
        }

    sections: dict[str, dict] = {}
    for chunk in retrieved:
        key = _section_for_heading(chunk.heading)
        bucket = sections.setdefault(key, {"heading": chunk.heading or key.replace("_", " ").title(), "evidence": []})
        bucket["evidence"].append(
            {
                "source_name": chunk.source_name,
                "document_title": chunk.document_title,
                "snippet": chunk.content[:400],
                "retrieval_score": chunk.score,
            }
        )

    sections.setdefault("questions_to_ask", {"heading": "Questions to Ask a Pharmacist/Doctor", "evidence": []})
    if not sections["questions_to_ask"]["evidence"]:
        sections["questions_to_ask"]["evidence"] = [{"snippet": q} for q in STATIC_QUESTIONS]

    return {
        "abstained": False,
        "medicine_name": retrieved[0].document_title,
        "sections": sections,
        "policy_flags": assessment.policy_flags,
        "disclaimer": (
            "This information does not replace advice from a doctor or pharmacist. It never "
            "recommends starting, stopping, or changing a prescription."
        ),
    }


@router.post("/scan")
async def scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    try:
        image_bytes = await read_validated_upload(file, IMAGE_MIME_TYPES)
    except UploadValidationError as exc:
        return exc.as_dict()

    ocr = get_ocr_provider()
    result = ocr.extract(image_bytes, kind="medicine_image")

    stored_path = get_file_storage().save(image_bytes, file.filename or "upload")
    document = UploadedDocument(
        user_id=user.id if user else None,
        kind="medicine_image",
        original_filename=file.filename or "upload",
        stored_path=stored_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(image_bytes),
        ocr_status="reliable" if result.reliable else "uncertain",
        ocr_result={"raw_text": result.raw_text, "notice": result.notice},
    )
    db.add(document)
    db.commit()

    return {
        "uploaded_document_id": document.id,
        "reliable": result.reliable,
        "raw_text": result.raw_text,
        "notice": result.notice,
        "fields": {k: {"value": v.value, "confidence": v.confidence} for k, v in result.fields.items()},
    }
