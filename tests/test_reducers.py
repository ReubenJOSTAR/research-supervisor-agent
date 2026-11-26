"""List fields in GraphState accumulate across updates instead of being overwritten."""
from langchain_core.messages import AIMessage, HumanMessage
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


def test_messages_accumulate_across_two_updates():
    graph = _two_step_graph(
        {"messages": [HumanMessage(content="hi", id="1")]},
        {"messages": [AIMessage(content="hello", id="2")]},
    )
    result = graph.invoke({"query": "x", "messages": []})
    assert [m.content for m in result["messages"]] == ["hi", "hello"]


def test_non_reducer_field_is_overwritten():
    graph = _two_step_graph({"research_iterations": 1}, {"research_iterations": 2})
    result = graph.invoke({"query": "x"})
    assert result["research_iterations"] == 2
