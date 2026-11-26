from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.types import Command
from pydantic import BaseModel

from config.settings import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
)


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

        Generate 5 research questions that cover:

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
            "questions": plan.questions
        },
        goto="researcher"
    )