import operator
from typing import Annotated, TypedDict

from schemas.finding import Finding
from schemas.critique import Critique


class GraphState(TypedDict):

    query: str

    questions: list[str]

    # What this round researches, one parallel branch per item: the planner's
    # questions in round 1, the critic's gaps after that. Set by the supervisor.
    research_queue: list[str]

    # Parallel branches and later rounds all add to this.
    findings: Annotated[list[Finding], operator.add]

    # None until the critic has run for the current round.
    critiques: Critique | None

    # Every round's critique (scores + gaps), oldest first.
    critique_history: Annotated[list[Critique], operator.add]

    # Number of research rounds completed (1 after the first pass).
    research_iterations: int

    finalReport: str
