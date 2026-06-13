from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.graph import END

from schemas.routing import RouteDecision

llm = ChatOpenAI(model="gpt-4o-mini")

router = llm.with_structured_output(
    RouteDecision
)

from langgraph.types import Command


MAX_RESEARCH_LOOPS = 3


def supervisor(state):

    if not state.get("questions"):

        return Command(
            goto="planner"
        )

    if not state.get("messages"):

        return Command(
            goto="researcher"
        )

    if not state.get("critiques"):

        return Command(
            goto="critic"
        )

    if (
        state.get(
            "research_iterations",
            0
        ) >= MAX_RESEARCH_LOOPS
    ):
        return Command(
            goto="writer"
        )

    if state["critiques"].sufficient:

        return Command(
            goto="writer"
        )

    return Command(
        goto="researcher"
    )

    decision = router.invoke(
        f"""
        Current State

        Questions:
        {state.get('questions')}

        Findings Count:
        {len(state.get('findings', []))}

        Critique:
        {state.get('critiques')}

        Available agents:

        - researcher
        - writer
        - FINISH

        Decide the next agent.
        """
    )

    if decision.next == "researcher":

        return Command(
            goto="researcher"
        )
    if decision.next == "writer":
        return Command(
            goto="writer"
        )
    
    return Command(goto = END)