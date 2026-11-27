"""Phase 6: SSE events (node, token, done) and async endpoints. No real LLM or search calls."""
import json

import httpx
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk

import agents.critic as critic_module
import agents.planner as planner_module
import agents.research_task as rt
import agents.writer as writer_module
import main
from agents.planner import ResearchPlan
from schemas.critique import CritiqueAssessment
from schemas.finding import Finding

HIGH = {"coverage": 0.9, "evidence_quality": 0.9, "source_diversity": 0.9, "completeness": 0.9}


class FakeGraph:
    """Replays `(mode, chunk)` pairs like `graph.astream(..., stream_mode=[...])`."""

    def __init__(self, chunks=(), error=None, result=None):
        self.chunks, self.error, self.result = list(chunks), error, result
        self.stream_modes = None

    async def astream(self, state, stream_mode):
        self.stream_modes = stream_mode
        for chunk in self.chunks:
            yield chunk
        if self.error:
            raise self.error

    async def ainvoke(self, state):
        if self.error:
            raise self.error
        return self.result


def writer_token(text, node="writer"):
    return ("messages", (AIMessageChunk(content=text), {"langgraph_node": node}))


async def collect(query="topic"):
    return [json.loads(e.removeprefix("data: ")) async for e in main.research_events(query)]


async def test_sse_emits_node_token_done_in_order(monkeypatch):
    fake = FakeGraph([
        ("updates", {"supervisor": None}),
        ("updates", {"planner": {"questions": ["q1"]}}),
        ("updates", {"supervisor": {"research_iterations": 1, "research_queue": ["q1"]}}),
        ("updates", {"research_task": {"findings": [Finding(id=1, finding="f", source="s", evidence="e")]}}),
        ("messages", (AIMessageChunk(content=""), {"langgraph_node": "critic"})),
        writer_token("Hello"),
        writer_token(" world"),
        ("updates", {"writer": {"finalReport": "Hello world\n\n# Sources"}}),
    ])
    monkeypatch.setattr(main, "graph", fake)

    events = await collect()

    assert [e["type"] for e in events] == ["node"] * 4 + ["token", "token", "node", "done"]
    assert [e["node"] for e in events if e["type"] == "node"] == [
        "supervisor", "planner", "supervisor", "research_task", "writer"]
    assert [e["content"] for e in events if e["type"] == "token"] == ["Hello", " world"]
    assert events[3]["data"]["findings"][0]["id"] == 1  # Pydantic models serialised
    assert events[-1] == {"type": "done", "report": "Hello world\n\n# Sources",
                          "questions": ["q1"], "research_iterations": 1}
    assert fake.stream_modes == ["updates", "messages"]


async def test_tokens_from_other_nodes_are_not_streamed(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph([writer_token("x", node="planner"),
                                                  writer_token("y", node="critic")]))
    assert [e["type"] for e in await collect()] == ["done"]


async def test_stream_error_is_generic_and_last(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph([writer_token("Hi")],
                                                 error=RuntimeError("secret db password in traceback")))
    events = await collect()
    assert [e["type"] for e in events] == ["token", "error"]
    assert "secret" not in json.dumps(events) and "Traceback" not in json.dumps(events)


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")


async def test_stream_endpoint_returns_sse(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph([writer_token("Hi")]))
    async with _client() as client:
        r = await client.post("/research/stream", json={"query": "topic"})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    assert [json.loads(l[6:])["type"] for l in r.text.split("\n\n") if l] == ["token", "done"]


async def test_research_endpoint_is_async(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph(result={
        "finalReport": "R", "questions": ["q"], "research_iterations": 2}))
    async with _client() as client:
        r = await client.post("/research", json={"query": "topic"})
    assert r.status_code == 200
    assert r.json() == {"query": "topic", "report": "R", "questions": ["q"], "research_iterations": 2}


async def test_research_endpoint_error_hides_exception_text(monkeypatch):
    monkeypatch.setattr(main, "graph", FakeGraph(error=ValueError("internal detail xyz")))
    async with _client() as client:
        r = await client.post("/research", json={"query": "topic"})
    assert r.status_code == 500
    assert "xyz" not in r.text and "ValueError" not in r.text


class Fake:
    def __init__(self, output):
        self.output = output

    async def ainvoke(self, arg):
        return self.output


async def test_real_graph_streams_writer_tokens(monkeypatch):
    """Through the compiled graph: the writer's LLM tokens arrive as token events before done."""
    monkeypatch.setattr(planner_module, "planner_llm", Fake(ResearchPlan(questions=["q1"])))
    monkeypatch.setattr(rt, "research_agent", Fake(AIMessage(content="no searches")))
    monkeypatch.setattr(critic_module, "judge", Fake(CritiqueAssessment(scores=HIGH, gaps=[], critique="ok")))
    monkeypatch.setattr(writer_module, "llm",
                        GenericFakeChatModel(messages=iter([AIMessage(content="Solar is growing fast")])))

    events = await collect()

    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert len(tokens) > 1 and "".join(tokens) == "Solar is growing fast"
    assert events[-1]["type"] == "done"
    assert events[-1]["report"].startswith("Solar is growing fast")
    assert events[-1]["questions"] == ["q1"] and events[-1]["research_iterations"] == 1
    last_token = max(i for i, e in enumerate(events) if e["type"] == "token")
    writer_node = next(i for i, e in enumerate(events) if e.get("node") == "writer")
    assert last_token < writer_node
