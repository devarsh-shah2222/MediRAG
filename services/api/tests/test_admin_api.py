from app.models import AuditEvent, RAGSource, User


def _register_admin(client, db_session) -> None:
    client.post("/api/auth/register", json={"email": "admin@example.com", "password": "supersecret123"})
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    user.is_admin = True
    db_session.commit()


def _register_regular_user(client) -> None:
    client.post("/api/auth/register", json={"email": "regular@example.com", "password": "supersecret123"})


def test_sources_requires_authentication(client) -> None:
    resp = client.get("/api/rag/sources")
    assert resp.status_code == 401


def test_sources_requires_admin_not_just_login(client) -> None:
    _register_regular_user(client)
    resp = client.get("/api/rag/sources")
    assert resp.status_code == 403


def test_admin_can_list_sources_and_documents(client, db_session) -> None:
    _register_admin(client, db_session)
    db_session.add(RAGSource(name="Demo Source", source_type="demo_reference", jurisdiction="global"))
    db_session.commit()

    sources_resp = client.get("/api/rag/sources")
    assert sources_resp.status_code == 200
    assert len(sources_resp.json()) == 1

    documents_resp = client.get("/api/rag/documents")
    assert documents_resp.status_code == 200
    assert documents_resp.json() == []


def test_admin_ingest_creates_document_and_audit_event(client, db_session) -> None:
    _register_admin(client, db_session)
    source = RAGSource(name="Demo Source", source_type="demo_reference", jurisdiction="global")
    db_session.add(source)
    db_session.commit()

    resp = client.post(
        "/api/rag/ingest",
        data={"source_id": source.id, "title": "Test Doc", "doc_type": "markdown", "medical_topic": "test_topic"},
        files={"file": ("doc.md", b"# Test Doc\n\n## Uses\nSome content here.", "text/markdown")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["chunk_count"] > 0

    audit_events = db_session.query(AuditEvent).filter(AuditEvent.action == "rag.ingest").all()
    assert len(audit_events) == 1
    assert audit_events[0].entity_id == body["document_id"]


def test_admin_reindex_creates_audit_event(client, db_session) -> None:
    _register_admin(client, db_session)
    resp = client.post("/api/rag/reindex")
    assert resp.status_code == 200

    audit_events = db_session.query(AuditEvent).filter(AuditEvent.action == "rag.reindex").all()
    assert len(audit_events) == 1
