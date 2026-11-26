from pydantic import BaseModel, Field, model_validator

# A round is sufficient only when every score reaches this and no gaps remain.
SUFFICIENT_SCORE = 0.7


class CritiqueScores(BaseModel):
    coverage: float = Field(ge=0, le=1)
    evidence_quality: float = Field(ge=0, le=1)
    source_diversity: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)


class CritiqueAssessment(BaseModel):
    """What the critic LLM returns. `sufficient` is derived, never guessed by the LLM."""
    scores: CritiqueScores
    gaps: list[str] = Field(
        description="Specific follow-up research queries for what is missing or weak. "
                    "Empty only if nothing important is missing."
    )
    critique: str


def is_sufficient(scores: CritiqueScores, gaps: list[str]) -> bool:
    return not gaps and all(v >= SUFFICIENT_SCORE for v in scores.model_dump().values())


class Critique(CritiqueAssessment):
    sufficient: bool

    @model_validator(mode="after")
    def _sufficient_matches_scores(self):
        if self.sufficient != is_sufficient(self.scores, self.gaps):
            raise ValueError(
                f"sufficient must be True exactly when every score >= {SUFFICIENT_SCORE} and there are no gaps"
            )
        return self

    @classmethod
    def from_assessment(cls, a: CritiqueAssessment) -> "Critique":
        return cls(**a.model_dump(), sufficient=is_sufficient(a.scores, a.gaps))
