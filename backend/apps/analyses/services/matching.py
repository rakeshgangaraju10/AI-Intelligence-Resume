"""
Deterministic, explainable resume-to-job matching (algorithm "baseline-v1").

Pure Python, no Django imports: every rule here is unit-tested in isolation.

Score
-----
    required_coverage  = 100 * sum(weight of matched required) / sum(weight of required)
    preferred_coverage = 100 * sum(weight of matched preferred) / sum(weight of preferred)

    score = required_share * required_coverage + (1 - required_share) * preferred_coverage
            when the job has both kinds (required_share defaults to 0.8),
          = the one coverage that exists otherwise.

A requirement is "matched" only when the same canonical skill is in the resume.
"Related" skills (same curated group, e.g. MySQL for PostgreSQL) are reported
for context with the group as the reason, but add nothing to the score.
The score is a resume-to-job *matching* score, not a probability of being hired.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ALGORITHM_VERSION = "baseline-v1"
REQUIRED = "required"
PREFERRED = "preferred"
MATCHED = "matched"
MISSING = "missing"
RELATED = "related"
SKILLS_SECTION = "Skills section"
MAX_LIST_ITEMS = 6


class MatchingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Requirement:
    name: str
    kind: str = REQUIRED
    weight: int = 1


@dataclass(frozen=True)
class Evidence:
    location: str   # "Skills section", "Project: CareerForge", "Experience: Intern at Acme"
    text: str       # the resume text that mentions the skill


@dataclass
class ResumeSkill:
    name: str
    evidence: list[Evidence] = field(default_factory=list)
    verified: bool = False     # confirmed or added by the user
    user_added: bool = False


@dataclass
class SkillResult:
    name: str
    kind: str
    weight: int
    status: str
    evidence: list[Evidence]
    related_to: list[str]
    related_reason: str
    explanation: str


@dataclass
class MatchResult:
    score: float
    required_coverage: float | None
    preferred_coverage: float | None
    required_share: float
    results: list[SkillResult]
    strengths: list[str]
    improvements: list[str]
    suggestions: list[str]
    breakdown: dict
    algorithm_version: str = ALGORITHM_VERSION


# --- helpers ----------------------------------------------------------------------


def _key(name: str) -> str:
    return " ".join(name.split()).lower()


def normalise_requirements(requirements: list[Requirement]) -> list[Requirement]:
    """
    Validate and de-duplicate (case-insensitive). If a skill appears more than
    once, "required" wins over "preferred" and the highest weight of the winning
    kind is kept. Order of first appearance is preserved.
    """
    merged: dict[str, Requirement] = {}
    for req in requirements:
        name = " ".join(req.name.split())
        if not name:
            raise MatchingError("invalid_requirement", "A requirement has an empty skill name.")
        if req.kind not in (REQUIRED, PREFERRED):
            raise MatchingError("invalid_kind", f"Unknown requirement kind '{req.kind}'.")
        if not isinstance(req.weight, int) or isinstance(req.weight, bool) or req.weight <= 0:
            raise MatchingError("invalid_weight", f"Weight for '{name}' must be a positive integer.")
        key = _key(name)
        current = merged.get(key)
        if current is None:
            merged[key] = Requirement(name, req.kind, req.weight)
        elif current.kind == req.kind:
            merged[key] = Requirement(current.name, current.kind, max(current.weight, req.weight))
        elif req.kind == REQUIRED:  # upgrade preferred -> required
            merged[key] = Requirement(current.name, REQUIRED, req.weight)
    return list(merged.values())


def _coverage(results: list[SkillResult], kind: str) -> tuple[float | None, int, int]:
    total = sum(r.weight for r in results if r.kind == kind)
    if total == 0:
        return None, 0, 0
    matched = sum(r.weight for r in results if r.kind == kind and r.status == MATCHED)
    return 100.0 * matched / total, matched, total


def _clamp(value: float) -> float:
    return round(min(100.0, max(0.0, value)), 1)


def _quote(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _strong_evidence(evidence: list[Evidence]) -> list[Evidence]:
    """Evidence of use (project/experience), as opposed to only being listed."""
    return [e for e in evidence if e.location != SKILLS_SECTION]


# --- engine -------------------------------------------------------------------------


def match_resume_to_job(
    resume_skills: list[ResumeSkill],
    requirements: list[Requirement],
    skill_groups: list[tuple[str, frozenset[str]]] | None = None,
    required_share: float = 0.8,
) -> MatchResult:
    if not 0.5 <= required_share <= 1.0:
        raise MatchingError("invalid_config", "required_share must be between 0.5 and 1.0.")
    reqs = normalise_requirements(requirements)
    if not reqs:
        raise MatchingError("no_requirements", "The job has no required or preferred skills to compare against.")

    resume_by_key = {_key(s.name): s for s in resume_skills}
    groups = [(reason, frozenset(_key(n) for n in names), names) for reason, names in (skill_groups or [])]

    results: list[SkillResult] = []
    for req in reqs:
        label = "Required" if req.kind == REQUIRED else "Preferred"
        found = resume_by_key.get(_key(req.name))
        if found is not None:
            evidence = found.evidence or [Evidence(SKILLS_SECTION, "Added manually to your skills list")]
            first = evidence[0]
            explanation = f"{label} skill '{req.name}' found in your resume ({first.location}: \"{_quote(first.text)}\")."
            results.append(SkillResult(req.name, req.kind, req.weight, MATCHED, evidence, [], "", explanation))
            continue

        related: list[str] = []
        reason = ""
        for group_reason, keys, _names in groups:
            if _key(req.name) in keys:
                hits = [s.name for k, s in resume_by_key.items() if k in keys]
                for hit in hits:
                    if hit not in related:
                        related.append(hit)
                if hits and not reason:
                    reason = group_reason
        if related:
            explanation = (
                f"{label} skill '{req.name}' was not found. Your resume lists {', '.join(related)} "
                f"({reason}). Related skills are shown for context and do not add to the score."
            )
            evidence = [e for name in related for e in resume_by_key[_key(name)].evidence[:1]]
            results.append(SkillResult(req.name, req.kind, req.weight, RELATED, evidence, related, reason, explanation))
        else:
            explanation = f"{label} skill '{req.name}' was not found in your resume."
            results.append(SkillResult(req.name, req.kind, req.weight, MISSING, [], [], "", explanation))

    req_cov, req_matched, req_total = _coverage(results, REQUIRED)
    pref_cov, pref_matched, pref_total = _coverage(results, PREFERRED)
    if req_cov is not None and pref_cov is not None:
        score = required_share * req_cov + (1 - required_share) * pref_cov
        formula = (
            f"{required_share:.2f} × required coverage ({req_cov:.1f}) + "
            f"{1 - required_share:.2f} × preferred coverage ({pref_cov:.1f})"
        )
    elif req_cov is not None:
        score, formula = req_cov, f"required coverage only ({req_cov:.1f}); the job lists no preferred skills"
    else:
        score, formula = pref_cov, f"preferred coverage only ({pref_cov:.1f}); the job lists no required skills"

    breakdown = {
        "formula": formula,
        "required": {"matched_weight": req_matched, "total_weight": req_total,
                     "coverage": None if req_cov is None else round(req_cov, 1)},
        "preferred": {"matched_weight": pref_matched, "total_weight": pref_total,
                      "coverage": None if pref_cov is None else round(pref_cov, 1)},
        "required_share": required_share,
        "related_skills_count_toward_score": False,
    }

    strengths, improvements, suggestions = _feedback(results, resume_skills)
    return MatchResult(
        score=_clamp(score),
        required_coverage=None if req_cov is None else round(req_cov, 1),
        preferred_coverage=None if pref_cov is None else round(pref_cov, 1),
        required_share=required_share,
        results=results,
        strengths=strengths,
        improvements=improvements,
        suggestions=suggestions,
        breakdown=breakdown,
    )


def _feedback(results: list[SkillResult], resume_skills: list[ResumeSkill]) -> tuple[list[str], list[str], list[str]]:
    """Evidence-based feedback. Never suggests claiming a skill the user hasn't used."""
    by_priority = sorted(results, key=lambda r: (r.kind != REQUIRED, -r.weight))
    matched = [r for r in by_priority if r.status == MATCHED]

    strengths: list[str] = []
    listed_only: list[SkillResult] = []
    for r in matched:
        strong = _strong_evidence(r.evidence)
        if strong:
            strengths.append(f"{r.name}: demonstrated in {strong[0].location} — \"{_quote(strong[0].text, 100)}\"")
        else:
            listed_only.append(r)
    if matched and not strengths:
        strengths.append(
            f"You list {len(matched)} of the job's skills ({', '.join(r.name for r in matched[:MAX_LIST_ITEMS])})."
        )

    improvements: list[str] = []
    for r in by_priority:
        if r.status != MATCHED and r.kind == REQUIRED:
            improvements.append(f"Missing required skill: {r.name}" + (f" (weight {r.weight})" if r.weight > 1 else ""))
    for r in listed_only:
        improvements.append(
            f"{r.name} is listed but not shown in any project or experience entry. "
            "Add a bullet describing where you used it."
        )

    suggestions: list[str] = []
    for r in by_priority:
        if r.kind != REQUIRED or r.status == MATCHED:
            continue
        if r.status == RELATED:
            suggestions.append(
                f"{r.name}: you list {', '.join(r.related_to)} ({r.related_reason}). If you have used {r.name}, "
                f"add it with a concrete example; if not, describe your {r.related_to[0]} work as transferable experience."
            )
        else:
            suggestions.append(
                f"{r.name}: if you have real experience with it, add it to your Skills and back it up with a "
                "project or experience bullet. Don't add skills you haven't used."
            )
    missing_preferred = [r.name for r in by_priority if r.kind == PREFERRED and r.status != MATCHED]
    if missing_preferred:
        suggestions.append(
            "Nice-to-have skills not found: " + ", ".join(missing_preferred[:MAX_LIST_ITEMS])
            + ". Mention any you have genuinely used."
        )
    unverified = [r.name for r in matched if not _resume_skill(resume_skills, r.name).verified]
    if unverified:
        suggestions.append(
            f"{len(unverified)} matched skill(s) were detected automatically and not yet confirmed "
            f"({', '.join(unverified[:MAX_LIST_ITEMS])}). Review them on your resume page."
        )
    return strengths[:MAX_LIST_ITEMS], improvements[: MAX_LIST_ITEMS * 2], suggestions[: MAX_LIST_ITEMS * 2]


def _resume_skill(resume_skills: list[ResumeSkill], name: str) -> ResumeSkill:
    key = _key(name)
    return next(s for s in resume_skills if _key(s.name) == key)
