"""All env vars and tunables live here. Every tunable can be overridden by an env var."""
import json
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not found")

# LLM
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))

# Research loop
MAX_RESEARCH_LOOPS = int(os.getenv("MAX_RESEARCH_LOOPS", "3"))
NUM_QUESTIONS = int(os.getenv("NUM_QUESTIONS", "5"))
MAX_TOOL_CALLS_PER_QUESTION = int(os.getenv("MAX_TOOL_CALLS_PER_QUESTION", "2"))

# USD per 1M tokens, keyed by model name. Override the whole table with a JSON
# string, e.g. MODEL_PRICES='{"gpt-4o-mini": {"input": 0.15, "output": 0.6}}'.
_DEFAULT_MODEL_PRICES = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}
MODEL_PRICES: dict[str, dict[str, float]] = (
    json.loads(os.environ["MODEL_PRICES"]) if os.getenv("MODEL_PRICES") else _DEFAULT_MODEL_PRICES
)
