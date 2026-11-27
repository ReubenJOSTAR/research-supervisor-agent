"""Every routing branch of the deterministic supervisor, from fake state dicts."""
import asyncio

import pytest

from agents.supervisor import supervisor
from config import settings
from schemas.critique import Critique

HIGH = {"coverage": 0.9, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}
LOW = {**HIGH, "coverage": 0.3}
GAPS = ["gap one", "gap two"]

SUFFICIENT = Critique(sufficient=True, scores=HIGH, gaps=[], critique="good")
INSUFFICIENT = Critique(sufficient=False, scores=LOW, gaps=GAPS, critique="needs more")
LOW_NO_GAPS = Critique(sufficient=False, scores=LOW, gaps=[], critique="weak but nothing to search")


@pytest.fixture(autouse=True)
def max_loops(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESEARCH_LOOPS", 3)


def run(state):
    return asyncio.run(supervisor(state))


def route(state):
    return run(state).goto


def test_no_questions_goes_to_planner():
    assert route({"query": "x"}) == "planner"
    assert route({"query": "x", "questions": []}) == "planner"


def sent_queries(cmd):
    assert all(s.node == "research_task" for s in cmd.goto)
    return [s.arg["query"] for s in cmd.goto]


def test_round_one_fans_out_one_branch_per_planner_question():
    cmd = run({"questions": ["q1", "q2"], "research_iterations": 0})
    assert sent_queries(cmd) == ["q1", "q2"]
    assert cmd.update["research_queue"] == ["q1", "q2"]
    assert cmd.update["research_iterations"] == 1
    assert sent_queries(run({"questions": ["q"]})) == ["q"]


def test_researched_without_critique_goes_to_critic():
    assert route({"questions": ["q"], "research_iterations": 1, "critiques": None}) == "critic"
    assert route({"questions": ["q"], "research_iterations": 1}) == "critic"


def test_sufficient_critique_goes_to_writer():
    state = {"questions": ["q"], "research_iterations": 1, "critiques": SUFFICIENT}
    assert route(state) == "writer"


def test_insufficient_at_max_loops_goes_to_writer():
    state = {"questions": ["q"], "research_iterations": 3, "critiques": INSUFFICIENT}
    assert route(state) == "writer"


def test_insufficient_without_gaps_goes_to_writer():
    state = {"questions": ["q"], "research_iterations": 1, "critiques": LOW_NO_GAPS}
    assert route(state) == "writer"


def test_round_two_fans_out_gaps_not_questions_and_clears_critique():
    state = {
        "questions": ["original q"],
        "research_queue": ["original q"],
        "research_iterations": 1,
        "critiques": INSUFFICIENT,
    }
    cmd = run(state)
    assert sent_queries(cmd) == GAPS
    assert cmd.update["research_queue"] == GAPS
    assert cmd.update["research_iterations"] == 2
    assert "original q" not in cmd.update["research_queue"]
    assert cmd.update["critiques"] is None


def test_max_loops_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESEARCH_LOOPS", 1)
    state = {"questions": ["q"], "research_iterations": 1, "critiques": INSUFFICIENT}
    assert route(state) == "writer"
