from langgraph.prebuilt import ToolNode

from tools.search import search_web
# from tools.wikipedia import search_wikipedia
# from tools.arxiv import search_arxiv


tool_node = ToolNode(
    [
        search_web
        # search_wikipedia,
        # search_arxiv
    ]
)