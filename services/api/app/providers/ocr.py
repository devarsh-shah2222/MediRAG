from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class OCRField:
    value: str | None
    confidence: float  # 0..1
    verified: bool = False


@dataclass
class OCRResult:
    fields: dict[str, OCRField] = field(default_factory=dict)
    raw_text: str = ""
    reliable: bool = False
    notice: str = ""


class OCRProvider(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, kind: str) -> OCRResult:
        """kind is 'medicine_image' or 'prescription'."""


class MockOCRProvider(OCRProvider):
    """No real vision/OCR call is made.

    ponytail: the user asked to mock every external provider for the first
    build, so this never attempts to read the image. Per the no-hallucination
    policy, it never invents plausible-looking medicine/prescription text --
    it always reports low confidence and asks the user to confirm manually.
    Upgrade trigger: wire OCR_PROVIDER=tesseract (needs the tesseract binary
    installed) or a real vision API behind this same interface.
    """

    def extract(self, image_bytes: bytes, kind: str) -> OCRResult:
        return OCRResult(
            fields={},
            raw_text="",
            reliable=False,
            notice=(
                "Some text could not be read reliably. OCR is running in demo/mock mode, "
                "so this upload was not analyzed automatically. Please type the medicine or "
                "prescription details manually to continue."
            ),
        )


class TesseractOCRProvider(OCRProvider):
    """Real local OCR via pytesseract. Requires the Tesseract binary installed
    on the host and OCR_PROVIDER=tesseract. Not wired by default."""

    def extract(self, image_bytes: bytes, kind: str) -> OCRResult:
        import io

        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        raw_text = pytesseract.image_to_string(image)
        reliable = len(raw_text.strip()) > 20
        notice = "" if reliable else "Some text could not be read reliably. Please confirm the details manually."
        return OCRResult(fields={}, raw_text=raw_text, reliable=reliable, notice=notice)


def get_ocr_provider() -> OCRProvider:
    from app.config import get_settings

    settings = get_settings()
    if settings.ocr_provider == "tesseract":
        return TesseractOCRProvider()
    return MockOCRProvider()
