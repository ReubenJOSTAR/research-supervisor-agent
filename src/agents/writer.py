from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from config.llm import get_llm

llm = get_llm()


def writer(state) -> Command[Literal["__end__"]]:

    report = llm.invoke(
        f"""
        Write a professional research report.

        Topic:
        {state['query']}

        Research Questions:
        {state['questions']}

        Findings:
        {state['findings']}

        Structure:

        # Executive Summary

        # Key Findings

        # Analysis

        # Challenges

        # Future Outlook

        # Sources
        """
    )

    return Command(
        update={
            "finalReport":
                report.content
        },
        goto=END
    )