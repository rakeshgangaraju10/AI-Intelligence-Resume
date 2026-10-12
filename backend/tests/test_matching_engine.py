"""Unit tests for the deterministic matching engine (pure Python, no database)."""
from apps.analyses.services.matching import (
    MATCHED,
    MISSING,
    PREFERRED,
    RELATED,
    REQUIRED,
    SKILLS_SECTION,
    Evidence,
    MatchingError,
    Requirement,
    ResumeSkill,
    match_resume_to_job,
    normalise_requirements,
)

GROUPS = [
    ("relational SQL databases", frozenset({"PostgreSQL", "MySQL", "SQLite"})),
    ("container tooling", frozenset({"Docker", "Kubernetes"})),
]


def skill(name, location=SKILLS_SECTION, text=None, verified=True):
    return ResumeSkill(name, [Evidence(location, text or f"Skills: {name}")], verified=verified)


def raises(code, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except MatchingError as exc:
        assert exc.code == code, exc.code
        return
    raise AssertionError(f"expected MatchingError({code})")


def by_name(result):
    return {r.name: r for r in result.results}


# --- Scoring -------------------------------------------------------------------------


def test_required_only_coverage_is_the_score():
    result = match_resume_to_job(
        [skill("Python"), skill("Django")],
        [Requirement("Python"), Requirement("Django"), Requirement("Docker"), Requirement("AWS")],
    )
    assert result.required_coverage == 50.0
    assert result.preferred_coverage is None
    assert result.score == 50.0
    assert "required coverage only" in result.breakdown["formula"]


def test_weighted_required_and_preferred_combination():
    # required: Python(3) matched, Docker(1) missing -> 75%; preferred: AWS(1) matched -> 100%
    result = match_resume_to_job(
        [skill("Python"), skill("AWS")],
        [
            Requirement("Python", REQUIRED, 3),
            Requirement("Docker", REQUIRED, 1),
            Requirement("AWS", PREFERRED, 1),
        ],
    )
    assert result.required_coverage == 75.0
    assert result.preferred_coverage == 100.0
    assert result.score == 80.0  # 0.8*75 + 0.2*100
    assert result.breakdown["required"] == {"matched_weight": 3, "total_weight": 4, "coverage": 75.0}


def test_configurable_required_share():
    reqs = [Requirement("Python"), Requirement("AWS", PREFERRED)]
    result = match_resume_to_job([skill("AWS")], reqs, required_share=0.5)
    assert result.score == 50.0
    raises("invalid_config", match_resume_to_job, [], reqs, required_share=0.3)
    raises("invalid_config", match_resume_to_job, [], reqs, required_share=1.5)


def test_preferred_only_job():
    result = match_resume_to_job([skill("Git")], [Requirement("Git", PREFERRED), Requirement("Jira", PREFERRED)])
    assert result.required_coverage is None
    assert result.score == 50.0


def test_score_bounds_with_no_resume_skills_and_full_match():
    reqs = [Requirement("Python"), Requirement("SQL", PREFERRED)]
    assert match_resume_to_job([], reqs).score == 0.0
    assert match_resume_to_job([skill("Python"), skill("SQL")], reqs).score == 100.0


def test_score_is_reproducible():
    reqs = [Requirement("Python", REQUIRED, 2), Requirement("Docker"), Requirement("AWS", PREFERRED)]
    skills = [skill("Python"), skill("Kubernetes")]
    first = match_resume_to_job(skills, reqs, GROUPS)
    second = match_resume_to_job(skills, reqs, GROUPS)
    assert first == second


def test_rounding_to_one_decimal():
    result = match_resume_to_job([skill("A")], [Requirement("A"), Requirement("B"), Requirement("C")])
    assert result.score == 33.3


# --- Edge cases -----------------------------------------------------------------------


def test_empty_job_is_rejected():
    raises("no_requirements", match_resume_to_job, [skill("Python")], [])


def test_invalid_and_zero_weights_are_rejected():
    raises("invalid_weight", match_resume_to_job, [], [Requirement("Python", REQUIRED, 0)])
    raises("invalid_weight", match_resume_to_job, [], [Requirement("Python", REQUIRED, -2)])
    raises("invalid_weight", match_resume_to_job, [], [Requirement("Python", REQUIRED, True)])
    raises("invalid_kind", match_resume_to_job, [], [Requirement("Python", "optional")])
    raises("invalid_requirement", match_resume_to_job, [], [Requirement("   ")])


def test_duplicate_requirements_are_merged():
    merged = normalise_requirements([
        Requirement("Python", PREFERRED, 2),
        Requirement("python", REQUIRED, 1),
        Requirement("PYTHON", REQUIRED, 3),
        Requirement("Docker"),
        Requirement("docker"),
    ])
    assert merged == [Requirement("Python", REQUIRED, 3), Requirement("Docker", REQUIRED, 1)]


def test_matching_is_case_insensitive():
    result = match_resume_to_job([skill("postgresql")], [Requirement("PostgreSQL")])
    assert result.score == 100.0


# --- Classification and evidence --------------------------------------------------------


def test_related_skills_are_reported_but_not_scored():
    result = match_resume_to_job(
        [skill("MySQL", "Project: Shop API", "Built a REST API on MySQL")],
        [Requirement("PostgreSQL"), Requirement("Docker")],
        GROUPS,
    )
    r = by_name(result)
    assert r["PostgreSQL"].status == RELATED
    assert r["PostgreSQL"].related_to == ["MySQL"]
    assert r["PostgreSQL"].related_reason == "relational SQL databases"
    assert "do not add to the score" in r["PostgreSQL"].explanation
    assert r["Docker"].status == MISSING
    assert result.score == 0.0
    assert result.breakdown["related_skills_count_toward_score"] is False


def test_matched_skill_carries_evidence_and_explanation():
    result = match_resume_to_job(
        [skill("Django", "Experience: Intern at Acme", "Built REST APIs with Django")],
        [Requirement("Django")],
    )
    r = by_name(result)["Django"]
    assert r.status == MATCHED
    assert r.evidence[0].location == "Experience: Intern at Acme"
    assert "Experience: Intern at Acme" in r.explanation
    assert "Built REST APIs with Django" in r.explanation


def test_user_added_skill_without_evidence_still_matches():
    result = match_resume_to_job([ResumeSkill("Go", [], verified=True, user_added=True)], [Requirement("Go")])
    assert by_name(result)["Go"].status == MATCHED
    assert "Added manually" in by_name(result)["Go"].evidence[0].text


# --- Feedback ------------------------------------------------------------------------


def test_strengths_require_usage_evidence():
    result = match_resume_to_job(
        [skill("Django", "Project: CareerForge", "Django REST API"), skill("Python")],
        [Requirement("Django"), Requirement("Python")],
    )
    assert result.strengths[0].startswith("Django: demonstrated in Project: CareerForge")
    assert any("Python is listed but not shown" in s for s in result.improvements)


def test_missing_required_skills_are_improvements_ordered_by_weight():
    result = match_resume_to_job(
        [],
        [Requirement("Docker", REQUIRED, 1), Requirement("AWS", REQUIRED, 3), Requirement("Jira", PREFERRED)],
    )
    assert result.improvements[:2] == ["Missing required skill: AWS (weight 3)", "Missing required skill: Docker"]


def test_suggestions_never_tell_user_to_claim_unused_skills():
    result = match_resume_to_job([skill("Kubernetes")], [Requirement("Docker"), Requirement("AWS")], GROUPS)
    docker, aws = result.suggestions[0], result.suggestions[1]
    assert "If you have used Docker" in docker and "transferable" in docker
    assert "Don't add skills you haven't used" in aws


def test_unverified_matches_are_flagged_for_review():
    result = match_resume_to_job([skill("Python", verified=False)], [Requirement("Python")])
    assert any("not yet confirmed" in s for s in result.suggestions)


def test_missing_preferred_skills_are_grouped():
    result = match_resume_to_job([skill("Python")], [Requirement("Python"), Requirement("Jira", PREFERRED)])
    assert result.suggestions == [
        "Nice-to-have skills not found: Jira. Mention any you have genuinely used."
    ]
    assert by_name(result)["Jira"].status == MISSING
    assert by_name(result)["Python"].status == MATCHED
