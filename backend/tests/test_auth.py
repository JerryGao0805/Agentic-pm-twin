from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app.main as main_module
from app.main import app


class FakeUserRepository:
    """Returns None for all lookups, falling back to legacy hardcoded credentials."""
    def get_user_by_username(self, username: str):
        return None

    def create_user(self, username: str, password: str) -> int:
        return 1

    def verify_password(self, password: str, password_hash: str) -> bool:
        return False


def test_session_is_unauthenticated_by_default():
    with TestClient(app) as client:
        response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "username": None}


def test_login_success_sets_authenticated_session(monkeypatch):
    monkeypatch.setattr(main_module, "user_repository", FakeUserRepository())

    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
        session_response = client.get("/api/auth/session")

    assert login_response.status_code == 200
    assert login_response.json() == {"authenticated": True, "username": "user"}
    assert session_response.status_code == 200
    assert session_response.json() == {"authenticated": True, "username": "user"}


def test_login_failure_returns_401(monkeypatch):
    monkeypatch.setattr(main_module, "user_repository", FakeUserRepository())

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "user", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_logout_clears_authenticated_session(monkeypatch):
    monkeypatch.setattr(main_module, "user_repository", FakeUserRepository())

    with TestClient(app) as client:
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        logout_response = client.post("/api/auth/logout")
        session_response = client.get("/api/auth/session")

    assert logout_response.status_code == 200
    assert logout_response.json() == {"authenticated": False, "username": None}
    assert session_response.status_code == 200
    assert session_response.json() == {"authenticated": False, "username": None}
