from pydantic import BaseModel


class FindingContent(BaseModel):
    """What a research branch extracts from search results (no id yet)."""
    finding: str
    source: str
    evidence: str


class Finding(FindingContent):
    """A finding in state. `id` is what the report cites as [id]; it never changes."""
    id: int


def _key(f: FindingContent) -> tuple[str, str]:
    """Duplicate check: same source URL and same finding text, ignoring case/whitespace."""
    url = f.source.strip().rstrip("/").lower()
    text = " ".join(f.finding.split()).lower()
    return url, text


def add_findings(existing: list[Finding], new: list[FindingContent]) -> list[Finding]:
    """Reducer for `findings`: drop duplicates, give each new finding the next id.

    Existing findings keep their ids, so a citation [n] stays valid across rounds
    and parallel branches.
    """
    merged = list(existing or [])
    seen = {_key(f) for f in merged}
    next_id = max((f.id for f in merged), default=0) + 1
    for f in new or []:
        key = _key(f)
        if key in seen:
            continue
        seen.add(key)
        merged.append(Finding(id=next_id, **FindingContent.model_validate(f, from_attributes=True).model_dump()))
        next_id += 1
    return merged
