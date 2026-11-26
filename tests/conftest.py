"""Dummy keys so modules import without real credentials. Tests never call OpenAI or Tavily."""
import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
