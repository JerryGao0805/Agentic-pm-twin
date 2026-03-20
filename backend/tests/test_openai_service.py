import pytest

from app.services.openai_service import (
    OpenAIConfigError,
    OpenAIService,
    OpenAIUpstreamError,
)


class FakeResponse:
    def __init__(self, output_text: str = "") -> None:
        self.output_text = output_text


class FakeResponsesAPI:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict[str, str]] = []

    def create(self, *, model: str, input: str):
        self.calls.append({"model": model, "input": input})
        if self._error is not None:
            raise self._error
        if self._response is not None:
            return self._response
        return FakeResponse("")


class FakeClient:
    def __init__(self, responses_api: FakeResponsesAPI) -> None:
        self.responses = responses_api


def test_openai_service_invokes_client_with_model_and_prompt() -> None:
    responses_api = FakeResponsesAPI(response=FakeResponse("4"))
    service = OpenAIService(
        api_key="test-key",
        model="gpt-4o-mini",
        client=FakeClient(responses_api),
    )

    reply = service.get_text_response("What is 2+2?")

    assert reply == "4"
    assert responses_api.calls == [{"model": "gpt-4o-mini", "input": "What is 2+2?"}]


def test_openai_service_rejects_missing_api_key() -> None:
    service = OpenAIService(api_key="   ", model="gpt-4o-mini")

    with pytest.raises(OpenAIConfigError):
        service.get_text_response("2+2")


def test_openai_service_handles_upstream_failure() -> None:
    responses_api = FakeResponsesAPI(error=RuntimeError("network"))
    service = OpenAIService(
        api_key="test-key",
        model="gpt-4o-mini",
        client=FakeClient(responses_api),
    )

    with pytest.raises(OpenAIUpstreamError):
        service.get_text_response("2+2")


def test_openai_service_rejects_empty_prompt() -> None:
    service = OpenAIService(
        api_key="test-key",
        model="gpt-4o-mini",
        client=FakeClient(FakeResponsesAPI(response=FakeResponse("4"))),
    )

    with pytest.raises(ValueError):
        service.get_text_response("   ")
