"""One parallel research branch: search for a single query and extract findings.

The supervisor fans out one `Send("research_task", {"query": ...})` per item in
`research_queue`. Branches run in the same superstep and their findings merge
through the `findings` reducer.
"""
import logging
from typing import TypedDict

from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from config import settings
from config.llm import get_llm
from schemas.finding import Finding
from tools.search import search_web

logger = logging.getLogger(__name__)

llm = get_llm()
research_agent = llm.bind_tools([search_web])


class Findings(BaseModel):
    findings: list[Finding]


extractor_llm = llm.with_structured_output(Findings)


class ResearchTaskInput(TypedDict):
    """The payload each `Send` carries: one question (round 1) or one gap (later rounds)."""

    query: str


def research_task(task: ResearchTaskInput) -> dict:
    query = task["query"]
    try:
        response = research_agent.invoke([HumanMessage(content=f"""
        You are a research agent. Use search_web to research this question,
        with at most {settings.MAX_TOOL_CALLS_PER_QUESTION} searches.

        Question: {query}
        """)])

        # Hard cap, in case the model ignores the prompt.
        tool_calls = response.tool_calls[: settings.MAX_TOOL_CALLS_PER_QUESTION]
        results = [search_web.invoke(call["args"]) for call in tool_calls]
        if not results:
            return {"findings": []}

        raw_text = "\n\n".join(results)
        extracted = extractor_llm.invoke(f"""Extract structured findings from these search results.

For each distinct finding, identify:
- The key finding or fact
- The source URL
- The supporting evidence

Question: {query}

Search results:
{raw_text}""")
        return {"findings": extracted.findings}

    except Exception:
        # A failing branch must never crash the run: it contributes no findings.
        logger.warning("Research branch failed for query %r", query, exc_info=True)
        return {"findings": []}
