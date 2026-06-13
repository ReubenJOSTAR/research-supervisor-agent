from langchain_openai import ChatOpenAI
from langgraph.types import Command

from schemas.critique import Critique

llm = ChatOpenAI(model="gpt-4o-mini")

judge = llm.with_structured_output(
    Critique
)


def critic(state):

    findings = state["findings"]
    topic = state['query']

    critique = judge.invoke(
        f"""
        You are evaluating research quality for the Topic:{topic}

        Determine:

        1. Coverage
        2. Evidence quality
        3. Source diversity
        4. Completeness

        Findings:

        {findings}

        If additional research is required,
        mark sufficient=False.
        """
    )

    return Command(
        update={
            "critiques": critique
        },
        goto="supervisor"
    )