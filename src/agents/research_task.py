"""One parallel research branch: search for a single query and extract findings.

The supervisor fans out one `Send("research_task", ...)` per question (round 1)
or per critic gap (later rounds). Branches run in the same superstep and their
findings merge through the `findings` reducer.
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
    """What each branch receives via Send: the overall topic and its own query."""
    topic: str
    task: str


def research_task(state: ResearchTaskInput) -> dict:
    """Never raises: a failing branch returns no findings so the run continues."""
    try:
        return {"findings": _research(state["topic"], state["task"])}
    except Exception as e:
        logger.warning("research_task failed for %r: %s: %s", state["task"], type(e).__name__, e)
        return {"findings": []}


def _research(topic: str, task: str) -> list[Finding]:
    response = research_agent.invoke([HumanMessage(content=f"""
    You are a research agent investigating the topic: {topic}

    Research this question:

    {task}

    Use the search_web tool, at most {settings.MAX_TOOL_CALLS_PER_QUESTION} searches.
    """)])

    # Hard cap, in case the model ignores the prompt.
    calls = response.tool_calls[:settings.MAX_TOOL_CALLS_PER_QUESTION]
    results = [search_web.invoke(call["args"]) for call in calls]
    if not results:
        return []

    raw_text = "\n\n".join(results)
    extracted = extractor_llm.invoke(f"""Extract structured findings from these search results.
They were gathered to answer: {task}

For each distinct finding, identify:
- The key finding or fact
- The source URL
- The supporting evidence

Search results:
{raw_text}""")
    return extracted.findings
