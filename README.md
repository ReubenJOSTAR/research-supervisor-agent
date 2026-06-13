Research Supervisor Agent
A production multi-agent research system built with LangGraph. Give it a topic — it plans, searches the web, critiques its own findings, and writes a structured research report.
Live API: `https://research-supervisor-agent-production.up.railway.app/docs`
---
How It Works
The system uses a Supervisor architecture with 5 specialized agents that collaborate through a self-correcting reflection loop.
```
User Query
    ↓
Supervisor  ←─────────────────────────────┐
    ↓                                      │
Planner → generates 5 research questions   │
    ↓                                      │
Researcher → searches web with Tavily      │
    ↓                                      │
Critic → evaluates findings quality        │
    ↓                                      │
sufficient? ──── No ──→ back to Researcher─┘
    ↓ Yes
Writer → produces structured report
    ↓
Final Report
```
The critic evaluates coverage, evidence quality, source diversity, and completeness. If findings are insufficient, the supervisor loops back to the researcher — up to 3 iterations — before forcing the writer to synthesize what it has.
---
Agents
Agent	Role
Supervisor	Routes between agents based on state. No LLM — pure rule-based logic.
Planner	Generates 5 structured research questions covering fundamentals, current state, challenges, opportunities, and outlook.
Researcher	Searches the web using Tavily and extracts structured findings in a single node.
Critic	Evaluates research quality and returns a `sufficient: bool` signal to control the loop.
Writer	Synthesizes all findings into a structured report with executive summary, analysis, and sources.
---
Tech Stack
Layer	Technology
Agent framework	LangGraph
LLM	OpenAI GPT-4o-mini
Web search	Tavily API
API server	FastAPI
Streaming	Server-Sent Events (SSE)
Validation	Pydantic v2
Containerization	Docker
Deployment	Railway
---
API Endpoints
Health Check
```bash
GET /health
```
```json
{"status": "ok"}
```
---
Run Research (standard)
```bash
POST /research
Content-Type: application/json

{"query": "What is LangGraph?"}
```
Response:
```json
{
  "query": "What is LangGraph?",
  "report": "# Executive Summary\n\n...",
  "questions": [
    "What are the fundamental principles of LangGraph?",
    "..."
  ],
  "iterations": 2
}
```
---
Run Research (streaming)
```bash
POST /research/stream
Content-Type: application/json

{"query": "What is LangGraph?"}
```
Returns Server-Sent Events — one event per agent node as it completes:
```
data: {"node": "planner", "data": {"questions": [...]}}

data: {"node": "researcher", "data": {"findings": [...]}}

data: {"node": "critic", "data": {"critiques": {...}}}

data: {"node": "writer", "data": {"finalReport": "..."}}

data: [DONE]
```
---
Run Locally
Prerequisites: Python 3.11+, Docker, OpenAI API key, Tavily API key.
Without Docker
```bash
git clone https://github.com/your-username/research-supervisor-agent
cd research-supervisor-agent

pip install -r requirements.txt

# Create .env in project root
echo "OPENAI_API_KEY=sk-proj-..." >> .env
echo "TAVILY_API_KEY=tvly-..." >> .env

cd src
uvicorn main:app --reload --port 8000
```
With Docker
```bash
git clone https://github.com/your-username/research-supervisor-agent
cd research-supervisor-agent

docker build -t research-agent .

docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-proj-... \
  -e TAVILY_API_KEY=tvly-... \
  research-agent
```
Test it:
```bash
# Health check
curl http://localhost:8000/health

# Research query
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LangGraph?"}'

# Streaming
curl -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is LangGraph?"}'
```
---
Project Structure
```
research-supervisor-agent/
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── src/
    ├── main.py                 # FastAPI app — endpoints and streaming
    ├── config/
    │   └── settings.py         # environment variable loading
    ├── graph/
    │   ├── state.py            # GraphState TypedDict
    │   └── workflow.py         # graph assembly and compilation
    ├── agents/
    │   ├── supervisor.py       # rule-based router
    │   ├── planner.py          # question generation
    │   ├── researcher.py       # web search + findings extraction
    │   ├── critic.py           # quality evaluation
    │   └── writer.py           # report synthesis
    ├── schemas/
    │   ├── critique.py         # Critique pydantic model
    │   ├── finding.py          # Finding pydantic model
    │   └── routing.py          # RouteDecision pydantic model
    └── tools/
        └── search.py           # Tavily search tool
```
---
Key Design Decisions
Rule-based supervisor over LLM routing. The supervisor uses deterministic if/else logic rather than an LLM to decide routing. This eliminates a class of hallucination bugs where the router sends execution to a nonexistent node, and reduces latency and cost per iteration.
Combined search and extraction in one node. The researcher handles both tool calling and structured extraction internally — two sequential LLM calls in one node. This keeps the graph clean and avoids an extra extraction node hop while maintaining structured `Finding` output.
Pydantic schemas for all inter-agent communication. Every agent output that crosses a node boundary is a typed Pydantic model. This catches malformed outputs at the boundary rather than letting bad data propagate through multiple nodes before failing.
`sufficient` flag as loop control signal. The critic returns a `Critique` model with a boolean `sufficient` field. The supervisor reads this flag directly rather than parsing free-text critique — making the loop control deterministic and testable.
---
Environment Variables
Variable	Description
`OPENAI_API_KEY`	OpenAI API key — used by all agents
`TAVILY_API_KEY`	Tavily API key — used by the researcher for web search
---
Planned Improvements
[ ] Wikipedia and arXiv tool integration
[ ] LangSmith tracing for full execution observability
[ ] Long-term memory with vector store for cross-session context
[ ] PostgreSQL checkpointing for persistent agent state
[ ] Frontend UI for real-time streaming visualization
---
Author
Reuben Joseph — Full Stack Developer & AI Engineer  
LinkedIn · GitHub · reubenjonathan.joseph@gmail.com