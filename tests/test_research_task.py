"""Parallel research via Send: fan-out per query, branch extraction, and failure isolation.

The LLMs and search are fakes; nothing calls OpenAI or Tavily.
"""
import threading

import pytest
from langchain_core.messages import AIMessage

import agents.critic as critic_module
import agents.planner as planner_module
import agents.research_task as rt
import agents.writer as writer_module
from agents.planner import ResearchPlan
from config import settings
from graph.workflow import graph
from schemas.critique import CritiqueAssessment
from schemas.finding import Finding

HIGH = {"coverage": 0.9, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}
LOW = {**HIGH, "coverage": 0.3}


def _query_in(prompt) -> str:
    """The query line of a research_task prompt (the first message's content)."""
    text = prompt[0].content if isinstance(prompt, list) else prompt
    return text.split("Question:")[1].strip().splitlines()[0].strip()


class FakeResearchAgent:
    """Asks for `n_calls` searches of its own query; raises for queries in `fail_on`."""

    def __init__(self, n_calls=1, fail_on=()):
        self.n_calls, self.fail_on = n_calls, set(fail_on)
        self.queries, self.lock = [], threading.Lock()

    def invoke(self, messages):
        query = _query_in(messages)
        with self.lock:
            self.queries.append(query)
        if query in self.fail_on:
            raise RuntimeError("LLM exploded")
        calls = [{"name": "search_web", "args": {"query": query}, "id": f"{query}-{i}"}
                 for i in range(self.n_calls)]
        return AIMessage(content="", tool_calls=calls)


class FakeSearch:
    def __init__(self, fail_on=()):
        self.fail_on, self.calls = set(fail_on), []

    def invoke(self, args):
        self.calls.append(args["query"])
        if args["query"] in self.fail_on:
            raise ConnectionError("Tavily down")
        return f"Source: https://example.com/{args['query']}\nContent: about {args['query']}"


class FakeExtractor:
    """One finding per call, sourced from the query in the prompt."""

    def invoke(self, prompt):
        q = _query_in(prompt)
        return rt.Findings(findings=[Finding(finding=f"fact {q}", source=f"https://example.com/{q}",
                                             evidence="e")])


class Fake:
    def __init__(self, *outputs):
        self.outputs = list(outputs)

    def invoke(self, arg):
        return self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]


@pytest.fixture
def fakes(monkeypatch):
    agent, search = FakeResearchAgent(), FakeSearch()
    monkeypatch.setattr(rt, "research_agent", agent)
    monkeypatch.setattr(rt, "search_web", search)
    monkeypatch.setattr(rt, "extractor_llm", FakeExtractor())
    monkeypatch.setattr(writer_module, "llm", Fake(AIMessage(content="REPORT")))
    monkeypatch.setattr(critic_module, "judge", Fake(CritiqueAssessment(scores=HIGH, gaps=[], critique="ok")))
    return agent, search


def _run():
    return graph.invoke({"query": "topic", "questions": [], "findings": [], "critiques": None,
                         "critique_history": [], "research_iterations": 0, "finalReport": ""})


def _plan(monkeypatch, questions):
    monkeypatch.setattr(planner_module, "planner_llm", Fake(ResearchPlan(questions=questions)))


# ---- one branch in isolation ------------------------------------------------

def test_branch_extracts_findings_for_its_own_query(fakes):
    agent, search = fakes
    result = rt.research_task({"query": "solar"})
    assert [f.finding for f in result["findings"]] == ["fact solar"]
    assert search.calls == ["solar"]


def test_branch_caps_tool_calls_at_setting(fakes, monkeypatch):
    agent, search = fakes
    agent.n_calls = 5
    monkeypatch.setattr(settings, "MAX_TOOL_CALLS_PER_QUESTION", 2)
    rt.research_task({"query": "q"})
    assert len(search.calls) == 2


def test_branch_without_tool_calls_returns_no_findings(fakes):
    agent, search = fakes
    agent.n_calls = 0
    assert rt.research_task({"query": "q"}) == {"findings": []}
    assert search.calls == []


def test_branch_llm_error_returns_no_findings_and_warns(fakes, caplog):
    agent, _ = fakes
    agent.fail_on = {"bad"}
    assert rt.research_task({"query": "bad"}) == {"findings": []}
    assert "bad" in caplog.text


def test_branch_search_error_returns_no_findings_and_warns(fakes, monkeypatch, caplog):
    monkeypatch.setattr(rt, "search_web", FakeSearch(fail_on={"bad"}))
    assert rt.research_task({"query": "bad"}) == {"findings": []}
    assert "bad" in caplog.text


# ---- fan-out through the real graph ------------------------------------------

def test_fan_out_creates_one_branch_per_question(fakes, monkeypatch):
    agent, _ = fakes
    questions = ["q1", "q2", "q3", "q4"]
    _plan(monkeypatch, questions)

    result = _run()

    assert sorted(agent.queries) == questions                 # N branches, one query each
    assert sorted(f.finding for f in result["findings"]) == [f"fact {q}" for q in questions]
    assert result["research_iterations"] == 1
    assert result["finalReport"] == "REPORT"


def test_one_failing_branch_does_not_fail_the_run(fakes, monkeypatch):
    agent, _ = fakes
    agent.fail_on = {"q2"}
    monkeypatch.setattr(rt, "search_web", FakeSearch(fail_on={"q3"}))
    _plan(monkeypatch, ["q1", "q2", "q3", "q4"])

    result = _run()

    assert sorted(f.finding for f in result["findings"]) == ["fact q1", "fact q4"]
    assert result["finalReport"] == "REPORT"


def test_round_two_fans_out_one_branch_per_gap(fakes, monkeypatch):
    agent, _ = fakes
    _plan(monkeypatch, ["Q1", "Q2"])
    monkeypatch.setattr(critic_module, "judge", Fake(
        CritiqueAssessment(scores=LOW, gaps=["GAP-A", "GAP-B", "GAP-C"], critique="thin"),
        CritiqueAssessment(scores=HIGH, gaps=[], critique="good"),
    ))

    result = _run()

    assert sorted(agent.queries[:2]) == ["Q1", "Q2"]
    assert sorted(agent.queries[2:]) == ["GAP-A", "GAP-B", "GAP-C"]
    assert len(result["findings"]) == 5                       # both rounds accumulate
    assert result["research_iterations"] == 2
    assert [c.sufficient for c in result["critique_history"]] == [False, True]
