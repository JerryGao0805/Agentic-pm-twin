from dataclasses import dataclass
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "pm-backend")
    db_host: str = os.getenv("DB_HOST", "mysql")
    db_port: int = _int_env("DB_PORT", 3306)
    db_user: str = os.getenv("DB_USER", "pm_user")
    db_password: str = os.getenv("DB_PASSWORD", "pm_password")
    db_admin_user: str = os.getenv("DB_ADMIN_USER", "root")
    db_admin_password: str = os.getenv("DB_ADMIN_PASSWORD", "root_password")
    db_name: str = os.getenv("DB_NAME", "pm_db")
    frontend_dist_dir: str = os.getenv("FRONTEND_DIST_DIR", "/app/frontend-dist")
    auth_username: str = os.getenv("AUTH_USERNAME", "user")
    auth_password: str = os.getenv("AUTH_PASSWORD", "password")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "pm_session")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    cors_origins: str = os.getenv("CORS_ORIGINS", "")

    def __post_init__(self) -> None:
        if self.auth_password == "password":
            logger.warning(
                "AUTH_PASSWORD is set to the default value 'password'. "
                "Please set a strong password via the AUTH_PASSWORD environment variable."
            )
        if not self.session_secret:
            raise RuntimeError(
                "SESSION_SECRET environment variable is required. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if os.getenv("ENVIRONMENT", "").lower() == "production" and not self.cookie_secure:
            logger.warning(
                "COOKIE_SECURE is not set in production. "
                "Set COOKIE_SECURE=true for secure cookies."
            )

    def _get_secret_key(self) -> str:
        return self.session_secret

    def sign_session(self, username: str) -> str:
        key = self._get_secret_key().encode()
        signature = hmac.new(key, username.encode(), hashlib.sha256).hexdigest()
        return f"{username}:{signature}"

    def verify_session(self, token: str) -> str | None:
        if not token or ":" not in token:
            return None
        username, signature = token.rsplit(":", 1)
        expected = self.sign_session(username)
        if hmac.compare_digest(token, expected):
            return username
        return None


settings = Settings()
