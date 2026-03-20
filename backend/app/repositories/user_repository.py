from __future__ import annotations

from typing import Any

import bcrypt

from app.config import settings
from app.db import get_connection


class UserRepository:
    def create_user(self, username: str, password: str) -> int:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            user_id = int(cursor.lastrowid)
            connection.commit()
            return user_id
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        connection = None
        cursor = None
        try:
            connection = get_connection(database=settings.db_name)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            password_hash = row[2]
            return {
                "id": int(row[0]),
                "username": str(row[1]),
                "password_hash": password_hash if password_hash is not None else None,
            }
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
