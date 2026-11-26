from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from config import settings
from config.llm import get_llm
from tools.search import search_web

llm = get_llm()

research_agent = llm.bind_tools([search_web])


def researcher(state) -> Command[Literal["tools", "extractor"]]:

    questions = state["questions"]

    prompt = f"""
    You are a research agent.

    Available tools:

    - search_web


    Research these questions:

    {questions}

    Use whichever tools are necessary, at most
    {settings.MAX_TOOL_CALLS_PER_QUESTION} searches per question.
    """

    response = research_agent.invoke([HumanMessage(content=prompt)])

    # Hard cap on searches per round, in case the model ignores the prompt.
    max_calls = settings.MAX_TOOL_CALLS_PER_QUESTION * max(len(questions), 1)
    if len(response.tool_calls) > max_calls:
        response.tool_calls = response.tool_calls[:max_calls]

    # No tool calls: skip the tool node; the extractor still closes the round
    # so it counts as an iteration (prevents an infinite loop).
    goto = "tools" if response.tool_calls else "extractor"

    return Command(update={"messages": [response]}, goto=goto)
