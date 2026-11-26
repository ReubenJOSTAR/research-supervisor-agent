from typing import Literal

from langgraph.types import Command
from pydantic import BaseModel

from config import settings
from config.llm import get_llm

llm = get_llm()


class ResearchPlan(BaseModel):
    questions: list[str]


planner_llm = llm.with_structured_output(
    ResearchPlan
)


def planner(state) -> Command[Literal["researcher"]]:

    query = state["query"]

    plan = planner_llm.invoke(
        f"""
        You are an expert research planner.

        Generate {settings.NUM_QUESTIONS} research questions that cover:

        - Fundamentals
        - Current state
        - Challenges
        - Opportunities
        - Future outlook

        Topic:

        {query}
        """
    )

    return Command(
        update={
            "questions": plan.questions,
            # Round 1 researches the planner's questions.
            "research_queue": plan.questions,
        },
        goto="researcher"
    )