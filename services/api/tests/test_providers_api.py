from app.models import Provider


def _seed_providers(db_session) -> None:
    db_session.add(
        Provider(
            name="Demo City General Hospital", provider_type="hospital", specialty="Emergency Medicine",
            address="1 Main St", city="Demo City", region="US", lat=37.77, lng=-122.42,
            phone="555-0101", accepts_emergency=True, is_demo=True,
        )
    )
    db_session.add(
        Provider(
            name="Dr. A. Patel - Family Medicine", provider_type="doctor", specialty="Family Medicine",
            address="2 Oak St", city="Demo City", region="US", lat=37.80, lng=-122.40,
            phone="555-0103", accepts_emergency=False, is_demo=True,
        )
    )
    db_session.commit()


def test_list_providers_returns_seeded_demo_data(client, db_session) -> None:
    _seed_providers(db_session)
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(p["is_demo"] for p in body)


def test_filter_by_specialty(client, db_session) -> None:
    _seed_providers(db_session)
    resp = client.get("/api/providers", params={"specialty": "Family Medicine"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["specialty"] == "Family Medicine"


def test_filter_by_emergency_only(client, db_session) -> None:
    _seed_providers(db_session)
    resp = client.get("/api/providers", params={"emergency_only": True})
    body = resp.json()
    assert len(body) == 1
    assert body[0]["accepts_emergency"] is True


def test_empty_result_for_unmatched_specialty(client, db_session) -> None:
    _seed_providers(db_session)
    resp = client.get("/api/providers", params={"specialty": "Neurosurgery"})
    assert resp.json() == []


def test_get_unknown_provider_returns_404(client) -> None:
    resp = client.get("/api/providers/does-not-exist")
    assert resp.status_code == 404
