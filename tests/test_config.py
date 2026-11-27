"""Settings defaults, env overrides, the shared LLM factory, and that the graph compiles."""
import importlib

from config import llm as llm_module
from config import settings


def test_env_vars_override_tunables(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("MAX_RESEARCH_LOOPS", "5")
    monkeypatch.setenv("NUM_QUESTIONS", "2")
    monkeypatch.setenv("MAX_TOOL_CALLS_PER_QUESTION", "4")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
    monkeypatch.setenv("MODEL_PRICES", '{"m": {"input": 1, "output": 2}}')
    try:
        s = importlib.reload(settings)
        assert s.OPENAI_MODEL == "gpt-4o"
        assert s.MAX_RESEARCH_LOOPS == 5
        assert s.NUM_QUESTIONS == 2
        assert s.MAX_TOOL_CALLS_PER_QUESTION == 4
        assert s.LLM_TEMPERATURE == 0.5
        assert s.MODEL_PRICES == {"m": {"input": 1, "output": 2}}
    finally:
        monkeypatch.undo()
        importlib.reload(settings)


def test_default_price_table_covers_default_model():
    assert settings.OPENAI_MODEL in settings.MODEL_PRICES


def test_llm_factory_uses_settings(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o")
    monkeypatch.setattr(settings, "LLM_TEMPERATURE", 0.3)
    assert llm_module.get_llm().model_name == "gpt-4o"
    assert llm_module.get_llm().temperature == 0.3
    assert llm_module.get_llm(temperature=0).temperature == 0


def test_graph_compiles():
    from graph.workflow import graph

    assert {"supervisor", "planner", "research_task", "critic", "writer"} <= set(
        graph.nodes
    )
