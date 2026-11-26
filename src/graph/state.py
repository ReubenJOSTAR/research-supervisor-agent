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

    # What the researcher works on this round: the planner's questions in
    # round 1, the critic's gaps after that. Set by the supervisor.
    research_queue: list[str]

    findings: Annotated[list[Finding], operator.add]

    # None until the critic has run for the current round.
    critiques: Critique | None

    # Every round's critique (scores + gaps), oldest first.
    critique_history: Annotated[list[Critique], operator.add]

    # Number of research rounds completed (1 after the first pass).
    research_iterations: int

    finalReport: str
