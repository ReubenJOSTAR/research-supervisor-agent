# PROGRESS.md — research-supervisor-agent v2 upgrade

New session? Read `CLAUDE.md`, then this file, then the spec for the next phase in `UPGRADE_PROMPT.md`. Update this file before ending the session.

**Branch:** `upgrade/v2`
**Current phase:** 1
**Last updated:** 2026-11-26 — plan created, no code changed yet

## Status

| Phase | Feature | Status | Commit | Notes |
|---|---|---|---|---|
| 1 | Bug fixes | ⬜ Not started | | |
| 2 | Config + tests | ⬜ Not started | | |
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
- [ ] Clear `critiques` on loop-back so the critic re-runs each round
- [ ] Reducers: `messages` → `add_messages`, `findings` → `operator.add`
- [ ] No-tool-call path counts as an iteration (no infinite loop)
- [ ] `research_iterations` = rounds completed; `depth_evaluator` updated
- [ ] README uses `research_iterations` (not `iterations`)
- [ ] `quality_evaluator` uses structured output instead of `json.loads`
- [ ] Remove unused supervisor LLM, `RouteDecision`, empty `wikipedia.py` / `arxiv.py`, duplicate imports
- [ ] Typed `Command[Literal[...]]` returns on every node

## Manual checks (Reuben)
| Phase | Check | Result |
|---|---|---|
| | | |

## Decisions
Choices made where the spec was ambiguous (phase — decision — why).
- 

## Blockers / needs Reuben
- [ ] Railway: add a Postgres instance and set `DATABASE_URL` (needed by Phase 8 in production)
- [ ] Railway: set `API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`
- [ ] GitHub secrets: `OPENAI_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY` (Phase 10 eval job)

## Rollbacks / incidents
What went wrong, what was rolled back, which guardrail was added to CLAUDE.md.
- 

## Next step
Start Phase 1 on a new branch `upgrade/v2`.
