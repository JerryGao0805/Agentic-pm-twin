from __future__ import annotations

from typing import Any

from app.db import db_connection, ensure_user_id


class CommentRepository:
    def list_comments(
        self, board_id: int, card_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        with db_connection(commit=False) as (connection, cursor):
            cursor.execute(
                "SELECT cc.id, cc.card_id, u.username, cc.content, cc.created_at "
                "FROM card_comments cc JOIN users u ON cc.user_id = u.id "
                "WHERE cc.board_id = %s AND cc.card_id = %s "
                "ORDER BY cc.created_at ASC LIMIT %s OFFSET %s",
                (board_id, card_id, limit, offset),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": int(row[0]),
                    "card_id": str(row[1]),
                    "username": str(row[2]),
                    "content": str(row[3]),
                    "created_at": str(row[4]),
                }
                for row in rows
            ]

    def add_comment(
        self, board_id: int, card_id: str, username: str, content: str
    ) -> dict[str, Any]:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "INSERT INTO card_comments (board_id, card_id, user_id, content) "
                "VALUES (%s, %s, %s, %s)",
                (board_id, card_id, user_id, content),
            )
            comment_id = int(cursor.lastrowid)
            cursor.execute(
                "SELECT created_at FROM card_comments WHERE id = %s",
                (comment_id,),
            )
            row = cursor.fetchone()
            return {
                "id": comment_id,
                "card_id": card_id,
                "username": username,
                "content": content,
                "created_at": str(row[0]) if row else "",
            }

    def delete_comment(self, comment_id: int, username: str) -> bool:
        with db_connection() as (connection, cursor):
            user_id = ensure_user_id(cursor, username)
            cursor.execute(
                "DELETE FROM card_comments WHERE id = %s AND user_id = %s",
                (comment_id, user_id),
            )
            return cursor.rowcount > 0

    def get_comment_counts(self, board_id: int) -> dict[str, int]:
        with db_connection(commit=False) as (connection, cursor):
            cursor.execute(
                "SELECT card_id, COUNT(*) FROM card_comments "
                "WHERE board_id = %s GROUP BY card_id",
                (board_id,),
            )
            rows = cursor.fetchall()
            return {str(row[0]): int(row[1]) for row in rows}
