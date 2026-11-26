from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.types import Command

from config.settings import OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
)


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