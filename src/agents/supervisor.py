from typing import Literal

from langgraph.types import Command, Send

from config import settings


def _fan_out(queue: list[str], iterations: int) -> Command:
    """Start a research round: one parallel `research_task` branch per queue item.

    The round is counted here (all branches return to the supervisor together),
    and the critique is cleared so the critic runs again after the round.
    """
    return Command(
        update={"research_queue": queue, "research_iterations": iterations + 1, "critiques": None},
        goto=[Send("research_task", {"query": q}) for q in queue],
    )


async def supervisor(state) -> Command[Literal["planner", "research_task", "critic", "writer"]]:
    """Deterministic router: plain Python, no LLM."""

    if not state.get("questions"):
        return Command(goto="planner")

    iterations = state.get("research_iterations", 0)

    # Round 1 researches the planner's questions.
    if iterations == 0:
        return _fan_out(state["questions"], iterations)

    critique = state.get("critiques")
    if not critique:
        return Command(goto="critic")

    # No gaps means there is nothing left to research, even if scores are low.
    if critique.sufficient or not critique.gaps or iterations >= settings.MAX_RESEARCH_LOOPS:
        return Command(goto="writer")

    # Round 2+: research only the critic's gaps, never the original questions.
    return _fan_out(critique.gaps, iterations)
