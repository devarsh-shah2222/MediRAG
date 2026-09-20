from app.models import Medicine, RAGSource, UploadedDocument
from app.providers.embeddings import MockEmbeddingProvider
from app.rag.ingest import ingest_document

PARACETAMOL_TEXT = """# Paracetamol

## Active Ingredient
Paracetamol, also known as acetaminophen, is the active ingredient in this medicine.

## Uses
Paracetamol is commonly used to relieve mild pain and reduce fever.

## Warnings
Taking more than the recommended dose can cause serious liver damage.
"""


def _seed(db_session) -> None:
    source = RAGSource(name="Test Source", source_type="demo_reference", jurisdiction="global")
    db_session.add(source)
    db_session.flush()
    ingest_document(
        db=db_session, embedding_provider=MockEmbeddingProvider(), source=source,
        title="Paracetamol", raw_bytes=PARACETAMOL_TEXT.encode(), doc_type="markdown",
        medical_topic="paracetamol",
    )
    db_session.add(Medicine(name="Paracetamol", generic_name="Acetaminophen", aliases=["acetaminophen"], medical_topic="paracetamol"))
    db_session.commit()


def test_analyze_returns_sectioned_medicine_info(client, db_session) -> None:
    _seed(db_session)
    resp = client.post("/api/medicine/analyze", json={"query": "Tell me about paracetamol", "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["abstained"] is False
    assert "warnings" in body["sections"] or "uses" in body["sections"]
    assert "questions_to_ask" in body["sections"]


def test_analyze_matches_by_alias(client, db_session) -> None:
    _seed(db_session)
    resp = client.post("/api/medicine/analyze", json={"query": "What is acetaminophen?", "language": "en"})
    assert resp.status_code == 200
    assert resp.json()["abstained"] is False


def test_analyze_abstains_for_unknown_medicine(client, db_session) -> None:
    resp = client.post("/api/medicine/analyze", json={"query": "Tell me about a totally unknown compound xyz123", "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["abstained"] is True
    assert body["sections"] == {}


def test_scan_endpoint_never_fabricates_and_flags_uncertainty(client) -> None:
    resp = client.post(
        "/api/medicine/scan",
        files={"file": ("pill.png", b"not-a-real-image", "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reliable"] is False
    assert body["fields"] == {}
    assert "manually" in body["notice"].lower()


def test_scan_endpoint_persists_an_uploaded_document_record(client, db_session) -> None:
    resp = client.post(
        "/api/medicine/scan",
        files={"file": ("pill.png", b"not-a-real-image", "image/png")},
    )
    document_id = resp.json()["uploaded_document_id"]
    stored = db_session.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
    assert stored is not None
    assert stored.kind == "medicine_image"
    assert stored.ocr_status == "uncertain"
