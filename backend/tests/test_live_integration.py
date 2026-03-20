import os

import pytest

from app.db import probe_mysql
from app.services.openai_service import OpenAIService


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_TESTS") != "1",
        reason="Live integration tests are disabled unless RUN_LIVE_TESTS=1.",
    ),
]


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.fail(f"{name} must be set for live integration tests.")
    return value


def test_live_mysql_connection() -> None:
    connected, error = probe_mysql()
    assert connected, f"MySQL probe failed: {error}"


def test_live_openai_response() -> None:
    api_key = _required_env("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    service = OpenAIService(api_key=api_key, model=model)

    reply = service.get_text_response("Reply with exactly one short sentence.")

    assert isinstance(reply, str)
    assert reply.strip(), "OpenAI live response should not be empty."
