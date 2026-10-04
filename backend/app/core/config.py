import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings:
    def __init__(self):
        self.openai_api_key = self._required("OPENAI_API_KEY")
        self.openai_base_url = self._required("OPENAI_BASE_URL")
        self.openai_model = self._required("OPENAI_MODEL")

    @staticmethod
    def _required(name: str) -> str:
        value = os.getenv(name)

        if value is None or not value.strip():
            raise ValueError(f"Missing environment variable: {name}")

        return value


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ENV_FILE)
    return Settings()