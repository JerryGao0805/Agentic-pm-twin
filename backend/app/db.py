from __future__ import annotations

import json
from typing import Any

import bcrypt
import mysql.connector
from mysql.connector import Error, IntegrityError
from mysql.connector.pooling import MySQLConnectionPool

from app.config import settings
from app.kanban import default_board

_pool: MySQLConnectionPool | None = None


def _get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="pm_pool",
            pool_size=5,
            pool_reset_session=True,
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
        )
    return _pool


def _connect(*, database: str | None, use_admin_credentials: bool) -> Any:
    user = settings.db_admin_user if use_admin_credentials else settings.db_user
    password = (
        settings.db_admin_password if use_admin_credentials else settings.db_password
    )

    params: dict[str, Any] = {
        "host": settings.db_host,
        "port": settings.db_port,
        "user": user,
        "password": password,
    }
    if database:
        params["database"] = database
    return mysql.connector.connect(**params)


def get_connection(database: str | None = None) -> Any:
    if database == settings.db_name:
        try:
            return _get_pool().get_connection()
        except Error:
            pass
    return _connect(database=database, use_admin_credentials=False)


def _create_database_if_missing() -> None:
    db_name = settings.db_name.replace("`", "``")
    statement = (
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )

    first_error: Error | None = None
    for use_admin_credentials in (False, True):
        connection = None
        cursor = None
        try:
            connection = _connect(
                database=None,
                use_admin_credentials=use_admin_credentials,
            )
            cursor = connection.cursor()
            cursor.execute(statement)
            connection.commit()
            return
        except Error as error:
            if first_error is None:
                first_error = error
            if use_admin_credentials:
                raise
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    if first_error is not None:
        raise first_error


def ensure_user_id(cursor: Any, username: str) -> int:
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    if row is not None:
        return int(row[0])

    try:
        cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
        return int(cursor.lastrowid)
    except IntegrityError:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Failed to create or load user row.")
        return int(row[0])


def _column_exists(cursor: Any, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (settings.db_name, table, column),
    )
    return cursor.fetchone() is not None


def _index_exists(cursor: Any, table: str, index_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s",
        (settings.db_name, table, index_name),
    )
    return cursor.fetchone() is not None


def _constraint_exists(cursor: Any, table: str, constraint_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s",
        (settings.db_name, table, constraint_name),
    )
    return cursor.fetchone() is not None


def _column_is_auto_increment(cursor: Any, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT EXTRA FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (settings.db_name, table, column),
    )
    row = cursor.fetchone()
    return row is not None and "auto_increment" in (row[0] or "").lower()


def _apply_migrations(cursor: Any) -> None:
    """Idempotent ALTER statements to upgrade old schemas to current."""

    # --- users table ---
    if not _column_exists(cursor, "users", "password_hash"):
        cursor.execute(
            "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL AFTER username"
        )

    # --- boards table: migrate from old single-row-per-user to multi-board ---
    if not _column_exists(cursor, "boards", "name"):
        cursor.execute(
            "ALTER TABLE boards ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT 'My Board' AFTER user_id"
        )

    # Old schema had user_id as PRIMARY KEY with no auto-increment id column.
    # Check if `id` column exists; if not, we need to restructure.
    if not _column_exists(cursor, "boards", "id"):
        # Must drop FK constraints that reference this table's PK before we can
        # alter it.  Also drop any FK on boards itself that uses the old PK index.
        if _constraint_exists(cursor, "boards", "fk_boards_user"):
            cursor.execute("ALTER TABLE boards DROP FOREIGN KEY fk_boards_user")

        # Drop old primary key (user_id) and add auto-increment id
        cursor.execute("ALTER TABLE boards DROP PRIMARY KEY")
        cursor.execute(
            "ALTER TABLE boards ADD COLUMN id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST"
        )
        if not _index_exists(cursor, "boards", "idx_boards_user_id"):
            cursor.execute(
                "ALTER TABLE boards ADD INDEX idx_boards_user_id (user_id)"
            )

    # Ensure FK from boards -> users exists
    if not _constraint_exists(cursor, "boards", "fk_boards_user"):
        try:
            cursor.execute(
                "ALTER TABLE boards ADD CONSTRAINT fk_boards_user "
                "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
            )
        except Error:
            pass  # FK may fail if data is inconsistent; non-critical

    # --- chat_messages table ---
    if not _column_exists(cursor, "chat_messages", "board_id"):
        cursor.execute(
            "ALTER TABLE chat_messages ADD COLUMN board_id BIGINT NULL AFTER user_id"
        )
        try:
            cursor.execute(
                "ALTER TABLE chat_messages ADD CONSTRAINT fk_chat_messages_board "
                "FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE SET NULL"
            )
        except Error:
            pass


def initialize_database() -> None:
    _create_database_if_missing()

    schema_statements = (
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS boards (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            name VARCHAR(255) NOT NULL DEFAULT 'My Board',
            board_json JSON NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_boards_user_id (user_id),
            CONSTRAINT fk_boards_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            board_id BIGINT NULL,
            role ENUM('user', 'assistant') NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_chat_messages_user_created_at (user_id, created_at),
            CONSTRAINT fk_chat_messages_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_chat_messages_board
                FOREIGN KEY (board_id) REFERENCES boards(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS card_comments (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            board_id BIGINT NOT NULL,
            card_id VARCHAR(255) NOT NULL,
            user_id BIGINT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_card_comments_board_card (board_id, card_id),
            CONSTRAINT fk_card_comments_board
                FOREIGN KEY (board_id) REFERENCES boards(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_card_comments_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS board_activity (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            board_id BIGINT NOT NULL,
            user_id BIGINT NOT NULL,
            action VARCHAR(50) NOT NULL,
            details JSON NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_board_activity_board_created (board_id, created_at),
            CONSTRAINT fk_board_activity_board
                FOREIGN KEY (board_id) REFERENCES boards(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_board_activity_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    )

    connection = None
    cursor = None
    try:
        connection = get_connection(database=settings.db_name)
        cursor = connection.cursor()

        for statement in schema_statements:
            cursor.execute(statement)

        # -- Migrations for pre-existing tables --
        _apply_migrations(cursor)

        user_id = ensure_user_id(cursor, settings.auth_username)

        # Seed default user with hashed password if not set
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        pw_row = cursor.fetchone()
        if pw_row is not None and (pw_row[0] is None or pw_row[0] == ""):
            hashed = bcrypt.hashpw(
                settings.auth_password.encode(), bcrypt.gensalt()
            ).decode()
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed, user_id),
            )

        cursor.execute("SELECT 1 FROM boards WHERE user_id = %s", (user_id,))
        board_exists = cursor.fetchone() is not None
        if not board_exists:
            cursor.execute(
                "INSERT INTO boards (user_id, name, board_json) VALUES (%s, %s, CAST(%s AS JSON))",
                (user_id, "My Board", json.dumps(default_board())),
            )

        connection.commit()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def probe_mysql() -> tuple[bool, str | None]:
    connection = None
    cursor = None
    try:
        connection = get_connection(database=settings.db_name)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True, None
    except Error as error:
        return False, str(error)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
