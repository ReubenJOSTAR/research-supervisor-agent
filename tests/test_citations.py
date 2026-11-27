"""Phase 5: heuristic citation evaluator — valid/invalid [n] and paragraph coverage."""
from evaluation.citations import cited_claims, cited_ids, citation_heuristics, strip_sources

REPORT = """# Executive Summary

Solar is growing fast.

# Key Findings

- Capacity doubled since 2020 [1].
- Costs fell 40% [2][3].
- Storage is the bottleneck.

# Analysis

Cheaper panels drive adoption [1, 2]. Grid limits slow it [9].

Policy matters too.

# Challenges

Permitting is slow.

# Sources

[1] https://a.example
[2] https://b.example
[7] https://c.example
"""


def test_cited_ids_parses_single_adjacent_and_grouped_citations():
    assert cited_ids("x [1] y [2][3] z [1, 4] [link](https://e.com) [a]") == [1, 2, 3, 4]


def test_strip_sources_drops_the_sources_section():
    body = strip_sources(REPORT)
    assert "# Sources" not in body and "[7]" not in body
    assert strip_sources("no sources here") == "no sources here"


def test_valid_and_invalid_citations():
    h = citation_heuristics(REPORT, finding_ids=[1, 2, 3])
    assert h["invalid_ids"] == [9]          # [7] is only in Sources, which is ignored
    assert h["num_citations"] == 4          # 1, 2, 3, 9
    assert h["valid_ratio"] == 0.75


def test_all_citations_valid():
    assert citation_heuristics(REPORT, finding_ids=[1, 2, 3, 9])["valid_ratio"] == 1.0


def test_paragraph_coverage_counts_key_findings_and_analysis_only():
    h = citation_heuristics(REPORT, finding_ids=[1, 2, 3])
    # Key Findings: 3 list items (2 cited). Analysis: 2 paragraphs (1 cited).
    assert h["num_paragraphs"] == 5
    assert h["paragraph_coverage"] == 0.6


def test_coverage_falls_back_to_all_paragraphs_without_those_sections():
    h = citation_heuristics("Intro [1].\n\nMore text.\n\nEnd [2].", finding_ids=[1, 2])
    assert h["num_paragraphs"] == 3
    assert h["paragraph_coverage"] == round(2 / 3, 3)


def test_report_without_citations_scores_zero():
    h = citation_heuristics("# Key Findings\n\nNothing cited.", finding_ids=[1])
    assert h == {"valid_ratio": 0.0, "invalid_ids": [], "paragraph_coverage": 0.0,
                 "num_citations": 0, "num_paragraphs": 1}


def test_empty_report():
    assert citation_heuristics("", finding_ids=[])["paragraph_coverage"] == 0.0


def test_cited_claims_are_sentences_with_their_ids():
    claims = cited_claims(REPORT)
    assert ("Capacity doubled since 2020 [1].", [1]) in claims
    assert ("Cheaper panels drive adoption [1, 2].", [1, 2]) in claims
    assert ("Grid limits slow it [9].", [9]) in claims
    assert all("Policy" not in c for c, _ in claims)
    assert all(7 not in ids for _, ids in claims)  # Sources section excluded
