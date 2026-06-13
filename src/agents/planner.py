from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.types import Command

llm = ChatOpenAI(model="gpt-4o-mini")


class ResearchPlan(BaseModel):
    questions: list[str]


planner_llm = llm.with_structured_output(
    ResearchPlan
)


def planner(state):

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