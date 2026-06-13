from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.graph import END

llm = ChatOpenAI(model="gpt-4o-mini")


def writer(state):

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