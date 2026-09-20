from app.models import UploadedDocument


def test_explain_rejects_unsupported_file_type(client) -> None:
    resp = client.post(
        "/api/prescription/explain",
        files={"file": ("notes.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["error"] == "unsupported_file_type"


def test_explain_never_fabricates_and_asks_for_confirmation(client) -> None:
    resp = client.post(
        "/api/prescription/explain",
        files={"file": ("prescription.png", b"not-a-real-image", "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["explanation_notice"] == "This is an explanation of the uploaded prescription, not a new prescription."
    assert body["requires_confirmation"] is True
    assert body["extracted"]["medicines"] == []


def test_explain_rejects_oversized_file(client) -> None:
    big_content = b"0" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        "/api/prescription/explain",
        files={"file": ("prescription.png", big_content, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["error"] == "file_too_large"


def test_explain_persists_an_uploaded_document_record(client, db_session) -> None:
    resp = client.post(
        "/api/prescription/explain",
        files={"file": ("prescription.png", b"not-a-real-image", "image/png")},
    )
    document_id = resp.json()["uploaded_document_id"]
    stored = db_session.query(UploadedDocument).filter(UploadedDocument.id == document_id).first()
    assert stored is not None
    assert stored.kind == "prescription"
