from typing import Literal

from langgraph.types import Command

from config.llm import get_llm
from schemas.critique import Critique

llm = get_llm()
judge = llm.with_structured_output(
    Critique
)


def critic(state) -> Command[Literal["supervisor"]]:

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