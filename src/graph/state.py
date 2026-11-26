import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from schemas.finding import Finding
from schemas.critique import Critique


class GraphState(TypedDict):

    query: str

    # Accumulate across rounds instead of being overwritten.
    messages: Annotated[list[BaseMessage], add_messages]

    questions: list[str]

    findings: Annotated[list[Finding], operator.add]

    # None until the critic has run for the current round.
    critiques: Critique | None

    # Number of research rounds completed (1 after the first pass).
    research_iterations: int

    finalReport: str
