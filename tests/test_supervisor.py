"""Every routing branch of the deterministic supervisor, from fake state dicts."""
import pytest

from agents.supervisor import supervisor
from config import settings
from schemas.critique import Critique

SUFFICIENT = Critique(sufficient=True, critique="good")
INSUFFICIENT = Critique(sufficient=False, critique="needs more")


@pytest.fixture(autouse=True)
def max_loops(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESEARCH_LOOPS", 3)


def route(state):
    return supervisor(state).goto


def test_no_questions_goes_to_planner():
    assert route({"query": "x"}) == "planner"
    assert route({"query": "x", "questions": []}) == "planner"


def test_questions_but_no_research_goes_to_researcher():
    assert route({"questions": ["q"], "research_iterations": 0}) == "researcher"
    assert route({"questions": ["q"]}) == "researcher"


def test_researched_without_critique_goes_to_critic():
    assert route({"questions": ["q"], "research_iterations": 1, "critiques": None}) == "critic"
    assert route({"questions": ["q"], "research_iterations": 1}) == "critic"


def test_sufficient_critique_goes_to_writer():
    state = {"questions": ["q"], "research_iterations": 1, "critiques": SUFFICIENT}
    assert route(state) == "writer"


def test_insufficient_at_max_loops_goes_to_writer():
    state = {"questions": ["q"], "research_iterations": 3, "critiques": INSUFFICIENT}
    assert route(state) == "writer"


def test_insufficient_below_max_loops_back_and_clears_critique():
    state = {"questions": ["q"], "research_iterations": 1, "critiques": INSUFFICIENT}
    cmd = supervisor(state)
    assert cmd.goto == "researcher"
    assert cmd.update == {"critiques": None}


def test_max_loops_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "MAX_RESEARCH_LOOPS", 1)
    state = {"questions": ["q"], "research_iterations": 1, "critiques": INSUFFICIENT}
    assert route(state) == "writer"
