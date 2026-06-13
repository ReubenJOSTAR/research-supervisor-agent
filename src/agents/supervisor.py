from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.graph import END

from schemas.routing import RouteDecision

llm = ChatOpenAI(model="gpt-4o-mini")

MAX_RESEARCH_LOOPS = 3


def supervisor(state):

    if not state.get("questions"):
        return Command(goto="planner")

    if not state.get("messages"):
        return Command(goto="researcher")

    if not state.get("findings"):
        return Command(goto="researcher")

    if not state.get("critiques"):
        return Command(goto="critic")

    current_iterations = state.get("research_iterations", 0)

    if current_iterations >= MAX_RESEARCH_LOOPS:
        return Command(goto="writer")

    if state["critiques"].sufficient:
        return Command(goto="writer")

    return Command(
        update={
            "research_iterations": current_iterations + 1
        },
        goto="researcher"
    )