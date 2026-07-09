from fastapi.testclient import TestClient


def test_register_login_and_me(client: TestClient) -> None:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer@example.com",
            "display_name": "Demo Customer",
            "password": "secure-password",
            "role": "customer",
        },
    )

    assert register.status_code == 201
    access_token = register.json()["access_token"]
    assert access_token

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "secure-password"},
    )
    assert login.status_code == 200

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "customer"


def test_health_and_root(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/api/v1/health/live").json() == {"status": "alive"}
    assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
