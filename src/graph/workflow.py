from langgraph.graph import (
    StateGraph,
    START
)

from graph.state import GraphState
from agents.extractor import extractor


from agents.supervisor import supervisor
from agents.planner import planner
from agents.researcher import researcher
from agents.critic import critic
from agents.writer import writer

from tools.tool_node import tool_node

builder = StateGraph(GraphState)

builder.add_node(
    "supervisor",
    supervisor
)

builder.add_node(
    "planner",
    planner
)

builder.add_node(
    "researcher",
    researcher
)

builder.add_node(
    "tools",
    tool_node
)

builder.add_node(
    "critic",
    critic
)

builder.add_node(
    "writer",
    writer
)

builder.add_node("extractor", extractor)

builder.add_edge(
    START,
    "supervisor"
)
builder.add_edge("tools", "extractor")  # not "critic" directly


graph = builder.compile()