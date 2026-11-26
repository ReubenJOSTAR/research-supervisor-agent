# CLAUDE.md — research-supervisor-agent

Read this file and `PROGRESS.md` at the start of every session. Then read `UPGRADE_PROMPT.md` for the full spec of the phase you're about to work on.

## What this project is
A LangGraph multi-agent research system exposed through FastAPI. A user sends a topic; the system plans research questions, searches the web (Tavily), critiques its findings in a reflection loop, and writes a structured, cited report. It is deployed on Railway from Docker and is a portfolio anchor project, so code clarity and the README matter as much as features.

## Stack
Python 3.11 · LangGraph · LangChain (langchain-openai) · OpenAI gpt-4o-mini · Tavily · FastAPI + SSE · Pydantic v2 · LangSmith (tracing + evals) · Postgres (checkpointer, Phase 8+) · Docker · Railway · GitHub Actions (Phase 10+)

## Layout (current — update when it changes)
```
src/
  main.py               FastAPI app, endpoints, SSE streaming
  config/settings.py    env vars and tunables
  graph/state.py        GraphState
  graph/workflow.py     graph assembly
  agents/               supervisor, planner, researcher, extractor, critic, writer
  schemas/              Pydantic models (Finding, Critique)
  tools/                search_web (Tavily), ToolNode
  evaluation/           eval.py (LangSmith) + research_agent_evals.jsonl
tests/                  (created in Phase 2)
```
Code runs from `src/` (`cd src && uvicorn main:app --reload`); imports are relative to `src/` (e.g. `from agents.critic import critic`). Tests must set this up via `pythonpath = src` in pytest config.

## How to work
- **One phase per session.** Don't start the next phase in the same session unless PROGRESS.md says otherwise. Token budget is limited.
- Branch: `upgrade/v2`. One commit per phase (small fix-up commits within a phase are fine).
- Run `pytest` before every commit. Never commit with failing tests.
- **Unit tests never call real LLMs or Tavily.** Use fakes/mocks. Real calls only in `evaluation/` and the optional end-to-end check.
- Keep it simple. Prefer the smallest change that meets the spec. No new abstractions, frameworks, or layers unless the phase requires them.
- Ambiguity: pick the simplest reasonable option, note it in the commit message and in PROGRESS.md under "Decisions", and continue.
- Every new env var goes in `settings.py`, `.env.example`, and the README env table. Never commit secrets or `.env`.
- Don't modify the Dockerfile/Railway setup beyond what a phase strictly requires; the image must still build and start.
- At the end of every session: update PROGRESS.md (status, decisions, blockers, next step).

## Architecture rules (keep these true)
- The supervisor is deterministic: plain Python routing, no LLM.
- Every node that returns `Command` has a typed return (`Command[Literal[...]]`).
- Anything crossing a node boundary is a Pydantic model or a typed state field.
- List fields that accumulate across rounds/branches use reducers (`add_messages`, `operator.add`).
- A failing research branch or tool call must never crash the whole run.
- API errors never leak stack traces or raw exception text to clients.

## Feature breakdown and required tests

| Phase | Feature | Required tests (automated, I run them) | Manual check (Reuben runs) |
|---|---|---|---|
| 1 | Bug fixes: stale critique, reducers, no-tool-call loop, iteration semantics, structured eval judge, cleanup, typed Commands | Covered by Phase 2 tests; at minimum `python -c "from graph.workflow import graph"` compiles | One `/research` call returns a report; iterations ≥ 1 |
| 2 | Settings + shared LLM factory + pinned deps + test suite | Supervisor routing: every branch from fake state. Reducers: findings accumulate across 2 updates | `pytest` passes locally |
| 3 | Critic returns scores + gaps; later rounds research only gaps; critique_history | Critique validator: `sufficient` inconsistent with scores is rejected. Supervisor routes gaps (not questions) on round ≥ 2 | Stream a query; critic events show scores and gaps |
| 4 | Parallel research via `Send` (map-reduce) | Fan-out creates N branches for N questions (mocked LLM + search). One branch raising doesn't fail the run; findings from other branches survive | Stream a query; see multiple research_task events in parallel |
| 5 | Finding IDs, dedupe, inline `[n]` citations, citation evaluator | Dedupe by URL+text. Heuristic citation evaluator: valid/invalid `[n]`, paragraph coverage | Report has inline citations that match Sources |
| 6 | Async nodes/endpoints, token streaming | SSE generator emits `node`, `token`, `done` event types in order (mocked graph) | Writer output streams token-by-token in curl |
| 7 | LangSmith tracing + per-node tokens/cost/latency | Metrics aggregation math from fake usage data. App starts with LangSmith vars unset | `metrics` in response looks sane; trace visible in LangSmith |
| 8 | Postgres checkpointer (MemorySaver fallback), thread_id, interrupt after planner, resume/get endpoints | Interrupt → resume with edited questions (MemorySaver, mocked LLM). `approve_plan=false` runs straight through | Approval flow works end to end via curl |
| 9 | API key auth, rate limit, input validation, timeout, safe errors | **Security tests:** missing/wrong key → 401; /health open; query too short/long → 422; rate limit → 429; timeout → 504; error responses contain no stack trace/exception text; API_KEY unset → check skipped with warning | Curl without key is rejected on Railway |
| 10 | CI: pytest on push/PR; eval smoke subset on PRs with thresholds | Workflow YAML is valid; `eval.py --subset 2` parses args and imports without side effects | First PR shows both jobs; eval job skips cleanly without secrets |
| 11 | README rewrite (Mermaid diagram, endpoints, env vars, design decisions) | — | README matches the code; clone URL correct |

## Guardrails learned
Add a line here whenever a session goes wrong, so it doesn't happen again.
- (none yet)
