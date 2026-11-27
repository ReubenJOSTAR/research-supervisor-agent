"""Critique validator: `sufficient` must agree with the scores and gaps."""
import pytest
from pydantic import ValidationError

from schemas.critique import Critique, CritiqueAssessment

HIGH = {"coverage": 0.9, "evidence_quality": 0.8, "source_diversity": 0.7, "completeness": 0.95}
LOW = {**HIGH, "source_diversity": 0.4}


def test_consistent_critiques_are_accepted():
    assert Critique(sufficient=True, scores=HIGH, gaps=[], critique="ok").sufficient
    assert not Critique(sufficient=False, scores=LOW, gaps=["more sources"], critique="x").sufficient
    assert not Critique(sufficient=False, scores=HIGH, gaps=["one gap"], critique="x").sufficient


@pytest.mark.parametrize(
    "scores, gaps",
    [
        (LOW, []),           # a score below threshold
        (HIGH, ["a gap"]),   # high scores but gaps remain
        (LOW, ["a gap"]),
    ],
)
def test_sufficient_true_inconsistent_with_scores_is_rejected(scores, gaps):
    with pytest.raises(ValidationError):
        Critique(sufficient=True, scores=scores, gaps=gaps, critique="x")


def test_sufficient_false_with_high_scores_and_no_gaps_is_rejected():
    with pytest.raises(ValidationError):
        Critique(sufficient=False, scores=HIGH, gaps=[], critique="x")


def test_scores_must_be_between_0_and_1():
    with pytest.raises(ValidationError):
        Critique(sufficient=False, scores={**HIGH, "coverage": 1.5}, gaps=["g"], critique="x")


def test_from_assessment_derives_sufficient():
    assert Critique.from_assessment(CritiqueAssessment(scores=HIGH, gaps=[], critique="x")).sufficient
    assert not Critique.from_assessment(CritiqueAssessment(scores=LOW, gaps=["g"], critique="x")).sufficient


async def test_critic_derives_sufficient_and_appends_history(monkeypatch):
    import agents.critic as critic_module

    class FakeJudge:
        async def ainvoke(self, prompt):
            return CritiqueAssessment(scores=LOW, gaps=["find independent sources"], critique="thin")

    monkeypatch.setattr(critic_module, "judge", FakeJudge())
    cmd = await critic_module.critic({"query": "topic", "findings": []})

    critique = cmd.update["critiques"]
    assert critique.sufficient is False
    assert critique.gaps == ["find independent sources"]
    assert cmd.update["critique_history"] == [critique]
    assert cmd.goto == "supervisor"
