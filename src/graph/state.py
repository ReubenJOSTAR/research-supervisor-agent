from typing import TypedDict

from langchain_core.messages import BaseMessage

from schemas.finding import Finding
from schemas.critique import Critique


class GraphState(TypedDict):

    query: str

    messages: list[BaseMessage]

    questions: list[str]

    findings: list[Finding]

    critiques: Critique

    research_iterations: int

    finalReport: str