from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import settings


class OpenAIConfigError(RuntimeError):
    pass


class OpenAIUpstreamError(RuntimeError):
    pass


class OpenAIService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model if model is not None else settings.openai_model
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    def get_text_response(self, prompt: str) -> str:
        prompt_text = prompt.strip()
        if not prompt_text:
            raise ValueError("Prompt cannot be empty.")

        client = self._get_client()

        try:
            response = client.responses.create(
                model=self._model,
                input=prompt_text,
            )
        except Exception as error:
            raise OpenAIUpstreamError("OpenAI request failed.") from error

        output_text = self._extract_output_text(response)
        if not output_text:
            raise OpenAIUpstreamError("OpenAI returned an empty response.")

        return output_text

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        api_key = self._api_key.strip()
        if not api_key:
            raise OpenAIConfigError("OPENAI_API_KEY is not configured.")

        self._client = OpenAI(api_key=api_key)
        return self._client

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output_items = getattr(response, "output", None)
        if isinstance(output_items, list):
            text_chunks: list[str] = []
            for output_item in output_items:
                content_blocks = getattr(output_item, "content", None)
                if not isinstance(content_blocks, list):
                    continue
                for block in content_blocks:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        text_chunks.append(text)

            merged = "".join(text_chunks).strip()
            if merged:
                return merged

        return ""
