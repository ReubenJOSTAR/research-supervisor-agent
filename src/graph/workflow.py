from langgraph.graph import StateGraph, START

from graph.state import GraphState
from agents.supervisor import supervisor
from agents.planner import planner
from agents.research_task import research_task
from agents.critic import critic
from agents.writer import writer

builder = StateGraph(GraphState)

builder.add_node("supervisor", supervisor)
builder.add_node("planner", planner)
builder.add_node("research_task", research_task)
builder.add_node("critic", critic)
builder.add_node("writer", writer)

builder.add_edge(START, "supervisor")
# Parallel branches (fanned out by the supervisor with Send) join back here.
builder.add_edge("research_task", "supervisor")

graph = builder.compile()
