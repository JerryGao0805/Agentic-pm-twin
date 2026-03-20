from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.openai_service import OpenAIService


class AIAssistantFormatError(RuntimeError):
    pass


class AIAssistantOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_message: str = Field(min_length=1)
    board: dict[str, Any] | None = None


class AIAssistantService:
    def __init__(self, openai_service: OpenAIService | None = None) -> None:
        self._openai_service = openai_service or OpenAIService()

    def build_prompt(
        self,
        board: dict[str, Any],
        chat_history: list[dict[str, str]],
        user_message: str,
    ) -> str:
        context = {
            "board": board,
            "chat_history": chat_history,
            "user_message": user_message,
        }

        current_columns = ", ".join(
            col.get("id", "") for col in board.get("columns", []) if isinstance(col, dict)
        )

        return (
            "You are a kanban project assistant.\n"
            "Return only a valid JSON object with exactly these keys: "
            '"assistant_message" and "board".\n'
            'Use this schema exactly: {"assistant_message": string, "board": object|null}.\n'
            "If the board should not change, set board to null.\n"
            "If board changes, return the full board JSON object, not partial updates.\n"
            f"The board currently has these columns: {current_columns}.\n"
            "Users can add, remove, or reorder columns. Preserve existing column IDs when possible.\n"
            "Cards can have: id, title, details, priority (low/medium/high or null), due_date (YYYY-MM-DD or null), assignee (string or null).\n"
            "Do not include markdown fences or extra keys.\n\n"
            "Context JSON:\n"
            f"{json.dumps(context, ensure_ascii=True)}"
        )

    def parse_output(self, output_text: str) -> AIAssistantOutput:
        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise AIAssistantFormatError("AI response was not valid JSON.") from error

        try:
            return AIAssistantOutput.model_validate(payload)
        except ValidationError as error:
            raise AIAssistantFormatError("AI response did not match expected schema.") from error

    def generate_reply(
        self,
        board: dict[str, Any],
        chat_history: list[dict[str, str]],
        user_message: str,
    ) -> AIAssistantOutput:
        prompt = self.build_prompt(board, chat_history, user_message)
        output_text = self._openai_service.get_text_response(prompt)
        return self.parse_output(output_text)
