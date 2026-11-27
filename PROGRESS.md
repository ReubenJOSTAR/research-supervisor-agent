# PROGRESS.md — research-supervisor-agent v2 upgrade

New session? Read `CLAUDE.md`, then this file, then the spec for the next phase in `UPGRADE_PROMPT.md`. Update this file before ending the session.

**Branch:** `upgrade/v2` is the integration branch. Each phase is developed on a session branch and merged into `upgrade/v2` via PR; `upgrade/v2` goes to `main` once all phases are done.
**Current phase:** 5
**Last updated:** 2026-11-27 — Phase 4 done

## Status

| Phase | Feature | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | Bug fixes | ✅ Done | b450e3c | PR #1 → `upgrade/v2`. Verified with a mocked end-to-end run; no pytest suite yet (Phase 2) |
| 2 | Config + tests | ✅ Done | 011758e | PR #2 (merged) → `upgrade/v2` from `claude/magical-dijkstra-nqe5vb`. 14 tests pass on 3.11 and 3.13 |
| 3 | Critic with gaps + scores | ✅ Done | 4457894 | PR #3 → `upgrade/v2`. 25 tests pass (3.11 + 3.13). Done in the same session as Phase 2 at Reuben's request |
| 4 | Parallel research (Send) | ✅ Done | 51383ff | PR #5 → `upgrade/v2` from `claude/next-upgrade-phase-k9t1jy`. 30 tests pass (3.13) |
| 5 | Grounded citations | ⬜ Not started | | |
| 6 | Async + token streaming | ⬜ Not started | | |
| 7 | Observability + cost | ⬜ Not started | | |
| 8 | Checkpointing + human approval | ⬜ Not started | | |
| 9 | API hardening | ⬜ Not started | | |
| 10 | Evals in CI | ⬜ Not started | | |
| 11 | README | ⬜ Not started | | |

Status key: ⬜ Not started · 🟡 In progress · ✅ Done · 🔴 Blocked · ↩️ Rolled back

## Phase 1 checklist
- [x] Clear `critiques` on loop-back so the critic re-runs each round
- [x] Reducers: `messages` → `add_messages`, `findings` → `operator.add`
- [x] No-tool-call path counts as an iteration (no infinite loop)
- [x] `research_iterations` = rounds completed; `depth_evaluator` updated
- [x] README uses `research_iterations` (not `iterations`)
- [x] `quality_evaluator` uses structured output instead of `json.loads`
- [x] Remove unused supervisor LLM, `RouteDecision`, empty `wikipedia.py` / `arxiv.py`, duplicate imports
- [x] Typed `Command[Literal[...]]` returns on every node

## Manual checks (Reuben)
| Phase | Check | Result |
|---|---|---|
| 1 | One `/research` call returns a report; `research_iterations` ≥ 1 | ⬜ pending |
| 2 | `pip install -r requirements-dev.txt && pytest` passes locally; `docker build .` succeeds | ⬜ pending |
| 3 | Stream a query; critic events show scores and gaps; round 2 searches the gaps | ⬜ pending (Reuben chose to defer manual checks) |
| 4 | Stream a query; several `research_task` events arrive per round (one per question/gap) | ⬜ pending |

## Decisions
Choices made where the spec was ambiguous (phase — decision — why).
- 1 — Created `upgrade/v2` from `main` (Reuben's request). All upgrade PRs target `upgrade/v2`, never `main`. Phase 1 was done on `claude/claude-md-upgrade-prompt-fctm2r` and goes in via PR #1.
- 1 — The extractor increments `research_iterations` — every research pass (tool calls or not) ends there, so one place counts rounds. Researcher with no tool calls routes straight to the extractor.
- 1 — `MAX_RESEARCH_LOOPS=3` now caps total rounds at 3 (old code allowed up to 4 because the first round wasn't counted).
- 1 — Extractor reads only the trailing ToolMessages (current round) — with `add_messages` accumulating, reading all of them would re-extract earlier rounds into duplicate findings.
- 1 — Supervisor no longer checks `messages`/`findings` to decide routing; it uses `research_iterations == 0` for "not researched yet". An empty round still goes to the critic, which can ask for more.
- 1 — Added CLAUDE.md, PROGRESS.md, UPGRADE_PROMPT.md to the repo root so future sessions can read them.
- 2 — Phase branch is `claude/magical-dijkstra-nqe5vb` (session branch), branched from `upgrade/v2`, PR into `upgrade/v2`.
- 2 — LLM factory lives in `src/config/llm.py` (`get_llm(temperature=None)`); modules reference `settings.X` via the module so tests can monkeypatch.
- 2 — `LLM_TEMPERATURE` defaults to 0 (previously OpenAI's default of 1) for reproducible runs/evals.
- 2 — `MODEL_PRICES` is one JSON env var (USD per 1M tokens); defaults cover gpt-4o-mini and gpt-4o. Used from Phase 7.
- 2 — `MAX_TOOL_CALLS_PER_QUESTION` (default 2): stated in the researcher prompt and hard-capped at `max × len(questions)` tool calls per round until Phase 4 makes it per-branch.
- 2 — `settings.py` still raises at import without API keys (fail fast in prod); `tests/conftest.py` sets dummy keys.
- 2 — Pinned to versions installed today; verified install + tests + `import main` on Python 3.11 (Docker daemon unavailable, so no image build). Added `langchain-core` and `langsmith` pins explicitly (both imported directly).
- 3 — Phase 3 was built in the same session as Phase 2 because Reuben asked to continue without doing the manual checks first. Manual checks for 1–3 are still pending.
- 3 — The critic LLM returns `CritiqueAssessment` (scores, gaps, critique) and `sufficient` is derived in code (`Critique.from_assessment`). The `Critique` validator still rejects inconsistent values, but an inconsistent LLM answer can't crash the run.
- 3 — Sufficiency threshold 0.7 is the constant `SUFFICIENT_SCORE` in `schemas/critique.py`, not an env var.
- 3 — New state field `research_queue` holds what the researcher works on this round: the planner sets it to its questions (the planner goes straight to the researcher), and the supervisor sets it to the gaps on loop-back. Phase 4 can fan out one `Send` per queue item.
- 3 — Insufficient critique with no gaps → writer (there is nothing to research, and the original questions must not be repeated).
- 4 — Phase branch is `claude/next-upgrade-phase-k9t1jy` (session branch), branched from `upgrade/v2` after PR #3 merged.
- 4 — The supervisor does the fan-out: `Command(goto=[Send("research_task", {"topic", "task"}) ...])`. The planner now returns to the supervisor instead of going straight to research. `research_task` has a static edge back to the supervisor, which runs once after all branches finish and routes to the critic.
- 4 — `research_iterations` is incremented by the supervisor when it dispatches a round (parallel branches can't all write a non-reducer field). By the time the supervisor runs again it equals rounds completed, so `MAX_RESEARCH_LOOPS` semantics are unchanged.
- 4 — Each branch makes one LLM call with `search_web` bound, runs at most `MAX_TOOL_CALLS_PER_QUESTION` of its tool calls directly (no ToolNode), then one structured extraction call. No tool calls → no findings.
- 4 — `search_web` now raises on Tavily errors (it used to return a "Search failed" string that the extractor would have parsed). `research_task` catches any exception, logs a warning, and returns `{"findings": []}` for that branch.
- 4 — Removed the `messages` state field (and its reducer test), `researcher.py`, `extractor.py`, `tools/tool_node.py`; nothing reads them any more. `research_queue` is kept so stream events show what each round researched.
- 4 — Shared test fakes live in `tests/fakes.py` (prompt-aware, since branch order is nondeterministic).

## Blockers / needs Reuben
- [ ] Railway: add a Postgres instance and set `DATABASE_URL` (needed by Phase 8 in production)
- [ ] Railway: set `API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`
- [ ] GitHub secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY` (Phase 10 eval job)

## Rollbacks / incidents
What went wrong, what was rolled back, which guardrail was added to CLAUDE.md.
- (none)

## Notes for later phases
- Phase 5: findings now arrive from parallel branches in nondeterministic order within a round — assign IDs after dedupe (e.g. in the writer or when merging), not inside branches. Expect duplicates across branches.
- Phase 6: `research_task` is sync; make it async and use `ainvoke` for the agent, search and extractor.
- README still describes the old researcher/extractor nodes and a `researcher` stream event (Phase 11 rewrite).
- Scores use `Field(ge=0, le=1)`; if OpenAI structured output ever rejects `minimum`/`maximum` in the schema, drop the bounds from `CritiqueAssessment` and clamp instead.
- `config/settings.py` raises at import when API keys are unset; `tests/conftest.py` sets dummy keys. Agents build their LLMs at import, so tests patch module-level objects (e.g. `agents.researcher.research_agent`).
- `evaluation/eval.py` creates a LangSmith `Client()` at import (Phase 10 fixes this).
- README "Key design decisions" still describes a combined researcher+extractor node (Phase 11 rewrite).

## Next step
Reuben: review and merge the Phase 4 PR into `upgrade/v2`; run the pending manual checks (Phases 1–4) when convenient. Then Phase 5 in a new session on a branch off `upgrade/v2`: grounded citations (Finding IDs, dedupe by URL+text, inline `[n]` citations, `citation_evaluator`). Tests: dedupe; heuristic citation evaluator (valid/invalid `[n]`, paragraph coverage).
