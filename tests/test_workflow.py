"""Two research rounds through the real graph with fakes: round 2 researches only the gaps."""
from langchain_core.messages import AIMessage

import agents.critic as critic_module
import agents.planner as planner_module
import agents.research_task as rt
import agents.writer as writer_module
from agents.planner import ResearchPlan
from graph.workflow import graph
from schemas.critique import CritiqueAssessment
from fakes import Fake, FakeExtractor, FakeResearchAgent, FakeSearch

LOW = {"coverage": 0.3, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}
HIGH = {k: 0.9 for k in LOW}
TASKS = ["ORIGINAL-Q", "GAP-A"]


def test_round_two_researches_only_the_critic_gaps(monkeypatch):
    search = FakeSearch()
    monkeypatch.setattr(planner_module, "planner_llm", Fake(ResearchPlan(questions=["ORIGINAL-Q"])))
    monkeypatch.setattr(rt, "research_agent", FakeResearchAgent(TASKS))
    monkeypatch.setattr(rt, "search_web", search)
    monkeypatch.setattr(rt, "extractor_llm", FakeExtractor(TASKS))
    monkeypatch.setattr(
        critic_module,
        "judge",
        Fake(
            CritiqueAssessment(scores=LOW, gaps=["GAP-A"], critique="thin"),
            CritiqueAssessment(scores=HIGH, gaps=[], critique="good"),
        ),
    )
    monkeypatch.setattr(writer_module, "llm", Fake(AIMessage(content="REPORT")))

    result = graph.invoke({"query": "topic", "questions": [], "findings": [],
                           "critiques": None, "critique_history": [], "research_iterations": 0,
                           "finalReport": ""})

    assert search.queries == ["ORIGINAL-Q", "GAP-A"]
    # Findings from both rounds accumulate.
    assert [f.finding for f in result["findings"]] == ["fact about ORIGINAL-Q", "fact about GAP-A"]
    assert result["research_iterations"] == 2
    assert [c.sufficient for c in result["critique_history"]] == [False, True]
    assert result["finalReport"] == "REPORT"
