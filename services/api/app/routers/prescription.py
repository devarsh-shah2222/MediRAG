from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import UploadedDocument, User
from app.providers.ocr import get_ocr_provider
from app.providers.storage import get_file_storage
from app.uploads import IMAGE_AND_PDF_MIME_TYPES, UploadValidationError, read_validated_upload

router = APIRouter(prefix="/api/prescription", tags=["prescription"])


@router.post("/explain")
async def explain(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> dict:
    try:
        contents = await read_validated_upload(file, IMAGE_AND_PDF_MIME_TYPES)
    except UploadValidationError as exc:
        return exc.as_dict()

    ocr = get_ocr_provider()
    result = ocr.extract(contents, kind="prescription")

    stored_path = get_file_storage().save(contents, file.filename or "upload")
    document = UploadedDocument(
        user_id=user.id if user else None,
        kind="prescription",
        original_filename=file.filename or "upload",
        stored_path=stored_path,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        ocr_status="reliable" if result.reliable else "uncertain",
        ocr_result={"raw_text": result.raw_text, "notice": result.notice},
    )
    db.add(document)
    db.commit()

    return {
        "uploaded_document_id": document.id,
        "explanation_notice": "This is an explanation of the uploaded prescription, not a new prescription.",
        "reliable": result.reliable,
        "raw_text": result.raw_text,
        "notice": result.notice,
        "extracted": {
            "medicines": [],
            "instructions": [],
        },
        "requires_confirmation": not result.reliable,
        "confirmation_message": (
            "We couldn't reliably read this prescription. Please confirm the medicine names, "
            "strength, and instructions manually, and check with your prescriber or pharmacist "
            "if anything is unclear."
        ),
    }
