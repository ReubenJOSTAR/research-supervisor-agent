from typing import Literal

from langgraph.types import Command

from config import settings


def supervisor(state) -> Command[Literal["planner", "researcher", "critic", "writer"]]:
    """Deterministic router: plain Python, no LLM."""

    if not state.get("questions"):
        return Command(goto="planner")

    iterations = state.get("research_iterations", 0)

    # Round 1 researches the planner's questions.
    if iterations == 0:
        return Command(update={"research_queue": state["questions"]}, goto="researcher")

    critique = state.get("critiques")
    if not critique:
        return Command(goto="critic")

    # No gaps means there is nothing left to research, even if scores are low.
    if critique.sufficient or not critique.gaps or iterations >= settings.MAX_RESEARCH_LOOPS:
        return Command(goto="writer")

    # Round 2+: research only the critic's gaps, never the original questions.
    # Clear the critique so the critic runs again next round.
    return Command(update={"critiques": None, "research_queue": critique.gaps}, goto="researcher")
