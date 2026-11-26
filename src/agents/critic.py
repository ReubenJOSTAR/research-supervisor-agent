from typing import Literal

from langgraph.types import Command

from config.llm import get_llm
from schemas.critique import SUFFICIENT_SCORE, Critique, CritiqueAssessment

llm = get_llm()
judge = llm.with_structured_output(CritiqueAssessment)


def critic(state) -> Command[Literal["supervisor"]]:

    findings = state["findings"]
    topic = state['query']

    assessment = judge.invoke(
        f"""
        You are evaluating research quality for the Topic:{topic}

        Score each from 0.0 to 1.0:

        1. coverage: are all important aspects of the topic addressed?
        2. evidence_quality: are claims backed by concrete, credible evidence?
        3. source_diversity: do findings come from varied, independent sources?
        4. completeness: is there enough detail to write a thorough report?

        List `gaps`: specific, searchable follow-up queries for anything
        missing or weak. Any score below {SUFFICIENT_SCORE} must come with at
        least one gap. Leave gaps empty only if nothing important is missing.

        Findings:

        {findings}
        """
    )

    critique = Critique.from_assessment(assessment)

    return Command(
        update={
            "critiques": critique,
            "critique_history": [critique],
        },
        goto="supervisor"
    )
