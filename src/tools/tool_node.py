from langgraph.prebuilt import ToolNode

from tools.search import search_web

tool_node = ToolNode([search_web])
