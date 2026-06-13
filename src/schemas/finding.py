from pydantic import BaseModel


class Finding(BaseModel):
    finding: str
    source: str
    evidence: str