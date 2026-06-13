from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage

from langgraph.types import Command

from tools.search import search_web
# from tools.wikipedia import search_wikipedia
# from tools.arxiv import search_arxiv


llm = ChatOpenAI(
    model="gpt-4o-mini"
)

tools = [
    search_web
    # search_wikipedia,
    # search_arxiv
]

research_agent = llm.bind_tools(
    tools
)


def researcher(state):

    questions = state["questions"]

    prompt = f"""
    You are a research agent.

    Available tools:

    - search_web


    Research these questions:

    {questions}

    Use whichever tools are necessary.
    """

    response = research_agent.invoke(
        [
            HumanMessage(content=prompt)
        ]
    )

    return Command(
        update={
            "messages":
                state.get("messages", [])
                + [response]
        },
        goto="tools"
    )