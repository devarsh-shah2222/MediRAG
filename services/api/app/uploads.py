from fastapi import UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
IMAGE_AND_PDF_MIME_TYPES = IMAGE_MIME_TYPES | {"application/pdf"}


class UploadValidationError(Exception):
    def __init__(self, error: str, message: str):
        self.error = error
        self.message = message

    def as_dict(self) -> dict:
        return {"error": self.error, "message": self.message}


async def read_validated_upload(file: UploadFile, allowed_types: set[str]) -> bytes:
    """Shared MIME/size checks for medicine-scan and prescription uploads."""
    if file.content_type not in allowed_types:
        raise UploadValidationError(
            "unsupported_file_type",
            "Please upload a PNG, JPEG, or WEBP image" + (" or a PDF" if "application/pdf" in allowed_types else "") + ".",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("file_too_large", "This file is too large. Please upload a file under 10 MB.")

    return contents
