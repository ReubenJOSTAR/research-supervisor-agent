# PROGRESS.md — research-supervisor-agent v2 upgrade

New session? Read `CLAUDE.md`, then this file, then the spec for the next phase in `UPGRADE_PROMPT.md`. Update this file before ending the session.

**Branch:** `upgrade/v2` is the integration branch. Each phase is developed on a session branch and merged into `upgrade/v2` via PR; `upgrade/v2` goes to `main` once all phases are done.
**Current phase:** 3
**Last updated:** 2026-11-26 — Phase 2 done

## Status

| Phase | Feature | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | Bug fixes | ✅ Done | b450e3c | PR #1 → `upgrade/v2`. Verified with a mocked end-to-end run; no pytest suite yet (Phase 2) |
| 2 | Config + tests | ✅ Done | 011758e | PR #2 → `upgrade/v2` from `claude/magical-dijkstra-nqe5vb`. 14 tests pass on 3.11 and 3.13 |
| 3 | Critic with gaps + scores | ⬜ Not started | | |
| 4 | Parallel research (Send) | ⬜ Not started | | |
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
| 2 | `pip install -r requirements-dev.txt && pytest` passes locally | ⬜ pending |

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

## Blockers / needs Reuben
- [ ] Railway: add a Postgres instance and set `DATABASE_URL` (needed by Phase 8 in production)
- [ ] Railway: set `API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`
- [ ] GitHub secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY` (Phase 10 eval job)

## Rollbacks / incidents
What went wrong, what was rolled back, which guardrail was added to CLAUDE.md.
- (none)

## Notes for later phases
- `config/settings.py` raises at import when API keys are unset; `tests/conftest.py` sets dummy keys. Agents build their LLMs at import, so tests patch module-level objects (e.g. `agents.researcher.research_agent`).
- `evaluation/eval.py` creates a LangSmith `Client()` at import (Phase 10 fixes this).
- README "Key design decisions" still describes a combined researcher+extractor node (Phase 11 rewrite).

## Next step
Merge the Phase 2 PR into `upgrade/v2` (after `pytest` passes locally), then Phase 3 on a branch off `upgrade/v2`: Critique with scores + gaps (validator), later rounds research only gaps, `critique_history`. Tests: inconsistent `sufficient` rejected; supervisor routes gaps on round ≥ 2.
