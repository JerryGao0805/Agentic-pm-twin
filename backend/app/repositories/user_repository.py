from __future__ import annotations

import logging
from typing import Any

import bcrypt

from app.db import db_connection

logger = logging.getLogger(__name__)


class UserRepository:
    def create_user(self, username: str, password: str) -> int:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with db_connection() as (connection, cursor):
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            return int(cursor.lastrowid)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with db_connection(commit=False) as (connection, cursor):
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

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    def get_profile(self, username: str) -> dict[str, Any] | None:
        with db_connection(commit=False) as (connection, cursor):
            cursor.execute(
                "SELECT u.id, u.username, u.created_at, COUNT(b.id) AS board_count "
                "FROM users u LEFT JOIN boards b ON u.id = b.user_id "
                "WHERE u.username = %s GROUP BY u.id",
                (username,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "id": int(row[0]),
                "username": str(row[1]),
                "created_at": str(row[2]),
                "board_count": int(row[3]),
            }

    def update_password(self, username: str, new_password: str) -> bool:
        new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        with db_connection() as (connection, cursor):
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (new_hash, username),
            )
            return cursor.rowcount > 0

    def delete_user(self, username: str) -> bool:
        logger.info("Deleting user account: %s", username)
        with db_connection() as (connection, cursor):
            cursor.execute(
                "DELETE FROM users WHERE username = %s",
                (username,),
            )
            return cursor.rowcount > 0
