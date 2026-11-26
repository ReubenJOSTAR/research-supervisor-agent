# Upgrade spec — research-supervisor-agent v2

This is the full spec. `CLAUDE.md` holds the working rules and the required tests for each phase. `PROGRESS.md` tracks status.

## Kickoff prompt (paste into Claude Code at the start of each session)

```
Read CLAUDE.md, PROGRESS.md and UPGRADE_PROMPT.md. Work on the next unfinished phase in
PROGRESS.md, and only that phase. Follow the rules in CLAUDE.md, write the required tests
for this phase listed there, run pytest, commit, then update PROGRESS.md (status, commit
hash, decisions, blockers, next step). Stop and summarise what you did and what I should
check manually.
```

---

You're working on my LangGraph project research-supervisor-agent (FastAPI, deployed on Railway).
Read the whole repo before you change anything.

## Ground rules
- Work on a branch called `upgrade/v2`. Commit once per phase below, with a clear message.
- Run `pytest` before every commit. Never commit with failing tests.
- Unit tests must never call real LLMs or Tavily. Use fakes or mocks.
- Keep the Dockerfile and Railway setup working. Add any new env var to
  settings.py, the README and a new `.env.example`. Never commit secrets.
- If something is ambiguous, pick the simplest option that works, note it in the commit
  message and in PROGRESS.md, and keep going. Don't stop to ask.
- At the end, give me a summary: what changed, the new env vars, and anything I need
  to set up by hand (GitHub secrets, a Railway Postgres instance).

## Phase 1: Fix existing bugs
1. Stale critique: when the supervisor loops back to research, clear `critiques` so the
   critic runs again every round. Right now it only runs once.
2. Reducers: `messages` uses `Annotated[list, add_messages]` and `findings` uses
   `Annotated[list[Finding], operator.add]`, so findings add up across rounds instead of
   being overwritten.
3. Infinite loop: if the researcher makes no tool calls, findings stay empty and the
   supervisor keeps routing back without counting an iteration, until it hits the recursion
   limit. Every pass through research must count as an iteration.
4. Iteration semantics: `research_iterations` means the number of research rounds
   completed (it's 1 after the first pass). Update `depth_evaluator` to match.
5. The API response field is `research_iterations` but the README shows `iterations`.
   Keep `research_iterations` and fix the README.
6. `quality_evaluator` calls json.loads on raw LLM text. Switch it to
   `with_structured_output` and a Pydantic model.
7. Cleanup: remove the unused LLM in supervisor.py, the unused RouteDecision schema and
   the empty tools/wikipedia.py and tools/arxiv.py. Remove duplicate imports everywhere.
8. Give every node that returns a Command a return type like `Command[Literal[...]]` so
   the compiled graph draws correctly.

## Phase 2: Config and tests (the safety net for everything after)
- Move the model name, temperature, MAX_RESEARCH_LOOPS, the number of questions, the max
  tool calls per question, and per-model token prices into settings.py, all overridable
  by env vars.
- Use one shared LLM factory instead of creating ChatOpenAI in each file.
- Pin every dependency in requirements.txt to the version you actually install. Add a
  requirements-dev.txt with pytest, pytest-asyncio and httpx.
- Add tests/ with unit tests for every branch of the supervisor's routing (built from fake
  state dicts) and for the reducers.

## Phase 3: A critic that names the gaps
- Change the Critique schema to: sufficient: bool, scores (coverage, evidence_quality,
  source_diversity, completeness, each 0–1), gaps: list[str] and critique: str.
- `sufficient` must be consistent with the scores. Validate this in the model
  (for example: every score ≥ 0.7 and no gaps).
- From round 2 on, research only the gaps, never the original questions again.
- Keep a `critique_history` list in state so every round's scores are kept.

## Phase 4: Research in parallel (map-reduce)
- Replace the researcher → tools → extractor chain with a fan-out using the Send API:
  - Round 1: one Send per planner question. Later rounds: one Send per critic gap.
  - Each branch runs a `research_task` node that takes its own query, calls the LLM with
    search_web bound (up to the configured max tool calls), runs the tools, and extracts
    Finding objects itself.
  - Branches merge through the findings reducer, then go to the critic.
- One failing branch (search error or LLM error) must not crash the run. It returns no
  findings and logs a warning.
- Unit-test the fan-out with a mocked LLM and a mocked search.

## Phase 5: Grounded citations
- Give every Finding a stable integer `id` and remove duplicates by source URL plus
  finding text.
- Give the writer a numbered list of findings. Every claim in Key Findings and Analysis
  must carry an inline citation like [3]. The Sources section lists each [n] with its URL.
  The writer must not use anything that isn't in the findings.
- Add `citation_evaluator` to eval.py:
  - A heuristic part: every [n] in the report exists in the findings, and the share of
    paragraphs with at least one citation.
  - A structured-output LLM judge that checks a sample of cited claims against their
    findings.
- Add a unit test for the heuristic part.

## Phase 6: Async and token streaming
- Make every node and both endpoints async (ainvoke / astream).
- In /research/stream, use stream_mode=["updates", "messages"]:
  - Node updates go out as `{"type":"node", ...}` events.
  - The writer's tokens go out as `{"type":"token","content":...}` events.
  - Finish with a `{"type":"done", ...}` event that includes the final metrics.
- Keep the SSE format and the X-Accel-Buffering header.

## Phase 7: Observability and cost
- Turn on LangSmith tracing through env vars (LANGSMITH_TRACING, LANGSMITH_API_KEY,
  LANGSMITH_PROJECT). The app must run fine when they aren't set.
- For every node, record input tokens, output tokens, cost in USD (from the price table)
  and latency in ms. Use usage metadata or a callback, whichever is cleaner.
- Return a `metrics` object from /research and in the stream's done event:
  { per_node: {...}, total_tokens, total_cost_usd, total_latency_ms }.
- Tag the LangSmith runs with the query and thread_id.

## Phase 8: Checkpointing and human approval
- Add AsyncPostgresSaver (langgraph-checkpoint-postgres) when DATABASE_URL is set.
  Otherwise fall back to MemorySaver so local runs and tests still work. Run setup() on
  startup through FastAPI's lifespan.
- Every run gets a thread_id (UUID).
- Add `interrupt()` after the planner so a user can review the questions.
- API:
  - `POST /research` with `{query, approve_plan: bool = false}`. When approve_plan is
    false, keep today's behaviour and run straight through (evals and the current
    /research flow depend on this). When it's true, return
    `{thread_id, status: "awaiting_approval", questions}`.
  - `POST /research/{thread_id}/resume` with `{questions?: list[str]}`: carries on with
    the edited or approved questions and returns the report.
  - `GET /research/{thread_id}`: returns the run's current state and status.
- Add tests for interrupt and resume using MemorySaver and mocked LLMs.

## Phase 9: Harden the API
- Require an `X-API-Key` header checked against the API_KEY env var. /health stays open.
  If API_KEY isn't set, skip the check (for local dev) and log a warning.
- Rate-limit each key or IP (slowapi is fine), with the limit in settings.
- Validate queries: 3–500 characters, whitespace trimmed.
- Put an overall timeout on each run (asyncio.wait_for, configurable). Return a 504 when
  it runs out.
- Never send stack traces or raw exception text to clients. Log them on the server and
  return a generic error with a request ID.
- Add API tests with httpx AsyncClient and a mocked graph. Include the security tests
  listed for Phase 9 in CLAUDE.md, and review the whole API for anything else worth
  hardening (report it, fix it only if it's small).

## Phase 10: Evals in CI
- Add .github/workflows/ci.yml:
  - On every push and PR: install dependencies and run pytest.
  - On PRs to main: a separate job runs eval.py on a 2-example smoke subset
    (`--subset 2` flag). It fails if the average structure, citation or quality score
    falls below thresholds in a small config file (start at 0.7). It skips cleanly when
    the OPENAI_API_KEY, TAVILY_API_KEY and LANGSMITH_API_KEY secrets are missing.
- Make eval.py importable without side effects (keep everything under `__main__`) and
  give it command-line arguments.

## Phase 11: Docs
- Rewrite the README so it matches the real system:
  - A new Mermaid graph diagram (supervisor, planner, interrupt, parallel research_task
    fan-out, critic with gaps, writer)
  - Updated agents table, endpoints with examples (approval flow and SSE event types),
    env vars table, project tree, how to run the tests and evals, a sample metrics output
  - A "Key design decisions" section covering: deterministic routing, map-reduce with
    Send, gap-targeted reflection, grounded citations, and checkpointing with
    human-in-the-loop.
- Fix the clone URL so it points to github.com/ReubenJOSTAR/research-supervisor-agent.
- Mark the finished roadmap items as done.

When you're finished, run the full test suite and one real end-to-end query locally if API
keys are present. Then give me the summary described in the ground rules.
