"""Two research rounds through the real graph with fake LLMs: round 2 researches only the gaps."""
from langchain_core.messages import AIMessage

import agents.critic as critic_module
import agents.planner as planner_module
import agents.researcher as researcher_module
import agents.writer as writer_module
from agents.planner import ResearchPlan
from graph.workflow import graph
from schemas.critique import CritiqueAssessment

LOW = {"coverage": 0.3, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}
HIGH = {k: 0.9 for k in LOW}


class Fake:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, arg):
        self.calls.append(arg)
        return self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]


def test_round_two_researches_only_the_critic_gaps(monkeypatch):
    researcher = Fake(AIMessage(content="no searches needed"))
    monkeypatch.setattr(planner_module, "planner_llm", Fake(ResearchPlan(questions=["ORIGINAL-Q"])))
    monkeypatch.setattr(researcher_module, "research_agent", researcher)
    monkeypatch.setattr(
        critic_module,
        "judge",
        Fake(
            CritiqueAssessment(scores=LOW, gaps=["GAP-A"], critique="thin"),
            CritiqueAssessment(scores=HIGH, gaps=[], critique="good"),
        ),
    )
    monkeypatch.setattr(writer_module, "llm", Fake(AIMessage(content="REPORT")))

    result = graph.invoke({"query": "topic", "messages": [], "questions": [], "findings": [],
                           "critiques": None, "critique_history": [], "research_iterations": 0,
                           "finalReport": ""})

    round1, round2 = (call[0].content for call in researcher.calls)
    assert "ORIGINAL-Q" in round1
    assert "GAP-A" in round2 and "ORIGINAL-Q" not in round2
    assert result["research_iterations"] == 2
    assert [c.sufficient for c in result["critique_history"]] == [False, True]
    assert result["finalReport"] == "REPORT"
