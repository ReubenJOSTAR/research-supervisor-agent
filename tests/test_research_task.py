"""Phase 4: parallel research via Send. Mocked LLMs and search; no network calls."""
from langchain_core.messages import AIMessage

import agents.critic as critic_module
import agents.planner as planner_module
import agents.research_task as rt
import agents.writer as writer_module
from agents.planner import ResearchPlan
from config import settings
from graph.workflow import graph
from schemas.critique import CritiqueAssessment
from fakes import Fake, FakeExtractor, FakeResearchAgent, FakeSearch

QUESTIONS = ["Q-ALPHA", "Q-BETA", "Q-GAMMA"]
HIGH = {"coverage": 0.9, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}
INITIAL = {"query": "topic", "questions": [], "findings": [], "critiques": None,
           "critique_history": [], "research_iterations": 0, "finalReport": ""}


def _patch_graph(monkeypatch, agent, search):
    monkeypatch.setattr(planner_module, "planner_llm", Fake(ResearchPlan(questions=QUESTIONS)))
    monkeypatch.setattr(rt, "research_agent", agent)
    monkeypatch.setattr(rt, "search_web", search)
    monkeypatch.setattr(rt, "extractor_llm", FakeExtractor(QUESTIONS))
    monkeypatch.setattr(critic_module, "judge",
                        Fake(CritiqueAssessment(scores=HIGH, gaps=[], critique="good")))
    monkeypatch.setattr(writer_module, "llm", Fake(AIMessage(content="REPORT")))


def test_fan_out_creates_one_branch_per_question(monkeypatch):
    agent, search = FakeResearchAgent(QUESTIONS), FakeSearch()
    _patch_graph(monkeypatch, agent, search)

    branches, result = [], None
    for mode, chunk in graph.stream(INITIAL, stream_mode=["updates", "values"]):
        if mode == "updates" and "research_task" in chunk:
            branches.append(chunk["research_task"])
        if mode == "values":
            result = chunk

    assert len(branches) == len(QUESTIONS)
    assert sorted(search.queries) == sorted(QUESTIONS)
    assert sorted(f.finding for f in result["findings"]) == sorted(f"fact about {q}" for q in QUESTIONS)
    assert result["research_iterations"] == 1
    assert result["finalReport"] == "REPORT"


def test_one_failing_llm_branch_does_not_fail_the_run(monkeypatch):
    _patch_graph(monkeypatch, FakeResearchAgent(QUESTIONS, fail_on={"Q-BETA"}), FakeSearch())

    result = graph.invoke(INITIAL)

    assert sorted(f.finding for f in result["findings"]) == ["fact about Q-ALPHA", "fact about Q-GAMMA"]
    assert result["finalReport"] == "REPORT"


def test_one_failing_search_branch_does_not_fail_the_run(monkeypatch):
    _patch_graph(monkeypatch, FakeResearchAgent(QUESTIONS), FakeSearch(fail_on={"Q-GAMMA"}))

    result = graph.invoke(INITIAL)

    assert sorted(f.finding for f in result["findings"]) == ["fact about Q-ALPHA", "fact about Q-BETA"]
    assert result["finalReport"] == "REPORT"


def test_branch_failure_returns_no_findings_and_logs_warning(monkeypatch, caplog):
    monkeypatch.setattr(rt, "research_agent", FakeResearchAgent(["Q"], fail_on={"Q"}))

    assert rt.research_task({"topic": "t", "task": "Q"}) == {"findings": []}
    assert "research_task failed" in caplog.text and "Q" in caplog.text


def test_branch_caps_tool_calls(monkeypatch):
    search = FakeSearch()
    monkeypatch.setattr(settings, "MAX_TOOL_CALLS_PER_QUESTION", 2)
    monkeypatch.setattr(rt, "research_agent", FakeResearchAgent(["Q"], calls_per_task=5))
    monkeypatch.setattr(rt, "search_web", search)
    monkeypatch.setattr(rt, "extractor_llm", FakeExtractor(["Q"]))

    result = rt.research_task({"topic": "t", "task": "Q"})

    assert search.queries == ["Q", "Q"]
    assert [f.finding for f in result["findings"]] == ["fact about Q"]


def test_branch_without_tool_calls_returns_no_findings(monkeypatch):
    extractor = Fake()
    monkeypatch.setattr(rt, "research_agent", Fake(AIMessage(content="nothing to search")))
    monkeypatch.setattr(rt, "extractor_llm", extractor)

    assert rt.research_task({"topic": "t", "task": "Q"}) == {"findings": []}
    assert extractor.calls == []
