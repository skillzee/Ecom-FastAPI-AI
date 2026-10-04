from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core import config


@lru_cache
def get_chat_model() -> ChatOpenAI:
    if not all((config.OPENAI_API_KEY, config.OPENAI_BASE_URL, config.OPENAI_MODEL)):
        raise ValueError("Set OPENAI_API_KEY, OPENAI_BASE_URL, and OPENAI_MODEL in .env")

    return ChatOpenAI(
        model=config.OPENAI_MODEL,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        timeout=30,
        max_retries=1,
    )
