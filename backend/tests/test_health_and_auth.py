import time

import jwt
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

TEST_JWT_SECRET = "test-supabase-jwt-secret-must-be-at-least-32-bytes"


def get_test_settings() -> Settings:
    return Settings(
        supabase_jwt_secret=TEST_JWT_SECRET,
        cors_origin="http://localhost:5173",
    )


app.dependency_overrides[get_settings] = get_test_settings
client = TestClient(app)


def create_token(
    sub: str | None = "user-123",
    secret: str = TEST_JWT_SECRET,
    exp_offset: int = 3600,
) -> str:
    payload: dict[str, str | int] = {"exp": int(time.time()) + exp_offset}
    if sub is not None:
        payload["sub"] = sub
    return jwt.encode(payload, secret, algorithm="HS256")


def test_health_returns_200() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_route_without_token_returns_401() -> None:
    response = client.get("/api/me")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_with_invalid_token_returns_401() -> None:
    token = create_token(secret="wrong-secret-key-that-is-at-least-32-bytes-long")
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_TOKEN"


def test_protected_route_with_expired_token_returns_401() -> None:
    token = create_token(exp_offset=-60)
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "TOKEN_EXPIRED"


def test_protected_route_with_valid_token_returns_200() -> None:
    token = create_token(sub="supabase-user-uuid-001")
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"user_id": "supabase-user-uuid-001"}
