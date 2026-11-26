from typing import Literal

from langchain_core.messages import ToolMessage
from langgraph.types import Command
from pydantic import BaseModel

from config.llm import get_llm
from schemas.finding import Finding

llm = get_llm()


class Findings(BaseModel):
    findings: list[Finding]


extractor_llm = llm.with_structured_output(Findings)


def _latest_tool_results(messages) -> list[str]:
    """Tool results from the current round only (the trailing ToolMessages).

    `messages` accumulates across rounds, so earlier rounds' results must be
    skipped or their findings would be extracted (and added) again.
    """
    results = []
    for m in reversed(messages):
        if not isinstance(m, ToolMessage):
            break
        results.append(m.content)
    return list(reversed(results))


def extractor(state) -> Command[Literal["supervisor"]]:
    # Every pass through research ends here, so the round is counted here.
    update = {"research_iterations": state.get("research_iterations", 0) + 1}

    tool_results = _latest_tool_results(state.get("messages", []))

    if tool_results:
        raw_text = "\n\n".join(tool_results)

        result = extractor_llm.invoke(
            f"""Extract structured findings from these search results.

For each distinct finding, identify:
- The key finding or fact
- The source URL
- The supporting evidence

Search results:
{raw_text}"""
        )
        update["findings"] = result.findings

    return Command(update=update, goto="supervisor")
