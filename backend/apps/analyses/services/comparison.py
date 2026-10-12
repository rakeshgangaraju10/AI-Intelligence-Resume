"""
Compare two stored analyses (pure Python).

Typical use: the same job analysed with two versions of a resume, to see which
skills an edit gained or lost. Works on any two analyses; `basis` says what they
have in common so the UI can warn when a comparison isn't like-for-like.
"""
from dataclasses import dataclass

MATCHED = "matched"

GAINED = "gained"          # not matched in A, matched in B
LOST = "lost"              # matched in A, not matched in B
UNCHANGED = "unchanged"    # same matched/not-matched outcome
ONLY_IN_A = "only_in_a"    # requirement exists only in A's job
ONLY_IN_B = "only_in_b"


@dataclass(frozen=True)
class SkillRow:
    skill_name: str
    kind: str
    weight: int
    status: str


@dataclass(frozen=True)
class SkillComparison:
    skill_name: str
    kind_a: str | None
    kind_b: str | None
    status_a: str | None
    status_b: str | None
    change: str


def comparison_basis(resume_a: str, resume_b: str, job_a: int, job_b: int) -> str:
    if job_a == job_b and resume_a == resume_b:
        return "same_resume_and_job"
    if job_a == job_b:
        return "same_job"
    if resume_a == resume_b:
        return "same_resume"
    return "different"


def compare_skill_results(a: list[SkillRow], b: list[SkillRow]) -> list[SkillComparison]:
    """
    One row per skill across both analyses (case-insensitive). Ordered: changed
    rows first (gained, lost), then the rest, each by name.
    """
    by_a = {r.skill_name.lower(): r for r in a}
    by_b = {r.skill_name.lower(): r for r in b}
    rows: list[SkillComparison] = []
    for key in sorted(set(by_a) | set(by_b)):
        ra, rb = by_a.get(key), by_b.get(key)
        if ra and rb:
            matched_a, matched_b = ra.status == MATCHED, rb.status == MATCHED
            change = GAINED if matched_b and not matched_a else LOST if matched_a and not matched_b else UNCHANGED
        else:
            change = ONLY_IN_A if ra else ONLY_IN_B
        name = (rb or ra).skill_name  # type: ignore[union-attr]
        rows.append(
            SkillComparison(
                skill_name=name,
                kind_a=ra.kind if ra else None,
                kind_b=rb.kind if rb else None,
                status_a=ra.status if ra else None,
                status_b=rb.status if rb else None,
                change=change,
            )
        )
    order = {GAINED: 0, LOST: 1, ONLY_IN_B: 2, ONLY_IN_A: 3, UNCHANGED: 4}
    return sorted(rows, key=lambda r: (order[r.change], r.skill_name.lower()))
