"""Unit tests for analysis comparison and Markdown report rendering (pure Python, no database)."""
from apps.analyses.services.comparison import (
    GAINED,
    LOST,
    ONLY_IN_A,
    ONLY_IN_B,
    UNCHANGED,
    SkillRow,
    compare_skill_results,
    comparison_basis,
)
from apps.analyses.services.report import render_markdown


def row(name, status, kind="required", weight=1):
    return SkillRow(skill_name=name, kind=kind, weight=weight, status=status)


# --- comparison ------------------------------------------------------------------------


def test_basis_reflects_what_the_analyses_share():
    assert comparison_basis("r1", "r1", 1, 1) == "same_resume_and_job"
    assert comparison_basis("r1", "r2", 1, 1) == "same_job"
    assert comparison_basis("r1", "r1", 1, 2) == "same_resume"
    assert comparison_basis("r1", "r2", 1, 2) == "different"


def test_gained_lost_and_unchanged():
    a = [row("Python", "matched"), row("Docker", "missing"), row("AWS", "matched"), row("MySQL", "related")]
    b = [row("Python", "matched"), row("Docker", "matched"), row("AWS", "missing"), row("MySQL", "missing")]
    changes = {r.skill_name: r.change for r in compare_skill_results(a, b)}
    assert changes == {"Python": UNCHANGED, "Docker": GAINED, "AWS": LOST, "MySQL": UNCHANGED}


def test_related_to_matched_counts_as_gained():
    # "related" never scores, so related -> matched is a real gain
    rows = compare_skill_results([row("Kubernetes", "related")], [row("Kubernetes", "matched")])
    assert rows[0].change == GAINED
    assert (rows[0].status_a, rows[0].status_b) == ("related", "matched")


def test_skills_only_in_one_job():
    rows = compare_skill_results([row("Java", "missing")], [row("Go", "matched", kind="preferred")])
    by_name = {r.skill_name: r for r in rows}
    assert by_name["Java"].change == ONLY_IN_A and by_name["Java"].kind_b is None
    assert by_name["Go"].change == ONLY_IN_B and by_name["Go"].status_a is None
    assert by_name["Go"].kind_b == "preferred"


def test_names_are_compared_case_insensitively_and_b_spelling_wins():
    rows = compare_skill_results([row("postgresql", "missing")], [row("PostgreSQL", "matched")])
    assert len(rows) == 1
    assert rows[0].skill_name == "PostgreSQL" and rows[0].change == GAINED


def test_ordering_puts_changes_first():
    a = [row("A", "matched"), row("B", "missing"), row("C", "matched"), row("D", "missing")]
    b = [row("A", "matched"), row("B", "matched"), row("C", "missing"), row("E", "missing")]
    assert [(r.skill_name, r.change) for r in compare_skill_results(a, b)] == [
        ("B", GAINED), ("C", LOST), ("E", ONLY_IN_B), ("D", ONLY_IN_A), ("A", UNCHANGED),
    ]


def test_empty_inputs():
    assert compare_skill_results([], []) == []


# --- report ----------------------------------------------------------------------------

DATA = {
    "id": 7,
    "resume_title": "Backend v2",
    "job_title": "Backend Intern @ Acme",
    "score": 58.0,
    "score_label": "Resume-to-job matching score. It is not a probability of being hired.",
    "required_coverage": 60.0,
    "preferred_coverage": 50.0,
    "algorithm_version": "baseline-v1",
    "breakdown": {
        "formula": "0.80 × required coverage (60.0) + 0.20 × preferred coverage (50.0)",
        "required": {"matched_weight": 3, "total_weight": 5, "coverage": 60.0},
        "preferred": {"matched_weight": 1, "total_weight": 2, "coverage": 50.0},
    },
    "strengths": ["Django: demonstrated in Project: Inventory Tracker"],
    "improvements": ["Missing required skill: Docker"],
    "suggestions": [],
    "skill_results": [
        {"skill_name": "Python", "kind": "required", "weight": 2, "status": "matched",
         "evidence": [{"location": "Skills section", "text": "Python | SQL"}], "explanation": "Found."},
        {"skill_name": "MySQL", "kind": "required", "weight": 1, "status": "related",
         "evidence": [], "explanation": "Related skills do not add to the score."},
        {"skill_name": "C#", "kind": "preferred", "weight": 1, "status": "missing",
         "evidence": [], "explanation": "Not found."},
    ],
    "created_at": "2026-10-12T07:00:00Z",
}


def test_report_has_score_label_and_formula():
    md = render_markdown(DATA)
    assert md.startswith("# Resume analysis: Backend Intern @ Acme\n")
    assert "## Matching score: 58.0 / 100" in md
    assert "not a probability of being hired" in md
    assert "Required skills: 60.0% (3/5 weight)" in md
    assert "Preferred skills: 50.0% (1/2 weight)" in md
    assert "do not count toward the score" in md
    assert md.rstrip().endswith("it is not a prediction of hiring outcomes._")


def test_report_table_escapes_markdown():
    md = render_markdown(DATA)
    assert "| Python | required | 2 | Matched | Found. |" in md
    assert "| MySQL | required | 1 | Related skill found |" in md
    assert "| C\\# | preferred |" in md
    # a pipe inside resume text must not break the table or the evidence line
    assert "Python \\| SQL" in md


def test_report_sections_and_empty_states():
    md = render_markdown(DATA)
    assert "## Strengths\n\n- Django: demonstrated in Project: Inventory Tracker" in md
    assert "## Areas for improvement\n\n- Missing required skill: Docker" in md
    assert "## Suggestions\n\n_None._" in md
    assert "- **Python**: Skills section:" in md


def test_report_handles_missing_coverage_and_no_evidence():
    data = {**DATA, "preferred_coverage": None, "skill_results": [], "strengths": []}
    md = render_markdown(data)
    assert "Preferred skills: n/a" in md
    assert "_No evidence lines recorded._" in md
    assert "## Strengths\n\n_None identified._" in md


def test_report_collapses_newlines_in_user_text():
    md = render_markdown({**DATA, "job_title": "Dev\n# injected heading"})
    assert md.splitlines()[0] == "# Resume analysis: Dev \\# injected heading"
