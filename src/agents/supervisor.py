from typing import Literal

from langgraph.types import Command

MAX_RESEARCH_LOOPS = 3


def supervisor(state) -> Command[Literal["planner", "researcher", "critic", "writer"]]:
    """Deterministic router: plain Python, no LLM."""

    if not state.get("questions"):
        return Command(goto="planner")

    iterations = state.get("research_iterations", 0)

    if iterations == 0:
        return Command(goto="researcher")

    if not state.get("critiques"):
        return Command(goto="critic")

    if state["critiques"].sufficient or iterations >= MAX_RESEARCH_LOOPS:
        return Command(goto="writer")

    # Loop back: clear the critique so the critic runs again next round.
    return Command(update={"critiques": None}, goto="researcher")
