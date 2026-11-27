from typing import Literal

from langgraph.types import Command, Send

from config import settings


def _fan_out(state, queue: list[str], update: dict) -> Command:
    """Start a research round: one parallel `research_task` branch per query.

    The round is counted here, when it is dispatched; branches return to the
    supervisor only after all of them finish, so `research_iterations` equals
    rounds completed whenever the supervisor next runs.
    """
    return Command(
        update={
            **update,
            "research_queue": queue,
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
        goto=[Send("research_task", {"topic": state["query"], "task": q}) for q in queue],
    )


def supervisor(state) -> Command[Literal["planner", "research_task", "critic", "writer"]]:
    """Deterministic router: plain Python, no LLM."""

    if not state.get("questions"):
        return Command(goto="planner")

    iterations = state.get("research_iterations", 0)

    # Round 1 researches the planner's questions.
    if iterations == 0:
        return _fan_out(state, state["questions"], {})

    critique = state.get("critiques")
    if not critique:
        return Command(goto="critic")

    # No gaps means there is nothing left to research, even if scores are low.
    if critique.sufficient or not critique.gaps or iterations >= settings.MAX_RESEARCH_LOOPS:
        return Command(goto="writer")

    # Round 2+: research only the critic's gaps, never the original questions.
    # Clear the critique so the critic runs again next round.
    return _fan_out(state, critique.gaps, {"critiques": None})
