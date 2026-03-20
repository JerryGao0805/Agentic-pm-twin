from __future__ import annotations

from typing import Any

from app.config import settings
from app.db import ensure_user_id, get_connection
from app.kanban import ChatRole


class ChatRepository:
    def list_messages(
        self,
        username: str,
        *,
        board_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, str]]:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()

            user_id = ensure_user_id(cursor, username)

            if board_id is not None:
                cursor.execute(
                    """
                    SELECT role, content FROM (
                        SELECT role, content, id
                        FROM chat_messages
                        WHERE user_id = %s AND board_id = %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                    ) recent ORDER BY id ASC
                    """,
                    (user_id, board_id, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT role, content FROM (
                        SELECT role, content, id
                        FROM chat_messages
                        WHERE user_id = %s
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                    ) recent ORDER BY id ASC
                    """,
                    (user_id, limit, offset),
                )
            rows = cursor.fetchall()
            connection.commit()

            messages: list[dict[str, str]] = []
            for role, content in rows:
                messages.append({"role": str(role), "content": str(content)})

            return messages
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def append_message(
        self,
        username: str,
        role: ChatRole,
        content: str,
        board_id: int | None = None,
    ) -> None:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()

            user_id = ensure_user_id(cursor, username)

            cursor.execute(
                """
                INSERT INTO chat_messages (user_id, board_id, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, board_id, role, content),
            )
            connection.commit()
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()
