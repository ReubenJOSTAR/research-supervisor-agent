from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json

load_dotenv()

from graph.workflow import graph

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


# ============================================================
# Health check
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# Standard endpoint — waits for full report
# ============================================================

@app.post("/research", response_model=ResearchResponse)
def run_research(request: ResearchRequest):
    try:
        result = graph.invoke({
            "query": request.query,
            "messages": [],
            "questions": [],
            "findings": [],
            "critiques": None,
            "research_iterations": 0,
            "finalReport": ""
        })

        return ResearchResponse(
            query=request.query,
            report=result.get("finalReport", "No report generated"),
            questions=result.get("questions", []),
            research_iterations=result.get("research_iterations", 0)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Streaming endpoint — yields each node update as it happens
# ============================================================

@app.post("/research/stream")
def stream_research(request: ResearchRequest):

    def generate():
        try:
            for chunk in graph.stream(
                {
                    "query": request.query,
                    "messages": [],
                    "questions": [],
                    "findings": [],
                    "critiques": None,
                    "research_iterations": 0,
                    "finalReport": ""
                },
                stream_mode="updates"   # yields state updates per node
            ):
                # chunk = {"node_name": {state updates}}
                node_name = list(chunk.keys())[0]
                update = chunk[node_name]

                event = {
                    "node": node_name,
                    "data": _serialize(update)
                }

                # Server-Sent Events format
                yield f"data: {json.dumps(event)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
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
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "model_dump"):      # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):            # Pydantic v1
        return obj.dict()
    if hasattr(obj, "content"):         # LangChain messages
        return {"role": obj.__class__.__name__, "content": obj.content}
    return str(obj)