from __future__ import annotations

from app.kanban import ChatRole
from app.repositories.chat_repository import ChatRepository


class ChatService:
    def __init__(self, repository: ChatRepository | None = None) -> None:
        self._repository = repository or ChatRepository()

    def list_messages(
        self,
        username: str,
        *,
        board_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        return self._repository.list_messages(
            username, board_id=board_id, limit=limit, offset=offset
        )

    def append_message(
        self,
        username: str,
        role: ChatRole,
        content: str,
        board_id: int | None = None,
    ) -> None:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValueError("Chat message cannot be empty.")
        self._repository.append_message(
            username, role, normalized_content, board_id=board_id
        )
