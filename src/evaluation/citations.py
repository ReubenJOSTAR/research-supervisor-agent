"""Pure citation helpers: parse inline [n] citations and score them. No LLM calls.

Used by the writer (to build the Sources section) and by `citation_evaluator`.
"""
import re

# [3] or [1, 4] — markdown links like [text](url) never match (digits only).
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_SOURCES_HEADING = re.compile(r"^#+\s*Sources\b.*$", re.IGNORECASE | re.MULTILINE)
_HEADING = re.compile(r"^#+\s*(.+?)\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

# Sections whose claims must carry a citation.
CITED_SECTIONS = ("key findings", "analysis")


def cited_ids(text: str) -> list[int]:
    """Every [n] in `text`, in order of first appearance, without repeats."""
    ids = []
    for match in _CITATION.finditer(text):
        for n in match.group(1).split(","):
            if int(n) not in ids:
                ids.append(int(n))
    return ids


def strip_sources(report: str) -> str:
    """The report body above its Sources section."""
    match = _SOURCES_HEADING.search(report)
    return report[: match.start()] if match else report


def _paragraphs_by_section(body: str) -> dict[str, list[str]]:
    """Paragraphs under each heading. Each list item counts as its own paragraph."""
    sections: dict[str, list[str]] = {"": []}
    current = ""
    for block in re.split(r"\n\s*\n", body):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        text_lines = []
        for line in lines:
            heading = _HEADING.match(line) if line.lstrip().startswith("#") else None
            if heading:
                current = heading.group(1).strip().lower()
                sections.setdefault(current, [])
            else:
                text_lines.append(line)
        if not text_lines:
            continue
        if all(_LIST_ITEM.match(l) for l in text_lines):
            sections[current].extend(text_lines)
        else:
            sections[current].append(" ".join(text_lines))
    return sections


def citation_heuristics(report: str, finding_ids) -> dict:
    """Checks on the report body (above Sources):

    - `valid_ratio`: share of distinct cited [n] that exist in the findings (0 if none cited).
    - `invalid_ids`: cited ids with no matching finding.
    - `paragraph_coverage`: share of paragraphs in Key Findings and Analysis with at
      least one citation (every body paragraph if neither section is present).
    """
    body = strip_sources(report)
    known = set(finding_ids)
    ids = cited_ids(body)
    invalid = [n for n in ids if n not in known]
    valid_ratio = (len(ids) - len(invalid)) / len(ids) if ids else 0.0

    sections = _paragraphs_by_section(body)
    paragraphs = [p for name, ps in sections.items() if name in CITED_SECTIONS for p in ps]
    if not paragraphs:
        paragraphs = [p for ps in sections.values() for p in ps]
    cited = sum(1 for p in paragraphs if _CITATION.search(p))
    coverage = cited / len(paragraphs) if paragraphs else 0.0

    return {
        "valid_ratio": round(valid_ratio, 3),
        "invalid_ids": invalid,
        "paragraph_coverage": round(coverage, 3),
        "num_citations": len(ids),
        "num_paragraphs": len(paragraphs),
    }


def cited_claims(report: str) -> list[tuple[str, list[int]]]:
    """Sentences in the report body that carry citations, with the ids they cite."""
    body = strip_sources(report)
    claims = []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line.strip()):
            ids = cited_ids(sentence)
            if ids:
                claims.append((_LIST_ITEM.sub("", sentence).strip(), ids))
    return claims
