from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-env")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    COOKIE_NAME: str = os.getenv("AUTH_COOKIE_NAME", "auth_token")  # Изменили имя cookie
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "session")  # Cookie для сессии
    COOKIE_MAX_AGE: int = int(os.getenv("AUTH_COOKIE_MAX_AGE", "86400"))  # 24h
    LOGIN_PATH: str = "/login"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(Path(__file__).resolve().parent.parent / "uploads"))
    UPLOAD_MAX_SIZE: int = int(os.getenv("UPLOAD_MAX_SIZE", "10485760"))  # 10 MB


settings = Settings()
