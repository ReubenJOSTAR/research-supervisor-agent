"""List fields in GraphState accumulate across updates instead of being overwritten."""
from langgraph.graph import END, START, StateGraph

from graph.state import GraphState
from schemas.finding import Finding

F1 = Finding(finding="a", source="https://a.example", evidence="ea")
F2 = Finding(finding="b", source="https://b.example", evidence="eb")


def _two_step_graph(first: dict, second: dict):
    builder = StateGraph(GraphState)
    builder.add_node("one", lambda state: first)
    builder.add_node("two", lambda state: second)
    builder.add_edge(START, "one")
    builder.add_edge("one", "two")
    builder.add_edge("two", END)
    return builder.compile()


def test_findings_accumulate_across_two_updates():
    graph = _two_step_graph({"findings": [F1]}, {"findings": [F2]})
    result = graph.invoke({"query": "x", "findings": []})
    assert result["findings"] == [F1, F2]


def test_non_reducer_field_is_overwritten():
    graph = _two_step_graph({"research_iterations": 1}, {"research_iterations": 2})
    result = graph.invoke({"query": "x"})
    assert result["research_iterations"] == 2


def test_critique_history_accumulates_across_two_updates():
    from schemas.critique import Critique

    scores = {"coverage": 0.2, "evidence_quality": 0.2, "source_diversity": 0.2, "completeness": 0.2}
    c1 = Critique(sufficient=False, scores=scores, gaps=["g1"], critique="r1")
    c2 = Critique(sufficient=False, scores=scores, gaps=["g2"], critique="r2")
    graph = _two_step_graph({"critique_history": [c1]}, {"critique_history": [c2]})
    result = graph.invoke({"query": "x", "critique_history": []})
    assert result["critique_history"] == [c1, c2]
