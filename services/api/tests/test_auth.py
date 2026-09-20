def test_register_login_me_logout_flow(client) -> None:
    email = "patient@example.com"
    password = "supersecret123"

    register_resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == email

    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 204

    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401

    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200


def test_duplicate_registration_is_rejected(client) -> None:
    payload = {"email": "dup@example.com", "password": "supersecret123"}
    client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_wrong_password_fails(client) -> None:
    client.post("/api/auth/register", json={"email": "wrongpw@example.com", "password": "correcthorse123"})
    resp = client.post("/api/auth/login", json={"email": "wrongpw@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_short_password_rejected_at_validation(client) -> None:
    resp = client.post("/api/auth/register", json={"email": "short@example.com", "password": "short"})
    assert resp.status_code == 422
