from typing import TypedDict

from langchain_core.messages import BaseMessage

from models.finding import Finding
from models.critique import Critique


class GraphState(TypedDict):

    query: str

    messages: list[BaseMessage]

    questions: list[str]

    findings: list[Finding]

    critiques: Critique

    research_iterations: int

    finalReport: str