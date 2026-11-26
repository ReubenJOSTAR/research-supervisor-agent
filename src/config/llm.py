"""Shared LLM factory: the one place ChatOpenAI is created."""
from langchain_openai import ChatOpenAI

from config import settings


def get_llm(temperature: float | None = None) -> ChatOpenAI:
    """Chat model configured from settings. `temperature` overrides the default."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        api_key=settings.OPENAI_API_KEY,
    )
