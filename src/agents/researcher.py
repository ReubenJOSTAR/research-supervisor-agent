from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from config.settings import OPENAI_API_KEY
from tools.search import search_web

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
)

research_agent = llm.bind_tools([search_web])


def researcher(state) -> Command[Literal["tools", "extractor"]]:

    questions = state["questions"]

    prompt = f"""
    You are a research agent.

    Available tools:

    - search_web


    Research these questions:

    {questions}

    Use whichever tools are necessary.
    """

    response = research_agent.invoke([HumanMessage(content=prompt)])

    # No tool calls: skip the tool node; the extractor still closes the round
    # so it counts as an iteration (prevents an infinite loop).
    goto = "tools" if response.tool_calls else "extractor"

    return Command(update={"messages": [response]}, goto=goto)
