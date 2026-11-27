# PROGRESS.md — research-supervisor-agent v2 upgrade

New session? Read `CLAUDE.md`, then this file, then the spec for the next phase in `UPGRADE_PROMPT.md`. Update this file before ending the session.

**Branch:** `upgrade/v2` is the integration branch. Each phase is developed on a session branch and merged into `upgrade/v2` via PR; `upgrade/v2` goes to `main` once all phases are done.
**Current phase:** 6
**Last updated:** 2026-11-27 — Phase 5 done

## Status

| Phase | Feature | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | Bug fixes | ✅ Done | b450e3c | PR #1 → `upgrade/v2`. Verified with a mocked end-to-end run; no pytest suite yet (Phase 2) |
| 2 | Config + tests | ✅ Done | 011758e | PR #2 (merged) → `upgrade/v2` from `claude/magical-dijkstra-nqe5vb`. 14 tests pass on 3.11 and 3.13 |
| 3 | Critic with gaps + scores | ✅ Done | 4457894 | PR #3 → `upgrade/v2`. 25 tests pass (3.11 + 3.13). Done in the same session as Phase 2 at Reuben's request |
| 4 | Parallel research (Send) | ✅ Done | 6eb09a4 | PR #4 → `upgrade/v2` from `claude/sharp-euler-5o852p`. 31 tests pass (3.13) |
| 5 | Grounded citations | ✅ Done | f8db652 | PR #6 → `upgrade/v2` from `claude/next-upgrade-phase-k9t1jy`. 51 tests pass (3.13) |
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
| 5 | `/research` report has inline `[n]` citations; each matches an entry in Sources with the right URL | ⬜ pending |

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
- 4 — Phase branch is `claude/sharp-euler-5o852p` (session branch), branched from `upgrade/v2`, PR into `upgrade/v2`.
- 4 — The supervisor does the fan-out (`Command(goto=[Send("research_task", {"query": q}), ...])`) for both round 1 and gap rounds; the planner now returns to the supervisor. Branches join back at the supervisor via a static `research_task → supervisor` edge (runs once after all branches).
- 4 — The supervisor increments `research_iterations` when it fans a round out (no extra join node). Mid-round stream events show the new round number; the final value is the same as before.
- 4 — Each branch is a single LLM turn: up to `MAX_TOOL_CALLS_PER_QUESTION` tool calls (hard-capped), run sequentially inside the branch, then one structured extraction. No multi-turn tool loop.
- 4 — Any exception in a branch (LLM or search) → warning logged with traceback, `{"findings": []}`. `search_web` no longer swallows errors into a "Search failed" string, so search errors reach the branch handler instead of being "extracted".
- 4 — Removed `researcher.py`, `extractor.py`, `tools/tool_node.py` and the unused `messages` state field (and its reducer test); replaced `tests/test_workflow.py` with the graph tests in `tests/test_research_task.py`.
- 4 — Small fix outside spec: SSE `_serialize` turned ints into strings (`"research_iterations": "1"`); primitives now pass through. Phase 6 rewrites streaming anyway.
- 4 — README: minimal updates so it no longer names the removed researcher node (full rewrite is Phase 11).
- 5 — Built in the same session as the (duplicate) Phase 4 work because Reuben asked to start Phase 5. Session branch `claude/next-upgrade-phase-k9t1jy` was reset onto `upgrade/v2` (after PR #4 merged) before starting; its old commits remain in closed PR #5.
- 5 — Branches extract `FindingContent` (no id; the LLM never sees an id field). `Finding(FindingContent)` adds `id: int`. The `findings` reducer `add_findings` (in `schemas/finding.py`) dedupes and assigns ids, so ids are stable once assigned.
- 5 — Duplicate = same source URL (case-insensitive, trailing `/` ignored) and same finding text (case- and whitespace-insensitive). Evidence is not part of the key.
- 5 — The writer LLM writes every section except Sources; code appends `# Sources` listing each cited `[n]` that exists, in citation order. Any LLM-written Sources section is cut, uncited findings are not listed, and unknown ids are left out of Sources (the evaluator still flags them).
- 5 — Citation helpers live in `evaluation/citations.py` (pure, no LLM) and are imported by the writer and `eval.py`, so the report format and its checks use one parser. `[1, 2]` and `[1][2]` both parse; markdown links don't.
- 5 — Paragraph coverage counts paragraphs in Key Findings and Analysis (each list item counts as one paragraph); if neither heading is present, all body paragraphs. A report with no citations scores 0 for validity.
- 5 — `citation_evaluator` returns three LangSmith scores: `citation_validity`, `citation_coverage` (heuristic) and `citation_support` (structured-output judge on up to 5 cited claims sampled with a fixed seed; claims citing unknown ids are skipped).

## Blockers / needs Reuben
- [ ] Railway: add a Postgres instance and set `DATABASE_URL` (needed by Phase 8 in production)
- [ ] Railway: set `API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`
- [ ] GitHub secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY` (Phase 10 eval job)

## Rollbacks / incidents
What went wrong, what was rolled back, which guardrail was added to CLAUDE.md.
- 4 — Two sessions built Phase 4 in parallel (PR #4 and PR #5). #4 merged; #5 closed as a duplicate. Guardrail added: check open PRs into `upgrade/v2` before starting a phase.

## Notes for later phases
- Phase 6: the writer appends Sources after the LLM returns, so when tokens stream the Sources section arrives in the final state, not as tokens. The `done` event should carry the final report.
- Optional: research branches only get their own question, not the overall topic; passing `state["query"]` in the `Send` payload would give searches more context.
- Scores use `Field(ge=0, le=1)`; if OpenAI structured output ever rejects `minimum`/`maximum` in the schema, drop the bounds from `CritiqueAssessment` and clamp instead.
- `config/settings.py` raises at import when API keys are unset; `tests/conftest.py` sets dummy keys. Agents build their LLMs at import, so tests patch module-level objects (e.g. `agents.researcher.research_agent`).
- `evaluation/eval.py` creates a LangSmith `Client()` at import (Phase 10 fixes this).
- README "Key design decisions" still describes a combined researcher+extractor node (Phase 11 rewrite).

## Next step
Reuben: review and merge the Phase 5 PR into `upgrade/v2`; run the pending manual checks (Phases 1–5) when convenient. Then Phase 6 in a new session on a branch off `upgrade/v2` (check for open PRs first): async nodes and endpoints, token streaming with `node`/`token`/`done` SSE events. Test: the SSE generator emits `node`, `token`, `done` in order (mocked graph).
