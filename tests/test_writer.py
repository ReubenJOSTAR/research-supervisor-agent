"""Phase 5: the writer gets numbered findings and the Sources section matches the citations."""
from langchain_core.messages import AIMessage

import agents.writer as writer_module
from schemas.finding import Finding

FINDINGS = [
    Finding(id=1, finding="Solar doubled", source="https://a.example", evidence="ea"),
    Finding(id=2, finding="Costs fell", source="https://b.example", evidence="eb"),
    Finding(id=3, finding="Unused", source="https://c.example", evidence="ec"),
]


class FakeLLM:
    def __init__(self, content):
        self.content, self.prompts = content, []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return AIMessage(content=self.content)


async def _write(monkeypatch, content):
    llm = FakeLLM(content)
    monkeypatch.setattr(writer_module, "llm", llm)
    state = {"query": "solar", "questions": ["q"], "findings": FINDINGS}
    return (await writer_module.writer(state)).update["finalReport"], llm.prompts[0]


async def test_prompt_numbers_every_finding(monkeypatch):
    _, prompt = await _write(monkeypatch, "# Key Findings\n\nx [1]")
    for f in FINDINGS:
        assert f"[{f.id}] {f.finding}" in prompt and f.source in prompt


async def test_sources_list_cited_findings_in_citation_order(monkeypatch):
    report, _ = await _write(monkeypatch, "# Key Findings\n\nCosts fell [2]. Solar doubled [1][2].")
    sources = report.split("# Sources")[1]
    assert sources.strip().splitlines() == ["[2] https://b.example", "[1] https://a.example"]
    assert "c.example" not in sources  # uncited finding is not listed


async def test_llm_sources_section_is_replaced_and_unknown_ids_dropped(monkeypatch):
    report, _ = await _write(monkeypatch, "# Analysis\n\nA [1] and B [42].\n\n# Sources\n[42] https://made-up.example")
    assert report.count("# Sources") == 1
    assert "made-up" not in report
    assert report.rstrip().endswith("[1] https://a.example")


async def test_no_citations_gives_empty_sources(monkeypatch):
    report, _ = await _write(monkeypatch, "# Key Findings\n\nNothing cited.")
    assert report.rstrip().endswith("# Sources\n\nNo sources cited.")
