from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from config.llm import get_llm
from evaluation.citations import cited_ids, strip_sources
from schemas.finding import Finding

llm = get_llm()


def numbered_findings(findings: list[Finding]) -> str:
    """The writer's evidence list: one `[id]` entry per finding."""
    return "\n".join(
        f"[{f.id}] {f.finding}\n    Evidence: {f.evidence}\n    Source: {f.source}" for f in findings
    )


def sources_section(report: str, findings: list[Finding]) -> str:
    """`# Sources` listing every [n] the report cites that exists, in citation order.

    Built in code, not by the LLM, so each [n] always matches its finding's URL.
    """
    by_id = {f.id: f for f in findings}
    lines = [f"[{n}] {by_id[n].source}" for n in cited_ids(report) if n in by_id]
    return "# Sources\n\n" + ("\n".join(lines) if lines else "No sources cited.")


def writer(state) -> Command[Literal["__end__"]]:

    findings = state["findings"]

    report = llm.invoke(
        f"""
        Write a professional research report using ONLY the numbered findings
        below. Do not add facts, numbers or sources that are not in them.

        Cite inline with the finding's number in square brackets, e.g. [3], or
        [2][5] for several. Every claim in Key Findings and Analysis must carry
        at least one citation. Only cite numbers from the list.

        Topic:
        {state['query']}

        Research Questions:
        {state['questions']}

        Findings:
        {numbered_findings(findings)}

        Structure (exactly these markdown headings):

        # Executive Summary

        # Key Findings

        # Analysis

        # Challenges

        # Future Outlook

        Do not write a Sources section; it is added automatically.
        """
    )

    body = strip_sources(report.content).rstrip()

    return Command(
        update={"finalReport": f"{body}\n\n{sources_section(body, findings)}\n"},
        goto=END
    )
