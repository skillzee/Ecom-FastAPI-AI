import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _required(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ValueError(f"Missing environment variable: {name}")

    return value


class Settings:
    def __init__(self):
        self.openai_api_key = _required("OPENAI_API_KEY")
        self.openai_base_url = _required("OPENAI_BASE_URL")
        self.openai_model = _required("OPENAI_MODEL")


class AuthSettings:
    def __init__(self):
        self.jwt_secret_key = _required("JWT_SECRET_KEY")
        if len(self.jwt_secret_key.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")

        self.access_token_expire_minutes = 30


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ENV_FILE)
    return Settings()


@lru_cache
def get_auth_settings() -> AuthSettings:
    load_dotenv(ENV_FILE)
    return AuthSettings()
