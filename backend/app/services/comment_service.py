from __future__ import annotations

import re
from typing import Any

from app.repositories.comment_repository import CommentRepository

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text)


class CommentService:
    def __init__(self, repository: CommentRepository | None = None) -> None:
        self._repository = repository or CommentRepository()

    def list_comments(
        self, board_id: int, card_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        return self._repository.list_comments(board_id, card_id, limit=limit, offset=offset)

    def add_comment(
        self, board_id: int, card_id: str, username: str, content: str
    ) -> dict[str, Any]:
        content = _strip_html(content.strip())
        if not content:
            raise ValueError("Comment cannot be empty.")
        if len(content) > 2000:
            raise ValueError("Comment too long (max 2000 characters).")
        return self._repository.add_comment(board_id, card_id, username, content)

    def delete_comment(self, comment_id: int, username: str) -> bool:
        return self._repository.delete_comment(comment_id, username)

    def get_comment_counts(self, board_id: int) -> dict[str, int]:
        return self._repository.get_comment_counts(board_id)
