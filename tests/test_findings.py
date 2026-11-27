"""Phase 5: finding ids and dedupe by source URL + finding text (the `findings` reducer)."""
from schemas.finding import Finding, FindingContent, add_findings


def fc(text, url="https://a.example/page", evidence="e"):
    return FindingContent(finding=text, source=url, evidence=evidence)


def test_new_findings_get_sequential_ids():
    merged = add_findings([], [fc("one"), fc("two")])
    assert [(f.id, f.finding) for f in merged] == [(1, "one"), (2, "two")]
    assert all(isinstance(f, Finding) for f in merged)


def test_same_url_and_text_is_a_duplicate():
    merged = add_findings([], [fc("Solar grew 20%"), fc("Solar grew 20%", evidence="other")])
    assert [f.finding for f in merged] == ["Solar grew 20%"]


def test_duplicate_ignores_case_whitespace_and_trailing_slash():
    merged = add_findings([], [fc("Solar grew 20%"), fc("  solar  GREW 20% ", url="HTTPS://A.example/page/")])
    assert len(merged) == 1


def test_same_text_from_another_url_is_kept():
    merged = add_findings([], [fc("fact"), fc("fact", url="https://b.example")])
    assert [f.id for f in merged] == [1, 2]


def test_same_url_different_text_is_kept():
    merged = add_findings([], [fc("fact one"), fc("fact two")])
    assert len(merged) == 2


def test_ids_are_stable_across_rounds_and_duplicates_are_dropped():
    round1 = add_findings([], [fc("a"), fc("b")])
    round2 = add_findings(round1, [fc("b"), fc("c")])  # "b" repeats from round 1
    assert round2[:2] == round1  # earlier ids unchanged
    assert [(f.id, f.finding) for f in round2] == [(1, "a"), (2, "b"), (3, "c")]


def test_dedupe_through_the_graph_reducer():
    from langgraph.graph import END, START, StateGraph
    from graph.state import GraphState

    builder = StateGraph(GraphState)
    builder.add_node("one", lambda s: {"findings": [fc("x"), fc("x")]})
    builder.add_node("two", lambda s: {"findings": [fc("x"), fc("y")]})
    builder.add_edge(START, "one")
    builder.add_edge("one", "two")
    builder.add_edge("two", END)

    result = builder.compile().invoke({"query": "q", "findings": []})

    assert [(f.id, f.finding) for f in result["findings"]] == [(1, "x"), (2, "y")]
