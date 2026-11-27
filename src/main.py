import json
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from graph.workflow import graph

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Research Agent API",
    description="A multi-agent research system powered by LangGraph",
    version="1.0.0"
)


# ============================================================
# Request / Response schemas
# ============================================================

class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    query: str
    report: str
    questions: list[str]
    research_iterations: int


def initial_state(query: str) -> dict:
    return {
        "query": query,
        "questions": [],
        "findings": [],
        "critiques": None,
        "critique_history": [],
        "research_iterations": 0,
        "finalReport": ""
    }


# ============================================================
# Health check
# ============================================================

@app.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================
# Standard endpoint — waits for full report
# ============================================================

@app.post("/research", response_model=ResearchResponse)
async def run_research(request: ResearchRequest):
    try:
        result = await graph.ainvoke(initial_state(request.query))
    except Exception:
        # Log the details; never send exception text to the client.
        logger.exception("Research run failed")
        raise HTTPException(status_code=500, detail="Research failed. Please try again.")

    return ResearchResponse(
        query=request.query,
        report=result.get("finalReport") or "No report generated",
        questions=result.get("questions", []),
        research_iterations=result.get("research_iterations", 0)
    )


# ============================================================
# Streaming endpoint — node updates + writer tokens as SSE
# ============================================================

# Nodes whose LLM tokens are streamed to the client.
TOKEN_NODES = {"writer"}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def research_events(query: str):
    """SSE events for one research run, in the order they happen:

    - {"type": "node", "node": ..., "data": {...}}  each node's state update
    - {"type": "token", "content": ...}             each writer token
    - {"type": "done", "report", "questions", "research_iterations"}  once, last
    - {"type": "error", "message": ...}             instead of done if the run fails
    """
    final = {"report": "", "questions": [], "research_iterations": 0}
    try:
        async for mode, chunk in graph.astream(
            initial_state(query), stream_mode=["updates", "messages"]
        ):
            if mode == "messages":
                message, metadata = chunk
                if metadata.get("langgraph_node") in TOKEN_NODES and message.content:
                    yield _sse({"type": "token", "content": message.content})
                continue

            # mode == "updates": {node_name: update}; parallel branches arrive one by one.
            for node, update in chunk.items():
                if isinstance(update, dict):
                    if "finalReport" in update:
                        final["report"] = update["finalReport"]
                    for key in ("questions", "research_iterations"):
                        if key in update:
                            final[key] = update[key]
                yield _sse({"type": "node", "node": node, "data": _serialize(update)})

        yield _sse({"type": "done", **final})

    except Exception:
        logger.exception("Research stream failed")
        yield _sse({"type": "error", "message": "Research failed. Please try again."})


@app.post("/research/stream")
async def stream_research(request: ResearchRequest):
    return StreamingResponse(
        research_events(request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"   # important for Railway/nginx proxies
        }
    )


# ============================================================
# Helpers
# ============================================================

def _serialize(obj):
    """
    Safely convert state updates to JSON-serializable format.
    Pydantic models, LangChain messages, and custom objects
    all need special handling.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "model_dump"):      # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, "content"):         # LangChain messages
        return {"role": obj.__class__.__name__, "content": obj.content}
    return str(obj)
