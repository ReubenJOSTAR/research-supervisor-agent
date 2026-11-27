"""Every routing branch of the deterministic supervisor, from fake state dicts."""
import pytest
from langgraph.types import Send

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


def route(state):
    return supervisor(state).goto


def test_no_questions_goes_to_planner():
    assert route({"query": "x"}) == "planner"
    assert route({"query": "x", "questions": []}) == "planner"


def sent_tasks(cmd):
    """The queries of the parallel research branches a Command fans out to."""
    assert all(isinstance(s, Send) and s.node == "research_task" for s in cmd.goto)
    return [s.arg["task"] for s in cmd.goto]


def test_round_one_fans_out_one_branch_per_planner_question():
    cmd = supervisor({"query": "topic", "questions": ["q1", "q2"], "research_iterations": 0})
    assert sent_tasks(cmd) == ["q1", "q2"]
    assert all(s.arg["topic"] == "topic" for s in cmd.goto)
    assert cmd.update == {"research_queue": ["q1", "q2"], "research_iterations": 1}
    assert sent_tasks(supervisor({"query": "t", "questions": ["q"]})) == ["q"]


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


def test_round_two_fans_out_over_gaps_not_questions_and_clears_critique():
    state = {
        "query": "topic",
        "questions": ["original q"],
        "research_queue": ["original q"],
        "research_iterations": 1,
        "critiques": INSUFFICIENT,
    }
    cmd = supervisor(state)
    assert sent_tasks(cmd) == GAPS
    assert cmd.update["research_queue"] == GAPS
    assert "original q" not in sent_tasks(cmd)
    assert cmd.update["critiques"] is None
    assert cmd.update["research_iterations"] == 2


def test_max_loops_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESEARCH_LOOPS", 1)
    state = {"questions": ["q"], "research_iterations": 1, "critiques": INSUFFICIENT}
    assert route(state) == "writer"
