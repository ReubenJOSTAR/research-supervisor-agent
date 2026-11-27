import operator
from typing import Annotated, TypedDict

from schemas.finding import Finding, add_findings
from schemas.critique import Critique


class GraphState(TypedDict):

    query: str

    questions: list[str]

    # What this round researches, one parallel branch per item: the planner's
    # questions in round 1, the critic's gaps after that. Set by the supervisor.
    research_queue: list[str]

    # Accumulate across rounds and parallel branches; duplicates (same URL +
    # text) are dropped and each new finding gets the next id (cited as [id]).
    findings: Annotated[list[Finding], add_findings]

    # None until the critic has run for the current round.
    critiques: Critique | None

    # Every round's critique (scores + gaps), oldest first.
    critique_history: Annotated[list[Critique], operator.add]

    # Number of research rounds (1 after the first pass). Incremented by the
    # supervisor when it fans a round out.
    research_iterations: int

    finalReport: str
