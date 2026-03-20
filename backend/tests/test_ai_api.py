from fastapi.testclient import TestClient

import app.main as main_module
from app.config import settings
from app.services.openai_service import OpenAIConfigError, OpenAIUpstreamError


class FakeOpenAIService:
    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.model = "gpt-4o-mini"
        self.prompts: list[str] = []

    def get_text_response(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.mode == "config_error":
            raise OpenAIConfigError("OPENAI_API_KEY is not configured.")
        if self.mode == "upstream_error":
            raise OpenAIUpstreamError("OpenAI request failed.")
        if self.mode == "value_error":
            raise ValueError("Prompt cannot be empty.")
        return "4"


def test_ai_test_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "openai_service", FakeOpenAIService())

    with TestClient(main_module.app) as client:
        response = client.post("/api/ai/test", json={"prompt": "2+2"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_ai_test_returns_reply_when_authenticated(monkeypatch) -> None:
    fake_service = FakeOpenAIService(mode="ok")
    monkeypatch.setattr(main_module, "openai_service", fake_service)

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.post("/api/ai/test", json={"prompt": "What is 2+2?"})

    assert response.status_code == 200
    assert response.json() == {"model": "gpt-4o-mini", "reply": "4"}
    assert fake_service.prompts == ["What is 2+2?"]


def test_ai_test_handles_missing_key(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "openai_service",
        FakeOpenAIService(mode="config_error"),
    )

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.post("/api/ai/test", json={"prompt": "2+2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENAI_API_KEY is not configured."}


def test_ai_test_handles_upstream_error(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "openai_service",
        FakeOpenAIService(mode="upstream_error"),
    )

    with TestClient(main_module.app) as client:
        client.cookies.set(settings.auth_cookie_name, settings.sign_session(settings.auth_username))
        response = client.post("/api/ai/test", json={"prompt": "2+2"})

    assert response.status_code == 502
    assert response.json() == {"detail": "OpenAI request failed."}
